from contextlib import asynccontextmanager

from fastapi import FastAPI

from .db import init_db
from .static import init_assets, mount_static
from .user.api import router as auth_router
from .agent.api import router as agent_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    init_assets()
    yield
    # nothing to clean up on shutdown for now


app = FastAPI(lifespan=lifespan)

app.include_router(auth_router)
app.include_router(agent_router)
mount_static(app)  # keep static router at the end
