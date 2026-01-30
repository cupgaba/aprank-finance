import asyncio
from datetime import datetime, timedelta
from typing import Optional, Callable, Awaitable
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
from aiogram import Bot
import pytz

from ..config import settings
from ..database import Database
from ..database.models import UserRole
from .channel import ChannelService


class SchedulerService:
    """Service for scheduled tasks"""

    def __init__(self, bot: Bot, db: Database):
        self.bot = bot
        self.db = db
        self.scheduler = AsyncIOScheduler(timezone=pytz.timezone(settings.TIMEZONE))
        self.channel_service = ChannelService(bot, db)

    def start(self):
        """Start the scheduler"""
        # Sales reminder at configured time
        self.scheduler.add_job(
            self._send_sales_reminder,
            CronTrigger(
                hour=settings.SALES_REMINDER_HOUR,
                minute=settings.SALES_REMINDER_MINUTE
            ),
            id="sales_reminder",
            replace_existing=True
        )

        # Daily pricelist publication
        self.scheduler.add_job(
            self._publish_daily_pricelist,
            CronTrigger(
                hour=settings.PRICELIST_HOUR,
                minute=settings.PRICELIST_MINUTE
            ),
            id="daily_pricelist",
            replace_existing=True
        )

        # Check expired reservations every hour
        self.scheduler.add_job(
            self._check_expired_reservations,
            IntervalTrigger(hours=1),
            id="check_reservations",
            replace_existing=True
        )

        # Check expiring reservations every 30 minutes
        self.scheduler.add_job(
            self._notify_expiring_reservations,
            IntervalTrigger(minutes=30),
            id="expiring_reservations",
            replace_existing=True
        )

        self.scheduler.start()

    def stop(self):
        """Stop the scheduler"""
        self.scheduler.shutdown()

    async def _send_sales_reminder(self):
        """Send reminder to admins to enter daily sales"""
        try:
            admins = await self.db.get_all_admins()

            message = (
                "🔔 <b>Напоминание</b>\n\n"
                "Введите продажи за сегодня!\n\n"
                "Нажмите /admin → Продажи → Добавить продажу"
            )

            for admin in admins:
                try:
                    await self.bot.send_message(
                        chat_id=admin.telegram_id,
                        text=message,
                        parse_mode="HTML"
                    )
                except Exception as e:
                    print(f"Failed to send reminder to {admin.telegram_id}: {e}")

        except Exception as e:
            print(f"Failed to send sales reminders: {e}")

    async def _publish_daily_pricelist(self):
        """Publish daily pricelist to channel"""
        try:
            await self.channel_service.publish_pricelist()
        except Exception as e:
            print(f"Failed to publish daily pricelist: {e}")

    async def _check_expired_reservations(self):
        """Check and expire old reservations"""
        try:
            expired = await self.db.expire_old_reservations()

            if expired:
                admins = await self.db.get_all_admins()

                for reservation in expired:
                    message = (
                        f"⏰ <b>Резерв истёк</b>\n\n"
                        f"📦 {reservation.product.brand.name} - {reservation.product.name}\n"
                        f"👤 Покупатель: {reservation.user.full_name}\n\n"
                        f"Товар возвращён в наличие."
                    )

                    for admin in admins:
                        try:
                            await self.bot.send_message(
                                chat_id=admin.telegram_id,
                                text=message,
                                parse_mode="HTML"
                            )
                        except Exception as e:
                            print(f"Failed to notify admin: {e}")

        except Exception as e:
            print(f"Failed to check expired reservations: {e}")

    async def _notify_expiring_reservations(self):
        """Notify about reservations expiring soon"""
        try:
            expiring = await self.db.get_expiring_reservations(hours=2)

            if not expiring:
                return

            admins = await self.db.get_all_admins()

            for reservation in expiring:
                time_left = reservation.expires_at - datetime.utcnow()
                minutes_left = int(time_left.total_seconds() / 60)

                message = (
                    f"⚠️ <b>Резерв истекает!</b>\n\n"
                    f"📦 {reservation.product.brand.name} - {reservation.product.name}\n"
                    f"👤 Покупатель: {reservation.user.full_name}\n"
                )
                if reservation.user.phone:
                    message += f"📱 {reservation.user.phone}\n"
                message += f"\n⏰ Осталось: {minutes_left} мин."

                for admin in admins:
                    try:
                        await self.bot.send_message(
                            chat_id=admin.telegram_id,
                            text=message,
                            parse_mode="HTML"
                        )
                    except Exception as e:
                        print(f"Failed to notify admin: {e}")

        except Exception as e:
            print(f"Failed to notify expiring reservations: {e}")

    async def notify_new_reservation(self, reservation):
        """Notify admins about new reservation"""
        try:
            admins = await self.db.get_all_admins()

            message = (
                f"🔔 <b>Новый резерв!</b>\n\n"
                f"📦 {reservation.product.brand.name} - {reservation.product.name}\n"
                f"💰 Цена: {reservation.product.sale_price}₽\n"
                f"📊 Количество: {reservation.quantity} шт.\n\n"
                f"👤 Покупатель: {reservation.user.full_name}\n"
            )
            if reservation.user.username:
                message += f"🆔 @{reservation.user.username}\n"
            if reservation.user.phone:
                message += f"📱 {reservation.user.phone}\n"
            message += f"\n⏰ Истекает: {reservation.expires_at.strftime('%d.%m.%Y %H:%M')}"

            for admin in admins:
                try:
                    await self.bot.send_message(
                        chat_id=admin.telegram_id,
                        text=message,
                        parse_mode="HTML"
                    )
                except Exception as e:
                    print(f"Failed to notify admin: {e}")

        except Exception as e:
            print(f"Failed to notify new reservation: {e}")
