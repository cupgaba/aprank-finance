from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext

from ...database import Database
from ...database.models import User
from ...keyboards.admin import AdminKeyboards
from ...keyboards.common import CommonKeyboards
from ...states.admin import AdminStates

brands_router = Router()


@brands_router.callback_query(F.data == "admin:brands")
async def list_all_brands(callback: CallbackQuery, db: Database, is_admin: bool):
    """List all brands"""
    if not is_admin:
        await callback.answer("⛔️ Нет доступа", show_alert=True)
        return

    brands = await db.get_all_brands()

    if not brands:
        await callback.message.edit_text(
            "🏷 <b>Бренды</b>\n\n"
            "Бренды пока не добавлены.\n"
            "Сначала создайте категорию, затем добавьте бренд.",
            reply_markup=AdminKeyboards.brands_list([]),
            parse_mode="HTML"
        )
    else:
        await callback.message.edit_text(
            "🏷 <b>Бренды</b>\n\n"
            "Выберите бренд:",
            reply_markup=AdminKeyboards.brands_list(brands),
            parse_mode="HTML"
        )


@brands_router.callback_query(F.data.startswith("admin:add_brand:"))
async def add_brand_start(callback: CallbackQuery, db: Database, is_admin: bool, state: FSMContext):
    """Start adding brand to category"""
    if not is_admin:
        await callback.answer("⛔️ Нет доступа", show_alert=True)
        return

    category_id = int(callback.data.split(":")[-1])
    category = await db.get_category_by_id(category_id)

    if not category:
        await callback.answer("❌ Категория не найдена", show_alert=True)
        return

    await state.set_state(AdminStates.add_brand_name)
    await state.update_data(category_id=category_id)

    await callback.message.edit_text(
        f"🏷 <b>Добавление бренда</b>\n\n"
        f"Категория: {category.name}\n\n"
        f"Введите название бренда:",
        parse_mode="HTML"
    )
    await callback.message.answer(
        "Ожидаю название...",
        reply_markup=CommonKeyboards.cancel()
    )


@brands_router.message(AdminStates.add_brand_name)
async def add_brand_name(message: Message, db: Database, state: FSMContext):
    """Process brand name"""
    data = await state.get_data()
    category_id = data.get("category_id")

    name = message.text.strip()
    if len(name) < 2:
        await message.answer("❌ Название должно быть не менее 2 символов. Попробуйте снова:")
        return

    brand = await db.create_brand(category_id=category_id, name=name)
    category = await db.get_category_by_id(category_id)

    await state.clear()
    await message.answer(
        f"✅ Бренд <b>{brand.name}</b> успешно создан!",
        reply_markup=AdminKeyboards.main_menu(),
        parse_mode="HTML"
    )

    # Return to brands list
    brands = await db.get_brands_by_category(category_id)
    await message.answer(
        f"📁 <b>{category.name}</b> → Бренды\n\n"
        f"Выберите бренд:",
        reply_markup=AdminKeyboards.brands_list(brands, category_id),
        parse_mode="HTML"
    )


@brands_router.callback_query(F.data.startswith("admin:brand:view:"))
async def view_brand(callback: CallbackQuery, db: Database, is_admin: bool):
    """View brand details"""
    if not is_admin:
        await callback.answer("⛔️ Нет доступа", show_alert=True)
        return

    brand_id = int(callback.data.split(":")[-1])
    brand = await db.get_brand_by_id(brand_id)

    if not brand:
        await callback.answer("❌ Бренд не найден", show_alert=True)
        return

    products = await db.get_products_by_brand(brand_id)

    # Build products list
    products_text = ""
    if products:
        for p in products:
            status = "✅" if p.quantity > 0 else "❌"
            products_text += f"  {status} {p.name} ({p.quantity} шт.) - закуп. {p.purchase_price}₽\n"
    else:
        products_text = "  Товары не добавлены\n"

    await callback.message.edit_text(
        f"🏷 <b>{brand.name}</b>\n\n"
        f"📁 Категория: {brand.category.name}\n\n"
        f"<b>Товары:</b>\n{products_text}"
        f"{f'📝 {brand.description}' if brand.description else ''}\n"
        f"Выберите действие:",
        reply_markup=AdminKeyboards.brand_actions(brand_id, brand.category_id),
        parse_mode="HTML"
    )


