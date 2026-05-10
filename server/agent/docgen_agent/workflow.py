"""docgen_agent 主循环 — 分批逐节生成 + 拼接 + 格式校验。

工作流程:
    Phase 1  读取文件     — Agent 调用 read_requirement / read_output_schema / read_output_layout
    Phase 2  拆解章节     — 按 output_schema 展开为 二级/三级 标题列表
    Phase 3  逐节生成     — 每个 (子)节独立调用 LLM，上下文含需求+规范+前后节摘要
    Phase 4  拼接校验     — 拼接全文 → 调用 LLM 做格式一致性校验
    Phase 5  保存         — save_document(.md)
"""

import json
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

from loguru import logger

from .tools import (
    TOOLS,
    client,
    OUTPUT_DIR,
    execute_tool,
    get_doc_structure,
    get_tools_for_phase,
    set_source_file,
)

CURRENT_DIR = Path(__file__).parent

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

## 排版布局规范
{layout_rules}

## {context_label}
{context_text}

## 用户额外指示
{user_hint}

## 写作要求
1. 内容详实、专业，符合大型软件项目需求文档的标准
2. 严格遵循上述 schema 结构，包含所有子章节，required:true 的必须生成
3. 覆盖每个子章节 tips 中提到的所有要素
4. 如需图表（diagram=true），使用 Mermaid 语法绘制
5. 图表标注格式: 图/表编号放在下方（全局编号），如 "图1：系统架构图"，"表1：需求跟踪矩阵"
6. 只输出本章节组（含子章节）的 Markdown 正文，不要输出文档总标题
7. 输出从该组的标题行开始（如 "## 一、引言"）
8. 利用你的领域知识丰富内容（IEEE 标准、DRG 政策、ICD 编码规范等）
9. 章节编号格式:
   - 一级标题: ## 一、标题名
   - 二级标题: ### 1.1 标题名
   - 三级标题: #### (1) 标题名
   - 四级标题: ##### a. 标题名
"""

STITCH_SYSTEM_PROMPT = """\
你是一个专业的软件工程文档审校专家。你的任务是将多个章节片段拼接成一份完整规范的文档。

## 要求
1. 检查各级标题编号是否正确、连续
2. 检查图表编号是否全局统一、无重复
3. 检查格式是否符合排版规范（标题层级、caption 格式）
4. 修正可能的编号错误、格式不一致问题
5. 在文档开头添加文档元数据（项目名称、版本号、日期、状态）
6. 在文档末尾添加生成声明
7. 输出完整的、可直接保存的 Markdown 文档

## 排版规范
{layout_rules}

