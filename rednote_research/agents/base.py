"""智能体基类"""

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Callable, Optional
from openai import AsyncOpenAI

if TYPE_CHECKING:
    from ..state import ResearchState


class BaseAgent(ABC):
    """
    所有智能体的基类
    
    定义了智能体的基本结构：
    - 名称和系统提示词
    - LLM调用接口
    - 日志回调
    """
    
    def __init__(
        self, 
        name: str, 
        llm_client: AsyncOpenAI,
        system_prompt: str,
        model: str = "gpt-4o"
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
        temperature: float = 0.7,
        max_tokens: int = 4000
    ) -> str:
        """
        调用LLM并返回响应
        
        Args:
            messages: 消息列表
            temperature: 温度参数
            max_tokens: 最大token数
            
        Returns:
            LLM响应文本
        """
        try:
            response = await self.llm.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens
            )
            
            # 检查响应有效性
            if response is None:
                raise RuntimeError("LLM 返回空响应")
            if not response.choices:
                raise RuntimeError(f"LLM 没有返回 choices: {response}")
            
            content = response.choices[0].message.content
            return content or ""
            
        except Exception as e:
            # 打印详细错误信息便于调试
            import sys
            print(f"[{self.name}] LLM调用失败: {type(e).__name__}: {e}", file=sys.stderr)
            raise
    
    def _log(
        self, 
        state: "ResearchState", 
        message: str,
        on_log: Optional[Callable[[str], None]] = None
    ):
        """记录日志"""
        full_message = f"[{self.name}] {message}"
        state.add_log(full_message)
        if on_log:
            on_log(full_message)
