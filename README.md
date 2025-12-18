# RedNote Research Agent

基于 MCP 协议的小红书深度研究智能体，一键 Docker 部署。

> ⚠️ **重要提示**：本项目使用 Git Submodule 集成 [RedNote-MCP](https://github.com/iFurySt/RedNote-MCP)。克隆时请使用 `--recursive` 参数，或在克隆后执行 `git submodule update --init`。

## 功能特性

- 🔍 智能搜索：自动拆解研究主题为多个搜索关键词
- 📊 数据分析：提取用户痛点、核心发现和建议
- 📝 报告生成：LLM 驱动的图文交错 HTML 报告
- 🌐 Web 界面：实时 SSE 流式展示研究进度
- 🐳 Docker 部署：一键启动，开箱即用

---

## 方式一：Docker 镜像拉取（推荐用户使用）

### 1. 拉取镜像

```bash
docker pull brooksli1/rednote-research-agent:latest 
```

### 2. 创建配置文件

创建一个目录用于存放配置：

```bash
mkdir rednote-research && cd rednote-research
```

创建 `docker-compose.yml`：

```yaml
services:
  rednote-research:
    image: your-username/rednote-research-agent:latest
    ports:
      - "8000:8000"
    env_file:
      - .env
    volumes:
      - ./reports:/app/reports
      - ./.mcp/rednote:/root/.mcp/rednote
    restart: unless-stopped
```

创建 `.env` 文件并填入你的 API Key：

```env
OPENAI_API_KEY=your-api-key-here
OPENAI_BASE_URL=https://api.openai.com/v1
OPENAI_MODEL=gpt-4o

# 如果使用 ModelScope:
# OPENAI_API_KEY=your-modelscope-api-key
# OPENAI_BASE_URL=https://api-inference.modelscope.cn/v1
# OPENAI_MODEL=Qwen/Qwen2.5-72B-Instruct
```

### 3. 小红书登录（必需）

首次使用需要在本地完成小红书登录：

```bash
# 克隆 RedNote-MCP 仓库（用于本地登录）
git clone https://github.com/iFurySt/RedNote-MCP.git
cd RedNote-MCP

# 安装依赖并安装 Playwright 浏览器
npm install
npx playwright install chromium

# 登录（会打开浏览器扫码，超时时间 60 秒）
npm run build
node dist/cli.js init 60

# 复制 cookie 到项目目录
mkdir -p ../rednote-research/.mcp/rednote
cp ~/.mcp/rednote/cookies.json ../rednote-research/.mcp/rednote/
```

### 4. 启动服务

```bash
cd rednote-research
docker-compose up -d
```

访问 http://localhost:8000

---

## 方式二：本地构建 Docker 镜像

### 1. 克隆项目

```bash
git clone --recursive https://github.com/user/rednote-research-agent.git
cd rednote-research-agent

# 如果忘记使用 --recursive，可以执行：
# git submodule update --init
```

### 2. 配置环境变量

编辑 `.env.docker` 文件，填入你的 API Key：

```env
OPENAI_API_KEY=your-api-key-here
OPENAI_BASE_URL=https://api.openai.com/v1
OPENAI_MODEL=gpt-4o
```

### 3. 小红书登录

```bash
cd rednote-mcp
npm install
npx playwright install chromium
npm run build
node dist/cli.js init 60
```

> 💡 登录时会弹出浏览器窗口，请用小红书 APP 扫码登录。超时时间为 60 秒。

登录成功后，复制 cookie：

```bash
mkdir -p ../.mcp/rednote
cp ~/.mcp/rednote/cookies.json ../.mcp/rednote/
```

### 4. 构建并启动

```bash
cd ..
docker-compose build
docker-compose up -d
```

---

## 方式三：本地开发（推荐开发者使用）

### 1. 克隆项目

```bash
git clone --recursive https://github.com/user/rednote-research-agent.git
cd rednote-research-agent

# 如果忘记使用 --recursive，执行：
# git submodule update --init
```

### 2. 安装依赖

```bash
# Python 环境（从 rednote_research 目录安装）
pip install -e ./rednote_research

# MCP 服务依赖
cd rednote-mcp
npm install
npx playwright install chromium
npm run build
```

### 3. 小红书登录

```bash
# 首次使用需要登录（会弹出浏览器窗口扫码）
cd rednote-mcp
node dist/cli.js init 60
```

### 4. 配置环境变量

编辑 `rednote_research/.env` 文件：

```env
# OpenAI API配置
OPENAI_API_KEY=your-api-key-here
OPENAI_BASE_URL=https://api-inference.modelscope.cn/v1
OPENAI_MODEL=Qwen/Qwen3-235B-A22B-Thinking-2507

# MCP服务器路径（支持相对路径）
REDNOTE_MCP_PATH=rednote-mcp/dist/index.js
```

### 5. 启动服务

> ⚠️ **重要提示**：由于 Windows 下 uvicorn 的 `--reload` 模式与 asyncio 子进程不兼容，**不要使用 `--reload` 参数**！

```bash
# 启动后端（不使用 --reload）
python -m uvicorn rednote_research.web.app:app --port 8000

# 另一个终端：启动前端开发服务器
cd rednote_research/frontend
npm install
npm run dev
```

访问 http://localhost:5173（前端开发服务器）或 http://localhost:8000（后端）

### 开发建议

- **后端热重载替代方案**：修改后端代码后，手动重启 uvicorn 进程
- **前端热重载**：正常使用 Vite 的 HMR 功能，无需特殊处理

## Cookie 过期处理

如果搜索时提示登录失效或 Cookie 过期，需要重新登录：

```bash
# 进入 rednote-mcp 目录
cd rednote-mcp

# 重新登录（会打开浏览器扫码）
npm run dev -- init

# 复制新的 cookie
cp ~/.mcp/rednote/cookies.json ../.mcp/rednote/

# 重启容器
docker-compose restart
```

---

## 项目结构

```
rednote-research-agent/
├── docker/
│   ├── Dockerfile          # 多阶段构建配置
│   └── entrypoint.sh       # 容器启动脚本
├── rednote_research/       # Python 研究智能体
│   ├── agents/             # 智能体层
│   ├── mcp/                # MCP 客户端
│   ├── output/             # 报告生成
│   └── web/                # Web 界面
├── rednote-mcp/            # Node.js MCP 服务器
├── .mcp/                   # Cookie 存储目录
├── reports/                # 报告输出目录
├── docker-compose.yml
└── .env.docker
```

---

## 常见问题

### 如何查看报告？

报告保存在 `./reports/` 目录下，也可以在 Web 界面直接下载。

### 如何更换 LLM 模型？

编辑 `.env` 或 `.env.docker` 文件，修改相关配置。支持任何 OpenAI 兼容 API。

### 容器启动失败？

查看日志：
```bash
docker-compose logs -f
```

---

## License

MIT
