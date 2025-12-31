"""FastAPI Web应用 - 提供SSE实时研究界面"""

import os
from pathlib import Path
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from ..config import Config
from ..mcp import XiaohongshuHTTPClient
from ..agents.orchestrator import ResearchOrchestrator
from .context import global_context
from .routers import research, history, settings, publish, tools

@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 启动时初始化
    config = Config.from_env()
    
    # MCP客户端（使用 HTTP API）
    mcp_url = os.getenv("XIAOHONGSHU_MCP_URL", "http://localhost:18060")
    mcp_client = XiaohongshuHTTPClient(base_url=mcp_url)
    await mcp_client.connect()
    orchestrator = ResearchOrchestrator(config, mcp_client)
    
    # 注入全局上下文
    global_context.config = config
    global_context.mcp_client = mcp_client
    global_context.orchestrator = orchestrator
    
    yield
    
    # 关闭时清理
    if mcp_client:
        await mcp_client.disconnect()

def create_app() -> FastAPI:
    """创建FastAPI应用"""
    app = FastAPI(
        title="RedNote Research Agent",
        description="基于MCP的小红书深度研究智能体",
        version="0.1.0",
        lifespan=lifespan
    )
    
    # 注册路由模块
    app.include_router(research.router)
    app.include_router(history.router)
    app.include_router(settings.router)
    app.include_router(publish.router)
    app.include_router(tools.router)
    
    # 挂载静态文件
    static_dir = Path(__file__).parent / "static"
    if static_dir.exists():
        assets_dir = static_dir / "assets"
        if assets_dir.exists():
            app.mount("/assets", StaticFiles(directory=str(assets_dir)), name="assets")
    
    # SPA 路由逻辑
    @app.get("/{full_path:path}", include_in_schema=False)
    async def serve_spa(full_path: str):
        if full_path.startswith("api/"):
            raise HTTPException(status_code=404, detail="API not found")
            
        requested_file = static_dir / full_path
        if requested_file.exists() and requested_file.is_file():
            return FileResponse(str(requested_file))
            
        return FileResponse(str(static_dir / "index.html"))

    return app

app = create_app()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
