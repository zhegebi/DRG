# TOOLS_INSTRUCTION — 工具实现原理与作用

## 架构概览

```
┌──────────────────────────────────────────────────────┐
│ workflow.py (主循环)                                  │
│                                                       │
│  Phase 1: 读取文件  → LLM 调用 read_* 工具            │
│  Phase 2: 拆解章节  → flatten_sections()              │
│  Phase 3: 逐节生成  → LLM 调用 render_*/search_web    │
│  Phase 3.5: Schema校验 → 缺失章节重生成                │
│  Phase 4: 拼接校验  → LLM 审校全文 + 封面小组信息      │
│  Phase 5: 保存 MD   → save_document + 列表修正安全网   │
│  Phase 6: 转 PDF    → convert_to_pdf                  │
└──────────────────────────────────────────────────────┘
```

工具按阶段分配（`get_tools_for_phase`）：

| 阶段 | 工具 |
|------|------|
| `read` | read_requirement, read_output_schema, read_output_layout, search_web, 9 个细粒度项目分析工具 + 2 个聚合上下文工具 |
| `write` | search_web, render_mermaid, render_plantuml, save_document |

## LLM 对话循环 (`_call_llm`)

```
client.chat.completions.create(tools=..., messages=...)
  → LLM 返回 text + tool_calls[]
    → execute_tool(name, arguments) 通过静态 _TOOL_HANDLERS 分发
      → 追加 tool 消息到 messages
        → 继续下一轮（最多 15 轮）
```

每轮调用前后检查中断/终止标志。

---

## 一、资料读取工具

### read_requirement
返回当前运行的 ContextVar 需求内容，默认读取 `agent_input/requirement.md`，可通过 `set_source_files()` 在运行时切换为前端上传的多个需求/依赖文件。`SECTION_SYSTEM_PROMPT` 将需求摘要和读取阶段得到的项目上下文共同注入每章节上下文。

### read_output_schema
预加载 `agent_input/output_schema.json`，按 `doc_type` 裁剪后返回。仅保留目标文档的 `selected_document` 节点，去除其他文档类型。

### read_output_layout
直接返回 `agent_input/output_layout.json` 原文，包含页面、字体、标题、图表、表格、代码块、列表、分页等全部排版规则。

---

## 二、项目分析工具

所有工具共享安全约束：
- `_resolve_project_path()` 用 `Path.relative_to()` 防越权
- 自动忽略 `.git`、`.venv`、`node_modules`、`output_docs` 等
- 非文本文件跳过（`_is_text_file()` 按扩展名判断）

| 工具 | 实现 | 用途 |
|------|------|------|
| `list_project_files` | `rglob("*")` 遍历，按 ignore/pattern 过滤 | 项目目录树 |
| `read_project_file` | `Path.read_text(utf-8)`，超 20000 字符截断 | 读取源码/配置 |
| `search_project` | 逐行正则匹配，结果上限 80 条 | 搜索符号/路由 |
| `read_dependency_manifest` | tomllib/json 解析 pyproject.toml/package.json | 依赖清单 |
| `read_api_routes` | 正则匹配 `@router.get("/path")` + `APIRouter(prefix)` | API 路由汇总 |
| `read_data_models` | 正则匹配 `class Xxx(SQLModel/BaseModel)` + 字段声明 | 数据模型 |
| `read_deployment_config` | 扫描 Dockerfile/docker-compose/.env/k8s/nginx | 部署配置 |
| `read_existing_tests` | 扫描 tests/，提取 `def test_xxx` | 测试文件 |
| `read_ci_config` | 扫描 .github/workflows、.gitlab-ci.yml、tox.ini | CI/CD 配置 |
| `read_architecture_context` | 聚合目录、依赖、路由、模型、部署配置和推荐图表 | 架构设计文档上下文 |
| `read_test_context` | 聚合接口、模型、现有测试、CI、候选命令和风险区域 | 测试文档上下文 |

---

## 三、联网搜索 (`search_web`)

