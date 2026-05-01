from typing import Optional, Dict, Any
from datetime import datetime
from enum import Enum

from sqlmodel import Field, SQLModel, JSON

__all__ = ["Agent", "Tasks", "Substeps"]


# ---------- Enum Definitions ----------
class TaskStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"

class SubstepStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"

class StepType(str, Enum):
    TESTCASE = "testcase"
    DRG = "drg"



class Tasks(SQLModel, table=True):
    """
    Task model representing a task in database.
    """

    id: Optional[int] = Field(default=None, primary_key=True)
    name: Optional[str] = Field(default=None, max_length=255)
    status: TaskStatus = Field(default=TaskStatus.PENDING)
    generate_testcase: bool = Field(...)                                    # should generate testcase
    input: Dict[str, Any] = Field(sa_type=JSON)                             # patient input (JSON)
    output: Optional[Dict[str, Any]] = Field(default=None, sa_type=JSON)    # final output (JSON)
    error_message: Optional[str] = Field(default=None)                 
    created_at: datetime = Field(default_factory=datetime.now)         
    completed_at: Optional[datetime] = Field(default=None)         


class Substeps(SQLModel, table=True):
    """
    Substep model representing a substep in database.
    """

    id: Optional[int] = Field(default=None, primary_key=True)
    task_id: int = Field(foreign_key="tasks.id", ondelete="CASCADE")            # reference to task id
    step_type: StepType = Field(default=StepType.DRG)                           # step type of the substep (testcase or drg)
    order_index: int = Field()                                                  # order index in the step
    name: str = Field(max_length=255)                     
    status: SubstepStatus = Field(default=SubstepStatus.PENDING)       
    details: Optional[Dict[str, Any]] = Field(default=None, sa_type=JSON)       # intermediate results or debug info(JSON)


class Agent(SQLModel, table=True):
    """
    Agent model representing an agent in database.
    This is hardcoded when system starts.
    """

    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    description: str
