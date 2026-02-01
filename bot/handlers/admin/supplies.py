from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext

from ...database import Database
from ...database.models import User
from ...keyboards.admin import AdminKeyboards
from ...keyboards.common import CommonKeyboards
from ...states.admin import AdminStates
from ...services.logger import LoggerService
from ...utils.formatting import format_price

supplies_router = Router()


def format_cart(items: list, delivery: float = 0, expenses: float = 0) -> str:
    """Format cart contents for display"""
    if not items:
        return "🛒 <b>Корзина пуста</b>\n\nДобавьте товары в закупку."

    text = "🛒 <b>Корзина закупки</b>\n\n"

    products_total = 0
    for item in items:
        subtotal = item["quantity"] * item["purchase_price"]
        products_total += subtotal
        text += f"• {item['name']} x{item['quantity']} по {item['purchase_price']}₽ = {format_price(subtotal)}\n"
        text += f"  └ Продажа: {item['sale_price']}₽\n"

    text += f"\n📦 Товары: {format_price(products_total)}"

    if delivery > 0:
        text += f"\n🚚 Доставка: {format_price(delivery)}"

    if expenses > 0:
        text += f"\n📋 Расходы: {format_price(expenses)}"

    total = products_total + delivery + expenses
    text += f"\n\n💰 <b>ИТОГО: {format_price(total)}</b>"

    return text


@supplies_router.callback_query(F.data == "admin:supply:new")
async def new_supply_start(callback: CallbackQuery, db: Database, is_admin: bool, state: FSMContext):
    """Start new supply"""
    if not is_admin:
        await callback.answer("⛔️ Нет доступа", show_alert=True)
        return

    # Initialize empty cart
    await state.update_data(
        supply_items=[],
        supply_delivery=0,
        supply_expenses=0
    )

    await callback.message.edit_text(
        format_cart([]),
        reply_markup=AdminKeyboards.supply_cart(has_items=False),
        parse_mode="HTML"
    )


@supplies_router.callback_query(F.data == "admin:supply:add_item")
async def supply_add_item(callback: CallbackQuery, db: Database, is_admin: bool, state: FSMContext):
    """Add items to supply - select category"""
    if not is_admin:
        await callback.answer("⛔️ Нет доступа", show_alert=True)
        return

    categories = await db.get_all_categories()

    if not categories:
        await callback.answer("❌ Сначала создайте категории", show_alert=True)
        return

    await callback.message.edit_text(
        "📥 <b>Добавление товаров в закупку</b>\n\n"
        "Выберите категорию:",
        reply_markup=AdminKeyboards.select_category_for_supply(categories),
        parse_mode="HTML"
    )


@supplies_router.callback_query(F.data.startswith("admin:supply:select_cat:"))
async def supply_category_selected(callback: CallbackQuery, db: Database, is_admin: bool, state: FSMContext):
    """Category selected for supply"""
    if not is_admin:
        await callback.answer("⛔️ Нет доступа", show_alert=True)
        return

    category_id = int(callback.data.split(":")[-1])
    brands = await db.get_brands_by_category(category_id)

    if not brands:
        await callback.answer("❌ В этой категории нет брендов", show_alert=True)
        return

    await state.update_data(supply_category_id=category_id)

    await callback.message.edit_text(
        "📥 <b>Добавление товаров в закупку</b>\n\n"
        "Выберите бренд:",
        reply_markup=AdminKeyboards.select_brand_for_supply(brands, category_id),
        parse_mode="HTML"
    )


@supplies_router.callback_query(F.data.startswith("admin:supply:select_brand:"))
async def supply_brand_selected(callback: CallbackQuery, db: Database, is_admin: bool, state: FSMContext):
    """Brand selected - ask for products list"""
    if not is_admin:
        await callback.answer("⛔️ Нет доступа", show_alert=True)
        return

    brand_id = int(callback.data.split(":")[-1])
    brand = await db.get_brand_by_id(brand_id)

    if not brand:
        await callback.answer("❌ Бренд не найден", show_alert=True)
        return

    await state.set_state(AdminStates.supply_enter_products)
    await state.update_data(supply_brand_id=brand_id)

    await callback.message.edit_text(
        f"📥 <b>Добавление товаров в {brand.name}</b>\n\n"
        f"Введите товары списком в формате:\n"
        f"<code>название | закупка | продажа | кол-во</code>\n\n"
        f"<b>Пример:</b>\n"
        f"<code>Красная смородина | 140 | 250 | 5\n"
        f"Кислое мороженое | 150 | 280 | 3\n"
        f"Манго | 140 | 250 | 10</code>\n\n"
        f"Каждый товар с новой строки!",
        parse_mode="HTML"
    )
    await callback.message.answer(
        "Ожидаю список товаров...",
        reply_markup=CommonKeyboards.cancel()
    )


