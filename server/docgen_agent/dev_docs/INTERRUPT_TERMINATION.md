# INTERRUPT_TERMINATION — 智能体中断/终止机制 正确性与冲突分析

> 最后更新: 2026-06-01  
> 涵盖: 前端终止按钮 → API → 工作流检查点 → 流关闭 全链路

---

## 1. 架构概览

```
┌──────────────────────────────────────────────────────────────────────┐
│                          终止控制流                                  │
│                                                                      │
│  前端                         后端 API                    工作流     │
│  ────                         ────────                   ──────     │
│                                                                      │
│  点击"终止"                                                          │
│    │                                                                 │
│    ▼                                                                 │
│  POST /terminate  ──────────►  request_generation_terminate()        │
│                                  │                                   │
│                                  ├─ _TERMINATE_FLAGS.add(run_id)     │
│                                  ├─ state.status = "terminate_req."  │
│                                  ├─ _record_trace("terminate_req.")  │
│                                  └─ _close_active_streams(run_id) ───┤
│                                                                      │
│  轮询 trace  ◄──────────────  get_generation_trace()                │
│    │                                                                 │
│    ▼                                                                 │
│  显示"已终止"                                                         │
│                                                                      │
│                                                      工作流检查点    │
│                                                      ───────────    │
│                                          _check_terminated()         │
│                                            ├─ run_id in _TERMINATE?  │
│                                            ├─ YES → raise            │
│                                            │   GenerationTerminated  │
│                                            └─ NO  → continue         │
│                                                                      │
│                                          异常传播链:                  │
│                                          _stream_chat_completion     │
│                                            → _call_llm              │
│                                              → _generate_section    │
│                                                → run_agent          │
│                                                  → finally: cleanup │
└──────────────────────────────────────────────────────────────────────┘
```

---

## 2. 终止机制详解

### 2.1 前端侧 (`useDocGen.ts`)

| 元素 | 逻辑 |
|------|------|
| 终止按钮可见性 | `isSelectedRunActive` → status ∈ `{running, terminate_requested}` |
| 终止按钮可点击性 | `canTerminateRun` → `isSelectedRunActive && status !== 'terminate_requested' && !isTerminating` |
| 终止操作 | `handleTerminate()` → `terminateRun(id)` → POST → `refreshSelectedRun()` |
| 轮询停止条件 | `terminalRunStatusSet` = `{completed, failed, terminated}`，匹配即 `stopPolling()` |
| SSE 流停止 | 收到 `[END]` 帧 → 返回；`AbortController.signal` 允许主动断开 |

**防重复点击**: `isTerminating.value = true` 锁住按钮，`finally` 中恢复。

### 2.2 后端 API 侧 (`api.py`)

```python
# terminate_task 端点
@router.post("/task/{task_id}/terminate")
async def terminate_task(task_id, db_client):
    row = await db_client.get(DocgenTask, task_id)    # 1. 查 DB 确认存在
    if row is None: return 404
    ok = request_generation_terminate(task_id)         # 2. 设置终止标志 + 关闭流
    if not ok:
        if row.status in _TERMINAL_STATUSES:           # 3. 已结束 → 返回当前状态
            return {"status": row.status}
        return 409  # "任务不在当前进程中运行"
    await _persist_trace_async(db_client, task_id)     # 4. 持久化
    return {"status": "terminate_requested"}
```

**`request_generation_terminate()` 内部逻辑** (workflow.py):

```
_TRACE_LOCK.acquire()
  ├─ state = _RUN_TRACES.get(run_id)          # 查内存
  │   └─ None → return False                  # 任务不在本进程
  ├─ _TERMINATE_FLAGS.add(run_id)             # 设置终止标志
  ├─ state["status"] = "terminate_requested"   # 更新状态
  ├─ state["updated_at"] = now
_TRACE_LOCK.release()

_record_trace("terminate_requested")           # 记录事件
_close_active_streams(run_id)                  # 关闭活跃的 LLM 流
```

### 2.3 工作流检查点 (`workflow.py`)

`_check_terminated()` 在以下 **27 个位置** 被调用：

| 阶段 | 调用次数 | 调用时机 |
|------|---------|---------|
| 流式 LLM 调用 | 3+ | 流创建前、每 chunk 到达时、异常时 |
| 工具执行 | 2 | 执行前、执行后 |
| `_call_llm` | 1/turn | 每轮 LLM 对话开始 |
| `_stream_chat_completion` | 3 | 开始、流中、异常后 |
| `_execute_traced_tool` | 2 | 工具调用前、后 |
| `run_agent` 总控 | 5 | 启动、拆分、逐节、校验、拼接 |
| `_save_and_convert_document` | 2 | 保存前、转换前 |
| `_generate_section_group` | 1 | 每章节开始 |

**检查逻辑**:

