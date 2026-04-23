from fastapi import APIRouter, FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .config import FRONTEND_ASSETS_DIR, FRONTEND_DIR

"""
The module to provide static assets apis.
"""

router = APIRouter()


def init_assets():
    if not FRONTEND_DIR.exists():
        FRONTEND_DIR.mkdir(parents=True, exist_ok=True)

    if not FRONTEND_ASSETS_DIR.exists():
        FRONTEND_ASSETS_DIR.mkdir(parents=True, exist_ok=True)


def mount_static(app: FastAPI):
    app.mount(
        "/assets",
        StaticFiles(directory=FRONTEND_ASSETS_DIR),
        name="assets",
    )


@router.get("/")
async def root():
    return FileResponse(FRONTEND_DIR / "index.html")
