from typing import Optional

from sqlmodel import JSON, Column, Field, SQLModel


class Thread(SQLModel, table=True):
    """
    Thread model representing a thread (conversation) in database.
    """

    id: Optional[int] = Field(default=None, primary_key=True)
    title: str
    created_at: str
    updated_at: str
    owner: int = Field(foreign_key="user.id")
    detail: dict[str, str] = Field(default_factory=dict, sa_column=Column(JSON))