```python
def _check_terminated(run_id, phase=""):
    if not run_id: return
    with _TRACE_LOCK:
        should_terminate = run_id in _TERMINATE_FLAGS  # 原子读取
    if should_terminate:
        _set_run_status(run_id, "terminated")           # 更新状态
        _record_trace(run_id, "terminated", phase=phase) # 记录事件
        raise GenerationTerminated(f"文档生成已终止: {run_id}")
```

---

## 3. 各阶段终止响应时间分析

| 正在执行的操作 | 终止响应延迟 | 原因 |
|--------------|-------------|------|
| LLM 流式输出中 | **< 50ms** | 每 chunk 到达时检查，DeepSeek 流 chunk 间隔通常 10-50ms |
| LLM 非流式调用中 | **取决于响应时间** | `await client.chat.completions.create(stream=False)` 期间无法中断；最长 ~60s |
| Mermaid/PlantUML 渲染中 | **< 30s** | 渲染在 `to_thread` 中，工具完成后下一行代码检查终止 |
| 文件读取中 | **< 500ms** | `to_thread` 完成后检查 |
| 文档格式化中 | **< 5s** | `to_thread` 完成后检查 |
| 章节间间隙 | **< 1ms** | for 循环迭代开始处立即检查 |

**最坏情况**: 刚发出 LLM 非流式请求（fallback 模式）→ 需要等待完整响应返回（最长 60s）。流式模式下的最坏情况是两个 chunk 之间的间隔 + 检查延迟 ≈ 100ms。

---

## 4. 多场景冲突分析

### 4.1 场景: 同账号多浏览器 Tab 并发

```
Tab A                     Tab B                    后端
─────                     ─────                     ───
显示任务列表              显示任务列表
选中 Task X              选中 Task X
点击"终止" ──────────────────────────────────────────► request_generation_terminate("X")
                                                         ├─ _TERMINATE_FLAGS.add("X")
                                                         └─ _close_active_streams("X")
                         SSE 轮询 (200ms 间隔)
                           ◄────────────────────────── status: "terminate_requested"
                         停止轮询, 显示"已终止"
◄─────────────────────── SSE 推送 status: "terminated"
停止轮询, 显示"已终止"
```

**结论: ✅ 安全**。两个 Tab 的 SSE 流各自独立，最终都收到 `terminated` 状态。无数据竞争。

### 4.2 场景: 双重点击终止按钮

```
点击终止 (第1次)        点击终止 (第2次, 0.5s后)
───────                 ───────
isTerminating = true    按钮 disabled (canTerminateRun = false)
POST /terminate         不会发起请求
  → 200 OK
isTerminating = false   按钮变为可用，但 status 已是 "terminate_requested"
                        canTerminateRun 仍为 false (因为 status !== 'running')
                        不会发起第二次请求
```

**结论: ✅ 安全**。前端 `canTerminateRun` 和 `isTerminating` 双重防护。即使绕过前端直接调 API，后端第二次调用返回 409 或当前状态（幂等）。

### 4.3 场景: 同时对多个任务终止

```
Task A (需求文档) running    Task B (测试文档) running
         │                           │
         ▼                           ▼
terminate("A")                terminate("B")
  ├─ _TERMINATE_FLAGS.add("A")   ├─ _TERMINATE_FLAGS.add("B")
  └─ _close_active_streams("A")  └─ _close_active_streams("B")

_check_terminated("A") → raise   _check_terminated("B") → raise
```

**结论: ✅ 安全**。`_TERMINATE_FLAGS` 是 `set[str]`，不同任务 ID 互不干扰。`_close_active_streams` 按 `run_id` 索引 `_ACTIVE_STREAMS`，也互不干扰。

### 4.4 场景: 终止 + 立即创建新任务

```
POST /terminate (Task A)        POST /create (Task B)
───────────────────────         ──────────────────────
request_generation_terminate    start_generation_trace (新 run_id)
  _TERMINATE_FLAGS.add("A")       _RUN_TRACES["B"] = {...}
                                  _record_trace("B", "run_started")
Task A 收到 GenerationTerminated
_run_agent_background finally:
  _persist_trace_sync("A")      run_agent("B") 正常开始
```

**结论: ✅ 安全**。不同 `run_id` 的数据完全隔离。终止 A 不影响 B 的创建和执行。

### 4.5 场景: 后端进程崩溃/重启

```
Task A running, Task B running
    │
    ▼ 后端崩溃
    │
    ▼ 重启
lifespan 启动
    │
    ▼
terminate_stale_tasks_on_startup()
    ├─ 查询 DB: status IN ("running", "terminate_requested")
    ├─ Task A → status="terminated", error="服务端已退出，任务被终止"
    ├─ Task B → status="terminated", error="服务端已退出，任务被终止"
    └─ commit
    │
    ▼ 前端轮询
SSE/trace 返回 status="terminated"
停止轮询，显示"中止：服务端已退出，任务被终止"
```

