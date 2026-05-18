"""docgen_agent 主循环 — 分批逐节生成 + 拼接 + 格式校验。

工作流程:
    Phase 1  读取文件     — Agent 调用 read_requirement / read_output_schema / read_output_layout
    Phase 2  拆解章节     — 按 output_schema 展开为 二级/三级 标题列表
    Phase 3  逐节生成     — 每个 (子)节独立调用 LLM，上下文含需求+规范+前后节摘要
    Phase 4  拼接校验     — 拼接全文 → 调用 LLM 做格式一致性校验
    Phase 5  保存并转 PDF — save_document(.md) + convert_to_pdf(.pdf)
"""

import json
import threading
from datetime import datetime
from pathlib import Path
from typing import Any, Optional, cast

from loguru import logger
from openai.types.chat import (
    ChatCompletionMessageFunctionToolCall,
    ChatCompletionMessageParam,
    ChatCompletionToolUnionParam,
)

from .tools import (
    _fix_unordered_lists_in_md,
    normalize_document_header,
    normalize_heading_numbering,
    _validate_table_captions,
    client,
    OUTPUT_DIR,
    execute_tool,
    get_doc_structure,
    get_tools_for_phase,
    set_source_file,
)

CURRENT_DIR = Path(__file__).parent

MAX_TRACE_EVENTS = 1000
MAX_TRACE_TEXT = 4000
MAX_READ_CONTEXT_CHARS = 60000
MAX_SECTION_REQUIREMENT_CHARS = 5000
MAX_SECTION_PROJECT_CONTEXT_CHARS = 14000

_PROJECT_CONTEXT_TOOL_NAMES = {
    "list_project_files",
    "read_project_file",
    "search_project",
    "read_dependency_manifest",
    "read_api_routes",
    "read_data_models",
    "read_deployment_config",
    "read_existing_tests",
    "read_ci_config",
    "read_architecture_context",
    "read_test_context",
}

_TRACE_LOCK = threading.RLock()
_RUN_TRACES: dict[str, dict[str, Any]] = {}
_INTERRUPT_FLAGS: set[str] = set()
_TERMINATE_FLAGS: set[str] = set()
_PENDING_HINTS: dict[str, list[str]] = {}


class GenerationInterrupted(RuntimeError):
    """文档生成被用户中断。"""


class GenerationTerminated(RuntimeError):
    """文档生成被用户终止。"""


