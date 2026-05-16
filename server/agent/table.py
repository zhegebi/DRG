from datetime import datetime
from enum import Enum
from typing import Optional

from sqlmodel import JSON, Column, Field, SQLModel

__all__ = ["Agent", "DrgTask"]


class TaskStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"


class Agent(SQLModel, table=True):
    """
    Agent model representing an agent in database.
    This is hardcoded when system starts.
    """

    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    description: str


class DrgTask(SQLModel, table=True):
    """
    DrgTask model representing a DRG task in database.
    This is generated when system runs.
    """

    task_id: str = Field(primary_key=True)
    name: str
    user_input: str
    user_id: int
    result: Optional[dict] = Field(
        default=None, sa_column=Column(JSON)
    )  # the format is DrgResult or DrgResultWithTestCase in models.py
    status: str
    should_generate_test: bool
    err_msg: Optional[str] = None
    created_at: datetime
