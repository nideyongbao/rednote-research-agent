# RedNote Research Agent

基于 MCP 协议的小红书深度研究智能体，支持自动搜索、分析笔记并生成图文交错的HTML报告。

## 功能特性

- 🔍 **智能搜索**: 自动将研究主题拆解为多个搜索关键词
- 📊 **数据分析**: 提取用户痛点、核心发现和建议
- 📝 **报告生成**: LLM驱动的图文交错HTML报告
- 🌐 **Web界面**: 实时SSE流式展示研究进度
- 🖥️ **CLI工具**: 命令行一键执行研究任务

## 项目结构

```
rednote_research/
├── mcp/              # MCP客户端层
│   ├── client.py     # MCP基础客户端
│   └── rednote.py    # 小红书专用客户端
├── agents/           # 智能体层
│   ├── base.py       # 智能体基类
│   ├── planner.py    # 规划智能体
│   ├── searcher.py   # 搜索智能体
│   ├── analyzer.py   # 分析智能体
│   └── orchestrator.py # 编排器
├── output/           # 输出生成层
│   └── html_generator.py
├── web/              # Web界面层
│   └── app.py
├── config.py         # 配置管理
├── state.py          # 共享状态定义
└── cli.py            # 命令行入口
```

## 快速开始

### 1. 安装依赖

```bash
cd rednote_research
pip install -e .
```

### 2. 配置环境变量

创建 `.env` 文件或设置环境变量：

```bash
# OpenAI API配置
OPENAI_API_KEY=your-api-key
OPENAI_BASE_URL=https://api.openai.com/v1  # 可选，自定义端点
OPENAI_MODEL=gpt-4o  # 可选，默认gpt-4o

# MCP服务器路径
REDNOTE_MCP_PATH=/path/to/rednote-mcp/dist/index.js
```

### 3. 使用方式

#### CLI命令行

```bash
# 执行研究任务
rednote-research research "冬天上海旅游3天2晚攻略" --mcp /path/to/mcp/server

# 启动Web服务
rednote-research server --port 8000
```

#### Web界面

```bash
# 启动Web服务
python -m rednote_research.web.app

# 访问 http://localhost:8000
```

#### Python API

```python
import asyncio
from rednote_research.config import Config
from rednote_research.mcp.rednote import RedNoteMCPClient
from rednote_research.agents.orchestrator import ResearchOrchestrator

async def main():
    config = Config.from_env()
    mcp_client = RedNoteMCPClient("/path/to/mcp/server")
    
    async with ResearchOrchestrator(config, mcp_client) as orchestrator:
        state = await orchestrator.run("2025年露营装备推荐")
        print(f"收集了 {len(state.documents)} 篇笔记")

asyncio.run(main())
```

## 依赖要求

- Python >= 3.10
- rednote-mcp: 小红书MCP服务器
- OpenAI API 或兼容接口

## 工作流程

```
用户任务 → Planner(规划) → Searcher(搜索) → Analyzer(分析) → HTML报告
              ↑                                    ↓
              └──────── 反思循环(如需补充数据) ←────┘
```

## License

MIT
