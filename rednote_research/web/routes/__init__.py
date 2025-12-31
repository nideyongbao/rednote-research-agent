"""路由模块包 - 将 app.py 拆分为多个子路由"""

from fastapi import APIRouter

# 导入所有子路由
from .research import router as research_router
from .history import router as history_router
from .settings import router as settings_router
from .publish import router as publish_router

__all__ = [
    "research_router",
    "history_router", 
    "settings_router",
    "publish_router"
]
