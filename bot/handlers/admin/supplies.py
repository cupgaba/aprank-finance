from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext

from ...database import Database
from ...database.models import User
from ...keyboards.admin import AdminKeyboards
from ...keyboards.common import CommonKeyboards
from ...states.admin import AdminStates
from ...services.logger import LoggerService
from ...utils.formatting import format_supply_item, format_price

supplies_router = Router()


@supplies_router.callback_query(F.data == "admin:supply:new")
async def new_supply_start(callback: CallbackQuery, db: Database, is_admin: bool, state: FSMContext):
    """Start new supply"""
    if not is_admin:
        await callback.answer("⛔️ Нет доступа", show_alert=True)
        return

    categories = await db.get_all_categories()

    if not categories:
        await callback.answer("❌ Сначала создайте категории и товары", show_alert=True)
        return

    await state.set_state(AdminStates.supply_select_category)
    await state.update_data(items=[])

    await callback.message.edit_text(
        "📥 <b>Новая закупка</b>\n\n"
        "Выберите категорию товара:",
        reply_markup=AdminKeyboards.select_category_for_product(categories),
        parse_mode="HTML"
    )


@supplies_router.callback_query(
    AdminStates.supply_select_category,
    F.data.startswith("admin:product:select_cat:")
)
async def supply_category_selected(callback: CallbackQuery, db: Database, state: FSMContext):
    """Category selected for supply"""
    category_id = int(callback.data.split(":")[-1])
    brands = await db.get_brands_by_category(category_id)

    if not brands:
        await callback.answer("❌ В этой категории нет брендов", show_alert=True)
        return

    await state.set_state(AdminStates.supply_select_brand)
    await state.update_data(category_id=category_id)

    await callback.message.edit_text(
        "📥 <b>Новая закупка</b>\n\n"
        "Выберите бренд:",
        reply_markup=AdminKeyboards.select_brand_for_product(brands),
        parse_mode="HTML"
    )


@supplies_router.callback_query(
    AdminStates.supply_select_brand,
    F.data.startswith("admin:product:select_brand:")
)
async def supply_brand_selected(callback: CallbackQuery, db: Database, state: FSMContext):
    """Brand selected for supply"""
    brand_id = int(callback.data.split(":")[-1])
    products = await db.get_products_by_brand(brand_id)

    if not products:
        await callback.answer("❌ В этом бренде нет товаров", show_alert=True)
        return

    await state.set_state(AdminStates.supply_select_product)
    await state.update_data(brand_id=brand_id)

    await callback.message.edit_text(
        "📥 <b>Новая закупка</b>\n\n"
        "Выберите товар:",
        reply_markup=AdminKeyboards.products_list(
            products,
            brand_id,
            action="supply",
            back_callback="admin:supply:cancel"
        ),
        parse_mode="HTML"
    )


@supplies_router.callback_query(
    AdminStates.supply_select_product,
    F.data.startswith("admin:product:supply:")
)
async def supply_product_selected(callback: CallbackQuery, db: Database, state: FSMContext):
    """Product selected for supply"""
    product_id = int(callback.data.split(":")[-1])
    product = await db.get_product_by_id(product_id)

    if not product:
        await callback.answer("❌ Товар не найден", show_alert=True)
        return

    await state.set_state(AdminStates.supply_enter_quantity)
    await state.update_data(current_product_id=product_id)

    await callback.message.edit_text(
        f"📥 <b>Закупка товара</b>\n\n"
        f"Товар: {product.full_name}\n"
        f"Текущий остаток: {product.quantity} шт.\n\n"
        f"Введите количество:",
        parse_mode="HTML"
    )


@supplies_router.message(AdminStates.supply_enter_quantity)
async def supply_quantity_entered(message: Message, db: Database, state: FSMContext):
    """Quantity entered for supply"""
    try:
        quantity = int(message.text.strip())
        if quantity <= 0:
            raise ValueError()
    except ValueError:
        await message.answer("❌ Введите корректное количество (целое положительное число):")
        return

    data = await state.get_data()
    product_id = data["current_product_id"]
    product = await db.get_product_by_id(product_id)

    await state.update_data(current_quantity=quantity)
    await state.set_state(AdminStates.supply_enter_price)

    await message.answer(
        f"📥 <b>Закупка товара</b>\n\n"
        f"Товар: {product.full_name}\n"
        f"Количество: {quantity} шт.\n\n"
        f"Введите цену закупки за единицу\n"
        f"(текущая: {product.purchase_price}₽):",
        reply_markup=CommonKeyboards.cancel(),
        parse_mode="HTML"
    )


