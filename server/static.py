from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .config import FRONTEND_ASSETS_DIR, FRONTEND_DIR

"""
The module to provide static assets apis.
"""

ALL_PAGE_ROUTERS = {"/", "/drg", "/doc"}


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

    @app.get("/")
    async def root():
        return FileResponse(FRONTEND_DIR / "index.html")

    @app.get("/{full_path:path}")
    async def serve_spa(full_path: str):
        # static files
        file_path = FRONTEND_DIR / full_path
        if file_path.is_file():
            return FileResponse(file_path)

        # wrong API endpoint
        if full_path.startswith("api"):
            raise HTTPException(status_code=404, detail="API endpoint not found")

        # SPA routes
        normalized_path = f"/{full_path}"
        if normalized_path in ALL_PAGE_ROUTERS:
            return FileResponse(FRONTEND_DIR / "index.html")

        raise HTTPException(status_code=404, detail="Page not found")
