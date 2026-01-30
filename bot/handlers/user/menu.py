from aiogram import Router, F
from aiogram.types import Message
from aiogram.fsm.context import FSMContext

from ...database import Database
from ...database.models import User
from ...keyboards.user import UserKeyboards
from ...keyboards.admin import AdminKeyboards

menu_router = Router()


@menu_router.message(F.text == "📋 Прайс-лист")
async def pricelist_menu(message: Message, db: Database, state: FSMContext):
    """Price list menu"""
    await state.clear()

    categories = await db.get_all_categories()

    await message.answer(
        "📋 <b>Прайс-лист</b>\n\n"
        "Выберите категорию или получите весь прайс:",
        reply_markup=UserKeyboards.pricelist_categories(categories),
        parse_mode="HTML"
    )


@menu_router.message(F.text == "🔍 Поиск")
async def search_menu(message: Message, state: FSMContext):
    """Search menu"""
    from ...states.user import UserStates

    await state.set_state(UserStates.search_query)

    await message.answer(
        "🔍 <b>Поиск товара</b>\n\n"
        "Введите название товара или вкуса:",
        parse_mode="HTML"
    )


@menu_router.message(F.text == "📌 Мои резервы")
async def my_reservations(message: Message, db: Database, user: User, state: FSMContext):
    """User's reservations"""
    await state.clear()

    reservations = await db.get_user_reservations(user.id)

    if not reservations:
        await message.answer(
            "📌 <b>Мои резервы</b>\n\n"
            "У вас нет активных резервов.",
            parse_mode="HTML"
        )
        return

    await message.answer(
        f"📌 <b>Мои резервы</b> ({len(reservations)})\n\n"
        "Выберите резерв для просмотра:",
        reply_markup=UserKeyboards.my_reservations(reservations),
        parse_mode="HTML"
    )


@menu_router.message(F.text == "📞 Контакты")
async def contacts(message: Message):
    """Show contacts"""
    await message.answer(
        "📞 <b>Контакты</b>\n\n"
        "Для связи с продавцом напишите администратору.\n\n"
        "Время работы: 10:00 - 22:00",
        parse_mode="HTML"
    )
