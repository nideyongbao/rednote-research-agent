"""小红书MCP客户端 - 封装小红书相关的MCP工具调用"""

import asyncio
from typing import Optional
from .client import MCPClientBase
from ..state import NotePreview, NoteDetail, NoteData


class RedNoteMCPClient(MCPClientBase):
    """
    小红书MCP客户端
    
    封装了小红书相关的业务逻辑：
    - 搜索笔记
    - 获取笔记详情
    - 获取评论（可选）
    """
    
    def __init__(self, server_path: str, headless: bool = True):
        """
        初始化小红书MCP客户端
        
        Args:
            server_path: rednote-mcp服务器的路径
            headless: 是否无头模式运行浏览器
        """
        super().__init__(
            command=["node", server_path, "--stdio"],
            env={
                "HEADLESS": "true" if headless else "false",
            }
        )
    
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
            sort: 排序方式 (general/time_descending/popularity_descending)
            
        Returns:
            笔记预览列表
        """
        result = await self.call_tool("search_notes", {
            "keywords": keyword,
            "limit": limit
        })
        
        notes = []
        
        # 处理多种返回格式
        if isinstance(result, list):
            # 新格式：每篇笔记是一个字符串（MCP返回多个content）
            for item in result:
                if isinstance(item, str):
                    # 解析单条文本格式的笔记
                    parsed = self._parse_single_note(item)
                    if parsed:
                        notes.append(parsed)
                elif isinstance(item, dict):
                    # JSON格式笔记
                    notes.append(NotePreview(
                        id=item.get("id", ""),
                        title=item.get("title", ""),
                        author=item.get("author", ""),
                        content_preview=item.get("content", ""),
                        likes=item.get("likes", 0),
                        comments=item.get("comments", 0),
                        url=item.get("url", "")
                    ))
        elif isinstance(result, str):
            # 旧格式：所有笔记在一个字符串中
            notes = self._parse_search_result(result)
        
        return notes
    
    def _parse_single_note(self, text: str) -> NotePreview | None:
        """解析单条文本格式的笔记"""
        note_data = {}
        
        for line in text.split("\n"):
            line = line.strip()
            if line.startswith("标题:"):
                note_data["title"] = line[3:].strip()
            elif line.startswith("作者:"):
                note_data["author"] = line[3:].strip()
            elif line.startswith("内容:"):
                note_data["content_preview"] = line[3:].strip()
            elif line.startswith("点赞:"):
                try:
                    note_data["likes"] = int(line[3:].strip())
                except ValueError:
                    note_data["likes"] = 0
            elif line.startswith("评论:"):
                try:
                    note_data["comments"] = int(line[3:].strip())
                except ValueError:
                    note_data["comments"] = 0
            elif line.startswith("链接:"):
                note_data["url"] = line[3:].strip()
        
        if note_data.get("title") or note_data.get("url"):
            return NotePreview(**note_data)
        return None
    
    def _parse_search_result(self, text: str) -> list[NotePreview]:
        """解析文本格式的搜索结果"""
        notes = []
        current_note = {}
        
        for line in text.split("\n"):
            line = line.strip()
            if line.startswith("标题:"):
                if current_note:
                    notes.append(NotePreview(**current_note))
                current_note = {"title": line[3:].strip()}
            elif line.startswith("作者:"):
                current_note["author"] = line[3:].strip()
            elif line.startswith("内容:"):
                current_note["content_preview"] = line[3:].strip()
            elif line.startswith("点赞:"):
                try:
                    current_note["likes"] = int(line[3:].strip())
                except ValueError:
                    current_note["likes"] = 0
            elif line.startswith("评论:"):
                try:
                    current_note["comments"] = int(line[3:].strip())
                except ValueError:
                    current_note["comments"] = 0
            elif line.startswith("链接:"):
                current_note["url"] = line[3:].strip()
            elif line == "---":
                if current_note:
                    notes.append(NotePreview(**current_note))
                    current_note = {}
        
        if current_note:
            notes.append(NotePreview(**current_note))
        
        return notes
    
    async def get_note_detail(self, url: str) -> NoteDetail:
        """
        获取笔记详情
        
        Args:
            url: 笔记URL
            
        Returns:
            笔记详情
        """
        result = await self.call_tool("get_note_content", {"url": url})
        
        if isinstance(result, dict):
            return NoteDetail(
                title=result.get("title", ""),
                content=result.get("content", ""),
                author=result.get("author", ""),
                images=result.get("imgs", []),
                videos=result.get("videos", []),
                tags=result.get("tags", []),
                likes=result.get("likes", 0),
                comments=result.get("comments", 0),
                url=result.get("url", url)
            )
        
        return NoteDetail(url=url)
    
    async def get_note_with_detail(
        self, 
        preview: NotePreview,
        delay: float = 1.0
    ) -> NoteData:
        """
        获取笔记完整数据（预览+详情）
        
        Args:
            preview: 笔记预览
            delay: 请求延迟（秒），用于速率控制
            
        Returns:
            笔记完整数据
        """
        # 速率控制
        if delay > 0:
            await asyncio.sleep(delay)
        
        try:
            detail = await self.get_note_detail(preview.url)
        except Exception as e:
            # 获取详情失败时，使用预览信息填充
            detail = NoteDetail(
                title=preview.title,
                content=preview.content_preview,
                author=preview.author,
                url=preview.url
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
        
        Args:
            previews: 笔记预览列表
            max_concurrent: 最大并发数
            delay: 每次请求间隔
            
        Returns:
            笔记完整数据列表
        """
        results = []
        
        # 使用信号量控制并发
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def get_with_limit(preview: NotePreview) -> NoteData:
            async with semaphore:
                return await self.get_note_with_detail(preview, delay)
        
        # 并发获取
        tasks = [get_with_limit(p) for p in previews]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 过滤错误结果
        valid_results = []
        for r in results:
            if isinstance(r, NoteData):
                valid_results.append(r)
        
        return valid_results
