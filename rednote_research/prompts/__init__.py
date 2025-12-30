"""
Prompt 统一管理模块

将所有智能体和生成器使用的 prompts 集中管理，便于维护和版本控制。

使用方法:
    from rednote_research.prompts import PLANNER_PROMPT, ANALYZER_PROMPT
    # 或
    from rednote_research.prompts.planner import PLANNER_PROMPT
"""

from .planner import PLANNER_PROMPT
from .searcher import SEARCHER_PROMPT
from .analyzer import ANALYZER_PROMPT
from .outline_generator import OUTLINE_GENERATOR_PROMPT
from .section_writer import SECTION_WRITER_PROMPT
from .image_analyzer import IMAGE_ANALYZER_PROMPT

__all__ = [
    "PLANNER_PROMPT",
    "SEARCHER_PROMPT", 
    "ANALYZER_PROMPT",
    "OUTLINE_GENERATOR_PROMPT",
    "SECTION_WRITER_PROMPT",
    "IMAGE_ANALYZER_PROMPT",
]