## 文档结构
{doc_structure_summary}
"""


# ============================================================
# 流式响应处理（Phase 1 用）
# ============================================================
class _FakeMessage:
    def __init__(self, content="", tool_calls=None):
        self.content = content
        self.tool_calls = tool_calls or []


class _FakeToolCall:
    def __init__(self, tc_id, name, arguments):
        self.id = tc_id
        self.function = _FakeFunction(name, arguments)


class _FakeFunction:
    def __init__(self, name, arguments):
        self.name = name
        self.arguments = arguments


def _handle_streaming_response(stream) -> _FakeMessage:
    collected_content = ""
    collected_tool_calls: dict[int, dict] = {}

    print("\n" + "─" * 60)
    print("[文档撰写中，实时预览]")
    print("─" * 60)

    for chunk in stream:
        delta = chunk.choices[0].delta if chunk.choices else None
        if delta is None:
            continue
        if delta.content:
            collected_content += delta.content
            print(delta.content, end="", flush=True)
        if delta.tool_calls:
            for tc_delta in delta.tool_calls:
                idx = tc_delta.index
                if idx not in collected_tool_calls:
                    collected_tool_calls[idx] = {
                        "id": tc_delta.id or "",
                        "function": {"name": "", "arguments": ""},
                    }
                if tc_delta.id:
                    collected_tool_calls[idx]["id"] = tc_delta.id
                if tc_delta.function:
                    if tc_delta.function.name:
                        collected_tool_calls[idx]["function"]["name"] += tc_delta.function.name
                    if tc_delta.function.arguments:
                        collected_tool_calls[idx]["function"]["arguments"] += tc_delta.function.arguments

    print("\n" + "─" * 60)

    tool_calls_list = []
    for idx in sorted(collected_tool_calls.keys()):
        tc = collected_tool_calls[idx]
        tool_calls_list.append(_FakeToolCall(tc["id"], tc["function"]["name"], tc["function"]["arguments"]))

    return _FakeMessage(collected_content, tool_calls_list if tool_calls_list else None)


# ============================================================
# Phase 1: 读取文件
# ============================================================
def _phase_read_files(doc_type: str) -> tuple[str, str, str]:
    """Agent 方式读取 requirement, schema, layout；返回三份文本。"""
    messages = [
        {"role": "system", "content": READ_PHASE_PROMPT.format(doc_type=doc_type)},
        {"role": "user", "content": f"请读取生成 {doc_type} 所需的所有文件。"},
    ]

    requirement = ""
    schema = ""
    layout = ""

    for turn in range(6):
        logger.info(f"  [读取阶段 Turn {turn}] 等待 LLM...")
        resp = client.chat.completions.create(
            model="deepseek-v4-pro",
            messages=messages,
            tools=get_tools_for_phase("read"),
            temperature=0.0,
        )
        msg = resp.choices[0].message

        if msg.tool_calls:
            names = [tc.function.name for tc in msg.tool_calls]
            logger.info(f"  [读取阶段] 调用: {names}")

            tc_list = []
            for tc in msg.tool_calls:
                tc_list.append({
                    "id": tc.id,
                    "type": "function",
                    "function": {"name": tc.function.name, "arguments": tc.function.arguments},
                })
            assistant_msg = {"role": "assistant", "content": msg.content or None, "tool_calls": tc_list}
            if hasattr(msg, "reasoning_content") and msg.reasoning_content:
                assistant_msg["reasoning_content"] = msg.reasoning_content
            messages.append(assistant_msg)

            for tc in msg.tool_calls:
                func_name = tc.function.name
                func_args = json.loads(tc.function.arguments)
                result = execute_tool(func_name, func_args)
                messages.append({
                    "role": "tool", "tool_call_id": tc.id, "content": result,
                })
                if func_name == "read_requirement":
                    requirement = result
                elif func_name == "read_output_schema":
                    schema = result
                elif func_name == "read_output_layout":
                    layout = result

            if requirement and schema and layout:
                logger.info("  [读取阶段] 三份文件全部读取完毕")
                break
        else:
            # LLM 直接输出文字，追加到对话继续
            if msg.content:
                messages.append({"role": "assistant", "content": msg.content})
            messages.append({"role": "user", "content": "请继续调用工具读取文件。"})

    return requirement, schema, layout


# ============================================================
# Phase 2-4: 逐节生成 + 拼接
# ============================================================
def _call_llm(system_prompt: str, user_prompt: str, tools: list | None = None) -> str:
    """同步调用 LLM，返回文本。如果有工具调用，执行并继续对话。"""
    msgs = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]
    kwargs = dict(model="deepseek-v4-pro", messages=msgs, temperature=0.4)
    if tools:
        kwargs["tools"] = tools

    max_turns = 5  # 防止无限循环
    for turn in range(max_turns):
        resp = client.chat.completions.create(**kwargs)
        msg = resp.choices[0].message

        if msg.tool_calls:
            # 处理工具调用
            tc_list = []
            for tc in msg.tool_calls:
                tc_list.append({
                    "id": tc.id,
                    "type": "function",
                    "function": {"name": tc.function.name, "arguments": tc.function.arguments},
                })
            assistant_msg = {"role": "assistant", "content": msg.content or None, "tool_calls": tc_list}
            if hasattr(msg, "reasoning_content") and msg.reasoning_content:
                assistant_msg["reasoning_content"] = msg.reasoning_content
            msgs.append(assistant_msg)

            for tc in msg.tool_calls:
                func_name = tc.function.name
                func_args = json.loads(tc.function.arguments)
                result = execute_tool(func_name, func_args)
                msgs.append({
                    "role": "tool", "tool_call_id": tc.id, "content": result,
                })

            # 继续对话
            kwargs["messages"] = msgs
        else:
            # 直接返回内容
            content = msg.content or ""
            if content.strip():
                return content
            else:
                # 如果内容为空，继续对话
                msgs.append({"role": "assistant", "content": content})
                msgs.append({"role": "user", "content": "请继续生成内容。"})
                kwargs["messages"] = msgs

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


def _generate_section_group(
    group: dict,
    requirement: str,
    schema_text: str,
    layout: str,
    doc_type: str,
    user_hint: str,
    prev_title: str,
    next_title: str,
) -> str:
    """为一个一级章节组（含所有子节）生成完整内容。"""
    context_label = "前后章节（保证连贯性）"
    context_text = f"上一章: {prev_title or '(无，这是第一章)'}\n下一章: {next_title or '(无，这是最后一章)'}"

    prompt = SECTION_SYSTEM_PROMPT.format(
        doc_type=doc_type,
        requirement_summary=requirement[:3000],
        section_path=group["title"],
        section_description=group.get("description", ""),
        section_schema=schema_text[:2000],  # 使用传入的 schema_text
        layout_rules=layout[:2000],
        context_label=context_label,
        context_text=context_text,
        user_hint=user_hint,
    )

    logger.info(f"  生成章节组: {group['title']}")
    # 只传入 search_web 工具，避免 save_document
    write_tools = [t for t in get_tools_for_phase("write") if t["function"]["name"] == "search_web"]
    content = _call_llm(prompt, f"请撰写 {group['title']} 及其所有子章节的完整内容。", tools=write_tools)
    return content


def _summarize_section(content: str, max_chars: int = 300) -> str:
    """对已生成章节做极简摘要，供后续章节参考。"""
    lines = content.strip().split("\n")
    summary_lines = []
    chars = 0
    for line in lines:
        if line.startswith("#"):
            summary_lines.append(line)
            chars += len(line)
        elif chars < max_chars:
            summary_lines.append(line[:200])
            chars += len(line)
        else:
            break
    return "\n".join(summary_lines)


# ============================================================
# 主入口
# ============================================================
def run_agent(
    doc_type: str = "需求规格说明书",
    user_hint: str = "",
    source_file: Optional[str] = None,
) -> Path:
    """完整的文档生成流程。

    Args:
        doc_type: "需求规格说明书" | "架构设计文档" | "测试文档"
        user_hint: 前端用户的提示词
        source_file: 前端上传的需求文件路径（txt/md），默认用 requirement.md
    """
    if source_file:
        set_source_file(source_file)

    logger.info(f"文档类型: {doc_type}")
    logger.info(f"输出目录: {OUTPUT_DIR}")

    # ── Phase 1: 读取文件 ──
    logger.info("=" * 50)
    logger.info("Phase 1: 读取文件")
    requirement, schema_text, layout = _phase_read_files(doc_type)

    # ── Phase 2: 拆解章节（按一级标题分组）──
    logger.info("=" * 50)
    logger.info("Phase 2: 拆解章节")
    top_sections = _get_top_sections(doc_type)
    logger.info(f"共 {len(top_sections)} 个章节组待生成")

    # ── Phase 3: 逐组生成 ──
    logger.info("=" * 50)
    logger.info("Phase 3: 逐组生成")
    generated: list[str] = []

    for i, group in enumerate(top_sections):
        prev_title = top_sections[i - 1]["title"] if i > 0 else ""
        next_title = top_sections[i + 1]["title"] if i + 1 < len(top_sections) else ""

        content = _generate_section_group(
            group, requirement, schema_text, layout, doc_type,
            user_hint, prev_title, next_title,
        )
        # 校验生成内容
        if not content or len(content.strip()) < 100:  # 简单校验：内容太短则重试一次
            logger.warning(f"  章节 {group['title']} 生成内容过短，重试...")
            content = _generate_section_group(
                group, requirement, schema_text, layout, doc_type,
                user_hint, prev_title, next_title,
            )
        generated.append(content)
        logger.info(f"  完成 ({i + 1}/{len(top_sections)}): {group['title']}")

    # ── Phase 4: 拼接 + 校验 ──
    logger.info("=" * 50)
    logger.info("Phase 4: 拼接 + 格式校验")

    # 获取文档总标题
    doc = get_doc_structure(doc_type)
    doc_title = doc["structure"]["title"] if doc else doc_type

    # 拼接全文
    parts = [f"# {doc_title}\n"]
    for content in generated:
        parts.append(content)
        parts.append("")
    full_body = "\n".join(parts)

    # LLM 格式校验
    stitch_prompt = STITCH_SYSTEM_PROMPT.format(
        layout_rules=layout[:2000],
        doc_structure_summary=json.dumps(
            get_doc_structure(doc_type), ensure_ascii=False, indent=2
        )[:3000],
    )
    logger.info("  向 LLM 提交全文校验...")
    final_doc = _call_llm(
        stitch_prompt,
        f"请审校并修正以下文档的格式问题，确保编号连续、格式规范:\n\n{full_body}",
    )

    # ── Phase 5: 保存 ──
    logger.info("=" * 50)
    logger.info("Phase 5: 保存")
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    file_name = f"{doc_type}_{ts}.md"
    output_path = OUTPUT_DIR / file_name
    output_path.write_text(final_doc, encoding="utf-8")
    logger.info(f"文档已保存至: {output_path}")

    return output_path


# ============================================================
# 直接运行
# ============================================================
if __name__ == "__main__":
    DOC_TYPE = "需求规格说明书"
    HINT = "请根据项目实际情况，生成一份完整规范的需求规格说明书。内容要详实，符合大型软件项目标准。"

    logger.info(f"智能体启动，目标: {DOC_TYPE}")
    path = run_agent(doc_type=DOC_TYPE, user_hint=HINT)
    logger.info(f"完成！文件: {path}")
