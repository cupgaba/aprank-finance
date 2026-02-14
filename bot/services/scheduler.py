from datetime import datetime, date
from typing import Optional
import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from aiogram import Bot
import pytz

from ..config import settings
from ..database import Database
from .channel import ChannelService

logger = logging.getLogger(__name__)


class SchedulerService:
    """Service for scheduled tasks"""

    def __init__(self, bot: Bot, db: Database):
        self.bot = bot
        self.db = db
        self.tz = pytz.timezone(settings.TIMEZONE)
        self.scheduler = AsyncIOScheduler(timezone=self.tz)
        self.channel_service = ChannelService(bot, db)
        self._last_sales_reminder_date: Optional[date] = None

    def start(self):
        """Start the scheduler"""
        # Sales reminder check every minute (time is taken from DB settings in app timezone)
        self.scheduler.add_job(
            self._check_sales_reminder_schedule,
            IntervalTrigger(minutes=1),
            id="sales_reminder_check",
            replace_existing=True
        )

        # Pricelist auto-publish check every minute
        self.scheduler.add_job(
            self._check_pricelist_schedule,
            IntervalTrigger(minutes=1),
            id="pricelist_schedule_check",
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

    async def _check_sales_reminder_schedule(self):
        """Check if it's time to send sales reminders using configured app timezone."""
        try:
            bot_settings = await self.db.get_settings()
            if not bot_settings.reminder_enabled:
                return

            now = datetime.now(self.tz)
            current_hour = now.hour
            current_minute = now.minute
            today = now.date()

            reminder_hour = bot_settings.reminder_hour if bot_settings.reminder_hour is not None else settings.SALES_REMINDER_HOUR
            reminder_minute = bot_settings.reminder_minute if bot_settings.reminder_minute is not None else settings.SALES_REMINDER_MINUTE

            if current_hour != reminder_hour or current_minute != reminder_minute:
                return

            if self._last_sales_reminder_date == today:
                return

            logger.info(
                "[SalesReminder] Sending reminders at %02d:%02d timezone=%s",
                current_hour,
                current_minute,
                settings.TIMEZONE,
            )
            await self._send_sales_reminder()
            self._last_sales_reminder_date = today

        except Exception as e:
            logger.exception("Failed to check sales reminder schedule: %s", e)

    async def _send_sales_reminder(self):
        """Send reminder to admins to enter daily sales"""
        try:
            bot_settings = await self.db.get_settings()
            if not bot_settings.reminder_enabled:
                return

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
                    logger.exception("Failed to send reminder to admin_id=%s err=%s", admin.telegram_id, e)

        except Exception as e:
            logger.exception("Failed to send sales reminders: %s", e)

    async def _check_pricelist_schedule(self):
        """Check if it's time to auto-publish pricelist based on DB settings"""
        try:
            bot_settings = await self.db.get_settings()
            if not bot_settings.pricelist_auto_enabled:
                return

            now = datetime.now(self.tz)
            current_hour = now.hour
            current_minute = now.minute

            freq = bot_settings.pricelist_auto_frequency or 1

            time_slots = []
            if bot_settings.pricelist_time1_hour is not None:
                time_slots.append((bot_settings.pricelist_time1_hour, bot_settings.pricelist_time1_minute or 0))
            if freq >= 2 and bot_settings.pricelist_time2_hour is not None:
                time_slots.append((bot_settings.pricelist_time2_hour, bot_settings.pricelist_time2_minute or 0))
            if freq >= 3 and bot_settings.pricelist_time3_hour is not None:
                time_slots.append((bot_settings.pricelist_time3_hour, bot_settings.pricelist_time3_minute or 0))

            logger.info(
                "[AutoPublish] now=%02d:%02d tz=%s freq=%s slots=%s enabled=%s",
                current_hour,
                current_minute,
                settings.TIMEZONE,
                freq,
                time_slots,
                bot_settings.pricelist_auto_enabled,
            )

            for hour, minute in time_slots:
                if current_hour == hour and current_minute == minute:
                    success = await self.channel_service.publish_pricelist(settings=bot_settings)
                    if success:
                        logger.info("[AutoPublish] Pricelist published successfully at %02d:%02d", hour, minute)
                    else:
                        logger.error(
                            "[AutoPublish] Pricelist publish failed at %02d:%02d reason=%s channel_id=%s",
                            hour,
                            minute,
                            self.channel_service.last_error,
                            self.channel_service.channel_id,
                        )
                    break

        except Exception as e:
            logger.exception("Failed to check pricelist schedule: %s", e)

    async def _check_expired_reservations(self):
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
                            logger.exception("Failed to notify admin about expired reservation admin_id=%s err=%s", admin.telegram_id, e)

        except Exception as e:
            logger.exception("Failed to check expired reservations: %s", e)

    async def _notify_expiring_reservations(self):
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
                        logger.exception("Failed to notify admin about expiring reservation admin_id=%s err=%s", admin.telegram_id, e)

        except Exception as e:
            logger.exception("Failed to notify expiring reservations: %s", e)

    async def notify_new_reservation(self, reservation):
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
                    logger.exception("Failed to notify admin about new reservation admin_id=%s err=%s", admin.telegram_id, e)

        except Exception as e:
            logger.exception("Failed to notify new reservation: %s", e)
