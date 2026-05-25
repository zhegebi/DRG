from datetime import datetime
from typing import Optional

from sqlmodel import JSON, Column, Field, SQLModel

__all__ = ["DocgenTask"]


class DocgenTask(SQLModel, table=True):
    """Database record for a docgen task and its generated document."""

    __tablename__ = "docgen_tasks"

    task_id: str = Field(primary_key=True)
    document_id: Optional[int] = Field(default=None, foreign_key="documents.id")
    name: str
    user_input: str = ""
    user_id: Optional[int] = Field(default=None, foreign_key="user.id", index=True)
    doc_type: str
    source_files: Optional[list[str]] = Field(default=None, sa_column=Column(JSON))
    status: str = "running"
    output_path: Optional[str] = None
    pdf_path: Optional[str] = None
    error: Optional[str] = None
    trace: Optional[dict] = Field(default=None, sa_column=Column(JSON))
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
