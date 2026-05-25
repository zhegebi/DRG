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
    normalize_inline_section_titles,
    normalize_caption_positions_and_numbering,
    _validate_table_captions,
    client,
    OUTPUT_DIR,
    OUTPUT_SCHEMA_PATH,
    execute_tool,
    get_doc_structure,
    get_tools_for_phase,
    set_source_files,
)

MAX_TRACE_EVENTS = 1000
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
_TERMINATE_FLAGS: set[str] = set()
_ACTIVE_STREAMS: dict[str, list[Any]] = {}


class GenerationTerminated(RuntimeError):
    """文档生成被用户终止。"""


def _now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _trim_trace_value(value: Any) -> Any:
    if isinstance(value, dict):
        return {k: _trim_trace_value(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_trim_trace_value(v) for v in value]
    return value


def _ensure_run_state_locked(run_id: str) -> dict[str, Any]:
    state = _RUN_TRACES.get(run_id)
    if state is None:
        state = {
            "run_id": run_id,
            "status": "running",
            "doc_type": "",
            "task_title": "文档生成任务",
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
    task_title: str = "",
    *,
    reset: bool = False,
) -> dict[str, Any]:
    """初始化或复用一次文档生成运行的 trace 状态。"""
    with _TRACE_LOCK:
        if reset or run_id not in _RUN_TRACES:
            if reset:
                _TERMINATE_FLAGS.discard(run_id)
            _RUN_TRACES[run_id] = {
                "run_id": run_id,
                "status": "running",
                "doc_type": doc_type,
                "task_title": task_title or doc_type or "文档生成任务",
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
            if task_title:
                state["task_title"] = task_title
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
            "task_title": state.get("task_title") or state.get("doc_type", ""),
            "created_at": state.get("created_at"),
            "updated_at": state.get("updated_at"),
            "output_path": state.get("output_path"),
            "pdf_path": state.get("pdf_path"),
            "error": state.get("error"),
            "terminated": run_id in _TERMINATE_FLAGS or state["status"] in {"terminate_requested", "terminated"},
            "events": [event.copy() for event in state.get("events", [])],
        }


def request_generation_terminate(run_id: str) -> bool:
    """请求终止指定运行，并尽快关闭正在进行的模型流。"""
    with _TRACE_LOCK:
        state = _RUN_TRACES.get(run_id)
        if state is None:
            return False
        _TERMINATE_FLAGS.add(run_id)
        state["status"] = "terminate_requested"
        state["updated_at"] = _now_iso()

    _record_trace(run_id, "terminate_requested", phase="run")
    _close_active_streams(run_id)
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


def _record_trace_delta(
    run_id: Optional[str],
    event_type: str,
    phase: str,
    content_delta: str,
    **payload: Any,
) -> None:
    """把流式 token 追加到同一条 trace 事件，前端 SSE 可即时刷新同一卡片。"""
    if not run_id or not content_delta:
        return
    with _TRACE_LOCK:
        state = _ensure_run_state_locked(run_id)
        events = state["events"]
        turn = payload.get("turn")
        last = events[-1] if events else None
        if (
            last
            and last.get("type") == event_type
            and last.get("phase") == phase
            and last.get("turn") == turn
            and last.get("streaming") is True
        ):
            content = str(last.get("content", "")) + content_delta
            last["content"] = _trim_trace_value(content)
            last["time"] = _now_iso()
            for key, value in payload.items():
                last[key] = _trim_trace_value(value)
        else:
            event_id = state.setdefault("next_event_id", len(events) + 1)
            state["next_event_id"] = event_id + 1
            events.append({
                "id": event_id,
                "time": _now_iso(),
                "type": event_type,
                "phase": phase,
                "content": _trim_trace_value(content_delta),
                "streaming": True,
                **{key: _trim_trace_value(value) for key, value in payload.items()},
            })
            if len(events) > MAX_TRACE_EVENTS:
                del events[: len(events) - MAX_TRACE_EVENTS]
        state["updated_at"] = _now_iso()


def _register_active_stream(run_id: Optional[str], stream: Any) -> None:
    if not run_id:
        return
    with _TRACE_LOCK:
        _ACTIVE_STREAMS.setdefault(run_id, []).append(stream)


def _unregister_active_stream(run_id: Optional[str], stream: Any) -> None:
    if not run_id:
        return
    with _TRACE_LOCK:
        streams = _ACTIVE_STREAMS.get(run_id)
        if not streams:
            return
        try:
            streams.remove(stream)
        except ValueError:
            pass
        if not streams:
            _ACTIVE_STREAMS.pop(run_id, None)


def _close_active_streams(run_id: str) -> None:
    with _TRACE_LOCK:
        streams = list(_ACTIVE_STREAMS.get(run_id, []))

    for stream in streams:
        close = getattr(stream, "close", None)
        if not callable(close):
            continue
        try:
            close()
        except Exception as exc:
            logger.debug(f"关闭模型流失败: {run_id}: {exc}")


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


def _stream_chat_completion(
    messages: list[ChatCompletionMessageParam],
    *,
    tools: list[dict[str, Any]] | None,
    temperature: float,
    run_id: Optional[str],
    phase: str,
    turn: int,
) -> tuple[str, list[dict[str, Any]], str]:
    """流式调用模型，实时写入 reasoning/content trace，并组装工具调用。"""
    _check_terminated(run_id, phase)
    kwargs: dict[str, Any] = {
        "model": "deepseek-v4-pro",
        "messages": messages,
        "temperature": temperature,
        "stream": True,
        "extra_body": {"thinking": {"type": "enabled"}},
    }
    if tools:
        kwargs["tools"] = _chat_tools(tools)

    try:
        stream = client.chat.completions.create(**kwargs)
    except Exception as exc:
        _check_terminated(run_id, phase)
        if run_id:
            _record_trace(run_id, "error", phase=phase, error=f"流式模型调用失败: {exc}")
            raise RuntimeError(f"流式模型调用失败: {exc}") from exc
        logger.warning(f"流式调用失败，退回普通调用: {exc}")
        fallback_kwargs: dict[str, Any] = {
            "model": "deepseek-v4-pro",
            "messages": messages,
            "temperature": temperature,
        }
        if tools:
            fallback_kwargs["tools"] = _chat_tools(tools)
        _check_terminated(run_id, phase)
        resp = client.chat.completions.create(**fallback_kwargs)
        _check_terminated(run_id, phase)
        msg = resp.choices[0].message
        reasoning = getattr(msg, "reasoning_content", "") or ""
        if reasoning:
            _record_trace(run_id, "reasoning", phase=phase, turn=turn, content=reasoning)
        if msg.content:
            _record_trace(run_id, "assistant_message", phase=phase, turn=turn, content=msg.content)
        tool_calls = [
            {
                "id": tc.id,
                "type": "function",
                "function": {"name": tc.function.name, "arguments": tc.function.arguments},
            }
            for tc in _function_tool_calls(msg.tool_calls)
        ]
        return msg.content or "", tool_calls, reasoning

    content_parts: list[str] = []
    reasoning_parts: list[str] = []
    tool_call_parts: dict[int, dict[str, Any]] = {}

    _register_active_stream(run_id, stream)
    try:
        for chunk in stream:
            _check_terminated(run_id, phase)
            if not chunk.choices:
                continue
            delta = chunk.choices[0].delta
            reasoning_delta = getattr(delta, "reasoning_content", None)
            if reasoning_delta:
                reasoning_parts.append(reasoning_delta)
                _record_trace_delta(
                    run_id,
                    "reasoning",
                    phase,
                    reasoning_delta,
                    turn=turn,
                )

            content_delta = getattr(delta, "content", None)
            if content_delta:
                content_parts.append(content_delta)
                _record_trace_delta(
                    run_id,
                    "assistant_message",
                    phase,
                    content_delta,
                    turn=turn,
                )

            for tool_delta in getattr(delta, "tool_calls", None) or []:
                index = int(getattr(tool_delta, "index", len(tool_call_parts)) or 0)
                entry = tool_call_parts.setdefault(
                    index,
                    {"id": "", "type": "function", "function": {"name": "", "arguments": ""}},
                )
                if getattr(tool_delta, "id", None):
                    entry["id"] = tool_delta.id
                if getattr(tool_delta, "type", None):
                    entry["type"] = tool_delta.type
                function_delta = getattr(tool_delta, "function", None)
                if function_delta:
                    if getattr(function_delta, "name", None):
                        entry["function"]["name"] += function_delta.name
                    if getattr(function_delta, "arguments", None):
                        entry["function"]["arguments"] += function_delta.arguments
    except Exception:
        _check_terminated(run_id, phase)
        raise
    finally:
        _unregister_active_stream(run_id, stream)
        close = getattr(stream, "close", None)
        if callable(close):
            try:
                close()
            except Exception:
                pass

    tool_calls = [
        call for _, call in sorted(tool_call_parts.items())
        if call.get("function", {}).get("name")
    ]
    return "".join(content_parts), tool_calls, "".join(reasoning_parts)


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


def _check_terminated(run_id: Optional[str], phase: str = "") -> None:
    if not run_id:
        return
    with _TRACE_LOCK:
        should_terminate = run_id in _TERMINATE_FLAGS
    if should_terminate:
        _set_run_status(run_id, "terminated")
        _record_trace(run_id, "terminated", phase=phase)
        raise GenerationTerminated(f"文档生成已终止: {run_id}")


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

## output_schema.json 章节定义与内容格式规则
```json
{section_schema}
```

## output_layout.json 规范摘录
{layout_rules}

## {context_label}
{context_text}

## 用户额外指示（最高优先级）
{user_hint}

## 写作任务
1. 只输出本章节组（含子章节）的 Markdown 正文，不要输出文档总标题和封面小组信息；总标题和封面小组信息由拼接阶段统一添加。
2. 输出必须从该章节组的标题行开始，并遵循上方 schema；required:true 的章节必须生成，tips 中的内容要完整覆盖。
3. 如 schema 要求图表，按该章节 tools 字段选择并调用工具；图片路径直接使用工具返回值。
4. 内容格式按 schema 的 content_format_rules 执行，视觉布局按 output_layout.json 摘录执行。
5. 内容必须详实、专业，并结合项目真实需求或代码信息展开；缺失项按文档类型标注“待确认”或“待补充”，不要编造。
6. 严禁输出任何客套话或 AI 声明，直接输出文档正文。
"""

STITCH_SYSTEM_PROMPT = """\
你是一个专业的软件工程文档审校专家。你的任务是将多个章节片段拼接成一份完整规范的文档。

## 审校任务
1. 拼接章节片段，保留完整 Markdown 文档。
2. 按 output_schema.json 处理内容结构，按 output_layout.json 处理布局规范。
3. 删除重复封面信息、孤立格式标记、客套话和 AI 声明。
4. 修复明显损坏的 Markdown 表格和图片路径。
5. 输出完整 Markdown 文档，严禁客套话或 AI 声明。

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
        "body_text",
        "figures",
        "tables",
        "lists",
        "rendering_conventions",
    )
    excerpt = {key: layout_obj.get(key) for key in keys if key in layout_obj}
    return json.dumps(excerpt, ensure_ascii=False, indent=2)


