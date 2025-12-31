"""图片生成服务 - 调用图片生成模型生成封面图和章节配图

支持小红书风格的图片生成：
- 封面图：吸睛、竖版3:4、鲜艳色彩
- 章节图：与内容对应、风格统一
"""

import os
import asyncio
import httpx
import base64
from pathlib import Path
from datetime import datetime
from typing import Optional
from openai import AsyncOpenAI


class ImageGenerator:
    """图片生成器"""
    
    def __init__(self):
        """初始化图片生成器，从设置服务获取配置"""
        from .settings import get_settings_service
        
        settings = get_settings_service().load()
        self.enabled = settings.imageGen.enabled
        self.api_key = settings.imageGen.api_key
        self.base_url = settings.imageGen.base_url
        self.model = settings.imageGen.model
        self.rate_limit_mode = settings.imageGen.rate_limit_mode
        
        # 内置 OpenAI 客户端（用于非万相模型）
        self._openai_client: Optional[AsyncOpenAI] = None
    
    def is_available(self) -> bool:
        """检查图片生成服务是否可用"""
        return self.enabled and bool(self.api_key)
    
    # ===== 封面图生成 =====
    
    async def generate_cover(
        self,
        topic: str,
        key_findings: list[str],
        output_dir: str,
        on_log: callable = None
    ) -> Optional[str]:
        """
        生成封面图
        
        Args:
            topic: 研究主题
            key_findings: 关键发现列表
            output_dir: 输出目录
            on_log: 日志回调函数
            
        Returns:
            生成的图片路径，失败返回 None
        """
        if not self.is_available():
            if on_log:
                on_log("⚠️ 图片生成服务未配置")
            return None
        
        prompt = self.build_cover_prompt(topic, key_findings)
        
        if on_log:
            on_log(f"🎨 生成封面图: {topic[:20]}...")
        
        try:
            image_path = await self._generate_image(
                prompt=prompt,
                output_path=os.path.join(output_dir, "cover.png"),
                size="1024x1536"  # 接近 3:4 竖版
            )
            
            if image_path and on_log:
                on_log(f"✅ 封面图生成成功")
            
            return image_path
            
        except Exception as e:
            if on_log:
                on_log(f"❌ 封面图生成失败: {str(e)[:50]}")
            return None
    
    def build_cover_prompt(self, topic: str, key_findings: list[str]) -> str:
        """
        构建封面图 Prompt（小红书风格）
        
        小红书封面图特点：
        - 色彩鲜艳、饱和度高、视觉冲击力强
        - 竖版 3:4 比例
        - 简洁大方、主体突出
        - 年轻化、精致感
        """
        findings_text = "\n".join(f"- {f}" for f in key_findings[:3]) if key_findings else ""
        
        return f"""创建一张吸引眼球的小红书风格封面图。

【主题】{topic}

【小红书封面图风格要求】
- 色彩：鲜艳明亮、高饱和度、吸引眼球
- 构图：主体居中或三分法构图，简洁大方
- 风格：精致、时尚、年轻化、有质感
- 氛围：温馨、治愈或活力四射
- 画面干净，留有适合添加文字的空间

【核心卖点】
{findings_text}

【技术要求】
- 竖版构图（适配手机屏幕）
- 高清画质、无噪点
- 摄影级真实感或精美插画风格
- 无文字水印

请生成一张能在小红书信息流中脱颖而出的封面图。"""
    
    # ===== 章节内容图生成 =====
    
    async def generate_section_images(
        self,
        sections: list[dict],
        topic: str,
        output_dir: str,
        max_images: int = 5,
        on_log: callable = None
    ) -> list[str]:
        """
        为每个重要章节生成配图
        
        Args:
            sections: 报告章节列表 [{title, content, ...}]
            topic: 主题
            output_dir: 输出目录
            max_images: 最大生成数量
            on_log: 日志回调
            
        Returns:
            生成的图片路径列表
        """
        if not self.is_available():
            if on_log:
                on_log("⚠️ 图片生成服务未配置")
            return []
        
        generated_images = []
        
        # 筛选需要生成图片的章节（跳过封面和总结类型）
        content_sections = [
            s for s in sections 
            if s.get("type") == "content" or s.get("content")
        ][:max_images]
        
        for i, section in enumerate(content_sections):
            if on_log:
                on_log(f"🎨 生成章节图 ({i+1}/{len(content_sections)}): {section.get('title', '')[:15]}...")
            
            try:
                prompt = self.build_section_prompt(
                    section_title=section.get("title", ""),
                    section_content=section.get("content", "")[:200],
                    topic=topic
                )
                
                image_path = await self._generate_image(
                    prompt=prompt,
                    output_path=os.path.join(output_dir, f"section_{i+1}.png"),
                    size="1024x1536"
                )
                
                if image_path:
                    generated_images.append(image_path)
                    if on_log:
                        on_log(f"✅ 章节图 {i+1} 生成成功")
                
                # 限流模式下等待
                if self.rate_limit_mode and i < len(content_sections) - 1:
                    await asyncio.sleep(2)
                    
            except Exception as e:
                if on_log:
                    on_log(f"⚠️ 章节图 {i+1} 生成失败: {str(e)[:30]}")
                continue
        
        return generated_images
    
    def build_section_prompt(
        self, 
        section_title: str,
        section_content: str,
        topic: str
    ) -> str:
        """
        构建章节配图 Prompt
        
        特点：
        - 图文对应，直观展示内容
        - 小红书风格
        - 保持风格统一
        """
        return f"""创建一张小红书风格的内容配图。

【主题背景】{topic}

【章节标题】{section_title}

【章节内容摘要】
{section_content[:150]}

【图片风格要求】
- 与内容高度相关，直观展示核心信息
- 小红书风格：精致、时尚、有质感
- 色彩明亮、画面干净
- 竖版构图
- 摄影级真实感或精美插画

请生成一张能准确传达章节内容的配图。"""
    
    # ===== 内部方法 =====
    
    async def _generate_image(
        self,
        prompt: str,
        output_path: Optional[str] = None,
        size: str = "1024x1536"
    ) -> Optional[str]:
        """
        调用图片生成模型生成图片
        
        支持模型：
        - 通义万相（wanx）
        - DALL-E 系列
        - 其他 OpenAI 兼容接口
        
        Args:
            prompt: 提示词
            output_path: 保存路径。如果为None，则返回图片URL
            size: 图片尺寸
        """
        # 如果指定了路径，确保目录存在
        if output_path:
            Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        
        # 根据 Base URL 判断是否使用 ModelScope 接口
        if "modelscope.cn" in self.base_url:
            return await self._generate_with_modelscope(prompt, output_path, size)
        else:
            return await self._generate_with_openai(prompt, output_path, size)
    
    async def _generate_with_modelscope(
        self,
        prompt: str,
        output_path: str,
        size: str
    ) -> Optional[str]:
        """使用 ModelScope 异步 API 生成图片"""
        async with httpx.AsyncClient(timeout=120.0) as client:
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
                "X-ModelScope-Async-Mode": "true"
            }
            
            # 1. 提交任务
            # 处理 base_url，避免重复 /v1
            base_url = self.base_url.rstrip('/')
            if base_url.endswith('/v1'):
                base_url = base_url[:-3]
            
            generate_url = f"{base_url}/v1/images/generations"
            
            response = await client.post(
                generate_url,
                headers=headers,
                json={
                    "model": self.model,
                    "prompt": prompt,
                    "n": 1,
                    "size": size
                    # 注意：如果需要 params 如 loras，需在此处扩展
                }
            )
            
            if response.status_code != 200:
                raise Exception(f"创建任务失败: {response.text[:200]}")
            
            data = response.json()
            task_id = data.get("task_id")
            
            if not task_id:
                raise Exception(f"未获取到任务ID: {data}")
            
            print(f"[ModelScope] Task submitted: {task_id}")
            
            # 2. 轮询任务状态
            task_url = f"{base_url}/v1/tasks/{task_id}"
            poll_headers = {
                "Authorization": f"Bearer {self.api_key}",
                "X-ModelScope-Task-Type": "image_generation"
            }
            
            for _ in range(60):  # 最多等待 5 分钟
                await asyncio.sleep(5)
                
                status_response = await client.get(task_url, headers=poll_headers)
                
                if status_response.status_code != 200:
                    print(f"[ModelScope] Check status failed: {status_response.status_code}")
                    continue
                    
                status_data = status_response.json()
                task_status = status_data.get("task_status")
                
                print(f"[Debug] Task {task_id} status: {task_status}")
                
                if task_status in ["SUCCEEDED", "SUCCEED"]:
                    output_images = status_data.get("output_images", [])
                    if output_images:
                        image_url = output_images[0]
                        if image_url:
                            # 1. 如果不需要保存文件，直接返回 URL
                            if output_path is None:
                                return image_url
                            
                            # 2. 如果需要保存文件，下载并返回路径
                            print(f"[ModelScope] Downloading image to {output_path}")
                            img_response = await client.get(image_url)
                            with open(output_path, "wb") as f:
                                f.write(img_response.content)
                            return output_path
                    raise Exception("未获取到图片URL")
                    
                elif task_status == "FAILED":
                    raise Exception(f"图片生成任务失败: {status_data}")
            
            raise Exception(f"任务超时 (5分钟). 最后状态: {task_status}")
    
    async def _generate_with_openai(
        self,
        prompt: str,
        output_path: str,
        size: str
    ) -> Optional[str]:
        """使用 OpenAI 兼容接口生成图片"""
        if self._openai_client is None:
            self._openai_client = AsyncOpenAI(
                api_key=self.api_key,
                base_url=self.base_url
            )
        
        # 如果不需要保存文件，使用 url 格式，否则使用 b64_json 以便保存
        resp_format = "b64_json" if output_path else "url"
        
        response = await self._openai_client.images.generate(
            model=self.model,
            prompt=prompt,
            n=1,
            size=size,
            response_format=resp_format
        )
        
        if response.data:
            # 如果配置了 path，下载/保存
            if output_path:
                if response.data[0].b64_json:
                    image_data = base64.b64decode(response.data[0].b64_json)
                    with open(output_path, "wb") as f:
                        f.write(image_data)
                    return output_path
                elif response.data[0].url:
                     # 下载 URL
                    import httpx
                    async with httpx.AsyncClient() as client:
                        r = await client.get(response.data[0].url)
                        with open(output_path, "wb") as f:
                            f.write(r.content)
                    return output_path
            
            # 否则返回 URL (或者 b64?) 
            # DALL-E 默认可能只返回 URL 如果不请求 b64_json
            # 但我们在上面请求了 response_format="b64_json"
            # 如果 output_path is None，我们最好返回 URL。所以应该修改 parameter
            if response.data[0].url:
                return response.data[0].url
            
            # 如果只有 b64，无法返回 URL，只能由调用者处理 b64？
            # 简单起见，如果 output_path is None，我们假设调用者想要 URL。
            # 这里如果只有 b64，我们暂时无法提供 URL。
            # 为了兼容性，如果没有 path，我们返回 None 或者以此情况抛出异常
            # 但 ImageAssigner 原来用的就是 .url，所以我们最好请求 standard response format if path is None
            
        return None


# 全局实例
_image_generator: Optional[ImageGenerator] = None


def get_image_generator() -> ImageGenerator:
    """获取图片生成器实例"""
    global _image_generator
    if _image_generator is None:
        _image_generator = ImageGenerator()
    return _image_generator
