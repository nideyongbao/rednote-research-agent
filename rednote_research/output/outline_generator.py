"""大纲生成器 - 将分析结果转换为结构化大纲"""

import json
from typing import Optional, Callable
from openai import AsyncOpenAI
from ..state import ResearchState


OUTLINE_GENERATOR_PROMPT = """你是一个专业的内容结构化专家。你的任务是将研究分析结果转换为结构化的报告大纲。

## 输入
- 研究主题
- 分析洞察（key_findings, user_pain_points, recommendations）
- 笔记数据（标题、内容、图片）
- 可用图片统计

## 输出要求
生成一个 JSON 数组，每个元素代表一个章节：
```json
[
  {
    "type": "cover",
    "title": "封面标题",
    "content": "报告主题描述",
    "source_notes": [],
    "required_image_keywords": [],
    "preferred_scene_types": []
  },
  {
    "type": "content",
    "title": "章节标题",
    "content": "章节内容（使用 Markdown 格式）",
    "source_notes": [0, 2, 5],
    "required_image_keywords": ["关键词1", "关键词2"],
    "preferred_scene_types": ["场景类型"]
  },
  {
    "type": "summary",
    "title": "总结与建议",
    "content": "总结内容",
    "source_notes": [],
    "required_image_keywords": [],
    "preferred_scene_types": []
  }
]
```

## 图片需求字段说明
- **required_image_keywords**: 该章节配图应包含的关键词（3-5个），用于匹配图片
  - 例如：预算章节 → ["预算表", "费用清单", "价格对比"]
  - 例如：风格章节 → ["北欧风", "现代简约", "效果图"]
- **preferred_scene_types**: 偏好的图片场景类型（1-2个）
  - 可选值：风格展示、数据展示、教程步骤、产品展示、真实场景

## 结构化原则
1. **封面**：包含主题和基于笔记数量的描述
2. **核心发现**：将 key_findings 整理为一个章节，关联支持这些发现的笔记
3. **用户痛点**：如果有 user_pain_points，整理为独立章节
4. **详细分析**：按主题维度组织 2-3 个内容章节，每个章节关联相关笔记
5. **建议总结**：将 recommendations 整理为结论章节

## 内容格式
- 使用 Markdown 格式
- 每个论点标注来源（来源：笔记X）
- 适当使用列表、粗体等格式增强可读性

直接输出 JSON 数组，不要包含其他文字。"""


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
                parts.append(f"{i+1}. {finding}")
        
        if "user_pain_points" in insights:
            parts.append("\n### 用户痛点")
            for point in insights["user_pain_points"]:
                parts.append(f"- {point}")
        
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
                content += f"{i+1}. {f}\n"
            
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
                content += f"- {p}\n"
            
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
