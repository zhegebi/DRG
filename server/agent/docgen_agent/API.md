# api.py — 前端接口文档

路由前缀 `/api/agent`，挂载在 `server/main.py`。

## 端点一览

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/generate-doc` | 同步生成文档 |
| POST | `/generate-doc/start` | 后台生成 (推荐) |
| GET | `/runs/{run_id}/trace` | 读取生成过程 |
| POST | `/runs/{run_id}/interrupt` | 协作式中断 |
| POST | `/runs/{run_id}/terminate` | 协作式终止 |
| GET | `/runs/{run_id}/download` | 下载最终 Markdown |
| GET | `/documents/{file_name}/download` | 按文件名下载 |
| GET | `/doc-types` | 支持的文档类型 |

---

## POST /generate-doc (同步)

等待生成完成后返回结果。适合调试，不建议前端长时间阻塞。

### 请求 (multipart/form-data)

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `prompt` | string | 否 | 用户提示词，默认空 |
| `doc_type` | string | 否 | `需求规格说明书` / `架构设计文档` / `测试文档`，默认需求 |
| `source_file` | file | 否 | 上传 .txt/.md 需求文件，不传则用 requirement.md |
| `run_id` | string | 否 | 运行 ID，不传则自动生成 |

```bash
curl -X POST http://localhost:8000/api/agent/generate-doc \
  -F "prompt=请重点关注模块划分" \
  -F "doc_type=架构设计文档"
```

### 响应

```json
{
  "status": "success",
  "run_id": "a1b2c3...",
  "file_name": "架构设计文档_20260517_120000.md",
  "file_path": "server/agent/docgen_agent/output_docs/架构设计文档_20260517_120000.md",
  "doc_type": "架构设计文档"
}
```

错误状态: `"terminated"` (被终止)、`"interrupted"` (被中断)，HTTP 500 为异常。

---

## POST /generate-doc/start (后台, 推荐)

立即返回 `run_id`，后端通过 `BackgroundTasks` 异步执行。前端用 trace 接口轮询进度。

### 请求

同 `/generate-doc`。

### 响应

```json
{
  "status": "started",
  "run_id": "a1b2c3...",
  "doc_type": "架构设计文档"
}
```

### 上传需求文件

```bash
curl -X POST http://localhost:8000/api/agent/generate-doc/start \
  -F "prompt=请生成测试文档" \
  -F "doc_type=测试文档" \
  -F "source_file=@/path/to/requirements.md"
```

上传文件保存到系统临时目录 `drg_docgen_uploads/`，仅允许 `.txt` / `.md`。

---

## GET /runs/{run_id}/trace

轮询生成过程，前端可增量渲染思考、工具调用和阶段进度。

### 响应

```json
{
  "run_id": "a1b2c3...",
  "status": "running",
  "doc_type": "需求规格说明书",
  "created_at": "2026-05-17T12:00:00",
  "updated_at": "2026-05-17T12:25:00",
  "output_path": null,
  "error": null,
  "interrupted": false,
  "terminated": false,
  "events": [
    {
      "id": 1,
      "time": "2026-05-17T12:00:01",
      "type": "phase_started",
      "phase": "read_files",
      "message": "读取需求、结构和排版规范"
    },
    {
      "id": 2,
      "time": "2026-05-17T12:00:05",
      "type": "tool_call",
      "phase": "read_files",
      "name": "read_requirement",
      "arguments": {}
    }
  ]
}
```

### status 枚举

| 值 | 说明 |
|-----|------|
| `running` | 生成中 |
| `completed` | 成功，`output_path` 有值 |
| `failed` | 异常，`error` 有值 |
| `interrupt_requested` / `interrupted` | 中断 |
| `terminate_requested` / `terminated` | 终止 |

### events[].type 枚举

| 类型 | 说明 |
|------|------|
| `run_started` | 开始 |
| `phase_started` / `phase_completed` | 阶段边界 |
| `llm_request` | LLM 调用 |
| `reasoning` | 思考过程 |
| `tool_calls_planned` | 计划调用的工具 |
| `tool_call` / `tool_result` | 工具调用和结果 |
| `section_started` / `section_completed` | 章节边界 |
| `error` | 错误 |

每个 event 最大存储 1000 条，超出则从头部删除。文本值截断到 4000 字符。

---

## POST /runs/{run_id}/interrupt

协作式中断——不会强杀已发出的 LLM 请求，但在下次模型返回、工具调用前或章节切换时尽快停止。

```bash
curl -X POST http://localhost:8000/api/agent/runs/a1b2c3.../interrupt
```

```json
{"status": "interrupt_requested", "run_id": "a1b2c3..."}
```

---

## POST /runs/{run_id}/terminate

协作式终止，与 interrupt 机制相同，但标记为 `terminate_requested`/`terminated`。

---

## GET /runs/{run_id}/download

下载最终生成的 Markdown 文件。

```bash
curl -L -o result.md http://localhost:8000/api/agent/runs/a1b2c3.../download
```

响应: `Content-Type: text/markdown; charset=utf-8`，`Content-Disposition: attachment`。

限制: 仅允许下载 `output_docs/` 内的文件（`_safe_output_path` 校验）。

---

## GET /documents/{file_name}/download

按文件名下载 `output_docs/` 中的任意文档。

```bash
curl -L -o result.md "http://localhost:8000/api/agent/documents/架构设计文档_20260516_153000.md/download"
```

---

## GET /doc-types

```bash
curl http://localhost:8000/api/agent/doc-types
```

```json
["需求规格说明书", "架构设计文档", "测试文档"]
```

---

## 安全措施

| 措施 | 位置 |
|------|------|
| 上传文件扩展名白名单 (`.txt` / `.md`) | `_save_uploaded_source_file()` |
| 下载路径限制在 `output_docs/` 内 | `_safe_output_path()` |
| 运行 ID 可手动指定或自动生成 (uuid4) | `run_id` 参数 |
| 中断/终止是协作式 (非暴力 kill) | `_check_interrupted()` |
