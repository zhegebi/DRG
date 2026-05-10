# docgen_agent — 文档自动生成智能体

基于大模型的软件工程文档自动生成系统。根据项目需求描述、文档结构规范(`output_schema.json`)和排版布局规范(`output_layout.json`)，自动生成符合 IEEE 830 / IEEE 1016 / IEEE 829 标准的专业文档。生成文档可能需要40分钟。

## 目录结构

```
docgen_agent/
├── workflow.py          # 智能体主循环：分批逐节生成 + 拼接 + 格式校验
├── tools.py             # 工具定义与实现（文件读取、联网搜索、文档保存、转换接口）
├── api.py               # [上层] FastAPI 路由，接收前端提示词和文件上传
├── output_schema.json   # 文档结构规范（章节树、required 标记、tips、图表要求）
├── output_layout.json   # 排版布局规范（页边距、字体、标题层级、图表 caption 格式）
├── requirement.md       # 默认项目需求输入
├── output_docs/         # 输出目录（.md 文档 + 渲染图表）
└── README.md            # 本文件
```

## 文件功能说明

### workflow.py — 智能体主循环

核心编排逻辑，分 5 个阶段：

| 阶段 | 说明 |
|------|------|
| Phase 1 读取文件 | Agent 方式调用 `read_requirement` / `read_output_schema` / `read_output_layout` |
| Phase 2 拆解章节 | 将 `output_schema.json` 中的文档结构展开为扁平的 (子)节列表 |
| Phase 3 逐节生成 | 每个节独立调用 LLM，上下文包含需求摘要 + schema 定义 + 排版规范 + 前后节衔接 |
| Phase 4 拼接校验 | 合并全文 → LLM 审校标题编号、图表编号、格式一致性 |
| Phase 5 保存 | 写入 `output_docs/{doc_type}_{timestamp}.md` |

关键函数：
- `run_agent(doc_type, user_hint, source_file)` — 主入口
- `_phase_read_files(doc_type)` — Agent 工具调用循环
- `_generate_section(section_info, ...)` — 单节 LLM 生成

### tools.py — 工具定义与实现

为 LLM Agent 提供可调用的工具函数：

| 工具 | 函数 | 说明 |
|------|------|------|
| `read_requirement` | `execute_tool("read_requirement", ...)` | 读取需求源文件（由前端上传或默认 requirement.md） |
| `read_output_schema` | `execute_tool("read_output_schema", ...)` | 读取文档结构规范，支持 `doc_type` 参数裁剪 |
| `read_output_layout` | `execute_tool("read_output_layout", ...)` | 读取排版规范 |
| `save_document` | `execute_tool("save_document", ...)` | 保存 Markdown 到 `output_docs/` |
| `search_web` | `execute_tool("search_web", ...)` | 联网搜索（DuckDuckGo API），补充领域知识 |

转换接口（预留，待后续实现）：
- `convert_to_pdf(md_path)` — Markdown → PDF
- `convert_to_docx(md_path)` — Markdown → DOCX
- `convert_to_txt(md_path)` — Markdown → 纯文本

辅助函数：
- `set_source_file(path)` — 切换需求源文件
- `get_doc_structure(doc_type)` — 获取文档类型结构定义
- `flatten_sections(doc_type)` — 展开章节树为扁平列表

### api.py — 前端接口

FastAPI 路由（挂载在 `server/main.py`）：

| 方法 | 路径 | 说明 |
|------|------|------|
| `POST` | `/api/agent/generate-doc` | 生成文档，接收 `prompt`(str) + `doc_type`(str) + `source_file`(txt/md) |
| `GET` | `/api/agent/doc-types` | 返回支持的文档类型列表 |

### output_schema.json — 文档结构规范

定义三类文档的完整章节树：
- **需求规格说明书**（参考 IEEE 830）— 引言 → 总体描述 → 具体需求 → 附录
- **架构设计文档**（参考 IEEE 1016）— 引言 → 总体结构 → 模块详细设计 → 数据设计 → 技术选型 → 部署视图
- **测试文档**（参考 IEEE 829）— 引言 → 测试策略 → 测试环境与工具 → 测试用例设计 → 测试执行计划

每个章节节点包含：`level`（标题层级）、`required`（是否必须）、`tips`（写作提示）、`diagram`（是否需要图表）、`children`（子章节）。

### output_layout.json — 排版布局规范

定义渲染参数：A4 页面、2.54cm/3.17cm 页边距、宋体/黑体字体、四级标题字号（18/16/14/12pt）、图表 caption 格式、表格单元格对齐。

## 使用方式

### 命令行直接运行

```bash
# 默认生成需求规格说明书
python -m server.agent.docgen_agent.workflow

# 或在代码中指定类型
python -c "
from server.agent.docgen_agent.workflow import run_agent
run_agent('架构设计文档', '侧重微服务架构设计')
"
```

### 前端 API 调用

```bash
# 无上传文件（使用默认 requirement.md）
curl -X POST http://localhost:8000/api/agent/generate-doc \
  -F "prompt=请重点关注 DRG 入组流程" \
  -F "doc_type=需求规格说明书"

# 上传自定义需求文件
curl -X POST http://localhost:8000/api/agent/generate-doc \
  -F "prompt=生成一份完整的架构设计文档" \
  -F "doc_type=架构设计文档" \
  -F "source_file=@/path/to/requirements.txt"
```

## 依赖

- `openai` — DeepSeek API 调用
- `loguru` — 日志
- `fastapi` + `python-multipart` — Web API
- `requests` — 联网搜索

## 后续扩展

- [ ] `convert_to_pdf()` — 使用 `fpdf2` + `markdown` 或 `weasyprint`
- [ ] `convert_to_docx()` — 使用 `python-docx`
- [ ] `convert_to_txt()` — 移除 Markdown 标记
- [ ] 流式输出 SSE（Server-Sent Events）推送生成进度
- [ ] 批量生成三种文档
