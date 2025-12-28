"""研究编排器 - 控制多智能体的执行流程"""

from typing import Callable, Optional, AsyncGenerator
from openai import AsyncOpenAI
from .planner import PlannerAgent
from .searcher import SearcherAgent
from .analyzer import AnalyzerAgent
from ..state import ResearchState
from ..mcp import XiaohongshuHTTPClient
from ..config import Config


class ResearchOrchestrator:
    """
    研究编排器
    
    控制多智能体的执行流程：
    Planner → Searcher → Analyzer → (反思循环) → 完成
    
    采用简单的状态机模式，降低复杂度
    """
    
    def __init__(self, config: Config, mcp_client: Optional[XiaohongshuHTTPClient] = None):
        """
        初始化编排器
        
        Args:
            config: 全局配置
            mcp_client: 可选的MCP客户端（如果不提供，将根据配置创建）
        """
        self.config = config
        self.llm = config.get_llm_client()
        self.mcp_client = mcp_client
        
        # 初始化智能体
        self.planner = PlannerAgent(self.llm, model=config.llm.model)
        self.analyzer = AnalyzerAgent(self.llm, model=config.llm.model)
        # Searcher需要MCP客户端，延迟初始化
        self._searcher: Optional[SearcherAgent] = None
    
    @property
    def searcher(self) -> SearcherAgent:
        """获取搜索智能体（延迟初始化）"""
        if self._searcher is None:
            if self.mcp_client is None:
                raise RuntimeError("MCP客户端未初始化")
            self._searcher = SearcherAgent(
                self.llm, 
                self.mcp_client,
                model=self.config.llm.model
            )
        return self._searcher
    
    async def run(
        self, 
        task: str,
        on_log: Optional[Callable[[str], None]] = None
    ) -> ResearchState:
        """
        执行完整研究流程
        
        Args:
            task: 用户任务描述
            on_log: 日志回调（用于SSE推送）
            
        Returns:
            最终研究状态
        """
        state = ResearchState(task=task)
        
        if on_log:
            on_log(f"🚀 开始研究: {task}")
        
        while not state.is_complete:
            # 阶段1: 规划
            if state.plan is None:
                state = await self.planner.run(state, on_log)
            
            # 阶段2: 搜索
            elif not state.documents or state.additional_keywords:
                state = await self.searcher.run(state, on_log)
            
            # 阶段3: 分析（含反思循环）
            else:
                state = await self.analyzer.run(state, on_log)
        
        if on_log:
            on_log(f"✅ 研究完成，收集了 {len(state.documents)} 篇笔记")
        
        return state
    
    async def run_stream(
        self, 
        task: str
    ) -> AsyncGenerator[str, None]:
        """
        流式执行研究流程，逐步产出日志
        
        Args:
            task: 用户任务描述
            
        Yields:
            日志消息
        """
        logs_queue: list[str] = []
        
        def collect_log(message: str):
            logs_queue.append(message)
        
        # 启动研究任务
        state = ResearchState(task=task)
        yield f"🚀 开始研究: {task}"
        
        while not state.is_complete:
            logs_queue.clear()
            
            # 阶段1: 规划
            if state.plan is None:
                state = await self.planner.run(state, collect_log)
            # 阶段2: 搜索
            elif not state.documents or state.additional_keywords:
                state = await self.searcher.run(state, collect_log)
            # 阶段3: 分析
            else:
                state = await self.analyzer.run(state, collect_log)
            
            # 产出本阶段的日志
            for log in logs_queue:
                yield log
        
        yield f"✅ 研究完成，收集了 {len(state.documents)} 篇笔记"
    
    async def __aenter__(self):
        """异步上下文管理器入口"""
        if self.mcp_client:
            await self.mcp_client.connect()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """异步上下文管理器退出"""
        if self.mcp_client:
            await self.mcp_client.disconnect()
