from typing import Optional

from sqlmodel import Field, SQLModel

__all__ = ["Agent"]


class Agent(SQLModel, table=True):
    """
    Agent model representing an agent in database.
    This is hardcoded when system starts.
    """

    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    description: str
