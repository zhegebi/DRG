# TOOLS_INSTRUCTION — 工具实现原理与作用

## 架构概览

```
┌──────────────────────────────────────────────────────────────────┐
│ workflow.py (主循环)                                              │
│                                                                   │
│  Phase 1: 读取文件  → LLM 调用 read_* 工具 (asyncio.gather 并行) │
│  Phase 2: 拆解章节  → flatten_sections()                          │
│  Phase 3: 逐节生成  → LLM 调用 render_*/search_web                │
│  Phase 3.5: Schema校验 → 缺失章节重生成                            │
│  Phase 4: 拼接校验  → asyncio.to_thread(规范化)                    │
│  Phase 5: 保存 MD   → asyncio.to_thread(格式化+保存)               │
│  Phase 6: 预处理 HTML → asyncio.to_thread(build_document_html)     │
└──────────────────────────────────────────────────────────────────┘
```

工具按阶段分配（`get_tools_for_phase`）：

| 阶段 | 工具 |
|------|------|
| `read` | read_requirement, read_output_schema, read_output_layout, search_web, 9 个细粒度项目分析工具 + 2 个聚合上下文工具 |
| `write` | search_web, render_mermaid, render_plantuml, save_document |

## 工具异步执行模型

所有工具通过 `execute_tool_async()` 统一调度：

```python
async def execute_tool_async(name, arguments):
    handler = _TOOL_HANDLERS.get(name)
    if asyncio.iscoroutinefunction(handler):
        return await handler(arguments)           # 异步工具: 原生 await
    return await asyncio.to_thread(handler, arguments)  # 同步工具: 线程池
```

| 工具类型 | 示例 | 执行位置 |
|---------|------|---------|
| 异步 | `search_web` (httpx.AsyncClient) | 事件循环 |
| 同步 — 纯内存 | `read_requirement` (ContextVar), `read_output_schema` (JSON) | 线程池（轻量，几乎无开销） |
| 同步 — 文件 I/O | `list_project_files`, `read_project_file`, `save_document` | 线程池 |
| 同步 — HTTP | `render_mermaid` (requests.get), `render_plantuml` (requests.get) | 线程池 |
| 同步 — 计算密集 | `build_document_html` (正则+Markdown→HTML+base64), 文档规范化 | 线程池 |

**关键原则**: 同步阻塞操作必须通过 `asyncio.to_thread()` 移出事件循环线程，避免冻结所有并发协程。详见 [ASYNC_CONCURRENCY.md](./ASYNC_CONCURRENCY.md)。

## LLM 对话循环 (`_call_llm`)

```
client.chat.completions.create(stream=True, tools=..., messages=...)
  → async for chunk in stream:                    ← 事件循环中异步流式读取
    → 累积 reasoning/content/tool_call delta      ← 每个 chunk 检查 _check_terminated()
      → 若有 tool_calls:
        → asyncio.gather(*(execute_tool_async()))  ← 并行执行所有工具
          → 追加 tool 消息到 messages
            → 继续下一轮（最多 15 轮）
```

每轮调用前后检查中断/终止标志。工具调用通过 `asyncio.gather` 并行执行——当 LLM 在一次响应中返回多个 tool_call 时，所有工具同时启动。

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

## 五、预处理 HTML (`convert_to_pdf`)

### 4 步流程（PDF 由前端浏览器原生打印）

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
      → 前端 PrintPage 拉取后通过浏览器 "另存为 PDF" 渲染
```

### `_embed_images_as_base64`

将所有本地 `<img src="...">` 转为 `data:image/...;base64,...`。跳过 `http`/`https`/`data:` 开头的 src。路径解析相对于 `OUTPUT_DIR`，避免本地路径和中文路径兼容问题。

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
| `pdf_rendering` | 图片高度、表格外边距等 PDF 渲染细节 |

全局 `img` 约束、figure 图片约束等均从 `pdf_rendering` 读取；页码由生成的 `@page @bottom-center` CSS 渲染。

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

| 函数 | 文件:行 | 作用 | 执行模式 |
|------|---------|------|---------|
| `execute_tool_async` | tools.py:725 | 统一工具调度：async→await，sync→to_thread | 事件循环 + 线程池 |
| `_stream_chat_completion` | workflow.py:344 | 流式 LLM 调用 + trace 实时推送 | 事件循环 (async for) |
| `_call_llm` | workflow.py:793 | LLM 对话循环 (max 15 turns) | 事件循环 |
| `_phase_read_files` | workflow.py:643 | Phase 1: 读取需求/结构/布局/项目上下文 | 事件循环 + asyncio.gather |
| `_generate_section_group` | workflow.py:899 | Phase 3: LLM 生成单个章节组 | 事件循环 |
| `_save_and_convert_document` | workflow.py:1068 | Phase 5-6: 格式化→保存→HTML | 线程池 (to_thread) |
| `_render_mermaid_to_file` | tools.py:1255 | Mermaid → mermaid.ink → PNG | 线程池 (via to_thread) |
| `_render_plantuml_to_file` | tools.py:1298 | PlantUML → plantuml.com → PNG | 线程池 (via to_thread) |
| `_render_diagram_blocks_for_html` | tools.py:1341 | mermaid/plantuml 代码块 → base64 img | 线程池 (via to_thread) |
| `_embed_images_as_base64` | tools.py:2847 | 本地图片 → data URI | 线程池 (via to_thread) |
| `_center_captions` | tools.py:2650 | 图/表标题居中 | 线程池 (via to_thread) |
| `_center_bare_images` | tools.py:2733 | 裸 img 段落居中 | 线程池 (via to_thread) |
| `_format_title_html` | tools.py:2620 | 标题页 + 封面小组信息 | 线程池 (via to_thread) |
| `_layout_css` | tools.py:1374 | JSON → 打印 CSS | 线程池 (via to_thread) |
| `_clean_boilerplate` | tools.py:1639 | 清除客套话 | 线程池 (via to_thread) |
| `_fix_unordered_lists_in_md` | tools.py:1648 | `- ` → `(N) ` | 线程池 (via to_thread) |
| `_validate_table_captions` | tools.py:2351 | 补缺失表头 | 线程池 (via to_thread) |
| `normalize_caption_positions_and_numbering` | tools.py:1909 | 图表 caption 按章重编号 | 线程池 (via to_thread) |
| `normalize_heading_numbering` | tools.py:2143 | 标题编号规范化 | 线程池 (via to_thread) |
| `normalize_document_header` | tools.py:2564 | 文档 H1 + 封面信息标准化 | 线程池 (via to_thread) |
| `convert_to_pdf` | tools.py:2826 | MD → HTML 预处理（PDF 由前端打印） | 线程池 (via to_thread) |
| `_check_terminated` | workflow.py:483 | 终止标志检查点 (27 处) | 事件循环 |
| `request_generation_terminate` | workflow.py:192 | 设置终止标志 + 关闭 LLM 流 | 事件循环 |
| `terminate_stale_tasks_on_startup` | api.py:57 | 启动时清理残留 running 任务 | 事件循环 (lifespan) |
| `_persist_trace_sync` | api.py:279 | trace 写 DB | 线程池 (via to_thread) |
