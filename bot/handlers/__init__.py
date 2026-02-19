from aiogram import Router, F
from aiogram.enums import ChatType

from .common import common_router
from .chat_subscription import chat_subscription_router
from .admin import admin_router
from .user import user_router


def setup_routers() -> Router:
    """Setup all routers"""
    router = Router()


    # Bot should respond only in private chats for common/admin/user routers
    common_router.message.filter(F.chat.type == ChatType.PRIVATE)
    common_router.callback_query.filter(F.message.chat.type == ChatType.PRIVATE)
    admin_router.message.filter(F.chat.type == ChatType.PRIVATE)
    admin_router.callback_query.filter(F.message.chat.type == ChatType.PRIVATE)
    user_router.message.filter(F.chat.type == ChatType.PRIVATE)
    user_router.callback_query.filter(F.message.chat.type == ChatType.PRIVATE)

    # Include routers in order (admin first to check admin status)
    router.include_router(chat_subscription_router)
    router.include_router(common_router)
    router.include_router(admin_router)
    router.include_router(user_router)

    return router
