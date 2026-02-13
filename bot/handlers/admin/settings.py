from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext

from ...database import Database
from ...database.models import User
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


# ==================== MAX RESERVATIONS ====================


@settings_router.callback_query(F.data == "admin:settings:max_reservations")
async def max_reservations_settings(callback: CallbackQuery, db: Database, is_admin: bool = False):
    """Show max reservations settings"""
    if not is_admin:
        await callback.answer("⛔️ Нет доступа", show_alert=True)
        return

    s = await db.get_settings()
    await callback.message.edit_text(
        "📌 <b>Макс. резервов на пользователя</b>\n\n"
        "Сколько товаров пользователь может\n"
        "зарезервировать одновременно:",
        reply_markup=AdminKeyboards.settings_max_reservations(s.max_reservations_per_user),
        parse_mode="HTML"
    )


@settings_router.callback_query(F.data.startswith("admin:settings:set_max_res:"))
async def set_max_reservations(callback: CallbackQuery, db: Database, is_admin: bool = False):
    """Set max reservations per user"""
    if not is_admin:
        await callback.answer("⛔️ Нет доступа", show_alert=True)
        return

    value = int(callback.data.split(":")[-1])
    await db.update_settings(max_reservations_per_user=value)
    await callback.answer(f"✅ Лимит: {value} резервов")
    await callback.message.edit_reply_markup(
        reply_markup=AdminKeyboards.settings_max_reservations(value)
    )


# ==================== CONTACTS SETTINGS ====================


@settings_router.callback_query(F.data == "admin:settings:contacts")
async def contacts_settings(callback: CallbackQuery, db: Database, is_admin: bool = False):
    """Show contacts settings"""
    if not is_admin:
        await callback.answer("⛔️ Нет доступа", show_alert=True)
        return

    s = await db.get_settings()
    text = "📞 <b>Настройка контактов</b>\n\n"
    text += f"Текст: {s.contacts_text or '<i>не задан</i>'}\n"
    text += f"Контакт: {s.contacts_contact or '<i>не задан</i>'}\n"
    text += f"Время работы: {s.contacts_work_hours or '<i>не задано</i>'}\n"

    await callback.message.edit_text(
        text,
        reply_markup=AdminKeyboards.contacts_settings(s),
        parse_mode="HTML"
    )


@settings_router.callback_query(F.data == "admin:settings:contacts:text")
async def contacts_set_text_start(callback: CallbackQuery, db: Database, state: FSMContext, is_admin: bool = False):
    """Start setting contacts text"""
    if not is_admin:
        await callback.answer("⛔️ Нет доступа", show_alert=True)
        return

    s = await db.get_settings()
    current = s.contacts_text or "не задан"

    await state.set_state(AdminStates.contacts_set_text)
    await callback.message.edit_text(
        "📝 <b>Текст контактов</b>\n\n"
        f"Текущий: <code>{current}</code>\n\n"
        "Введите текст, который будет отображаться на странице контактов.\n"
        "Отправьте <code>-</code> чтобы сбросить на стандартный.",
        parse_mode="HTML"
    )


@settings_router.message(AdminStates.contacts_set_text)
async def contacts_set_text(message: Message, db: Database, state: FSMContext, is_admin: bool = False):
    """Process contacts text"""
    if not is_admin:
        return

    text = message.text.strip()
    if text == "-":
        text = None

    await db.update_settings(contacts_text=text or "")
    await state.clear()

    s = await db.get_settings()
    await message.answer(
        "✅ Текст контактов обновлён!",
        reply_markup=AdminKeyboards.contacts_settings(s),
        parse_mode="HTML"
    )


@settings_router.callback_query(F.data == "admin:settings:contacts:contact")
async def contacts_set_contact_start(callback: CallbackQuery, db: Database, state: FSMContext, is_admin: bool = False):
    """Start setting contact info"""
    if not is_admin:
        await callback.answer("⛔️ Нет доступа", show_alert=True)
        return

    s = await db.get_settings()
    current = s.contacts_contact or "не задан"

    await state.set_state(AdminStates.contacts_set_contact)
    await callback.message.edit_text(
        "👤 <b>Контакт для связи</b>\n\n"
        f"Текущий: <code>{current}</code>\n\n"
        "Введите контакт (например @username, номер телефона или ссылку).\n"
        "Отправьте <code>-</code> чтобы убрать.",
        parse_mode="HTML"
    )


@settings_router.message(AdminStates.contacts_set_contact)
async def contacts_set_contact(message: Message, db: Database, state: FSMContext, is_admin: bool = False):
    """Process contact info"""
    if not is_admin:
        return

    text = message.text.strip()
    if text == "-":
        text = None

    await db.update_settings(contacts_contact=text or "")
    await state.clear()

    s = await db.get_settings()
    await message.answer(
        "✅ Контакт обновлён!",
        reply_markup=AdminKeyboards.contacts_settings(s),
        parse_mode="HTML"
    )


