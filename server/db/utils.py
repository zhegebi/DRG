from typing import AsyncGenerator, Generator

from sqlmodel import Session
from sqlmodel.ext.asyncio.session import AsyncSession

import server.db


def get_session() -> Generator[Session]:
    """FastAPI dependency to get a synchronous database session."""
    if server.db.sync_engine is None:
        raise RuntimeError("Database not initialized. Call init_db() on application startup.")
    with Session(server.db.sync_engine) as session:
        yield session


async def get_async_session() -> AsyncGenerator[AsyncSession]:
    """FastAPI dependency to get an asynchronous database session."""
    if server.db.async_engine is None:
        raise RuntimeError("Database not initialized. Call init_db() on application startup.")
    async with AsyncSession(server.db.async_engine) as session:
        yield session
