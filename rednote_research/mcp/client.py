"""MCP客户端基类 - 处理与MCP服务器的通信"""

import asyncio
import json
from abc import ABC, abstractmethod
from typing import Any, Optional
from contextlib import asynccontextmanager


class MCPClientBase(ABC):
    """
    MCP客户端基类
    
    提供与MCP服务器通信的基础能力：
    - 启动/停止服务器进程
    - 发送JSON-RPC请求
    - 接收和解析响应
    """
    
    def __init__(self, command: list[str], env: Optional[dict] = None):
        """
        初始化MCP客户端
        
        Args:
            command: 启动MCP服务器的命令，如 ["node", "path/to/server.js"]
            env: 环境变量
        """
        self.command = command
        self.env = env or {}
        self.process: Optional[asyncio.subprocess.Process] = None
        self._request_id = 0
        self._connected = False
    
    async def connect(self) -> None:
        """建立与MCP服务器的连接"""
        if self._connected:
            return
        
        # 启动MCP服务器进程
        self.process = await asyncio.create_subprocess_exec(
            *self.command,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env={**dict(__import__("os").environ), **self.env}
        )
        
        # 发送初始化请求
        await self._initialize()
        self._connected = True
    
    async def disconnect(self) -> None:
        """关闭连接"""
        if self.process:
            self.process.terminate()
            await self.process.wait()
            self.process = None
        self._connected = False
    
    async def _initialize(self) -> dict:
        """发送MCP初始化请求"""
        return await self._send_request("initialize", {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {
                "name": "rednote-research",
                "version": "0.1.0"
            }
        })
    
    async def list_tools(self) -> list[dict]:
        """列出可用工具"""
        response = await self._send_request("tools/list", {})
        return response.get("tools", [])
    
    async def call_tool(self, name: str, arguments: dict) -> Any:
        """
        调用MCP工具
        
        Args:
            name: 工具名称
            arguments: 工具参数
            
        Returns:
            工具执行结果
        """
        response = await self._send_request("tools/call", {
            "name": name,
            "arguments": arguments
        })
        
        # 解析响应内容
        content = response.get("content", [])
        if content and len(content) > 0:
            first_content = content[0]
            if first_content.get("type") == "text":
                text = first_content.get("text", "")
                # 尝试解析为JSON
                try:
                    return json.loads(text)
                except json.JSONDecodeError:
                    return text
        
        return response
    
    async def _send_request(self, method: str, params: dict) -> dict:
        """发送JSON-RPC请求"""
        if not self.process or not self.process.stdin or not self.process.stdout:
            raise RuntimeError("MCP服务器未连接")
        
        self._request_id += 1
        request = {
            "jsonrpc": "2.0",
            "id": self._request_id,
            "method": method,
            "params": params
        }
        
        # 发送请求
        request_line = json.dumps(request) + "\n"
        self.process.stdin.write(request_line.encode())
        await self.process.stdin.drain()
        
        # 读取响应
        response_line = await self.process.stdout.readline()
        if not response_line:
            raise RuntimeError("MCP服务器无响应")
        
        response = json.loads(response_line.decode())
        
        # 检查错误
        if "error" in response:
            error = response["error"]
            raise RuntimeError(f"MCP错误: {error.get('message', str(error))}")
        
        return response.get("result", {})
    
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
