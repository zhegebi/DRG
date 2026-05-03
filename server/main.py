from contextlib import asynccontextmanager

from fastapi import FastAPI
from dotenv import load_dotenv

from .db import init_db
from .static import init_assets, mount_static
from .static import router as static_router
from .user.api import router as auth_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    init_assets()
    load_dotenv()
    yield
    # nothing to clean up on shutdown for now


app = FastAPI(lifespan=lifespan)

app.include_router(auth_router)
app.include_router(static_router)  # keep static router at the end
mount_static(app)
