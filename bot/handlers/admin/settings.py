from aiogram import Router, F, Bot
from aiogram.types import CallbackQuery, Message, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext

from ...database import Database
from ...database.models import User
from ...keyboards.admin import AdminKeyboards
from ...states.admin import AdminStates
from ...services import SubscriptionGuardService, ChatSubscriptionConfig

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


# ==================== BROADCAST ====================


def _broadcast_hide_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="Скрыть", callback_data="broadcast:hide")]])


@settings_router.callback_query(F.data == "admin:settings:broadcast")
async def broadcast_start(callback: CallbackQuery, state: FSMContext, is_admin: bool = False):
    if not is_admin:
        await callback.answer("⛔️ Нет доступа", show_alert=True)
        return

    await state.set_state(AdminStates.broadcast_wait_content)
    await callback.message.edit_text(
        "📣 <b>Рассылка пользователям</b>\n\n"
        "Отправьте сообщение для рассылки.\n"
        "Поддерживаются все форматы: текст, фото, видео, документы, кружки,\n"
        "голосовые, стикеры, а также подписи и форматирование.\n\n"
        "Для отмены: /cancel",
        parse_mode="HTML"
    )


@settings_router.message(AdminStates.broadcast_wait_content)
async def broadcast_process(message: Message, db: Database, state: FSMContext, bot: Bot, is_admin: bool = False):
    if not is_admin:
        return

    users = await db.get_all_users(active_only=True)
    recipients = [u for u in users if u.telegram_id != message.from_user.id]

    total = len(recipients)
    sent = 0
    errors = 0

    status = await message.answer(
        "📣 <b>Запуск рассылки</b>\n\n"
        f"Отправлено: <b>{sent}/{total}</b>\n"
        f"Ошибок: <b>{errors}</b>",
        parse_mode="HTML"
    )

    for idx, user in enumerate(recipients, start=1):
        try:
            await message.copy_to(chat_id=user.telegram_id, reply_markup=_broadcast_hide_keyboard())
            sent += 1
        except Exception:
            errors += 1

        # update progress each 10 messages and on finish
        if idx % 10 == 0 or idx == total:
            try:
                await status.edit_text(
                    "📣 <b>Запуск рассылки</b>\n\n"
                    f"Отправлено: <b>{sent}/{total}</b>\n"
                    f"Ошибок: <b>{errors}</b>",
                    parse_mode="HTML"
                )
            except Exception:
                pass

    try:
        await status.edit_text(
            "✅ <b>Рассылка завершена</b>\n\n"
            f"Отправлено: <b>{sent}/{total}</b>\n"
            f"Ошибок: <b>{errors}</b>",
            parse_mode="HTML"
        )
    except Exception:
        await message.answer(
            "✅ <b>Рассылка завершена</b>\n\n"
            f"Отправлено: <b>{sent}/{total}</b>\n"
            f"Ошибок: <b>{errors}</b>",
            parse_mode="HTML"
        )

    await state.clear()


@settings_router.callback_query(F.data == "broadcast:hide")
async def broadcast_hide(callback: CallbackQuery):
    try:
        await callback.message.delete()
    except Exception:
        pass
    await callback.answer()


# ==================== MARKETPLACE CHAT SUBSCRIPTION ====================


@settings_router.callback_query(F.data == "admin:settings:market_subs")
async def market_subscriptions_menu(callback: CallbackQuery, db: Database, is_admin: bool = False):
    if not is_admin:
        await callback.answer("⛔️ Нет доступа", show_alert=True)
        return

    s = await db.get_settings()
    configs = SubscriptionGuardService.parse_settings(s)
    await callback.message.edit_text(
        "🛡 <b>Проверка подписки для бесед</b>\n\n"
        "Здесь вы можете добавить беседы барахолки и список каналов,\n"
        "на которые пользователь должен быть подписан для отправки сообщений.",
        reply_markup=AdminKeyboards.market_subscriptions_list(configs),
        parse_mode="HTML"
    )


@settings_router.callback_query(F.data == "admin:settings:market_sub:add")
async def market_sub_add_start(callback: CallbackQuery, state: FSMContext, is_admin: bool = False):
    if not is_admin:
        await callback.answer("⛔️ Нет доступа", show_alert=True)
        return

    await state.set_state(AdminStates.market_sub_chat_id)
    await callback.message.edit_text(
        "➕ <b>Добавить беседу</b>\n\n"
        "Отправьте ID беседы (например: <code>-1001234567890</code>).",
        parse_mode="HTML"
    )


