"""设置相关 API 路由"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from ...services.settings import get_settings_service, Settings

router = APIRouter(prefix="/api/settings", tags=["settings"])


class LLMTestRequest(BaseModel):
    """LLM 测试请求"""
    apiKey: str
    baseUrl: str
    model: str


class VLMTestRequest(BaseModel):
    """VLM 测试请求"""
    apiKey: str
    baseUrl: str
    model: str


class ImageGenTestRequest(BaseModel):
    """图片生成模型测试请求"""
    apiKey: str
    baseUrl: str
    model: str


@router.get("")
async def get_settings():
    """获取设置（脱敏）"""
    service = get_settings_service()
    return service.get_masked()


@router.post("")
async def save_settings(settings: Settings):
    """保存设置"""
    service = get_settings_service()
    service.save(settings)
    return {"status": "ok", "message": "设置已保存"}


@router.post("/test")
async def test_llm_connection(request: LLMTestRequest):
    """测试 LLM 连接"""
    from openai import AsyncOpenAI
    
    try:
        client = AsyncOpenAI(
            api_key=request.apiKey,
            base_url=request.baseUrl
        )
        
        # 发送简单测试请求
        response = await client.chat.completions.create(
            model=request.model,
            messages=[{"role": "user", "content": "Hi"}],
            max_tokens=5
        )
        
        return {"status": "ok", "message": "连接成功"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"连接失败: {str(e)}")


@router.post("/test-vlm")
async def test_vlm_connection(request: VLMTestRequest):
    """测试 VLM 连接（发送图片验证请求）"""
    from openai import AsyncOpenAI
    
    try:
        client = AsyncOpenAI(
            api_key=request.apiKey,
            base_url=request.baseUrl,
            timeout=30.0
        )
        
        # 使用一个简单的 base64 编码的测试图片（100x100 红色方块）
        test_image_base64 = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAGQAAABkCAIAAAD/gAIDAAAAaklEQVR42u3QMQEAAAwCIPuX1hjL8AETDlNVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVXVH2YBy8IABVQAAABJRU5ErkJggg=="
        
        response = await client.chat.completions.create(
            model=request.model,
            messages=[{
                "role": "user",
                "content": [
                    {"type": "text", "text": "What color is this image? Answer in one word."},
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": test_image_base64
                        }
                    }
                ]
            }],
            max_tokens=10
        )
        
        return {"status": "ok", "message": f"VLM 连接成功！模型: {request.model}"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"VLM 连接失败: {str(e)}")


@router.post("/test-imagegen")
async def test_imagegen_connection(request: ImageGenTestRequest):
    """测试图片生成模型连接"""
    import httpx
    
    try:
        # 根据模型类型选择不同的测试方式
        if "wanx" in request.model.lower():
            # 通义万相使用阿里云 DashScope API
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{request.baseUrl}/services/aigc/text2image/image-synthesis",
                    headers={
                        "Authorization": f"Bearer {request.apiKey}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": request.model,
                        "input": {"prompt": "test"},
                        "parameters": {"n": 1, "size": "256*256"}
                    }
                )
                if response.status_code in [200, 202]:
                    return {"status": "ok", "message": f"图片生成模型连接成功！模型: {request.model}"}
                else:
                    raise Exception(f"HTTP {response.status_code}: {response.text[:200]}")
        else:
            # 其他模型使用 OpenAI 兼容接口
            from openai import AsyncOpenAI
            client = AsyncOpenAI(
                api_key=request.apiKey,
                base_url=request.baseUrl
            )
            await client.models.list()
            return {"status": "ok", "message": f"图片生成模型 API 连接成功！模型: {request.model}"}
            
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"图片生成模型连接失败: {str(e)}")


@router.post("/test-mcp")
async def test_mcp_connection():
    """测试 MCP 连接（完整测试：登录状态 + 搜索 + 获取详情）"""
    from ...mcp.http_client import get_mcp_client
    
    try:
        client = get_mcp_client()
        
        # 1. 检查登录状态
        status = await client.check_login_status()
        
        if not status.get("is_logged_in"):
            return {
                "status": "warning",
                "message": "MCP 服务正常，但未登录小红书。请扫码登录。"
            }
        
        username = status.get('username', '未知')
        
        # 2. 测试搜索
        try:
            await client._ensure_connected()
            response = await client._client.post("/api/v1/feeds/search", json={
                "keyword": "奶茶"
            })
            raw_data = response.json()
            
            if raw_data.get("success"):
                feeds = raw_data.get("data", {}).get("feeds", [])
                search_count = len(feeds)
                
                # 3. 测试获取详情
                detail_test = ""
                if feeds:
                    first_feed = feeds[0]
                    feed_id = first_feed.get("id", "")
                    xsec_token = first_feed.get("xsecToken", "")
                    
                    if feed_id and xsec_token:
                        try:
                            detail_response = await client._client.post("/api/v1/feeds/detail", json={
                                "feed_id": feed_id,
                                "xsec_token": xsec_token
                            })
                            detail_data = detail_response.json()
                            if detail_data.get("success"):
                                note_title = detail_data.get("data", {}).get("title", "")[:15]
                                detail_test = f"，详情获取✓({note_title})"
                            else:
                                err_msg = detail_data.get('message', '') or detail_data.get('error', '') or '未知错误'
                                detail_test = f"，详情获取✗({err_msg[:30]})"
                        except Exception as e:
                            detail_test = f"，详情获取异常({str(e)[:30]})"
                    else:
                        detail_test = f"，缺少token(id={feed_id[:8] if feed_id else 'N/A'})"
                
                return {
                    "status": "ok",
                    "message": f"MCP 连接成功！用户: {username}，搜索到 {search_count} 条结果{detail_test}"
                }
            else:
                return {
                    "status": "warning",
                    "message": f"MCP 连接成功，用户: {username}，但搜索失败: {raw_data.get('message', '未知错误')}"
                }
                
        except Exception as e:
            return {
                "status": "warning",
                "message": f"MCP 连接成功，用户: {username}，但搜索测试失败: {str(e)[:100]}"
            }
            
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"MCP 连接失败: {str(e)[:200]}")


# MCP 登录相关 API
@router.get("/mcp/login/status")
async def mcp_login_status():
    """获取小红书登录状态"""
    from ...mcp.http_client import get_mcp_client
    
    try:
        client = get_mcp_client()
        status = await client.check_login_status()
        return {
            "success": True,
            "data": status
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取登录状态失败: {str(e)}")


@router.get("/mcp/login/qrcode")
async def mcp_login_qrcode():
    """获取小红书登录二维码"""
    from ...mcp.http_client import get_mcp_client
    
    try:
        client = get_mcp_client()
        qr_data = await client.get_login_qrcode()
        return {
            "success": True,
            "data": qr_data
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取二维码失败: {str(e)}")
