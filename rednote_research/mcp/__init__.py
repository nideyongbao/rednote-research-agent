"""MCP客户端模块 - 通过 HTTP API 访问 xiaohongshu-mcp 服务"""

from .http_client import XiaohongshuHTTPClient, get_mcp_client

# 别名，保持向后兼容
XiaohongshuMCPClient = XiaohongshuHTTPClient

__all__ = ["XiaohongshuHTTPClient", "XiaohongshuMCPClient", "get_mcp_client"]
