from fastapi import APIRouter, Depends, HTTPException, Query
from loguru import logger
from sqlmodel import desc, select, distinct
from sqlmodel.ext.asyncio.session import AsyncSession

from server.db.utils import get_async_session
from server.user.auth import get_current_user
from server.user.table import User

from .table import Document

router = APIRouter(prefix="/api/doc")


@router.post("/list")
async def list_docs(
    category: str = Query(default=None, description="Filter by category"),
    current_user: User = Depends(get_current_user),
    db_client: AsyncSession = Depends(get_async_session),
) -> list[Document]:
    """List all documents in the knowledge base, optionally filtered by category."""
    try:
        query = select(Document)
        if category:
            query = query.where(Document.category == category)
        query = query.order_by(desc(Document.created_at))
        result = await db_client.exec(query)
        documents = result.all()
        return list(documents)
    except Exception as e:
        await db_client.rollback()
        logger.exception(f"Error listing documents: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/categories")
async def list_categories(
    current_user: User = Depends(get_current_user),
    db_client: AsyncSession = Depends(get_async_session),
) -> list[str]:
    """List all distinct document categories."""
    try:
        result = await db_client.exec(select(distinct(Document.category)))
        categories = result.all()
        return [c for c in categories if c is not None]
    except Exception as e:
        await db_client.rollback()
        logger.exception(f"Error listing categories: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/{id}")
async def get_doc(
    id: str,
    current_user: User = Depends(get_current_user),
    db_client: AsyncSession = Depends(get_async_session),
) -> Document:
    """Get a specific document by ID."""
    try:
        result = await db_client.exec(select(Document).where(Document.id == id))
        document = result.first()
        if not document:
            raise HTTPException(status_code=404, detail="Document not found")
        return document
    except HTTPException:
        raise
    except Exception as e:
        await db_client.rollback()
        logger.exception(f"Error fetching document: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")
