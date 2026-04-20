import os
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .api import router as api_router
from .storage import init_db

init_db()

app = FastAPI()

frontend_dist_path = Path("./client/dist")
if not frontend_dist_path.exists():
    frontend_dist_path.mkdir(parents=True, exist_ok=True)

frontend_assets_path = frontend_dist_path / "assets"
if not frontend_assets_path.exists():
    frontend_assets_path.mkdir(parents=True, exist_ok=True)

# 挂载 /assets 目录（前端构建后的静态资源）
app.mount(
    "/assets",
    StaticFiles(directory=frontend_assets_path),
    name="assets",
)


# 根路径路由
@app.get("/")
async def root():
    return FileResponse(frontend_dist_path / "index.html")


# API 路由
app.include_router(api_router, prefix="/api")


# 最后：catch-all 路由，用于前端 SPA 的 history 模式
# 返回 index.html，让 Vue Router 根据 URL 显示对应的前端页面。
# 如果请求的是 API 路径，返回 Not Found。
@app.get("/{full_path:path}")
async def serve_spa(full_path: str):
    index_path = os.path.join(frontend_dist_path, "index.html")
    if full_path.startswith("api"):
        return {"detail": "Not Found"}
    if os.path.exists(index_path):
        return FileResponse(index_path)
    else:
        return {"detail": "Frontend not built yet. Run 'npm run build' in client directory."}
