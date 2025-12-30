"""小红书MCP HTTP客户端 - 通过 HTTP API 访问 xiaohongshu-mcp 服务

使用方式：
1. 在 Docker Compose 中启动 xiaohongshu-mcp 服务
2. 本客户端通过 HTTP API 与服务通信
"""

import os
import httpx
from typing import Optional, Any
from ..state import NotePreview, NoteDetail, NoteData


# 默认 MCP 服务地址（Docker 内部网络 或 本地）
DEFAULT_MCP_URL = os.getenv("XIAOHONGSHU_MCP_URL", "http://localhost:18060")


class XiaohongshuHTTPClient:
    """
    小红书MCP HTTP客户端
    
    通过 HTTP REST API 与 xiaohongshu-mcp 服务通信
    """
    
    def __init__(self, base_url: str = None, timeout: float = 120.0):
        """
        初始化客户端
        
        Args:
            base_url: xiaohongshu-mcp 服务地址
            timeout: 请求超时时间（秒）
        """
        self.base_url = (base_url or DEFAULT_MCP_URL).rstrip("/")
        self.timeout = timeout
        self._client: Optional[httpx.AsyncClient] = None
        self._last_search_tokens: dict[str, str] = {}  # xsec_token 缓存
    
    async def connect(self) -> None:
        """建立连接"""
        if self._client is None:
            self._client = httpx.AsyncClient(
                base_url=self.base_url,
                timeout=self.timeout
            )
    
    async def disconnect(self) -> None:
        """关闭连接"""
        if self._client:
            await self._client.aclose()
            self._client = None
    
    async def __aenter__(self):
        await self.connect()
        return self
    
    async def __aexit__(self, *args):
        await self.disconnect()
    
    # ==== 登录相关 ====
    
    async def check_login_status(self) -> dict:
        """
        检查登录状态
        
        Returns:
            {"is_logged_in": bool, "username": str}
        """
        await self._ensure_connected()
        response = await self._client.get("/api/v1/login/status")
        data = response.json()
        
        if data.get("success"):
            login_data = data.get("data", {})
            return {
                "is_logged_in": login_data.get("is_logged_in", False),
                "username": login_data.get("username", "")
            }
        return {"is_logged_in": False, "username": ""}
    
    async def get_login_qrcode(self) -> dict:
        """
        获取登录二维码
        
        Returns:
            {"img": str (base64), "timeout": str, "is_logged_in": bool}
        """
        await self._ensure_connected()
        response = await self._client.get("/api/v1/login/qrcode")
        data = response.json()
        
        if data.get("success"):
            return data.get("data", {})
        raise Exception(data.get("message", "获取二维码失败"))
    
    # ==== 搜索相关 ====
    
    async def search_feeds(
        self, 
        keyword: str,
        sort_by: str = "综合",
        note_type: str = "不限",
        max_retries: int = 3
    ) -> tuple[list[NotePreview], dict[str, str]]:
        """
        搜索笔记（带重试）
        
        Returns:
            (笔记预览列表, xsec_token字典)
        """
        import asyncio
        
        await self._ensure_connected()
        
        last_error = None
        for attempt in range(max_retries):
            try:
                response = await self._client.post("/api/v1/feeds/search", json={
                    "keyword": keyword,
                    "filters": {
                        "sort_by": sort_by,
                        "note_type": note_type
                    }
                })
                data = response.json()
                
                # 检查服务端错误
                if response.status_code >= 500 or not data.get("success"):
                    error_msg = data.get("message", data.get("error", f"HTTP {response.status_code}"))
                    if attempt < max_retries - 1:
                        await asyncio.sleep(2 ** attempt)  # 指数退避
                        continue
                    raise Exception(f"搜索失败: {error_msg}")
                
                break  # 成功，跳出重试循环
                
            except Exception as e:
                last_error = e
                if attempt < max_retries - 1:
                    await asyncio.sleep(2 ** attempt)
                    continue
                raise
        
        data = response.json()
        
        notes = []
        tokens = {}
        
        if data.get("success"):
            feeds = data.get("data", {}).get("feeds", [])
            for feed in feeds:
                feed_id = feed.get("id", "")
                xsec_token = feed.get("xsecToken", "")
                
                if feed_id and xsec_token:
                    tokens[feed_id] = xsec_token
                    self._last_search_tokens[feed_id] = xsec_token  # 缓存 token
                
                note_card = feed.get("noteCard", {})
                user_info = note_card.get("user", {})
                
                notes.append(NotePreview(
                    id=feed_id,
                    title=note_card.get("displayTitle", ""),
                    author=user_info.get("nickname", ""),
                    content_preview="",
                    likes=self._parse_count(note_card.get("interactInfo", {}).get("likedCount", 0)),
                    comments=0,
                    url=f"https://www.xiaohongshu.com/explore/{feed_id}"
                ))
        
        return notes, tokens
    
    async def get_feed_detail(
        self, 
        feed_id: str, 
        xsec_token: str
    ) -> NoteDetail:
        """
        获取笔记详情
        """
        await self._ensure_connected()
        response = await self._client.post("/api/v1/feeds/detail", json={
            "feed_id": feed_id,
            "xsec_token": xsec_token
        })
        data = response.json()
        
        # API 可能返回多种格式:
        # 1. {"success": true, "data": {...}}
        # 2. {"feed_id": "...", "data": {"note": {...}}}
        # 3. {"data": {"note": {...}}}
        
        note = None
        
        # 尝试从 data.data.note 获取
        raw_data = data.get("data", {})
        if isinstance(raw_data, dict):
            # 1. 直接在 data.data 下 (e.g. data.data.note)
            if "note" in raw_data:
                note = raw_data.get("note", {})
            # 2. 在 data.data.data 下 (e.g. data.data.data.note) <--- 修复这里
            elif "data" in raw_data and isinstance(raw_data["data"], dict) and "note" in raw_data["data"]:
                note = raw_data["data"]["note"]
            # 3. data.data 本身就是 note 内容
            elif "title" in raw_data or "desc" in raw_data:
                note = raw_data
        
        # 如果还没找到，尝试直接从顶层获取 (data.note)
        if not note and ("title" in data or "desc" in data):
            note = data
        
        if not note:
            return NoteDetail(url=f"https://www.xiaohongshu.com/explore/{feed_id}")
        
        # 解析图片列表
        images = []
        for img in note.get("imageList", []):
            url = img.get("urlDefault") or img.get("url") or ""
            if url:
                images.append(url)
        
        # 解析内容
        content = note.get("desc", "") or note.get("content", "") or ""
        title = note.get("title", "") or note.get("displayTitle", "") or ""
        
        return NoteDetail(
            title=title,
            content=content,
            author=note.get("user", {}).get("nickname", ""),
            images=images,
            videos=[],
            tags=[t.get("name", "") if isinstance(t, dict) else t for t in note.get("tagList", [])],
            likes=self._parse_count(note.get("interactInfo", {}).get("likedCount", 0)),
            comments=self._parse_count(note.get("interactInfo", {}).get("commentCount", 0)),
            url=f"https://www.xiaohongshu.com/explore/{feed_id}"
        )
    
    # ==== 兼容旧接口 ====
    
    async def search_notes(self, keyword: str, limit: int = 10, sort: str = "general") -> list[NotePreview]:
        """搜索笔记（兼容旧接口）- 自动缓存 xsec_token"""
        notes, _ = await self.search_feeds(keyword)
        return notes[:limit]
    
    async def get_note_with_detail(self, preview: NotePreview, delay: float = 1.0, xsec_token: str = None) -> NoteData:
        """获取完整笔记数据 - 自动从缓存获取 xsec_token"""
        import asyncio
        if delay > 0:
            await asyncio.sleep(delay)
        
        # 如果没有传入 token，尝试从缓存获取
        token = xsec_token or self._last_search_tokens.get(preview.id)
        
        if not token:
            return NoteData(preview=preview, detail=NoteDetail(
                title=preview.title, author=preview.author, url=preview.url
            ))
        
        try:
            detail = await self.get_feed_detail(preview.id, token)
            return NoteData(preview=preview, detail=detail)
        except Exception:
            return NoteData(preview=preview)
    
    # ==== 工具方法 ====
    
    async def _ensure_connected(self):
        if self._client is None:
            await self.connect()
    
    def _parse_count(self, value) -> int:
        """解析计数值"""
        if isinstance(value, int):
            return value
        if isinstance(value, str):
            value = value.strip()
            if not value:
                return 0
            try:
                if '万' in value:
                    return int(float(value.replace('万', '')) * 10000)
                return int(value)
            except ValueError:
                return 0
        return 0
    
    # ==== 发布相关 ====
    
    async def publish_content(
        self,
        title: str,
        content: str,
        images: list[str],
        tags: list[str] = None
    ) -> dict:
        """
        发布笔记到小红书
        
        Args:
            title: 标题（≤20字）
            content: 正文内容（≤200字，图文笔记）
            images: 图片路径列表（1-9张，支持本地路径或在线URL）
            tags: 标签列表（可选，3-5个）
        
        Returns:
            {
                "success": bool,
                "note_id": str,
                "url": str,
                "error": str (if failed)
            }
        """
        await self._ensure_connected()
        
        # 构建发布请求
        publish_data = {
            "title": title[:20],  # 确保标题不超过20字
            "content": content[:1000],  # API 限制
            "images": images,
        }
        
        if tags:
            publish_data["tags"] = tags[:8]  # 最多8个标签
        
        try:
            response = await self._client.post(
                "/api/v1/publish",
                json=publish_data,
                timeout=120.0  # 发布需要更长时间
            )
            data = response.json()
            
            if data.get("success"):
                result_data = data.get("data", {})
                note_id = result_data.get("note_id", "")
                # 有些版本 API 可能直接返回 note_id 字符串
                if not note_id and isinstance(result_data, str):
                    note_id = result_data

                return {
                    "success": True,
                    "note_id": note_id,
                    "url": f"https://www.xiaohongshu.com/explore/{note_id}" if note_id else "",
                    "error": None
                }
            else:
                return {
                    "success": False,
                    "note_id": None,
                    "url": None,
                    "error": data.get("message") or data.get("error") or "发布失败"
                }
                
        except Exception as e:
            return {
                "success": False,
                "note_id": None,
                "url": None,
                "error": str(e)
            }


# 全局客户端实例
_http_client: Optional[XiaohongshuHTTPClient] = None


def get_mcp_client() -> XiaohongshuHTTPClient:
    """获取全局 MCP 客户端实例"""
    global _http_client
    if _http_client is None:
        _http_client = XiaohongshuHTTPClient()
    return _http_client
