# docgen_agent API

基础前缀：`/api/docgen_agent`

接口由 `server/docgen_agent/api.py` 提供。文档生成智能体按任务模型工作，对外使用 `task_id`，数据库表模型为 `DocgenTask`。任务控制只支持协作式终止，不支持中途追加提示词或暂停。

## 文档类型

`doc_type` 仅支持：

- `需求规格说明书`
- `架构设计文档`
- `测试文档`

## 接口总览

| 方法 | 路径 | 说明 |
|---|---|---|
| `POST` | `/task/create` | 创建后台文档生成任务，立即返回 `task_id` |
| `GET` | `/task/list` | 查询当前用户的文档生成任务 |
| `GET` | `/task/status` | 批量查询任务状态 |
| `GET` | `/task/{task_id}/trace` | 查询任务轨迹、状态、事件和输出路径 |
| `GET` | `/task/{task_id}/trace/stream` | SSE 推送任务轨迹快照 |
| `POST` | `/task/{task_id}/terminate` | 请求终止任务 |
| `GET` | `/task/{task_id}/download` | 下载任务生成的 Markdown |
| `GET` | `/task/{task_id}/download/pdf` | 下载任务生成的 PDF |
| `DELETE` | `/task/{task_id}` | 删除已结束任务，运行中任务不会删除 |
| `GET` | `/documents/{file_name}/download` | 按文件名下载 `output_docs/` 内文件 |
| `GET` | `/doc-types` | 获取支持的文档类型 |

## POST /task/create

创建后台文档生成任务，适合前端通过 trace 或 SSE 展示进度。

请求类型：`multipart/form-data`

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `prompt` | string | 否 | 用户初始提示词 |
| `doc_type` | string | 否 | 文档类型，默认 `需求规格说明书` |
| `generation_mode` | string | 否 | 生成模式，默认 `structured`；可选 `structured`（提示词+文件+预定义 output 规范）、`prompt_only`（提示词+文件） |
| `source_file` | file | 否 | 单个需求文件，兼容旧字段，仅支持 `.txt` / `.md` |
| `source_files` | file[] | 否 | 需求/依赖文件列表，仅支持 `.txt` / `.md`，可重复传入 |
| `task_id` | string | 否 | 自定义任务 ID；不传则后端生成 |

响应：

```json
{
  "status": "started",
  "task_id": "a1b2c3",
  "doc_type": "测试文档",
  "task_title": "测试文档",
  "generation_mode": "structured"
}
```

## GET /task/list

查询当前登录用户的文档生成任务。每条记录结构与 `/task/{task_id}/trace` 相同，包含任务标题、文档类型、状态、输出路径和已持久化的 trace。

## GET /task/status

批量查询任务状态。

查询参数：

| 参数 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `task_ids` | string[] | 是 | 要查询的任务 ID，可重复传入 |

响应：

```json
[
  {
    "task_id": "a1b2c3",
    "task_status": "running"
  }
]
```

## GET /task/{task_id}/trace

查询任务状态和事件流。

响应：

```json
{
  "task_id": "a1b2c3",
  "status": "running",
  "doc_type": "架构设计文档",
  "task_title": "架构文档",
  "generation_mode": "structured",
  "document_id": null,
  "created_at": "2026-05-18T12:00:00",
  "updated_at": "2026-05-18T12:05:00",
  "output_path": null,
  "pdf_path": null,
  "error": null,
  "terminated": false,
  "events": []
}
```

状态值：

| 状态 | 说明 |
|---|---|
| `running` | 正在生成 |
| `completed` | 已完成，`output_path` 为 Markdown，`pdf_path` 为 PDF |
| `failed` | 失败，查看 `error` |
| `terminate_requested` / `terminated` | 已请求/已完成终止 |

常见事件类型：`run_started`、`phase_started`、`phase_completed`、`llm_request`、`reasoning`、`assistant_message`、`tool_call`、`tool_result`、`section_started`、`section_completed`、`document_stitched`、`format_repaired`、`terminate_requested`、`terminated`、`error`。

## GET /task/{task_id}/trace/stream

以 `text/event-stream` 持续推送完整 trace 快照。前端收到新快照后直接替换本地任务状态，即可实时展示模型思考、章节输出、工具调用和保存结果。流在任务进入 `completed`、`failed` 或 `terminated` 后发送 `[END]` 并结束。

## POST /task/{task_id}/terminate

请求协作式终止。任务会在下一次模型流读取、模型调用边界、工具调用边界或阶段检查点停止。

响应：

```json
{
  "status": "terminate_requested",
  "task_id": "a1b2c3"
}
```

## GET /task/{task_id}/download

下载该任务生成的 Markdown 文件。

响应头：

- `Content-Type: text/markdown; charset=utf-8`
- `Content-Disposition: attachment`

## GET /task/{task_id}/download/pdf

下载该任务生成的 PDF 文件。

响应头：

- `Content-Type: application/pdf`
- `Content-Disposition: attachment`

## DELETE /task/{task_id}

删除已结束任务。运行中任务返回 `false`，已删除或不存在返回 `true`。

## GET /documents/{file_name}/download

按文件名下载 `server/docgen_agent/output_docs/` 内的文件。后端会剥离路径，仅使用文件名，并校验最终路径必须位于 `output_docs/` 内。

## GET /doc-types

响应：

```json
["需求规格说明书", "架构设计文档", "测试文档"]
```

## 错误码

| 状态码 | 场景 |
|---|---|
| `400` | 上传文件类型不支持，或下载路径不在 `output_docs/` 内 |
| `404` | `task_id` 不存在，文件不存在，或 PDF 尚未生成 |
| `409` | 文档尚未生成完成，或任务不在当前进程中运行无法终止 |
| `500` | 文档生成或底层工具执行失败 |

## curl 示例

```bash
curl -X POST http://localhost:8000/api/docgen_agent/task/create \
  -H "Authorization: Bearer <token>" \
  -F "prompt=请结合当前代码生成测试文档" \
  -F "doc_type=测试文档" \
  -F "source_files=@requirements.md" \
  -F "source_files=@constraints.md"
```

```bash
curl -H "Authorization: Bearer <token>" \
  http://localhost:8000/api/docgen_agent/task/a1b2c3/trace
```

```bash
curl -X POST -H "Authorization: Bearer <token>" \
  http://localhost:8000/api/docgen_agent/task/a1b2c3/terminate
```

```bash
curl -L -o result.md http://localhost:8000/api/docgen_agent/task/a1b2c3/download
curl -L -o result.pdf http://localhost:8000/api/docgen_agent/task/a1b2c3/download/pdf
```
