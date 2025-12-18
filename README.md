# RedNote Research Agent

基于 MCP 协议的小红书深度研究智能体，自动搜索、分析小红书笔记并生成研究报告。

> ⚠️ **重要提示**：本项目使用 Git Submodule 集成 [RedNote-MCP](https://github.com/iFurySt/RedNote-MCP)。克隆时请使用 `--recursive` 参数。

## 功能特性

- 🔍 **智能搜索**：自动拆解研究主题为多个搜索关键词
- 📊 **数据分析**：提取用户痛点、核心发现和建议
- 📝 **报告生成**：LLM 驱动的图文交错 HTML 报告
- 🌐 **Web 界面**：实时 SSE 流式展示研究进度

---

## 快速开始

### 1. 克隆项目

```bash
git clone --recursive https://github.com/user/rednote-research-agent.git
cd rednote-research-agent

# 如果忘记使用 --recursive，执行：
git submodule update --init
```

### 2. 安装 Python 依赖

```bash
# 进入项目根目录安装 Python 包
pip install -e ./rednote_research
```

### 3. 安装 MCP 服务依赖

```bash
cd rednote-mcp
npm install
npx playwright install chromium
npm run build
cd ..
```

### 4. 配置环境变量

编辑 `rednote_research/.env` 文件：

```env
# OpenAI 兼容的 API 配置
OPENAI_API_KEY=your-api-key-here
OPENAI_BASE_URL=https://api.openai.com/v1  # 或其他兼容端点
OPENAI_MODEL=gpt-4o  # 或其他模型

# MCP 服务器路径（相对于项目根目录）
REDNOTE_MCP_PATH=rednote-mcp/dist/index.js
```

**支持的 LLM 服务示例：**

```env
# OpenAI
OPENAI_API_KEY=sk-xxx
OPENAI_BASE_URL=https://api.openai.com/v1
OPENAI_MODEL=gpt-4o

# ModelScope (通义千问)
OPENAI_API_KEY=your-modelscope-key
OPENAI_BASE_URL=https://api-inference.modelscope.cn/v1
OPENAI_MODEL=Qwen/Qwen3-235B-A22B-Thinking-2507
```

### 5. 小红书登录（必需）

首次使用需要登录小红书以获取 Cookie：

```bash
cd rednote-mcp
node dist/cli.js init
```

> 💡 这会打开浏览器窗口，请用小红书 APP 扫码登录。登录成功后 Cookie 会自动保存到 `~/.mcp/rednote/cookies.json`。

### 6. 启动服务

> ⚠️ **Windows 用户注意**：不要使用 `--reload` 参数，会导致 asyncio 子进程问题！

```bash
# 启动后端服务
python -m uvicorn rednote_research.web.app:app --host 0.0.0.0 --port 8000
```

访问 http://localhost:8000 即可使用。

---

## 前端开发模式（可选）

如果需要修改前端代码，可以使用 Vite 开发服务器：

```bash
# 终端 1：启动后端
python -m uvicorn rednote_research.web.app:app --port 8000

# 终端 2：启动前端开发服务器
cd rednote_research/frontend
npm install
npm run dev
```

访问 http://localhost:5173 使用前端开发模式（支持热更新）。

---

## Cookie 过期处理

如果搜索时提示登录失效，需要重新登录：

```bash
cd rednote-mcp
node dist/cli.js init
```

---

## 项目结构

```
rednote-research-agent/
├── rednote_research/       # Python 研究智能体
│   ├── agents/             # 智能体层（Planner/Searcher/Analyzer）
│   ├── mcp/                # MCP 客户端封装
│   ├── output/             # 报告生成器
│   ├── services/           # 业务服务（历史记录/设置）
│   ├── web/                # Web 界面（FastAPI）
│   │   └── static/         # 前端构建产物（生产环境）
│   ├── frontend/           # 前端源码（Vue.js）
│   ├── .env                # 环境变量配置
│   └── pyproject.toml      # Python 包配置
├── rednote-mcp/            # 小红书 MCP 服务器（Git Submodule）
├── reports/                # 报告输出目录
└── README.md
```

---

## 常见问题

### 如何查看报告？

报告保存在 `./reports/` 目录下，也可以在 Web 界面直接下载。

### 如何更换 LLM 模型？

编辑 `rednote_research/.env` 文件，修改 `OPENAI_*` 相关配置。支持任何 OpenAI 兼容 API。

### 研究卡住或超时？

- 检查 LLM API Key 是否有效
- 检查小红书 Cookie 是否过期（重新执行 `node dist/cli.js init`）
- 查看终端输出的错误信息

### Windows 下启动报错？

确保不要使用 `--reload` 参数启动 uvicorn，这会导致 asyncio 子进程不兼容问题。

---

## License

MIT
