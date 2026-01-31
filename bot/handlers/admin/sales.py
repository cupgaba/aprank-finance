from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from datetime import datetime, timedelta

from ...database import Database
from ...database.models import User
from ...keyboards.admin import AdminKeyboards
from ...keyboards.common import CommonKeyboards
from ...states.admin import AdminStates
from ...services.logger import LoggerService
from ...services.channel import ChannelService
from ...utils.formatting import format_price

sales_router = Router()


@sales_router.callback_query(F.data == "admin:sale:new")
async def new_sale_start(callback: CallbackQuery, db: Database, is_admin: bool, state: FSMContext):
    """Start new sale"""
    if not is_admin:
        await callback.answer("⛔️ Нет доступа", show_alert=True)
        return

    categories = await db.get_all_categories()

    if not categories:
        await callback.answer("❌ Сначала создайте категории и товары", show_alert=True)
        return

    await state.set_state(AdminStates.sale_select_category)

    await callback.message.edit_text(
        "💰 <b>Новая продажа</b>\n\n"
        "Выберите категорию товара:",
        reply_markup=AdminKeyboards.select_category_for_product(categories),
        parse_mode="HTML"
    )


@sales_router.callback_query(
    AdminStates.sale_select_category,
    F.data.startswith("admin:product:select_cat:")
)
async def sale_category_selected(callback: CallbackQuery, db: Database, state: FSMContext):
    """Category selected for sale"""
    category_id = int(callback.data.split(":")[-1])
    brands = await db.get_brands_by_category(category_id)

    if not brands:
        await callback.answer("❌ В этой категории нет брендов", show_alert=True)
        return

    await state.set_state(AdminStates.sale_select_brand)

    await callback.message.edit_text(
        "💰 <b>Новая продажа</b>\n\n"
        "Выберите бренд:",
        reply_markup=AdminKeyboards.select_brand_for_product(brands),
        parse_mode="HTML"
    )


@sales_router.callback_query(
    AdminStates.sale_select_brand,
    F.data.startswith("admin:product:select_brand:")
)
async def sale_brand_selected(callback: CallbackQuery, db: Database, state: FSMContext):
    """Brand selected for sale"""
    brand_id = int(callback.data.split(":")[-1])
    products = await db.get_products_by_brand(brand_id, available_only=True)

    if not products:
        await callback.answer("❌ Нет товаров в наличии", show_alert=True)
        return

    # Filter only products with stock
    products = [p for p in products if p.quantity > 0]

    if not products:
        await callback.answer("❌ Нет товаров в наличии", show_alert=True)
        return

    await state.set_state(AdminStates.sale_select_product)

    await callback.message.edit_text(
        "💰 <b>Новая продажа</b>\n\n"
        "Выберите товар:",
        reply_markup=AdminKeyboards.products_list(
            products,
            brand_id,
            action="sell",
            back_callback="admin:sales_menu"
        ),
        parse_mode="HTML"
    )


@sales_router.callback_query(
    AdminStates.sale_select_product,
    F.data.startswith("admin:product:sell:")
)
async def sale_product_selected(callback: CallbackQuery, db: Database, state: FSMContext):
    """Product selected for sale"""
    product_id = int(callback.data.split(":")[-1])
    product = await db.get_product_by_id(product_id)

    if not product:
        await callback.answer("❌ Товар не найден", show_alert=True)
        return

    if product.quantity <= 0:
        await callback.answer("❌ Товар закончился", show_alert=True)
        return

    await state.update_data(product_id=product_id)

    await callback.message.edit_text(
        f"💰 <b>Продажа товара</b>\n\n"
        f"Товар: {product.full_name}\n"
        f"Цена: {format_price(product.sale_price)}\n"
        f"В наличии: {product.quantity} шт.\n\n"
        f"Выберите количество:",
        reply_markup=AdminKeyboards.sale_quantity(product_id, product.quantity),
        parse_mode="HTML"
    )


