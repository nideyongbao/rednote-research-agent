"""
图片分配器 - 为章节分配图片并按需生成

职责：
1. 根据图片分析结果为章节匹配图片
2. 按章节类型分配合适数量的图片
3. 如果图片不足且启用了图片生成，调用AI生成
"""

import asyncio
import logging
from typing import Callable, Optional
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
        outline: list[dict],
        on_log: Optional[Callable[[str], None]] = None
    ) -> list[dict]:
        """
        为大纲的每个章节分配图片
        
        Args:
            state: 包含image_analyses的研究状态
            outline: 结构化大纲
            on_log: 日志回调
            
        Returns:
            添加了images字段的大纲
        """
        enriched_outline = []
        
        for section in outline:
            section_title = section.get("title", "")
            section_content = section.get("content", "")
            section_type = section.get("type", "content")
            suggested_count = section.get("suggested_image_count", 2)
            
            # 使用OutlineGenerator输出的图片需求（优先）或fallback到旧字段
            required_keywords = section.get("required_image_keywords", [])
            preferred_scene_types = section.get("preferred_scene_types", [])
            preferred_types = section.get("preferred_image_types", [])  # 兼容旧字段
            
            # 跳过封面和总结
            if section_type in ["cover", "summary"]:
                enriched_outline.append({**section, "images": []})
                continue
            
            # 筛选候选图片（传入required_keywords用于语义匹配）
            candidates = self._find_candidates(
                state.image_analyses,
                section_title,
                section_content,
                required_keywords,
                preferred_scene_types,
                preferred_types
            )
            
            # 选取图片
            MIN_IMAGES = 1
            MAX_IMAGES = min(suggested_count + 1, 4)
            SCORE_THRESHOLD = 8  # 匹配分数阈值，低于此值视为不匹配
            
            selected_urls = []
            best_score = 0
            for url, result, score in candidates[:MAX_IMAGES]:
                selected_urls.append(url)
                self.used_images.add(url)
                if score > best_score:
                    best_score = score
            
            # 改进的图片生成触发条件：
            # 1. 图片数量不足
            # 2. 或者有图片但匹配分数过低（语义不匹配）
            should_generate = (
                len(selected_urls) < MIN_IMAGES or 
                (len(selected_urls) > 0 and best_score < SCORE_THRESHOLD)
            )
            
            if should_generate:
                if self.settings.imageGen.enabled:
                    needed = max(MIN_IMAGES - len(selected_urls), 1)
                    reason = "图片不足" if len(selected_urls) < MIN_IMAGES else f"匹配分数过低({best_score}<{SCORE_THRESHOLD})"
                    msg = f"[ImageAssigner] 章节'{section_title}' {reason}，生成{needed}张"
                    logger.info(msg)
                    if on_log: on_log(msg)
                    
                    generated = await self._generate_images(section, state.task, needed)
                    selected_urls.extend(generated)
                else:
                    msg = f"[ImageAssigner] 章节'{section_title}' 需要生成图片但功能未启用 (Found {len(selected_urls)}, BestScore {best_score})"
                    logger.info(msg)
                    # 降低日志级别或仅调试时显示，以免刷屏，但这里为了调试目的显示
                    if on_log: on_log(msg)
            
            enriched_outline.append({
                **section,
                "images": selected_urls
            })
            
            logger.info(f"[ImageAssigner] '{section_title}' | 候选: {len(candidates)} | 最高分: {best_score} | 分配: {len(selected_urls)}")
        
        return enriched_outline
    
    def _find_candidates(
        self,
        analyses: dict[str, ImageAnalysisResult],
        section_title: str,
        section_content: str,
        required_keywords: list[str],
        preferred_scene_types: list[str],
        preferred_types: list[str]
    ) -> list[tuple[str, ImageAnalysisResult, int]]:
        """查找适合章节的候选图片 - 基于语义关键词匹配"""
        candidates = []
        
        # 0. 准备匹配关键词
        # 如果大纲指定了 required_keywords，则优先使用；否则从内容中提取
        if required_keywords:
            target_keywords = set(required_keywords)
        else:
            target_keywords = self._extract_keywords(section_title + " " + section_content)
            
        for url, result in analyses.items():
            if url in self.used_images:
                continue
            
            if not result.should_use:
                continue
            
            # 计算匹配分数
            score = result.quality_score
            
            # 1. 语义关键词匹配
            image_keywords = set(result.content_keywords or [])
            keyword_overlap = len(target_keywords & image_keywords)
            # 如果是 LLM 指定的精确关键词，权重更高 (+5/词)，否则 (+3/词)
            weight = 5 if required_keywords else 3
            score += keyword_overlap * weight
            
            # 2. 场景类型匹配
            if preferred_scene_types and result.scene_type in preferred_scene_types:
                 score += 5  # 明确匹配到偏好场景
            else:
                 # 否则尝试推断匹配
                 scene_match = self._match_scene_type(section_title, result.scene_type)
                 score += scene_match * 4
            
            # 3. 原有的章节标题匹配加分
            if section_title in result.matched_sections:
                score += 5
            elif any(section_title in s or s in section_title for s in result.matched_sections):
                score += 3
            
            # 4. 分类匹配加分
            if result.category in preferred_types:
                score += 2
            
            candidates.append((url, result, score))
        
        # 按分数排序
        candidates.sort(key=lambda x: x[2], reverse=True)
        
        return candidates
    
    def _extract_keywords(self, text: str) -> set[str]:
        """从文本中提取关键词（简单实现）"""
        # 移除标点，按空格分词
        import re
        words = re.findall(r'[\u4e00-\u9fa5a-zA-Z0-9]+', text)
        # 过滤太短的词
        return set(w for w in words if len(w) >= 2)
    
    def _match_scene_type(self, section_title: str, scene_type: str) -> int:
        """
        通用的场景类型匹配（无硬编码）
        
        思路：场景类型本身就是对图片的语义描述，
        直接检查scene_type中的关键词是否出现在章节标题中
        """
        if not scene_type:
            return 0
        
        # 通用方法：将场景类型分词，检查与章节标题的重叠
        # 例如："风格展示" 中的 "风格" 出现在 "北欧风格选择" 中
        scene_keywords = self._extract_keywords(scene_type)
        title_keywords = self._extract_keywords(section_title)
        
        # 计算重叠度
        overlap = len(scene_keywords & title_keywords)
        
        if overlap >= 2:
            return 2  # 高度匹配
        elif overlap >= 1:
            return 1  # 部分匹配
        else:
            return 0  # 无匹配
    
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
        
        # 使用LLM动态构建Image Prompt
        prompt = await self._build_smart_prompt(section, topic)
        logger.info(f"[ImageAssigner] 生成图片Prompt: {prompt}")
        
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

    async def _build_smart_prompt(self, section: dict, topic: str) -> str:
        """让LLM根据章节内容动态生成图片提示词"""
        try:
            # 引入LLM客户端（复用gen_client如果支持chat，或者需要传入llm_client）
            # 这里假设 gen_client 是 OpenAI 兼容客户端
            from ..config import Config
            config = Config()
            
            # 使用 LLM 生成 Prompt
            # 注意：这里需要一个 LLM 客户端。由于 ImageAssigner 初始化时可能只传入了 gen_client（通常用于绘图），
            # 如果 gen_client 不支持 chat completion，可能需要单独的 LLM client。
            # 简单起见，这里复用 self.llm_client 如果存在，或者暂时使用简单的逻辑
            # 为了确保稳健性，我们构造一个详细的 prompt
            
            content_preview = section.get('content', '')[:300]
            section_title = section.get('title', '')
            
            # 如果有 OutlineGenerator 生成的关键词，利用它们
            keywords = section.get('required_image_keywords', [])
            scene_types = section.get('preferred_scene_types', [])
            
            # 构造一个结构化的 prompt，即使不调用 LLM 也能比之前好
            base_prompt = f"为小红书笔记生成配图。\n主题：{topic}\n画面内容：{section_title}\n"
            
            if keywords:
                base_prompt += f"关键元素：{', '.join(keywords)}\n"
            
            if scene_types:
                base_prompt += f"场景风格：{', '.join(scene_types)}\n"
            else:
                 # 根据标题简单推断风格
                if any(k in section_title for k in ["预算", "费用", "表"]):
                    base_prompt += "场景风格：清晰的数据图表，扁平化设计\n"
                elif any(k in section_title for k in ["风格", "设计", "图"]):
                    base_prompt += "场景风格：高质量室内设计摄影，明亮温馨\n"
                else:
                    base_prompt += "场景风格：精致的生活方式摄影，氛围感强\n"

            base_prompt += f"参考内容：{content_preview[:100]}"
            
            return base_prompt
            
        except Exception as e:
            logger.warning(f"构建Prompt失败，使用默认: {e}")
            return f"Topic: {topic}, Section: {section.get('title')}"
