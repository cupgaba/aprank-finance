from typing import Callable, Dict, Any, Awaitable
from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, Message, CallbackQuery

from ..database import Database


class UserMiddleware(BaseMiddleware):
    """Middleware that creates/updates user in database"""

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any]
    ) -> Any:
        db: Database = data.get("db")
        if not db:
            return await handler(event, data)

        # Get user info from event
        user = None
        if isinstance(event, Message) and event.from_user:
            user = event.from_user
        elif isinstance(event, CallbackQuery) and event.from_user:
            user = event.from_user

        if user:
            db_user = await db.get_or_create_user(
                telegram_id=user.id,
                username=user.username,
                first_name=user.first_name,
                last_name=user.last_name
            )
            data["user"] = db_user

            # Block banned users (except admins)
            if not db_user.is_active and not db_user.is_admin:
                if isinstance(event, Message):
                    await event.answer("🚫 Вы заблокированы.")
                elif isinstance(event, CallbackQuery):
                    await event.answer("🚫 Вы заблокированы.", show_alert=True)
                return

        return await handler(event, data)
