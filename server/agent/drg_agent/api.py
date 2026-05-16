import asyncio
import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from loguru import logger
from pydantic import BaseModel
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from server.db.utils import get_async_session
from server.user.auth import get_current_user
from server.user.table import User

from ..table import DrgTask, TaskStatus
from .task import DrgResult, DrgResultWithTestCase, StepLog, Task, TaskStep

router = APIRouter(prefix="/api/drg")


class TaskRequest(BaseModel):
    user_input: str
    should_generate_test: bool = False


class TaskListResponse(BaseModel):
    task_id: str
    task_name: str
    task_status: TaskStatus
    created_at: datetime


class TaskStatusResponse(BaseModel):
    task_id: str
    task_status: TaskStatus


class TaskProgressResponse(BaseModel):
    task_progress: StepLog
    is_completed: bool = False


@router.post("/task/create")
async def create_task(
    req: TaskRequest,
    current_user: User = Depends(get_current_user),
    db_client: AsyncSession = Depends(get_async_session),
) -> str:
    """
    create a new task
    return the task id
    """
    try:
        task_id = uuid.uuid4().hex
        user_input = req.user_input
        should_generate_test = req.should_generate_test
        task_name = user_input.replace("\n", "").replace("\r", "")[:10]
        assert current_user.id is not None, "current_user.id is None"
        task_obj = Task(
            id=task_id,
            name=task_name,
            user_input=user_input,
            should_generate_test=should_generate_test,
            user_id=current_user.id,
        )
        task_table_line = DrgTask(
            task_id=task_obj.id,
            name=task_obj.name,
            user_input=task_obj.user_input,
            user_id=task_obj.user_id,
            status=task_obj.status.value,
            should_generate_test=task_obj.should_generate_test,
            created_at=task_obj.created_at,
        )
        db_client.add(task_table_line)
        await db_client.commit()
        if task_obj.should_generate_test:
            asyncio.create_task(task_obj.run_task_with_test(task_obj.user_input))
        else:
            asyncio.create_task(task_obj.run_task_without_test(task_obj.user_input))
        return task_obj.id
    except HTTPException:
        await db_client.rollback()
        raise
    except Exception as e:
        await db_client.rollback()
        logger.exception(f"Error creating task: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/task/list")
async def get_task_list(
    current_user: User = Depends(get_current_user),
    db_client: AsyncSession = Depends(get_async_session),
) -> list[TaskListResponse]:
    """
    get the task list of the current user
    """
    try:
        query_result = await db_client.exec(
            select(DrgTask.task_id, DrgTask.name, DrgTask.status, DrgTask.created_at).where(
                DrgTask.user_id == current_user.id
            )
        )
        results = query_result.all()
        task_list: list[TaskListResponse] = []
        for row in results:
            task_list.append(
                TaskListResponse(task_id=row[0], task_name=row[1], task_status=TaskStatus(row[2]), created_at=row[3])
            )
        return task_list
    except HTTPException:
        await db_client.rollback()
        raise
    except Exception as e:
        await db_client.rollback()
        logger.exception(f"Error getting task list: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/task/status")
async def get_task_status(
    task_ids: list[str] = Query(..., description="The task ids to get status"),
    db_client: AsyncSession = Depends(get_async_session),
) -> list[TaskStatusResponse]:
    """
    get the status of the tasks
    """
    try:
        query_result = await db_client.exec(
            select(DrgTask.task_id, DrgTask.status).where(DrgTask.task_id.in_(task_ids))  # type: ignore
        )
        results = query_result.all()
        task_status_list: list[TaskStatusResponse] = []
        for row in results:
            task_status_list.append(TaskStatusResponse(task_id=row[0], task_status=TaskStatus(row[1])))
        return task_status_list
    except HTTPException:
        await db_client.rollback()
        raise
    except Exception as e:
        await db_client.rollback()
        logger.exception(f"Error getting task status: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/task/result/{task_id}/stream")
