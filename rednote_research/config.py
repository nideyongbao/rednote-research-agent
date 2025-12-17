"""配置管理模块"""

import os
from pathlib import Path

# 自动加载 .env 文件（从项目根目录）
try:
    from dotenv import load_dotenv
    # 查找本文件所在目录的 .env 文件
    env_path = Path(__file__).parent / ".env"
    load_dotenv(env_path)
except ImportError:
    pass  # python-dotenv 未安装时跳过
from typing import Optional
import yaml
from pydantic import BaseModel
from openai import AsyncOpenAI


class MCPConfig(BaseModel):
    """MCP服务器配置"""
    command: str = "node"
    args: list[str] = []
    env: dict[str, str] = {}


class LLMConfig(BaseModel):
    """LLM配置"""
    provider: str = "openai"
    api_key: Optional[str] = None
    base_url: Optional[str] = None
    model: str = "gpt-4o"


class Config(BaseModel):
    """全局配置"""
    llm: LLMConfig = LLMConfig()
    mcp: dict[str, MCPConfig] = {}
    output_dir: Path = Path("./reports")
    
    @classmethod
    def from_yaml(cls, path: str) -> "Config":
        """从YAML文件加载配置"""
        with open(path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        
        # 从环境变量填充API Key
        if data.get("llm", {}).get("api_key") == "${OPENAI_API_KEY}":
            data["llm"]["api_key"] = os.getenv("OPENAI_API_KEY")
        
        return cls(**data)
    
    @classmethod
    def from_env(cls) -> "Config":
        """从环境变量加载配置"""
        return cls(
            llm=LLMConfig(
                api_key=os.getenv("OPENAI_API_KEY"),
                base_url=os.getenv("OPENAI_BASE_URL"),
                model=os.getenv("OPENAI_MODEL", "gpt-4o"),
            ),
            mcp={
                "rednote": MCPConfig(
                    command="node",
                    args=[os.getenv("REDNOTE_MCP_PATH", "")],
                )
            }
        )
    
    def get_llm_client(self) -> AsyncOpenAI:
        """获取异步OpenAI客户端"""
        return AsyncOpenAI(
            api_key=self.llm.api_key,
            base_url=self.llm.base_url,
        )
