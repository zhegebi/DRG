# docgen_agent API

基础前缀：`/api/docgen_agent`

该接口由 `server/agent/docgen_agent/api.py` 提供，用于启动文档生成、轮询运行轨迹、追加提示、中断/终止任务，以及下载生成的 Markdown/PDF 文件。

## 文档类型

`doc_type` 仅支持：

- `需求规格说明书`
- `架构设计文档`
- `测试文档`

## 接口总览

| 方法 | 路径 | 说明 |
|---|---|---|
| `POST` | `/generate-doc` | 同步生成文档，完成后返回 Markdown/PDF 路径 |
| `POST` | `/generate-doc/start` | 后台启动生成任务，立即返回 `run_id` |
| `GET` | `/runs/{run_id}/trace` | 查询生成轨迹、状态、事件和输出路径 |
| `POST` | `/runs/{run_id}/hint` | 运行中追加提示词或参考文件 |
| `POST` | `/runs/{run_id}/interrupt` | 请求中断运行 |
| `POST` | `/runs/{run_id}/terminate` | 请求终止运行 |
| `GET` | `/runs/{run_id}/download` | 下载该运行生成的 Markdown |
| `GET` | `/runs/{run_id}/download/pdf` | 下载该运行生成的 PDF |
| `GET` | `/documents/{file_name}/download` | 按文件名下载 `output_docs/` 内文件 |
| `GET` | `/doc-types` | 获取支持的文档类型 |

## POST /generate-doc

同步生成文档。接口会阻塞到生成完成、被中断、被终止或失败。

请求类型：`multipart/form-data`

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `prompt` | string | 否 | 用户补充提示词 |
| `doc_type` | string | 否 | 文档类型，默认 `需求规格说明书` |
| `source_file` | file | 否 | 需求源文件，仅支持 `.txt` / `.md` |
| `run_id` | string | 否 | 自定义运行 ID；不传则后端生成 |

响应：

```json
{
  "status": "success",
  "run_id": "a1b2c3",
  "file_name": "架构设计文档_20260518_120000.md",
  "file_path": "server/agent/docgen_agent/output_docs/架构设计文档_20260518_120000.md",
  "pdf_path": "server/agent/docgen_agent/output_docs/架构设计文档_20260518_120000.pdf",
  "doc_type": "架构设计文档"
}
```

`status` 也可能是 `interrupted` 或 `terminated`。

## POST /generate-doc/start

后台启动文档生成，适合前端通过 trace 轮询进度。

请求字段与 `/generate-doc` 相同。

响应：

```json
{
  "status": "started",
  "run_id": "a1b2c3",
  "doc_type": "测试文档"
}
```

## GET /runs/{run_id}/trace

查询运行状态和事件流。

响应：

```json
{
  "run_id": "a1b2c3",
  "status": "running",
  "doc_type": "架构设计文档",
  "created_at": "2026-05-18T12:00:00",
  "updated_at": "2026-05-18T12:05:00",
  "output_path": null,
  "pdf_path": null,
  "error": null,
  "interrupted": false,
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
| `interrupt_requested` / `interrupted` | 已请求/已完成中断 |
| `terminate_requested` / `terminated` | 已请求/已完成终止 |

常见事件类型：`run_started`、`phase_started`、`phase_completed`、`llm_request`、`reasoning`、`tool_call`、`tool_result`、`section_started`、`section_completed`、`error`。

## POST /runs/{run_id}/hint

向运行中的任务追加提示。下一轮 LLM 调用会把该提示作为用户消息注入。

请求类型：`multipart/form-data`

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `hint` | string | 是 | 追加提示词或指导内容 |
| `source_file` | file | 否 | 追加参考文件，仅支持 `.txt` / `.md` |

响应：

```json
{
  "status": "hint_appended",
  "run_id": "a1b2c3"
}
```

## POST /runs/{run_id}/interrupt

请求协作式中断。任务会在下一次工具调用或模型调用边界停止。

响应：

```json
{
  "status": "interrupt_requested",
  "run_id": "a1b2c3"
}
```

## POST /runs/{run_id}/terminate

请求协作式终止。语义上比 interrupt 更明确地表示放弃本次生成。

响应：

```json
{
  "status": "terminate_requested",
  "run_id": "a1b2c3"
}
```

## GET /runs/{run_id}/download

下载该运行生成的 Markdown 文件。

响应头：

- `Content-Type: text/markdown; charset=utf-8`
- `Content-Disposition: attachment`

## GET /runs/{run_id}/download/pdf

下载该运行生成的 PDF 文件。

响应头：

- `Content-Type: application/pdf`
- `Content-Disposition: attachment`

## GET /documents/{file_name}/download

按文件名下载 `server/agent/docgen_agent/output_docs/` 内的文件。后端会剥离路径，仅使用文件名，并校验最终路径必须位于 `output_docs/` 内。

## GET /doc-types

响应：

```json
["需求规格说明书", "架构设计文档", "测试文档"]
```

## 错误码

| 状态码 | 场景 |
|---|---|
| `400` | 上传文件类型不支持，或下载路径不在 `output_docs/` 内 |
| `404` | `run_id` 不存在，文件不存在，或 PDF 尚未生成 |
| `409` | 文档尚未生成完成，暂不能下载 |
| `500` | 文档生成或底层工具执行失败 |

## curl 示例

```bash
curl -X POST http://localhost:8000/api/docgen_agent/generate-doc/start \
  -F "prompt=请结合当前代码生成测试文档" \
  -F "doc_type=测试文档" \
  -F "source_file=@requirements.md"
```

```bash
curl http://localhost:8000/api/docgen_agent/runs/a1b2c3/trace
```

```bash
curl -L -o result.md http://localhost:8000/api/docgen_agent/runs/a1b2c3/download
curl -L -o result.pdf http://localhost:8000/api/docgen_agent/runs/a1b2c3/download/pdf
```