@brands_router.callback_query(F.data.startswith("admin:brand:products:"))
async def brand_products(callback: CallbackQuery, db: Database, is_admin: bool):
    """List products in brand"""
    if not is_admin:
        await callback.answer("⛔️ Нет доступа", show_alert=True)
        return

    brand_id = int(callback.data.split(":")[-1])
    brand = await db.get_brand_by_id(brand_id)

    if not brand:
        await callback.answer("❌ Бренд не найден", show_alert=True)
        return

    products = await db.get_products_by_brand(brand_id)

    await callback.message.edit_text(
        f"🏷 <b>{brand.name}</b> → Товары\n\n"
        f"{'Выберите товар:' if products else 'Товары не добавлены.'}",
        reply_markup=AdminKeyboards.products_list(
            products,
            brand_id,
            back_callback=f"admin:brand:view:{brand_id}"
        ),
        parse_mode="HTML"
    )


@brands_router.callback_query(F.data.startswith("admin:brand:edit:"))
async def edit_brand_start(callback: CallbackQuery, db: Database, is_admin: bool, state: FSMContext):
    """Start editing brand"""
    if not is_admin:
        await callback.answer("⛔️ Нет доступа", show_alert=True)
        return

    brand_id = int(callback.data.split(":")[-1])
    brand = await db.get_brand_by_id(brand_id)

    if not brand:
        await callback.answer("❌ Бренд не найден", show_alert=True)
        return

    await state.set_state(AdminStates.edit_brand_name)
    await state.update_data(brand_id=brand_id)

    await callback.message.edit_text(
        f"✏️ <b>Редактирование бренда</b>\n\n"
        f"Текущее название: {brand.name}\n\n"
        f"Введите новое название:",
        parse_mode="HTML"
    )


@brands_router.message(AdminStates.edit_brand_name)
async def edit_brand_name(message: Message, db: Database, state: FSMContext):
    """Process new brand name"""
    data = await state.get_data()
    brand_id = data.get("brand_id")

    name = message.text.strip()
    if len(name) < 2:
        await message.answer("❌ Название должно быть не менее 2 символов. Попробуйте снова:")
        return

    brand = await db.update_brand(brand_id, name=name)

    await state.clear()
    await message.answer(
        f"✅ Бренд переименован в <b>{brand.name}</b>!",
        reply_markup=AdminKeyboards.main_menu(),
        parse_mode="HTML"
    )


@brands_router.callback_query(F.data.startswith("admin:brand:delete:"))
async def delete_brand(callback: CallbackQuery, db: Database, is_admin: bool):
    """Delete brand"""
    if not is_admin:
        await callback.answer("⛔️ Нет доступа", show_alert=True)
        return

    brand_id = int(callback.data.split(":")[-1])
    brand = await db.get_brand_by_id(brand_id)

    if not brand:
        await callback.answer("❌ Бренд не найден", show_alert=True)
        return

    # Check if brand has products
    products = await db.get_products_by_brand(brand_id)
    if products:
        await callback.answer(
            "❌ Нельзя удалить бренд с товарами. Сначала удалите товары.",
            show_alert=True
        )
        return

    category_id = brand.category_id
    await db.delete_brand(brand_id)

    await callback.answer("✅ Бренд удален")

    # Return to category brands list
    brands = await db.get_brands_by_category(category_id)
    category = await db.get_category_by_id(category_id)

    await callback.message.edit_text(
        f"📁 <b>{category.name}</b> → Бренды\n\n"
        f"{'Выберите бренд:' if brands else 'Бренды не добавлены.'}",
        reply_markup=AdminKeyboards.brands_list(brands, category_id),
        parse_mode="HTML"
    )


@brands_router.callback_query(F.data.startswith("admin:brand:select_cat:"))
async def brand_select_category(callback: CallbackQuery, db: Database, is_admin: bool, state: FSMContext):
    """Category selected for new brand"""
    if not is_admin:
        await callback.answer("⛔️ Нет доступа", show_alert=True)
        return

    category_id = int(callback.data.split(":")[-1])
    category = await db.get_category_by_id(category_id)

    if not category:
        await callback.answer("❌ Категория не найдена", show_alert=True)
        return

    await state.set_state(AdminStates.add_brand_name)
    await state.update_data(category_id=category_id)

    await callback.message.edit_text(
        f"🏷 <b>Добавление бренда</b>\n\n"
        f"Категория: {category.name}\n\n"
        f"Введите название бренда:",
        parse_mode="HTML"
    )
