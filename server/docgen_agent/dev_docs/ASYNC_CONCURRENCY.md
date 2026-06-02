# ASYNC_CONCURRENCY — 异步并发/同步/线程池/事件循环 分析报告

> 最后更新: 2026-06-01  
> 涵盖文件: `workflow.py`, `tools.py`, `api.py`

---

## 1. 基础知识

### 1.1 Python asyncio 事件循环

```
┌──────────────────────────────────────────────────────────┐
│                   Event Loop (单线程)                      │
│                                                           │
│  Task A (协程)  ←→  await  ←→  I/O 等待                  │
│  Task B (协程)  ←→  await  ←→  I/O 等待                  │
│  Task C (协程)  ←→  await  ←→  I/O 等待                  │
│  ...                                                      │
│                                                           │
│  关键规则:                                                 │
│  ① 所有协程共享同一个 OS 线程                              │
│  ② 协程通过 await 主动让出控制权                           │
│  ③ 任何同步阻塞操作 = 冻结整个事件循环 = 所有协程卡死       │
│  ④ asyncio.to_thread() 是唯一的合法"逃脱"路径             │
└──────────────────────────────────────────────────────────┘
```

Python 的 `asyncio` 使用**单线程协作式多任务**模型。所有协程运行在同一个操作系统线程中。协程之间不是抢占式的——一个协程必须主动 `await` 才能让其他协程运行。如果某个协程执行了同步阻塞操作（如 `time.sleep(5)`、同步文件 I/O、同步 HTTP 请求），整个事件循环会被冻结 5 秒，**所有**其他请求、后台任务、SSE 流全部卡住。

### 1.2 `asyncio.to_thread()` 原理

```python
# 错误做法 — 冻结事件循环
async def bad_handler():
    data = requests.get("https://example.com")  # 同步阻塞! 冻结所有协程!
    return data

# 正确做法 — 卸载到线程池
async def good_handler():
    data = await asyncio.to_thread(requests.get, "https://example.com")
    # ↑ 在线程池中执行 requests.get，事件循环继续处理其他协程
    return data
```

`asyncio.to_thread()` 将同步函数提交给 `ThreadPoolExecutor`（默认 `min(32, cpu_count + 4)` 个线程），立即返回一个 `Future`。事件循环在等待 Future 完成期间可以处理其他协程。**这是让同步阻塞操作与 asyncio 共存的唯一正确方式。**

关键约束：
- 默认线程池大小有限（通常 8-12 个线程），所有 `to_thread` 调用共享此池
- 如果 N 个并行渲染任务各需 30s（Mermaid 外部 API），线程池可能在高峰期耗尽
- 线程池耗尽 → 新的 `to_thread` 调用排队等待 → 不影响事件循环主线程，但该协程被挂起

### 1.3 `ContextVar` — 协程安全的"线程局部变量"

```python
_source_md_content_ctx: ContextVar[str] = ContextVar("docgen_source_content", default="...")
_image_output_dir_ctx: ContextVar[str] = ContextVar("docgen_image_output_dir", default="...")
```

`ContextVar` 是 Python 3.7+ 提供的协程局部存储。每个 `asyncio.Task` 有独立的 context 副本，`set()` 只在当前 Task 及其派生子 Task 中生效。**天然适合多任务并发场景**，无需加锁。

---

## 2. 代码中所有同步阻塞操作分类

### 2.1 ✅ 已正确处理（通过 `asyncio.to_thread` 卸载）

| 操作 | 位置 | 线程池函数 | 阻塞时长 |
|------|------|-----------|---------|
| 读取项目文件 | `tools.py:_handle_read_project_file` | `Path.read_text()` | < 100ms |
| 遍历项目文件树 | `tools.py:_handle_list_project_files` | `os.walk()` | < 500ms |
| 搜索项目文本 | `tools.py:_handle_search_project` | 逐行正则匹配 | < 2s |
| 读取依赖清单 | `tools.py:_handle_read_dependency_manifest` | `tomllib.loads`/`json.loads` | < 200ms |
| 读取 API 路由 | `tools.py:_handle_read_api_routes` | 正则扫描 | < 1s |
| 读取数据模型 | `tools.py:_handle_read_data_models` | 正则扫描 | < 1s |
| 保存文档 | `tools.py:_handle_save_document` | 文件写入 | < 500ms |
| Mermaid 渲染 | `tools.py:_handle_render_mermaid` | `requests.get(mermaid.ink)` | 1-30s |
| PlantUML 渲染 | `tools.py:_handle_render_plantuml` | `requests.get(plantuml.com)` | 1-30s |
| HTML 构建 | `tools.py:build_document_html` | Mermaid 渲染+MD→HTML+base64 | 5-30s |
| 文件上传 I/O | `api.py:_save_one_uploaded_source_file` | `shutil.copyfileobj` | < 500ms |
| 文档格式化 | `workflow.py:_save_and_convert_document` | 5 个规范化函数 | 1-5s |
| 文档头规范化 | `workflow.py:Phase 4` | `normalize_document_header` | < 1s |
| DB 持久化 | `api.py:_run_agent_background` | `_persist_trace_sync` | 200ms-2s |

