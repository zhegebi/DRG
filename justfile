set shell         := ["bash", "-c"]
set windows-shell := ["powershell.exe", "-NoLogo", "-Command"]

root              := justfile_directory()
server_dir        := root / "server"
client_dir        := root / "client"
client_output_dir := client_dir / "dist"

# 跨平台的命令连接符：Unix 用 &&，Windows 用 ;
and := if os_family() == "windows" { ";" } else { "&&" }

# 列出所有recipe
list:
    @just --list --unsorted
alias l := list

# 安装所有依赖
install:
    cd "{{client_dir}}" {{and}} npm install
    uv sync
alias i := install

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
alias c := clean