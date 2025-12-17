"""HTML报告生成器 - 使用LLM生成图文交错的HTML报告"""

import re
from typing import Optional
from openai import AsyncOpenAI
from ..state import ResearchState


HTML_WRITER_PROMPT = '''你是一个专业的HTML报告撰写专家。根据提供的研究数据，生成一份精美的图文交错HTML报告。

## 核心要求
1. **图文交错**：图片应该自然地嵌入在文字段落之间，而不是集中在最后
2. **防盗链处理**：所有图片必须使用 `referrerpolicy="no-referrer"` 属性
3. **美观排版**：使用现代CSS，Card布局，渐变背景
4. **响应式设计**：适配手机和电脑
5. **引用标注**：每个论点需标注来源笔记标题

## 图片标签格式（必须严格遵守）
```html
<figure class="note-image">
  <img src="{image_url}" alt="相关描述" referrerpolicy="no-referrer" loading="lazy">
  <figcaption>来源：{笔记标题}</figcaption>
</figure>
```

## HTML结构要求
1. 包含完整的 <!DOCTYPE html> 声明
2. 使用内联CSS样式（不依赖外部CSS文件）
3. 主色调使用小红书红色 #ff2442
4. 背景使用浅色渐变 linear-gradient(135deg, #fff5f5 0%, #fff 100%)

## 报告结构
1. 标题区：研究主题 + 生成时间
2. 摘要区：核心发现（3-5条）
3. 正文区：按维度分章节，每章节包含图片和文字
4. 结论区：总结建议
5. 来源区：列出引用的笔记

## 输出
直接输出完整的HTML代码（从<!DOCTYPE html>开始），不要包含任何解释性文字、markdown代码块标记。'''


class HTMLReportGenerator:
    """
    使用LLM生成图文交错的HTML报告
    
    设计理念：让LLM直接生成完整HTML，实现精细的图文排版控制
    """
    
    def __init__(self, llm_client: AsyncOpenAI, model: str = "gpt-4o"):
        """
        初始化HTML生成器
        
        Args:
            llm_client: OpenAI客户端
            model: 使用的模型
        """
        self.llm = llm_client
        self.model = model
    
    async def generate(self, state: ResearchState) -> str:
        """
        生成图文交错的HTML报告
        
        Args:
            state: 包含研究数据的状态对象
            
        Returns:
            完整的HTML字符串
        """
        # 构建给LLM的数据摘要
        data_summary = self._prepare_data_for_llm(state)
        
        messages = [
            {"role": "system", "content": HTML_WRITER_PROMPT},
            {"role": "user", "content": f"""
## 研究主题
{state.task}

## 研究计划
{state.plan.model_dump_json(indent=2) if state.plan else "无"}

## 分析洞察
{self._format_insights(state.insights)}

## 收集到的笔记数据
{data_summary}

请生成一份精美的图文交错HTML报告。确保图片和文字自然交错，每个关键论点都有配图。
"""}
        ]
        
        response = await self.llm.chat.completions.create(
            model=self.model,
            messages=messages,
            max_tokens=8000,
            temperature=0.7
        )
        
        html = response.choices[0].message.content or ""
        
        # 清理markdown代码块标记
        html = self._clean_markdown_wrapper(html)
        
        # 后处理：确保所有图片都有防盗链属性
        html = self._ensure_referrer_policy(html)
        
        return html
    
    def _prepare_data_for_llm(self, state: ResearchState) -> str:
        """将笔记数据整理为LLM可理解的格式"""
        summaries = []
        
        for i, note in enumerate(state.documents[:10]):  # 限制数量避免超出token
            detail = note.detail
            preview = note.preview
            
            title = detail.title or preview.title
            content = (detail.content or preview.content_preview)[:300]
            images = detail.images[:3]  # 每篇最多3张图
            
            summary = f"""
### 笔记 {i+1}: {title}
- 作者: {detail.author or preview.author}
- 点赞: {detail.likes or preview.likes}
- 内容摘要: {content}...
- 可用图片链接:"""
            
            for j, img in enumerate(images):
                summary += f"\n  图片{j+1}: {img}"
            
            if detail.tags:
                summary += f"\n- 标签: {', '.join(detail.tags[:5])}"
            
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
