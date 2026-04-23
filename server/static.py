import os

from fastapi import APIRouter, FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .config import FRONTEND_ASSETS_DIR, FRONTEND_DIR

"""
The module to provide static assets apis.
"""

ALL_PAGE_ROUTERS = {"/", "/drg", "/doc"}

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


@router.get("/{full_path:path}")
async def serve_spa(full_path: str):
    index_path = os.path.join(FRONTEND_DIR, "index.html")
    if full_path.startswith("api"):
        raise HTTPException(status_code=404, detail="API endpoint not found")
    if full_path not in ALL_PAGE_ROUTERS:
        raise HTTPException(status_code=404, detail="Page not found")
    return FileResponse(index_path)
