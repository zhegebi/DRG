set shell := ["bash", "-c"]

root        := justfile_directory()
server_dir  := root / "server"
client_dir  := root / "client"

# 默认列出所有任务
default:
    @just --list

# 开发模式：前端热重载 + 后端热重载
dev:
    @echo "🚀 启动开发模式..."
    (cd {{client_dir}} && npm run dev) & \
    (cd {{server_dir}} && uv run uvicorn main:app --reload --port 8000)

# 生产模式：构建前端并启动后端托管
prod:
    @echo "🏗️ 生产模式..."
    cd {{client_dir}} && npm run build
    @echo "🚀 启动后端服务器 (http://localhost:8000)"
    cd {{server_dir}} && uv run uvicorn main:app --port 8000

# 安装所有依赖
install:
    @echo "📦 安装依赖..."
    cd {{client_dir}} && npm install
    uv sync

# 清理构建产物
clean:
    rm -rf {{client_dir}}/dist
    find . -type d -name "__pycache__" -exec rm -rf {} +
