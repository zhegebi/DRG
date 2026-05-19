from contextlib import asynccontextmanager

from fastapi import FastAPI

from .agent.docgen_agent.api import router as docgen_agent_router
from .agent.drg_agent.api import router as drg_agent_router
from .db import init_db
from .static import init_assets, mount_static
from .user.api import router as auth_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    init_assets()
    yield
    # nothing to clean up on shutdown for now


app = FastAPI(lifespan=lifespan)

app.include_router(auth_router)
app.include_router(docgen_agent_router)
app.include_router(drg_agent_router)
init_assets()  # ensure asset dirs exist before mounting
mount_static(app)  # keep static router at the end
