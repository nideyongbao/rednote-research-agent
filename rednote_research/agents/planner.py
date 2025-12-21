"""规划智能体 - 将用户意图拆解为搜索计划"""

import json
from typing import Callable, Optional
from openai import AsyncOpenAI
from .base import BaseAgent
from ..state import ResearchState, ResearchPlan


PLANNER_PROMPT = """你是一个专业的研究规划专家。用户给出了一个研究主题，你需要：

1. **理解意图**：分析用户真正想要了解什么
2. **识别约束**：敏锐识别主题中的限定条件（如：地点、预算、具体人群、时间季节、特殊要求等）
3. **拆解维度**：将研究主题拆分为3-5个分析维度（维度中要体现约束条件）
4. **生成关键词**：为搜索生成5-8个精准关键词

## 关键词生成规则（重要！）

1. **核心原则：核心词 + 约束词**
   - 必须包含主题核心（如"奶茶店"）
   - **必须保留重要约束**（如"临港"、"低成本"），不要遗漏用户明确指定的限制条件！
   - 组合方式：核心词+约束、核心词+维度、核心词+场景

2. **简短精准**：
   - 每个关键词 2-6 个字为最佳
   - **必须用空格分隔**多个词，如 "上海 冬天 旅游"
   - ❌ 绝对禁止长句，如 "上海冬天旅游攻略推荐"

3. **搜索友好**：
   - ✅ 好: "穿搭 显瘦", "小个子 穿搭", "穿搭 避雷"
   - ❌ 差: "小个子穿搭分享实用技巧", "2025穿搭分享保姆级攻略"

4. **覆盖多角度**：包含正面（推荐、分享）和负面（避雷、避坑）

## 示例

**场景1：强约束任务（地点+预算）**
用户主题：上海临港奶茶店创业 低成本
*分析*：核心词="奶茶店"，约束="上海临港"(地点)、"低成本"(预算)
✅ 正确关键词：
- "临港 奶茶店" (地点+核心)
- "奶茶店 低成本" (核心+预算)
- "临港 奶茶店 选址" (地点+核心+维度)
- "奶茶店 装修 省钱" (核心+维度)
- "奶茶店 创业 避雷" (核心+多角度)

**场景2：一般攻略（多维度）**
用户主题：冬天上海旅游3天2晚攻略
✅ 正确关键词：["上海 冬天 旅游", "上海 3天 行程", "上海 必去 景点", "上海 美食", "上海 旅游 避坑"]
❌ 错误关键词：["冬季旅游保姆级攻略", "上海3天2晚详细旅游攻略推荐"]（太长、缺少空格分隔）

**场景3：泛话题（细分场景）**
用户主题：穿搭分享
✅ 正确关键词：["穿搭 分享", "穿搭 显瘦", "小个子 穿搭", "通勤 穿搭", "穿搭 避雷"]

## 输出格式
请以JSON格式输出，不要包含其他文字：
```json
{
  "understanding": "对用户意图的理解（包含核心诉求和约束）",
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
