from aiogram import Router

from .common import common_router
from .admin import admin_router
from .user import user_router


def setup_routers() -> Router:
    """Setup all routers"""
    router = Router()

    # Include routers in order (admin first to check admin status)
    router.include_router(common_router)
    router.include_router(admin_router)
    router.include_router(user_router)

    return router