@settings_router.message(AdminStates.market_sub_chat_id)
async def market_sub_add_chat_id(message: Message, state: FSMContext, is_admin: bool = False):
    if not is_admin:
        return

    try:
        chat_id = int(message.text.strip())
    except (TypeError, ValueError):
        await message.answer("❌ Некорректный ID беседы. Пример: <code>-1001234567890</code>", parse_mode="HTML")
        return

    await state.update_data(market_sub_chat_id=chat_id)
    await state.set_state(AdminStates.market_sub_channels)
    await message.answer(
        "📡 Теперь отправьте ID каналов через запятую.\n"
        "Пример: <code>-1001111111111,-1002222222222</code>",
        parse_mode="HTML"
    )


@settings_router.message(AdminStates.market_sub_channels)
async def market_sub_add_channels(message: Message, db: Database, state: FSMContext, is_admin: bool = False):
    if not is_admin:
        return

    raw = message.text.strip()
    try:
        channels = [int(x.strip()) for x in raw.split(",") if x.strip()]
    except ValueError:
        await message.answer("❌ Некорректный список каналов. Используйте только ID через запятую.")
        return

    if not channels:
        await message.answer("❌ Укажите хотя бы один канал.")
        return

    data = await state.get_data()
    chat_id = data.get("market_sub_chat_id")
    if chat_id is None:
        await state.clear()
        await message.answer("❌ Данные утеряны. Начните снова через настройки.")
        return

    settings = await db.get_settings()
    configs = SubscriptionGuardService.parse_settings(settings)

    updated = False
    for i, cfg in enumerate(configs):
        if cfg.chat_id == chat_id:
            configs[i] = ChatSubscriptionConfig(chat_id=chat_id, channels=channels)
            updated = True
            break
    if not updated:
        configs.append(ChatSubscriptionConfig(chat_id=chat_id, channels=channels))

    await db.update_settings(market_chat_subscriptions=SubscriptionGuardService.serialize(configs))
    await state.clear()

    fresh = SubscriptionGuardService.parse_settings(await db.get_settings())
    await message.answer(
        "✅ Настройка сохранена.",
        reply_markup=AdminKeyboards.market_subscriptions_list(fresh),
        parse_mode="HTML"
    )


@settings_router.callback_query(F.data.startswith("admin:settings:market_sub:edit:"))
async def market_sub_edit(callback: CallbackQuery, db: Database, is_admin: bool = False):
    if not is_admin:
        await callback.answer("⛔️ Нет доступа", show_alert=True)
        return

    chat_id = int(callback.data.split(":")[-1])
    settings = await db.get_settings()
    cfg = SubscriptionGuardService.get_chat_config(settings, chat_id)
    if not cfg:
        await callback.answer("Беседа не найдена", show_alert=True)
        return

    channels_text = "\n".join(str(c) for c in cfg.channels) if cfg.channels else "<i>Не заданы</i>"
    await callback.message.edit_text(
        "💬 <b>Настройка беседы</b>\n\n"
        f"ID беседы: <code>{cfg.chat_id}</code>\n"
        f"Каналы:\n{channels_text}",
        reply_markup=AdminKeyboards.market_subscription_actions(cfg.chat_id, cfg.channels),
        parse_mode="HTML"
    )


@settings_router.callback_query(F.data.startswith("admin:settings:market_sub:set_channels:"))
async def market_sub_set_channels_start(callback: CallbackQuery, state: FSMContext, is_admin: bool = False):
    if not is_admin:
        await callback.answer("⛔️ Нет доступа", show_alert=True)
        return

    chat_id = int(callback.data.split(":")[-1])
    await state.update_data(market_sub_chat_id=chat_id)
    await state.set_state(AdminStates.market_sub_channels)
    await callback.message.edit_text(
        "✏️ <b>Изменение каналов</b>\n\n"
        f"Беседа: <code>{chat_id}</code>\n"
        "Отправьте новый список каналов через запятую.",
        parse_mode="HTML"
    )


@settings_router.callback_query(F.data.startswith("admin:settings:market_sub:delete:"))
async def market_sub_delete(callback: CallbackQuery, db: Database, is_admin: bool = False):
    if not is_admin:
        await callback.answer("⛔️ Нет доступа", show_alert=True)
        return

    chat_id = int(callback.data.split(":")[-1])
    settings = await db.get_settings()
    configs = [cfg for cfg in SubscriptionGuardService.parse_settings(settings) if cfg.chat_id != chat_id]
    await db.update_settings(market_chat_subscriptions=SubscriptionGuardService.serialize(configs))

    await callback.answer("✅ Беседа удалена")
    await callback.message.edit_text(
        "🛡 <b>Проверка подписки для бесед</b>",
        reply_markup=AdminKeyboards.market_subscriptions_list(configs),
        parse_mode="HTML"
    )


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
