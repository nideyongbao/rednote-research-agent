"""分析智能体 - 数据分析、反思和报告撰写"""

import json
from typing import Callable, Optional
from openai import AsyncOpenAI
from .base import BaseAgent
from ..state import ResearchState
from ..prompts.analyzer import ANALYZER_PROMPT


class AnalyzerAgent(BaseAgent):
    """
    分析智能体
    
    职责：执行数据分析、反思和报告撰写
    融合了Analyst、Critic和Writer的功能
    
    输入：原始笔记数据
    输出：结构化洞察 + 最终报告
    """
    
    def __init__(self, llm_client: AsyncOpenAI, model: str):
        super().__init__(
            name="Analyzer",
            llm_client=llm_client,
            system_prompt=ANALYZER_PROMPT,
            model=model
        )
    
    async def run(
        self, 
        state: ResearchState,
        on_log: Optional[Callable[[str], None]] = None
    ) -> ResearchState:
        """
        执行分析
        
        Args:
            state: 共享状态
            on_log: 日志回调
            
        Returns:
            更新后的状态（包含insights，可能包含additional_keywords）
        """
        self._log(state, f"开始分析 {len(state.documents)} 篇笔记", on_log)
        
        # 阶段1: 数据分析
        insights = await self._analyze_documents(state, on_log)
        state.insights = insights
        
        # 阶段2: 自我反思
        if insights.get("needs_more_data", False) and state.iteration_count < 3:
            suggested = insights.get("suggested_keywords", [])
            if suggested:
                state.additional_keywords = suggested
                state.iteration_count += 1
                self._log(
                    state, 
                    f"数据不足，建议补充搜索: {suggested}", 
                    on_log
                )
                return state
        
        # 阶段3: 标记完成
        state.is_complete = True
        self._log(state, "分析完成", on_log)
        
        return state
    
    async def _analyze_documents(
        self, 
        state: ResearchState,
        on_log: Optional[Callable[[str], None]] = None
    ) -> dict:
        """分析文档并提取洞察"""
        
        # 准备数据摘要
        data_summary = self._prepare_data_summary(state)
        
        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": f"""
## 研究主题
{state.task}

## 研究计划
{state.plan.model_dump_json() if state.plan else "无"}

## 收集到的数据
{data_summary}

请分析以上数据并给出洞察。
"""}
        ]
        
        self._log(state, "正在分析数据...", on_log)
        response = await self._invoke_llm(messages, temperature=0.5, max_tokens=4000)
        
        # 解析响应
        try:
            json_start = response.find("{")
            json_end = response.rfind("}") + 1
            if json_start >= 0 and json_end > json_start:
                return json.loads(response[json_start:json_end])
        except json.JSONDecodeError:
            pass
        
        return {
            "key_findings": ["分析结果解析失败"],
            "needs_more_data": False,
            "confidence": 0.5
        }
    
    def _prepare_data_summary(self, state: ResearchState) -> str:
        """准备数据摘要供LLM分析"""
        summaries = []
        
        for i, note in enumerate(state.documents):  # 全量处理
            detail = note.detail
            preview = note.preview
            
            summary = f"""
### 笔记 {i+1}: {detail.title or preview.title}
- 作者: {detail.author or preview.author}
- 点赞: {detail.likes or preview.likes}
- 内容: {detail.content or preview.content_preview}
- 标签: {', '.join(detail.tags) if detail.tags else '无'}
- 图片数量: {len(detail.images)}
"""
            summaries.append(summary)
        
        return "\n".join(summaries)
