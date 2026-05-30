import datetime
from enum import Enum
from typing import Optional

from sqlmodel import Field, SQLModel, text


class Category(str, Enum):
    """Enumeration for document categories used by DRG/DocGen agents."""

    TEST_CASE = "test_case"
    DRG_GROUP = "drg_group"
    REQUIREMENT = "requirement"
    ARC = "ARCH"
    TEST_CASE_DOC = "test_case_doc"
    ANY = "any"


class Document(SQLModel, table=True):
    """Represents a document in the knowledge base."""

    __tablename__ = "documents"

    id: Optional[int] = Field(default=None, primary_key=True)
    title: str = Field(..., description="The title of the document")
    content: str = Field(..., description="The content of the document")
    category: str = Field(
        default=Category.ANY.value,
        description="The category of the document",
    )
    created_at: Optional[datetime.datetime] = Field(
        default_factory=datetime.datetime.now,
        sa_column_kwargs={"server_default": text("CURRENT_TIMESTAMP")},
        description="The timestamp when the document was created",
    )
