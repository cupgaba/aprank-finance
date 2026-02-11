from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext

from ...database import Database
from ...keyboards.admin import AdminKeyboards
from ...states.admin import AdminStates
from ...services.channel import ChannelService
from ...utils.formatting import format_pricelist

publications_router = Router()


# ==================== PUBLISH PRICELIST ====================


@publications_router.callback_query(F.data == "admin:publish:pricelist")
async def publish_pricelist(callback: CallbackQuery, db: Database, bot: Bot, is_admin: bool):
    """Publish full pricelist to channel"""
    if not is_admin:
        await callback.answer("⛔️ Нет доступа", show_alert=True)
        return

    s = await db.get_settings()
    channel_service = ChannelService(bot, db)
    success = await channel_service.publish_pricelist(settings=s)

    if success:
        await callback.answer("✅ Прайс-лист опубликован!")
        await callback.message.edit_text(
            "✅ Прайс-лист успешно опубликован в канал!",
            reply_markup=AdminKeyboards.publications_menu(),
            parse_mode="HTML"
        )
    else:
        await callback.answer("❌ Ошибка публикации. Проверьте настройки канала.", show_alert=True)


# ==================== PRICELIST CONFIG ====================


@publications_router.callback_query(F.data == "admin:publish:config")
async def pricelist_config(callback: CallbackQuery, db: Database, is_admin: bool):
    """Show pricelist template config"""
    if not is_admin:
        await callback.answer("⛔️ Нет доступа", show_alert=True)
        return

    s = await db.get_settings()
    await callback.message.edit_text(
        "⚙️ <b>Настройка шаблона прайса</b>\n\n"
        "Настройте как будет выглядеть прайс-лист\n"
        "при публикации в канал:",
        reply_markup=AdminKeyboards.pricelist_config(s),
        parse_mode="HTML"
    )


@publications_router.callback_query(F.data == "admin:publish:config:header")
async def pricelist_set_header_start(callback: CallbackQuery, db: Database, is_admin: bool, state: FSMContext):
    """Start setting pricelist header"""
    if not is_admin:
        await callback.answer("⛔️ Нет доступа", show_alert=True)
        return

    s = await db.get_settings()
    current = s.pricelist_header or "ПРАЙС-ЛИСТ"

    await state.set_state(AdminStates.pricelist_set_header)
    await callback.message.edit_text(
        "📝 <b>Заголовок прайс-листа</b>\n\n"
        f"Текущий: <code>{current}</code>\n\n"
        "Введите новый заголовок:",
        parse_mode="HTML"
    )


@publications_router.message(AdminStates.pricelist_set_header)
async def pricelist_set_header(message: Message, db: Database, state: FSMContext):
    """Process new pricelist header"""
    header = message.text.strip()
    if len(header) > 200:
        await message.answer("❌ Заголовок слишком длинный (макс. 200 символов). Попробуйте снова:")
        return

    await db.update_settings(pricelist_header=header)
    await state.clear()

    s = await db.get_settings()
    await message.answer(
        f"✅ Заголовок установлен: <b>{header}</b>",
        reply_markup=AdminKeyboards.pricelist_config(s),
        parse_mode="HTML"
    )


@publications_router.callback_query(F.data == "admin:publish:config:toggle_qty")
async def pricelist_toggle_qty(callback: CallbackQuery, db: Database, is_admin: bool):
    """Toggle show quantities in pricelist"""
    if not is_admin:
        await callback.answer("⛔️ Нет доступа", show_alert=True)
        return

    s = await db.get_settings()
    s = await db.update_settings(pricelist_show_quantities=not s.pricelist_show_quantities)
    state = "✅ Вкл" if s.pricelist_show_quantities else "❌ Выкл"
    await callback.answer(f"Количество: {state}")
    await callback.message.edit_reply_markup(
        reply_markup=AdminKeyboards.pricelist_config(s)
    )


@publications_router.callback_query(F.data == "admin:publish:config:toggle_brands")
async def pricelist_toggle_brands(callback: CallbackQuery, db: Database, is_admin: bool):
    """Toggle brand grouping in pricelist"""
    if not is_admin:
        await callback.answer("⛔️ Нет доступа", show_alert=True)
        return

    s = await db.get_settings()
    s = await db.update_settings(pricelist_show_brands=not s.pricelist_show_brands)
    state = "✅ Вкл" if s.pricelist_show_brands else "❌ Выкл"
    await callback.answer(f"Группировка: {state}")
    await callback.message.edit_reply_markup(
        reply_markup=AdminKeyboards.pricelist_config(s)
    )


