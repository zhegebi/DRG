from contextlib import asynccontextmanager

from fastapi import FastAPI
from sqlmodel import select

from .db import init_db
from .db.utils import get_async_session
from .static import init_assets, mount_static
from .agent.docgen_agent.api import router as docgen_agent_router
from .agent.drg_agent.api import router as drg_agent_router
from .user.api import router as auth_router
from .user.auth import AuthUtils
from .user.table import User


async def seed_default_users() -> None:
    default_users = [
        ('admin', 'admin@example.com', 'admin123'),
        ('user', 'user@example.com', 'user123'),
    ]

    async for session in get_async_session():
        for username, email, password in default_users:
            result = await session.exec(
                select(User).where((User.username == username) | (User.email == email))
            )
            if result.first() is None:
                new_user = User(
                    username=username,
                    email=email,
                    password_hash=AuthUtils.hash_password(password),
                )
                session.add(new_user)
                await session.commit()
                await session.refresh(new_user)


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    init_assets()
    await seed_default_users()
    yield
    # nothing to clean up on shutdown for now


app = FastAPI(lifespan=lifespan)

app.include_router(auth_router)
app.include_router(docgen_agent_router)
app.include_router(drg_agent_router)
init_assets()       # ensure asset dirs exist before mounting
mount_static(app)   # keep static router at the end
