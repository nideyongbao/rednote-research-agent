"""搜索智能体 - 执行MCP工具调用，收集数据"""

import asyncio
from typing import Callable, Optional
from openai import AsyncOpenAI
from .base import BaseAgent
from ..state import ResearchState, NoteData
from ..mcp import XiaohongshuHTTPClient
from ..services.settings import get_settings_service
from ..prompts.searcher import SEARCHER_PROMPT


class SearcherAgent(BaseAgent):
    """
    搜索智能体
    
    职责：执行MCP工具调用，收集小红书笔记数据
    
    输入：搜索关键词列表
    输出：笔记数据列表（含详情）
    """
    
    # 搜索重试配置
    MAX_SEARCH_RETRIES = 3
    SEARCH_RETRY_DELAY = 2.0
    
    def __init__(
        self, 
        llm_client: AsyncOpenAI, 
        mcp_client: XiaohongshuHTTPClient,
        model: str
    ):
        super().__init__(
            name="Searcher",
            llm_client=llm_client,
            system_prompt=SEARCHER_PROMPT,
            model=model
        )
        self.mcp = mcp_client
    
    async def _search_with_retry(
        self, 
        keyword: str, 
        limit: int,
        state: ResearchState,
        on_log: Optional[Callable[[str], None]] = None
    ) -> list:
        """
        带重试机制的搜索
        
        Args:
            keyword: 搜索关键词
            limit: 结果数量限制
            state: 研究状态（用于日志）
            on_log: 日志回调
            
        Returns:
            搜索结果列表
        """
        last_exception = None
        
        for attempt in range(self.MAX_SEARCH_RETRIES):
            try:
                previews = await self.mcp.search_notes(keyword, limit=limit)
                
                if previews:
                    if attempt > 0:
                        self._log(state, f"    ✓ 重试成功 (第{attempt + 1}次)", on_log)
                    return previews
                
                # 空结果时重试
                if attempt < self.MAX_SEARCH_RETRIES - 1:
                    self._log(
                        state, 
                        f"    ⚠ 搜索返回空结果，{self.SEARCH_RETRY_DELAY}s后重试 ({attempt + 1}/{self.MAX_SEARCH_RETRIES})", 
                        on_log
                    )
                    await asyncio.sleep(self.SEARCH_RETRY_DELAY)
                    
            except Exception as e:
                last_exception = e
                if attempt < self.MAX_SEARCH_RETRIES - 1:
                    self._log(
                        state, 
                        f"    ⚠ 搜索异常: {str(e)[:50]}，{self.SEARCH_RETRY_DELAY}s后重试 ({attempt + 1}/{self.MAX_SEARCH_RETRIES})", 
                        on_log
                    )
                    await asyncio.sleep(self.SEARCH_RETRY_DELAY)
        
        # 所有重试都失败
        if last_exception:
            self._log(state, f"    ✗ 搜索最终失败: {str(last_exception)[:50]}", on_log)
        else:
            self._log(state, f"    ✗ 搜索多次返回空结果", on_log)
        
        return []
    
    # 并发控制
    MAX_CONCURRENT_SEARCHES = 3  # 限制同时搜索的关键词数量
    
    async def _search_single_keyword(
        self,
        keyword: str,
        index: int,
        total: int,
        limit: int,
        state: ResearchState,
        semaphore: asyncio.Semaphore,
        on_log: Optional[Callable[[str], None]] = None
    ) -> list[NoteData]:
        """
        单个关键词搜索（并行友好）
        
        Args:
            keyword: 搜索关键词
            index: 当前索引
            total: 总数
            limit: 结果数量限制
            state: 研究状态
            semaphore: 并发控制信号量
            on_log: 日志回调
            
        Returns:
            该关键词搜索到的笔记列表
        """
        async with semaphore:
            self._log(state, f"搜索关键词 [{index+1}/{total}]: {keyword}", on_log)
            
            try:
                # 1. 广度搜索（使用带重试的方法）
                previews = await self._search_with_retry(keyword, limit, state, on_log)
                self._log(state, f"  找到 {len(previews)} 篇笔记", on_log)
                
                if not previews:
                    return []
                
                # 2. 按点赞数排序
                sorted_previews = sorted(previews, key=lambda x: x.likes, reverse=True)
                
                # 3. 获取详情
                notes = []
                for j, preview in enumerate(sorted_previews):
                    self._log(
                        state, 
                        f"  获取详情 [{j+1}/{len(sorted_previews)}]: {preview.title[:30]}...", 
                        on_log
                    )
                    
                    try:
                        note_data = await self.mcp.get_note_with_detail(preview, delay=1.0)
                        notes.append(note_data)
                    except Exception as e:
                        self._log(state, f"  ⚠ 获取详情失败: {str(e)}", on_log)
                        notes.append(NoteData(preview=preview))
                
                return notes
                
            except Exception as e:
                self._log(state, f"  ⚠ 搜索失败: {str(e)}", on_log)
                return []
    
    async def run(
        self, 
        state: ResearchState,
        on_log: Optional[Callable[[str], None]] = None
    ) -> ResearchState:
        """
        执行搜索（并行优化版）
        
        Args:
            state: 共享状态
            on_log: 日志回调
            
        Returns:
            更新后的状态（包含documents）
        """
        # 处理补充关键词
        keywords_to_search = state.search_keywords.copy()
        if state.additional_keywords:
            keywords_to_search.extend(state.additional_keywords)
            state.additional_keywords = []
        
        self._log(state, f"开始并行搜索 {len(keywords_to_search)} 个关键词 (并发={self.MAX_CONCURRENT_SEARCHES})", on_log)
        
        # 从配置读取每个关键词搜索的笔记数量
        settings = get_settings_service().load()
        notes_per_keyword = settings.search.notes_per_keyword
        
        # 使用 Semaphore 控制并发数
        semaphore = asyncio.Semaphore(self.MAX_CONCURRENT_SEARCHES)
        
        # 并行执行所有搜索任务
        tasks = [
            self._search_single_keyword(
                keyword=kw,
                index=i,
                total=len(keywords_to_search),
                limit=notes_per_keyword,
                state=state,
                semaphore=semaphore,
                on_log=on_log
            )
            for i, kw in enumerate(keywords_to_search)
        ]
        
        # 等待所有任务完成
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 合并结果
        all_notes: list[NoteData] = []
        for result in results:
            if isinstance(result, Exception):
                self._log(state, f"⚠ 搜索任务异常: {str(result)[:50]}", on_log)
            elif isinstance(result, list):
                all_notes.extend(result)
        
        # 更新状态
        state.documents.extend(all_notes)
        
        self._log(
            state, 
            f"搜索完成，共收集 {len(all_notes)} 篇笔记，总计 {len(state.documents)} 篇", 
            on_log
        )
        
        return state
    
    async def filter_relevant(
        self, 
        state: ResearchState,
        notes: list[NoteData]
    ) -> list[NoteData]:
        """
        使用LLM筛选相关笔记（可选功能）
        
        Args:
            state: 共享状态
            notes: 待筛选笔记
            
        Returns:
            相关笔记列表
        """
        if not notes:
            return []
        
        # 构建筛选请求
        notes_summary = "\n".join([
            f"- {n.preview.title} (点赞: {n.preview.likes})"
            for n in notes  # 全量筛选、不截断
        ])
        
        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": f"""
研究主题：{state.task}

以下是搜索到的笔记，请选出与主题最相关的笔记（返回序号，用逗号分隔，可以选多篇）：

{notes_summary}
"""}
        ]
        
        response = await self._invoke_llm(messages, temperature=0.3)
        
        # 解析选中的序号
        try:
            indices = [int(x.strip()) - 1 for x in response.split(",")]
            return [notes[i] for i in indices if 0 <= i < len(notes)]
        except:
            return notes  # 解析失败时返回全部
