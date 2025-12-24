"""小红书MCP客户端 - 使用 xiaohongshu-mcp REST API"""

import asyncio
from typing import Optional
from .client import MCPClientBase
from ..state import NotePreview, NoteDetail, NoteData


class RedNoteMCPClient(MCPClientBase):
    """
    小红书 MCP 客户端
    
    使用 xiaohongshu-mcp 的 REST API：
    - GET /api/v1/login/status - 检查登录状态
    - POST /api/v1/feeds/search - 搜索笔记
    - POST /api/v1/feeds/detail - 获取笔记详情
    """
    
    def __init__(self, base_url: str = "http://localhost:18060"):
        """
        初始化小红书 MCP 客户端
        
        Args:
            base_url: xiaohongshu-mcp 服务地址
        """
        super().__init__(base_url=base_url)
    
    async def check_login_status(self) -> dict:
        """
        检查登录状态
        
        Returns:
            {"is_logged_in": bool, "username": str}
        """
        result = await self._get("/api/v1/login/status")
        
        # 解析响应
        if result.get("success"):
            data = result.get("data", {})
            return {
                "is_logged_in": data.get("is_logged_in", False),
                "username": data.get("username", "")
            }
        
        return {"is_logged_in": False, "username": ""}
    
    async def search_notes(
        self, 
        keyword: str, 
        limit: int = 10,
        sort: str = "general"
    ) -> list[NotePreview]:
        """
        搜索小红书笔记
        
        Args:
            keyword: 搜索关键词
            limit: 返回数量限制
            sort: 排序方式
            
        Returns:
            笔记预览列表
        """
        # 构建筛选参数
        filters = {}
        if sort == "time_descending":
            filters["sort_by"] = "最新"
        elif sort == "popularity_descending":
            filters["sort_by"] = "最多点赞"
        
        request_data = {"keyword": keyword}
        if filters:
            request_data["filters"] = filters
        
        result = await self._post("/api/v1/feeds/search", request_data)
        
        notes = []
        
        if result.get("success"):
            data = result.get("data", {})
            feeds = data.get("feeds", [])
            
            for feed in feeds:
                notes.append(self._parse_feed_to_preview(feed))
        
        return notes[:limit] if limit else notes
    
    def _parse_feed_to_preview(self, feed: dict) -> NotePreview:
        """将 xiaohongshu-mcp 的 Feed 解析为 NotePreview"""
        # 搜索结果的实际数据在 noteCard 子对象中
        note_card = feed.get("noteCard", {})
        user = note_card.get("user", {})
        interact_info = note_card.get("interactInfo", {})
        cover = note_card.get("cover", {})
        
        # 提取封面图片 URL
        cover_url = cover.get("urlDefault", cover.get("url", ""))
        
        return NotePreview(
            id=feed.get("id", ""),
            title=note_card.get("displayTitle", ""),
            author=user.get("nickname", user.get("name", "")),
            content_preview=note_card.get("desc", "")[:200] if note_card.get("desc") else "",
            likes=self._parse_count(interact_info.get("likedCount", 0)),
            comments=self._parse_count(interact_info.get("commentCount", 0)),
            url=f"https://www.xiaohongshu.com/explore/{feed.get('id', '')}",
            xsec_token=feed.get("xsecToken", ""),
            cover_image=cover_url
        )
    
    def _parse_count(self, value) -> int:
        """解析数量值（可能是字符串如 "1.2万"）"""
        if isinstance(value, int):
            return value
        if isinstance(value, str):
            value = value.strip()
            if not value:
                return 0
            try:
                if "万" in value:
                    return int(float(value.replace("万", "")) * 10000)
                if "亿" in value:
                    return int(float(value.replace("亿", "")) * 100000000)
                return int(value)
            except:
                return 0
        return 0
    
    async def get_note_detail(self, feed_id: str, xsec_token: str) -> NoteDetail:
        """
        获取笔记详情
        
        Args:
            feed_id: 笔记ID
            xsec_token: 访问令牌
            
        Returns:
            笔记详情
        """
        result = await self._post("/api/v1/feeds/detail", {
            "feed_id": feed_id,
            "xsec_token": xsec_token
        })
        
        if result.get("success"):
            data = result.get("data", {})
            return NoteDetail(
                title=data.get("title", ""),
                content=data.get("content", data.get("desc", "")),
                author=data.get("author", data.get("nickname", "")),
                images=data.get("images", data.get("imageList", [])),
                videos=data.get("videos", data.get("videoList", [])),
                tags=data.get("tags", data.get("hashTags", [])),
                likes=self._parse_count(data.get("likedCount", data.get("likes", 0))),
                comments=self._parse_count(data.get("commentCount", data.get("comments", 0))),
                url=data.get("noteUrl", data.get("url", ""))
            )
        
        return NoteDetail()
    
    async def get_note_with_detail(
        self, 
        preview: NotePreview,
        delay: float = 1.0
    ) -> NoteData:
        """
        获取笔记完整数据（预览+详情）
        
        Args:
            preview: 笔记预览
            delay: 请求延迟（秒）
            
        Returns:
            笔记完整数据
        """
        if delay > 0:
            await asyncio.sleep(delay)
        
        detail = None
        
        try:
            feed_id = preview.id
            xsec_token = preview.xsec_token
            
            if feed_id and xsec_token:
                detail = await self.get_note_detail(feed_id, xsec_token)
                # 检查是否获取到有效内容
                if not detail.content and not detail.images:
                    detail = None
        except Exception:
            detail = None
        
        # 降级处理：使用预览数据
        if detail is None:
            images = [preview.cover_image] if preview.cover_image else []
            detail = NoteDetail(
                title=preview.title,
                content=preview.content_preview,
                author=preview.author,
                images=images,
                url=preview.url,
                likes=preview.likes,
                comments=preview.comments
            )
        
        return NoteData(preview=preview, detail=detail)
    
    async def batch_get_details(
        self, 
        previews: list[NotePreview],
        max_concurrent: int = 3,
        delay: float = 1.0
    ) -> list[NoteData]:
        """
        批量获取笔记详情
        """
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def get_with_limit(preview: NotePreview) -> NoteData:
            async with semaphore:
                return await self.get_note_with_detail(preview, delay)
        
        tasks = [get_with_limit(p) for p in previews]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        return [r for r in results if isinstance(r, NoteData)]
