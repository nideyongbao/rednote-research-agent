"""MCP客户端基类 - 使用 xiaohongshu-mcp REST API"""

from typing import Any, Optional
from contextlib import asynccontextmanager

import httpx


class MCPClientBase:
    """
    MCP客户端基类
    
    使用 xiaohongshu-mcp 的 REST API 进行通信：
    - GET /api/v1/login/status - 检查登录状态
    - POST /api/v1/feeds/search - 搜索笔记
    - POST /api/v1/feeds/detail - 获取笔记详情
    - POST /api/v1/publish - 发布内容
    """
    
    def __init__(self, base_url: str = "http://localhost:18060"):
        """
        初始化 MCP 客户端
        
        Args:
            base_url: xiaohongshu-mcp 服务地址
        """
        self.base_url = base_url.rstrip("/")
        self._client: Optional[httpx.AsyncClient] = None
        self._connected = False
    
    async def connect(self) -> None:
        """建立 HTTP 客户端连接"""
        if self._connected:
            return
        
        self._client = httpx.AsyncClient(
            base_url=self.base_url,
            timeout=120.0
        )
        self._connected = True
    
    async def disconnect(self) -> None:
        """关闭连接"""
        if self._client:
            await self._client.aclose()
            self._client = None
        self._connected = False
    
    async def _get(self, path: str) -> dict:
        """发送 GET 请求"""
        if not self._client:
            raise RuntimeError("客户端未连接")
        
        response = await self._client.get(path)
        response.raise_for_status()
        return response.json()
    
    async def _post(self, path: str, data: dict = None) -> dict:
        """发送 POST 请求"""
        if not self._client:
            raise RuntimeError("客户端未连接")
        
        response = await self._client.post(path, json=data or {})
        response.raise_for_status()
        return response.json()
    
    @asynccontextmanager
    async def session(self):
        """上下文管理器，自动管理连接生命周期"""
        await self.connect()
        try:
            yield self
        finally:
            await self.disconnect()
    
    async def __aenter__(self):
        await self.connect()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.disconnect()
