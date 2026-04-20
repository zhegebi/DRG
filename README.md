# DRG
## 开发
### 环境要求
- Node.js
- npm
- uv（[安装指南](https://docs.astral.sh/uv/)）
- just (可通过`cargo install just`安装)

### 安装依赖
该操作会自动安装前端 npm 依赖和后端 python 依赖。
```bash
just install
```

### 运行 
#### 开发模式: 前端热重载 + 后端热重载
*注：如果使用的是 VS Code，会自动在后台启动开发服务器*
```bash
just dev
```
该脚本会自动打开[前端网页](http://localhost:5173)和[后端服务器](http://localhost:8000)

#### 生产模式: 构建前端 + 后端托管
```bash
just prod
```
该脚本会自动构建前端并启动后端服务器，并启动[服务器](http://localhost:8000)

### 清理
```bash
just clean
```

### 生成前端 API 客户端代码
```bash
just gen
```

### 代码检查
```bash
just check
```