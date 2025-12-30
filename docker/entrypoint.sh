#!/bin/bash
set -e

echo "============================================"
echo "  RedNote Research Agent"
echo "============================================"
echo ""

# Check if MCP cookie exists
COOKIE_PATH="/app/data/mcp/cookies.json"
if [ ! -f "$COOKIE_PATH" ]; then
    echo "⚠️  注意: 未检测到登录Cookie"
    echo "   Cookie路径: $COOKIE_PATH"
    echo ""
    echo "   第一次启动？"
    echo "   请启动后访问Web界面 http://localhost:8000"
    echo "   进入 [设置] 页面获取登录二维码完成登录。"
    echo ""
else
    echo "✅ 检测到登录Cookie"
fi

echo "🚀 启动Web服务..."
echo "   访问地址: http://localhost:8000"
echo ""

# Start the application with uvicorn
exec python -m uvicorn rednote_research.web.app:app --host 0.0.0.0 --port 8000
