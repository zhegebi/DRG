# docgen_agent — 文档自动生成智能体

基于大模型的软件工程文档自动生成系统。读取项目需求、`output_schema.json`（文档结构）和 `output_layout.json`（排版规范），生成符合 IEEE 830 / 1016 / 829 风格的需求规格说明书、架构设计文档和测试文档。

**核心设计原则**：所有格式与排版规范集中在配置文件（JSON）中，提示词（prompt）仅做补充说明，不重复或覆盖配置中的规则。

## 目录结构

```text
docgen_agent/
├── workflow.py            # 主循环: Phase 1→6 (读取→拆章→生成→校验→拼接→PDF)
├── tools.py               # 工具定义、实现、渲染、CSS、PDF 转换
├── api.py                 # FastAPI 路由 (同步/后台生成、trace、中断、下载)
├── output_schema.json     # 文档结构: 章节树、required/tips/diagram、UML 语法指南
├── output_layout.json     # 排版唯一来源: 页面、字体、标题、图表、表格、列表
├── requirement.md         # 默认需求输入
├── output_docs/           # 输出目录
│   ├── diagrams/          # 渲染后的图片 (PNG)
│   └── *.md / *.pdf       # 生成的文档
├── README.md
└── TOOLS_INSTRUCTION.md   # 工具实现原理详解
```

## 生成流程

| Phase | 名称 | 说明 |
|-------|------|------|
| 1 | 读取文件 | LLM 调用 read_requirement / read_output_schema / read_output_layout |
| 2 | 拆解章节 | 按 schema 展开一级章节列表 |
| 3 | 逐节生成 | 每个一级章节组独立生成，LLM 可调用 render_* / search_web |
| 3.5 | Schema 校验 | 检查 required 章节是否都存在，缺失则重新生成 (最多 2 轮) |
| 4 | 拼接校验 | LLM 审校全文格式、编号、图表标题，添加文档元数据 |
| 5 | 保存 MD | 列表修正安全网 + 保存 Markdown |
| 6 | 转 PDF | 清理 → 图表渲染 → Markdown→HTML → base64 嵌入 → Playwright 渲染 |

## 支持文档

| doc_type | 参考标准 | 内容 |
|----------|---------|------|
| `需求规格说明书` | IEEE 830 | 功能需求、非功能需求、接口需求、约束和附录 |
| `架构设计文档` | IEEE 1016 | 系统上下文、组件结构、模块详细设计、数据设计、部署视图 |
| `测试文档` | IEEE 829 | 测试策略、测试环境、测试用例设计、测试执行计划 |

## 配置驱动

所有视觉格式由 `output_layout.json` 统一定义，CSS 生成和 LLM 提示词均从此读取，不硬编码。

| 配置节 | 控制内容 |
|--------|---------|
| `page_setup` | A4 纸张、四边页边距 |
| `font` | 正文(SimSun)、标题(SimHei)、等宽(Consolas) 及 fallback |
| `headings` | 5 级标题的 HTML 标签、编号样式、字号、对齐 |
| `body_text` | 两端对齐、首行缩进 2em、1.25 倍行距 |
| `document_title` | 项目名前缀 + 文档名、22pt 居中 |
| `document_meta` | 模板化元数据字段 (文档编号/版本号/编制日期/文档状态) |
| `figures` | 图标题格式 `图{章}-{序号}：{caption}`、按章编号、强制标题 |
| `tables` | 表标题在表上方、按章编号、单元格居中、长文本缩进 |
| `lists` | 无序列表禁用 (`allow_unordered: false`) |
| `page_breaks` | 一级章节前分页 |

改 `output_layout.json` 即改全局排版，无需改动代码或提示词。

## 图片处理

### 渲染方式

| 图表类型 | 工具 | 服务 |
|---------|------|------|
| 用例图 | `render_plantuml` | plantuml.com (deflate + PlantUML base64) |
| 其他 UML | `render_mermaid` | mermaid.ink (`?type=png` → PNG) |

### PDF 嵌入

Markdown 中的 `![图](diagrams/xxx.png)` 和 ` ```mermaid/plantuml ``` ` 代码块在 PDF 转换时统一转为 `data:image/png;base64,...`，图片完全内嵌，无外部依赖。

## 工具列表

| 工具 | 阶段 | 说明 |
|------|------|------|
| `read_requirement` | read | 读取需求源文件 |
| `read_output_schema` | read | 读取文档结构 (按 doc_type 裁剪) |
| `read_output_layout` | read | 读取排版规范 |
| `search_web` | read/write | DuckDuckGo 搜索 |
| `render_mermaid` | write | Mermaid → PNG (mermaid.ink) |
| `render_plantuml` | write | PlantUML → PNG (plantuml.com) |
| `save_document` | write | 保存 Markdown |
| 9 个项目分析工具 | read | 文件树、源码、路由、模型、部署、测试、CI |
| `convert_to_pdf` | convert | MD → HTML → PDF |

## 命令行

```powershell
# 默认生成需求规格说明书
uv run python -m server.agent.docgen_agent.workflow

# 指定类型
uv run python -c "from server.agent.docgen_agent.workflow import run_agent; run_agent(doc_type='架构设计文档')"

# 首次使用需安装 Playwright 浏览器
uv run python -m playwright install chromium
```

输出: `output_docs/{doc_type}_{timestamp}.md` + `.pdf`

## 前端 API

路由前缀 `/api/agent`，挂载在 `server/main.py`。

### 同步生成

```bash
curl -X POST http://localhost:8000/api/agent/generate-doc \
  -F "prompt=..." -F "doc_type=需求规格说明书"
```

### 后台生成 (推荐)

```bash
curl -X POST http://localhost:8000/api/agent/generate-doc/start \
  -F "prompt=..." -F "doc_type=需求规格说明书"
# → {"status": "started", "run_id": "..."}
```

### trace / 控制 / 下载

```bash
GET  /api/agent/runs/{run_id}/trace       # 轮询进度
POST /api/agent/runs/{run_id}/interrupt    # 协作式中断
POST /api/agent/runs/{run_id}/terminate    # 协作式终止
GET  /api/agent/runs/{run_id}/download     # 下载 MD
GET  /api/agent/documents/{name}/download  # 按文件名下载
GET  /api/agent/doc-types                  # 文档类型列表
```

## 依赖

| 依赖 | 用途 |
|------|------|
| `openai` | DeepSeek API 调用 |
| `fastapi` | 前端 API |
| `loguru` | 日志 |
| `markdown` | MD → HTML |
| `playwright` | Chromium 渲染 HTML → PDF |
| `requests` | 搜索 + Mermaid/PlantUML 渲染 |
