from typing import Callable, Dict, Any, Awaitable
from aiogram import BaseMiddleware
from aiogram.types import TelegramObject

from ..database import get_db, Database


class DatabaseMiddleware(BaseMiddleware):
    """Middleware that injects database instance into handler data"""

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any]
    ) -> Any:
        db = await get_db()
        data["db"] = db
        return await handler(event, data)
