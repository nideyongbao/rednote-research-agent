"""图片处理模块 - VLM理解 + 图片生成"""

import asyncio
import logging
from typing import Optional
from pydantic import BaseModel
from openai import AsyncOpenAI

from ..state import ResearchState
from ..services.settings import get_settings_service

logger = logging.getLogger(__name__)


class ImageAnalysis(BaseModel):
    """图片分析结果"""
    image_index: int
    image_url: str
    description: str  # 图片内容简述
    tags: list[str]  # 主要元素标签
    matched_section: str  # 最匹配的章节标题
    relevance_score: int  # 与章节相关度 1-10
    quality_score: int  # 图片质量 1-10
    should_use: bool  # 是否建议采用
    reason: str  # 原因说明


class ImageProcessor:
    """
    图片处理器
    
    职责：
    1. 使用VLM批量理解笔记中的图片
    2. 判断图片与提纲的相关性
    3. 为每个章节分配图片（去重）
    4. 需要时调用ImageGen生成新图片
    """
    
    def __init__(self):
        """初始化图片处理器"""
        self.settings = get_settings_service().load()
        
        # 获取有效的API Key（VLM/ImageGen使用LLM的Key作为备用）
        llm_api_key = self.settings.llm.api_key
        vlm_api_key = self.settings.vlm.api_key if self.settings.vlm.api_key else llm_api_key
        imagegen_api_key = self.settings.imageGen.api_key if self.settings.imageGen.api_key else llm_api_key
        
        # VLM 客户端 - 使用VLM配置的base_url，但可能共享LLM的API Key
        self.vlm_client = AsyncOpenAI(
            api_key=vlm_api_key,
            base_url=self.settings.vlm.base_url or self.settings.llm.base_url
        )
        
        # 图片生成客户端（如果启用）
        if self.settings.imageGen.enabled:
            self.imagegen_client = AsyncOpenAI(
                api_key=imagegen_api_key,
                base_url=self.settings.imageGen.base_url or self.settings.llm.base_url
            )
        else:
            self.imagegen_client = None
        
        # 已使用的图片URL（防止重复）
        self.used_images: set[str] = set()
    
    async def process(
        self, 
        state: ResearchState, 
        outline: list[dict]
    ) -> list[dict]:
        """
        处理图片：分析、分配、生成
        
        Args:
            state: 研究状态（包含documents）
            outline: 生成的大纲
            
        Returns:
            带图片分配的大纲
        """
        if not self.settings.vlm.enabled:
            logger.info("[ImageProcessor] VLM未启用，使用原有图片分配逻辑")
            return self._fallback_image_assignment(state, outline)
        
        # 1. 收集所有图片
        all_images = self._collect_images(state)
        if not all_images:
            logger.warning("[ImageProcessor] 未找到任何图片")
            return outline
        
        logger.info(f"[ImageProcessor] 收集到 {len(all_images)} 张图片，开始VLM分析")
        
        # 2. VLM批量分析图片
        analyses = await self._analyze_images(all_images, outline, state.task)
        
        # 3. 为每个章节分配图片
        enriched_outline = await self._assign_images_to_sections(
            outline, analyses, state.task
        )
        
        return enriched_outline
    
    def _collect_images(self, state: ResearchState) -> list[str]:
        """从笔记中收集所有图片URL（全量，不截断）"""
        images = []
        for note in state.documents:
            if note.detail.images:
                images.extend(note.detail.images)  # 全量收集，不限制每篇数量
        
        # 去重，不限制总数
        unique_images = list(dict.fromkeys(images))
        return unique_images
    
    async def _analyze_images(
        self, 
        images: list[str], 
        outline: list[dict],
        topic: str
    ) -> dict[str, ImageAnalysis]:
        """
        使用VLM批量分析图片
        
        Returns:
            URL -> ImageAnalysis 的字典
        """
        # 构建章节列表
        sections_text = "\n".join([
            f"- {section.get('title', 'Untitled')}: {section.get('type', 'content')}"
            for section in outline
        ])
        
        # 构建提纲JSON
        outline_json = "\n".join([
            f"{i+1}. {section.get('title', 'Untitled')}"
            for i, section in enumerate(outline)
        ])
        
        prompt = f"""你是一个图片分析专家。分析图片与报告提纲的相关性。

## 研究主题
{topic}

## 报告提纲
{outline_json}

## 输出格式（严格JSON，不要添加任何解释文字）
直接输出JSON数组，每张图片一个对象：
- image_index: 图片序号(从0开始的整数)
- description: 内容简述(20字内字符串)
- tags: 标签数组(最多5个字符串)
- matched_section: 匹配章节(字符串，无匹配填"无")
- relevance_score: 相关度(1-10整数)
- quality_score: 质量分(1-10整数)
- should_use: 是否采用(布尔值true/false)
- reason: 原因(字符串)

## 判断标准
- 广告/营销图: 相关度≤3, should_use=false
- 实拍相关图: 相关度≥7, should_use=true
- 个人专属内容(店铺招牌/二维码): 相关度≤2, should_use=false

## 输出示例
[{{"image_index":0,"description":"咖啡店内景","tags":["咖啡店","装修"],"matched_section":"店铺装修","relevance_score":8,"quality_score":7,"should_use":true,"reason":"实拍装修图"}}]

请直接输出JSON数组，不要输出任何其他内容："""
        
        # 分批处理：每批最多20张图片（VLM单次请求限制）
        BATCH_SIZE = 20
        # 根据配置决定是否使用速率限制模式
        use_rate_limit = getattr(self.settings.vlm, 'rate_limit_mode', True)
        BATCH_DELAY = 3.0 if use_rate_limit else 0  # 串行延迟模式才有延迟
        MAX_RETRIES = 3 if use_rate_limit else 1    # 快速模式不重试
        
        if use_rate_limit:
            logger.info("[ImageProcessor] 使用稳定模式（串行+延迟+重试）")
        else:
            logger.info("[ImageProcessor] 使用快速模式（无延迟）")
        
        all_analyses = {}
        total_batches = (len(images) + BATCH_SIZE - 1) // BATCH_SIZE
        
        for batch_idx in range(total_batches):
            start = batch_idx * BATCH_SIZE
            end = min(start + BATCH_SIZE, len(images))
            batch_images = images[start:end]
            
            logger.info(f"[ImageProcessor] VLM分析批次 {batch_idx+1}/{total_batches}，图片 {start+1}-{end}")
            
            # 构建多图消息
            content = [{"type": "text", "text": prompt}]
            for i, img_url in enumerate(batch_images):
                content.append({
                    "type": "image_url",
                    "image_url": {"url": img_url}
                })
            
            # 带重试的VLM调用
            for retry in range(MAX_RETRIES):
                try:
                    response = await self.vlm_client.chat.completions.create(
                        model=self.settings.vlm.model,
                        messages=[{"role": "user", "content": content}],
                        max_tokens=self.settings.vlm.max_tokens,
                        temperature=self.settings.vlm.temperature
                    )
                    
                    result_text = response.choices[0].message.content or "[]"
                    
                    # 多重fallback解析（VLM输出格式不总是规范）
                    import json
                    import re
                    import ast
                    
                    analyses_list = []
                    
                    # 提取JSON数组部分
                    json_start = result_text.find("[")
                    json_end = result_text.rfind("]") + 1
                    
                    if json_start >= 0 and json_end > json_start:
                        json_str = result_text[json_start:json_end]
                        
                        # 方案1: 标准JSON解析
                        try:
                            analyses_list = json.loads(json_str)
                        except json.JSONDecodeError:
                            # 方案2: 修复常见错误后重试
                            try:
                                # 修复：单引号→双引号，尾部逗号，True/False→true/false
                                fixed = json_str.replace("'", '"')
                                fixed = re.sub(r',\s*]', ']', fixed)
                                fixed = re.sub(r',\s*}', '}', fixed)
                                fixed = re.sub(r'\bTrue\b', 'true', fixed)
                                fixed = re.sub(r'\bFalse\b', 'false', fixed)
                                analyses_list = json.loads(fixed)
                            except json.JSONDecodeError:
                                # 方案3: 使用ast.literal_eval（支持Python格式）
                                try:
                                    analyses_list = ast.literal_eval(json_str)
                                except (ValueError, SyntaxError):
                                    logger.warning(f"[ImageProcessor] 批次{batch_idx+1}无法解析，跳过")
                                    analyses_list = []
                    else:
                        logger.warning(f"[ImageProcessor] 批次{batch_idx+1}未找到JSON数组")
                        analyses_list = []
                    
                    # 转换为字典（调整索引为全局索引）
                    for item in analyses_list:
                        local_idx = item.get("image_index", 0)
                        global_idx = start + local_idx
                        if global_idx < len(images):
                            url = images[global_idx]
                            all_analyses[url] = ImageAnalysis(
                                image_index=global_idx,
                                image_url=url,
                                description=item.get("description", ""),
                                tags=item.get("tags", []),
                                matched_section=item.get("matched_section", "无"),
                                relevance_score=item.get("relevance_score", 5),
                                quality_score=item.get("quality_score", 5),
                                should_use=item.get("should_use", False),
                                reason=item.get("reason", "")
                            )
                    
                    logger.info(f"[ImageProcessor] 批次{batch_idx+1}完成，累计{len(all_analyses)}张")
                    break  # 成功则跳出重试循环
                    
                except Exception as e:
                    error_str = str(e)
                    if "429" in error_str or "rate limit" in error_str.lower():
                        wait_time = (retry + 1) * 10  # 指数退避：10s, 20s, 30s
                        logger.warning(f"[ImageProcessor] 批次{batch_idx+1}触发速率限制，等待{wait_time}秒后重试({retry+1}/{MAX_RETRIES})")
                        await asyncio.sleep(wait_time)
                    else:
                        logger.error(f"[ImageProcessor] 批次{batch_idx+1}失败: {e}")
                        break  # 非429错误不重试
            
            # 批次间延迟，避免触发速率限制
            if batch_idx < total_batches - 1:
                logger.info(f"[ImageProcessor] 等待{BATCH_DELAY}秒后处理下一批...")
                await asyncio.sleep(BATCH_DELAY)
        
        logger.info(f"[ImageProcessor] VLM分析全部完成，共{len(all_analyses)}张图片有结果")
        return all_analyses
    
    async def _assign_images_to_sections(
        self,
        outline: list[dict],
        analyses: dict[str, ImageAnalysis],
        topic: str
    ) -> list[dict]:
        """为每个章节分配图片"""
        enriched_outline = []
        
        for section in outline:
            section_title = section.get("title", "")
            section_type = section.get("type", "content")
            
            # 跳过封面和总结
            if section_type in ["cover", "summary"]:
                enriched_outline.append({**section, "images": []})
                continue
            
            # 筛选适合当前章节的图片
            candidates = []
            for url, analysis in analyses.items():
                if url in self.used_images:
                    continue  # 跳过已使用的图片
                
                if not analysis.should_use:
                    continue
                
                # 检查匹配的章节
                if analysis.matched_section == section_title or \
                   analysis.matched_section in section_title or \
                   section_title in analysis.matched_section:
                    candidates.append((url, analysis))
            
            # 按相关度+质量综合评分排序
            candidates.sort(
                key=lambda x: x[1].relevance_score * 0.6 + x[1].quality_score * 0.4,
                reverse=True
            )
            
            # 选取Top图片
            MIN_IMAGES = 2
            MAX_IMAGES = 4
            
            selected_urls = []
            for url, analysis in candidates[:MAX_IMAGES]:
                selected_urls.append(url)
                self.used_images.add(url)
            
            # 如果图片不足且启用了图片生成
            if len(selected_urls) < MIN_IMAGES and self.settings.imageGen.enabled:
                needed = MIN_IMAGES - len(selected_urls)
                logger.info(f"[ImageProcessor] 章节'{section_title}'图片不足，需生成{needed}张")
                
                generated = await self._generate_images(section, topic, needed)
                selected_urls.extend(generated)
            
            enriched_outline.append({
                **section,
                "images": selected_urls
            })
            
            # 详细日志：显示匹配结果
            logger.info(f"[ImageProcessor] 章节'{section_title}' | 候选: {len(candidates)}张 | 分配: {len(selected_urls)}张")
        
        return enriched_outline
    
    async def _generate_images(
        self, 
        section: dict, 
        topic: str, 
        count: int
    ) -> list[str]:
        """为章节生成图片"""
        if not self.imagegen_client:
            return []
        
        generated_urls = []
        
        for i in range(count):
            prompt = f"""创建一张高品质的小红书风格配图：

主题：{topic}
章节：{section.get('title', '')}
内容要点：{section.get('content', '')[:100]}

风格要求：
- 小红书博主风格，温馨有质感
- 色调明亮，构图美观
- 可以包含简单的文字排版
"""
            
            try:
                # 调用图片生成API
                response = await self.imagegen_client.images.generate(
                    model=self.settings.imageGen.model,
                    prompt=prompt,
                    n=1,
                    size=f"{self.settings.imageGen.width}x{self.settings.imageGen.height}"
                )
                
                if response.data and response.data[0].url:
                    generated_urls.append(response.data[0].url)
                    logger.info(f"[ImageProcessor] 生成图片成功")
                    
            except Exception as e:
                logger.error(f"[ImageProcessor] 图片生成失败: {e}")
        
        return generated_urls
    
    def _fallback_image_assignment(
        self, 
        state: ResearchState, 
        outline: list[dict]
    ) -> list[dict]:
        """备用图片分配逻辑（VLM未启用时使用）"""
        enriched_outline = []
        image_pool = []
        
        # 收集所有图片
        for note in state.documents:
            if note.detail.images:
                image_pool.extend(note.detail.images[:2])
        
        # 简单轮询分配
        image_idx = 0
        for section in outline:
            section_type = section.get("type", "content")
            
            if section_type in ["cover", "summary"]:
                enriched_outline.append({**section, "images": []})
                continue
            
            # 分配2-4张图片
            section_images = []
            for _ in range(min(3, len(image_pool) - image_idx)):
                if image_idx < len(image_pool):
                    section_images.append(image_pool[image_idx])
                    image_idx += 1
            
            enriched_outline.append({**section, "images": section_images})
        
        return enriched_outline


async def process_images(
    state: ResearchState, 
    outline: list[dict]
) -> list[dict]:
    """便捷函数：处理图片"""
    processor = ImageProcessor()
    return await processor.process(state, outline)
