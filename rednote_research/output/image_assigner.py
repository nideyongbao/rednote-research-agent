"""
图片分配器 - 为章节分配图片并按需生成

职责：
1. 根据图片分析结果为章节匹配图片
2. 按章节类型分配合适数量的图片
3. 如果图片不足且启用了图片生成，调用AI生成
"""

import asyncio
import logging
from openai import AsyncOpenAI

from ..state import ResearchState, ImageAnalysisResult
from ..services.settings import get_settings_service

logger = logging.getLogger(__name__)


class ImageAssigner:
    """图片分配器 - 为章节分配和生成图片"""
    
    def __init__(self):
        self.settings = get_settings_service().load()
        self.used_images: set[str] = set()
        
        # 初始化图片生成客户端
        if self.settings.imageGen.enabled:
            gen_api_key = self.settings.imageGen.api_key or self.settings.llm.api_key
            self.gen_client = AsyncOpenAI(
                api_key=gen_api_key,
                base_url=self.settings.imageGen.base_url
            )
    
    async def assign(
        self,
        state: ResearchState,
        outline: list[dict]
    ) -> list[dict]:
        """
        为大纲的每个章节分配图片
        
        Args:
            state: 包含image_analyses的研究状态
            outline: 结构化大纲
            
        Returns:
            添加了images字段的大纲
        """
        enriched_outline = []
        
        for section in outline:
            section_title = section.get("title", "")
            section_type = section.get("type", "content")
            suggested_count = section.get("suggested_image_count", 2)
            preferred_types = section.get("preferred_image_types", [])
            
            # 跳过封面和总结
            if section_type in ["cover", "summary"]:
                enriched_outline.append({**section, "images": []})
                continue
            
            # 筛选候选图片
            candidates = self._find_candidates(
                state.image_analyses,
                section_title,
                preferred_types
            )
            
            # 选取图片
            MIN_IMAGES = 1
            MAX_IMAGES = min(suggested_count + 1, 4)
            
            selected_urls = []
            for url, result in candidates[:MAX_IMAGES]:
                selected_urls.append(url)
                self.used_images.add(url)
            
            # 图片不足时生成
            if len(selected_urls) < MIN_IMAGES and self.settings.imageGen.enabled:
                needed = MIN_IMAGES - len(selected_urls)
                logger.info(f"[ImageAssigner] 章节'{section_title}'图片不足，生成{needed}张")
                
                generated = await self._generate_images(section, state.task, needed)
                selected_urls.extend(generated)
            
            enriched_outline.append({
                **section,
                "images": selected_urls
            })
            
            logger.info(f"[ImageAssigner] '{section_title}' | 候选: {len(candidates)} | 分配: {len(selected_urls)}")
        
        return enriched_outline
    
    def _find_candidates(
        self,
        analyses: dict[str, ImageAnalysisResult],
        section_title: str,
        preferred_types: list[str]
    ) -> list[tuple[str, ImageAnalysisResult]]:
        """查找适合章节的候选图片"""
        candidates = []
        
        for url, result in analyses.items():
            if url in self.used_images:
                continue
            
            if not result.should_use:
                continue
            
            # 计算匹配分数
            score = result.quality_score
            
            # 章节标题匹配加分
            if section_title in result.matched_sections:
                score += 5
            elif any(section_title in s or s in section_title for s in result.matched_sections):
                score += 3
            
            # 分类匹配加分
            if result.category in preferred_types:
                score += 2
            
            candidates.append((url, result, score))
        
        # 按分数排序
        candidates.sort(key=lambda x: x[2], reverse=True)
        
        return [(url, result) for url, result, _ in candidates]
    
    async def _generate_images(
        self,
        section: dict,
        topic: str,
        count: int
    ) -> list[str]:
        """使用AI生成图片"""
        if not self.settings.imageGen.enabled:
            return []
        
        generated = []
        prompt = f"为以下内容生成配图：\n主题：{topic}\n章节：{section.get('title')}\n内容：{section.get('content', '')[:200]}"
        
        for i in range(count):
            try:
                response = await self.gen_client.images.generate(
                    model=self.settings.imageGen.model,
                    prompt=prompt,
                    n=1,
                    size="1024x1024"
                )
                
                if response.data:
                    url = response.data[0].url
                    generated.append(url)
                    logger.info(f"[ImageAssigner] 生成图片 {i+1}/{count} 成功")
                    
            except Exception as e:
                logger.error(f"[ImageAssigner] 生成图片失败: {e}")
        
        return generated
