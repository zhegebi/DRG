"""docgen_agent 工具定义与实现。

工具列表:
    read_requirement  — 读取需求源文件（默认 requirement.md，可由前端覆盖）
    read_output_schema — 读取 output_schema.json（按 doc_type 裁剪）
    read_output_layout — 读取 output_layout.json
    save_document      — 保存生成的 Markdown 文档
    search_web         — 联网搜索（补充领域知识）
    convert_to_pdf     — [预留] MD → PDF
    convert_to_docx    — [预留] MD → DOCX
    convert_to_txt     — [预留] MD → 纯文本
"""

import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

from loguru import logger
from openai import OpenAI

try:
    from ...config import API_KEY
except ImportError:
    _SERVER_DIR = Path(__file__).parent.parent.parent
    sys.path.insert(0, str(_SERVER_DIR))
    from config import API_KEY

CURRENT_DIR = Path(__file__).parent
OUTPUT_DIR = CURRENT_DIR / "output_docs"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

client = OpenAI(api_key=API_KEY, base_url="https://api.deepseek.com")

# ============================================================
# 预加载 — 静态资源
# ============================================================
with open(CURRENT_DIR / "output_schema.json", "r", encoding="utf-8") as f:
    _OUTPUT_SCHEMA = json.load(f)

_OUTPUT_LAYOUT = (CURRENT_DIR / "output_layout.json").read_text(encoding="utf-8")

# 需求源文件路径 — 可在运行时由前端覆盖
_source_md_path: Path = CURRENT_DIR / "requirement.md"
_source_md_content: str = _source_md_path.read_text(encoding="utf-8")


def set_source_file(path: str | Path) -> None:
    """设置需求源文件（前端上传的 txt/md）。"""
    global _source_md_path, _source_md_content
    _source_md_path = Path(path)
    _source_md_content = _source_md_path.read_text(encoding="utf-8")
    logger.info(f"需求源文件已切换为: {_source_md_path}")


# ============================================================
# 工具定义
# ============================================================
TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "read_requirement",
            "description": "读取项目需求源文件，了解系统功能目标、具体需求和规则。",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "read_output_schema",
            "description": "读取文档结构规范。传入 doc_type 只取目标文档类型的章节树。"
            "用于了解目标文档有哪些章节、每个章节的 required/tips/diagram 信息。",
            "parameters": {
                "type": "object",
                "properties": {
                    "doc_type": {
                        "type": "string",
                        "enum": ["需求规格说明书", "架构设计文档", "测试文档"],
                        "description": "目标文档类型，不传则返回全部。",
                    }
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "read_output_layout",
            "description": "读取排版布局规范（字体、标题层级、页边距、图表 caption 格式等）。",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "save_document",
            "description": "将 Markdown 文档正文保存到 output_docs/ 目录，返回 .md 文件路径。",
            "parameters": {
                "type": "object",
                "properties": {
                    "file_name": {"type": "string", "description": "文件名（不含路径），如 '需求规格说明书.md'"},
                    "content": {"type": "string", "description": "完整的 Markdown 文档正文"},
                },
                "required": ["file_name", "content"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_web",
            "description": "联网搜索相关资料，用于补充文档中的领域知识（如 ICD 编码规范、IEEE 标准细节、DRG 政策等）。"
            "返回搜索结果的摘要。",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "搜索关键词或问题"},
                },
                "required": ["query"],
            },
        },
    },
]


def get_tools_for_phase(phase: str) -> list[dict]:
    """返回某阶段可用的工具列表。

    'read'  — 文件读取阶段（read_* + search_web）
    'write' — 撰写阶段（search_web + save_document）
    """
    if phase == "read":
        return [t for t in TOOLS if t["function"]["name"] in (
            "read_requirement", "read_output_schema", "read_output_layout", "search_web"
        )]
    elif phase == "write":
        return [t for t in TOOLS if t["function"]["name"] in (
            "search_web", "save_document"
        )]
    return TOOLS


