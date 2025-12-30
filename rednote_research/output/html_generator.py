"""HTML报告生成器 - 使用LLM分章节生成图文交错的HTML报告"""

import re
import logging
from typing import Optional, Callable, AsyncGenerator
from openai import AsyncOpenAI
from ..state import ResearchState
from ..services.settings import get_settings_service
from ..prompts.section_writer import SECTION_WRITER_PROMPT

logger = logging.getLogger(__name__)


class HTMLReportGenerator:
    """
    使用LLM分章节生成图文交错的HTML报告
    
    设计理念：按章节逐步生成，降低单次LLM调用复杂度，支持流式返回
    """
    
    def __init__(self, llm_client: AsyncOpenAI, model: str):
        self.llm = llm_client
        self.model = model
        self.settings = get_settings_service().load()
    
    async def generate(self, state: ResearchState, on_progress: Optional[Callable[[int, str], None]] = None) -> str:
        """
        分章节生成HTML报告
        
        Args:
            state: 研究状态
            on_progress: 进度回调 (章节索引, 章节标题)
            
        Returns:
            完整HTML文档
        """
        # 获取结构化大纲（由ImageProcessor处理后的）
        outline = getattr(state, 'processed_outline', None)
        if not outline and hasattr(state, 'outline'):
            outline = state.outline
        
        # 如果没有大纲，使用旧的单次生成方式
        if not outline:
            logger.info("[HTMLGenerator] 无结构化大纲，使用单次生成模式")
            return await self._generate_single(state)
        
        logger.info(f"[HTMLGenerator] 分章节生成模式，共 {len(outline)} 个章节")
        
        # 构建各章节内容
        sections_html = []
        for i, section in enumerate(outline):
            section_title = section.get('title', f'章节 {i+1}')
            
            if on_progress:
                on_progress(i, section_title)
            
            logger.info(f"[HTMLGenerator] 生成章节 {i+1}/{len(outline)}: {section_title}")
            
            try:
                section_html = await self._generate_section(section, state)
                sections_html.append(section_html)
            except Exception as e:
                logger.warning(f"[HTMLGenerator] 章节生成失败: {e}, 使用备用内容")
                sections_html.append(self._generate_fallback_section(section))
        
        # 组装完整HTML
        return self._assemble_html(state.task, state.insights, sections_html, state.documents)
    
    async def _generate_section(self, section: dict, state: ResearchState) -> str:
        """生成单个章节的HTML"""
        section_type = section.get('type', 'content')
        section_title = section.get('title', '')
        section_content = section.get('content', '')
        images = section.get('images', [])
        source_notes = section.get('source_notes', [])
        
        # 准备引用的笔记数据
        notes_context = ""
        for idx in source_notes:  # 全量引用
            if idx < len(state.documents):
                note = state.documents[idx]
                notes_context += f"\n- {note.detail.title}: {note.detail.content}"
        
        # 构建章节Prompt
        prompt = f"""## 章节信息
类型: {section_type}
标题: {section_title}
内容提纲: {section_content}

## 可用图片
{chr(10).join([f'- {img}' for img in images[:4]])}

## 引用笔记
{notes_context if notes_context else '无特定引用'}

请生成这个章节的HTML内容片段，图文交错排版。"""
        
        messages = [
            {"role": "system", "content": SECTION_WRITER_PROMPT},
            {"role": "user", "content": prompt}
        ]
        
        response = await self.llm.chat.completions.create(
            model=self.model,
            messages=messages,
            max_tokens=self.settings.llm.max_tokens // 2,  # 单章节用一半token
            temperature=self.settings.llm.temperature
        )
        
        html = response.choices[0].message.content or ""
        html = self._clean_markdown_wrapper(html)
        html = self._ensure_referrer_policy(html)
        
        return f'''<section class="report-section" data-type="{section_type}">
    <h2>{section_title}</h2>
    {html}
</section>'''
    
    def _generate_fallback_section(self, section: dict) -> str:
        """生成章节备用HTML"""
        section_type = section.get('type', 'content')
        section_title = section.get('title', '章节')
        section_content = section.get('content', '')
        images = section.get('images', [])
        
        images_html = ""
        for img in images:  # 全量图片
            images_html += f'''
            <figure class="note-image">
                <img src="{img}" referrerpolicy="no-referrer" loading="lazy" alt="{section_title}">
            </figure>'''
        
        return f'''<section class="report-section" data-type="{section_type}">
    <h2>{section_title}</h2>
    <p>{section_content}</p>
    {images_html}
</section>'''
    
    def _assemble_html(self, topic: str, insights: dict, sections_html: list, documents: list) -> str:
        """组装完整HTML文档"""
        from datetime import datetime
        
        # 关键发现
        findings_html = ""
        if insights and "key_findings" in insights:
            findings_html = '<div class="findings-section"><h2>✨ 关键发现</h2><ul>'
            for finding in insights["key_findings"]:  # 全量展示
                findings_html += f'<li>{finding}</li>'
            findings_html += '</ul></div>'
        
        # 数据来源
        sources_html = '<div class="sources-section"><h2>📚 数据来源</h2><ul>'
        for note in documents:  # 全量展示
            sources_html += f'''<li>
                <a href="{note.detail.url}" target="_blank" rel="noopener">{note.detail.title}</a>
                <span class="source-meta">{note.detail.author} · ❤️ {note.detail.likes}</span>
            </li>'''
        sources_html += '</ul></div>'
        
        return f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{topic} - 研究报告</title>
    <style>
        :root {{ --primary: #ff2442; }}
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
            background: linear-gradient(135deg, #fff5f5 0%, #fff 100%);
            max-width: 900px;
            margin: 0 auto;
            padding: 40px 20px;
            line-height: 1.8;
            color: #333;
        }}
        h1 {{ color: var(--primary); font-size: 28px; margin-bottom: 8px; }}
        h2 {{ font-size: 20px; margin: 24px 0 16px; border-bottom: 2px solid var(--primary); padding-bottom: 8px; }}
        .meta {{ color: #888; font-size: 14px; margin-bottom: 32px; }}
        .report-section {{
            background: white;
            padding: 24px;
            border-radius: 16px;
            margin: 20px 0;
            box-shadow: 0 2px 12px rgba(0,0,0,0.06);
        }}
        .note-image img {{
            max-width: 100%;
            border-radius: 12px;
            margin: 16px 0;
        }}
        .note-image figcaption {{
            font-size: 12px;
            color: #888;
            text-align: center;
        }}
        .findings-section ul, .sources-section ul {{
            list-style: none;
            padding: 0;
        }}
        .findings-section li {{
            background: #fff5f5;
            padding: 12px 16px;
            margin: 8px 0;
            border-radius: 8px;
            border-left: 4px solid var(--primary);
        }}
        .sources-section li {{
            padding: 12px 16px;
            background: #f9f9f9;
            border-radius: 8px;
            margin: 8px 0;
        }}
        .sources-section a {{
            color: var(--primary);
            text-decoration: none;
            font-weight: 500;
        }}
        .source-meta {{
            display: block;
            font-size: 12px;
            color: #888;
            margin-top: 4px;
        }}
        footer {{
            text-align: center;
            color: #999;
            margin-top: 48px;
            padding-top: 24px;
            border-top: 1px solid #eee;
            font-size: 13px;
        }}
    </style>
</head>
<body>
    <h1>📝 {topic}</h1>
    <p class="meta">生成时间：{datetime.now().strftime("%Y-%m-%d %H:%M")} | 基于 {len(documents)} 篇笔记分析</p>
    
    {findings_html}
    
    {''.join(sections_html)}
    
    {sources_html}
    
    <footer>由 RedNote Research Agent 生成</footer>
</body>
</html>'''
    
    async def _generate_single(self, state: ResearchState) -> str:
        """单次生成完整报告（旧模式兼容）"""
        # 保留原有的单次生成逻辑
        HTML_WRITER_PROMPT = '''你是一个专业的HTML报告撰写专家。根据提供的研究数据，生成一份精美的图文交错HTML报告。

## 核心要求
1. 图文交错：图片自然嵌入文字段落间
2. 防盗链处理：所有图片必须使用 referrerpolicy="no-referrer"
3. 美观排版：使用现代CSS，Card布局
4. 引用标注：每个论点标注来源笔记

直接输出完整的HTML代码，不要包含markdown代码块标记。'''
        
        data_summary = self._prepare_data_for_llm(state)
        
        messages = [
            {"role": "system", "content": HTML_WRITER_PROMPT},
            {"role": "user", "content": f"""
## 研究主题
{state.task}

## 分析洞察
{self._format_insights(state.insights)}

## 笔记数据
{data_summary}

请生成图文交错HTML报告。
"""}
        ]
        
        response = await self.llm.chat.completions.create(
            model=self.model,
            messages=messages,
            max_tokens=self.settings.llm.max_tokens,
            temperature=self.settings.llm.temperature
        )
        
        html = response.choices[0].message.content or ""
        html = self._clean_markdown_wrapper(html)
        html = self._ensure_referrer_policy(html)
        
        return html
    
    def _prepare_data_for_llm(self, state: ResearchState) -> str:
        """将笔记数据整理为LLM可理解的格式"""
        summaries = []
        
        for i, note in enumerate(state.documents):  # 全量处理
            detail = note.detail
            preview = note.preview
            
            title = detail.title or preview.title
            content = detail.content or preview.content_preview  # 全量内容
            images = detail.images  # 全量图片
            
            summary = f"""
### 笔记 {i+1}: {title}
- 作者: {detail.author or preview.author}
- 点赞: {detail.likes or preview.likes}
- 内容: {content}
- 可用图片链接:"""
            
            for j, img in enumerate(images):
                summary += f"\n  图片{j+1}: {img}"
            
            if detail.tags:
                summary += f"\n- 标签: {', '.join(detail.tags)}"  # 全量标签
            
            summaries.append(summary)
        
        return "\n".join(summaries)
    
    def _format_insights(self, insights: Optional[dict]) -> str:
        """格式化分析洞察"""
        if not insights:
            return "无分析结果"
        
        parts = []
        
        if "key_findings" in insights:
            parts.append("### 核心发现")
            for finding in insights["key_findings"]:
                parts.append(f"- {finding}")
        
        if "user_pain_points" in insights:
            parts.append("\n### 用户痛点")
            for point in insights["user_pain_points"]:
                parts.append(f"- {point}")
        
        if "recommendations" in insights:
            parts.append("\n### 建议")
            for rec in insights["recommendations"]:
                parts.append(f"- {rec}")
        
        return "\n".join(parts)
    
    def _clean_markdown_wrapper(self, html: str) -> str:
        """清理markdown代码块标记"""
        # 移除 ```html 和 ``` 标记
        html = re.sub(r'^```html\s*\n?', '', html, flags=re.IGNORECASE)
        html = re.sub(r'\n?```\s*$', '', html)
        return html.strip()
    
    def _ensure_referrer_policy(self, html: str) -> str:
        """确保所有img标签都有referrerpolicy属性"""
        # 匹配没有referrerpolicy的img标签
        pattern = r'<img(?![^>]*referrerpolicy)([^>]*)>'
        replacement = r'<img\1 referrerpolicy="no-referrer">'
        
        return re.sub(pattern, replacement, html)
    
    def generate_fallback_html(self, state: ResearchState) -> str:
        """
        生成备用的简单HTML报告（当LLM生成失败时使用）
        
        Args:
            state: 研究状态
            
        Returns:
            简单的HTML报告
        """
        notes_html = ""
        for note in state.documents[:10]:
            detail = note.detail
            preview = note.preview
            title = detail.title or preview.title
            content = detail.content or preview.content_preview
            
            images_html = ""
            for img in (detail.images or [])[:2]:
                images_html += f'''
                <figure class="note-image">
                    <img src="{img}" referrerpolicy="no-referrer" loading="lazy" alt="{title}">
                </figure>'''
            
            notes_html += f'''
            <div class="card">
                <h3>{title}</h3>
                <p class="meta">👤 {detail.author or preview.author} | ❤️ {detail.likes or preview.likes}</p>
                {images_html}
                <p>{content[:200]}...</p>
            </div>'''
        
        return f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>研究报告: {state.task}</title>
    <style>
        :root {{ --primary: #ff2442; }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
            background: linear-gradient(135deg, #fff5f5 0%, #fff 100%);
            max-width: 800px;
            margin: 0 auto;
            padding: 20px;
            line-height: 1.8;
        }}
        h1 {{ color: var(--primary); }}
        .card {{
            background: white;
            padding: 20px;
            border-radius: 16px;
            margin: 16px 0;
            box-shadow: 0 2px 8px rgba(0,0,0,0.05);
        }}
        .meta {{ color: #999; font-size: 0.9em; }}
        .note-image img {{
            max-width: 100%;
            border-radius: 12px;
            margin: 10px 0;
        }}
    </style>
</head>
<body>
    <h1>📝 {state.task}</h1>
    <p>共收集 {len(state.documents)} 篇相关笔记</p>
    {notes_html}
</body>
</html>'''
