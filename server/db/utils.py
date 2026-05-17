from typing import AsyncGenerator

from sqlalchemy.orm import sessionmaker
from sqlmodel import Session
from sqlmodel.ext.asyncio.session import AsyncSession

from . import get_sync_engine, get_async_engine


def get_session():
    """FastAPI dependency to get a synchronous database session."""
    # 优先使用 getter 函数获取引擎（更可靠）
    engine = get_sync_engine()
    if engine is None:
        raise RuntimeError("Database not initialized. Call init_db() on application startup.")
    with Session(engine) as session:
        yield session


async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency to get an asynchronous database session."""
    # 优先使用 getter 函数获取引擎（更可靠）
    engine = get_async_engine()
    if engine is None:
        raise RuntimeError("Database not initialized. Call init_db() on application startup.")

    async_session_maker = sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)  # type: ignore

    async with async_session_maker() as session:  # type: ignore
        yield session