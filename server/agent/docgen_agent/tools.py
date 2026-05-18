"""docgen_agent 工具定义与实现。

工具列表:
    read_requirement   — 读取需求源文件（默认 requirement.md，可由前端覆盖）
    read_output_schema — 读取 output_schema.json（按 doc_type 裁剪）
    read_output_layout — 读取 output_layout.json
    save_document      — 保存生成的 Markdown 文档
    search_web         — 联网搜索（补充领域知识）
    render_mermaid     — 将 Mermaid 代码渲染为 SVG/PNG 图片
    list_project_files — 读取项目文件树
    read_project_file  — 读取项目内文本文件
    search_project     — 搜索项目源码/配置
    read_api_routes    — 汇总后端路由
    read_data_models   — 汇总数据模型线索
    read_architecture_context — 汇总架构设计文档上下文
    read_test_context  — 汇总测试文档上下文
    convert_to_pdf     — MD → PDF（含排版样式）
"""

import base64
import fnmatch
import html as html_module
import json
import os
import re
import sys
import tomllib
from pathlib import Path
from typing import Any, Callable, Optional, cast

from loguru import logger
from openai import OpenAI

try:
    from ...config import API_KEY
except ImportError:
    _SERVER_DIR = Path(__file__).parent.parent.parent
    sys.path.insert(0, str(_SERVER_DIR))
    from config import API_KEY

CURRENT_DIR = Path(__file__).parent
PROJECT_ROOT = CURRENT_DIR.parents[2]
OUTPUT_DIR = CURRENT_DIR / "output_docs"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

DIAGRAM_DIR = OUTPUT_DIR / "diagrams"
DIAGRAM_DIR.mkdir(parents=True, exist_ok=True)

client = OpenAI(api_key=API_KEY, base_url="https://api.deepseek.com")

_IGNORED_DIRS = {
    ".git",
    ".idea",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    ".venv",
    "__pycache__",
    "dist",
    "build",
    "node_modules",
    "output_docs",
    ".playwright",
}
_TEXT_EXTENSIONS = {
    ".bat",
    ".cfg",
    ".conf",
    ".css",
    ".csv",
    ".env",
    ".example",
    ".html",
    ".ini",
    ".js",
    ".json",
    ".jsx",
    ".lock",
    ".md",
    ".py",
    ".sql",
    ".toml",
    ".ts",
    ".tsx",
    ".txt",
    ".yaml",
    ".yml",
}
_MAX_TOOL_CHARS = 20000

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
ToolDefinition = dict[str, Any]