调用 DuckDuckGo Instant Answer API：
```
GET https://api.duckduckgo.com/?q=...&format=json&no_html=1
```
返回摘要 + 最多 5 条 RelatedTopics。超时 15s，失败则返回错误信息让 LLM 用已有知识继续。

---

## 四、图片渲染

### Mermaid 渲染 (`render_mermaid` → `_render_mermaid_to_file`)

```
Mermaid 源码
  → json.dumps({"code": "...", "mermaid": {"theme": "default"}})
    → base64url 编码
      → GET https://mermaid.ink/img/{encoded}?type=png
        → 校验 Content-Type 含 "image"
          → 写入 output_docs/diagrams/{name}.png
            → 返回 "diagrams/{name}.png"
```

`?type=png` 必不可少——mermaid.ink 的 `/img/` 端点默认返回 JPEG。

### PlantUML 渲染 (`render_plantuml` → `_render_plantuml_to_file`)

```
PlantUML 源码 (@startuml...@enduml)
  → UTF-8 编码
    → zlib deflate 压缩 (level 9)
      → 去 zlib header (2B) + Adler-32 checksum (4B)
        → 标准 base64 编码
          → 字母表映射: 标准 → PlantUML 专用
            → GET https://www.plantuml.com/plantuml/png/{encoded}
              → 写入 output_docs/diagrams/{name}.png
                → 返回 "diagrams/{name}.png"
```

PlantUML 自定义 base64 字母表（与标准完全不同）：

```
标准: ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/
PUML: 0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz-_
```

通过 `str.maketrans` 做完整映射，不可简单 `+→-` `/→_` 替换。

### 图片路径设计

两个工具都返回相对于 `output_docs/` 的路径（如 `diagrams/use_case.png`）。LLM 直接用于 `![标题](返回值)`，无需拼接。

### 代码块 → 图片 (`_render_diagram_blocks_for_html`)

PDF 转换时处理 LLM 未通过工具渲染而直接留下的 ` ```mermaid ` / ` ```plantuml ` 代码块：

```python
regex: ```(mermaid|plantuml)\n(code)```
  → 调用对应渲染函数
    → 成功 → 读 PNG → base64 → <img src="data:image/png;base64,...">
    → 失败 → <pre><code> 转义展示源码
```

---

## 五、PDF 转换 (`convert_to_pdf`)

### 5 步流程

```
步骤 1: 预处理
  ├── _clean_boilerplate()          → 清除 LLM 客套话
  ├── _fix_unordered_lists_in_md()  → -   → (1)(2)(3)
  ├── _validate_table_captions()    → 补缺失表头
  └── _render_diagram_blocks_for_html() → mermaid/plantuml → base64

步骤 2: Markdown → HTML
  └── markdown.markdown(tables, fenced_code, codehilite, toc)

步骤 3: HTML 后处理
  ├── _embed_images_as_base64() → 本地 <img src> → data:image/...;base64
  ├── _format_title_html()      → H1 → 居中标题 + 封面小组信息
  ├── _center_captions()        → 图N/表N 标题居中
  └── _center_bare_images()     → 裸 <img> 段落居中

步骤 4: 组装 HTML
  └── _layout_css() → 从 output_layout.json 生成完整打印 CSS
      → <!DOCTYPE html> + <style> + <body>

步骤 5: Playwright 渲染 PDF
  └── chromium.launch() → set_content → page.pdf(page_setup.paper_size, page_setup.margins)
```

### `_embed_images_as_base64`

将所有本地 `<img src="...">` 转为 `data:image/...;base64,...`。跳过 `http`/`https`/`data:` 开头的 src。路径解析相对于 `OUTPUT_DIR`。避免 Chromium `file:///` 中文路径问题。

### `_center_captions`

按 `output_layout.json` 中的图表前缀匹配章节标题格式，注入居中样式：

```
^(图|表)\s*(?P<num>[A-Z]?\d*(?:[-.]\d+)?)(?P<sep>[：:]|\s+)(?P<title>.+)$
```

