from typing import Optional

from sqlmodel import Field, SQLModel
from enum import Enum

__all__ = ["Agent", "DrgResult", "Complication"]


class Complication(str, Enum):
    CC = "cc"
    MCC = "mcc"
    NO = "no"


class DrgResult(SQLModel, table = True):
    """
    DrgResult model representing a DRG result in database.
    This is generated when system runs.
    """

    id: Optional[int] = Field(default=None, primary_key=True)
    mdc: str
    adrg: str
    drg: str
    complication: Complication
    reason: str

class Agent(SQLModel, table=True):
    """
    Agent model representing an agent in database.
    This is hardcoded when system starts.
    """

    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    description: str