TOOLS: list[ToolDefinition] = [
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
    {
        "type": "function",
        "function": {
            "name": "list_project_files",
            "description": "读取项目文件树，用于架构设计和测试文档中识别模块、配置、测试目录。默认忽略 .git/.venv/node_modules/output_docs 等目录。",
            "parameters": {
                "type": "object",
                "properties": {
                    "root": {"type": "string", "description": "相对项目根目录的子目录，默认项目根目录。"},
                    "patterns": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "可选 glob 列表，如 ['server/**/*.py', '*.toml']。为空则返回常用源码/配置文件。",
                    },
                    "max_files": {"type": "integer", "description": "最多返回文件数，默认 300。"},
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "read_project_file",
            "description": "读取项目内指定文本文件。用于查看源码、配置、README、接口说明等。",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "相对项目根目录的文件路径。"},
                    "max_chars": {"type": "integer", "description": "最多返回字符数，默认 20000。"},
                },
                "required": ["path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_project",
            "description": "在项目内搜索文本。用于查找路由、类、模型、测试、配置项等。",
            "parameters": {
                "type": "object",
                "properties": {
                    "pattern": {"type": "string", "description": "正则或普通文本搜索模式。"},
                    "glob": {"type": "string", "description": "可选 glob，如 'server/**/*.py'。"},
                    "max_results": {"type": "integer", "description": "最多返回匹配行数，默认 80。"},
                },
                "required": ["pattern"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "read_dependency_manifest",
            "description": "汇总项目依赖和技术栈信息，读取 pyproject.toml、package.json、requirements.txt 等。",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "read_api_routes",
            "description": "扫描后端源码中的 FastAPI/APIRouter 路由，用于生成接口定义、时序图和接口测试用例。",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "read_data_models",
            "description": "扫描项目中的数据模型、ORM、Schema、数据库迁移线索，用于生成 ER 图和数据字典。",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "read_deployment_config",
            "description": "读取 Docker、Compose、K8s、环境变量、启动脚本等部署配置，用于部署视图和测试环境说明。",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "read_existing_tests",
            "description": "扫描现有测试目录和测试文件，用于测试文档中复用已有测试范围与命名。",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "read_ci_config",
            "description": "读取 CI/CD 配置、测试命令和覆盖率配置，用于测试执行计划。",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "read_architecture_context",
            "description": "一次性汇总架构设计文档需要的项目上下文，包括目录、依赖、API、数据模型、部署配置和推荐图表。",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "read_test_context",
            "description": "一次性汇总测试文档需要的项目上下文，包括现有测试、接口、数据模型、CI 配置、测试命令和风险区域。",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "render_mermaid",
            "description": "将 Mermaid 图表代码渲染为 PNG 图片文件。"
            "返回值为相对于 output_docs/ 的图片路径（如 'diagrams/use_case.png'），请直接将该路径用于 Markdown 图片引用 ![标题](返回值)，不要自行拼接或修改路径。",
            "parameters": {
                "type": "object",
                "properties": {
                    "code": {"type": "string", "description": "完整的 Mermaid 图表代码（不含 ```mermaid 标记）"},
                    "file_name": {"type": "string", "description": "保存的图片文件名（不含扩展名），如 'use_case_diagram'"},
                    "format": {
                        "type": "string",
                        "enum": ["svg", "png"],
                        "description": "输出图片格式，默认 png（含中文必须用 png，svg 中文渲染不出）",
                    },
                },
                "required": ["code", "file_name"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "render_plantuml",
            "description": "将 PlantUML 图表代码渲染为 PNG 图片文件。PlantUML 支持 UML 用例图（含火柴人 Actor 和椭圆 UseCase）、类图、时序图等，适合需要标准 UML 图标的场景。"
            "返回值为相对于 output_docs/ 的图片路径，请直接用于 Markdown 图片引用 ![标题](返回值)。",
            "parameters": {
                "type": "object",
                "properties": {
                    "code": {"type": "string", "description": "完整的 PlantUML 代码（包含 @startuml 和 @enduml）"},
                    "file_name": {"type": "string", "description": "保存的图片文件名（不含扩展名），如 'use_case_overall'"},
                },
                "required": ["code", "file_name"],
            },
        },
    },
]


_PROJECT_READ_TOOL_NAMES = (
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
)
_READ_TOOL_NAMES = (
    "read_requirement",
    "read_output_schema",
    "read_output_layout",
    "search_web",
    *_PROJECT_READ_TOOL_NAMES,
)
_WRITE_TOOL_NAMES = (
    "search_web",
    "render_mermaid",
    "render_plantuml",
    "save_document",
)
def _tool_name(tool: ToolDefinition) -> str:
    function = cast(dict[str, Any], tool["function"])
    return str(function["name"])


_TOOL_BY_NAME: dict[str, ToolDefinition] = {_tool_name(tool): tool for tool in TOOLS}


def get_tools_for_phase(phase: str) -> list[ToolDefinition]:
    """返回某阶段可用的工具列表。

    'read'  — 文件读取阶段（read_* + search_web）
    'write' — 撰写阶段（search_web + save_document）
    """
    if phase == "read":
        return [_TOOL_BY_NAME[name] for name in _READ_TOOL_NAMES]
    if phase == "write":
        return [_TOOL_BY_NAME[name] for name in _WRITE_TOOL_NAMES]
    return TOOLS


# ============================================================
# 工具实现
# ============================================================
ToolHandler = Callable[[dict], str]


def _handle_read_requirement(_arguments: dict) -> str:
    logger.info("   read_requirement → 返回需求文档")
    return _source_md_content


def _handle_read_output_schema(arguments: dict) -> str:
    doc_type = arguments.get("doc_type")
    if not doc_type:
        logger.info("   read_output_schema (全部)")
        return json.dumps(_OUTPUT_SCHEMA, ensure_ascii=False, indent=2)

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


def _handle_read_output_layout(_arguments: dict) -> str:
    logger.info("   read_output_layout → 返回排版规范")
    return _OUTPUT_LAYOUT


def _handle_save_document(arguments: dict) -> str:
    file_name = Path(arguments.get("file_name", "output.md")).name
    content = arguments.get("content", "")
    doc_type = str(arguments.get("doc_type", ""))
    if doc_type:
        content = normalize_document_header(content, doc_type)
    content = normalize_heading_numbering(content)
    content = _fix_unordered_lists_in_md(content)
    content, table_issues = _validate_table_captions(content)
    for issue in table_issues:
        logger.warning(f"   save_document 表格修复: {issue}")
    output_path = OUTPUT_DIR / file_name
    output_path.write_text(content, encoding="utf-8")
    logger.info(f"   save_document → {output_path}")
    return str(output_path)


def _handle_search_web(arguments: dict) -> str:
    query = arguments.get("query", "")
    logger.info(f"   search_web: {query[:80]}...")
    return _do_web_search(query)


def _handle_list_project_files(arguments: dict) -> str:
    return list_project_files(
        root=arguments.get("root", ""),
        patterns=arguments.get("patterns") or None,
        max_files=int(arguments.get("max_files") or 300),
    )


def _handle_read_project_file(arguments: dict) -> str:
    return read_project_file(
        path=arguments.get("path", ""),
        max_chars=int(arguments.get("max_chars") or _MAX_TOOL_CHARS),
    )


def _handle_search_project(arguments: dict) -> str:
    return search_project(
        pattern=arguments.get("pattern", ""),
        glob=arguments.get("glob", ""),
        max_results=int(arguments.get("max_results") or 80),
    )


def _handle_read_dependency_manifest(_arguments: dict) -> str:
    return read_dependency_manifest()


def _handle_read_api_routes(_arguments: dict) -> str:
    return read_api_routes()


def _handle_read_data_models(_arguments: dict) -> str:
    return read_data_models()


def _handle_read_deployment_config(_arguments: dict) -> str:
    return read_deployment_config()


def _handle_read_existing_tests(_arguments: dict) -> str:
    return read_existing_tests()


def _handle_read_ci_config(_arguments: dict) -> str:
    return read_ci_config()


def _handle_read_architecture_context(_arguments: dict) -> str:
    return read_architecture_context()


def _handle_read_test_context(_arguments: dict) -> str:
    return read_test_context()


def _handle_render_mermaid(arguments: dict) -> str:
    code = arguments.get("code", "")
    file_name = arguments.get("file_name", "diagram")
    fmt = arguments.get("format", "png")
    logger.info(f"   render_mermaid → {DIAGRAM_DIR / file_name}.{fmt}")
    return _render_mermaid_to_file(code, file_name, fmt)


def _handle_render_plantuml(arguments: dict) -> str:
    code = arguments.get("code", "")
    file_name = arguments.get("file_name", "diagram")
    logger.info(f"   render_plantuml → {DIAGRAM_DIR / file_name}.png")
    return _render_plantuml_to_file(code, file_name)


def _handle_convert_to_pdf(arguments: dict) -> str:
    md_path = arguments.get("md_path", "")
    logger.info(f"   convert_to_pdf: {md_path}")
    return convert_to_pdf(md_path)


_TOOL_HANDLERS: dict[str, ToolHandler] = {
    "read_requirement": _handle_read_requirement,
    "read_output_schema": _handle_read_output_schema,
    "read_output_layout": _handle_read_output_layout,
    "save_document": _handle_save_document,
    "search_web": _handle_search_web,
    "list_project_files": _handle_list_project_files,
    "read_project_file": _handle_read_project_file,
    "search_project": _handle_search_project,
    "read_dependency_manifest": _handle_read_dependency_manifest,
    "read_api_routes": _handle_read_api_routes,
    "read_data_models": _handle_read_data_models,
    "read_deployment_config": _handle_read_deployment_config,
    "read_existing_tests": _handle_read_existing_tests,
    "read_ci_config": _handle_read_ci_config,
    "read_architecture_context": _handle_read_architecture_context,
    "read_test_context": _handle_read_test_context,
    "render_mermaid": _handle_render_mermaid,
    "render_plantuml": _handle_render_plantuml,
    "convert_to_pdf": _handle_convert_to_pdf,
}


def execute_tool(name: str, arguments: dict) -> str:
    handler = _TOOL_HANDLERS.get(name)
    if handler is None:
        return f"未知工具: {name}"
    return handler(arguments)


# ============================================================
# 项目资料读取工具
# ============================================================
def _is_ignored_path(path: Path) -> bool:
    return any(part in _IGNORED_DIRS for part in path.parts)


def _resolve_project_path(path: str | Path = "") -> Path:
    """解析项目内路径，禁止越过项目根目录。"""
    raw = Path(path) if path else PROJECT_ROOT
    target = raw if raw.is_absolute() else PROJECT_ROOT / raw
    target = target.resolve()
    try:
        target.relative_to(PROJECT_ROOT.resolve())
    except ValueError as exc:
        raise ValueError(f"路径超出项目根目录: {path}") from exc
    return target


def _is_text_file(path: Path) -> bool:
    return path.suffix.lower() in _TEXT_EXTENSIONS or path.name in {
        ".env",
        ".env.example",
        "Dockerfile",
        "Makefile",
    }


def _rel(path: Path) -> str:
    return path.resolve().relative_to(PROJECT_ROOT.resolve()).as_posix()


def _iter_project_files(root: str | Path = "", patterns: list[str] | None = None) -> list[Path]:
    base = _resolve_project_path(root)
    if not base.exists():
        return []
    result = []

    if base.is_file():
        candidates = [base]
    else:
        candidates = []
        for dirpath, dirnames, filenames in os.walk(base):
            current_dir = Path(dirpath)
            dirnames[:] = [
                dirname
                for dirname in dirnames
                if dirname not in _IGNORED_DIRS
                and not _is_ignored_path(Path(_rel(current_dir / dirname)))
            ]
            candidates.extend(current_dir / filename for filename in filenames)

    for path in candidates:
        rel_path = _rel(path)
        if _is_ignored_path(Path(rel_path)):
            continue
        if patterns and not any(fnmatch.fnmatch(rel_path, pat) for pat in patterns):
            continue
        if not patterns and not _is_text_file(path):
            continue
        result.append(path)
    return sorted(result, key=lambda p: _rel(p))


def _read_text_limited(path: Path, max_chars: int = _MAX_TOOL_CHARS) -> str:
    if not path.exists():
        return f"[错误] 文件不存在: {_rel(path) if path.is_absolute() else path}"
    if not path.is_file():
        return f"[错误] 不是文件: {_rel(path)}"
    if not _is_text_file(path):
        return f"[跳过] 非文本文件: {_rel(path)}"
    text = path.read_text(encoding="utf-8", errors="replace")
    if len(text) > max_chars:
        return text[:max_chars] + f"\n...[已截断，原始长度 {len(text)} 字符]"
    return text


def list_project_files(
    root: str = "",
    patterns: list[str] | None = None,
    max_files: int = 300,
) -> str:
    """返回项目文件列表，供架构/测试文档理解项目边界。"""
    files = _iter_project_files(root, patterns)
    payload = {
        "project_root": str(PROJECT_ROOT),
        "root": root or ".",
        "patterns": patterns or [],
        "total": len(files),
        "files": [_rel(path) for path in files[:max_files]],
        "truncated": len(files) > max_files,
    }
    return json.dumps(payload, ensure_ascii=False, indent=2)


def read_project_file(path: str, max_chars: int = _MAX_TOOL_CHARS) -> str:
    """读取项目内单个文本文件。"""
    target = _resolve_project_path(path)
    return _read_text_limited(target, max_chars=max_chars)


def search_project(pattern: str, glob: str = "", max_results: int = 80) -> str:
    """在项目内搜索文本，返回匹配文件和行号。"""
    if not pattern:
        return json.dumps({"error": "pattern 不能为空"}, ensure_ascii=False)
    try:
        regex = re.compile(pattern, re.IGNORECASE)
    except re.error:
        regex = re.compile(re.escape(pattern), re.IGNORECASE)

    patterns = [glob] if glob else None
    results = []
    for path in _iter_project_files("", patterns):
        try:
            lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
        except OSError:
            continue
        for line_no, line in enumerate(lines, start=1):
            if regex.search(line):
                results.append({
                    "path": _rel(path),
                    "line": line_no,
                    "text": line.strip()[:500],
                })
                if len(results) >= max_results:
                    return json.dumps(
                        {"pattern": pattern, "glob": glob, "results": results, "truncated": True},
                        ensure_ascii=False,
                        indent=2,
                    )

    return json.dumps(
        {"pattern": pattern, "glob": glob, "results": results, "truncated": False},
        ensure_ascii=False,
        indent=2,
    )


def read_dependency_manifest() -> str:
    """读取依赖清单，汇总技术栈。"""
    manifest_names = [
        "pyproject.toml",
        "requirements.txt",
        "requirements-dev.txt",
        "server/requirements.txt",
        "server/requirements-dev.txt",
        "package.json",
        "client/package.json",
        "server/package.json",
        "pnpm-lock.yaml",
        "client/pnpm-lock.yaml",
        "yarn.lock",
        "client/yarn.lock",
        "package-lock.json",
        "client/package-lock.json",
        "uv.lock",
    ]
    manifests = []
    for name in manifest_names:
        path = PROJECT_ROOT / name
        if not path.exists():
            continue
        entry: dict[str, object] = {"path": _rel(path)}
        if path.name == "pyproject.toml":
            try:
                data = tomllib.loads(path.read_text(encoding="utf-8"))
                project = data.get("project", {})
                entry["name"] = project.get("name")
                entry["requires_python"] = project.get("requires-python")
                entry["dependencies"] = project.get("dependencies", [])
                entry["dev_dependencies"] = data.get("dependency-groups", {}).get("dev", [])
            except Exception as exc:
                entry["error"] = str(exc)
        elif path.name == "package.json":
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                entry["name"] = data.get("name")
                entry["scripts"] = data.get("scripts", {})
                entry["dependencies"] = data.get("dependencies", {})
                entry["devDependencies"] = data.get("devDependencies", {})
            except Exception as exc:
                entry["error"] = str(exc)
        else:
            entry["preview"] = _read_text_limited(path, max_chars=4000)
        manifests.append(entry)

    return json.dumps({"manifests": manifests}, ensure_ascii=False, indent=2)


def read_api_routes() -> str:
    """扫描 FastAPI 路由定义。"""
    route_pattern = re.compile(
        r"@(?P<router>\w+)\.(?P<method>get|post|put|delete|patch|options|head)\(\s*['\"](?P<path>[^'\"]+)['\"]",
        re.IGNORECASE,
    )
    prefix_pattern = re.compile(r"APIRouter\(\s*prefix\s*=\s*['\"](?P<prefix>[^'\"]*)['\"]")
    routes = []
    for path in _iter_project_files("server", ["server/**/*.py"]):
        text = path.read_text(encoding="utf-8", errors="replace")
        prefix_match = prefix_pattern.search(text)
        prefix = prefix_match.group("prefix") if prefix_match else ""
        for match in route_pattern.finditer(text):
            routes.append({
                "file": _rel(path),
                "method": match.group("method").upper(),
                "router": match.group("router"),
                "prefix": prefix,
                "path": match.group("path"),
                "full_path": f"{prefix}{match.group('path')}",
            })
    return json.dumps({"routes": routes}, ensure_ascii=False, indent=2)


def read_data_models() -> str:
    """扫描数据模型和 schema 线索。"""
    class_pattern = re.compile(r"^class\s+(?P<name>\w+)\((?P<bases>[^)]*)\):", re.MULTILINE)
    field_pattern = re.compile(r"^\s+(?P<name>\w+)\s*:\s*(?P<type>[^=\n]+)", re.MULTILINE)
    model_files = []
    for path in _iter_project_files("", ["server/**/*.py"]):
        text = path.read_text(encoding="utf-8", errors="replace")
        if not any(token in text for token in ("SQLModel", "BaseModel", "Field(", "Relationship(", "table=True")):
            continue
        classes = []
        for match in class_pattern.finditer(text):
            bases = match.group("bases")
            if not any(token in bases or token in text[match.start(): match.start() + 300] for token in ("SQLModel", "BaseModel", "table=True")):
                continue
            body_start = match.end()
            next_class = class_pattern.search(text, body_start)
            body = text[body_start: next_class.start() if next_class else len(text)]
            fields = [
                {"name": f.group("name"), "type": f.group("type").strip()}
                for f in field_pattern.finditer(body)
                if not f.group("name").startswith("_")
            ][:50]
            classes.append({"name": match.group("name"), "bases": bases, "fields": fields})
        if classes:
            model_files.append({"file": _rel(path), "classes": classes})
    return json.dumps({"model_files": model_files}, ensure_ascii=False, indent=2)


def read_deployment_config() -> str:
    """读取部署和环境配置线索。"""
    patterns = [
        "Dockerfile",
        "**/Dockerfile",
        "docker-compose*.yml",
        "docker-compose*.yaml",
        "**/*.env",
        "**/*.env.example",
        "**/k8s/**/*.yaml",
        "**/k8s/**/*.yml",
        "**/deploy/**/*.yaml",
        "**/deploy/**/*.yml",
        "**/nginx*.conf",
        "**/README.md",
    ]
    files = _iter_project_files("", patterns)
    entries = []
    for path in files[:30]:
        entries.append({"path": _rel(path), "content": _read_text_limited(path, max_chars=5000)})
    return json.dumps({"files": entries, "truncated": len(files) > 30}, ensure_ascii=False, indent=2)


def read_existing_tests() -> str:
    """读取测试文件概览和关键内容。"""
    patterns = [
        "tests/**/*.py",
        "server/**/test_*.py",
        "server/**/*_test.py",
        "client/**/*.test.*",
        "client/**/*.spec.*",
        "**/pytest.ini",
        "**/conftest.py",
    ]
    files = _iter_project_files("", patterns)
    entries = []
    for path in files[:60]:
        text = _read_text_limited(path, max_chars=5000)
        test_names = re.findall(r"def\s+(test_\w+)\s*\(", text)
        entries.append({"path": _rel(path), "test_names": test_names[:50], "content": text})
    return json.dumps({"test_files": entries, "truncated": len(files) > 60}, ensure_ascii=False, indent=2)


def read_ci_config() -> str:
    """读取 CI/CD 与测试命令配置。"""
    patterns = [
        ".github/workflows/*.yml",
        ".github/workflows/*.yaml",
        ".gitlab-ci.yml",
        "azure-pipelines.yml",
        "Jenkinsfile",
        "tox.ini",
        "pytest.ini",
        "coverage.ini",
        "pyproject.toml",
        "package.json",
    ]
    files = _iter_project_files("", patterns)
    entries = []
    for path in files[:30]:
        entries.append({"path": _rel(path), "content": _read_text_limited(path, max_chars=6000)})
    return json.dumps({"ci_files": entries, "truncated": len(files) > 30}, ensure_ascii=False, indent=2)


def _json_tool_payload(raw: str) -> dict:
    try:
        value = json.loads(raw)
    except json.JSONDecodeError:
        return {"raw": raw}
    return value if isinstance(value, dict) else {"value": value}


def _candidate_test_commands(dependencies: dict, existing_tests: dict) -> list[str]:
    commands: list[str] = []
    manifests = dependencies.get("manifests", [])
    for manifest in manifests if isinstance(manifests, list) else []:
        if not isinstance(manifest, dict):
            continue
        path = str(manifest.get("path", ""))
        scripts = manifest.get("scripts", {})
        if path.endswith("package.json") and isinstance(scripts, dict):
            for script_name in ("test", "test:unit", "test:e2e", "coverage", "lint", "type-check", "build"):
                if script_name in scripts:
                    commands.append(f"npm run {script_name}")
        if path.endswith("pyproject.toml"):
            deps = manifest.get("dependencies", [])
            dev_deps = manifest.get("dev_dependencies", [])
            dep_items = []
            for value in (deps, dev_deps):
                if isinstance(value, list):
                    dep_items.extend(value)
                elif isinstance(value, dict):
                    dep_items.extend(value)
                elif value:
                    dep_items.append(value)
            dep_text = " ".join(str(item) for item in dep_items)
            dep_text_lower = dep_text.lower()
            if "pytest" in dep_text_lower:
                commands.extend(["python -m pytest", "uv run pytest"])
            if "ruff" in dep_text_lower:
                commands.append("uv run ruff check server")
            if "ty" in dep_text_lower:
                commands.append("uv run ty check server")

    test_files = existing_tests.get("test_files", [])
    if test_files and not any("pytest" in command for command in commands):
        commands.append("python -m pytest")
    return list(dict.fromkeys(commands))


def read_architecture_context() -> str:
    """汇总架构设计文档需要的项目上下文。"""
    file_patterns = [
        "server/**/*.py",
        "client/src/**/*",
        "pyproject.toml",
        "package.json",
        "README.md",
        "server/**/README.md",
        "client/**/README.md",
        "Dockerfile",
        "docker-compose*.yml",
        "docker-compose*.yaml",
    ]
    payload = {
        "project_root": str(PROJECT_ROOT),
        "project_files": _json_tool_payload(list_project_files(patterns=file_patterns, max_files=220)),
        "dependencies": _json_tool_payload(read_dependency_manifest()),
        "api_routes": _json_tool_payload(read_api_routes()),
        "data_models": _json_tool_payload(read_data_models()),
        "deployment_config": _json_tool_payload(read_deployment_config()),
        "recommended_diagrams": [
            {
                "name": "系统上下文图",
                "tool": "render_mermaid",
                "syntax": "flowchart TB",
                "source": "project_files + dependencies",
            },
            {
                "name": "容器/组件图",
                "tool": "render_mermaid",
                "syntax": "flowchart TB",
                "source": "project_files + api_routes",
            },
            {
                "name": "核心接口时序图",
                "tool": "render_mermaid",
                "syntax": "sequenceDiagram",
                "source": "api_routes",
            },
            {
                "name": "数据模型图",
                "tool": "render_mermaid 或 render_plantuml",
                "syntax": "erDiagram 或 classDiagram",
                "source": "data_models",
            },
            {
                "name": "部署视图",
                "tool": "render_mermaid",
                "syntax": "flowchart TB",
                "source": "deployment_config",
            },
        ],
        "writing_guidance": [
            "优先引用真实目录、依赖、路由和模型；缺失信息需要标注为待确认，不要编造实现细节。",
            "状态图、组件图和部署图优先使用 TB/从上到下方向，避免横向过宽。",
            "接口章节应从 api_routes 中提取真实 path/method/prefix。",
        ],
    }
    return json.dumps(payload, ensure_ascii=False, indent=2)


def read_test_context() -> str:
    """汇总测试文档需要的项目上下文。"""
    dependencies = _json_tool_payload(read_dependency_manifest())
    existing_tests = _json_tool_payload(read_existing_tests())
    payload = {
        "project_root": str(PROJECT_ROOT),
        "dependencies": dependencies,
        "api_routes": _json_tool_payload(read_api_routes()),
        "data_models": _json_tool_payload(read_data_models()),
        "deployment_config": _json_tool_payload(read_deployment_config()),
        "existing_tests": existing_tests,
        "ci_config": _json_tool_payload(read_ci_config()),
        "candidate_test_commands": _candidate_test_commands(dependencies, existing_tests),
        "recommended_test_scope": [
            "单元测试：核心算法、数据转换、工具函数、边界条件。",
            "接口测试：FastAPI 路由、请求参数、响应结构、异常状态码。",
            "集成测试：文档生成流程、LLM 工具调用、Markdown/PDF 输出链路。",
            "前端测试：文档生成页面、状态轮询、下载、中断、追加提示。",
            "回归测试：表格修复、图表渲染、输出 schema/layout 约束。",
        ],
        "risk_areas": [
            "外部渲染服务或联网搜索失败时的降级行为。",
            "Markdown 表格列数不一致、单元格未转义竖线导致 PDF 渲染异常。",
            "长文档生成过程中的中断、终止和追加提示状态一致性。",
            "上传文件路径和 output_docs 下载路径的安全校验。",
        ],
    }
    return json.dumps(payload, ensure_ascii=False, indent=2)


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
# Mermaid 渲染
# ============================================================
def _normalize_mermaid_code(code: str) -> str:
    """对常见 Mermaid 图做可读性修正。具体图型要求来自 output_schema.json。"""
    lines = code.strip().splitlines()
    if not lines:
        return code

    first = lines[0].strip()
    if first.startswith("stateDiagram") and not any(
        line.strip().startswith("direction ") for line in lines[1:4]
    ):
        lines.insert(1, "    direction TB")
    return "\n".join(lines)


def _render_mermaid_to_file(code: str, file_name: str, fmt: str = "png") -> str:
    """通过 mermaid.ink API 将 Mermaid 代码渲染为图片文件。"""
    import requests

    code = _normalize_mermaid_code(code)

    # 尝试渲染，失败时自动拆分多图合并的代码块（LLM 有时用 --- 拼接多个图）
    codes_to_try = [code]
    if "\n---\n" in code:
        codes_to_try = [c.strip() for c in code.split("\n---\n") if c.strip()]
        logger.info(f"   Mermaid 代码含 {len(codes_to_try)} 个分段，将分别尝试渲染")

    last_error = None
    for i, sub_code in enumerate(codes_to_try):
        sub_code = _normalize_mermaid_code(sub_code)
        sub_mermaid = json.dumps({"code": sub_code, "mermaid": {"theme": "default"}})
        sub_enc = base64.urlsafe_b64encode(sub_mermaid.encode()).decode().rstrip("=")
        sub_url = (
            f"https://mermaid.ink/img/{sub_enc}?type=png"
            if fmt == "png"
            else f"https://mermaid.ink/svg/{sub_enc}"
        )

        try:
            resp = requests.get(sub_url, timeout=30)
            resp.raise_for_status()
            content_type = resp.headers.get("Content-Type", "")
            if "image" not in content_type:
                raise ValueError(f"非图片响应: {content_type}")
            # 成功：保存并返回
            suffix = f"_{i}" if i > 0 else ""
            output_path = DIAGRAM_DIR / f"{file_name}{suffix}.{fmt}"
            output_path.write_bytes(resp.content)
            return str(output_path.relative_to(OUTPUT_DIR))
        except Exception as e:
            last_error = e
            logger.warning(f"   Mermaid 分段 {i + 1}/{len(codes_to_try)} 渲染失败: {e}")

    # 全部失败，fallback
    logger.warning(f"Mermaid 全部渲染失败: {last_error}")
    fallback_path = DIAGRAM_DIR / f"{file_name}.txt"
    fallback_path.write_text(f"```mermaid\n{code}\n```\n", encoding="utf-8")
    return f"[渲染失败] Mermaid 代码已保存至 {fallback_path}，错误: {last_error}"


def _render_plantuml_to_file(code: str, file_name: str) -> str:
    """通过 plantuml.com 官方服务器将 PlantUML 代码渲染为 PNG。
    PlantUML 专为 UML 图设计，原生支持 Actor（火柴人）、UseCase（椭圆）等元素。
    编码方式：deflate 压缩 → 去 zlib 头尾 → PlantUML base64（+/ → -_）。
    """
    import requests
    import zlib

    try:
        compressor = zlib.compressobj(level=9)
        compressed = compressor.compress(code.encode("utf-8")) + compressor.flush()
        data = compressed[2:-4]  # 去掉 zlib header (2B) + Adler-32 checksum (4B)
        b64 = base64.b64encode(data).decode()
        # PlantUML 自定义 base64 字母表（与标准 base64 完全不同！）
        _STD = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/"
        _PUML = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz-_"
        _TRANS = str.maketrans(_STD, _PUML)
        encoded = b64.translate(_TRANS).rstrip("=")
        url = f"https://www.plantuml.com/plantuml/png/{encoded}"
    except Exception as e:
        logger.warning(f"PlantUML 编码失败: {e}")
        fallback_path = DIAGRAM_DIR / f"{file_name}.txt"
        fallback_path.write_text(f"```plantuml\n{code}\n```\n", encoding="utf-8")
        return f"[渲染失败] PlantUML 编码失败: {e}"

    try:
        resp = requests.get(url, timeout=30)
        resp.raise_for_status()
        content_type = resp.headers.get("Content-Type", "")
        if "image" not in content_type and "svg" not in content_type:
            raise ValueError(f"非图片响应: {content_type}")
    except Exception as e:
        logger.warning(f"PlantUML 渲染失败: {e}")
        fallback_path = DIAGRAM_DIR / f"{file_name}.txt"
        fallback_path.write_text(f"```plantuml\n{code}\n```\n", encoding="utf-8")
        return f"[渲染失败] PlantUML 代码已保存至 {fallback_path}，错误: {e}"

    output_path = DIAGRAM_DIR / f"{file_name}.png"
    output_path.write_bytes(resp.content)
    return str(output_path.relative_to(OUTPUT_DIR))


def _render_diagram_blocks_for_html(md_text: str) -> str:
    """将 Markdown 中的 ```mermaid / ```plantuml 代码块替换为 base64 <img> 标签。"""
    pattern = re.compile(r"```(mermaid|plantuml)\s*\n(.*?)```", re.DOTALL)

    def _replace(match):
        diagram_type = match.group(1)
        code = match.group(2).strip()
        import hashlib
        hash_suffix = hashlib.md5(code.encode()).hexdigest()[:8]
        file_name = f"{diagram_type}_{hash_suffix}"

        if diagram_type == "mermaid":
            result = _render_mermaid_to_file(code, file_name, "png")
        else:
            result = _render_plantuml_to_file(code, file_name)

        if "渲染失败" in result:
            return f'<pre><code>{html_module.escape(code)}</code></pre>'
        try:
            png_bytes = (OUTPUT_DIR / result).read_bytes()
            b64 = base64.b64encode(png_bytes).decode()
            data_uri = f"data:image/png;base64,{b64}"
        except Exception:
            return f'<pre><code>{html_module.escape(code)}</code></pre>'
        return (
            f'<div class="figure-container">'
            f'<img src="{data_uri}" alt="diagram"/>'
            f'</div>'
        )

    return pattern.sub(_replace, md_text)


# ============================================================
# CSS 生成（完全由 output_layout.json 驱动，不硬编码格式值）
# ============================================================
def _layout_css() -> str:
    """根据 output_layout.json 生成打印 CSS。所有格式值均从配置读取。"""
    L = json.loads(_OUTPUT_LAYOUT)

    ps = L["page_setup"]
    font = L["font"]
    body = L["body_text"]
    doc_title = L["document_title"]
    doc_meta = L["document_meta"]
    figs = L["figures"]
    tbls = L["tables"]
    code_cfg = L["code_blocks"]
    lists_cfg = L["lists"]
    page_breaks = L.get("page_breaks", {})
    pdf_cfg = L["pdf_rendering"]

    bf = font["body_font"]
    bff = font["body_font_fallback"]
    tf = font["title_font"]
    tff = font["title_font_fallback"]
    mf = font["mono_font"]
    mff = font["mono_font_fallback"]

    # 标题 CSS
    heading_css_parts = []
    for lv in L["headings"]["levels"]:
        tag = lv["html_tag"]
        fs = lv["font_size"]
        bold = "bold" if lv.get("bold") else "normal"
        align = lv.get("alignment", "left")
        ti = lv.get("text_indent", "0")
        sb = L["headings"]["global"]["space_before"]
        sa = L["headings"]["global"]["space_after"]
        heading_css_parts.append(f"""\
{tag} {{
    font-family: "{tff}", "{tf}", sans-serif;
    font-size: {fs};
    font-weight: {bold};
    text-align: {align};
    margin-top: {sb};
    margin-bottom: {sa};
    text-indent: {ti};
}}""")

    heading_css = "\n\n".join(heading_css_parts)

    # 分页符（h2 前分页，排除第一个 h2；同时用 legacy 和标准属性兼容 Chromium）
    pb_css = ""
    if page_breaks.get("enabled"):
        pb_css = """
/* ===== 分页符（仅 PDF/DOCX 生效，md 中不可见）===== */
h2 {
    break-before: page;
    page-break-before: always;
    break-after: avoid;
    page-break-after: avoid;
}
h2:first-of-type {
    break-before: avoid;
    page-break-before: avoid;
}
"""

    return f"""\
@page {{
    size: {ps['paper_size']};
    margin-top: {ps['margin_top']};
    margin-bottom: {ps['margin_bottom']};
    margin-left: {ps['margin_left']};
    margin-right: {ps['margin_right']};
}}

body {{
    font-family: "{bff}", "{bf}", serif;
    font-size: {font['body_size']};
    line-height: {body['line_spacing']};
    text-align: {body['alignment']};
}}

/* ===== 段落 ===== */
p {{
    text-indent: {body['first_line_indent']};
    margin-top: {body['space_before']};
    margin-bottom: {body['space_after']};
}}

/* ===== 标题页垂直居中容器 ===== */
.title-page-wrapper {{
    display: flex;
    flex-direction: column;
    justify-content: center;
    align-items: center;
    min-height: {pdf_cfg['title_page_min_height']};
    text-align: center;
    page-break-after: always;
}}

/* ===== 文档总标题（居中）===== */
.doc-title {{
    text-align: {doc_title['alignment']};
    font-family: "{tff}", "{tf}", sans-serif;
    font-size: {doc_title['font_size']};
    font-weight: {'bold' if doc_title.get('bold') else 'normal'};
    margin-top: {doc_title['margin_top']};
    margin-bottom: {doc_title['margin_bottom']};
    text-indent: 0;
}}

/* ===== 文档元数据（版本号、日期、状态）===== */
.doc-meta {{
    text-align: {doc_meta['alignment']};
    font-family: "{bff}", "{bf}", serif;
    font-size: {doc_meta['font_size']};
    color: {doc_meta['color']};
    margin-bottom: {doc_meta['margin_bottom']};
    text-indent: 0;
}}
.doc-meta p {{
    text-align: center;
    text-indent: 0;
    margin: {pdf_cfg['doc_meta_line_margin']};
}}

{heading_css}

/* ===== 全局图片约束（覆盖所有 img，含 Markdown 裸图）===== */
img {{
    max-width: {pdf_cfg['image_max_width']};
    max-height: {pdf_cfg['image_max_height']};
    width: auto;
    height: auto;
    object-fit: contain;
}}

/* ===== 图表容器（图片本身无缩进，标题由 _center_captions 居中）===== */
figure, .figure-container {{
    text-align: {figs['alignment']};
    margin: {figs['margin']};
    text-indent: 0;
}}

figure img, .figure-container img {{
    max-width: {pdf_cfg['figure_image_max_width']};
    max-height: {pdf_cfg['figure_image_max_height']};
    height: auto;
}}

/* 图表所在的段落不缩进 */
figure + p, .figure-container + p {{
    text-indent: 0;
}}

figcaption, .figcaption {{
    font-size: {figs['font_size']};
    text-align: center;
    margin-top: {pdf_cfg['caption_margin_top']};
    text-indent: 0;
}}

/* ===== 表格 ===== */
table {{
    margin: {pdf_cfg['table_margin']};
    border-collapse: collapse;
    text-indent: 0;
}}

th {{
    font-weight: bold;
    font-size: {tbls['font_size']};
    text-align: center;
    vertical-align: middle;
    padding: {tbls['header']['padding']};
    border: {tbls['border']};
    background-color: {tbls['header']['background_color']};
}}

td {{
    font-size: {tbls['font_size']};
    text-align: center;
    vertical-align: middle;
    padding: {tbls['cell']['padding']};
    border: {tbls['border']};
}}


/* ===== 代码块 ===== */
pre {{
    font-family: "{mf}", "{mff}", monospace;
    font-size: {code_cfg['font_size']};
    line-height: {code_cfg['line_spacing']};
    background-color: {code_cfg['background_color']};
    border: {code_cfg['border']};
    padding: {code_cfg['padding']};
    overflow-x: auto;
    text-indent: {code_cfg['text_indent']};
    white-space: pre-wrap;
}}

code {{
    font-family: "{mf}", "{mff}", monospace;
    font-size: {code_cfg['font_size']};
    background-color: {code_cfg['background_color']};
    padding: {pdf_cfg['inline_code_padding']};
}}

pre code {{
    background-color: transparent;
    padding: 0;
}}

/* ===== 列表 ===== */
ul, ol {{
    margin: {pdf_cfg['list_margin']};
    padding-left: {lists_cfg['indent']};
    text-indent: {lists_cfg['text_indent']};
}}

li {{
    margin-bottom: {lists_cfg['item_margin_bottom']};
    text-indent: 0;
}}

/* ===== 分隔线 ===== */
hr {{
    border: none;
    border-top: {pdf_cfg['horizontal_rule_border']};
    margin: {pdf_cfg['horizontal_rule_margin']};
}}
{pb_css}"""


# ============================================================
# 文本清理
# ============================================================
_BOILERPLATE_PATTERNS = [
    # 开头客套话
    r"^好的[，,]我这就[为您你]?[生编]?写[^\n]*[\n]+",
    r"^好的[，,]以下是为[您你][生编]?成的[^\n]*[\n]+",
    r"^收到[，,][我]?[马上]?[为您你]?[生编]?[成写][^\n]*[\n]+",
    r"^明白了[，,][我]?[马上]?[为您你]?[生编]?[成写][^\n]*[\n]+",
    r"^让我[们]?[来]?[为您你]?[生编]?[成写][^\n]*[\n]+",
    r"^以下是[我]*[为您你]?[生编]?[成写]?的[^\n]*[\n]+",
    r"^根据[您的你][需求要]求[，,][我][^\n]*[\n]+",
    # 结尾声明
    r"[\n]+[>]*\s*[以]?上[述内]?容[由仅]?[AI人工智能]?[生]?[成]?[，,]?[仅供参]?考[。]?\s*",
    r"[\n]+[>]*\s*\*{0,2}[以]?上[述内]?[文档容]?[由仅]?AI[生]?[成]?[，,]?[仅供参]?考[。]?\*{0,2}\s*",
    r"[\n]+[>]*\s*\*{0,2}本文[档由]?[由仅]?AI[生]?[成]?\*{0,2}\s*",
    r"[\n]+\s*请注意[，,][以]?上[述]?[内容文档]?[由仅]?AI[生]?[成][^\n]*[\n]?",
]


def _clean_boilerplate(text: str) -> str:
    """清理 LLM 输出中常见的客套话和 AI 声明。"""
    import re as _re
    for pattern in _BOILERPLATE_PATTERNS:
        text = _re.sub(pattern, "", text, flags=_re.IGNORECASE)
    return text.strip()


def _fix_unordered_lists_in_md(md_text: str) -> str:
    """后处理安全网：将 Markdown 中残余的 - 无序列表转为 (1)(2)... 有序编号。
    仅在代码块外部生效，代码块内的 - 保持不动。
    """
    import re as _re

    parts = _re.split(r'(```.*?```)', md_text, flags=_re.DOTALL)

    for i in range(0, len(parts), 2):
        lines = parts[i].split('\n')
        fixed = []
        counter = 0
        prev_blank = False

        for line in lines:
            m = _re.match(r'^(\s*)- (.*)', line)
            if m:
                indent, content = m.groups()
                counter = 1 if prev_blank else counter + 1
                fixed.append(f'{indent}({counter}) {content}')
                prev_blank = False
            else:
                fixed.append(line)
                stripped = line.strip()
                if not stripped:
                    prev_blank = True
                else:
                    # 非空非列表行：若为正文（非缩进续行），重置计数器
                    if not line.startswith((' ', '\t')) and not _re.match(r'^#', line):
                        counter = 0
                    prev_blank = False

        parts[i] = '\n'.join(fixed)

    return ''.join(parts)


_DETAIL_LABELS = {
    "描述",
    "功能描述",
    "输入",
    "处理",
    "处理流程",
    "输出",
    "异常处理",
    "待定原因",
    "影响评估",
    "建议处理阶段",
    "前置条件",
    "操作步骤",
    "预期结果",
    "通过准则",
    "职责描述",
    "接口定义",
    "依赖与其他模块的交互",
    "测试数据",
    "优先级",
    "说明",
}


def _heading_number_from_line(line: str) -> str:
    match = re.match(r"^#{2,6}\s+(?P<number>\d+(?:\.\d+){1,4})\b", line.strip())
    return match.group("number") if match else ""


def _segments(number: str) -> int:
    return len(number.split(".")) if number else 0


def _current_four_part_parent(parent_numbers: list[str]) -> str:
    for number in reversed(parent_numbers):
        if _segments(number) >= 3:
            return ".".join(number.split(".")[:3])
    for number in reversed(parent_numbers):
        if _segments(number) == 2:
            return f"{number}.1"
    return ""


def _looks_like_detail_line(line: str) -> bool:
    match = re.match(r"^\s*\(\d+\)\s*([^：:]{1,24})[：:]", line)
    return bool(match and match.group(1).strip() in _DETAIL_LABELS)


def _looks_like_promotable_title(lines: list[str], index: int) -> bool:
    line = lines[index]
    if _looks_like_detail_line(line):
        return False
    if not re.match(r"^\s*(?:#{5,6}\s*)?\(\d+\)\s+\S+", line):
        return False
    for next_line in lines[index + 1:index + 6]:
        if not next_line.strip():
            continue
        if re.match(r"^#{1,6}\s+", next_line):
            return False
        return _looks_like_detail_line(next_line)
    return False


def _strip_heading_number(title: str) -> str:
    title = re.sub(r"^\s*\(?\d+\)?[.、．]?\s*", "", title).strip()
    title = re.sub(r"^\d+(?:\.\d+){1,4}\s+", "", title).strip()
    return title


def normalize_heading_numbering(md_text: str) -> str:
    """Promote heading-like numbered list items to four-part Markdown headings."""
    lines = md_text.splitlines()
    out: list[str] = []
    parent_numbers: list[str] = []
    in_promoted_block = False

    for index, line in enumerate(lines):
        heading_match = re.match(r"^(#{1,6})\s+(.+?)\s*$", line)
        if heading_match:
            in_promoted_block = False
            level = min(len(heading_match.group(1)), 6)
            title = heading_match.group(2).strip()
            number = _heading_number_from_line(line)
            if number:
                parent_numbers = parent_numbers[: max(level - 2, 0)] + [number]

            title_match = re.match(r"^\((\d+)\)\s+(.+)$", title)
            parent = _current_four_part_parent(parent_numbers)
            if level >= 5 and title_match and parent:
                ordinal = title_match.group(1)
                title_text = _strip_heading_number(title_match.group(2))
                out.append(f"##### {parent}.{ordinal} {title_text}")
                in_promoted_block = True
                continue

            if level > 6:
                level = 6
            out.append(f"{'#' * level} {title}")
            continue

        if _looks_like_promotable_title(lines, index):
            match = re.match(r"^\s*(?:#{5,6}\s*)?\((\d+)\)\s+(.+?)\s*$", line)
            parent = _current_four_part_parent(parent_numbers)
            if match and parent:
                ordinal = match.group(1)
                title_text = _strip_heading_number(match.group(2))
                out.append(f"##### {parent}.{ordinal} {title_text}")
                in_promoted_block = True
                continue

        if in_promoted_block:
            detail_match = re.match(r"^\s*\(\d+\)\s*([^：:]{1,24})[：:]\s*(.*)$", line)
            if detail_match and detail_match.group(1).strip() in _DETAIL_LABELS:
                label = detail_match.group(1).strip()
                value = detail_match.group(2).strip()
                out.append(f"**{label}**：{value}")
                continue
            if re.match(r"^#{1,6}\s+", line):
                in_promoted_block = False

        out.append(line)

    return "\n".join(out) + ("\n" if md_text.endswith("\n") else "")


def _is_table_line(line: str) -> bool:
    stripped = line.strip()
    return stripped.startswith("|") and stripped.endswith("|") and stripped.count("|") >= 2


def _split_table_row(line: str) -> list[str]:
    stripped = line.strip()
    if stripped.startswith("|"):
        stripped = stripped[1:]
    if stripped.endswith("|"):
        stripped = stripped[:-1]
    return [cell.strip() for cell in stripped.split("|")]


def _format_table_row(cells: list[str]) -> str:
    return "| " + " | ".join(cells) + " |"


def _is_alignment_cell(cell: str) -> bool:
    return bool(re.fullmatch(r":?-{3,}:?", cell.strip()))


def _table_alignment_marker() -> str:
    align = json.loads(_OUTPUT_LAYOUT)["tables"]["cell"]["horizontal_alignment"]
    if align == "right":
        return "---:"
    if align == "center":
        return ":---:"
    return ":---"


def _normalized_table_row(cells: list[str], target_count: int) -> tuple[list[str], bool]:
    changed = False
    if len(cells) < target_count:
        cells = cells + [""] * (target_count - len(cells))
        changed = True
    elif len(cells) > target_count:
        cells = cells[:target_count - 1] + ["；".join(cells[target_count - 1:])]
        changed = True
    return cells, changed


def _repair_table_block(block: list[str], start_line: int) -> tuple[list[str], list[str]]:
    issues: list[str] = []
    rows = [_split_table_row(line) for line in block]
    if len(rows) < 2:
        return block, issues

    header = rows[0]
    separator = rows[1]
    data_rows = rows[2:]
    leading_alignment = []
    for cell in separator:
        if not _is_alignment_cell(cell):
            break
        leading_alignment.append(cell)
    separator_tail = separator[len(leading_alignment):]
    data_counts = [len(row) for row in data_rows if row]
    target_count = max(set(data_counts), key=data_counts.count) if data_counts else len(leading_alignment)

    if leading_alignment and separator_tail and len(header) + len(separator_tail) == len(leading_alignment):
        header = header + separator_tail
        separator = leading_alignment
        target_count = len(separator)
        issues.append(f"第 {start_line} 行附近表头被拆入对齐行，已合并为标准表头")
    elif not separator or not all(_is_alignment_cell(cell) for cell in separator):
        if target_count <= 0:
            return block, issues
        separator = [_table_alignment_marker()] * target_count
        issues.append(f"第 {start_line + 1} 行附近表格对齐行非法，已按布局规范重建")
    else:
        target_count = len(separator)

    header, changed = _normalized_table_row(header, target_count)
    if changed:
        issues.append(f"第 {start_line} 行附近表头列数与对齐行不一致，已修复")

    marker = _table_alignment_marker()
    separator = [cell if _is_alignment_cell(cell) else marker for cell in separator]
    separator, changed = _normalized_table_row(separator, target_count)
    if changed:
        separator = [marker] * target_count
        issues.append(f"第 {start_line + 1} 行附近对齐行列数与表头不一致，已修复")
    if any(cell != marker for cell in separator):
        separator = [marker] * target_count
        issues.append(f"第 {start_line + 1} 行附近表格对齐方式已按布局规范统一为居中")

    fixed_rows = [_format_table_row(header), _format_table_row(separator)]
    for offset, row in enumerate(data_rows, start=2):
        fixed_row, changed = _normalized_table_row(row, target_count)
        if changed:
            issues.append(f"第 {start_line + offset} 行附近数据行列数不一致，已修复")
        fixed_rows.append(_format_table_row(fixed_row))

    return fixed_rows, issues


def _has_table_caption(lines: list[str], index: int) -> bool:
    lo = json.loads(_OUTPUT_LAYOUT)
    prefix = re.escape(lo["tables"]["prefix"])
    caption_re = re.compile(
        rf'^\s*(?:\*\*)?\s*{prefix}\s*(?:[A-Z]?\d+|[A-Z])(?:[.\-]\d+)*\s*[：:].*(?:\*\*)?\s*$'
    )
    if index > 0 and caption_re.match(lines[index - 1]):
        return True
    if index > 1 and lines[index - 1].strip() == "" and caption_re.match(lines[index - 2]):
        return True
    return False


def _caption_text_from_heading(line: str) -> str:
    text = re.sub(r"^#{1,6}\s+", "", line).strip()
    text = re.sub(r"^(?:[一二三四五六七八九十]+、|\d+(?:\.\d+)*\s+)", "", text).strip()
    return text


def _infer_table_caption_text(lines: list[str], start: int) -> str:
    for offset in range(start - 1, max(-1, start - 12), -1):
        text = lines[offset].strip()
        if not text or _is_table_line(text):
            continue
        if re.match(r"^\s*(?:\*\*)?\s*表\s*(?:[A-Z]?\d+|[A-Z])(?:[.\-]\d+)*\s*[：:]", text):
            continue
        if re.match(r"^#{2,6}\s+", text):
            heading = _caption_text_from_heading(text)
            return f"{heading}表" if heading and not heading.endswith("表") else heading
        plain = re.sub(r"[*`_]+", "", text)
        plain = re.sub(r"^(?:如下|见下表|包括|包含)[：:，,]?\s*", "", plain).strip()
        if 4 <= len(plain) <= 40 and not plain.endswith(("。", "；", ";")):
            return f"{plain}表" if not plain.endswith("表") else plain
    return "相关信息表"


def _format_table_caption(caption_num: str, caption_text: str = "相关信息表") -> str:
    tbls = json.loads(_OUTPUT_LAYOUT)["tables"]
    parts = caption_num.replace(".", "-").split("-", 1)
    chapter = parts[0]
    number = parts[1] if len(parts) > 1 else "1"
    caption = tbls["caption_format"].format(
        prefix=tbls["prefix"],
        chapter=chapter,
        number=number,
        caption=caption_text,
    )
    return f"**{caption}**"


def _validate_table_captions(md_text: str) -> tuple[str, list[str]]:
    """修复 Markdown 表格结构，并补足缺失的表格标题。

    返回 (修正后的文本, 问题列表)。仅处理 fenced code 外部的表格。
    """
    import re as _re

    issues = []

    def _repair_part(part: str, line_offset: int) -> str:
        lines = part.split('\n')
        fixed_lines = []
        i = 0

        while i < len(lines):
            line = lines[i]
            if not _is_table_line(line):
                fixed_lines.append(line)
                i += 1
                continue

            start = i
            block = []
            while i < len(lines) and _is_table_line(lines[i]):
                block.append(lines[i])
                i += 1

            if len(block) < 2:
                fixed_lines.extend(block)
                continue

            if not _has_table_caption(lines, start):
                caption_num = _find_next_table_number(md_text, line_offset + start)
                caption_text = _infer_table_caption_text(lines, start)
                caption = _format_table_caption(caption_num, caption_text)
                issues.append(f"第 {line_offset + start + 1} 行附近的表格缺少标题，已自动补充 {caption}")
                fixed_lines.append(caption)
                fixed_lines.append("")

            repaired, block_issues = _repair_table_block(block, line_offset + start + 1)
            issues.extend(block_issues)
            fixed_lines.extend(repaired)

        return '\n'.join(fixed_lines)

    parts = _re.split(r'(```.*?```)', md_text, flags=_re.DOTALL)
    line_offset = 0
    for i, part in enumerate(parts):
        if i % 2 == 0:
            parts[i] = _repair_part(part, line_offset)
        line_offset += part.count("\n")

    return ''.join(parts), issues


def _find_next_table_number(md_text: str, up_to_line: int) -> str:
    """找出下一个可用的表号。"""
    import re as _re
    prefix = _re.escape(json.loads(_OUTPUT_LAYOUT)["tables"]["prefix"])
    prefix_length = sum(len(line) + 1 for line in md_text.split('\n')[:up_to_line])
    search_text = md_text[:prefix_length] if up_to_line > 0 else md_text
    existing = _re.findall(rf'\*\*{prefix}\s*((?:[A-Z]?\d+|[A-Z])(?:[.\-]\d+)*)\s*[：:]', search_text)
    if existing:
        last = existing[-1]
        # 尝试递增
        sep = '-' if '-' in last else '.'
        parts = last.replace('-', '.').split('.')
        try:
            parts[-1] = str(int(parts[-1]) + 1)
            return sep.join(parts)
        except ValueError:
            return f"{last}-1"
    return "1-1"


def _document_meta_fields() -> list[dict[str, str]]:
    fields = json.loads(_OUTPUT_LAYOUT).get("document_meta", {}).get("fields", [])
    return [field for field in fields if isinstance(field, dict) and field.get("key")]


def _document_title_for_type(doc_type: str) -> str:
    for doc in _OUTPUT_SCHEMA.get("documents", []):
        if doc.get("doc_type") == doc_type:
            return str(doc.get("structure", {}).get("title") or doc_type)
    return doc_type


def _default_meta_value(key: str, doc_type: str) -> str:
    doc_meta = json.loads(_OUTPUT_LAYOUT).get("document_meta", {})
    if key == "文档编号":
        document_numbers = doc_meta.get("document_numbers", {})
        if isinstance(document_numbers, dict) and doc_type in document_numbers:
            return str(document_numbers[doc_type])
    defaults = doc_meta.get("defaults", {})
    if isinstance(defaults, dict) and key in defaults:
        return str(defaults[key])
    for field in _document_meta_fields():
        if field.get("key") == key:
            return str(field.get("example", ""))
    return ""


def _metadata_line_value(line: str, key: str) -> Optional[str]:
    import re as _re

    escaped_key = _re.escape(key)
    patterns = (
        rf"^\s*\*\*\s*{escaped_key}\s*\*\*\s*[:\uff1a]\s*(?P<value>.*?)\s*$",
        rf"^\s*\*\*\s*{escaped_key}\s*[:\uff1a]\s*(?P<value>.*?)\s*\*\*\s*$",
        rf"^\s*{escaped_key}\s*[:\uff1a]\s*(?P<value>.*?)\s*$",
    )
    for pattern in patterns:
        match = _re.match(pattern, line)
        if match:
            return match.group("value").strip().strip("*").strip()
    return None


def _is_document_metadata_line(line: str) -> bool:
    return any(_metadata_line_value(line, field["key"]) is not None for field in _document_meta_fields())


def _extract_metadata_values(md_text: str, doc_type: str = "") -> dict[str, str]:
    values: dict[str, str] = {}
    for line in md_text.splitlines():
        for field in _document_meta_fields():
            key = field["key"]
            value = _metadata_line_value(line, key)
            if value is None:
                continue
            if value and not values.get(key):
                values[key] = value
            elif key not in values:
                values[key] = ""

    return {
        field["key"]: values.get(field["key"]) or _default_meta_value(field["key"], doc_type)
        for field in _document_meta_fields()
    }


def _remove_document_metadata_lines(md_text: str) -> str:
    return "\n".join(line for line in md_text.splitlines() if not _is_document_metadata_line(line))


def normalize_document_header(md_text: str, doc_type: str = "") -> str:
    """Ensure the document has exactly one H1 and one metadata block."""
    import re as _re

    title = _document_title_for_type(doc_type)
    metadata = _extract_metadata_values(md_text, doc_type)
    lines = _remove_document_metadata_lines(md_text).splitlines()
    body_lines = []
    first_title = ""
    for line in lines:
        match = _re.match(r"^#\s+(.+?)\s*$", line)
        if match:
            if not first_title:
                first_title = match.group(1).strip()
            continue
        body_lines.append(line)

    title = title or first_title or doc_type or "文档"
    meta_lines = [f"**{field['key']}**：{metadata[field['key']]}  " for field in _document_meta_fields()]
    body = "\n".join(body_lines).strip()
    return f"# {title}\n\n" + "\n".join(meta_lines) + "\n\n" + body + "\n"


def _extract_doc_info(md_text: str) -> dict:
    """从 Markdown 中提取元数据。字段名与 output_layout.json document_meta.fields 对齐。"""
    lo = json.loads(_OUTPUT_LAYOUT)
    prefix = lo.get("document_title", {}).get("prefix", "")
    meta_fields = lo.get("document_meta", {}).get("fields", [])

    info = {"project": prefix, "title": ""}
    for f in meta_fields:
        info[f["key"]] = ""

    import re as _re
    m = _re.search(r"^#\s+(.+)$", md_text, _re.MULTILINE)
    if m:
        info["title"] = m.group(1).strip()

    metadata = _extract_metadata_values(md_text)
    for f in meta_fields:
        key = f["key"]
        info[key] = metadata.get(key, "")

    return info


def _format_title_html(md_body: str, md_text: str, doc_info: dict | None = None) -> str:
    """将 H1 替换为居中标题块，元数据垂直排列，整体垂直水平居中并独立成页。
    若传入 doc_info 则直接使用，否则从 md_text 提取。"""
    lo = json.loads(_OUTPUT_LAYOUT)
    meta_fields = lo.get("document_meta", {}).get("fields", [])
    info = doc_info or _extract_doc_info(md_text)
    title = str(info["title"])
    prefix = str(info["project"])
    full_title = title if prefix and title.startswith(prefix) else f"{prefix}{title}"

    meta_lines = []
    for f in meta_fields:
        key = f["key"]
        val = html_module.escape(info.get(key, ""))
        meta_lines.append(f"<p>{key}：{val}</p>")

    title_block = f"""<div class="title-page-wrapper"><div class="doc-title">{html_module.escape(full_title)}</div>
<div class="doc-meta">
{chr(10).join(meta_lines)}
</div></div>"""

    import re as _re
    html_out = _re.sub(r"<h1[^>]*>.*?</h1>", title_block, md_body, count=1, flags=_re.DOTALL)
    # 清理标题页 wrapper 后多余的空 <p> 段落
    html_out = _re.sub(r'(<div class="title-page-wrapper">.*?</div>)\s*<p>\s*</p>\s*', r'\1', html_out, flags=_re.DOTALL)
    return html_out


def _center_captions(html_body: str) -> str:
    """仅将真正的图表标题居中，如「图1：...」「表 2-1 接口清单」。

    说明性正文（如「图2说明了...」「表6列出了...」）不应被当作 caption。
    Markdown 粗体标题会被转换成 <strong>表1：...</strong>，因此需要按去标签后的文本判断。
    """
    import re as _re
    lo = json.loads(_OUTPUT_LAYOUT)
    caption_font_sizes = {
        lo["figures"]["prefix"]: lo["figures"]["font_size"],
        lo["tables"]["prefix"]: lo["tables"]["font_size"],
    }

    prefix_pattern = "|".join(_re.escape(prefix) for prefix in caption_font_sizes)
    caption_pattern = _re.compile(
        rf"^({prefix_pattern})\s*(?P<num>(?:[A-Z]?\d+|[A-Z])(?:[-.]\d+)*)(?P<sep>[：:]|\s+)(?P<title>.+)$"
    )
    non_caption_starts = (
        "说明", "展示", "显示", "列出", "列举", "给出", "描述",
        "表示", "如下", "所示", "用于", "为",
    )

    def _is_caption(text: str) -> bool:
        normalized = _re.sub(r"\s+", " ", text).strip()
        match = caption_pattern.match(normalized)
        if not match:
            return False
        title = match.group("title").strip()
        if not title or len(title) > 120:
            return False
        if not match.group("sep").strip() and title.startswith(non_caption_starts):
            return False
        return True

    def _wrap(match):
        attrs = match.group(1) or ""
        inner = match.group(2)
        plain_text = html_module.unescape(_re.sub(r"<[^>]+>", "", inner)).strip()
        if not _is_caption(plain_text):
            return match.group(0)
        prefix = plain_text[:1]
        font_size = caption_font_sizes.get(prefix, lo["font"]["body_size"])

        if "style=" in attrs:
            attrs = _re.sub(
                r'style=(["\'])(.*?)\1',
                rf'style=\1\2;text-align:center;text-indent:0;font-size:{font_size}\1',
                attrs,
                count=1,
            )
            return f"<p{attrs}>{inner}</p>"
        return f'<p{attrs} style="text-align:center;text-indent:0;font-size:{font_size}">{inner}</p>'

    return _re.sub(r"<p([^>]*)>(.*?)</p>", _wrap, html_body, flags=_re.DOTALL)


def _center_bare_images(html_body: str) -> str:
    """将不在 figure-container 内的裸 <img> 所在段落居中。"""
    import re as _re

    def _fix(match):
        inner = match.group(2)
        if "<img" not in inner:
            return match.group(0)
        attrs = match.group(1) or ""
        attrs = _re.sub(r'text-indent:\s*[^;"]+;?', "", attrs)
        if "style=" in attrs:
            attrs = _re.sub(
                r'style=(["\'])(.*?)\1',
                r'style=\1\2;text-align:center;text-indent:0\1',
                attrs, count=1,
            )
            return f"<p{attrs}>{inner}</p>"
        return f'<p{attrs} style="text-align:center;text-indent:0">{inner}</p>'

    return _re.sub(r"<p([^>]*)>(.*?)</p>", _fix, html_body, flags=_re.DOTALL)


# ============================================================
# MD → PDF 转换
# ============================================================
def convert_to_pdf(md_path: str) -> str:
    """将 Markdown 文档转换为 PDF，应用排版规范。

    处理流程:
        1. 预处理 — Mermaid 代码块渲染为 PNG，清理 LLM 客套话
        2. MD → HTML — 使用 Python-Markdown 库
        3. 标题格式化 — 居中 + 项目名前缀 + 元数据
        4. HTML + CSS → PDF — 使用 Playwright (Chromium)

    Returns:
        PDF 文件路径（与源 .md 同目录）
    """
    import markdown as md_lib
    import re as _re

    md_file = Path(md_path)
    if not md_file.exists():
        raise FileNotFoundError(f"Markdown 文件不存在: {md_path}")

    md_text = md_file.read_text(encoding="utf-8")

    # ── 步骤1: 清理 + Mermaid + 列表修正 ──
    logger.info("  [PDF] 步骤1: 清理文本 + 渲染图表 + 修正列表...")
    md_text = _clean_boilerplate(md_text)
    # 先从原始 MD 提取元数据（删除前提取，否则 _extract_doc_info 读到空值）
    _doc_info = _extract_doc_info(md_text)
    # 在 MD 层面移除所有文档元数据行，标题页由 _format_title_html 统一生成。
    md_text = _remove_document_metadata_lines(md_text)
    md_text = normalize_heading_numbering(md_text)
    md_text = _fix_unordered_lists_in_md(md_text)
    md_text = _render_diagram_blocks_for_html(md_text)
    md_text, _table_issues = _validate_table_captions(md_text)

    # ── 步骤2: MD → HTML（先转义 UML 原型符号 <<...>>，防止被当作 HTML 标签）──
    logger.info("  [PDF] 步骤2: Markdown → HTML")
    md_text = _re.sub(
        r'<<(include|extend|uses|depends|refine|trace|implement|derive)>>',
        r'&lt;&lt;\1&gt;&gt;', md_text,
    )
    md_extensions = ["tables", "fenced_code", "codehilite", "toc", "attr_list"]
    md_body = md_lib.markdown(md_text, extensions=md_extensions)

    # ── 步骤3: 图片路径 + 标题格式化 + 图表标题居中 + 图片居中 ──
    logger.info("  [PDF] 步骤3: 格式化标题 + 图片路径 + 图表标题居中 + 图片居中")
    md_body = _embed_images_as_base64(md_body)
    md_body = _format_title_html(md_body, md_text, _doc_info)
    md_body = _center_captions(md_body)
    md_body = _center_bare_images(md_body)

    # ── 步骤4: CSS + 组装 HTML ──
    logger.info("  [PDF] 步骤4: 生成 CSS 并组装 HTML")
    css = _layout_css()

    html_full = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8"/>
<style>
{css}
</style>
</head>
<body>
{md_body}
</body>
</html>"""

    # ── 步骤5: Playwright 渲染 PDF ──
    logger.info("  [PDF] 步骤5: Playwright 渲染 PDF...")
    pdf_path = md_file.with_suffix(".pdf")

    try:
        from playwright.sync_api import sync_playwright
        lo = json.loads(_OUTPUT_LAYOUT)
        ps = lo.get("page_setup", {})
        pdf_cfg = lo["pdf_rendering"]

        with sync_playwright() as p:
            browser = p.chromium.launch()
            page = browser.new_page()
            page.set_content(html_full, timeout=30000)
            page.wait_for_timeout(500)
            page.pdf(
                path=str(pdf_path),
                format=ps["paper_size"],
                margin={
                    "top": ps["margin_top"],
                    "bottom": ps["margin_bottom"],
                    "left": ps["margin_left"],
                    "right": ps["margin_right"],
                },
                print_background=True,
                display_header_footer=True,
                header_template=pdf_cfg["pdf_header_template"],
                footer_template=pdf_cfg["pdf_footer_template"],
            )
            browser.close()
    except ImportError:
        raise RuntimeError(
            "PDF 转换需要 Playwright。安装步骤:\n"
            "  1. uv add playwright\n"
            "  2. .venv\\Scripts\\python.exe -m playwright install chromium"
        )

    logger.info(f"  [PDF] 完成 → {pdf_path}")
    return str(pdf_path)


def _embed_images_as_base64(html_text: str) -> str:
    """将 HTML 中的本地图片 src 转为 base64 data URI，避免 Chromium file:/// 路径问题。"""
    import re as _re

    _MIME_MAP = {
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".gif": "image/gif",
        ".svg": "image/svg+xml",
        ".webp": "image/webp",
    }

    def _to_data_uri(match):
        src = match.group(1)
        if src.startswith(("http", "https", "data:")):
            return match.group(0)
        p = Path(src)
        if not p.is_absolute():
            p = (OUTPUT_DIR / src).resolve()
        if not p.exists():
            return match.group(0)
        try:
            img_bytes = p.read_bytes()
            b64 = base64.b64encode(img_bytes).decode()
            mime = _MIME_MAP.get(p.suffix.lower(), "image/png")
            return f'src="data:{mime};base64,{b64}"'
        except Exception:
            return match.group(0)

    return _re.sub(r'src="(.*?)"', _to_data_uri, html_text)
