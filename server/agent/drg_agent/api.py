from fastapi import APIRouter, HTTPException, Depends # noqa
from sqlmodel.ext.asyncio.session import AsyncSession
from pydantic import BaseModel
import uuid

from ..table import DrgTask # noqa
from .task import Task
from server.db.utils import get_async_session
from server.user.auth import get_current_user
from server.user.table import User


router = APIRouter(prefix="/api/drg")


class TaskRequest(BaseModel):
    user_input: str
    should_generate_test: bool = False


@router.post("/task")
async def create_task(
    req: TaskRequest,
    current_user: User = Depends(get_current_user),
    db_client: AsyncSession = Depends(get_async_session)
) -> str:
    """
    create a new task
    return the task id
    """
    task_id=uuid.uuid4().hex
    user_input=req.user_input
    should_generate_test=req.should_generate_test
    task_name = user_input.replace("\n", "").replace("\r", "")[:10]
    assert current_user.id is not None, "current_user.id is None"
    task_obj = Task( # noqa: F841
        id=task_id,
        name=task_name,
        user_input=user_input,
        should_generate_test=should_generate_test,
        user_id=current_user.id
    )
    return "10086"