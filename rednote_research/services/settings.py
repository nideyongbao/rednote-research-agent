"""设置服务 - 管理用户配置的持久化"""

import json
from pathlib import Path
from typing import Optional
from pydantic import BaseModel


class LLMSettings(BaseModel):
    """LLM 配置"""
    api_key: str = ""
    base_url: str = "https://api-inference.modelscope.cn/v1"
    model: str = "gpt-4o"


class VLMSettings(BaseModel):
    """VLM 配置（图片验证）"""
    enabled: bool = False
    api_key: str = ""
    base_url: str = "https://api-inference.modelscope.cn/v1"
    model: str = "qwen-vl-plus"


class ImageGenSettings(BaseModel):
    """图片生成配置"""
    enabled: bool = False
    api_key: str = ""
    base_url: str = "https://api-inference.modelscope.cn/v1"
    model: str = "wanx-v1"


class Settings(BaseModel):
    """用户配置"""
    llm: LLMSettings = LLMSettings()
    vlm: VLMSettings = VLMSettings()
    imageGen: ImageGenSettings = ImageGenSettings()


class SettingsService:
    """设置服务 - 管理配置的读写"""
    
    def __init__(self, config_path: Optional[Path] = None):
        if config_path is None:
            config_path = Path(__file__).parent / "settings.json"
        self.config_path = config_path
    
    def load(self) -> Settings:
        """加载配置"""
        if self.config_path.exists():
            try:
                with open(self.config_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                return Settings(**data)
            except (json.JSONDecodeError, Exception):
                pass
        return Settings()
    
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
                "model": settings.vlm.model
            },
            "imageGen": {
                "enabled": settings.imageGen.enabled,
                "apiKey": mask_key(settings.imageGen.api_key),
                "baseUrl": settings.imageGen.base_url,
                "model": settings.imageGen.model
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