@supplies_router.message(AdminStates.supply_enter_products)
async def supply_products_entered(message: Message, db: Database, state: FSMContext):
    """Process products list for supply"""
    data = await state.get_data()
    brand_id = data.get("supply_brand_id")
    items = data.get("supply_items", [])

    brand = await db.get_brand_by_id(brand_id)

    lines = message.text.strip().split("\n")
    added = 0
    errors = []

    for line in lines:
        line = line.strip()
        if not line:
            continue

        # Parse: name | purchase | sale | quantity
        parts = [p.strip() for p in line.split("|")]

        if len(parts) < 4:
            # Try simpler format: name quantity (use existing prices)
            simple_parts = line.rsplit(maxsplit=1)
            if len(simple_parts) == 2:
                try:
                    name = simple_parts[0].strip()
                    qty = int(simple_parts[1])
                    # Need purchase and sale prices
                    errors.append(f"❌ '{name}' - укажите цены в формате: название | закупка | продажа | кол-во")
                    continue
                except ValueError:
                    pass
            errors.append(f"❌ '{line}' - неверный формат")
            continue

        try:
            name = parts[0].strip()
            purchase_price = float(parts[1].replace(",", ".").replace(" ", ""))
            sale_price = float(parts[2].replace(",", ".").replace(" ", ""))
            quantity = int(parts[3])

            if len(name) < 2:
                errors.append(f"❌ '{name}' - название слишком короткое")
                continue

            if purchase_price < 0 or sale_price < 0 or quantity <= 0:
                errors.append(f"❌ '{name}' - некорректные значения")
                continue

            items.append({
                "brand_id": brand_id,
                "brand_name": brand.name,
                "name": name,
                "purchase_price": purchase_price,
                "sale_price": sale_price,
                "quantity": quantity
            })
            added += 1

        except (ValueError, IndexError) as e:
            errors.append(f"❌ '{line}' - ошибка парсинга")
            continue

    await state.update_data(supply_items=items)
    await state.set_state(None)

    # Build response
    result = ""
    if added > 0:
        result = f"✅ Добавлено товаров: {added}\n\n"

    if errors:
        result += "⚠️ <b>Ошибки:</b>\n" + "\n".join(errors[:5]) + "\n\n"

    delivery = data.get("supply_delivery", 0)
    expenses = data.get("supply_expenses", 0)

    await message.answer(
        result + format_cart(items, delivery, expenses),
        reply_markup=AdminKeyboards.supply_cart(
            has_items=len(items) > 0,
            delivery=delivery,
            expenses=expenses
        ),
        parse_mode="HTML"
    )


@supplies_router.callback_query(F.data == "admin:supply:delivery")
async def supply_set_delivery(callback: CallbackQuery, is_admin: bool, state: FSMContext):
    """Set delivery cost"""
    if not is_admin:
        await callback.answer("⛔️ Нет доступа", show_alert=True)
        return

    await state.set_state(AdminStates.supply_enter_delivery)

    await callback.message.edit_text(
        "🚚 <b>Стоимость доставки</b>\n\n"
        "Введите стоимость доставки (или 0 если бесплатно):",
        parse_mode="HTML"
    )


@supplies_router.message(AdminStates.supply_enter_delivery)
async def supply_delivery_entered(message: Message, state: FSMContext):
    """Process delivery cost"""
    try:
        delivery = float(message.text.strip().replace(",", ".").replace(" ", ""))
        if delivery < 0:
            raise ValueError()
    except ValueError:
        await message.answer("❌ Введите корректную сумму:")
        return

    data = await state.get_data()
    items = data.get("supply_items", [])
    expenses = data.get("supply_expenses", 0)

    await state.update_data(supply_delivery=delivery)
    await state.set_state(None)

    await message.answer(
        f"✅ Доставка: {format_price(delivery)}\n\n" + format_cart(items, delivery, expenses),
        reply_markup=AdminKeyboards.supply_cart(
            has_items=len(items) > 0,
            delivery=delivery,
            expenses=expenses
        ),
        parse_mode="HTML"
    )


@supplies_router.callback_query(F.data == "admin:supply:expenses")
async def supply_set_expenses(callback: CallbackQuery, is_admin: bool, state: FSMContext):
    """Set additional expenses"""
    if not is_admin:
        await callback.answer("⛔️ Нет доступа", show_alert=True)
        return

    await state.set_state(AdminStates.supply_enter_expenses)

    await callback.message.edit_text(
        "📋 <b>Дополнительные расходы</b>\n\n"
        "Введите сумму дополнительных расходов (или 0 если нет):",
        parse_mode="HTML"
    )


