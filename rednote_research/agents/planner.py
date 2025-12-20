"""规划智能体 - 将用户意图拆解为搜索计划"""

import json
from typing import Callable, Optional
from openai import AsyncOpenAI
from .base import BaseAgent
from ..state import ResearchState, ResearchPlan


PLANNER_PROMPT = """你是一个专业的研究规划专家。用户给出了一个研究主题，你需要：

1. **理解意图**：分析用户真正想要了解什么
2. **提取核心词**：识别主题中的核心关键词（如地点、产品名、品牌等）
3. **拆解维度**：将研究主题拆分为3-5个分析维度
4. **生成关键词**：为每个维度生成1-2个适合在小红书搜索的关键词

## 关键词生成规则（必须严格遵守）
- **每个关键词必须包含主题的核心词**（如地点"上海"、产品名"露营帐篷"等）
- 使用小红书用户的习惯用语（如"攻略"、"避雷"、"保姆级"、"测评"）
- 关键词长度5-15个字
- 覆盖正面（推荐）和负面（避坑）两个角度
- 考虑时效性（如"2025"、"最新"）

## 示例
用户主题：冬天上海旅游3天2晚攻略
正确的关键词：["上海冬天旅游攻略", "上海3天2晚行程", "上海旅游冬季避坑指南", "上海必去景点推荐", "上海美食推荐"]
错误的关键词：["冬季旅游攻略", "避坑指南", "美食推荐"]（缺少"上海", "旅游", "冬天", "3天2晚"等核心词）

## 输出格式
请以JSON格式输出，不要包含其他文字：
```json
{
  "understanding": "对用户意图的理解（一句话）",
  "dimensions": ["维度1", "维度2", "维度3"],
  "keywords": ["关键词1", "关键词2", "关键词3", "关键词4", "关键词5"]
}
```"""


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
