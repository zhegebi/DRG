# DRG 项目运行指南

## 环境准备
- Node.js 18+
- npm
- uv（[安装指南](https://docs.astral.sh/uv/)）

## 安装依赖

```bash
# 前端
cd client && npm install

# 后端
cd server && uv sync
```

## 运行 (根目录执行)

### 开发模式（前端热重载 + 后端热重载）

```bash
uv run --directory server dev
```

- 前端：http://localhost:5173
- 后端：http://localhost:8000

### 生产模式（构建前端 + 后端托管）

```bash
uv run --directory server prod
```

- 先执行 `npm run build` 构建前端
- 后端启动并托管静态文件：http://localhost:8000

## 停止

在终端按 `Ctrl + C`。