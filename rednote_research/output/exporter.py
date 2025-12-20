"""报告导出服务 - 支持多格式导出"""

import re
from typing import Optional
from datetime import datetime


class ReportExporter:
    """
    报告导出器
    
    支持格式：
    - HTML (直接返回)
    - Markdown
    - PDF (需要额外依赖)
    """
    
    @staticmethod
    def to_markdown(
        topic: str,
        insights: dict,
        outline: list,
        notes: list
    ) -> str:
        """
        导出为Markdown格式
        
        Args:
            topic: 研究主题
            insights: 分析洞察
            outline: 结构化大纲
            notes: 笔记列表
            
        Returns:
            Markdown文本
        """
        lines = [
            f"# {topic}",
            f"",
            f"> 生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M')} | 基于 {len(notes)} 篇笔记分析",
            f"",
        ]
        
        # 关键发现
        if insights and "key_findings" in insights:
            lines.append("## ✨ 关键发现")
            lines.append("")
            for i, finding in enumerate(insights["key_findings"][:5], 1):
                lines.append(f"{i}. {finding}")
            lines.append("")
        
        # 章节内容
        for i, section in enumerate(outline, 1):
            section_title = section.get('title', f'章节 {i}')
            section_content = section.get('content', '')
            images = section.get('images', [])
            
            lines.append(f"## {i}. {section_title}")
            lines.append("")
            
            if section_content:
                lines.append(section_content)
                lines.append("")
            
            # 图片
            for j, img in enumerate(images[:3], 1):
                lines.append(f"![图片{j}]({img})")
            
            lines.append("")
        
        # 数据来源
        lines.append("## 📚 数据来源")
        lines.append("")
        for note in notes[:10]:
            note_title = note.get('title', '未知标题')
            note_url = note.get('url', '#')
            note_author = note.get('author', '未知作者')
            note_likes = note.get('likes', 0)
            lines.append(f"- [{note_title}]({note_url}) - {note_author} ❤️ {note_likes}")
        lines.append("")
        
        # 页脚
        lines.append("---")
        lines.append("*由 RedNote Research Agent 生成*")
        
        return "\n".join(lines)
    
    @staticmethod
    def html_to_text(html: str) -> str:
        """将HTML转换为纯文本"""
        # 移除style和script标签
        text = re.sub(r'<style[^>]*>.*?</style>', '', html, flags=re.DOTALL | re.IGNORECASE)
        text = re.sub(r'<script[^>]*>.*?</script>', '', text, flags=re.DOTALL | re.IGNORECASE)
        
        # 处理标题
        text = re.sub(r'<h1[^>]*>(.*?)</h1>', r'\n# \1\n', text, flags=re.IGNORECASE)
        text = re.sub(r'<h2[^>]*>(.*?)</h2>', r'\n## \1\n', text, flags=re.IGNORECASE)
        text = re.sub(r'<h3[^>]*>(.*?)</h3>', r'\n### \1\n', text, flags=re.IGNORECASE)
        
        # 处理段落和换行
        text = re.sub(r'<p[^>]*>(.*?)</p>', r'\1\n', text, flags=re.IGNORECASE | re.DOTALL)
        text = re.sub(r'<br\s*/?>', '\n', text, flags=re.IGNORECASE)
        text = re.sub(r'<li[^>]*>(.*?)</li>', r'• \1\n', text, flags=re.IGNORECASE | re.DOTALL)
        
        # 移除所有标签
        text = re.sub(r'<[^>]+>', '', text)
        
        # 清理多余空行和空格
        text = re.sub(r'\n\s*\n\s*\n', '\n\n', text)
        text = re.sub(r'  +', ' ', text)
        
        return text.strip()
    
    @staticmethod
    async def to_pdf(html: str) -> Optional[bytes]:
        """
        导出为PDF格式
        
        需要安装: pip install weasyprint
        
        Args:
            html: HTML内容
            
        Returns:
            PDF字节数据，失败返回None
            
        Raises:
            ImportError: WeasyPrint未安装
            Exception: 其他转换错误
        """
        import logging
        logger = logging.getLogger(__name__)
        
        try:
            from weasyprint import HTML
            logger.info("[Exporter] 开始PDF转换...")
            pdf_bytes = HTML(string=html).write_pdf()
            logger.info(f"[Exporter] PDF转换成功，大小: {len(pdf_bytes)} bytes")
            return pdf_bytes
        except ImportError as e:
            logger.error(f"[Exporter] WeasyPrint未安装: {e}")
            raise ImportError("WeasyPrint未安装，请执行: pip install weasyprint")
        except Exception as e:
            logger.error(f"[Exporter] PDF转换失败: {type(e).__name__}: {e}")
            raise Exception(f"PDF转换失败: {e}")


def export_to_markdown(topic: str, insights: dict, outline: list, notes: list) -> str:
    """便捷函数"""
    return ReportExporter.to_markdown(topic, insights, outline, notes)