async def get_task_result_stream(
    task_id: str,
    db_client: AsyncSession = Depends(get_async_session),
) -> StreamingResponse:
    """
    get the result of the task in streaming format
    """
    try:
        query_result = await db_client.exec(
            select(DrgTask.result, DrgTask.err_msg, DrgTask.status, DrgTask.should_generate_test).where(
                DrgTask.task_id == task_id
            )
        )
        result, err_msg, status, should_generate_test = query_result.first()  # type: ignore
        if should_generate_test:
            result = DrgResultWithTestCase.model_validate_json(result)
            if status == TaskStatus.SUCCESS.value and result.test_result is not None:
                response = f"""
                # DRG 测试用例生成及其验证

                ### 测试病历

                {result.medical_record_text}

                ### 预期结果

                **MDC 分组**: {result.expected_result.mdc}

                **ADRG 分组**: {result.expected_result.adrg}

                **最终 DRG 组**: {result.expected_result.drg}

                **并发症/合并症等级**: {result.expected_result.complication}

                **入组理由**: 
                
                {result.expected_result.reason}

                ### 测试结果

                **MDC 分组**: {result.test_result.mdc}

                **ADRG 分组**: {result.test_result.adrg}

                **最终 DRG 组**: {result.test_result.drg}

                **并发/合并症等级**: {result.test_result.complication}

                **入组理由**: 
                
                {result.test_result.reason}
                """
            elif status == TaskStatus.FAILED.value:
                response = f"""
                # DRG 测试用例生成及其验证

                ### 测试病历

                {result.medical_record_text}

                ### 预期结果

                **MDC 分组**: {result.expected_result.mdc}

                **ADRG 分组**: {result.expected_result.adrg}

                **最终 DRG 组**: {result.expected_result.drg}

                **并发症/合并症等级**: {result.expected_result.complication}

                **入组理由**: 
                
                {result.expected_result.reason}

                ### 测试结果

                **错误信息**: 
                
                {err_msg}
                """
            else:
                raise HTTPException(status_code=400, detail=f"Invalid task status '{status}' to get the result")
        else:
            result = DrgResult.model_validate_json(result)
            if status == TaskStatus.SUCCESS.value:
                response = f"""
                # DRG 入组结果报告

                **MDC 分组**：{result.mdc}

                **ADRG 分组**：{result.adrg}

                **最终 DRG 组**：{result.drg}

                **并发症/合并症等级**：{result.complication}

                **入组理由**：

                {result.reason}
                """
            elif status == TaskStatus.FAILED.value:
                response = f"""
                # DRG 入组结果报告

                **错误信息**:
                
                {err_msg}
                """
            else:
                raise HTTPException(status_code=400, detail=f"Invalid task status '{status}' to get the result")

        async def event_generator():
            # split response into chunks of size chunk_size
            chunk_size = 10
            for i in range(0, len(response), chunk_size):
                chunk = response[i : i + chunk_size]
                # yield chunk as SSE data
                yield f"data: {chunk}\n\n"
            # yield end marker
            yield "data: [END]\n\n"

        return StreamingResponse(
            event_generator(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "X-Accel-Buffering": "no",  # disable nginx buffering
            },
        )
    except HTTPException:
        await db_client.rollback()
        raise
    except Exception as e:
        await db_client.rollback()
        logger.exception(f"Error getting task result in streaming format: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/task/result/{task_id}")
async def get_task_result(
    task_id: str,
    db_client: AsyncSession = Depends(get_async_session),
) -> str:
    """
    get the result of the task
    """
    try:
        query_result = await db_client.exec(
            select(DrgTask.result, DrgTask.err_msg, DrgTask.status, DrgTask.should_generate_test).where(
                DrgTask.task_id == task_id
            )
        )
        result, err_msg, status, should_generate_test = query_result.first()  # type: ignore
        if should_generate_test:
            result = DrgResultWithTestCase.model_validate_json(result)
            if status == TaskStatus.SUCCESS.value and result.test_result is not None:
                response = f"""
                # DRG 测试用例生成及其验证

                ### 测试病历

                {result.medical_record_text}

                ### 预期结果

                **MDC 分组**: {result.expected_result.mdc}

                **ADRG 分组**: {result.expected_result.adrg}

                **最终 DRG 组**: {result.expected_result.drg}

                **并发症/合并症等级**: {result.expected_result.complication}

                **入组理由**: 
                
                {result.expected_result.reason}

                ### 测试结果

                **MDC 分组**: {result.test_result.mdc}

                **ADRG 分组**: {result.test_result.adrg}

                **最终 DRG 组**: {result.test_result.drg}

                **并发/合并症等级**: {result.test_result.complication}

                **入组理由**: 
                
                {result.test_result.reason}
                """
            elif status == TaskStatus.FAILED.value:
                response = f"""
                # DRG 测试用例生成及其验证

                ### 测试病历

                {result.medical_record_text}

                ### 预期结果

                **MDC 分组**: {result.expected_result.mdc}

                **ADRG 分组**: {result.expected_result.adrg}

                **最终 DRG 组**: {result.expected_result.drg}

                **并发症/合并症等级**: {result.expected_result.complication}

                **入组理由**: 
                
                {result.expected_result.reason}

                ### 测试结果

                **错误信息**: 
                
                {err_msg}
                """
            else:
                raise HTTPException(status_code=400, detail=f"Invalid task status '{status}' to get the result")
        else:
            result = DrgResult.model_validate_json(result)
            if status == TaskStatus.SUCCESS.value:
                response = f"""
                # DRG 入组结果报告

                **MDC 分组**：{result.mdc}

                **ADRG 分组**：{result.adrg}

                **最终 DRG 组**：{result.drg}

                **并发症/合并症等级**：{result.complication}

                **入组理由**：

                {result.reason}
                """
            elif status == TaskStatus.FAILED.value:
                response = f"""
                # DRG 入组结果报告

                **错误信息**:
                
                {err_msg}
                """
            else:
                raise HTTPException(status_code=400, detail=f"Invalid task status '{status}' to get the result")
        return response
    except HTTPException:
        await db_client.rollback()
        raise
    except Exception as e:
        await db_client.rollback()
        logger.exception(f"Error getting task result: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/task/{task_id}/progress/{step}")
async def get_task_progress(
    task_id: str,
    step: TaskStep,
) -> TaskProgressResponse:
    """
    Get the progress of a task at a specific step.
    if the task has been completed, the is_completed field will be True.
    """
    try:
        task_log = Task.TASK_LOG_MAP.get(task_id, None)
        # task_log being None means the task has been completed
        # (because it has been deleted from the map when the task is completed)
        if task_log is None:
            return TaskProgressResponse(task_progress=StepLog(step_log_lines=[]), is_completed=True)
        else:
            task_progress = task_log.get(step, None)
            if task_progress is None:
                return TaskProgressResponse(task_progress=StepLog(step_log_lines=[]))  # step not started
            else:
                return TaskProgressResponse(task_progress=task_progress)
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error getting task progress: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")