@publications_router.callback_query(F.data == "admin:publish:config:footer")
async def pricelist_set_footer_start(callback: CallbackQuery, db: Database, is_admin: bool, state: FSMContext):
    """Start setting pricelist footer"""
    if not is_admin:
        await callback.answer("⛔️ Нет доступа", show_alert=True)
        return

    s = await db.get_settings()
    current = s.pricelist_footer or "не задана"

    await state.set_state(AdminStates.pricelist_set_footer)
    await callback.message.edit_text(
        "📝 <b>Подпись прайс-листа</b>\n\n"
        f"Текущая: <code>{current}</code>\n\n"
        "Введите текст подписи (будет добавлена в конце прайса).\n"
        "Отправьте <code>-</code> чтобы убрать подпись.",
        parse_mode="HTML"
    )


@publications_router.message(AdminStates.pricelist_set_footer)
async def pricelist_set_footer(message: Message, db: Database, state: FSMContext):
    """Process new pricelist footer"""
    footer = message.text.strip()
    if footer == "-":
        footer = None

    if footer and len(footer) > 500:
        await message.answer("❌ Подпись слишком длинная (макс. 500 символов). Попробуйте снова:")
        return

    await db.update_settings(pricelist_footer=footer if footer else "")
    await state.clear()

    s = await db.get_settings()
    if footer:
        await message.answer(
            f"✅ Подпись установлена",
            reply_markup=AdminKeyboards.pricelist_config(s),
            parse_mode="HTML"
        )
    else:
        await message.answer(
            "✅ Подпись удалена",
            reply_markup=AdminKeyboards.pricelist_config(s),
            parse_mode="HTML"
        )


@publications_router.callback_query(F.data == "admin:publish:config:photo")
async def pricelist_set_photo_start(callback: CallbackQuery, db: Database, is_admin: bool, state: FSMContext):
    """Start setting pricelist photo"""
    if not is_admin:
        await callback.answer("⛔️ Нет доступа", show_alert=True)
        return

    s = await db.get_settings()

    await state.set_state(AdminStates.pricelist_set_photo)

    text = "🖼 <b>Фото прайс-листа</b>\n\n"
    if s.pricelist_photo_file_id:
        text += "Текущее фото установлено.\n\n"
    else:
        text += "Фото не установлено.\n\n"
    text += "Отправьте фото для прайс-листа.\nОтправьте <code>-</code> чтобы убрать фото."

    if s.pricelist_photo_file_id:
        await callback.message.delete()
        await callback.message.answer_photo(
            photo=s.pricelist_photo_file_id,
            caption=text,
            parse_mode="HTML"
        )
    else:
        await callback.message.edit_text(text, parse_mode="HTML")


@publications_router.message(AdminStates.pricelist_set_photo, F.photo)
async def pricelist_set_photo(message: Message, db: Database, state: FSMContext):
    """Process new pricelist photo"""
    photo_file_id = message.photo[-1].file_id
    await db.update_settings(pricelist_photo_file_id=photo_file_id)
    await state.clear()

    s = await db.get_settings()
    await message.answer(
        "✅ Фото прайс-листа установлено!",
        reply_markup=AdminKeyboards.pricelist_config(s),
        parse_mode="HTML"
    )


@publications_router.message(AdminStates.pricelist_set_photo, F.text)
async def pricelist_remove_photo(message: Message, db: Database, state: FSMContext):
    """Remove pricelist photo"""
    if message.text.strip() == "-":
        await db.update_settings(pricelist_photo_file_id="")
        await state.clear()

        s = await db.get_settings()
        await message.answer(
            "✅ Фото удалено",
            reply_markup=AdminKeyboards.pricelist_config(s),
            parse_mode="HTML"
        )
    else:
        await message.answer("❌ Отправьте фото или <code>-</code> для удаления.", parse_mode="HTML")


