from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext

from ...database import Database
from ...keyboards.admin import AdminKeyboards
from ...states.admin import AdminStates

settings_router = Router()


# ==================== SETTINGS MENU ====================


@settings_router.callback_query(F.data == "admin:settings_menu")
async def settings_menu_callback(callback: CallbackQuery, state: FSMContext, is_admin: bool = False):
    """Return to settings menu"""
    if not is_admin:
        await callback.answer("⛔️ Нет доступа", show_alert=True)
        return

    await state.clear()
    await callback.message.edit_text(
        "⚙️ <b>Настройки</b>\n\n"
        "Выберите раздел:",
        reply_markup=AdminKeyboards.settings_menu(),
        parse_mode="HTML"
    )


# ==================== LOGGING SETTINGS ====================


@settings_router.callback_query(F.data == "admin:settings:logging")
async def logging_settings(callback: CallbackQuery, db: Database, is_admin: bool = False):
    """Show logging settings"""
    if not is_admin:
        await callback.answer("⛔️ Нет доступа", show_alert=True)
        return

    s = await db.get_settings()
    await callback.message.edit_text(
        "📋 <b>Настройка логирования</b>\n\n"
        "Включайте/выключайте типы логов, которые\n"
        "будут отправляться в лог-канал:",
        reply_markup=AdminKeyboards.settings_logging(s),
        parse_mode="HTML"
    )


@settings_router.callback_query(F.data.startswith("admin:settings:log_toggle:"))
async def toggle_log(callback: CallbackQuery, db: Database, is_admin: bool = False):
    """Toggle a log type"""
    if not is_admin:
        await callback.answer("⛔️ Нет доступа", show_alert=True)
        return

    key = callback.data.split(":")[-1]
    s = await db.get_settings()
    current = getattr(s, key, None)
    if current is None:
        await callback.answer("Неизвестная настройка")
        return

    s = await db.update_settings(**{key: not current})
    new_state = "✅ Вкл" if not current else "❌ Выкл"
    await callback.answer(f"{new_state}")
    await callback.message.edit_reply_markup(
        reply_markup=AdminKeyboards.settings_logging(s)
    )


# ==================== REMINDER SETTINGS ====================


@settings_router.callback_query(F.data == "admin:settings:reminders")
async def reminders_settings(callback: CallbackQuery, db: Database, is_admin: bool = False):
    """Show reminder settings"""
    if not is_admin:
        await callback.answer("⛔️ Нет доступа", show_alert=True)
        return

    s = await db.get_settings()
    await callback.message.edit_text(
        "⏰ <b>Настройки напоминаний</b>\n\n"
        "Ежедневное напоминание о внесении продаж:",
        reply_markup=AdminKeyboards.settings_reminders(s),
        parse_mode="HTML"
    )


@settings_router.callback_query(F.data == "admin:settings:reminder_toggle")
async def toggle_reminder(callback: CallbackQuery, db: Database, is_admin: bool = False):
    """Toggle reminder on/off"""
    if not is_admin:
        await callback.answer("⛔️ Нет доступа", show_alert=True)
        return

    s = await db.get_settings()
    s = await db.update_settings(reminder_enabled=not s.reminder_enabled)
    new_state = "✅ Включено" if s.reminder_enabled else "❌ Выключено"
    await callback.answer(f"Напоминание: {new_state}")
    await callback.message.edit_reply_markup(
        reply_markup=AdminKeyboards.settings_reminders(s)
    )


@settings_router.callback_query(F.data == "admin:settings:reminder_time")
async def reminder_time_start(callback: CallbackQuery, state: FSMContext, is_admin: bool = False):
    """Start setting reminder time"""
    if not is_admin:
        await callback.answer("⛔️ Нет доступа", show_alert=True)
        return

    await state.set_state(AdminStates.settings_reminder_time)
    await callback.message.edit_text(
        "⏰ <b>Время напоминания</b>\n\n"
        "Введите время в формате <b>ЧЧ:ММ</b>\n"
        "Например: <code>23:00</code> или <code>21:30</code>",
        parse_mode="HTML"
    )


@settings_router.message(AdminStates.settings_reminder_time)
async def reminder_time_set(message: Message, db: Database, state: FSMContext, is_admin: bool = False):
    """Set reminder time"""
    if not is_admin:
        return

    text = message.text.strip()
    try:
        parts = text.split(":")
        hour = int(parts[0])
        minute = int(parts[1]) if len(parts) > 1 else 0
        if not (0 <= hour <= 23) or not (0 <= minute <= 59):
            raise ValueError()
    except (ValueError, IndexError):
        await message.answer(
            "❌ Неверный формат. Введите время в формате <b>ЧЧ:ММ</b>\n"
            "Например: <code>23:00</code>",
            parse_mode="HTML"
        )
        return

    s = await db.update_settings(reminder_hour=hour, reminder_minute=minute)
    await state.clear()
    await message.answer(
        f"✅ Время напоминания установлено: <b>{hour:02d}:{minute:02d}</b>\n\n"
        "⏰ <b>Настройки напоминаний</b>",
        reply_markup=AdminKeyboards.settings_reminders(s),
        parse_mode="HTML"
    )


# ==================== LOW STOCK THRESHOLD ====================


@settings_router.callback_query(F.data == "admin:settings:low_stock")
async def low_stock_settings(callback: CallbackQuery, db: Database, is_admin: bool = False):
    """Show low stock threshold settings"""
    if not is_admin:
        await callback.answer("⛔️ Нет доступа", show_alert=True)
        return

    s = await db.get_settings()
    await callback.message.edit_text(
        "📦 <b>Порог низкого остатка</b>\n\n"
        "Товары с остатком ≤ порога будут\n"
        "отображаться в разделе «Мало на складе»:",
        reply_markup=AdminKeyboards.settings_low_stock(s.low_stock_threshold),
        parse_mode="HTML"
    )


@settings_router.callback_query(F.data.startswith("admin:settings:set_low_stock:"))
async def set_low_stock(callback: CallbackQuery, db: Database, is_admin: bool = False):
    """Set low stock threshold"""
    if not is_admin:
        await callback.answer("⛔️ Нет доступа", show_alert=True)
        return

    value = int(callback.data.split(":")[-1])
    await db.update_settings(low_stock_threshold=value)
    await callback.answer(f"✅ Порог установлен: {value} шт.")
    await callback.message.edit_reply_markup(
        reply_markup=AdminKeyboards.settings_low_stock(value)
    )


# ==================== RESERVATION TIME ====================


@settings_router.callback_query(F.data == "admin:settings:reservation")
async def reservation_settings(callback: CallbackQuery, db: Database, is_admin: bool = False):
    """Show reservation time settings"""
    if not is_admin:
        await callback.answer("⛔️ Нет доступа", show_alert=True)
        return

    s = await db.get_settings()
    await callback.message.edit_text(
        "🔔 <b>Время резерва</b>\n\n"
        "Сколько часов действует резерв товара:",
        reply_markup=AdminKeyboards.settings_reservation(s.reservation_hours),
        parse_mode="HTML"
    )


@settings_router.callback_query(F.data.startswith("admin:settings:set_reservation:"))
async def set_reservation_time(callback: CallbackQuery, db: Database, is_admin: bool = False):
    """Set reservation time"""
    if not is_admin:
        await callback.answer("⛔️ Нет доступа", show_alert=True)
        return

    value = int(callback.data.split(":")[-1])
    await db.update_settings(reservation_hours=value)
    await callback.answer(f"✅ Время резерва: {value} ч.")
    await callback.message.edit_reply_markup(
        reply_markup=AdminKeyboards.settings_reservation(value)
    )
