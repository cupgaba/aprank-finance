from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext

from ...database import Database
from ...database.models import User
from ...keyboards.admin import AdminKeyboards
from ...keyboards.common import CommonKeyboards
from ...states.admin import AdminStates
from ...services.logger import LoggerService

categories_router = Router()


@categories_router.callback_query(F.data == "admin:categories")
async def list_categories(callback: CallbackQuery, db: Database, is_admin: bool):
    """List all categories"""
    if not is_admin:
        await callback.answer("⛔️ Нет доступа", show_alert=True)
        return

    categories = await db.get_all_categories()

    if not categories:
        await callback.message.edit_text(
            "📁 <b>Категории</b>\n\n"
            "Категории пока не добавлены.",
            reply_markup=AdminKeyboards.categories_list([]),
            parse_mode="HTML"
        )
    else:
        await callback.message.edit_text(
            "📁 <b>Категории</b>\n\n"
            "Выберите категорию:",
            reply_markup=AdminKeyboards.categories_list(categories),
            parse_mode="HTML"
        )


@categories_router.callback_query(F.data == "admin:add_category")
async def add_category_start(callback: CallbackQuery, is_admin: bool, state: FSMContext):
    """Start adding category"""
    if not is_admin:
        await callback.answer("⛔️ Нет доступа", show_alert=True)
        return

    await state.set_state(AdminStates.add_category_name)
    await callback.message.edit_text(
        "📁 <b>Добавление категории</b>\n\n"
        "Введите название категории:",
        parse_mode="HTML"
    )
    await callback.message.answer(
        "Ожидаю название...",
        reply_markup=CommonKeyboards.cancel()
    )


@categories_router.message(AdminStates.add_category_name)
async def add_category_name(message: Message, db: Database, state: FSMContext):
    """Process category name"""
    name = message.text.strip()

    if len(name) < 2:
        await message.answer("❌ Название должно быть не менее 2 символов. Попробуйте снова:")
        return

    # Create category
    category = await db.create_category(name=name)

    await state.clear()
    await message.answer(
        f"✅ Категория <b>{category.name}</b> успешно создана!",
        reply_markup=AdminKeyboards.main_menu(),
        parse_mode="HTML"
    )

    # Return to categories list
    categories = await db.get_all_categories()
    await message.answer(
        "📁 <b>Категории</b>\n\n"
        "Выберите категорию:",
        reply_markup=AdminKeyboards.categories_list(categories),
        parse_mode="HTML"
    )


@categories_router.callback_query(F.data.startswith("admin:category:view:"))
async def view_category(callback: CallbackQuery, db: Database, is_admin: bool):
    """View category details"""
    if not is_admin:
        await callback.answer("⛔️ Нет доступа", show_alert=True)
        return

    category_id = int(callback.data.split(":")[-1])
    category = await db.get_category_by_id(category_id)

    if not category:
        await callback.answer("❌ Категория не найдена", show_alert=True)
        return

    brands = await db.get_brands_by_category(category_id)

    # Build brands list with product counts
    brands_text = ""
    if brands:
        for brand in brands:
            products = await db.get_products_by_brand(brand.id)
            in_stock = sum(1 for p in products if p.quantity > 0)
            brands_text += f"  🏷 {brand.name} ({in_stock} в наличии)\n"
    else:
        brands_text = "  Бренды не добавлены\n"

    await callback.message.edit_text(
        f"📁 <b>{category.name}</b>\n\n"
        f"<b>Бренды:</b>\n{brands_text}"
        f"{f'📝 {category.description}' if category.description else ''}\n"
        f"Выберите действие:",
        reply_markup=AdminKeyboards.category_actions(category_id),
        parse_mode="HTML"
    )


@categories_router.callback_query(F.data.startswith("admin:category:brands:"))
async def category_brands(callback: CallbackQuery, db: Database, is_admin: bool):
    """List brands in category"""
    if not is_admin:
        await callback.answer("⛔️ Нет доступа", show_alert=True)
        return

    category_id = int(callback.data.split(":")[-1])
    category = await db.get_category_by_id(category_id)

    if not category:
        await callback.answer("❌ Категория не найдена", show_alert=True)
        return

    brands = await db.get_brands_by_category(category_id)

    await callback.message.edit_text(
        f"📁 <b>{category.name}</b> → Бренды\n\n"
        f"{'Выберите бренд:' if brands else 'Бренды не добавлены.'}",
        reply_markup=AdminKeyboards.brands_list(brands, category_id),
        parse_mode="HTML"
    )


@categories_router.callback_query(F.data.startswith("admin:category:edit:"))
async def edit_category_start(callback: CallbackQuery, db: Database, is_admin: bool, state: FSMContext):
    """Start editing category"""
    if not is_admin:
        await callback.answer("⛔️ Нет доступа", show_alert=True)
        return

    category_id = int(callback.data.split(":")[-1])
    category = await db.get_category_by_id(category_id)

    if not category:
        await callback.answer("❌ Категория не найдена", show_alert=True)
        return

    await state.set_state(AdminStates.edit_category_name)
    await state.update_data(category_id=category_id)

    await callback.message.edit_text(
        f"✏️ <b>Редактирование категории</b>\n\n"
        f"Текущее название: {category.name}\n\n"
        f"Введите новое название:",
        parse_mode="HTML"
    )


@categories_router.message(AdminStates.edit_category_name)
async def edit_category_name(message: Message, db: Database, state: FSMContext):
    """Process new category name"""
    data = await state.get_data()
    category_id = data.get("category_id")

    name = message.text.strip()
    if len(name) < 2:
        await message.answer("❌ Название должно быть не менее 2 символов. Попробуйте снова:")
        return

    category = await db.update_category(category_id, name=name)

    await state.clear()
    await message.answer(
        f"✅ Категория переименована в <b>{category.name}</b>!",
        reply_markup=AdminKeyboards.main_menu(),
        parse_mode="HTML"
    )


@categories_router.callback_query(F.data.startswith("admin:category:delete:"))
async def delete_category(callback: CallbackQuery, db: Database, is_admin: bool):
    """Delete category"""
    if not is_admin:
        await callback.answer("⛔️ Нет доступа", show_alert=True)
        return

    category_id = int(callback.data.split(":")[-1])
    category = await db.get_category_by_id(category_id)

    if not category:
        await callback.answer("❌ Категория не найдена", show_alert=True)
        return

    # Check if category has brands
    brands = await db.get_brands_by_category(category_id)
    if brands:
        await callback.answer(
            "❌ Нельзя удалить категорию с брендами. Сначала удалите бренды.",
            show_alert=True
        )
        return

    await db.delete_category(category_id)

    await callback.answer("✅ Категория удалена")

    # Return to categories list
    categories = await db.get_all_categories()
    await callback.message.edit_text(
        "📁 <b>Категории</b>\n\n"
        "Выберите категорию:",
        reply_markup=AdminKeyboards.categories_list(categories),
        parse_mode="HTML"
    )