@settings_router.callback_query(F.data == "admin:settings:contacts:hours")
async def contacts_set_hours_start(callback: CallbackQuery, db: Database, state: FSMContext, is_admin: bool = False):
    """Start setting work hours"""
    if not is_admin:
        await callback.answer("⛔️ Нет доступа", show_alert=True)
        return

    s = await db.get_settings()
    current = s.contacts_work_hours or "не задано"

    await state.set_state(AdminStates.contacts_set_hours)
    await callback.message.edit_text(
        "🕐 <b>Время работы</b>\n\n"
        f"Текущее: <code>{current}</code>\n\n"
        "Введите время работы (например: <code>10:00 - 22:00</code>).\n"
        "Отправьте <code>-</code> чтобы убрать.",
        parse_mode="HTML"
    )


@settings_router.message(AdminStates.contacts_set_hours)
async def contacts_set_hours(message: Message, db: Database, state: FSMContext, is_admin: bool = False):
    """Process work hours"""
    if not is_admin:
        return

    text = message.text.strip()
    if text == "-":
        text = None

    await db.update_settings(contacts_work_hours=text or "")
    await state.clear()

    s = await db.get_settings()
    await message.answer(
        "✅ Время работы обновлено!",
        reply_markup=AdminKeyboards.contacts_settings(s),
        parse_mode="HTML"
    )


@settings_router.callback_query(F.data == "admin:settings:contacts:preview")
async def contacts_preview(callback: CallbackQuery, db: Database, is_admin: bool = False):
    """Preview contacts page"""
    if not is_admin:
        await callback.answer("⛔️ Нет доступа", show_alert=True)
        return

    s = await db.get_settings()
    text = _build_contacts_text(s)

    await callback.answer()
    await callback.message.edit_text(
        f"👁 <b>Предпросмотр:</b>\n\n{'─' * 20}\n{text}\n{'─' * 20}",
        reply_markup=AdminKeyboards.contacts_settings(s),
        parse_mode="HTML"
    )


def _build_contacts_text(s) -> str:
    """Build contacts page text from settings"""
    parts = ["📞 <b>Контакты</b>\n"]
    if s.contacts_text:
        parts.append(s.contacts_text)
    else:
        parts.append("Для связи с продавцом напишите администратору.")
    if s.contacts_contact:
        parts.append(f"\n👤 {s.contacts_contact}")
    if s.contacts_work_hours:
        parts.append(f"\n🕐 Время работы: {s.contacts_work_hours}")
    return "\n".join(parts)


# ==================== BAN MANAGEMENT ====================


@settings_router.callback_query(F.data == "admin:settings:bans")
async def ban_management(callback: CallbackQuery, db: Database, is_admin: bool = False):
    """Show ban management"""
    if not is_admin:
        await callback.answer("⛔️ Нет доступа", show_alert=True)
        return

    banned = await db.get_banned_users()
    await callback.message.edit_text(
        "🚫 <b>Управление банами</b>\n\n"
        f"Забаненных: {len(banned)}\n"
        "Нажмите на пользователя чтобы разбанить:",
        reply_markup=AdminKeyboards.ban_management(banned),
        parse_mode="HTML"
    )


@settings_router.callback_query(F.data == "admin:ban:add")
async def ban_add_start(callback: CallbackQuery, state: FSMContext, is_admin: bool = False):
    """Start ban process"""
    if not is_admin:
        await callback.answer("⛔️ Нет доступа", show_alert=True)
        return

    await state.set_state(AdminStates.ban_user_id)
    await callback.message.edit_text(
        "🚫 <b>Бан пользователя</b>\n\n"
        "Отправьте Telegram ID или @username пользователя:",
        parse_mode="HTML"
    )


@settings_router.message(AdminStates.ban_user_id)
async def ban_add_process(message: Message, db: Database, state: FSMContext, is_admin: bool = False):
    """Process ban"""
    if not is_admin:
        return

    text = message.text.strip()
    user = None

    if text.startswith("@"):
        username = text[1:]
        user = await db.get_user_by_username(username)
    else:
        try:
            tid = int(text)
            user = await db.get_user_by_telegram_id(tid)
        except ValueError:
            user = await db.get_user_by_username(text)

    if not user:
        await message.answer(
            "❌ Пользователь не найден. Он должен хотя бы раз написать боту.\n"
            "Попробуйте снова или отправьте /admin для отмены.",
            parse_mode="HTML"
        )
        return

    if user.is_admin:
        await message.answer("❌ Нельзя забанить администратора!")
        await state.clear()
        return

    await db.ban_user(user.telegram_id)
    await state.clear()

    banned = await db.get_banned_users()
    await message.answer(
        f"🚫 Пользователь {user.full_name} забанен!",
        reply_markup=AdminKeyboards.ban_management(banned),
        parse_mode="HTML"
    )


@settings_router.callback_query(F.data.startswith("admin:ban:remove:"))
async def ban_remove(callback: CallbackQuery, db: Database, is_admin: bool = False):
    """Unban user"""
    if not is_admin:
        await callback.answer("⛔️ Нет доступа", show_alert=True)
        return

    tid = int(callback.data.split(":")[-1])
    await db.unban_user(tid)
    await callback.answer("✅ Пользователь разбанен")

    banned = await db.get_banned_users()
    await callback.message.edit_text(
        "🚫 <b>Управление банами</b>\n\n"
        f"Забаненных: {len(banned)}\n"
        "Нажмите на пользователя чтобы разбанить:",
        reply_markup=AdminKeyboards.ban_management(banned),
        parse_mode="HTML"
    )