@supplies_router.message(AdminStates.supply_enter_expenses)
async def supply_expenses_entered(message: Message, state: FSMContext):
    """Process additional expenses"""
    try:
        expenses = float(message.text.strip().replace(",", ".").replace(" ", ""))
        if expenses < 0:
            raise ValueError()
    except ValueError:
        await message.answer("❌ Введите корректную сумму:")
        return

    data = await state.get_data()
    items = data.get("supply_items", [])
    delivery = data.get("supply_delivery", 0)

    await state.update_data(supply_expenses=expenses)
    await state.set_state(None)

    await message.answer(
        f"✅ Расходы: {format_price(expenses)}\n\n" + format_cart(items, delivery, expenses),
        reply_markup=AdminKeyboards.supply_cart(
            has_items=len(items) > 0,
            delivery=delivery,
            expenses=expenses
        ),
        parse_mode="HTML"
    )


@supplies_router.callback_query(F.data == "admin:supply:finish")
async def supply_finish(callback: CallbackQuery, is_admin: bool, state: FSMContext):
    """Show supply summary for confirmation"""
    if not is_admin:
        await callback.answer("⛔️ Нет доступа", show_alert=True)
        return

    data = await state.get_data()
    items = data.get("supply_items", [])
    delivery = data.get("supply_delivery", 0)
    expenses = data.get("supply_expenses", 0)

    if not items:
        await callback.answer("❌ Корзина пуста", show_alert=True)
        return

    await state.set_state(AdminStates.supply_confirm)

    await callback.message.edit_text(
        "📋 <b>ПОДТВЕРЖДЕНИЕ ЗАКУПКИ</b>\n\n" +
        format_cart(items, delivery, expenses) +
        "\n\n⚠️ После подтверждения товары будут добавлены в базу.",
        reply_markup=AdminKeyboards.supply_confirm(),
        parse_mode="HTML"
    )


@supplies_router.callback_query(F.data == "admin:supply:back_to_cart")
async def supply_back_to_cart(callback: CallbackQuery, is_admin: bool, state: FSMContext):
    """Back to cart from confirmation"""
    if not is_admin:
        await callback.answer("⛔️ Нет доступа", show_alert=True)
        return

    data = await state.get_data()
    items = data.get("supply_items", [])
    delivery = data.get("supply_delivery", 0)
    expenses = data.get("supply_expenses", 0)

    await state.set_state(None)

    await callback.message.edit_text(
        format_cart(items, delivery, expenses),
        reply_markup=AdminKeyboards.supply_cart(
            has_items=len(items) > 0,
            delivery=delivery,
            expenses=expenses
        ),
        parse_mode="HTML"
    )


@supplies_router.callback_query(F.data == "admin:supply:confirm")
async def supply_confirm(callback: CallbackQuery, db: Database, user: User, bot: Bot, is_admin: bool, state: FSMContext):
    """Confirm and create supply"""
    if not is_admin:
        await callback.answer("⛔️ Нет доступа", show_alert=True)
        return

    data = await state.get_data()
    items = data.get("supply_items", [])
    delivery = data.get("supply_delivery", 0)
    expenses = data.get("supply_expenses", 0)

    if not items:
        await callback.answer("❌ Корзина пуста", show_alert=True)
        return

    # Create products
    logger = LoggerService(bot)
    created_products = []
    products_total = 0

    for item in items:
        try:
            product = await db.create_product(
                brand_id=item["brand_id"],
                name=item["name"],
                purchase_price=item["purchase_price"],
                sale_price=item["sale_price"],
                quantity=item["quantity"]
            )
            created_products.append(product)
            products_total += item["quantity"] * item["purchase_price"]

            # Log creation
            await logger.log_product_created(product, user)
        except Exception as e:
            await callback.answer(f"❌ Ошибка: {str(e)}", show_alert=True)
            return

    total = products_total + delivery + expenses

    await state.clear()

    # Format result
    result_text = f"✅ <b>Закупка оформлена!</b>\n\n"
    result_text += f"📦 Создано товаров: {len(created_products)}\n"
    for p in created_products:
        result_text += f"  • {p.name} ({p.quantity} шт.)\n"

    result_text += f"\n📦 Товары: {format_price(products_total)}"
    if delivery > 0:
        result_text += f"\n🚚 Доставка: {format_price(delivery)}"
    if expenses > 0:
        result_text += f"\n📋 Расходы: {format_price(expenses)}"
    result_text += f"\n\n💰 <b>ИТОГО: {format_price(total)}</b>"

    await callback.message.edit_text(result_text, parse_mode="HTML")

    await callback.message.answer(
        "Товары добавлены в базу.",
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
        "Закупка отменена.",
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
