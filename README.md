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
git clone https://github.com/user/rednote-research-agent.git
cd rednote-research-agent
```

### 2. 安装 Python 依赖

```bash
# 推荐使用 conda 环境
conda create -n rednote-research python=3.11
conda activate rednote-research

# 安装依赖
cd rednote_research
pip install -e .
pip install httpx  # HTTP 客户端（必需）
```

### 3. 下载 xiaohongshu-mcp 服务

从 [xiaohongshu-mcp Releases](https://github.com/xpzouying/xiaohongshu-mcp/releases) 下载对应系统的预编译文件：

- Windows: `xiaohongshu-mcp-windows-amd64.exe` + `xiaohongshu-login-windows-amd64.exe`
- macOS: `xiaohongshu-mcp-darwin-amd64`
- Linux: `xiaohongshu-mcp-linux-amd64`

### 4. 小红书登录（必需）

```bash
# Windows
.\xiaohongshu-login-windows-amd64.exe

# macOS/Linux
./xiaohongshu-login-darwin-amd64
```

> 💡 浏览器会打开小红书登录页，用 APP 扫码登录。Cookie 自动保存到 `./cookies/` 目录。

### 5. 配置环境变量

编辑 `rednote_research/.env`：

```env
OPENAI_API_KEY=your-api-key-here
OPENAI_BASE_URL=https://api-inference.modelscope.cn/v1
OPENAI_MODEL=gpt-4o

# xiaohongshu-mcp 服务地址
XIAOHONGSHU_MCP_URL=http://localhost:18060
```

---

## 启动服务

### 开发模式（推荐）

需要**三个终端**：

**终端 1 - xiaohongshu-mcp 服务：**
```bash
# Windows
.\xiaohongshu-mcp-windows-amd64.exe

