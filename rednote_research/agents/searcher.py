"""搜索智能体 - 执行MCP工具调用，收集数据"""

import asyncio
from typing import Callable, Optional
from openai import AsyncOpenAI
from .base import BaseAgent
from ..state import ResearchState, NoteData
from ..mcp.rednote import RedNoteMCPClient


SEARCHER_PROMPT = """你是一个数据筛选专家。给定一组小红书笔记的标题和摘要，判断它们与研究主题的相关性。

## 筛选标准
1. 直接相关：标题或内容直接涉及研究主题
2. 间接相关：提供有价值的背景信息或用户体验
3. 不相关：广告、无关话题、纯推广

## 需注意
- 优先选择高点赞数的笔记（通常质量更高）
- 优先选择有实际体验的笔记（而非纯转载）
- 避免明显的软广"""


class SearcherAgent(BaseAgent):
    """
    搜索智能体
    
    职责：执行MCP工具调用，收集小红书笔记数据
    
    输入：搜索关键词列表
    输出：笔记数据列表（含详情）
    """
    
    def __init__(
        self, 
        llm_client: AsyncOpenAI, 
        mcp_client: RedNoteMCPClient,
        model: str = "gpt-4o"
    ):
        super().__init__(
            name="Searcher",
            llm_client=llm_client,
            system_prompt=SEARCHER_PROMPT,
            model=model
        )
        self.mcp = mcp_client
    
    async def run(
        self, 
        state: ResearchState,
        on_log: Optional[Callable[[str], None]] = None
    ) -> ResearchState:
        """
        执行搜索
        
        Args:
            state: 共享状态
            on_log: 日志回调
            
        Returns:
            更新后的状态（包含documents）
        """
        all_notes: list[NoteData] = []
        
        # 处理补充关键词
        keywords_to_search = state.search_keywords.copy()
        if state.additional_keywords:
            keywords_to_search.extend(state.additional_keywords)
            state.additional_keywords = []
        
        self._log(state, f"开始搜索 {len(keywords_to_search)} 个关键词", on_log)
        
        for i, keyword in enumerate(keywords_to_search):
            self._log(state, f"搜索关键词 [{i+1}/{len(keywords_to_search)}]: {keyword}", on_log)
            
            try:
                # 1. 广度搜索
                previews = await self.mcp.search_notes(keyword, limit=10)
                self._log(state, f"  找到 {len(previews)} 篇笔记", on_log)
                
                if not previews:
                    continue
                
                # 2. 按点赞数排序，取Top N
                sorted_previews = sorted(previews, key=lambda x: x.likes, reverse=True)
                top_previews = sorted_previews[:3]  # 每个关键词取Top3
                
                # 3. 获取详情
                for j, preview in enumerate(top_previews):
                    self._log(
                        state, 
                        f"  获取详情 [{j+1}/{len(top_previews)}]: {preview.title[:30]}...", 
                        on_log
                    )
                    
                    try:
                        note_data = await self.mcp.get_note_with_detail(preview, delay=1.0)
                        all_notes.append(note_data)
                    except Exception as e:
                        self._log(state, f"  ⚠ 获取详情失败: {str(e)}", on_log)
                        # 使用预览信息创建NoteData
                        all_notes.append(NoteData(preview=preview))
                
            except Exception as e:
                self._log(state, f"  ⚠ 搜索失败: {str(e)}", on_log)
                continue
        
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
            for n in notes[:20]  # 最多筛选20篇
        ])
        
        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": f"""
研究主题：{state.task}

以下是搜索到的笔记，请选出与主题最相关的5篇（返回序号，用逗号分隔）：

{notes_summary}
"""}
        ]
        
        response = await self._invoke_llm(messages, temperature=0.3)
        
        # 解析选中的序号
        try:
            indices = [int(x.strip()) - 1 for x in response.split(",")]
            return [notes[i] for i in indices if 0 <= i < len(notes)]
        except:
            return notes[:5]  # 解析失败时返回前5篇
