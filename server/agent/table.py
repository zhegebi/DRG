from typing import Optional, Dict
from sqlmodel import Field, SQLModel, JSON, Column
import uuid
from .drg_agent.task import TaskStatus

__all__ = ["Agent", "DrgTask"]




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
    task_id: uuid.UUID = Field(primary_key=True)
    name: str
    result: Optional[Dict] = Field(default=None, sa_column=Column(JSON)) # the format is DrgResult or DrgTestCase in models.py
    status: TaskStatus = TaskStatus.RUNNING
    should_generate_test: bool = False
    err_msg: Optional[str] = None
