from typing import Optional
from datetime import datetime
from aiogram import Bot
import pytz

from ..config import settings
from ..database.models import User, Product, Sale, WriteOff, Reservation, Supply

_tz = pytz.timezone(settings.TIMEZONE)


def _now_str() -> str:
    return datetime.now(_tz).strftime('%d.%m.%Y %H:%M')


class LoggerService:
    """Service for logging changes to a Telegram channel"""

    def __init__(self, bot: Bot, db=None):
        self.bot = bot
        self.db = db
        self.log_channel_id = settings.LOG_CHANNEL_ID

    async def _send_log(self, message: str, log_type: Optional[str] = None):
        """Send log message to log channel"""
        if not self.log_channel_id:
            return

        # Check if this log type is enabled in settings
        if self.db and log_type:
            try:
                bot_settings = await self.db.get_settings()
                flag = getattr(bot_settings, log_type, True)
                if not flag:
                    return
            except Exception:
                pass

        try:
            await self.bot.send_message(
                chat_id=self.log_channel_id,
                text=message,
                parse_mode="HTML"
            )
        except Exception as e:
            print(f"Failed to send log: {e}")

    async def log_product_created(self, product: Product, admin: User):
        """Log product creation"""
        message = (
            f"➕ <b>Добавлен товар</b>\n\n"
            f"📦 {product.brand.name} - {product.name}\n"
            f"💵 Закупка: {product.purchase_price}₽\n"
            f"💰 Продажа: {product.sale_price}₽\n"
            f"📊 Количество: {product.quantity} шт.\n\n"
            f"👤 Админ: {admin.full_name}\n"
            f"🕐 {_now_str()}"
        )
        await self._send_log(message, "log_products")

    async def log_product_updated(
        self,
        product: Product,
        admin: User,
        field: str,
        old_value,
        new_value
    ):
        """Log product update"""
        field_names = {
            "sale_price": "Цена продажи",
            "purchase_price": "Цена закупки",
            "quantity": "Количество",
            "name": "Название",
        }
        field_name = field_names.get(field, field)

        message = (
            f"✏️ <b>Изменён товар</b>\n\n"
            f"📦 {product.brand.name} - {product.name}\n"
            f"📝 {field_name}: {old_value} → {new_value}\n\n"
            f"👤 Админ: {admin.full_name}\n"
            f"🕐 {_now_str()}"
        )
        await self._send_log(message, "log_products")

    async def log_product_deleted(self, product: Product, admin: User):
        """Log product deletion"""
        message = (
            f"🗑 <b>Удалён товар</b>\n\n"
            f"📦 {product.brand.name} - {product.name}\n\n"
            f"👤 Админ: {admin.full_name}\n"
            f"🕐 {_now_str()}"
        )
        await self._send_log(message, "log_products")

    async def log_sale(self, sale: Sale, admin: Optional[User] = None):
        """Log sale"""
        product = sale.product
        message = (
            f"💰 <b>Продажа</b>\n\n"
            f"📦 {product.brand.name} - {product.name}\n"
            f"📊 Количество: {sale.quantity} шт.\n"
            f"💵 Цена: {sale.sale_price}₽\n"
            f"📈 Прибыль: {sale.profit}₽\n\n"
        )
        if admin:
            message += f"👤 Админ: {admin.full_name}\n"
        message += f"🕐 {_now_str()}"
        await self._send_log(message, "log_sales")

    async def log_supply(self, supply: Supply, admin: Optional[User] = None):
        """Log supply"""
        items_text = "\n".join([
            f"• {item.product.name} x{item.quantity} по {item.purchase_price}₽"
            for item in supply.items
        ])

        message = (
            f"📥 <b>Закупка</b>\n\n"
            f"{items_text}\n\n"
            f"💰 Итого: {supply.total_amount}₽\n"
        )
        if supply.supplier_name:
            message += f"🏪 Поставщик: {supply.supplier_name}\n"
        if admin:
            message += f"\n👤 Админ: {admin.full_name}\n"
        message += f"🕐 {_now_str()}"
        await self._send_log(message, "log_supplies")

    async def log_writeoff(self, writeoff: WriteOff, admin: Optional[User] = None):
        """Log write-off"""
        product = writeoff.product
        reasons = {
            "defect": "Брак",
            "damage": "Бракираж",
            "loss": "Потеря",
            "other": "Другое",
        }
        reason_text = reasons.get(writeoff.reason.value, writeoff.reason.value)

        message = (
            f"📤 <b>Списание</b>\n\n"
            f"📦 {product.brand.name} - {product.name}\n"
            f"📊 Количество: {writeoff.quantity} шт.\n"
            f"❗️ Причина: {reason_text}\n"
        )
        if writeoff.notes:
            message += f"📝 Заметки: {writeoff.notes}\n"
        if admin:
            message += f"\n👤 Админ: {admin.full_name}\n"
        message += f"🕐 {_now_str()}"
        await self._send_log(message, "log_writeoffs")

    async def log_reservation_created(self, reservation: Reservation):
        """Log reservation creation"""
        product = reservation.product
        user = reservation.user

        message = (
            f"🔔 <b>Новый резерв</b>\n\n"
            f"📦 {product.brand.name} - {product.name}\n"
            f"📊 Количество: {reservation.quantity} шт.\n"
            f"⏰ До: {reservation.expires_at.strftime('%d.%m.%Y %H:%M')}\n\n"
            f"👤 Покупатель: {user.full_name}\n"
        )
        if user.username:
            message += f"🆔 @{user.username}\n"
        if user.phone:
            message += f"📱 {user.phone}\n"
        message += f"\n🕐 {datetime.now().strftime('%d.%m.%Y %H:%M')}"
        await self._send_log(message, "log_reservations")

    async def log_reservation_completed(self, reservation: Reservation, admin: User):
        """Log reservation completion"""
        product = reservation.product

        message = (
            f"✅ <b>Резерв завершён</b>\n\n"
            f"📦 {product.brand.name} - {product.name}\n"
            f"👤 Покупатель: {reservation.user.full_name}\n\n"
            f"👤 Админ: {admin.full_name}\n"
            f"🕐 {_now_str()}"
        )
        await self._send_log(message, "log_reservations")

    async def log_reservation_cancelled(self, reservation: Reservation, admin: Optional[User] = None):
        """Log reservation cancellation"""
        product = reservation.product

        message = (
            f"❌ <b>Резерв отменён</b>\n\n"
            f"📦 {product.brand.name} - {product.name}\n"
            f"👤 Покупатель: {reservation.user.full_name}\n"
        )
        if admin:
            message += f"\n👤 Админ: {admin.full_name}\n"
        message += f"🕐 {_now_str()}"
        await self._send_log(message, "log_reservations")

    async def log_admin_added(self, new_admin: User, by_admin: User):
        """Log admin addition"""
        message = (
            f"👑 <b>Добавлен админ</b>\n\n"
            f"👤 {new_admin.full_name}\n"
        )
        if new_admin.username:
            message += f"🆔 @{new_admin.username}\n"
        message += (
            f"\n👤 Добавил: {by_admin.full_name}\n"
            f"🕐 {_now_str()}"
        )
        await self._send_log(message)