@supplies_router.message(AdminStates.supply_enter_price)
async def supply_price_entered(message: Message, db: Database, state: FSMContext):
    """Price entered for supply"""
    try:
        price = float(message.text.strip().replace(",", ".").replace(" ", ""))
        if price < 0:
            raise ValueError()
    except ValueError:
        await message.answer("❌ Введите корректную цену:")
        return

    data = await state.get_data()
    items = data.get("items", [])
    product_id = data["current_product_id"]
    quantity = data["current_quantity"]

    # Add item to list
    items.append({
        "product_id": product_id,
        "quantity": quantity,
        "purchase_price": price
    })

    await state.update_data(items=items)
    await state.set_state(AdminStates.supply_add_more)

    # Show current items
    product = await db.get_product_by_id(product_id)
    items_text = ""
    total = 0
    for item in items:
        p = await db.get_product_by_id(item["product_id"])
        items_text += f"\n{format_supply_item(p, item['quantity'], item['purchase_price'])}"
        total += item["quantity"] * item["purchase_price"]

    await message.answer(
        f"📥 <b>Текущая закупка</b>\n"
        f"{items_text}\n\n"
        f"💰 Итого: {format_price(total)}\n\n"
        f"Добавить ещё товар или завершить?",
        reply_markup=AdminKeyboards.supply_add_more(),
        parse_mode="HTML"
    )


@supplies_router.callback_query(F.data == "admin:supply:add_item")
async def supply_add_more_item(callback: CallbackQuery, db: Database, is_admin: bool, state: FSMContext):
    """Add more items to supply"""
    if not is_admin:
        await callback.answer("⛔️ Нет доступа", show_alert=True)
        return

    categories = await db.get_all_categories()

    await state.set_state(AdminStates.supply_select_category)

    await callback.message.edit_text(
        "📥 <b>Добавление товара в закупку</b>\n\n"
        "Выберите категорию:",
        reply_markup=AdminKeyboards.select_category_for_product(categories),
        parse_mode="HTML"
    )


@supplies_router.callback_query(F.data == "admin:supply:finish")
async def supply_finish(callback: CallbackQuery, db: Database, user: User, bot: Bot, is_admin: bool, state: FSMContext):
    """Finish supply"""
    if not is_admin:
        await callback.answer("⛔️ Нет доступа", show_alert=True)
        return

    data = await state.get_data()
    items = data.get("items", [])

    if not items:
        await callback.answer("❌ Нет товаров для закупки", show_alert=True)
        return

    # Create supply
    supply = await db.create_supply(
        items=items,
        created_by_id=user.id
    )

    # Log supply
    logger = LoggerService(bot)
    await logger.log_supply(supply, user)

    await state.clear()

    # Format result
    items_text = ""
    for item in supply.items:
        items_text += f"\n• {item.product.name} x{item.quantity} по {item.purchase_price}₽"

    await callback.message.edit_text(
        f"✅ <b>Закупка создана!</b>\n"
        f"{items_text}\n\n"
        f"💰 Итого: {format_price(supply.total_amount)}",
        parse_mode="HTML"
    )

    await callback.message.answer(
        "Закупка успешно сохранена. Остатки товаров обновлены.",
        reply_markup=AdminKeyboards.main_menu()
    )


@supplies_router.callback_query(F.data == "admin:supply:cancel")
async def supply_cancel(callback: CallbackQuery, is_admin: bool, state: FSMContext):
    """Cancel supply"""
    if not is_admin:
        await callback.answer("⛔️ Нет доступа", show_alert=True)
        return

    await state.clear()
    await callback.message.edit_text(
        "📥 <b>Закупки</b>\n\n"
        "Закупка отменена. Выберите действие:",
        reply_markup=AdminKeyboards.supplies_menu(),
        parse_mode="HTML"
    )


@supplies_router.callback_query(F.data == "admin:supply:history")
async def supply_history(callback: CallbackQuery, db: Database, is_admin: bool):
    """Show supply history"""
    if not is_admin:
        await callback.answer("⛔️ Нет доступа", show_alert=True)
        return

    supplies = await db.get_supplies(limit=20)

    if not supplies:
        await callback.message.edit_text(
            "📥 <b>История закупок</b>\n\n"
            "Закупок пока не было.",
            reply_markup=AdminKeyboards.supplies_menu(),
            parse_mode="HTML"
        )
        return

    text = "📥 <b>История закупок</b>\n\n"
    for supply in supplies:
        date = supply.created_at.strftime("%d.%m.%Y %H:%M")
        items_count = len(supply.items)
        text += f"📦 {date} - {items_count} поз. - {format_price(supply.total_amount)}\n"

    await callback.message.edit_text(
        text,
        reply_markup=AdminKeyboards.supplies_menu(),
        parse_mode="HTML"
    )
