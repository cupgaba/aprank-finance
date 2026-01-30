from aiogram import Router, F
from aiogram.types import Message
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext

from ..database import Database
from ..database.models import User
from ..keyboards.admin import AdminKeyboards
from ..keyboards.user import UserKeyboards

common_router = Router()


@common_router.message(CommandStart())
async def cmd_start(
    message: Message,
    db: Database,
    user: User,
    is_admin: bool,
    state: FSMContext
):
    """Handle /start command"""
    await state.clear()

    if is_admin:
        await message.answer(
            f"👋 Привет, {user.full_name}!\n\n"
            f"Вы авторизованы как <b>администратор</b>.\n"
            f"Используйте меню ниже для управления.",
            reply_markup=AdminKeyboards.main_menu(),
            parse_mode="HTML"
        )
    else:
        await message.answer(
            f"👋 Привет, {user.full_name}!\n\n"
            f"Добро пожаловать! Используйте меню для просмотра товаров.",
            reply_markup=UserKeyboards.main_menu(),
            parse_mode="HTML"
        )


@common_router.message(Command("admin"))
async def cmd_admin(
    message: Message,
    user: User,
    is_admin: bool,
    state: FSMContext
):
    """Handle /admin command"""
    await state.clear()

    if not is_admin:
        await message.answer("⛔️ У вас нет доступа к админ-панели.")
        return

    await message.answer(
        "🔐 <b>Админ-панель</b>\n\n"
        "Выберите раздел:",
        reply_markup=AdminKeyboards.main_menu(),
        parse_mode="HTML"
    )


@common_router.message(Command("cancel"))
@common_router.message(F.text == "❌ Отмена")
async def cmd_cancel(
    message: Message,
    user: User,
    is_admin: bool,
    state: FSMContext
):
    """Handle cancel command"""
    await state.clear()

    if is_admin:
        await message.answer(
            "Действие отменено.",
            reply_markup=AdminKeyboards.main_menu()
        )
    else:
        await message.answer(
            "Действие отменено.",
            reply_markup=UserKeyboards.main_menu()
        )


@common_router.message(Command("help"))
async def cmd_help(message: Message, is_admin: bool):
    """Handle /help command"""
    if is_admin:
        text = (
            "📖 <b>Справка для администратора</b>\n\n"
            "<b>Команды:</b>\n"
            "/start - Главное меню\n"
            "/admin - Админ-панель\n"
            "/cancel - Отмена действия\n\n"
            "<b>Разделы:</b>\n"
            "📦 Товары - управление каталогом\n"
            "📊 Статистика - отчёты и аналитика\n"
            "📥 Закупки - приём товара\n"
            "💰 Продажи - учёт продаж\n"
            "📤 Списания - списание товара\n"
            "📢 Публикации - публикации в канал\n"
            "🔔 Резервы - управление резервами\n"
            "⚙️ Настройки - настройки бота"
        )
    else:
        text = (
            "📖 <b>Справка</b>\n\n"
            "<b>Команды:</b>\n"
            "/start - Главное меню\n"
            "/cancel - Отмена действия\n\n"
            "<b>Возможности:</b>\n"
            "📋 Прайс-лист - просмотр товаров и цен\n"
            "🔍 Поиск - поиск товаров\n"
            "📌 Резерв - резервирование товара\n"
            "📞 Контакты - связь с продавцом"
        )

    await message.answer(text, parse_mode="HTML")
