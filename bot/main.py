import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from .config import settings
from .database import get_db
from .handlers import setup_routers
from .middlewares import DatabaseMiddleware, UserMiddleware, AdminMiddleware
from .services.scheduler import SchedulerService

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


async def main():
    # Initialize bot
    bot = Bot(
        token=settings.BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )

    # Initialize dispatcher with memory storage for FSM
    storage = MemoryStorage()
    dp = Dispatcher(storage=storage)

    # Initialize database
    db = await get_db()
    logger.info("Database initialized")

    # Setup middlewares (order matters!)
    dp.message.middleware(DatabaseMiddleware())
    dp.message.middleware(UserMiddleware())
    dp.message.middleware(AdminMiddleware())

    dp.callback_query.middleware(DatabaseMiddleware())
    dp.callback_query.middleware(UserMiddleware())
    dp.callback_query.middleware(AdminMiddleware())

    # Setup routers
    router = setup_routers()
    dp.include_router(router)
    logger.info("Routers configured")

    # Initialize scheduler
    scheduler = SchedulerService(bot, db)
    scheduler.start()
    logger.info("Scheduler started")

    # Start polling
    logger.info("Starting bot...")
    try:
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
    finally:
        scheduler.stop()
        await bot.session.close()


def run():
    """Entry point for the bot"""
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot stopped")


if __name__ == "__main__":
    run()
