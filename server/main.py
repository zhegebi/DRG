from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import os


app = FastAPI()

# 静态资源挂载（前端构建后的 assets 目录）
# 注意：路径是相对于当前 main.py 的位置（server 目录）
frontend_dist_path = "../client/dist"

# 挂载 /assets 目录（前端构建后的静态资源）
app.mount(
    "/assets",
    StaticFiles(directory=os.path.join(frontend_dist_path, "assets")),
    name="assets",
)

# 根路径路由
@app.get("/")
async def root():
    return FileResponse(os.path.join(frontend_dist_path, "index.html"))

# API 路由（必须放在静态挂载之后，但放在 catch-all 之前）
@app.get("/api/hello")
async def hello():
    return {"message": "Hello from FastAPI"}


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