@publications_router.callback_query(F.data == "admin:publish:preview")
async def pricelist_preview(callback: CallbackQuery, db: Database, bot: Bot, is_admin: bool):
    """Preview pricelist with current template"""
    if not is_admin:
        await callback.answer("⛔️ Нет доступа", show_alert=True)
        return

    s = await db.get_settings()
    products = await db.get_all_products(in_stock_only=True)

    if not products:
        await callback.answer("❌ Нет товаров в наличии", show_alert=True)
        return

    text = format_pricelist(
        products,
        header=s.pricelist_header,
        show_quantities=s.pricelist_show_quantities,
        show_brands=s.pricelist_show_brands,
        footer=s.pricelist_footer,
    )

    # Truncate if too long for preview
    if len(text) > 3800:
        text = text[:3800] + "\n\n<i>... (обрезано для предпросмотра)</i>"

    preview_text = f"👁 <b>Предпросмотр прайс-листа:</b>\n\n{'─' * 20}\n{text}\n{'─' * 20}"

    try:
        await callback.message.delete()
    except Exception:
        pass

    if s.pricelist_photo_file_id:
        # With photo - caption limit is 1024
        if len(preview_text) <= 1024:
            await callback.message.answer_photo(
                photo=s.pricelist_photo_file_id,
                caption=preview_text,
                parse_mode="HTML"
            )
        else:
            # Split: first part as caption, rest as follow-up
            from ...services.channel import ChannelService
            caption, remaining = ChannelService._split_text_for_caption(preview_text, 1024)
            await callback.message.answer_photo(
                photo=s.pricelist_photo_file_id,
                caption=caption,
                parse_mode="HTML"
            )
            if remaining:
                await callback.message.answer(
                    remaining,
                    parse_mode="HTML"
                )
        await callback.message.answer(
            "⚙️ <b>Настройка шаблона прайса</b>",
            reply_markup=AdminKeyboards.pricelist_config(s),
            parse_mode="HTML"
        )
    else:
        await callback.message.answer(
            preview_text,
            reply_markup=AdminKeyboards.pricelist_config(s),
            parse_mode="HTML"
        )


# ==================== AUTO-PUBLISH SETTINGS ====================


@publications_router.callback_query(F.data == "admin:publish:auto")
async def pricelist_auto_settings(callback: CallbackQuery, db: Database, is_admin: bool):
    """Show pricelist auto-publish settings"""
    if not is_admin:
        await callback.answer("⛔️ Нет доступа", show_alert=True)
        return

    s = await db.get_settings()
    await callback.message.edit_text(
        "⏰ <b>Автопубликация прайс-листа</b>\n\n"
        "Настройте автоматическую публикацию\n"
        "прайса в канал по расписанию:",
        reply_markup=AdminKeyboards.pricelist_auto(s),
        parse_mode="HTML"
    )


@publications_router.callback_query(F.data == "admin:publish:auto:toggle")
async def pricelist_auto_toggle(callback: CallbackQuery, db: Database, is_admin: bool):
    """Toggle pricelist auto-publish"""
    if not is_admin:
        await callback.answer("⛔️ Нет доступа", show_alert=True)
        return

    s = await db.get_settings()
    s = await db.update_settings(pricelist_auto_enabled=not s.pricelist_auto_enabled)
    state = "✅ Включена" if s.pricelist_auto_enabled else "❌ Выключена"
    await callback.answer(f"Автопубликация: {state}")
    await callback.message.edit_reply_markup(
        reply_markup=AdminKeyboards.pricelist_auto(s)
    )


@publications_router.callback_query(F.data.startswith("admin:publish:auto:freq:"))
async def pricelist_auto_frequency(callback: CallbackQuery, db: Database, is_admin: bool):
    """Set auto-publish frequency"""
    if not is_admin:
        await callback.answer("⛔️ Нет доступа", show_alert=True)
        return

    freq = int(callback.data.split(":")[-1])
    s = await db.update_settings(pricelist_auto_frequency=freq)
    await callback.answer(f"✅ Частота: {freq}x/день")
    await callback.message.edit_reply_markup(
        reply_markup=AdminKeyboards.pricelist_auto(s)
    )