# ============================================================
# 工具实现
# ============================================================
def execute_tool(name: str, arguments: dict) -> str:
    if name == "read_requirement":
        logger.info("   read_requirement → 返回需求文档")
        return _source_md_content

    elif name == "read_output_schema":
        doc_type = arguments.get("doc_type")
        if doc_type:
            logger.info(f"   read_output_schema(doc_type='{doc_type}')")
            for doc in _OUTPUT_SCHEMA.get("documents", []):
                if doc.get("doc_type") == doc_type:
                    slim = {
                        "supported_output_formats": _OUTPUT_SCHEMA.get("supported_output_formats"),
                        "rendering_conventions": _OUTPUT_SCHEMA.get("rendering_conventions"),
                        "global_tips": _OUTPUT_SCHEMA.get("global_tips"),
                        "selected_document": doc,
                    }
                    return json.dumps(slim, ensure_ascii=False, indent=2)
            return json.dumps({"error": f"未找到文档类型: {doc_type}"}, ensure_ascii=False)
        else:
            logger.info("   read_output_schema (全部)")
            return json.dumps(_OUTPUT_SCHEMA, ensure_ascii=False, indent=2)

    elif name == "read_output_layout":
        logger.info("   read_output_layout → 返回排版规范")
        return _OUTPUT_LAYOUT

    elif name == "save_document":
        file_name = arguments.get("file_name", "output.md")
        content = arguments.get("content", "")
        output_path = OUTPUT_DIR / file_name
        output_path.write_text(content, encoding="utf-8")
        logger.info(f"   save_document → {output_path}")
        return str(output_path)

    elif name == "search_web":
        query = arguments.get("query", "")
        logger.info(f"   search_web: {query[:80]}...")
        # 调用外部搜索 API（使用 DuckDuckGo 免费接口）
        return _do_web_search(query)

    # ── 转换接口（预留）──
    elif name == "convert_to_pdf":
        return f"[预留] PDF 转换功能尚未实现。参数: {arguments}"
    elif name == "convert_to_docx":
        return f"[预留] DOCX 转换功能尚未实现。参数: {arguments}"
    elif name == "convert_to_txt":
        return f"[预留] TXT 转换功能尚未实现。参数: {arguments}"

    return f"未知工具: {name}"


# ============================================================
# 联网搜索
# ============================================================
def _do_web_search(query: str) -> str:
    """使用 DuckDuckGo Instant Answer API 搜索。"""
    import requests
    try:
        resp = requests.get(
            "https://api.duckduckgo.com/",
            params={"q": query, "format": "json", "no_html": "1", "skip_disambig": "1"},
            timeout=15,
        )
        data = resp.json()
        results = []
        if data.get("AbstractText"):
            results.append(f"摘要: {data['AbstractText']}")
        for item in data.get("RelatedTopics", [])[:5]:
            if isinstance(item, dict) and item.get("Text"):
                results.append(f"- {item['Text']}")
        return "\n".join(results) if results else f"未找到与 '{query}' 相关的结果。"
    except Exception as e:
        logger.warning(f"搜索失败: {e}")
        return f"搜索 '{query}' 失败: {e}。请基于已有知识回答。"


# ============================================================
# 文档结构辅助函数
# ============================================================
def get_doc_structure(doc_type: str) -> Optional[dict]:
    """获取指定文档类型的完整结构定义。"""
    for doc in _OUTPUT_SCHEMA.get("documents", []):
        if doc.get("doc_type") == doc_type:
            return doc
    return None


def flatten_sections(doc_type: str) -> list[dict]:
    """将文档的章节树展开为扁平的节列表（level 1 + level 2）。

    返回 [{"path": ["一","引言"], "level": 1, "section": {...}}, ...]
    """
    doc = get_doc_structure(doc_type)
    if doc is None:
        return []

    result = []
    _walk(doc["structure"]["sections"], [], result)
    return result


def _walk(sections: list, path: list, result: list):
    for sec in sections:
        cur = path + [sec["title"]]
        result.append({"path": cur, "level": sec["level"], "section": sec})
        for child in sec.get("children", []):
            _walk([child], cur, result)


# ============================================================
# 转换接口（预留，后续实现）
# ============================================================
def convert_to_pdf(md_path: str) -> str:
    """[预留] 将 Markdown 转为 PDF。"""
    raise NotImplementedError("PDF 转换功能尚未实现")


def convert_to_docx(md_path: str) -> str:
    """[预留] 将 Markdown 转为 DOCX。"""
    raise NotImplementedError("DOCX 转换功能尚未实现")


def convert_to_txt(md_path: str) -> str:
    """[预留] 将 Markdown 转为纯文本。"""
    raise NotImplementedError("TXT 转换功能尚未实现")
