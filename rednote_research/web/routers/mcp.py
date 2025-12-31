from fastapi import APIRouter, HTTPException
from ..context import global_context
from ...mcp.http_client import get_mcp_client

router = APIRouter(prefix="/api/mcp", tags=["mcp"])

async def _get_client():
    return global_context.mcp_client or get_mcp_client()

@router.get("/login/status")
async def check_login_status():
    """获取小红书登录状态"""
    try:
        client = await _get_client()
        return await client.check_login_status()
    except Exception as e:
        # 如果连接不上 MCP 服务，返回未登录状态而非 500
        return {"is_logged_in": False, "username": "", "error": str(e)}

@router.get("/login/qrcode")
async def get_login_qrcode():
    """获取登录二维码"""
    try:
        client = await _get_client()
        return await client.get_login_qrcode()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