@publications_router.callback_query(F.data == "admin:publish:auto:time1")
async def pricelist_set_time1_start(callback: CallbackQuery, is_admin: bool, state: FSMContext):
    """Start setting time slot 1"""
    if not is_admin:
        await callback.answer("⛔️ Нет доступа", show_alert=True)
        return

    await state.set_state(AdminStates.pricelist_set_time1)
    await callback.message.edit_text(
        "⏰ <b>Время публикации 1</b>\n\n"
        "Введите время в формате <b>ЧЧ:ММ</b>\n"
        "Например: <code>10:00</code>",
        parse_mode="HTML"
    )


@publications_router.message(AdminStates.pricelist_set_time1)
async def pricelist_set_time1(message: Message, db: Database, state: FSMContext):
    """Process time slot 1"""
    hour, minute = _parse_time(message.text)
    if hour is None:
        await message.answer("❌ Неверный формат. Введите время в формате <b>ЧЧ:ММ</b>", parse_mode="HTML")
        return

    s = await db.update_settings(pricelist_time1_hour=hour, pricelist_time1_minute=minute)
    await state.clear()
    await message.answer(
        f"✅ Время 1 установлено: <b>{hour:02d}:{minute:02d}</b>",
        reply_markup=AdminKeyboards.pricelist_auto(s),
        parse_mode="HTML"
    )


@publications_router.callback_query(F.data == "admin:publish:auto:time2")
async def pricelist_set_time2_start(callback: CallbackQuery, is_admin: bool, state: FSMContext):
    """Start setting time slot 2"""
    if not is_admin:
        await callback.answer("⛔️ Нет доступа", show_alert=True)
        return

    await state.set_state(AdminStates.pricelist_set_time2)
    await callback.message.edit_text(
        "⏰ <b>Время публикации 2</b>\n\n"
        "Введите время в формате <b>ЧЧ:ММ</b>\n"
        "Например: <code>18:00</code>",
        parse_mode="HTML"
    )


@publications_router.message(AdminStates.pricelist_set_time2)
async def pricelist_set_time2(message: Message, db: Database, state: FSMContext):
    """Process time slot 2"""
    hour, minute = _parse_time(message.text)
    if hour is None:
        await message.answer("❌ Неверный формат. Введите время в формате <b>ЧЧ:ММ</b>", parse_mode="HTML")
        return

    s = await db.update_settings(pricelist_time2_hour=hour, pricelist_time2_minute=minute)
    await state.clear()
    await message.answer(
        f"✅ Время 2 установлено: <b>{hour:02d}:{minute:02d}</b>",
        reply_markup=AdminKeyboards.pricelist_auto(s),
        parse_mode="HTML"
    )


@publications_router.callback_query(F.data == "admin:publish:auto:time3")
async def pricelist_set_time3_start(callback: CallbackQuery, is_admin: bool, state: FSMContext):
    """Start setting time slot 3"""
    if not is_admin:
        await callback.answer("⛔️ Нет доступа", show_alert=True)
        return

    await state.set_state(AdminStates.pricelist_set_time3)
    await callback.message.edit_text(
        "⏰ <b>Время публикации 3</b>\n\n"
        "Введите время в формате <b>ЧЧ:ММ</b>\n"
        "Например: <code>14:00</code>",
        parse_mode="HTML"
    )


@publications_router.message(AdminStates.pricelist_set_time3)
async def pricelist_set_time3(message: Message, db: Database, state: FSMContext):
    """Process time slot 3"""
    hour, minute = _parse_time(message.text)
    if hour is None:
        await message.answer("❌ Неверный формат. Введите время в формате <b>ЧЧ:ММ</b>", parse_mode="HTML")
        return

    s = await db.update_settings(pricelist_time3_hour=hour, pricelist_time3_minute=minute)
    await state.clear()
    await message.answer(
        f"✅ Время 3 установлено: <b>{hour:02d}:{minute:02d}</b>",
        reply_markup=AdminKeyboards.pricelist_auto(s),
        parse_mode="HTML"
    )


def _parse_time(text: str) -> tuple:
    """Parse time string HH:MM, returns (hour, minute) or (None, None)"""
    try:
        parts = text.strip().split(":")
        hour = int(parts[0])
        minute = int(parts[1]) if len(parts) > 1 else 0
        if 0 <= hour <= 23 and 0 <= minute <= 59:
            return hour, minute
    except (ValueError, IndexError):
        pass
    return None, None
