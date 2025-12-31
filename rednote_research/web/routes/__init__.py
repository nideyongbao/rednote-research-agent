"""路由模块包 - 将 app.py 拆分为多个子路由

P1 重构：渐进式拆分，research 路由暂保留在 app.py
"""

from fastapi import APIRouter

# 导入已拆分的子路由
from .history import router as history_router
from .settings import router as settings_router
from .publish import router as publish_router

__all__ = [
    "history_router", 
    "settings_router",
    "publish_router"
]

