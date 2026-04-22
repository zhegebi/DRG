from contextlib import asynccontextmanager

from fastapi import FastAPI

from .static import init_assets
from .static import router as static_router
from .storage import init_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    init_assets()
    yield
    # nothing to clean up on shutdown for now


app = FastAPI(lifespan=lifespan)

app.include_router(static_router)
