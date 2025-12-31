"""规划智能体 - 将用户意图拆解为搜索计划"""

import json
from typing import Callable, Optional
from openai import AsyncOpenAI
from .base import BaseAgent
from ..state import ResearchState, ResearchPlan
from ..prompts.planner import PLANNER_PROMPT


class PlannerAgent(BaseAgent):
    """
    规划智能体
    
    职责：将用户的模糊需求拆解为具体的搜索计划
    
    输入：用户原始查询
    输出：搜索关键词列表 + 研究维度
    """
    
    def __init__(self, llm_client: AsyncOpenAI, model: str):
        super().__init__(
            name="Planner",
            llm_client=llm_client,
            system_prompt=PLANNER_PROMPT,
            model=model
        )
    
    async def run(
        self, 
        state: ResearchState,
        on_log: Optional[Callable[[str], None]] = None
    ) -> ResearchState:
        """
        执行规划
        
        Args:
            state: 共享状态
            on_log: 日志回调
            
        Returns:
            更新后的状态（包含plan和search_keywords）
        """
        self._log(state, f"开始规划研究任务: {state.task}", on_log)
        
        # 构建消息
        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": f"研究主题：{state.task}"}
        ]
        
        # 调用LLM
        response = await self._invoke_llm(messages, temperature=0.7)
        
        # 解析响应
        plan = self._parse_plan(response)
        
        # 更新状态
        state.plan = plan
        state.search_keywords = plan.keywords.copy()
        
        # 输出 CoT 分析过程（如果有）
        if plan.reasoning:
            self._log(state, f"💭 分析过程: {plan.reasoning}", on_log)
        
        self._log(
            state, 
            f"生成了 {len(plan.keywords)} 个搜索关键词: {plan.keywords}", 
            on_log
        )
        
        return state
    
    def _parse_plan(self, response: str) -> ResearchPlan:
        """解析LLM响应为研究计划"""
        try:
            # 提取JSON部分
            json_start = response.find("{")
            json_end = response.rfind("}") + 1
            if json_start >= 0 and json_end > json_start:
                json_str = response[json_start:json_end]
                data = json.loads(json_str)
                return ResearchPlan(
                    reasoning=data.get("reasoning", ""),
                    understanding=data.get("understanding", ""),
                    dimensions=data.get("dimensions", []),
                    keywords=data.get("keywords", [])
                )
        except json.JSONDecodeError:
            pass
        
        # 解析失败时使用默认值
        return ResearchPlan(
            understanding="无法解析研究计划",
            dimensions=["综合分析"],
            keywords=[]  # 解析失败时返回空关键词列表
        )