def _now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _trim_trace_value(value: Any) -> Any:
    if isinstance(value, str):
        return value if len(value) <= MAX_TRACE_TEXT else value[:MAX_TRACE_TEXT] + "...[truncated]"
    if isinstance(value, dict):
        return {k: _trim_trace_value(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_trim_trace_value(v) for v in value[:50]]
    return value


def _ensure_run_state_locked(run_id: str) -> dict[str, Any]:
    state = _RUN_TRACES.get(run_id)
    if state is None:
        state = {
            "run_id": run_id,
            "status": "running",
            "doc_type": "",
            "created_at": _now_iso(),
            "updated_at": _now_iso(),
            "output_path": None,
            "pdf_path": None,
            "error": None,
            "events": [],
            "next_event_id": 1,
        }
        _RUN_TRACES[run_id] = state
    return state


def start_generation_trace(
    run_id: str,
    doc_type: str = "",
    user_hint: str = "",
    *,
    reset: bool = False,
) -> dict[str, Any]:
    """初始化或复用一次文档生成运行的 trace 状态。"""
    with _TRACE_LOCK:
        if reset or run_id not in _RUN_TRACES:
            if reset:
                _INTERRUPT_FLAGS.discard(run_id)
                _TERMINATE_FLAGS.discard(run_id)
            _RUN_TRACES[run_id] = {
                "run_id": run_id,
                "status": "running",
                "doc_type": doc_type,
                "created_at": _now_iso(),
                "updated_at": _now_iso(),
                "output_path": None,
                "pdf_path": None,
                "error": None,
                "events": [],
                "next_event_id": 1,
            }
        else:
            state = _ensure_run_state_locked(run_id)
            state["status"] = "running"
            state["doc_type"] = doc_type or state.get("doc_type", "")
            state["updated_at"] = _now_iso()

    _record_trace(
        run_id,
        "run_started",
        phase="run",
        doc_type=doc_type,
        user_hint=user_hint,
    )
    trace = get_generation_trace(run_id)
    return trace or {}


def get_generation_trace(run_id: str) -> dict[str, Any] | None:
    """读取指定运行的 trace。供前端轮询渲染思考、阶段和工具调用过程。"""
    with _TRACE_LOCK:
        state = _RUN_TRACES.get(run_id)
        if state is None:
            return None
        return {
            "run_id": state["run_id"],
            "status": state["status"],
            "doc_type": state.get("doc_type", ""),
            "created_at": state.get("created_at"),
            "updated_at": state.get("updated_at"),
            "output_path": state.get("output_path"),
            "pdf_path": state.get("pdf_path"),
            "error": state.get("error"),
            "interrupted": run_id in _INTERRUPT_FLAGS or state["status"] in {"interrupt_requested", "interrupted"},
            "terminated": run_id in _TERMINATE_FLAGS or state["status"] in {"terminate_requested", "terminated"},
            "events": [event.copy() for event in state.get("events", [])],
        }


def request_generation_interrupt(run_id: str) -> bool:
    """请求中断指定运行。实际停止点在下一次模型调用返回或工具调用边界。"""
    with _TRACE_LOCK:
        state = _RUN_TRACES.get(run_id)
        if state is None:
            return False
        _INTERRUPT_FLAGS.add(run_id)
        state["status"] = "interrupt_requested"
        state["updated_at"] = _now_iso()

    _record_trace(run_id, "interrupt_requested", phase="run")
    return True


def request_generation_terminate(run_id: str) -> bool:
    """请求终止指定运行。与 interrupt 一样是协作式停止，但状态标记为 terminated。"""
    with _TRACE_LOCK:
        state = _RUN_TRACES.get(run_id)
        if state is None:
            return False
        _TERMINATE_FLAGS.add(run_id)
        state["status"] = "terminate_requested"
        state["updated_at"] = _now_iso()

    _record_trace(run_id, "terminate_requested", phase="run")
    return True


def _set_run_status(run_id: Optional[str], status: str, **updates: Any) -> None:
    if not run_id:
        return
    with _TRACE_LOCK:
        state = _ensure_run_state_locked(run_id)
        state["status"] = status
        state["updated_at"] = _now_iso()
        for key, value in updates.items():
            state[key] = _trim_trace_value(value)


def _record_trace(run_id: Optional[str], event_type: str, phase: str = "", **payload: Any) -> None:
    if not run_id:
        return
    with _TRACE_LOCK:
        state = _ensure_run_state_locked(run_id)
        events = state["events"]
        event_id = state.setdefault("next_event_id", len(events) + 1)
        state["next_event_id"] = event_id + 1
        events.append({
            "id": event_id,
            "time": _now_iso(),
            "type": event_type,
            "phase": phase,
            **{key: _trim_trace_value(value) for key, value in payload.items()},
        })
        if len(events) > MAX_TRACE_EVENTS:
            del events[: len(events) - MAX_TRACE_EVENTS]
        state["updated_at"] = _now_iso()


def _safe_json_loads(raw: str) -> dict[str, Any]:
    try:
        value = json.loads(raw or "{}")
        return value if isinstance(value, dict) else {"value": value}
    except json.JSONDecodeError:
        return {"raw": raw}


def _chat_message(payload: dict[str, Any]) -> ChatCompletionMessageParam:
    return cast(ChatCompletionMessageParam, payload)


def _chat_tools(tools: list[dict[str, Any]]) -> list[ChatCompletionToolUnionParam]:
    return cast(list[ChatCompletionToolUnionParam], tools)


def _function_tool_calls(tool_calls: Any) -> list[ChatCompletionMessageFunctionToolCall]:
    if not tool_calls:
        return []
    return [
        cast(ChatCompletionMessageFunctionToolCall, tool_call)
        for tool_call in tool_calls
        if getattr(tool_call, "type", "") == "function"
    ]


def _append_project_context(chunks: list[str], tool_name: str, result: str) -> None:
    if tool_name not in _PROJECT_CONTEXT_TOOL_NAMES:
        return
    if not result.strip():
        return
    chunks.append(f"### {tool_name}\n{result}")


def _project_context_tool_for_doc_type(doc_type: str) -> str:
    if doc_type == "架构设计文档":
        return "read_architecture_context"
    if doc_type == "测试文档":
        return "read_test_context"
    return ""


def _check_interrupted(run_id: Optional[str], phase: str = "") -> None:
    if not run_id:
        return
    with _TRACE_LOCK:
        should_terminate = run_id in _TERMINATE_FLAGS
        should_interrupt = run_id in _INTERRUPT_FLAGS
    if should_terminate:
        _set_run_status(run_id, "terminated")
        _record_trace(run_id, "terminated", phase=phase)
        raise GenerationTerminated(f"文档生成已终止: {run_id}")
    if should_interrupt:
        _set_run_status(run_id, "interrupted")
        _record_trace(run_id, "interrupted", phase=phase)
        raise GenerationInterrupted(f"文档生成已中断: {run_id}")


def append_generation_hint(run_id: str, hint: str) -> bool:
    """在生成过程中追加用户提示词。下一轮 LLM 调用会作为 user 消息注入。"""
    with _TRACE_LOCK:
        state = _RUN_TRACES.get(run_id)
        if state is None or state["status"] not in ("running",):
            return False
        _PENDING_HINTS.setdefault(run_id, []).append(hint)
    _record_trace(run_id, "hint_appended", phase="run", hint=hint)
    return True


def _consume_pending_hints(run_id: Optional[str]) -> list[str]:
    """取出并清空指定运行的待注入提示词。"""
    if not run_id:
        return []
    with _TRACE_LOCK:
        return _PENDING_HINTS.pop(run_id, [])


# ============================================================
# 提示词模板
# ============================================================

READ_PHASE_PROMPT = """\
你是一个专业的软件工程文档撰写智能体。

当前任务：为生成 **{doc_type}** 做准备，先读取所有必要的文件。

请依次调用：
1. read_requirement — 了解项目需求
2. read_output_schema(doc_type="{doc_type}") — 了解文档结构
3. read_output_layout — 了解排版规范

如生成架构设计文档，优先调用 read_architecture_context；如生成测试文档，优先调用 read_test_context。
如果聚合上下文不足，再按需调用细粒度项目分析工具：
- list_project_files / read_project_file / search_project — 了解项目结构和源码
- read_dependency_manifest — 了解技术栈和依赖
- read_api_routes — 了解后端 API
- read_data_models — 了解数据模型
- read_deployment_config — 了解部署和运行环境
- read_existing_tests / read_ci_config — 了解测试基础和执行命令

可以同时调用多个工具以提高效率。
"""

SECTION_SYSTEM_PROMPT = """\
你是一个专业的软件工程文档撰写专家。你正在撰写 **{doc_type}** 的一个完整章节组。

## 项目上下文
{requirement_summary}

## 目标章节
- 章节路径: {section_path}
- 章节描述: {section_description}

## 本章节的完整结构定义（含所有子章节）
```json
{section_schema}
```

## output_layout.json 规范摘录
{layout_rules}

## {context_label}
{context_text}

## 用户额外指示
{user_hint}

## 写作要求（以下规则必须严格遵守）
1. 只输出本章节组（含子章节）的 Markdown 正文，不要输出文档总标题和元数据行；总标题和元数据由拼接阶段统一添加。
2. 输出必须从该章节组的标题行开始，并严格遵循上述 output_schema.json 结构；required:true 的章节必须生成，tips 中的内容要完整覆盖。
3. 四级及更深标题必须使用 Markdown 标题和四段/多段十进制编号，例如 `##### 3.1.1.2 字段校验`；严禁把 `(1) 标题`、`(2) 标题` 当作标题使用，括号编号只能用于正文枚举。
4. 所有格式、排版、标题层级、元数据字段、图表标题、表格标题、编号、列表和分页规则均以 output_layout.json 为唯一依据，不得自行创造或覆盖格式规则。
5. 如 schema 要求图表，按 output_schema.json 的 uml_diagram_guide 和该章节 tools 字段选择并调用工具；图片路径必须直接使用工具返回值。
6. Markdown 表格必须是可解析的标准表格：表头行、对齐行、数据行的列数必须一致；单元格内不要使用未转义的竖线；表格标题必须是 `**表X-Y：具体表名**`，不得使用“表格说明”等泛化标题。
7. 内容必须详实、专业，每个章节都要达到可独立审阅的深度，并结合项目真实需求或代码信息展开。
8. 生成架构设计文档时，必须基于读取阶段获得的真实目录、依赖、路由、数据模型和部署配置展开；缺失项标注“待确认”，不要编造。
9. 生成测试文档时，必须基于读取阶段获得的现有测试、接口、数据模型、CI 配置和部署配置展开；缺失项标注“待补充”，不要编造。
10. 严禁输出任何客套话或 AI 声明，直接输出文档正文。
"""

STITCH_SYSTEM_PROMPT = """\
你是一个专业的软件工程文档审校专家。你的任务是将多个章节片段拼接成一份完整规范的文档。

## 要求（按优先级排列）
1. 全文第一行必须保留为一级 Markdown 文档标题；标题之后立即按 output_layout.json 的 document_meta.fields 顺序生成元数据行。
2. 所有格式、排版、标题层级、图表标题、表格标题、编号、列表和分页规则均以 output_layout.json 为唯一依据。
3. 删除正文中重复或残留的元数据行、孤立格式标记、客套话和 AI 声明。
4. 表格必须保持标准 Markdown 结构：表头行、对齐行、数据行列数一致；发现坏表格时修复列数和表头，不要把表格降级成普通文本。
5. 图片路径必须使用工具返回的相对路径；如出现输出目录前缀，只保留相对 output_docs 的路径。
6. 图表与表格的标题、位置和编号必须按 output_layout.json 对应配置修正。
7. 输出完整 Markdown 文档，严禁客套话或 AI 声明。

## output_layout.json 规范摘录
{layout_rules}

## 文档结构（output_schema.json）
{doc_structure_summary}
"""


def _layout_prompt_excerpt(layout: str) -> str:
    """生成给模型看的布局规范摘录，内容值全部来自 output_layout.json。"""
    try:
        layout_obj = json.loads(layout)
    except json.JSONDecodeError:
        return layout

    keys = (
        "document_meta",
        "headings",
        "figures",
        "tables",
        "lists",
        "page_breaks",
        "pdf_rendering",
        "rendering_conventions",
        "boilerplate_rules",
    )
    excerpt = {key: layout_obj.get(key) for key in keys if key in layout_obj}
    return json.dumps(excerpt, ensure_ascii=False, indent=2)


# ============================================================
# Phase 1: 读取文件
# ============================================================
def _phase_read_files(doc_type: str, run_id: Optional[str] = None) -> tuple[str, str, str, str]:
    """Agent 方式读取 requirement, schema, layout 和项目上下文。"""
    messages: list[ChatCompletionMessageParam] = [
        _chat_message({"role": "system", "content": READ_PHASE_PROMPT.format(doc_type=doc_type)}),
        _chat_message({"role": "user", "content": f"请读取生成 {doc_type} 所需的所有文件。"}),
    ]

    requirement = ""
    schema = ""
    layout = ""
    project_context_chunks: list[str] = []
    read_completed = False

    for turn in range(6):
        _check_interrupted(run_id, "read_files")
        logger.info(f"  [读取阶段 Turn {turn}] 等待 LLM...")
        _record_trace(run_id, "llm_request", phase="read_files", turn=turn, action="读取需求、结构和排版规范")
        resp = client.chat.completions.create(
            model="deepseek-v4-pro",
            messages=messages,
            tools=_chat_tools(get_tools_for_phase("read")),
            temperature=0.0,
        )
        _check_interrupted(run_id, "read_files")
        msg = resp.choices[0].message
        if hasattr(msg, "reasoning_content") and msg.reasoning_content:
            _record_trace(run_id, "reasoning", phase="read_files", turn=turn, content=msg.reasoning_content)
        if msg.content:
            _record_trace(run_id, "assistant_message", phase="read_files", turn=turn, content=msg.content)

        tool_calls = _function_tool_calls(msg.tool_calls)
        if tool_calls:
            names = [tc.function.name for tc in tool_calls]
            logger.info(f"  [读取阶段] 调用: {names}")
            _record_trace(run_id, "tool_calls_planned", phase="read_files", turn=turn, tools=names)

            tc_list: list[dict[str, Any]] = []
            for tc in tool_calls:
                tc_list.append({
                    "id": tc.id,
                    "type": "function",
                    "function": {"name": tc.function.name, "arguments": tc.function.arguments},
                })
            assistant_msg: dict[str, Any] = {"role": "assistant", "content": msg.content or None, "tool_calls": tc_list}
            if hasattr(msg, "reasoning_content") and msg.reasoning_content:
                assistant_msg["reasoning_content"] = msg.reasoning_content
            messages.append(_chat_message(assistant_msg))

            for tc in tool_calls:
                _check_interrupted(run_id, "read_files")
                func_name = tc.function.name
                func_args = _safe_json_loads(tc.function.arguments)
                _record_trace(
                    run_id,
                    "tool_call",
                    phase="read_files",
                    tool_call_id=tc.id,
                    name=func_name,
                    arguments=func_args,
                )
                result = execute_tool(func_name, func_args)
                _record_trace(
                    run_id,
                    "tool_result",
                    phase="read_files",
                    tool_call_id=tc.id,
                    name=func_name,
                    result=result,
                )
                _check_interrupted(run_id, "read_files")
                messages.append(_chat_message({
                    "role": "tool", "tool_call_id": tc.id, "content": result,
                }))
                if func_name == "read_requirement":
                    requirement = result
                elif func_name == "read_output_schema":
                    schema = result
                elif func_name == "read_output_layout":
                    layout = result
                else:
                    _append_project_context(project_context_chunks, func_name, result)

            context_required = bool(_project_context_tool_for_doc_type(doc_type))
            if requirement and schema and layout and (not context_required or project_context_chunks):
                logger.info("  [读取阶段] 三份文件全部读取完毕")
                _record_trace(run_id, "phase_completed", phase="read_files", message="三份文件全部读取完毕")
                read_completed = True
                break
        else:
            # LLM 直接输出文字，追加到对话继续
            if msg.content:
                messages.append(_chat_message({"role": "assistant", "content": msg.content}))
            messages.append(_chat_message({"role": "user", "content": "请继续调用工具读取文件。"}))

    fallback_calls = []
    if not requirement:
        fallback_calls.append(("read_requirement", {}))
    if not schema:
        fallback_calls.append(("read_output_schema", {"doc_type": doc_type}))
    if not layout:
        fallback_calls.append(("read_output_layout", {}))

    for func_name, func_args in fallback_calls:
        logger.warning(f"  [读取阶段] LLM 未返回 {func_name}，使用工具兜底读取")
        _record_trace(
            run_id,
            "tool_call",
            phase="read_files",
            name=func_name,
            arguments=func_args,
            fallback=True,
        )
        result = execute_tool(func_name, func_args)
        _record_trace(
            run_id,
            "tool_result",
            phase="read_files",
            name=func_name,
            result=result,
            fallback=True,
        )
        if func_name == "read_requirement":
            requirement = result
        elif func_name == "read_output_schema":
            schema = result
        elif func_name == "read_output_layout":
            layout = result

    context_tool = _project_context_tool_for_doc_type(doc_type)
    if context_tool and not project_context_chunks:
        logger.warning(f"  [读取阶段] 未获得项目上下文，使用 {context_tool} 兜底读取")
        _record_trace(
            run_id,
            "tool_call",
            phase="read_files",
            name=context_tool,
            arguments={},
            fallback=True,
        )
        result = execute_tool(context_tool, {})
        _append_project_context(project_context_chunks, context_tool, result)
        _record_trace(
            run_id,
            "tool_result",
            phase="read_files",
            name=context_tool,
            result=result,
            fallback=True,
        )

    if not read_completed and requirement and schema and layout:
        _record_trace(run_id, "phase_completed", phase="read_files", message="读取阶段已完成")

    project_context = "\n\n".join(project_context_chunks)
    if len(project_context) > MAX_READ_CONTEXT_CHARS:
        project_context = project_context[:MAX_READ_CONTEXT_CHARS] + "\n...[项目上下文已截断]"

    return requirement, schema, layout, project_context


# ============================================================
# Phase 2-4: 逐节生成 + 拼接
# ============================================================
def _call_llm(
    system_prompt: str,
    user_prompt: str,
    tools: list[dict[str, Any]] | None = None,
    *,
    run_id: Optional[str] = None,
    phase: str = "llm",
) -> str:
    """同步调用 LLM，返回文本。如果有工具调用，执行并继续对话。"""
    msgs: list[ChatCompletionMessageParam] = [
        _chat_message({"role": "system", "content": system_prompt}),
        _chat_message({"role": "user", "content": user_prompt}),
    ]
    tool_params = _chat_tools(tools) if tools else None

    max_turns = 15  # 留够图表渲染（可能多次重试）+ 联网搜索 + 写正文的轮次
    for turn in range(max_turns):
        _check_interrupted(run_id, phase)
        # 注入用户追加的提示词
        hints = _consume_pending_hints(run_id)
        for hint in hints:
            msgs.append(_chat_message({"role": "user", "content": f"[用户补充指示] {hint}"}))
        _record_trace(run_id, "llm_request", phase=phase, turn=turn, has_tools=bool(tools))
        if tool_params:
            resp = client.chat.completions.create(
                model="deepseek-v4-pro",
                messages=msgs,
                tools=tool_params,
                temperature=0.4,
            )
        else:
            resp = client.chat.completions.create(
                model="deepseek-v4-pro",
                messages=msgs,
                temperature=0.4,
            )
        _check_interrupted(run_id, phase)
        msg = resp.choices[0].message
        if hasattr(msg, "reasoning_content") and msg.reasoning_content:
            _record_trace(run_id, "reasoning", phase=phase, turn=turn, content=msg.reasoning_content)
        if msg.content:
            _record_trace(run_id, "assistant_message", phase=phase, turn=turn, content=msg.content)

        tool_calls = _function_tool_calls(msg.tool_calls)
        if tool_calls:
            # 处理工具调用
            tc_list: list[dict[str, Any]] = []
            for tc in tool_calls:
                tc_list.append({
                    "id": tc.id,
                    "type": "function",
                    "function": {"name": tc.function.name, "arguments": tc.function.arguments},
                })
            assistant_msg: dict[str, Any] = {"role": "assistant", "content": msg.content or None, "tool_calls": tc_list}
            if hasattr(msg, "reasoning_content") and msg.reasoning_content:
                assistant_msg["reasoning_content"] = msg.reasoning_content
            msgs.append(_chat_message(assistant_msg))
            _record_trace(
                run_id,
                "tool_calls_planned",
                phase=phase,
                turn=turn,
                tools=[tc.function.name for tc in tool_calls],
            )

            for tc in tool_calls:
                _check_interrupted(run_id, phase)
                func_name = tc.function.name
                func_args = _safe_json_loads(tc.function.arguments)
                _record_trace(
                    run_id,
                    "tool_call",
                    phase=phase,
                    tool_call_id=tc.id,
                    name=func_name,
                    arguments=func_args,
                )
                result = execute_tool(func_name, func_args)
                _record_trace(
                    run_id,
                    "tool_result",
                    phase=phase,
                    tool_call_id=tc.id,
                    name=func_name,
                    result=result,
                )
                _check_interrupted(run_id, phase)
                msgs.append(_chat_message({
                    "role": "tool", "tool_call_id": tc.id, "content": result,
                }))
        else:
            # 直接返回内容
            content = msg.content or ""
            if content.strip():
                return content
            else:
                # 如果内容为空，继续对话
                msgs.append(_chat_message({"role": "assistant", "content": content}))
                msgs.append(_chat_message({"role": "user", "content": "请继续生成内容。"}))

    # 如果达到最大轮次，返回空
    return ""


def _get_top_sections(doc_type: str) -> list[dict]:
    """返回文档的一级章节列表（每个含其完整 children 树）。"""
    doc = get_doc_structure(doc_type)
    if doc is None:
        return []
    secs = doc["structure"]["sections"]
    result = []
    for i, sec in enumerate(secs):
        result.append({
            "index": i + 1,
            "title": sec.get("title", ""),
            "description": sec.get("description", ""),
            "required": sec.get("required", False),
            "children": sec.get("children", []),
            "schema": sec,  # 完整 schema
        })
    return result


def _section_context_excerpt(requirement: str, project_context: str) -> str:
    parts = [f"### 需求源文档摘要\n{requirement[:MAX_SECTION_REQUIREMENT_CHARS]}"]
    if project_context.strip():
        parts.append(
            "### 项目分析上下文\n"
            f"{project_context[:MAX_SECTION_PROJECT_CONTEXT_CHARS]}"
        )
    return "\n\n".join(parts)


def _generate_section_group(
    group: dict,
    requirement: str,
    project_context: str,
    layout: str,
    doc_type: str,
    user_hint: str,
    prev_title: str,
    next_title: str,
    run_id: Optional[str] = None,
) -> str:
    """为一个一级章节组（含所有子节）生成完整内容。"""
    context_label = "前后章节（保证连贯性）"
    context_text = f"上一章: {prev_title or '(无，这是第一章)'}\n下一章: {next_title or '(无，这是最后一章)'}"
    phase = f"generate_section:{group['title']}"
    group_schema = json.dumps(group.get("schema", group), ensure_ascii=False, indent=2)
    layout_excerpt = _layout_prompt_excerpt(layout)

    prompt = SECTION_SYSTEM_PROMPT.format(
        doc_type=doc_type,
        requirement_summary=_section_context_excerpt(requirement, project_context),
        section_path=group["title"],
        section_description=group.get("description", ""),
        section_schema=group_schema[:8000],
        layout_rules=layout_excerpt,
        context_label=context_label,
        context_text=context_text,
        user_hint=user_hint,
    )

    logger.info(f"  生成章节组: {group['title']}")
    _record_trace(run_id, "section_started", phase=phase, title=group["title"])
    # 章节生成阶段允许读取项目资料和渲染图表，但不让模型直接保存文档。
    write_tools = [t for t in get_tools_for_phase("write") if t["function"]["name"] != "save_document"]
    content = _call_llm(
        prompt,
        f"请撰写 {group['title']} 及其所有子章节的完整内容。",
        tools=write_tools,
        run_id=run_id,
        phase=phase,
    )
    _record_trace(run_id, "section_completed", phase=phase, title=group["title"], content=content)
    return content


def _flatten_required_sections(doc: dict) -> list[dict]:
    """展平文档结构，返回所有 required: true 的节，含 search_keyword。

    会自动跳过模板/示例类章节（标题含"模板""可重复""示例""依此类推"），
    因为 LLM 会将这些替换为实际内容（如 "FR-001 DRG入组核心功能"）。
    """
    _TEMPLATE_MARKERS = ("模板", "可重复", "示例", "依此类推")
    result = []

    def _walk(sections, path_prefix=""):
        for sec in sections:
            title = sec.get("title", "")
            if any(m in title for m in _TEMPLATE_MARKERS):
                continue  # 模板章节不参与校验
            result.append({
                "title": title,
                "required": sec.get("required", False),
                "search_keyword": title[:6] if len(title) > 4 else title,
                "diagram": sec.get("diagram", False),
                "diagram_types": sec.get("diagram_types", []),
            })
            for child in sec.get("children", []):
                _walk([child], f"{path_prefix}/{title}")

    _walk(doc.get("structure", {}).get("sections", []))
    return result


def _section_contains(sub_sec: dict, group: dict) -> bool:
    """判断 sub_sec 是否属于 group 章节。"""
    title = sub_sec.get("title", "")
    # 直接匹配 title 或检查 children
    for child in group.get("children", []):
        if child.get("title") == title:
            return True
        for grandchild in child.get("children", []):
            if grandchild.get("title") == title:
                return True
    return False


# ============================================================
# 主入口
# ============================================================
def run_agent(
    doc_type: str = "需求规格说明书",
    user_hint: str = "",
    source_file: Optional[str] = None,
    run_id: Optional[str] = None,
) -> Path:
    """完整的文档生成流程。

    Args:
        doc_type: "需求规格说明书" | "架构设计文档" | "测试文档"
        user_hint: 前端用户的提示词
        source_file: 前端上传的需求文件路径（txt/md），默认用 requirement.md
        run_id: 可选运行 ID，用于读取 trace 或请求中断
    """
    if run_id and get_generation_trace(run_id) is None:
        start_generation_trace(run_id, doc_type=doc_type, user_hint=user_hint)

    try:
        _check_interrupted(run_id, "run")
        if source_file:
            set_source_file(source_file)
            _record_trace(run_id, "source_file_set", phase="run", source_file=source_file)

        logger.info(f"文档类型: {doc_type}")
        logger.info(f"输出目录: {OUTPUT_DIR}")

        # ── Phase 1: 读取文件 ──
        logger.info("=" * 50)
        logger.info("Phase 1: 读取文件")
        _record_trace(run_id, "phase_started", phase="read_files", message="读取需求、结构和排版规范")
        requirement, _schema_text, layout, project_context = _phase_read_files(doc_type, run_id=run_id)

        # ── Phase 2: 拆解章节（按一级标题分组）──
        _check_interrupted(run_id, "split_sections")
        logger.info("=" * 50)
        logger.info("Phase 2: 拆解章节")
        _record_trace(run_id, "phase_started", phase="split_sections")
        top_sections = _get_top_sections(doc_type)
        logger.info(f"共 {len(top_sections)} 个章节组待生成")
        _record_trace(
            run_id,
            "phase_completed",
            phase="split_sections",
            section_count=len(top_sections),
            sections=[section["title"] for section in top_sections],
        )

        # ── Phase 3: 逐组生成 ──
        logger.info("=" * 50)
        logger.info("Phase 3: 逐组生成")
        _record_trace(run_id, "phase_started", phase="generate_sections", section_count=len(top_sections))
        generated: list[str] = []

        for i, group in enumerate(top_sections):
            _check_interrupted(run_id, "generate_sections")
            prev_title = top_sections[i - 1]["title"] if i > 0 else ""
            next_title = top_sections[i + 1]["title"] if i + 1 < len(top_sections) else ""

            content = _generate_section_group(
                group, requirement, project_context, layout, doc_type,
                user_hint, prev_title, next_title, run_id=run_id,
            )
            # 校验生成内容
            if not content or len(content.strip()) < 100:  # 简单校验：内容太短则重试一次
                logger.warning(f"  章节 {group['title']} 生成内容过短，重试...")
                _record_trace(run_id, "section_retry", phase="generate_sections", title=group["title"])
                content = _generate_section_group(
                    group, requirement, project_context, layout, doc_type,
                    user_hint, prev_title, next_title, run_id=run_id,
                )
            generated.append(content)
            logger.info(f"  完成 ({i + 1}/{len(top_sections)}): {group['title']}")
            _record_trace(
                run_id,
                "section_saved_in_memory",
                phase="generate_sections",
                title=group["title"],
                index=i + 1,
                total=len(top_sections),
            )
        _record_trace(run_id, "phase_completed", phase="generate_sections", section_count=len(generated))

        # ── Phase 3.5: Schema 合规校验 + 缺失章节重生成 ──
        _check_interrupted(run_id, "validate")
        logger.info("=" * 50)
        logger.info("Phase 3.5: Schema 合规校验")
        _record_trace(run_id, "phase_started", phase="validate")
        max_retries = 2
        for retry in range(max_retries + 1):
            issues_found = False
            doc = get_doc_structure(doc_type)
            if doc:
                flat = _flatten_required_sections(doc)
                for sec in flat:
                    keyword = sec.get("search_keyword", sec["title"])
                    found = any(keyword in content for content in generated)
                    if not found and sec.get("required"):
                        logger.warning(f"  缺失章节: {sec['title']}，重生成...")
                        _record_trace(run_id, "section_missing", phase="validate", title=sec["title"])
                        # 找到对应的一级章节组并重新生成
                        for j, group in enumerate(top_sections):
                            if _section_contains(sec, group):
                                prev_title = top_sections[j - 1]["title"] if j > 0 else ""
                                next_title = top_sections[j + 1]["title"] if j + 1 < len(top_sections) else ""
                                content = _generate_section_group(
                                    group, requirement, project_context, layout, doc_type,
                                    user_hint, prev_title, next_title, run_id=run_id,
                                )
                                if content and len(content.strip()) >= 100:
                                    generated[j] = content
                                issues_found = True
                                break

            _record_trace(run_id, "phase_completed", phase="validate", retry=retry, issues_found=issues_found)
            if not issues_found:
                logger.info("  Schema 校验通过")
                break

        # ── Phase 4: 拼接 + 校验 ──
        _check_interrupted(run_id, "stitch")
        logger.info("=" * 50)
        logger.info("Phase 4: 拼接 + 格式校验")
        _record_trace(run_id, "phase_started", phase="stitch")

        # 获取文档总标题
        doc = get_doc_structure(doc_type)
        doc_title = doc["structure"]["title"] if doc else doc_type

        # 拼接全文
        parts = [f"# {doc_title}\n"]
        for content in generated:
            parts.append(content)
            parts.append("")
        full_body = "\n".join(parts)
        _record_trace(run_id, "document_stitched", phase="stitch", content=full_body)

        # 全文拼接只做确定性规范化，避免最终 LLM 审校压缩正文或引入重复元数据。
        final_doc = normalize_document_header(full_body, doc_type)
        _record_trace(
            run_id,
            "phase_completed",
            phase="stitch",
            content=final_doc,
            deterministic=True,
        )

        # ── Phase 5: 保存 Markdown ──
        _check_interrupted(run_id, "save")
        logger.info("=" * 50)
        logger.info("Phase 5: 保存 Markdown")
        _record_trace(run_id, "phase_started", phase="save")
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        file_name = f"{doc_type}_{ts}.md"
        final_doc = normalize_heading_numbering(final_doc)
        final_doc = _fix_unordered_lists_in_md(final_doc)
        final_doc, table_issues = _validate_table_captions(final_doc)
        for issue in table_issues:
            logger.warning(f"  表格修复: {issue}")
            _record_trace(run_id, "table_repaired", phase="save", message=issue)
        md_output_path = Path(execute_tool("save_document", {"file_name": file_name, "content": final_doc, "doc_type": doc_type}))
        logger.info(f"Markdown 已保存至: {md_output_path}")
        _record_trace(run_id, "phase_completed", phase="save", markdown_path=str(md_output_path))

        # ── Phase 6: 转 PDF ──
        _check_interrupted(run_id, "convert_pdf")
        logger.info("=" * 50)
        logger.info("Phase 6: 转 PDF")
        _record_trace(run_id, "phase_started", phase="convert_pdf", markdown_path=str(md_output_path))
        pdf_output_path = Path(execute_tool("convert_to_pdf", {"md_path": str(md_output_path)}))
        logger.info(f"PDF 已保存至: {pdf_output_path}")
        _record_trace(
            run_id,
            "phase_completed",
            phase="convert_pdf",
            markdown_path=str(md_output_path),
            pdf_path=str(pdf_output_path),
        )
        _set_run_status(
            run_id,
            "completed",
            output_path=str(md_output_path),
            pdf_path=str(pdf_output_path),
            error=None,
        )

        return md_output_path
    except GenerationTerminated:
        logger.info(f"文档生成被终止: {run_id}")
        _set_run_status(run_id, "terminated")
        raise
    except GenerationInterrupted:
        logger.info(f"文档生成被中断: {run_id}")
        _set_run_status(run_id, "interrupted")
        raise
    except Exception as exc:
        _set_run_status(run_id, "failed", error=str(exc))
        _record_trace(run_id, "error", phase="run", error=str(exc))
        raise


# ============================================================
# 直接运行
# ============================================================
if __name__ == "__main__":
    DOC_TYPE = "需求规格说明书"
    HINT = "请根据项目实际情况，生成一份完整规范的需求规格说明书。内容要详实，符合大型软件项目标准。"

    logger.info(f"智能体启动，目标: {DOC_TYPE}")
    path = run_agent(doc_type=DOC_TYPE, user_hint=HINT)
    logger.info(f"完成！文件: {path}")