### 2.2 ✅ 同步但极快（< 5ms，留在事件循环中无害）

| 操作 | 位置 | 说明 |
|------|------|------|
| ContextVar.set() | `tools.py:set_source_files` 等 | 纯内存操作 |
| `_record_trace()` | `workflow.py` | 加锁 → dict 操作 → 解锁 |
| `_record_trace_delta()` | `workflow.py` | 追加 trace 事件 |
| `_check_terminated()` | `workflow.py` | 加锁检查 set |
| `_get_top_sections()` | `workflow.py` | JSON 查找 |
| `_flatten_required_sections()` | `workflow.py` | 树遍历 |
| `get_tools_for_phase()` | `tools.py` | 列表过滤 |

### 2.3 ✅ 异步 I/O（原生 `await`，不阻塞）

| 操作 | 位置 | 说明 |
|------|------|------|
| LLM API 调用 | `workflow.py:_stream_chat_completion` | `client.chat.completions.create(stream=True)` + `async for` |
| LLM 非流式调用 | `api.py:_generate_task_title` | `client.chat.completions.create()` |
| 联网搜索 | `tools.py:_handle_search_web` | `httpx.AsyncClient.get()` |
| DB 查询 | `api.py:create_task` 等 | `AsyncSession.get()` / `exec()` |
| SSE 推送 | `api.py:stream_task_trace` | `StreamingResponse` + `asyncio.sleep(0.2)` |

### 2.4 ⚠️ 潜在风险点

#### 风险 1: 线程池耗尽（Mermaid/PlantUML 并发渲染）

```
场景: Phase 3 并行生成 8 个章节，每个章节都调用 render_mermaid
→ 8 个线程因 requests.get() 阻塞在 mermaid.ink (最多 30s/个)
→ 默认线程池 ~12 个线程，剩余 4 个可用
→ 如果再有工具调用需要 to_thread，排队等待
→ 事件循环主线程不受影响，但这些协程被挂起
```

**缓解措施建议**: 为渲染操作使用独立的 `ThreadPoolExecutor`，避免影响文件 I/O 等其他操作。

#### 风险 2: `build_document_html` 中 Mermaid 代码块渲染

```python
# tools.py:2786
md_text = _render_diagram_blocks_for_html(md_text)
```

`_render_diagram_blocks_for_html` 为每个 ` ```mermaid ``` ` 代码块调用 `_render_mermaid_to_file`，后者使用 `requests.get()` 同步调用 mermaid.ink。这个函数被 `build_document_html` 调用，而 `build_document_html` 通过 `await asyncio.to_thread(build_document_html, ...)` 执行 → 整个 `build_document_html` 在线程池中运行 → 内部的 `requests.get()` 阻塞线程池线程而非事件循环。**这是安全的**，但会长时间占用一个线程池线程。

#### 风险 3: `httpx.AsyncClient` 超时默认值

```python
# tools.py:1188
async with httpx.AsyncClient(timeout=15) as http:
```

DuckDuckGo 搜索有 15s 超时。超时后抛异常 → LLM 收到错误信息 → 用已有知识继续。这是正确的降级策略。

---

## 3. 并发控制架构

### 3.1 `threading.RLock` — 内存 trace 的线程安全

```python
_TRACE_LOCK = threading.RLock()  # workflow.py:66
```

`_RUN_TRACES`、`_TERMINATE_FLAGS`、`_ACTIVE_STREAMS` 三个全局 dict/set 共享此锁。

**为何用 `threading.RLock` 而非 `asyncio.Lock`?**

| 因素 | threading.RLock | asyncio.Lock |
|------|----------------|-------------|
| 适用场景 | 临界区极短（< 1μs），不涉及 await | 临界区含 await |
| 性能 | 极快（C 实现） | 需要事件循环调度 |
| 跨线程安全 | ✅ | ❌（仅限同一事件循环） |
| 重入 | ✅ | ❌ |

本项目中所有 trace 操作都是纯内存 dict 操作（无 I/O、无 await），用 `threading.RLock` 是最优选择。

**重要**: 自 2026-06-01 修复后，不再有线程池线程调用 trace 函数（所有 trace 调用都在事件循环主线程中），因此 `threading.RLock` 在单线程 asyncio 环境中实际上是无竞争的。

