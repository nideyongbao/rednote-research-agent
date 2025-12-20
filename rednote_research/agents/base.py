"""智能体基类"""

import asyncio
import logging
from abc import ABC, abstractmethod
from datetime import datetime
from typing import TYPE_CHECKING, Callable, Optional
from openai import AsyncOpenAI

if TYPE_CHECKING:
    from ..state import ResearchState

# 配置日志
logger = logging.getLogger(__name__)


class BaseAgent(ABC):
    """
    所有智能体的基类
    
    定义了智能体的基本结构：
    - 名称和系统提示词
    - LLM调用接口（带重试机制）
    - 日志回调
    """
    
    # 重试配置
    MAX_RETRIES = 3
    INITIAL_RETRY_DELAY = 1.0  # 初始延迟（秒）
    MAX_RETRY_DELAY = 10.0  # 最大延迟（秒）
    
    def __init__(
        self, 
        name: str, 
        llm_client: AsyncOpenAI,
        system_prompt: str,
        model: str
    ):
        """
        初始化智能体
        
        Args:
            name: 智能体名称
            llm_client: OpenAI客户端
            system_prompt: 系统提示词
            model: 使用的模型
        """
        self.name = name
        self.llm = llm_client
        self.system_prompt = system_prompt
        self.model = model
    
    @abstractmethod
    async def run(
        self, 
        state: "ResearchState",
        on_log: Optional[Callable[[str], None]] = None
    ) -> "ResearchState":
        """
        执行智能体逻辑
        
        Args:
            state: 共享状态对象
            on_log: 日志回调函数
            
        Returns:
            更新后的状态对象
        """
        pass
    
    async def _invoke_llm(
        self, 
        messages: list[dict],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        top_p: Optional[float] = None,
        presence_penalty: Optional[float] = None
    ) -> str:
        """
        调用LLM并返回响应（带重试机制）
        
        Args:
            messages: 消息列表
            temperature: 温度参数（None则使用settings默认值）
            max_tokens: 最大token数（None则使用settings默认值）
            top_p: top_p采样参数
            presence_penalty: 存在惩罚参数
            
        Returns:
            LLM响应文本
        """
        # 从settings获取默认参数
        from ..services.settings import get_settings_service
        settings = get_settings_service().load()
        
        # 使用settings中的默认值
        temperature = temperature if temperature is not None else settings.llm.temperature
        max_tokens = max_tokens if max_tokens is not None else settings.llm.max_tokens
        top_p = top_p if top_p is not None else settings.llm.top_p
        presence_penalty = presence_penalty if presence_penalty is not None else settings.llm.presence_penalty
        
        last_exception = None
        
        for attempt in range(self.MAX_RETRIES):
            try:
                start_time = datetime.now()
                
                # 构建请求参数
                request_params = {
                    "model": self.model,
                    "messages": messages,
                    "temperature": temperature,
                    "max_tokens": max_tokens,
                    "top_p": top_p,
                }
                
                # 添加可选参数
                if presence_penalty is not None:
                    request_params["presence_penalty"] = presence_penalty
                
                # 日志：请求开始
                logger.info(
                    f"[{self.name}] LLM请求开始 | 尝试 {attempt + 1}/{self.MAX_RETRIES} | "
                    f"模型: {self.model} | temperature: {temperature} | max_tokens: {max_tokens}"
                )
                
                response = await self.llm.chat.completions.create(**request_params)
                
                # 计算耗时
                elapsed = (datetime.now() - start_time).total_seconds()
                
                # 检查响应有效性
                if response is None:
                    raise RuntimeError("LLM 返回空响应")
                if not response.choices:
                    raise RuntimeError(f"LLM 没有返回 choices: {response}")
                
                content = response.choices[0].message.content or ""
                
                # 日志：请求成功
                usage = response.usage
                logger.info(
                    f"[{self.name}] LLM请求成功 | 耗时: {elapsed:.2f}s | "
                    f"输入tokens: {usage.prompt_tokens if usage else 'N/A'} | "
                    f"输出tokens: {usage.completion_tokens if usage else 'N/A'} | "
                    f"响应长度: {len(content)}字符"
                )
                
                return content
                
            except Exception as e:
                last_exception = e
                
                # 计算退避延迟（指数退避）
                delay = min(
                    self.INITIAL_RETRY_DELAY * (2 ** attempt),
                    self.MAX_RETRY_DELAY
                )
                
                # 日志：请求失败
                logger.warning(
                    f"[{self.name}] LLM请求失败 | 尝试 {attempt + 1}/{self.MAX_RETRIES} | "
                    f"错误: {type(e).__name__}: {str(e)[:100]} | "
                    f"{'将在 %.1fs 后重试' % delay if attempt < self.MAX_RETRIES - 1 else '已达最大重试次数'}"
                )
                
                if attempt < self.MAX_RETRIES - 1:
                    await asyncio.sleep(delay)
        
        # 所有重试都失败
        logger.error(
            f"[{self.name}] LLM请求最终失败 | 已重试 {self.MAX_RETRIES} 次 | "
            f"最后错误: {type(last_exception).__name__}: {last_exception}"
        )
        raise last_exception
    
    def _log(
        self, 
        state: "ResearchState", 
        message: str,
        on_log: Optional[Callable[[str], None]] = None,
        level: str = "info"
    ):
        """
        记录日志
        
        Args:
            state: 研究状态
            message: 日志消息
            on_log: 日志回调
            level: 日志级别 (info/warning/error)
        """
        full_message = f"[{self.name}] {message}"
        state.add_log(full_message)
        
        # 输出到标准日志
        log_func = getattr(logger, level, logger.info)
        log_func(full_message)
        
        if on_log:
            on_log(full_message)
