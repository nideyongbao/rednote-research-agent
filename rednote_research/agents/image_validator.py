"""
VLM 图片验证模块

使用视觉语言模型（如 Qwen-VL）验证图片与内容的相关性
"""

import base64
import httpx
from pathlib import Path
from typing import Optional, Union
from pydantic import BaseModel

from ..services.settings import get_settings_service


class ImageValidationResult(BaseModel):
    """图片验证结果"""
    is_relevant: bool  # 是否相关
    confidence: float  # 置信度 0-1
    reason: str  # 判断理由
    suggested_action: str  # 建议操作: keep, replace, remove


class ImageValidator:
    """
    图片验证器
    
    使用 VLM 模型分析图片与文本内容的相关性
    """
    
    def __init__(self):
        self.settings = get_settings_service().load()
        self.client: Optional[httpx.AsyncClient] = None
        
    async def _get_client(self) -> httpx.AsyncClient:
        """获取 HTTP 客户端"""
        if self.client is None:
            self.client = httpx.AsyncClient(timeout=60.0)
        return self.client
    
    async def close(self):
        """关闭客户端"""
        if self.client:
            await self.client.aclose()
            self.client = None
    
    def _encode_image(self, image_source: Union[str, bytes, Path]) -> str:
        """
        将图片编码为 base64
        
        支持：URL、本地路径、字节数据
        """
        if isinstance(image_source, bytes):
            return base64.b64encode(image_source).decode('utf-8')
        
        if isinstance(image_source, Path) or (isinstance(image_source, str) and not image_source.startswith('http')):
            path = Path(image_source)
            if path.exists():
                return base64.b64encode(path.read_bytes()).decode('utf-8')
            raise FileNotFoundError(f"图片文件不存在: {path}")
        
        # URL 类型直接返回
        return image_source
    
    async def validate(
        self, 
        image_source: Union[str, bytes, Path],
        context: str,
        topic: str = ""
    ) -> ImageValidationResult:
        """
        验证图片与内容的相关性
        
        Args:
            image_source: 图片来源（URL、路径或字节）
            context: 相关文本内容/分论点
            topic: 研究主题（可选）
            
        Returns:
            ImageValidationResult: 验证结果
        """
        vlm_settings = self.settings.vlm
        
        if not vlm_settings.enabled:
            # VLM 未启用，默认通过
            return ImageValidationResult(
                is_relevant=True,
                confidence=1.0,
                reason="VLM 验证未启用",
                suggested_action="keep"
            )
        
        if not vlm_settings.api_key:
            return ImageValidationResult(
                is_relevant=True,
                confidence=0.5,
                reason="VLM API Key 未配置",
                suggested_action="keep"
            )
        
        try:
            # 构建消息
            prompt = self._build_prompt(context, topic)
            
            # 处理图片
            is_url = isinstance(image_source, str) and image_source.startswith('http')
            
            if is_url:
                image_content = {
                    "type": "image_url",
                    "image_url": {"url": image_source}
                }
            else:
                base64_image = self._encode_image(image_source)
                image_content = {
                    "type": "image_url",
                    "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}
                }
            
            messages = [
                {
                    "role": "user",
                    "content": [
                        image_content,
                        {"type": "text", "text": prompt}
                    ]
                }
            ]
            
            # 调用 VLM API
            client = await self._get_client()
            response = await client.post(
                f"{vlm_settings.base_url}/chat/completions",
                headers={
                    "Authorization": f"Bearer {vlm_settings.api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": vlm_settings.model,
                    "messages": messages,
                    "max_tokens": 500
                }
            )
            
            response.raise_for_status()
            result = response.json()
            
            # 解析响应
            return self._parse_response(result)
            
        except Exception as e:
            # 出错时默认保留
            return ImageValidationResult(
                is_relevant=True,
                confidence=0.3,
                reason=f"验证出错: {str(e)[:100]}",
                suggested_action="keep"
            )
    
    def _build_prompt(self, context: str, topic: str) -> str:
        """构建验证提示词"""
        topic_part = f"研究主题：{topic}\n" if topic else ""
        
        return f"""请分析这张图片与以下内容的相关性。

{topic_part}内容：{context}

请从以下几个方面评估：
1. 图片主题与内容是否相关
2. 图片是否能支持或说明文字内容
3. 图片质量是否适合用于research报告

请用JSON格式回复：
{{
  "is_relevant": true/false,
  "confidence": 0.0-1.0,
  "reason": "判断理由",
  "suggested_action": "keep/replace/remove"
}}

规则：
- confidence >= 0.6 且 is_relevant=true 时建议 keep
- confidence < 0.4 或 is_relevant=false 时建议 replace
- 图片严重不相关或质量差时建议 remove"""

    def _parse_response(self, result: dict) -> ImageValidationResult:
        """解析 VLM 响应"""
        import json
        
        try:
            content = result["choices"][0]["message"]["content"]
            
            # 尝试提取 JSON
            if "```json" in content:
                json_str = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                json_str = content.split("```")[1].split("```")[0].strip()
            elif "{" in content and "}" in content:
                start = content.index("{")
                end = content.rindex("}") + 1
                json_str = content[start:end]
            else:
                # 无法解析，默认保留
                return ImageValidationResult(
                    is_relevant=True,
                    confidence=0.5,
                    reason="无法解析 VLM 响应",
                    suggested_action="keep"
                )
            
            data = json.loads(json_str)
            return ImageValidationResult(
                is_relevant=data.get("is_relevant", True),
                confidence=float(data.get("confidence", 0.5)),
                reason=data.get("reason", ""),
                suggested_action=data.get("suggested_action", "keep")
            )
            
        except Exception as e:
            return ImageValidationResult(
                is_relevant=True,
                confidence=0.5,
                reason=f"解析响应出错: {str(e)[:50]}",
                suggested_action="keep"
            )


async def validate_images_batch(
    images: list[dict],
    context: str,
    topic: str = ""
) -> list[dict]:
    """
    批量验证图片
    
    Args:
        images: 图片列表，每项包含 url 和可选的 caption
        context: 相关文本内容
        topic: 研究主题
        
    Returns:
        带验证结果的图片列表
    """
    validator = ImageValidator()
    results = []
    
    try:
        for img in images:
            url = img.get("url", "")
            if not url:
                continue
                
            result = await validator.validate(url, context, topic)
            results.append({
                **img,
                "validation": result.model_dump()
            })
    finally:
        await validator.close()
    
    return results