### 3.2 全局状态隔离

```
多任务并发场景 (Task A 生成需求文档, Task B 生成测试文档)

_run_agent_background(task_id="A")          _run_agent_background(task_id="B")
  └─ run_agent(run_id="A")                    └─ run_agent(run_id="B")
       └─ set_source_files(...)                    └─ set_source_files(...)
            └─ _source_md_content_ctx.set()             └─ _source_md_content_ctx.set()
                                                    ↑ ContextVar: Task A 和 Task B 互不干扰
       └─ set_image_output_dir("A")                 └─ set_image_output_dir("B")
            └─ _image_output_dir_ctx.set()               └─ _image_output_dir_ctx.set()
                                                    ↑ ContextVar: 图片输出目录隔离
       └─ _record_trace("A", ...)                   └─ _record_trace("B", ...)
            └─ _TRACE_LOCK                                  └─ _TRACE_LOCK
            └─ _RUN_TRACES["A"]                             └─ _RUN_TRACES["B"]
                                                    ↑ RLock + dict: 不同 key，无冲突
```

结论：**多任务并发是安全且正确隔离的。**

### 3.3 FastAPI BackgroundTasks 执行模型

```python
# Starlette 源码逻辑 (简化)
async def __call__(self, scope, receive, send):
    await self.app(scope, receive, send)  # 处理请求 → 发送响应
    for task in self.background:          # 响应发出后，逐一执行后台任务
        if task.is_async:
            await task.func(*task.args, **task.kwargs)
        else:
            await run_in_threadpool(task.func, *task.args, **task.kwargs)
```

每个请求的 `BackgroundTasks` 是独立实例。请求 A 的 `_run_agent_background` 和请求 B 的 `_run_agent_background` 不互相等待——它们作为独立的协程在事件循环中并发执行。

**但是**，同一请求中的多个 `background_tasks.add_task()` 调用会**串行**执行。本项目中每个请求只添加一个后台任务，因此不受影响。

---

## 4. 修复记录 (2026-06-01)

| 修复项 | 修复前 | 修复后 |
|--------|--------|--------|
| 文件上传 | `shutil.copyfileobj` 在事件循环中同步执行 | `await asyncio.to_thread(_write)` |
| 文档格式化 | 5 个 `normalize_*` 函数在事件循环中直接调用 | `await asyncio.to_thread(_normalize_document, ...)` |
| Phase 4 拼接 | `normalize_document_header` 在事件循环中直接调用 | `await asyncio.to_thread(normalize_document_header, ...)` |
| DB 持久化 | `_persist_trace_sync` 在 finally 中直接同步调用 | `await asyncio.to_thread(_persist_trace_sync, task_id)` |
| 前端提交 | `for...await` 串行提交多个文档类型 | `Promise.all()` 并行提交 |

---

## 5. 建议改进项 (未实施)

### 5.1 独立线程池用于外部渲染

```python
# 避免 Mermaid/PlantUML 渲染耗尽默认线程池
_RENDER_EXECUTOR = ThreadPoolExecutor(max_workers=4, thread_name_prefix="render")

async def execute_render_async(name, arguments):
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(_RENDER_EXECUTOR, ...)
```

### 5.2 流式 trace 事件批量刷新

当前 `_record_trace_delta` 每个 LLM token 就触发一次锁+列表操作（每秒可达 100+ 次）。可考虑批量缓冲（每 50ms 或在 `async for` 迭代间隙统一写入）。

### 5.3 限制单用户并发任务数

当前无限制。恶意或误操作可能同时启动 100 个生成任务，耗尽 LLM API 额度。建议在 `create_task` 中检查当前用户运行中任务数。

---

## 6. 事件循环健康检查清单

| 检查项 | 状态 |
|--------|------|
| 所有同步 I/O 通过 `asyncio.to_thread` 卸载 | ✅ 已修复 |
| 所有同步 HTTP 请求通过 `asyncio.to_thread` 卸载 | ✅ `requests.get` 在 `to_thread` 内 |
| 所有 CPU 密集型操作通过 `asyncio.to_thread` 卸载 | ✅ 字符串规范化在 `to_thread` 内 |
| async 函数中无 `time.sleep()` | ✅ 不存在 |
| async 函数中无同步 `open()` / 文件读写 | ✅ 已修复 |
| async 函数中无同步 DB 操作 | ✅ 已修复 |
| 无 `asyncio.Lock` 跨 await 持有 | ✅ 不适用（无 asyncio.Lock） |
| `threading.RLock` 不在 await 期间持有 | ✅ 所有 trace 操作不跨越 await |
| ContextVar 用于任务级状态隔离 | ✅ |
| 线程池大小合理 | ⚠️ 默认值在极端并发下可能不足 |
