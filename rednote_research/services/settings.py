"""设置服务 - 管理用户配置的持久化"""

import json
from pathlib import Path
from typing import Optional
from pydantic import BaseModel


class LLMSettings(BaseModel):
    """LLM 配置 - Qwen3-235B-A22B-Thinking-2507"""
    api_key: str = "ms-04d662ab-d9b4-46db-a13e-9082887778d3"
    base_url: str = "https://api-inference.modelscope.cn/v1"
    model: str = "Qwen/Qwen3-235B-A22B-Thinking-2507"
    # 推理参数
    temperature: float = 0.6  # Thinking模型推荐值
    top_p: float = 0.95
    top_k: int = 20
    max_tokens: int = 130000  # 长上下文全量处理
    presence_penalty: float = 1.5  # 防止重复循环
    enable_thinking: bool = True  # 启用思维链


class VLMSettings(BaseModel):
    """VLM 配置 - Qwen2.5-VL-32B-Instruct"""
    enabled: bool = False
    api_key: str = "ms-04d662ab-d9b4-46db-a13e-9082887778d3"
    base_url: str = "https://api-inference.modelscope.cn/v1"
    model: str = "Qwen/Qwen2.5-VL-32B-Instruct"
    # 推理参数
    temperature: float = 0.7  # 标准对话推荐；OCR建议0.1
    top_p: float = 0.8  # 略窄采样保证准确性
    max_tokens: int = 8192  # VLM模型限制最大8192
    repetition_penalty: float = 1.1  # 防止词汇卡死
    # 速率限制模式
    rate_limit_mode: bool = True  # True=串行延迟(稳定), False=快速并行


class ImageGenSettings(BaseModel):
    """图片生成配置 - Qwen/Qwen-Image"""
    enabled: bool = False
    api_key: str = "ms-04d662ab-d9b4-46db-a13e-9082887778d3"
    base_url: str = "https://api-inference.modelscope.cn/v1"
    model: str = "Qwen/Qwen-Image"
    # 图片生成参数（蒸馏模型特有）
    num_inference_steps: int = 8  # Turbo甜点区8-9
    guidance_scale: float = 0.0  # 蒸馏模型不需CFG
    width: int = 1024
    height: int = 1024
    sampler_name: str = "Euler"
    # 速率限制模式
    rate_limit_mode: bool = True  # True=串行延迟(稳定), False=快速并行


class SearchSettings(BaseModel):
    """搜索配置"""
    notes_per_keyword: int = 1  # 每个关键词搜索的笔记数量（默认1，可调高）


class Settings(BaseModel):
    """用户配置"""
    llm: LLMSettings = LLMSettings()
    search: SearchSettings = SearchSettings()
    vlm: VLMSettings = VLMSettings()
    imageGen: ImageGenSettings = ImageGenSettings()


class SettingsService:
    """设置服务 - 管理配置的读写"""
    
    def __init__(self, config_path: Optional[Path] = None):
        if config_path is None:
            config_path = Path(__file__).parent / "settings.json"
        self.config_path = config_path
    
    def load(self) -> Settings:
        """加载配置（优先级：环境变量 > 配置文件 > 默认值）"""
        import os
        
        # 1. 基础配置
        settings = Settings()
        
        # 2. 如果文件存在，先加载文件
        if self.config_path.exists():
            try:
                with open(self.config_path, "r", encoding="utf-8") as f:
                    file_data = json.load(f)
                    # 使用 update 逻辑而不是直接覆盖，保留默认结构
                    # 这里简单起见，利用 Pydantic 的自动转换
                    # 注意：如果文件结构不完整，Pydantic 会用默认值补全
                    settings = Settings(**file_data)
            except (json.JSONDecodeError, Exception):
                pass
        
        # 3. 环境变量覆盖 (Docker 部署的核心逻辑)
        # LLM
        if env_key := os.getenv("OPENAI_API_KEY"):
            settings.llm.api_key = env_key
        if env_base := os.getenv("OPENAI_BASE_URL"):
            settings.llm.base_url = env_base
        if env_model := os.getenv("OPENAI_MODEL"):
            settings.llm.model = env_model
            
        # VLM (可选)
        if env_vlm_enable := os.getenv("VLM_ENABLED"):
             settings.vlm.enabled = env_vlm_enable.lower() == "true"
        if env_vlm_key := os.getenv("VLM_API_KEY"):
            settings.vlm.api_key = env_vlm_key
        if env_vlm_base := os.getenv("VLM_BASE_URL"):
            settings.vlm.base_url = env_vlm_base
        if env_vlm_model := os.getenv("VLM_MODEL"):
            settings.vlm.model = env_vlm_model
        
        # ImageGen (可选)
        if env_img_enable := os.getenv("IMAGE_GEN_ENABLED"):
             settings.imageGen.enabled = env_img_enable.lower() == "true"
        if env_img_key := os.getenv("IMAGE_GEN_API_KEY"):
            settings.imageGen.api_key = env_img_key
        if env_img_base := os.getenv("IMAGE_GEN_BASE_URL"):
            settings.imageGen.base_url = env_img_base
        if env_img_model := os.getenv("IMAGE_GEN_MODEL"):
            settings.imageGen.model = env_img_model
            
        # Search Config
        if env_notes_limit := os.getenv("SEARCH_NOTES_PER_KEYWORD"):
            try:
                settings.search.notes_per_keyword = int(env_notes_limit)
            except ValueError:
                pass
             
        return settings
    
    def save(self, settings: Settings) -> None:
        """保存配置"""
        with open(self.config_path, "w", encoding="utf-8") as f:
            json.dump(settings.model_dump(), f, ensure_ascii=False, indent=2)
    
    def get_masked(self) -> dict:
        """获取脱敏的配置（隐藏 API Key，使用 camelCase 字段名）"""
        settings = self.load()
        
        def mask_key(key: str) -> str:
            if not key:
                return ""
            return key[:8] + "..." if len(key) > 8 else "***"
        
        return {
            "llm": {
                "apiKey": mask_key(settings.llm.api_key),
                "baseUrl": settings.llm.base_url,
                "model": settings.llm.model
            },
            "vlm": {
                "enabled": settings.vlm.enabled,
                "apiKey": mask_key(settings.vlm.api_key),
                "baseUrl": settings.vlm.base_url,
                "model": settings.vlm.model,
                "rateLimitMode": settings.vlm.rate_limit_mode
            },
            "imageGen": {
                "enabled": settings.imageGen.enabled,
                "apiKey": mask_key(settings.imageGen.api_key),
                "baseUrl": settings.imageGen.base_url,
                "model": settings.imageGen.model,
                "rateLimitMode": settings.imageGen.rate_limit_mode
            },
            "search": {
                "notesPerKeyword": settings.search.notes_per_keyword
            }
        }


# 全局单例
_settings_service: Optional[SettingsService] = None


def get_settings_service() -> SettingsService:
    """获取设置服务单例"""
    global _settings_service
    if _settings_service is None:
        _settings_service = SettingsService()
    return _settings_service
