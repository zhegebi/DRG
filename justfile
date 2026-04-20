set shell         := ["bash", "-c"]
set windows-shell := ["powershell.exe", "-NoLogo", "-Command"]

root              := justfile_directory()
server_dir        := root / "server"
client_dir        := root / "client"
client_output_dir := client_dir / "dist"
openapi_file      := server_dir / "openapi.json"

# cross-platform tools
and := if os_family() == "windows" { ";" } else { "&&" }

# List all recipe
list:
    @just --list --unsorted
alias l := list

# Install dependencies
install:
    cd "{{client_dir}}" {{and}} npm install
    uv sync
alias i := install

# Format and type check
check:
    cd "{{client_dir}}" {{and}} npm run type-check
    uv run ruff check
    uv run ty check
alias ck := check

# Dev mode: support hot reload for both frontend and backend
[parallel]
dev: _dev-frontend _dev-backend
alias d := dev

_dev-frontend:
    cd "{{client_dir}}" {{and}} npm run dev

_dev-backend:
    uv run uvicorn server.main:app --reload --port 8000

# Production mode: build frontend and run server
prod:
    cd "{{client_dir}}" {{and}} npm run build
    uv run uvicorn server.main:app --port 8000
alias p := prod

# Clean build artifacts and cache
clean:
    npx shx rm -rf "{{client_output_dir}}"
    npx shx rm -rf "**/__pycache__"
alias cl := clean

extract_script := "
import json
from server.main import app
with open('" + openapi_file + "', 'w', encoding='utf-8') as f:
    json.dump(app.openapi(), f)
"

# Generate API client from OpenAPI spec
gen: 
    # Extracting OpenAPI spec from FastAPI app..."
    uv run python -c "{{extract_script}}"
    # Generating Frontend API client...
    cd "{{client_dir}}" {{and}} npx openapi-ts -i ../server/openapi.json -o src/api -c @hey-api/client-axios
    npx shx rm -f "{{openapi_file}}"
alias g := gen