@sales_router.callback_query(F.data.startswith("admin:sale:qty:"))
async def sale_quantity_selected(
    callback: CallbackQuery,
    db: Database,
    user: User,
    bot: Bot,
    is_admin: bool,
    state: FSMContext
):
    """Quantity selected for sale - ask for price"""
    if not is_admin:
        await callback.answer("⛔️ Нет доступа", show_alert=True)
        return

    parts = callback.data.split(":")
    product_id = int(parts[-2])
    quantity = int(parts[-1])

    product = await db.get_product_by_id(product_id)

    if not product or product.quantity < quantity:
        await callback.answer("❌ Недостаточно товара", show_alert=True)
        return

    # Save data and ask for price
    await state.update_data(product_id=product_id, quantity=quantity)
    await state.set_state(AdminStates.sale_enter_price)

    await callback.message.edit_text(
        f"💰 <b>Продажа товара</b>\n\n"
        f"Товар: {product.full_name}\n"
        f"Количество: {quantity} шт.\n"
        f"Стандартная цена: {format_price(product.sale_price)}\n\n"
        f"Введите цену продажи (или отправьте <b>0</b> для стандартной цены):",
        parse_mode="HTML"
    )


@sales_router.message(AdminStates.sale_enter_price)
async def sale_price_entered(
    message: Message,
    db: Database,
    user: User,
    bot: Bot,
    state: FSMContext
):
    """Sale price entered"""
    data = await state.get_data()
    product_id = data["product_id"]
    quantity = data["quantity"]

    product = await db.get_product_by_id(product_id)

    if not product or product.quantity < quantity:
        await message.answer("❌ Недостаточно товара", reply_markup=AdminKeyboards.main_menu())
        await state.clear()
        return

    try:
        price_input = message.text.strip().replace(",", ".")
        sale_price = float(price_input)
        if sale_price < 0:
            raise ValueError()
        # If 0 entered, use default price
        if sale_price == 0:
            sale_price = product.sale_price
    except ValueError:
        await message.answer("❌ Введите корректную цену (число):")
        return

    # Create sale
    sale = await db.create_sale(
        product_id=product_id,
        quantity=quantity,
        sale_price=sale_price,
        sold_by_id=user.id
    )

    if not sale:
        await message.answer("❌ Ошибка при создании продажи", reply_markup=AdminKeyboards.main_menu())
        await state.clear()
        return

    # Log sale
    logger = LoggerService(bot)
    await logger.log_sale(sale, user)

    # Mark as sold in channel if product is out of stock
    if product.quantity - quantity <= 0:
        channel_service = ChannelService(bot, db)
        await channel_service.mark_product_sold(product_id)

    await state.clear()

    await message.answer(
        f"✅ <b>Продажа оформлена!</b>\n\n"
        f"Товар: {product.full_name}\n"
        f"Количество: {quantity} шт.\n"
        f"Цена за шт.: {format_price(sale.sale_price)}\n"
        f"Сумма: {format_price(sale.sale_price * quantity)}\n"
        f"Прибыль: {format_price(sale.profit)}",
        reply_markup=AdminKeyboards.main_menu(),
        parse_mode="HTML"
    )


@sales_router.callback_query(F.data.startswith("admin:sale:qty_custom:"))
async def sale_custom_quantity(callback: CallbackQuery, db: Database, is_admin: bool, state: FSMContext):
    """Custom quantity for sale"""
    if not is_admin:
        await callback.answer("⛔️ Нет доступа", show_alert=True)
        return

    product_id = int(callback.data.split(":")[-1])
    product = await db.get_product_by_id(product_id)

    if not product:
        await callback.answer("❌ Товар не найден", show_alert=True)
        return

    await state.set_state(AdminStates.sale_enter_quantity)
    await state.update_data(product_id=product_id)

    await callback.message.edit_text(
        f"💰 <b>Продажа товара</b>\n\n"
        f"Товар: {product.full_name}\n"
        f"В наличии: {product.quantity} шт.\n\n"
        f"Введите количество:",
        parse_mode="HTML"
    )


@sales_router.message(AdminStates.sale_enter_quantity)
async def sale_quantity_entered(
    message: Message,
    db: Database,
    user: User,
    bot: Bot,
    state: FSMContext
):
    """Custom quantity entered - ask for price"""
    try:
        quantity = int(message.text.strip())
        if quantity <= 0:
            raise ValueError()
    except ValueError:
        await message.answer("❌ Введите корректное количество:")
        return

    data = await state.get_data()
    product_id = data["product_id"]
    product = await db.get_product_by_id(product_id)

    if not product or product.quantity < quantity:
        await message.answer(f"❌ Недостаточно товара. В наличии: {product.quantity} шт.")
        return

    # Save data and ask for price
    await state.update_data(quantity=quantity)
    await state.set_state(AdminStates.sale_enter_price)

    await message.answer(
        f"💰 <b>Продажа товара</b>\n\n"
        f"Товар: {product.full_name}\n"
        f"Количество: {quantity} шт.\n"
        f"Стандартная цена: {format_price(product.sale_price)}\n\n"
        f"Введите цену продажи (или отправьте <b>0</b> для стандартной цены):",
        parse_mode="HTML"
    )


