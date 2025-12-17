#!/bin/bash
set -e

echo "============================================"
echo "  RedNote Research Agent"
echo "============================================"
echo ""

# Check if MCP cookie exists (支持两种路径)
COOKIE_PATH="/root/.mcp/rednote/cookies.json"
if [ ! -f "$COOKIE_PATH" ]; then
    echo "⚠️  警告: 未检测到登录Cookie"
    echo "   Cookie路径: $COOKIE_PATH"
    echo ""
    echo "   请先在本地运行以下命令完成登录:"
    echo "   cd rednote-mcp && npm run dev -- init"
    echo ""
    echo "   然后将 cookie 复制到挂载目录:"
    echo "   cp ~/.mcp/rednote/cookies.json ./.mcp/rednote/"
    echo ""
    echo "   最后重启容器"
    echo ""
else
    echo "✅ 检测到登录Cookie"
fi

echo "🚀 启动Web服务..."
echo "   访问地址: http://localhost:8000"
echo ""

# Start the application with uvicorn
exec python -m uvicorn rednote_research.web.app:app --host 0.0.0.0 --port 8000
