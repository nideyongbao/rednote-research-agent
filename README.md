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

# 如果忘记使用 --recursive：
git submodule update --init
```

### 2. 安装 Python 依赖

```bash
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

### 4. 小红书登录（必需）

```bash
cd rednote-mcp
node dist/cli.js init
```

> 💡 浏览器会打开小红书登录页，用 APP 扫码登录。Cookie 自动保存到 `~/.mcp/rednote/cookies.json`。

### 5. 配置环境变量

编辑 `rednote_research/.env`：

```env
OPENAI_API_KEY=your-api-key-here
OPENAI_BASE_URL=https://api-inference.modelscope.cn/v1
OPENAI_MODEL=gpt-4o
REDNOTE_MCP_PATH=rednote-mcp/dist/index.js
```

---

## 启动服务

### 开发模式（推荐）

需要**两个终端**：

**终端 1 - 后端：**
```bash
cd rednote-research-agent
python -m uvicorn rednote_research.web.app:app --host 0.0.0.0 --port 8000
```

**终端 2 - 前端：**
```bash
cd rednote-research-agent/rednote_research/frontend
npm install
npm run dev
```

访问 **http://localhost:5173**

> ⚠️ Windows 用户：后端不要使用 `--reload` 参数！

### 生产模式（单服务）

```bash
# 1. 构建前端
cd rednote_research/frontend
npm install && npm run build

# 2. 复制到 static 目录
xcopy /E /Y dist\* ..\web\static\

# 3. 启动服务
cd ../..
python -m uvicorn rednote_research.web.app:app --host 0.0.0.0 --port 8000
```

访问 **http://localhost:8000**

---

## Cookie 过期处理

```bash
cd rednote-mcp
node dist/cli.js init
```

---

## 项目结构

```
rednote-research-agent/
├── rednote_research/       # Python 研究智能体
│   ├── agents/             # 智能体层
│   ├── mcp/                # MCP 客户端
│   ├── web/                # FastAPI 后端
│   ├── frontend/           # Vue.js 前端源码
│   └── .env                # 环境配置
├── rednote-mcp/            # MCP 服务器 (submodule)
└── reports/                # 报告输出
```

## 日志示例

```
18:50:30
info
开始研究主题: 旅行攻略
18:50:30
info
🚀 开始研究: 旅行攻略
18:50:30
success
进入阶段: 规划
18:50:30
info
📡 连接小红书MCP服务...
18:50:32
success
✅ MCP连接成功
18:50:32
info
📋 [Planner] 分析研究主题...
18:50:52
success
📋 [Planner] 生成了 5 个搜索关键词
18:50:52
info
- 旅行攻略2025最新版
18:50:52
info
- 旅行攻略避雷指南
18:50:52
info
- 保姆级旅行攻略教程
18:50:52
info
- 旅行攻略省钱秘籍
18:50:52
info
- 旅行攻略安全必备
18:50:52
info
📐 [阶段1统计] 关键词: 5个 | 维度: 5个 | LLM调用: 1次
18:50:52
success
进入阶段: 搜索
18:50:52
info
🔍 [Searcher] 开始搜索笔记...
19:07:41
success
🔍 [Searcher] 收集了 5 篇笔记
19:07:41
info
📊 [统计] 共 48 张图片，总文本 2080 字，平均每篇 416 字
19:07:41
success
进入阶段: 分析
19:07:41
info
🧠 [Analyzer] 分析数据中...
19:08:22
success
🧠 [Analyzer] 提取了 4 条核心发现
19:08:22
info
📐 [阶段3统计] 分析笔记: 5篇 | 提取发现: 4条 | LLM调用: 1次
19:08:22
success
进入阶段: 生成
19:08:22
info
📑 [OutlineGenerator] 生成结构化大纲...
19:09:52
success
📑 [OutlineGenerator] 生成了 7 个章节
19:09:52
info
📐 [阶段4统计] 章节数: 7 | LLM调用: 1次
19:09:52
info
🖼️ [ImageProcessor] 处理图片...
19:12:44
success
🖿️ [ImageProcessor] 图片处理完成
19:12:44
info
📐 [阶段5统计] 收集图片: 48张 | VLM批次: 3 | 分配图片: 10张
19:12:44
info
📝 [Writer] 生成图文交错报告...
19:14:24
success
✅ 报告生成完成！
19:14:24
info
📐 [阶段6统计] 报告HTML长度: 17978字符 | 章节数: 7 | LLM调用: 8次
19:14:24
success
加载了 7 个结构化章节
19:14:24
success
研究完成！

```


## License

MIT
