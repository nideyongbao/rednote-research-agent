"""
图片分析器 - 使用VLM分析图片内容和分类

职责：
1. 收集所有笔记图片
2. 下载图片转Base64（避免CDN防盗链问题）
3. 调用VLM分批分析图片内容
4. 对图片进行分类（实景/攻略/装饰/广告）
5. 评估图片质量和可用性
"""

import asyncio
import logging
import json
import re
import base64
import aiohttp
from openai import AsyncOpenAI

from ..state import ResearchState, ImageAnalysisResult
from ..services.settings import get_settings_service

logger = logging.getLogger(__name__)


class ImageAnalyzer:
    """图片分析器 - VLM图片理解"""
    
    def __init__(self):
        self.settings = get_settings_service().load()
        
        # 初始化VLM客户端
        vlm_api_key = self.settings.vlm.api_key or self.settings.llm.api_key
        self.vlm_client = AsyncOpenAI(
            api_key=vlm_api_key,
            base_url=self.settings.vlm.base_url
        )
    
    async def analyze(self, state: ResearchState) -> ResearchState:
        """
        分析所有图片并更新state.image_analyses
        
        Args:
            state: 包含documents的研究状态
            
        Returns:
            更新了image_analyses的状态
        """
        if not self.settings.vlm.enabled:
            logger.info("[ImageAnalyzer] VLM未启用，跳过图片分析")
            return state
        
        # 1. 收集所有图片
        images = self._collect_images(state)
        if not images:
            logger.info("[ImageAnalyzer] 没有找到图片")
            return state
        
        logger.info(f"[ImageAnalyzer] 收集了 {len(images)} 张图片，开始VLM分析")
        
        # 2. 分批分析
        analyses = await self._analyze_images_batch(images, state.task)
        
        # 3. 更新state
        state.image_analyses = analyses
        
        # 4. 统计日志
        categories = {}
        for result in analyses.values():
            cat = result.category or "未分类"
            categories[cat] = categories.get(cat, 0) + 1
        
        usable = sum(1 for r in analyses.values() if r.should_use)
        logger.info(f"[ImageAnalyzer] 分析完成 | 总计: {len(analyses)}张 | 可用: {usable}张")
        logger.info(f"[ImageAnalyzer] 分类统计: {categories}")
        
        return state
    
    def _collect_images(self, state: ResearchState) -> list[str]:
        """收集所有笔记图片"""
        images = []
        for note in state.documents:
            if note.detail.images:
                images.extend(note.detail.images)
        
        # 去重
        unique_images = list(dict.fromkeys(images))
        return unique_images
    
    async def _download_image_to_base64(self, url: str, max_retries: int = 2) -> str | None:
        """
        下载图片并转换为base64格式（带重试）
        
        Args:
            url: 图片URL
            max_retries: 最大重试次数
            
        Returns:
            base64编码的data URI，失败返回None
        """
        headers = {
            "Referer": "https://www.xiaohongshu.com/",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }
        
        for attempt in range(max_retries + 1):
            try:
                # 增加超时时间到30秒
                timeout = aiohttp.ClientTimeout(total=30, connect=10)
                async with aiohttp.ClientSession(timeout=timeout) as session:
                    async with session.get(url, headers=headers) as resp:
                        if resp.status == 200:
                            data = await resp.read()
                            b64 = base64.b64encode(data).decode()
                            content_type = resp.headers.get("Content-Type", "image/jpeg")
                            return f"data:{content_type};base64,{b64}"
                        else:
                            logger.warning(f"[ImageAnalyzer] 下载图片失败 HTTP {resp.status}: {url[:60]}...")
                            break  # HTTP错误不重试
            except asyncio.TimeoutError:
                if attempt < max_retries:
                    logger.warning(f"[ImageAnalyzer] 下载图片超时(尝试{attempt+1}/{max_retries+1}): {url[:60]}...")
                    await asyncio.sleep(1)  # 短暂等待后重试
                else:
                    logger.warning(f"[ImageAnalyzer] 下载图片超时(已放弃): {url[:60]}...")
            except Exception as e:
                logger.warning(f"[ImageAnalyzer] 下载图片异常: {url[:60]}... - {e}")
                break  # 其他异常不重试
        return None
    
    async def _analyze_images_batch(
        self,
        images: list[str],
        topic: str
    ) -> dict[str, ImageAnalysisResult]:
        """分批分析图片"""
        
        # 参数配置
        BATCH_SIZE = 10  # 减小批次大小，提高稳定性
        use_rate_limit = getattr(self.settings.vlm, 'rate_limit_mode', True)
        BATCH_DELAY = 3.0 if use_rate_limit else 0
        MAX_RETRIES = 3 if use_rate_limit else 1
        
        all_analyses = {}
        total_batches = (len(images) + BATCH_SIZE - 1) // BATCH_SIZE
        
        # 优化后的prompt - 明确要求JSON输出
        prompt = f"""你是图片分析专家。请分析以下图片并以JSON数组格式输出分析结果。

## 研究主题
{topic}

## 输出要求
请输出一个JSON数组，每个元素包含以下字段：
- image_index: 图片序号（从0开始）
- description: 图片内容描述（20字以内）
- tags: 标签数组（2-3个关键词）
- category: 分类（只能是：实景、攻略、装饰、广告 之一）
- quality_score: 质量分数（1-10整数）
- should_use: 是否建议使用（true/false）

## 分类说明
- 实景: 真实场景拍摄
- 攻略: 包含文字说明的教程图
- 装饰: 通用装饰插图
- 广告: 明显的营销推广图

请直接输出JSON数组，不要添加任何解释文字："""
        
        for batch_idx in range(total_batches):
            start = batch_idx * BATCH_SIZE
            end = min(start + BATCH_SIZE, len(images))
            batch_images = images[start:end]
            batch_count = len(batch_images)
            
            logger.info(f"[ImageAnalyzer] 批次 {batch_idx+1}/{total_batches}，图片 {start+1}-{end}")
            
            # 下载图片转base64
            logger.info(f"[ImageAnalyzer] 正在下载 {batch_count} 张图片...")
            image_contents = []
            successful_downloads = 0
            
            for i, img_url in enumerate(batch_images):
                base64_data = await self._download_image_to_base64(img_url)
                if base64_data:
                    image_contents.append({
                        "type": "image_url",
                        "image_url": {"url": base64_data}
                    })
                    successful_downloads += 1
                else:
                    # 下载失败时尝试直接使用URL
                    image_contents.append({
                        "type": "image_url",
                        "image_url": {"url": img_url}
                    })
            
            logger.info(f"[ImageAnalyzer] 下载完成: {successful_downloads}/{batch_count} 成功")
            
            if not image_contents:
                logger.warning(f"[ImageAnalyzer] 批次{batch_idx+1}无可用图片，跳过")
                continue
            
            # 构建消息
            content = [{"type": "text", "text": prompt}]
            content.extend(image_contents)
            
            for retry in range(MAX_RETRIES):
                try:
                    # 使用 response_format 确保JSON输出（Qwen支持json_object）
                    response = await self.vlm_client.chat.completions.create(
                        model=self.settings.vlm.model,
                        messages=[{"role": "user", "content": content}],
                        max_tokens=self.settings.vlm.max_tokens,
                        temperature=self.settings.vlm.temperature,
                        response_format={"type": "json_object"}  # Qwen支持
                    )
                    
                    result_text = response.choices[0].message.content or "{}"
                    
                    # 记录原始响应用于调试
                    logger.info(f"[ImageAnalyzer] 批次{batch_idx+1} VLM响应: {result_text[:300]}...")
                    
                    # 解析JSON
                    analyses_list = self._parse_json_robust(result_text, batch_idx, batch_count)
                    
                    # 转换结果
                    for item in analyses_list:
                        local_idx = item.get("image_index", 0)
                        global_idx = start + local_idx
                        if global_idx < len(images):
                            url = images[global_idx]
                            all_analyses[url] = ImageAnalysisResult(
                                image_url=url,
                                description=item.get("description", ""),
                                tags=item.get("tags", []),
                                category=item.get("category", "未分类"),
                                quality_score=item.get("quality_score", 5),
                                should_use=item.get("should_use", True),
                                matched_sections=[]
                            )
                    
                    logger.info(f"[ImageAnalyzer] 批次{batch_idx+1}完成，解析{len(analyses_list)}张，累计{len(all_analyses)}张")
                    break
                    
                except Exception as e:
                    error_str = str(e)
                    if "429" in error_str or "rate limit" in error_str.lower():
                        wait_time = (retry + 1) * 10
                        logger.warning(f"[ImageAnalyzer] 速率限制，等待{wait_time}秒")
                        await asyncio.sleep(wait_time)
                    elif "response_format" in error_str.lower():
                        # 模型不支持response_format，使用fallback
                        logger.warning(f"[ImageAnalyzer] 模型不支持response_format，尝试不使用")
                        try:
                            response = await self.vlm_client.chat.completions.create(
                                model=self.settings.vlm.model,
                                messages=[{"role": "user", "content": content}],
                                max_tokens=self.settings.vlm.max_tokens,
                                temperature=self.settings.vlm.temperature
                            )
                            result_text = response.choices[0].message.content or "[]"
                            logger.info(f"[ImageAnalyzer] 批次{batch_idx+1} VLM响应(无format): {result_text[:300]}...")
                            analyses_list = self._parse_json_robust(result_text, batch_idx, batch_count)
                            for item in analyses_list:
                                local_idx = item.get("image_index", 0)
                                global_idx = start + local_idx
                                if global_idx < len(images):
                                    url = images[global_idx]
                                    all_analyses[url] = ImageAnalysisResult(
                                        image_url=url,
                                        description=item.get("description", ""),
                                        tags=item.get("tags", []),
                                        category=item.get("category", "未分类"),
                                        quality_score=item.get("quality_score", 5),
                                        should_use=item.get("should_use", True),
                                        matched_sections=[]
                                    )
                            logger.info(f"[ImageAnalyzer] 批次{batch_idx+1}完成(fallback)，累计{len(all_analyses)}张")
                            break
                        except Exception as e2:
                            logger.error(f"[ImageAnalyzer] 批次{batch_idx+1} fallback也失败: {e2}")
                            # 使用默认值
                            self._add_default_analyses(all_analyses, batch_images, images, start)
                            break
                    else:
                        logger.error(f"[ImageAnalyzer] 批次{batch_idx+1}失败: {e}")
                        if retry == MAX_RETRIES - 1:
                            # 最后一次重试仍失败，使用默认值
                            self._add_default_analyses(all_analyses, batch_images, images, start)
                        break
            
            # 批次间延迟
            if batch_idx < total_batches - 1 and BATCH_DELAY > 0:
                await asyncio.sleep(BATCH_DELAY)
        
        return all_analyses
    
    def _add_default_analyses(
        self, 
        all_analyses: dict, 
        batch_images: list[str], 
        all_images: list[str], 
        start_idx: int
    ):
        """添加默认分析结果（当VLM失败时使用）"""
        for i, url in enumerate(batch_images):
            if url not in all_analyses:
                all_analyses[url] = ImageAnalysisResult(
                    image_url=url,
                    description="",
                    tags=[],
                    category="未分类",
                    quality_score=5,
                    should_use=True,  # 默认可用，让后续流程决定
                    matched_sections=[]
                )
        logger.info(f"[ImageAnalyzer] 使用默认值填充 {len(batch_images)} 张图片")
    
    def _parse_json_robust(self, text: str, batch_idx: int, expected_count: int) -> list:
        """
        多层fallback解析JSON
        
        Args:
            text: VLM返回的文本
            batch_idx: 批次索引
            expected_count: 预期的图片数量
            
        Returns:
            解析后的列表
        """
        import ast
        
        # 1. 尝试直接解析（response_format返回的应该是纯JSON）
        try:
            result = json.loads(text)
            # 可能返回的是 {"analyses": [...]} 格式
            if isinstance(result, dict):
                for key in ["analyses", "images", "results", "data"]:
                    if key in result and isinstance(result[key], list):
                        return result[key]
                # 单个对象转数组
                return [result]
            elif isinstance(result, list):
                return result
        except json.JSONDecodeError:
            pass
        
        # 2. 提取markdown代码块中的JSON
        json_match = re.search(r'```(?:json)?\s*([\s\S]*?)```', text)
        if json_match:
            try:
                return json.loads(json_match.group(1))
            except json.JSONDecodeError:
                pass
        
        # 3. 查找并提取JSON数组
        json_start = text.find("[")
        json_end = text.rfind("]") + 1
        
        if json_start >= 0 and json_end > json_start:
            json_str = text[json_start:json_end]
            
            # 3a. 标准JSON解析
            try:
                return json.loads(json_str)
            except json.JSONDecodeError:
                pass
            
            # 3b. 修复常见格式问题后重试
            try:
                fixed = json_str.replace("'", '"')
                fixed = re.sub(r',\s*]', ']', fixed)
                fixed = re.sub(r',\s*}', '}', fixed)
                fixed = re.sub(r'\bTrue\b', 'true', fixed)
                fixed = re.sub(r'\bFalse\b', 'false', fixed)
                return json.loads(fixed)
            except json.JSONDecodeError:
                pass
            
            # 3c. 使用ast.literal_eval
            try:
                return ast.literal_eval(json_str)
            except (ValueError, SyntaxError):
                pass
        
        # 4. 解析失败，返回默认值而非空数组
        logger.warning(f"[ImageAnalyzer] 批次{batch_idx+1}解析失败，使用默认值")
        return [
            {
                "image_index": i, 
                "should_use": True, 
                "category": "未分类", 
                "quality_score": 5, 
                "description": "", 
                "tags": []
            } 
            for i in range(expected_count)
        ]
