from datetime import datetime
from enum import Enum
from typing import Optional

from sqlalchemy import Enum as SAEnum
from sqlmodel import JSON, Column, Field, SQLModel

__all__ = ["DrgTask"]


class TaskStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"


class DrgTask(SQLModel, table=True):
    """
    DrgTask model representing a DRG task in database.
    This is generated when system runs.
    """

    task_id: str = Field(primary_key=True)
    document_id: Optional[int] = Field(default=None, foreign_key="documents.id")
    name: str
    user_input: str
    user_id: int = Field(foreign_key="user.id")
    result: Optional[dict] = Field(
        default=None, sa_column=Column(JSON)
    )  # the format is DrgResult or DrgResultWithTestCase in models.py
    status: TaskStatus = Field(
        sa_column=Column(SAEnum(TaskStatus, values_callable=lambda x: [e.value for e in x]))
    )
    should_generate_test: bool
    err_msg: Optional[str] = None
    created_at: datetime
