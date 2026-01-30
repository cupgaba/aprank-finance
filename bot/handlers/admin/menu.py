from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import BaseFilter
from aiogram.fsm.context import FSMContext

from ...database import Database
from ...database.models import User
from ...keyboards.admin import AdminKeyboards

menu_router = Router()


# Filter for admin only
class IsAdmin(BaseFilter):
    async def __call__(self, message: Message, is_admin: bool = False) -> bool:
        return is_admin


@menu_router.message(F.text == "📦 Товары", IsAdmin())
async def products_menu(message: Message, state: FSMContext):
    """Products management menu"""
    await state.clear()
    await message.answer(
        "📦 <b>Управление товарами</b>\n\n"
        "Выберите действие:",
        reply_markup=AdminKeyboards.products_menu(),
        parse_mode="HTML"
    )


@menu_router.callback_query(F.data == "admin:products_menu")
async def products_menu_callback(callback: CallbackQuery, is_admin: bool, state: FSMContext):
    """Products menu callback"""
    if not is_admin:
        await callback.answer("⛔️ Нет доступа", show_alert=True)
        return

    await state.clear()
    await callback.message.edit_text(
        "📦 <b>Управление товарами</b>\n\n"
        "Выберите действие:",
        reply_markup=AdminKeyboards.products_menu(),
        parse_mode="HTML"
    )


@menu_router.message(F.text == "📊 Статистика", IsAdmin())
async def statistics_menu(message: Message, state: FSMContext):
    """Statistics menu"""
    await state.clear()
    await message.answer(
        "📊 <b>Статистика</b>\n\n"
        "Выберите период:",
        reply_markup=AdminKeyboards.statistics_menu(),
        parse_mode="HTML"
    )


@menu_router.message(F.text == "📥 Закупки", IsAdmin())
async def supplies_menu(message: Message, state: FSMContext):
    """Supplies menu"""
    await state.clear()
    await message.answer(
        "📥 <b>Закупки</b>\n\n"
        "Выберите действие:",
        reply_markup=AdminKeyboards.supplies_menu(),
        parse_mode="HTML"
    )


@menu_router.callback_query(F.data == "admin:supplies_menu")
async def supplies_menu_callback(callback: CallbackQuery, is_admin: bool, state: FSMContext):
    """Supplies menu callback"""
    if not is_admin:
        await callback.answer("⛔️ Нет доступа", show_alert=True)
        return

    await state.clear()
    await callback.message.edit_text(
        "📥 <b>Закупки</b>\n\n"
        "Выберите действие:",
        reply_markup=AdminKeyboards.supplies_menu(),
        parse_mode="HTML"
    )


@menu_router.message(F.text == "💰 Продажи", IsAdmin())
async def sales_menu(message: Message, state: FSMContext):
    """Sales menu"""
    await state.clear()
    await message.answer(
        "💰 <b>Продажи</b>\n\n"
        "Выберите действие:",
        reply_markup=AdminKeyboards.sales_menu(),
        parse_mode="HTML"
    )


@menu_router.callback_query(F.data == "admin:sales_menu")
async def sales_menu_callback(callback: CallbackQuery, is_admin: bool, state: FSMContext):
    """Sales menu callback"""
    if not is_admin:
        await callback.answer("⛔️ Нет доступа", show_alert=True)
        return

    await state.clear()
    await callback.message.edit_text(
        "💰 <b>Продажи</b>\n\n"
        "Выберите действие:",
        reply_markup=AdminKeyboards.sales_menu(),
        parse_mode="HTML"
    )


@menu_router.message(F.text == "📤 Списания", IsAdmin())
async def writeoffs_menu(message: Message, state: FSMContext):
    """Write-offs menu"""
    await state.clear()
    await message.answer(
        "📤 <b>Списания</b>\n\n"
        "Выберите действие:",
        reply_markup=AdminKeyboards.writeoffs_menu(),
        parse_mode="HTML"
    )


@menu_router.callback_query(F.data == "admin:writeoffs_menu")
async def writeoffs_menu_callback(callback: CallbackQuery, is_admin: bool, state: FSMContext):
    """Write-offs menu callback"""
    if not is_admin:
        await callback.answer("⛔️ Нет доступа", show_alert=True)
        return

    await state.clear()
    await callback.message.edit_text(
        "📤 <b>Списания</b>\n\n"
        "Выберите действие:",
        reply_markup=AdminKeyboards.writeoffs_menu(),
        parse_mode="HTML"
    )


@menu_router.message(F.text == "📢 Публикации", IsAdmin())
async def publications_menu(message: Message, state: FSMContext):
    """Publications menu"""
    await state.clear()
    await message.answer(
        "📢 <b>Публикации</b>\n\n"
        "Выберите действие:",
        reply_markup=AdminKeyboards.publications_menu(),
        parse_mode="HTML"
    )


@menu_router.callback_query(F.data == "admin:publications_menu")
async def publications_menu_callback(callback: CallbackQuery, is_admin: bool, state: FSMContext):
    """Publications menu callback"""
    if not is_admin:
        await callback.answer("⛔️ Нет доступа", show_alert=True)
        return

    await state.clear()
    await callback.message.edit_text(
        "📢 <b>Публикации</b>\n\n"
        "Выберите действие:",
        reply_markup=AdminKeyboards.publications_menu(),
        parse_mode="HTML"
    )


@menu_router.message(F.text == "🔔 Резервы", IsAdmin())
async def reservations_menu(message: Message, state: FSMContext):
    """Reservations menu"""
    await state.clear()
    await message.answer(
        "🔔 <b>Резервирования</b>\n\n"
        "Выберите действие:",
        reply_markup=AdminKeyboards.reservations_menu(),
        parse_mode="HTML"
    )


@menu_router.callback_query(F.data == "admin:reservations_menu")
async def reservations_menu_callback(callback: CallbackQuery, is_admin: bool, state: FSMContext):
    """Reservations menu callback"""
    if not is_admin:
        await callback.answer("⛔️ Нет доступа", show_alert=True)
        return

    await state.clear()
    await callback.message.edit_text(
        "🔔 <b>Резервирования</b>\n\n"
        "Выберите действие:",
        reply_markup=AdminKeyboards.reservations_menu(),
        parse_mode="HTML"
    )


@menu_router.message(F.text == "⚙️ Настройки", IsAdmin())
async def settings_menu(message: Message, state: FSMContext):
    """Settings menu"""
    await state.clear()
    await message.answer(
        "⚙️ <b>Настройки</b>\n\n"
        "Выберите раздел:",
        reply_markup=AdminKeyboards.settings_menu(),
        parse_mode="HTML"
    )


@menu_router.callback_query(F.data == "cancel")
async def cancel_callback(callback: CallbackQuery, is_admin: bool, state: FSMContext):
    """Cancel callback"""
    await state.clear()
    await callback.message.delete()
    await callback.answer("Отменено")