**结论: ✅ 安全**。启动清理逻辑确保残留任务不会永远处于 "running" 状态。

### 4.6 场景: 终止不存在/已结束的任务

| 请求 | 后端行为 | HTTP |
|------|---------|------|
| terminate(不存在的 task_id) | `row is None` → 404 | 404 |
| terminate(已 completed 的任务) | `row.status in _TERMINAL_STATUSES` → 返回当前状态 | 200 `{"status": "completed"}` |
| terminate(已 terminated 的任务) | 同上 | 200 `{"status": "terminated"}` |
| terminate(非本进程的任务) | `request_generation_terminate` → `run_id not in _RUN_TRACES` → `ok=False` | 409 |

**结论: ✅ 安全**。所有边界情况有明确处理。

---

## 5. 流关闭机制

### 5.1 `_close_active_streams()` 细节

```python
def _close_active_streams(run_id: str) -> None:
    with _TRACE_LOCK:
        streams = list(_ACTIVE_STREAMS.get(run_id, []))  # 复制引用

    for stream in streams:
        close = getattr(stream, "close", None)
        if not callable(close):
            continue
        try:
            close()  # 关闭 httpx 响应流
        except Exception as exc:
            logger.debug(f"关闭模型流失败: {run_id}: {exc}")
```

关闭流后，`async for chunk in stream` 的下一次迭代会触发连接关闭异常。HTTPX 通常抛出 `httpx.RemoteProtocolError` 或 `GeneratorExit`。由于 `_check_terminated` 在每次 chunk 迭代开始处执行，它会在异常被抛出前先检测到终止标志并主动 `raise GenerationTerminated`。

### 5.2 异常传播链

```
async for chunk in stream:
    _check_terminated()  → raise GenerationTerminated
        │
        ▼ (在 _stream_chat_completion 的 finally 中)
    _unregister_active_stream(run_id, stream)
    stream.close()
        │
        ▼ (在 _call_llm 中)
    # 不捕获 GenerationTerminated，继续向上传播
        │
        ▼ (在 _generate_section_group 中)
    # 不捕获，继续向上
        │
        ▼ (在 run_agent 中)
    except GenerationTerminated:
        logger.info("文档生成被终止")
        _set_run_status(run_id, "terminated")
        raise  # 重新抛出，让 _run_agent_background 处理
            │
            ▼ (在 _run_agent_background 中)
    except GenerationTerminated:
        logger.info("后台文档生成已终止")  # 正常终止，不是错误
    finally:
        await asyncio.to_thread(_persist_trace_sync, task_id)
```

**关键**: `GenerationTerminated` 继承自 `RuntimeError`（不是 `BaseException`），因此不会被 `except Exception` 捕获后误处理。在每个需要区分"终止"和"真正的错误"的地方，`GenerationTerminated` 被单独 catch。

---

## 6. 安全网汇总

| 层级 | 安全机制 | 作用 |
|------|---------|------|
| 前端 UI | `canTerminateRun` computed | 防止在不可终止状态点击 |
| 前端 UI | `isTerminating` ref | 防止双击发起重复请求 |
| 前端轮询 | `terminalRunStatusSet` | 终止后自动停止轮询 |
| 后端 API | DB 行存在性检查 | 404 不存在的任务 |
| 后端 API | `_TERMINAL_STATUSES` 检查 | 已结束任务返回当前状态 |
| 后端 API | `_RUN_TRACES` 存在性检查 | 409 非本进程任务 |
| 工作流 | 27 个 `_check_terminated()` 检查点 | 每个 I/O 边界检查终止 |
| 工作流 | 流关闭 (`_close_active_streams`) | 主动中断 LLM 流 |
| 工作流 | `GenerationTerminated` 异常类型 | 区分终止 vs 错误 |
| 工作流 | `finally` 块 cleanup | 无论终止还是错误都执行 |
| 启动 | `terminate_stale_tasks_on_startup()` | 清理崩溃残留 |
| 状态 | `threading.RLock` 保护 | 全局状态读写线程安全 |

---

## 7. 已知局限

| 局限 | 影响 | 建议 |
|------|------|------|
| LLM 非流式调用期间无法中断 | 最长阻塞 60s，期间终止请求排队等待 | 始终使用流式 (`stream=True`)；非流式仅在 fallback 时使用，且 fallback 触发概率极低 |
| `to_thread` 中的操作无法中途取消 | 工具执行中无法终止，需等待工具完成 | Python 线程不支持强制中断；通过检查点（工具执行前后）实现协作式终止 |
| 同任务多 Tab 终止 | 两个 Tab 都可能发起 POST /terminate | 后端幂等处理，无副作用 |
| SSE 流无心跳机制 | 代理/负载均衡可能因无数据而断开 | 当前 200ms 轮询足够；可加 `: heartbeat\n\n` 注释帧 |