支持 `图2-1`、`表3-2`、`表A-1` 等章节编号。排除说明性正文（如"图2说明了..."）。

### `_center_bare_images`

检测含 `<img>` 的 `<p>` 标签（来自 Markdown `![alt](path)`），注入 `text-align:center;text-indent:0`。

### `_format_title_html`

按 `output_layout.json` 的 `document_meta.fields` 模板生成标题页：
- 替换 H1 为 `<div class="doc-title">` 居中标题
- 按 fields 顺序垂直生成封面小组信息行：班级、组长、组员、日期
- `.doc-meta` CSS 含 `page-break-after: always` 实现标题独立成页
- 自动删除 LLM 正文中重复的封面信息行，并兼容清理旧版文档编号/版本号等字段

### `_layout_css`

完全由 `output_layout.json` 驱动，无硬编码。读取所有配置节后拼接 CSS：

| JSON 节 | 生成的 CSS |
|---------|-----------|
| `page_setup` | `@page { size; margins }` |
| `font` | `body { font-family; font-size }` |
| `headings` | `h1-h5 { font-size; font-weight; alignment }` |
| `body_text` | `p { text-indent; line-height }` |
| `figures` | `figure/.figure-container { text-align; margin }` |
| `tables` | `table/th/td { border; padding; text-align }` + `td.cell-text` |
| `code_blocks` | `pre/code { font-family; background }` |
| `lists` | `ul/ol/li { margin; padding }` |
| `page_breaks` | `h2 { page-break-before: always }` |
| `pdf_rendering` | 图片高度、表格外边距、页眉页脚模板等 PDF 渲染细节 |

全局 `img` 约束、figure 图片约束、页脚模板等均从 `pdf_rendering` 读取。

---

## 六、文本清理

### `_clean_boilerplate`

正则剔除 LLM 客套话（"好的，我这就为您生成..."等），模式定义在 `output_layout.json` 的 `boilerplate_rules`。

### `_fix_unordered_lists_in_md`

安全网：将代码块外的 `- ` 行转为 `(1)(2)(3)...` 有序编号。在 Phase 5 保存 MD 和 Phase 6 转 PDF 前各执行一次。

### `_validate_table_captions`

扫描 `|...|` 表格行，检查前面是否有 `**表N：...**` 标题。缺失则自动补 `**表N：表格说明**`。

---

## 七、路径安全

```python
def _resolve_project_path(path):
    target = (PROJECT_ROOT / path).resolve()
    target.relative_to(PROJECT_ROOT.resolve())  # 越权抛 ValueError
    return target
```

`OUTPUT_DIR` 和 `DIAGRAM_DIR` 在模块加载时自动创建。

---

## 八、关键函数索引

| 函数 | 文件:行 | 作用 |
|------|---------|------|
| `_render_mermaid_to_file` | tools.py:799 | Mermaid → mermaid.ink → PNG |
| `_render_plantuml_to_file` | tools.py:830 | PlantUML → plantuml.com → PNG |
| `_render_diagram_blocks_for_html` | tools.py:875 | `mermaid/plantuml 代码块 → base64 <img>` |
| `_embed_images_as_base64` | tools.py:1482 | 本地图片 → data URI |
| `_center_captions` | tools.py:1337 | 图/表标题居中 |
| `_center_bare_images` | tools.py:1386 | 裸 `<img>` 段落居中 |
| `_format_title_html` | tools.py:1305 | 标题页 + 封面小组信息 |
| `_layout_css` | tools.py:920 | JSON → 打印 CSS |
| `_clean_boilerplate` | tools.py:1141 | 清除客套话 |
| `_fix_unordered_lists_in_md` | tools.py:1148 | `- ` → `(N) ` |
| `_validate_table_captions` | tools.py:1186 | 补缺失表头 |
| `_flatten_required_sections` | workflow.py:624 | 展平 schema 必需章节 |
| `_generate_section_group` | workflow.py:580 | LLM 生成单个章节组 |
| `convert_to_pdf` | tools.py:1406 | MD → HTML → PDF 全流程 |
