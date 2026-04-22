from typing import Optional

from sqlmodel import Field, SQLModel

__all__ = ["User"]


class User(SQLModel, table=True):
    """
    User model representing a user in database.
    """

    id: Optional[int] = Field(default=None, primary_key=True)
    username: str
    email: str
    password_hash: str
