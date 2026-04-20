set shell         := ["bash", "-c"]
set windows-shell := ["powershell.exe", "-NoLogo", "-Command"]

root              := justfile_directory()
server_dir        := root / "server"
client_dir        := root / "client"
client_output_dir := client_dir / "dist"
openapi_file   := server_dir / "openapi.json"

# 跨平台工具命令
and := if os_family() == "windows" { ";" } else { "&&" }
rm := if os_family() == "windows" { "cmd /c del /q /f" } else { "rm -f" }

# 列出所有recipe
list:
    @just --list --unsorted
alias l := list

# 安装所有依赖
install:
    cd "{{client_dir}}" {{and}} npm install
    uv sync
alias i := install

# 格式检查
check:
    cd "{{client_dir}}" {{and}} npm run type-check
    uv run ruff check
    uv run ty check
alias ck := check

# 开发模式：前端热重载 + 后端热重载
[parallel]
dev: _dev-frontend _dev-backend
alias d := dev

_dev-frontend:
    cd "{{client_dir}}" {{and}} npm run dev

_dev-backend:
    cd "{{server_dir}}" {{and}} uv run uvicorn main:app --reload --port 8000

# 生产模式：构建前端并启动后端托管
prod:
    cd "{{client_dir}}" {{and}} npm run build
    cd "{{server_dir}}" {{and}} uv run uvicorn main:app --port 8000
alias p := prod

# 清理构建产物
[unix]
clean:
    rm -rf "{{client_output_dir}}"
    find . -type d -name "__pycache__" -exec rm -rf {} +

[windows]
clean:
    if exist "{{client_output_dir}}" rmdir /s /q "{{client_output_dir}}"
    for /d /r . %d in (__pycache__) do @if exist "%d" rmdir /s /q "%d"
alias cl := clean

# 自动根据后端接口定义生成前端 API 客户端代码
gen: 
    @echo "Extracting OpenAPI spec from FastAPI app..."
    cd "{{server_dir}}" && uv run python -c \
        "import json; from main import app; print(json.dumps(app.openapi()))" > "{{openapi_file}}"
    @echo "Generating Frontend API client..."
    cd "{{client_dir}}" && npx openapi-ts -i ../server/openapi.json -o src/api -c @hey-api/client-axios
    {{rm}} "{{openapi_file}}"
alias g := gen