@sales_router.callback_query(F.data.startswith("admin:product:sell:"))
async def quick_sell_product(callback: CallbackQuery, db: Database, is_admin: bool, state: FSMContext):
    """Quick sell from product view"""
    if not is_admin:
        await callback.answer("⛔️ Нет доступа", show_alert=True)
        return

    product_id = int(callback.data.split(":")[-1])
    product = await db.get_product_by_id(product_id)

    if not product:
        await callback.answer("❌ Товар не найден", show_alert=True)
        return

    if product.quantity <= 0:
        await callback.answer("❌ Товар закончился", show_alert=True)
        return

    await state.update_data(product_id=product_id)

    await callback.message.edit_text(
        f"💰 <b>Продажа товара</b>\n\n"
        f"Товар: {product.full_name}\n"
        f"Цена: {format_price(product.sale_price)}\n"
        f"В наличии: {product.quantity} шт.\n\n"
        f"Выберите количество:",
        reply_markup=AdminKeyboards.sale_quantity(product_id, product.quantity),
        parse_mode="HTML"
    )


@sales_router.callback_query(F.data == "admin:sale:today")
async def today_sales(callback: CallbackQuery, db: Database, is_admin: bool):
    """Show today's sales"""
    if not is_admin:
        await callback.answer("⛔️ Нет доступа", show_alert=True)
        return

    sales = await db.get_today_sales()

    if not sales:
        await callback.message.edit_text(
            "💰 <b>Продажи за сегодня</b>\n\n"
            "Сегодня продаж не было.",
            reply_markup=AdminKeyboards.sales_menu(),
            parse_mode="HTML"
        )
        return

    text = "💰 <b>Продажи за сегодня</b>\n\n"
    total_revenue = 0
    total_profit = 0

    for sale in sales:
        time = sale.sold_at.strftime("%H:%M")
        text += f"• {time} - {sale.product.name} x{sale.quantity} - {format_price(sale.sale_price * sale.quantity)}\n"
        total_revenue += sale.sale_price * sale.quantity
        total_profit += sale.profit

    text += f"\n📊 Выручка: {format_price(total_revenue)}"
    text += f"\n📈 Прибыль: {format_price(total_profit)}"

    await callback.message.edit_text(
        text,
        reply_markup=AdminKeyboards.sales_menu(),
        parse_mode="HTML"
    )


@sales_router.callback_query(F.data == "admin:sale:history")
async def sales_history(callback: CallbackQuery, db: Database, is_admin: bool):
    """Show sales history"""
    if not is_admin:
        await callback.answer("⛔️ Нет доступа", show_alert=True)
        return

    # Get sales for last 7 days
    start_date = datetime.utcnow() - timedelta(days=7)
    sales = await db.get_sales_by_period(start_date)

    if not sales:
        await callback.message.edit_text(
            "💰 <b>История продаж</b>\n\n"
            "За последние 7 дней продаж не было.",
            reply_markup=AdminKeyboards.sales_menu(),
            parse_mode="HTML"
        )
        return

    text = "💰 <b>История продаж (7 дней)</b>\n\n"

    # Group by date
    by_date = {}
    for sale in sales:
        date_key = sale.sold_at.strftime("%d.%m.%Y")
        if date_key not in by_date:
            by_date[date_key] = {"sales": [], "revenue": 0, "profit": 0}
        by_date[date_key]["sales"].append(sale)
        by_date[date_key]["revenue"] += sale.sale_price * sale.quantity
        by_date[date_key]["profit"] += sale.profit

    for date, data in sorted(by_date.items(), reverse=True):
        text += f"📅 <b>{date}</b>\n"
        text += f"   Продаж: {len(data['sales'])}, Выручка: {format_price(data['revenue'])}\n\n"

    await callback.message.edit_text(
        text,
        reply_markup=AdminKeyboards.sales_menu(),
        parse_mode="HTML"
    )
