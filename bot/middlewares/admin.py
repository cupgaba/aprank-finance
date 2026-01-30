from typing import Callable, Dict, Any, Awaitable
from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, Message, CallbackQuery

from ..database import Database
from ..database.models import User, UserRole
from ..config import settings


class AdminMiddleware(BaseMiddleware):
    """Middleware that checks if user is admin and sets is_admin flag"""

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any]
    ) -> Any:
        db_user: User = data.get("user")

        is_admin = False

        if db_user:
            # Check if user is admin in database
            if db_user.role in (UserRole.ADMIN, UserRole.OWNER):
                is_admin = True
            # Also check if user is in ADMIN_IDS from config
            elif db_user.telegram_id in settings.ADMIN_IDS:
                # Update user role in database
                db: Database = data.get("db")
                if db:
                    await db.set_user_role(db_user.telegram_id, UserRole.ADMIN)
                is_admin = True

        data["is_admin"] = is_admin

        return await handler(event, data)
