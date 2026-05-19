import datetime
from typing import Optional

from sqlmodel import Field, SQLModel, text


class Document(SQLModel, table=True):
    """Represents a document in the knowledge base."""

    __tablename__ = "documents"

    id: Optional[int] = Field(default=None, primary_key=True)
    title: str = Field(..., description="The title of the document")
    content: str = Field(..., description="The content of the document")
    created_at: Optional[datetime.datetime] = Field(
        default_factory=datetime.datetime.now,
        sa_column_kwargs={"server_default": text("CURRENT_TIMESTAMP")},
        description="The timestamp when the document was created",
    )