# macOS/Linux
./xiaohongshu-mcp-darwin-amd64
```

> 服务启动后在 http://localhost:18060 运行

**终端 2 - 后端：**
```bash
conda activate rednote-research
cd rednote-research-agent
python -m uvicorn rednote_research.web.app:app --host 0.0.0.0 --port 8000
```

**终端 3 - 前端：**
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
22:27:58
info
开始研究主题: 上海临港低成本奶茶店创业，注意地点和资金要求
22:27:59
info
🚀 开始研究: 上海临港低成本奶茶店创业，注意地点和资金要求
22:27:59
success
进入阶段: 规划
22:27:59
info
📡 连接小红书MCP服务...
22:28:01
success
✅ MCP连接成功
22:28:01
info
📋 [Planner] 分析研究主题...
22:28:40
success
📋 [Planner] 生成了 5 个搜索关键词
22:28:40
info
💡 理解: 用户想了解在上海临港地区以低成本开设奶茶店的创业可行性，重点关注选址策略和资金预算的具体要求。
22:28:40
info
📊 维度: 选址策略分析, 资金预算规划, 市场竞争评估, 低成本运营方案
22:28:40
info
- 临港 奶茶店
22:28:40
info
- 奶茶店 低成本
22:28:40
info
- 临港 创业 资金
22:28:40
info
- 低成本 创业 避雷
22:28:40
info
- 奶茶店 选址 要求
22:28:40
info
📐 [阶段1统计] 关键词: 5个 | 维度: 4个 | LLM调用: 1次
22:28:40
success
进入阶段: 搜索
22:28:40
info
🔍 [Searcher] 开始搜索笔记...
22:30:14
info
[Searcher] 开始搜索 5 个关键词
22:30:14
info
[Searcher] 搜索关键词 [1/5]: 临港 奶茶店
22:30:14
info
[Searcher] 找到 1 篇笔记
22:30:14
info
[Searcher] 获取详情 [1/1]: 记录临港美食之甜品饮料篇【自用版】...
22:30:14
info
[Searcher] 搜索关键词 [2/5]: 奶茶店 低成本
22:30:14
info
[Searcher] 找到 1 篇笔记
22:30:14
info
[Searcher] 获取详情 [1/1]: 谈谈卷王赛道！倒闭的奶茶店都没避开这些坑...
22:30:14
info
[Searcher] 搜索关键词 [3/5]: 临港 创业 资金
22:30:14
info
[Searcher] 找到 1 篇笔记
22:30:14
info
[Searcher] 获取详情 [1/1]: 上海AI创业疯抢补贴！10亿红包+免租+算力券...
22:30:14
info
[Searcher] 搜索关键词 [4/5]: 低成本 创业 避雷
22:30:14
info
[Searcher] 找到 1 篇笔记
22:30:14
info
[Searcher] 获取详情 [1/1]: 每天避坑一种副业（1/365）...
22:30:14
info
[Searcher] 搜索关键词 [5/5]: 奶茶店 选址 要求
22:30:14
info
[Searcher] 找到 0 篇笔记
22:30:14
info
[Searcher] 搜索完成，共收集 4 篇笔记，总计 4 篇
22:30:14
success
🔍 [Searcher] 收集了 4 篇笔记
22:30:14
info
📊 [统计] 共 24 张图片，总文本 1622 字，平均每篇 405 字
22:30:14
success
进入阶段: 分析
22:30:14
info
🧠 [Analyzer] 分析数据中...
22:30:43
success
🧠 [Analyzer] 提取了 3 条核心发现
22:30:43
info
📐 [阶段3统计] 分析笔记: 4篇 | 提取发现: 3条 | LLM调用: 1次
22:30:43
info
🖼️ [ImageAnalyzer] VLM分析图片...
22:31:36
info
[ImageAnalyzer] 图片去重: 24张 → 16张 (去除8张重复)
22:31:36
success
🖼️ [ImageAnalyzer] 分析了 16 张图片，12 张可用
22:31:36
info
📐 [阶段4统计] 分类: 实景:8, 攻略:4, 策略:2, 广告:1, 信息表:1 | VLM调用: 2次
22:31:36
success
进入阶段: 生成
22:31:36
info
📑 [OutlineGenerator] 生成结构化大纲（含图片上下文）...
22:33:15
success
📑 [OutlineGenerator] 生成了 6 个章节
22:33:15
info
📐 [阶段5统计] 章节数: 6 | LLM调用: 1次
22:33:15
info
🎯 [ImageAssigner] 分配图片到章节...
22:33:26
info
[ImageAssigner] 章节'深度分析：资金优化与政策对接路径' 匹配分数过低(7<8)，生成1张
22:33:26
success
🎯 [ImageAssigner] 分配了 12 张图片
22:33:26
info
📐 [阶段6统计] 分配图片: 12张
22:33:26
info
📝 [Writer] 生成图文交错报告...
22:34:32
success
✅ 报告生成完成！
22:34:32
info
📐 [阶段7统计] 报告HTML长度: 14389字符 | 章节数: 6 | LLM调用: 7次
22:34:32
success
加载了 6 个结构化章节
22:34:32
success
研究完成！点击"编辑大纲"继续
```

## 数据流设计：

```
┌─────────────────────────────────────────────────────────────────┐
│                        数据流隔离设计                            │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  【进行中任务】                    【历史编辑】                   │
│                                                                 │
│  activeTask.ts (NEW)              research.ts (原有)            │
│  ├── taskId                       ├── topic                    │
│  ├── topic                        ├── outline                  │
│  └── isRunning                    ├── notes                    │
│          ↓                        └── keyFindings              │
│  HomeView（显示入口卡片）                   ↑                    │
│          ↓                                 │                    │
│  ResearchView（进度日志）          HistoryView（点击加载）       │
│          ↓ 完成                            │                    │
│  clearTask()                      /api/history/{id}/full       │
│                                            ↓                    │
│                                   loadFromJSON()               │
│                                            ↓                    │
│                                   OutlineView（编辑）           │
│                                            ↓                    │
│                                   ReportView（预览）            │
└─────────────────────────────────────────────────────────────────┘
```

## License

MIT
