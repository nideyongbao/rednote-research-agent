# RedNote Research Agent

基于 xiaohongshu-mcp 的小红书深度研究智能体，自动搜索、分析笔记并生成图文交错报告。

## 功能特性

- 🔍 **智能搜索** - 自动拆解研究主题为多个搜索关键词
- 📊 **数据分析** - 提取用户痛点、核心发现和建议
- 📝 **报告生成** - LLM 驱动的图文交错 HTML 报告
- 🌐 **Web 界面** - 实时 SSE 流式展示研究进度
- 🔐 **扫码登录** - 在设置页直接扫码登录小红书

---

## Docker 部署（进阶）

### 构建与推送镜像

本项目提供了辅助脚本用于构建和推送 Docker 镜像：

```bash
# 构建并推送到 Docker Hub
./scripts/build_and_push.sh [tag]

# 示例：构建 latest 版本
./scripts/build_and_push.sh

# 示例：构建 v1.0.0 版本
./scripts/build_and_push.sh v1.0.0
```

手动构建命令：

```bash
# 构建镜像
docker build -t brooksli1/rednote-research-agent:latest -f docker/Dockerfile .

# 推送镜像
docker push brooksli1/rednote-research-agent:latest
```

### 生产环境部署（仅拉取镜像）

如果你在服务器上部署，推荐使用 `docker-compose.prod.yml`，它会直接从 Docker Hub 拉取镜像而不进行构建：

```bash
# 1. 配置环境变量
cp .env.docker .env

# 2. 启动服务（使用 prod 配置）
docker compose -f docker-compose.prod.yml up -d
```

---

## 快速开始（Docker Compose）

### 1. 配置环境变量

复制并编辑环境变量文件 `cp .env.docker .env` 或直接创建 `.env.docker`：

```env
OPENAI_API_KEY=your-api-key-here
OPENAI_BASE_URL=https://api-inference.modelscope.cn/v1
OPENAI_MODEL=Qwen/Qwen3-235B-A22B-Thinking-2507
```

### 2. 启动服务

```bash
# 克隆项目
git clone https://github.com/user/rednote-research-agent.git
cd rednote-research-agent

# 启动所有服务
docker compose up -d

# 查看日志
docker compose logs -f
```

### 3. 访问并登录

1. 打开 **http://localhost:8000**
2. 进入 **设置** 页面
3. 点击 **获取登录二维码**
4. 用小红书 App 扫码登录
5. 返回首页开始研究！

---

## 开发模式

### 后端 + 前端分离开发

**终端 1 - 后端：**
```bash
pip install -e ./rednote_research
python -m uvicorn rednote_research.web.app:app --host 0.0.0.0 --port 8000
```

**终端 2 - 前端：**
```bash
cd rednote_research/frontend
npm install
npm run dev
```

**终端 3 - xiaohongshu-mcp（需要 Docker）：**
```bash
docker compose up xiaohongshu-mcp
```

访问 **http://localhost:5173**（前端开发服务器）

---

## 项目结构

```
rednote-research-agent/
├── docker-compose.yml      # Docker 编排配置
├── rednote_research/       # Python 研究智能体
│   ├── agents/             # 智能体层
│   ├── web/                # FastAPI 后端
│   │   └── app.py          # API 路由
│   ├── frontend/           # Vue.js 前端源码
│   └── .env                # 环境配置
├── data/                   # 数据持久化
│   ├── mcp/                # cookies (挂载共享)
│   └── images/             # 发布图片 (挂载共享)
└── reports/                # 报告输出
```

---

## Docker Compose 服务

| 服务 | 端口 | 说明 |
|------|------|------|
| `xiaohongshu-mcp` | 18060 | 小红书 MCP 服务（搜索、登录） |
| `rednote-research` | 8000 | 研究代理后端 + 前端 |

### 常用命令

```bash
# 启动所有服务
docker compose up -d

# 停止所有服务
docker compose down

# 重新构建并启动
docker compose up -d --build

# 仅重启 MCP 服务（登录失效时）
docker compose restart xiaohongshu-mcp
```

---

## API 接口

### MCP 登录相关

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/mcp/login/status` | 获取登录状态 |
| GET | `/api/mcp/login/qrcode` | 获取登录二维码 |
| POST | `/api/settings/test-mcp` | 测试 MCP 连接 |

### 研究流程

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/research?topic=xxx` | SSE 流式研究 |
| GET | `/api/history` | 历史记录列表 |
| GET | `/api/history/{id}/full` | 完整历史详情 |

---

## 环境变量

| 变量 | 说明 | 默认值 |
|------|------|--------|
| `OPENAI_API_KEY` | LLM API Key | 必填 |
| `OPENAI_BASE_URL` | LLM API 地址 | OpenAI 官方 |
| `OPENAI_MODEL` | 模型名称 | gpt-4o |
| `XIAOHONGSHU_MCP_URL` | MCP 服务地址 | http://localhost:18060 |

---

## 常见问题

### 1. 登录二维码获取失败？

确保 xiaohongshu-mcp 服务正在运行：
```bash
docker compose ps
docker compose logs xiaohongshu-mcp
```

### 2. 搜索无结果？

可能是登录已过期，在设置页重新扫码登录。

### 3. 前端无法访问后端？

开发模式下确保后端运行在 8000 端口，并且前端 `vite.config.ts` 配置了正确的代理。

---

## License

MIT
