"""大纲生成器 - 将分析结果转换为结构化大纲"""

import json
from typing import Optional, Callable
from openai import AsyncOpenAI
from ..state import ResearchState
from ..prompts.outline_generator import OUTLINE_GENERATOR_PROMPT


class OutlineSection:
    """大纲章节数据结构"""
    
    def __init__(
        self,
        type: str,
        title: str,
        content: str,
        source_notes: list[int] = None,
        images: list[str] = None
    ):
        self.type = type
        self.title = title
        self.content = content
        self.source_notes = source_notes or []
        self.images = images or []
    
    def to_dict(self) -> dict:
        return {
            "type": self.type,
            "title": self.title,
            "content": self.content,
            "source_notes": self.source_notes,
            "images": self.images
        }


class OutlineGenerator:
    """
    大纲生成器
    
    职责：将 Analyzer 输出的 insights 和笔记数据转换为结构化大纲
    
    设计理念：
    1. 按主题/维度组织内容
    2. 为每个章节关联相关笔记和图片
    3. 确保每个论点都有数据来源标注
    """
    
    def __init__(self, llm_client: AsyncOpenAI, model: str):
        self.llm = llm_client
        self.model = model
    
    async def generate(
        self, 
        state: ResearchState,
        on_log: Optional[Callable[[str], None]] = None
    ) -> list[dict]:
        """
        生成结构化大纲
        
        Args:
            state: 包含 insights, documents 和 image_analyses 的研究状态
            on_log: 可选的日志回调
            
        Returns:
            结构化大纲列表
        """
        if on_log:
            on_log("📑 [OutlineGenerator] 开始生成结构化大纲...")
        
        # 准备数据
        notes_summary = self._prepare_notes_summary(state)
        insights_text = self._format_insights(state.insights)
        image_context = self._prepare_image_context(state)
        
        messages = [
            {"role": "system", "content": OUTLINE_GENERATOR_PROMPT},
            {"role": "user", "content": f"""
## 研究主题
{state.task}

## 分析洞察
{insights_text}

## 可用图片统计
{image_context}

## 笔记数据（共 {len(state.documents)} 篇）
{notes_summary}

请生成结构化大纲，根据图片分布合理规划每章节建议配图数量（suggested_image_count）和偏好类型（preferred_image_types）。
"""}
        ]
        
        try:
            response = await self.llm.chat.completions.create(
                model=self.model,
                messages=messages,
                max_tokens=4000,
                temperature=0.5
            )
            
            content = response.choices[0].message.content or "[]"
            
            # 解析 JSON
            outline = self._parse_outline(content, state)
            
            if on_log:
                on_log(f"📑 [OutlineGenerator] 生成了 {len(outline)} 个章节")
            
            return outline
            
        except Exception as e:
            if on_log:
                on_log(f"⚠ [OutlineGenerator] 生成失败: {str(e)[:100]}，使用备用方案")
            return self._generate_fallback_outline(state)
    
    def _prepare_notes_summary(self, state: ResearchState) -> str:
        """准备笔记摘要供 LLM 分析"""
        summaries = []
        
        for i, note in enumerate(state.documents[:15]):
            detail = note.detail
            preview = note.preview
            
            title = detail.title or preview.title
            content = (detail.content or preview.content_preview)[:200]
            images = detail.images[:2] if detail.images else []
            
            summary = f"""
### 笔记 {i}: {title}
- 作者: {detail.author or preview.author}
- 点赞: {detail.likes or preview.likes}
- 内容: {content}...
- 图片数量: {len(detail.images if detail.images else [])}
"""
            summaries.append(summary)
        
        return "\n".join(summaries)
    
    def _format_insights(self, insights: Optional[dict]) -> str:
        """格式化分析洞察"""
        if not insights:
            return "无分析结果"
        
        parts = []
        
        if "key_findings" in insights:
            parts.append("### 核心发现")
            for i, finding in enumerate(insights["key_findings"]):
                # 兼容结构化对象和字符串
                text = finding.get("statement", "") if isinstance(finding, dict) else str(finding)
                parts.append(f"{i+1}. {text}")
        
        if "user_pain_points" in insights:
            parts.append("\n### 用户痛点")
            for point in insights["user_pain_points"]:
                # 兼容结构化对象和字符串
                text = point.get("point", "") if isinstance(point, dict) else str(point)
                parts.append(f"- {text}")
        
        if "recommendations" in insights:
            parts.append("\n### 建议")
            for rec in insights["recommendations"]:
                parts.append(f"- {rec}")
        
        return "\n".join(parts)
    
    def _prepare_image_context(self, state: ResearchState) -> str:
        """准备图片上下文信息供大纲生成参考"""
        if not state.image_analyses:
            return "暂无图片分析结果"
        
        # 统计分类
        categories = {}
        usable_count = 0
        for result in state.image_analyses.values():
            cat = result.category or "未分类"
            categories[cat] = categories.get(cat, 0) + 1
            if result.should_use:
                usable_count += 1
        
        parts = [f"- 总图片数: {len(state.image_analyses)}"]
        parts.append(f"- 可用图片: {usable_count}")
        parts.append("- 分类统计:")
        for cat, count in categories.items():
            parts.append(f"  - {cat}: {count}张")
        
        return "\n".join(parts)
    
    def _parse_outline(self, content: str, state: ResearchState) -> list[dict]:
        """解析 LLM 输出的 JSON 大纲"""
        try:
            # 清理 markdown 代码块标记
            content = content.strip()
            if content.startswith("```"):
                lines = content.split("\n")
                content = "\n".join(lines[1:-1] if lines[-1] == "```" else lines[1:])
            
            # 查找 JSON 数组
            json_start = content.find("[")
            json_end = content.rfind("]") + 1
            if json_start >= 0 and json_end > json_start:
                outline_data = json.loads(content[json_start:json_end])
            else:
                return self._generate_fallback_outline(state)
            
            # 为每个章节添加图片
            outline = []
            for section in outline_data:
                section_dict = {
                    "type": section.get("type", "content"),
                    "title": section.get("title", ""),
                    "content": section.get("content", ""),
                    "source_notes": section.get("source_notes", []),
                    "images": []
                }
                
                # 从引用的笔记中提取图片
                for note_idx in section_dict["source_notes"]:
                    if 0 <= note_idx < len(state.documents):
                        note = state.documents[note_idx]
                        if note.detail.images:
                            section_dict["images"].extend(note.detail.images[:2])
                
                # 限制每章节最多 4 张图片
                section_dict["images"] = section_dict["images"][:4]
                
                outline.append(section_dict)
            
            return outline
            
        except json.JSONDecodeError:
            return self._generate_fallback_outline(state)
    
    def _generate_fallback_outline(self, state: ResearchState) -> list[dict]:
        """生成备用大纲（当 LLM 失败时）"""
        outline = []
        
        # 封面
        outline.append({
            "type": "cover",
            "title": state.task,
            "content": f"# {state.task}\n\n基于 {len(state.documents)} 篇小红书笔记的深度研究",
            "source_notes": [],
            "images": []
        })
        
        # 核心发现
        if state.insights and state.insights.get("key_findings"):
            findings = state.insights["key_findings"]
            content = "## 核心发现\n\n"
            for i, f in enumerate(findings):
                text = f.get("statement", "") if isinstance(f, dict) else str(f)
                content += f"{i+1}. {text}\n"
            
            outline.append({
                "type": "content",
                "title": "核心发现",
                "content": content,
                "source_notes": list(range(min(3, len(state.documents)))),
                "images": self._collect_images(state, 0, 3)
            })
        
        # 用户痛点
        if state.insights and state.insights.get("user_pain_points"):
            points = state.insights["user_pain_points"]
            content = "## 用户痛点\n\n"
            for p in points:
                text = p.get("point", "") if isinstance(p, dict) else str(p)
                content += f"- {text}\n"
            
            outline.append({
                "type": "content",
                "title": "用户痛点",
                "content": content,
                "source_notes": list(range(3, min(6, len(state.documents)))),
                "images": self._collect_images(state, 3, 6)
            })
        
        # 建议总结
        if state.insights and state.insights.get("recommendations"):
            recs = state.insights["recommendations"]
            content = "## 建议与总结\n\n"
            for r in recs:
                content += f"- {r}\n"
            
            outline.append({
                "type": "summary",
                "title": "建议与总结",
                "content": content,
                "source_notes": [],
                "images": []
            })
        
        return outline
    
    def _collect_images(self, state: ResearchState, start: int, end: int) -> list[str]:
        """从笔记中收集图片"""
        images = []
        for i in range(start, min(end, len(state.documents))):
            note = state.documents[i]
            if note.detail.images:
                images.extend(note.detail.images[:2])
        return images[:4]