def _schema_content_format_rules() -> dict[str, Any]:
    try:
        schema_obj = json.loads(OUTPUT_SCHEMA_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    rules = schema_obj.get("content_format_rules", {})
    return rules if isinstance(rules, dict) else {}


# ============================================================
# Phase 1: 读取文件
# ============================================================
def _phase_read_files(
    doc_type: str,
    user_hint: str = "",
    run_id: Optional[str] = None,
) -> tuple[str, str, str, str]:
    """Agent 方式读取 requirement, schema, layout 和项目上下文。"""
    read_user_prompt = f"请读取生成 {doc_type} 所需的所有文件。"
    if user_hint.strip():
        read_user_prompt += f"\n\n[最高优先级用户提示]\n{user_hint.strip()[:2000]}"
    messages: list[ChatCompletionMessageParam] = [
        _chat_message({"role": "system", "content": READ_PHASE_PROMPT.format(doc_type=doc_type)}),
        _chat_message({"role": "user", "content": read_user_prompt}),
    ]

    requirement = ""
    schema = ""
    layout = ""
    project_context_chunks: list[str] = []
    read_completed = False

    for turn in range(6):
        _check_terminated(run_id, "read_files")
        logger.info(f"  [读取阶段 Turn {turn}] 等待 LLM...")
        _record_trace(run_id, "llm_request", phase="read_files", turn=turn, action="读取需求、结构和排版规范")
        msg_content, tool_calls, reasoning_content = _stream_chat_completion(
            messages,
            tools=get_tools_for_phase("read"),
            temperature=0.0,
            run_id=run_id,
            phase="read_files",
            turn=turn,
        )
        _check_terminated(run_id, "read_files")

        if tool_calls:
            for idx, tc in enumerate(tool_calls):
                if not tc.get("id"):
                    tc["id"] = f"tool_{turn}_{idx}_{tc['function']['name']}"
            names = [tc["function"]["name"] for tc in tool_calls]
            logger.info(f"  [读取阶段] 调用: {names}")
            _record_trace(run_id, "tool_calls_planned", phase="read_files", turn=turn, tools=names)

            assistant_msg: dict[str, Any] = {"role": "assistant", "content": msg_content or None, "tool_calls": tool_calls}
            if reasoning_content:
                assistant_msg["reasoning_content"] = reasoning_content
            messages.append(_chat_message(assistant_msg))

            for tc in tool_calls:
                _check_terminated(run_id, "read_files")
                func_name = tc["function"]["name"]
                tool_call_id = tc["id"]
                func_args = _safe_json_loads(tc["function"].get("arguments", ""))
                _record_trace(
                    run_id,
                    "tool_call",
                    phase="read_files",
                    tool_call_id=tool_call_id,
                    name=func_name,
                    arguments=func_args,
                )
                result = execute_tool(func_name, func_args)
                _record_trace(
                    run_id,
                    "tool_result",
                    phase="read_files",
                    tool_call_id=tool_call_id,
                    name=func_name,
                    result=result,
                )
                _check_terminated(run_id, "read_files")
                messages.append(_chat_message({
                    "role": "tool", "tool_call_id": tool_call_id, "content": result,
                }))
                if func_name == "read_requirement":
                    requirement = result
                elif func_name == "read_output_schema":
                    if result.lstrip().startswith('{"error"'):
                        messages.append(_chat_message({
                            "role": "user",
                            "content": f"请重新调用 read_output_schema，并传入 doc_type=\"{doc_type}\"。",
                        }))
                    else:
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
            if msg_content:
                messages.append(_chat_message({"role": "assistant", "content": msg_content}))
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

    max_turns = 15  # 留够图表渲染（可能多次重试）+ 联网搜索 + 写正文的轮次
    for turn in range(max_turns):
        _check_terminated(run_id, phase)
        _record_trace(run_id, "llm_request", phase=phase, turn=turn, has_tools=bool(tools))
        msg_content, tool_calls, reasoning_content = _stream_chat_completion(
            msgs,
            tools=tools,
            temperature=0.4,
            run_id=run_id,
            phase=phase,
            turn=turn,
        )
        _check_terminated(run_id, phase)

        if tool_calls:
            # 处理工具调用
            for idx, tc in enumerate(tool_calls):
                if not tc.get("id"):
                    tc["id"] = f"tool_{turn}_{idx}_{tc['function']['name']}"
            assistant_msg: dict[str, Any] = {"role": "assistant", "content": msg_content or None, "tool_calls": tool_calls}
            if reasoning_content:
                assistant_msg["reasoning_content"] = reasoning_content
            msgs.append(_chat_message(assistant_msg))
            _record_trace(
                run_id,
                "tool_calls_planned",
                phase=phase,
                turn=turn,
                tools=[tc["function"]["name"] for tc in tool_calls],
            )

            for tc in tool_calls:
                _check_terminated(run_id, phase)
                func_name = tc["function"]["name"]
                tool_call_id = tc["id"]
                func_args = _safe_json_loads(tc["function"].get("arguments", ""))
                _record_trace(
                    run_id,
                    "tool_call",
                    phase=phase,
                    tool_call_id=tool_call_id,
                    name=func_name,
                    arguments=func_args,
                )
                result = execute_tool(func_name, func_args)
                _record_trace(
                    run_id,
                    "tool_result",
                    phase=phase,
                    tool_call_id=tool_call_id,
                    name=func_name,
                    result=result,
                )
                _check_terminated(run_id, phase)
                msgs.append(_chat_message({
                    "role": "tool", "tool_call_id": tool_call_id, "content": result,
                }))
        else:
            # 直接返回内容
            content = msg_content or ""
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
    schema_payload = {
        "content_format_rules": _schema_content_format_rules(),
        "section": group.get("schema", group),
    }
    group_schema = json.dumps(schema_payload, ensure_ascii=False, indent=2)
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
    source_files: Optional[list[str]] = None,
    run_id: Optional[str] = None,
) -> Path:
    """完整的文档生成流程。

    Args:
        doc_type: "需求规格说明书" | "架构设计文档" | "测试文档"
        user_hint: 前端用户的提示词
        source_file: 前端上传的单个需求文件路径（兼容旧接口）
        source_files: 前端上传的需求/依赖文件路径列表，默认用 agent_input/requirement.md
        run_id: 可选任务 ID，用于读取 trace 或请求终止
    """
    if run_id and get_generation_trace(run_id) is None:
        start_generation_trace(run_id, doc_type=doc_type, user_hint=user_hint)

    try:
        _check_terminated(run_id, "run")
        resolved_source_files = list(source_files or ([] if source_file is None else [source_file]))
        set_source_files(resolved_source_files)
        _record_trace(
            run_id,
            "source_files_set",
            phase="run",
            source_files=resolved_source_files or ["agent_input/requirement.md"],
        )

        logger.info(f"文档类型: {doc_type}")
        logger.info(f"输出目录: {OUTPUT_DIR}")

        # ── Phase 1: 读取文件 ──
        logger.info("=" * 50)
        logger.info("Phase 1: 读取文件")
        _record_trace(run_id, "phase_started", phase="read_files", message="读取需求、结构和排版规范")
        requirement, _schema_text, layout, project_context = _phase_read_files(
            doc_type,
            user_hint=user_hint,
            run_id=run_id,
        )

        # ── Phase 2: 拆解章节（按一级标题分组）──
        _check_terminated(run_id, "split_sections")
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
            _check_terminated(run_id, "generate_sections")
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
        _check_terminated(run_id, "validate")
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
        _check_terminated(run_id, "stitch")
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

        # 全文拼接只做确定性规范化，避免最终 LLM 审校压缩正文或引入重复封面信息。
        final_doc = normalize_document_header(full_body, doc_type, user_hint)
        _record_trace(
            run_id,
            "phase_completed",
            phase="stitch",
            content=final_doc,
            deterministic=True,
        )

        # ── Phase 5: 保存 Markdown ──
        _check_terminated(run_id, "save")
        logger.info("=" * 50)
        logger.info("Phase 5: 保存 Markdown")
        _record_trace(run_id, "phase_started", phase="save")
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        file_name = f"{doc_type}_{ts}.md"
        final_doc = normalize_heading_numbering(final_doc)
        final_doc = _fix_unordered_lists_in_md(final_doc)
        final_doc = normalize_inline_section_titles(final_doc)
        final_doc, caption_issues = normalize_caption_positions_and_numbering(final_doc)
        final_doc, table_issues = _validate_table_captions(final_doc)
        final_doc, caption_issues_after_table_repair = normalize_caption_positions_and_numbering(final_doc)
        for issue in [*caption_issues, *table_issues, *caption_issues_after_table_repair]:
            logger.warning(f"  格式修复: {issue}")
            _record_trace(run_id, "format_repaired", phase="save", message=issue)
        md_output_path = Path(execute_tool(
            "save_document",
            {
                "file_name": file_name,
                "content": final_doc,
                "doc_type": doc_type,
                "metadata_source": user_hint,
            },
        ))
        logger.info(f"Markdown 已保存至: {md_output_path}")
        _record_trace(run_id, "phase_completed", phase="save", markdown_path=str(md_output_path))

        # ── Phase 6: 转 PDF ──
        _check_terminated(run_id, "convert_pdf")
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

