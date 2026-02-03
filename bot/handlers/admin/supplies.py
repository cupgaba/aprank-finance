from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
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
        cat_brand = f"({item.get('category_name', '')} | {item['brand_name']})"
        text += f"• {cat_brand} {item['name']} x{item['quantity']} по {item['purchase_price']}₽ = {format_price(subtotal)}\n"
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

    await callback.message.edit_text(
        "📥 <b>Добавление товаров в закупку</b>\n\n"
        f"{'Выберите категорию:' if categories else 'Категорий пока нет. Создайте первую!'}",
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

    await state.update_data(supply_category_id=category_id)

    await callback.message.edit_text(
        "📥 <b>Добавление товаров в закупку</b>\n\n"
        f"{'Выберите бренд:' if brands else 'Брендов пока нет. Создайте первый!'}",
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
        f"<code>название закупка продажа кол-во</code>\n\n"
        f"<b>Пример:</b>\n"
        f"<code>Красная смородина 140 250 5\n"
        f"Кислое мороженое 150 280 3\n"
        f"Манго 140 250 10</code>\n\n"
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
    category = await db.get_category_by_id(brand.category_id)

    lines = message.text.strip().split("\n")
    added = 0
    errors = []

    for line in lines:
        line = line.strip()
        if not line:
            continue

        # Parse: name purchase sale quantity (last 3 are numbers)
        parts = line.rsplit(maxsplit=3)

        if len(parts) < 4:
            errors.append(f"❌ '{line}' - формат: название закупка продажа кол-во")
            continue

        try:
            name = parts[0].strip()
            purchase_price = float(parts[1].replace(",", "."))
            sale_price = float(parts[2].replace(",", "."))
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
                "category_name": category.name,
                "name": name,
                "purchase_price": purchase_price,
                "sale_price": sale_price,
                "quantity": quantity
            })
            added += 1

        except (ValueError, IndexError):
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

    # Check for existing products
    duplicates = []
    for i, item in enumerate(items):
        existing = await db.find_product_by_name_and_brand(item["brand_id"], item["name"])
        if existing:
            duplicates.append({
                "index": i,
                "item": item,
                "existing": existing
            })

    # If there are duplicates, ask user what to do
    if duplicates and not data.get("duplicates_resolved"):
        dup_text = "⚠️ <b>Найдены существующие товары:</b>\n\n"
        for dup in duplicates:
            ex = dup["existing"]
            item = dup["item"]
            dup_text += f"• <b>{item['name']}</b> ({item['brand_name']})\n"
            dup_text += f"  Существует: {ex.quantity} шт. по {ex.purchase_price}₽\n"
            dup_text += f"  Новая закупка: +{item['quantity']} шт. по {item['purchase_price']}₽\n\n"

        dup_text += "Что сделать с дубликатами?"

        await state.update_data(duplicates=duplicates)

        builder = InlineKeyboardBuilder()
        builder.row(InlineKeyboardButton(text="📦 Добавить к остаткам", callback_data="admin:supply:merge"))
        builder.row(InlineKeyboardButton(text="🆕 Создать отдельно", callback_data="admin:supply:create_new"))
        builder.row(InlineKeyboardButton(text="◀️ Назад", callback_data="admin:supply:back_to_cart"))

        await callback.message.edit_text(dup_text, reply_markup=builder.as_markup(), parse_mode="HTML")
        return

    # Process items
    logger = LoggerService(bot)
    created_products = []
    updated_products = []
    supply_items = []
    products_total = 0

    merge_mode = data.get("merge_duplicates", False)

    for item in items:
        try:
            existing = await db.find_product_by_name_and_brand(item["brand_id"], item["name"]) if merge_mode else None

            if existing and merge_mode:
                # Add to existing product quantity
                old_qty = existing.quantity
                product = await db.update_product(
                    existing.id,
                    quantity=existing.quantity + item["quantity"],
                    purchase_price=item["purchase_price"],
                    sale_price=item["sale_price"]
                )
                updated_products.append((product, item["quantity"]))
                await logger.log_product_updated(product, user, "quantity", old_qty, product.quantity)
            else:
                # Create new product
                product = await db.create_product(
                    brand_id=item["brand_id"],
                    name=item["name"],
                    purchase_price=item["purchase_price"],
                    sale_price=item["sale_price"],
                    quantity=item["quantity"]
                )
                created_products.append(product)
                await logger.log_product_created(product, user)

            supply_items.append({
                "product_id": product.id,
                "quantity": item["quantity"],
                "purchase_price": item["purchase_price"]
            })
            products_total += item["quantity"] * item["purchase_price"]

        except Exception as e:
            await callback.answer(f"❌ Ошибка: {str(e)}", show_alert=True)
            return

    # Create supply record for history
    await db.create_supply_record(
        items=supply_items,
        delivery=delivery,
        expenses=expenses,
        created_by_id=user.id
    )

    total = products_total + delivery + expenses

    await state.clear()

    # Format result
    result_text = f"✅ <b>Закупка оформлена!</b>\n\n"

    if created_products:
        result_text += f"🆕 Создано товаров: {len(created_products)}\n"
        for p in created_products:
            result_text += f"  • {p.name} ({p.quantity} шт.)\n"

    if updated_products:
        result_text += f"\n📦 Пополнено товаров: {len(updated_products)}\n"
        for p, added in updated_products:
            result_text += f"  • {p.name} (+{added} шт. = {p.quantity} шт.)\n"

    result_text += f"\n📦 Товары: {format_price(products_total)}"
    if delivery > 0:
        result_text += f"\n🚚 Доставка: {format_price(delivery)}"
    if expenses > 0:
        result_text += f"\n📋 Расходы: {format_price(expenses)}"
    result_text += f"\n\n💰 <b>ИТОГО: {format_price(total)}</b>"

    await callback.message.edit_text(result_text, parse_mode="HTML")

    await callback.message.answer(
        "Закупка сохранена в историю.",
        reply_markup=AdminKeyboards.main_menu()
    )


@supplies_router.callback_query(F.data == "admin:supply:merge")
async def supply_merge_duplicates(callback: CallbackQuery, is_admin: bool, state: FSMContext):
    """Merge duplicates with existing products"""
    if not is_admin:
        await callback.answer("⛔️ Нет доступа", show_alert=True)
        return

    await state.update_data(duplicates_resolved=True, merge_duplicates=True)

    # Trigger confirm again
    data = await state.get_data()
    items = data.get("supply_items", [])
    delivery = data.get("supply_delivery", 0)
    expenses = data.get("supply_expenses", 0)

    await callback.message.edit_text(
        "📋 <b>ПОДТВЕРЖДЕНИЕ ЗАКУПКИ</b>\n\n" +
        format_cart(items, delivery, expenses) +
        "\n\n✅ Дубликаты будут добавлены к существующим остаткам.",
        reply_markup=AdminKeyboards.supply_confirm(),
        parse_mode="HTML"
    )


@supplies_router.callback_query(F.data == "admin:supply:create_new")
async def supply_create_new(callback: CallbackQuery, is_admin: bool, state: FSMContext):
    """Create new products for all items"""
    if not is_admin:
        await callback.answer("⛔️ Нет доступа", show_alert=True)
        return

    await state.update_data(duplicates_resolved=True, merge_duplicates=False)

    # Trigger confirm again
    data = await state.get_data()
    items = data.get("supply_items", [])
    delivery = data.get("supply_delivery", 0)
    expenses = data.get("supply_expenses", 0)

    await callback.message.edit_text(
        "📋 <b>ПОДТВЕРЖДЕНИЕ ЗАКУПКИ</b>\n\n" +
        format_cart(items, delivery, expenses) +
        "\n\n🆕 Все товары будут созданы как отдельные позиции.",
        reply_markup=AdminKeyboards.supply_confirm(),
        parse_mode="HTML"
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
async def supply_history(callback: CallbackQuery, db: Database, is_admin: bool, state: FSMContext):
    """Show supply history"""
    if not is_admin:
        await callback.answer("⛔️ Нет доступа", show_alert=True)
        return

    supplies = await db.get_supplies(limit=100)

    if not supplies:
        await callback.message.edit_text(
            "📥 <b>История закупок</b>\n\n"
            "Закупок пока не было.",
            reply_markup=AdminKeyboards.supplies_menu(),
            parse_mode="HTML"
        )
        return

    # Save supplies to state for pagination
    await state.update_data(supply_history_ids=[s.id for s in supplies])

    await callback.message.edit_text(
        "📥 <b>История закупок</b>\n\n"
        "Выберите закупку для просмотра:",
        reply_markup=AdminKeyboards.supply_history_list(supplies, page=0),
        parse_mode="HTML"
    )


@supplies_router.callback_query(F.data.startswith("admin:supply:page:"))
async def supply_history_page(callback: CallbackQuery, db: Database, is_admin: bool):
    """Supply history pagination"""
    if not is_admin:
        await callback.answer("⛔️ Нет доступа", show_alert=True)
        return

    page = int(callback.data.split(":")[-1])
    supplies = await db.get_supplies(limit=100)

    await callback.message.edit_text(
        "📥 <b>История закупок</b>\n\n"
        "Выберите закупку для просмотра:",
        reply_markup=AdminKeyboards.supply_history_list(supplies, page=page),
        parse_mode="HTML"
    )


@supplies_router.callback_query(F.data.startswith("admin:supply:view:"))
async def supply_view_detail(callback: CallbackQuery, db: Database, is_admin: bool):
    """View supply details"""
    if not is_admin:
        await callback.answer("⛔️ Нет доступа", show_alert=True)
        return

    supply_id = int(callback.data.split(":")[-1])
    supply = await db.get_supply_by_id(supply_id)

    if not supply:
        await callback.answer("❌ Закупка не найдена", show_alert=True)
        return

    date = supply.created_at.strftime("%d.%m.%Y %H:%M")
    text = f"📦 <b>Закупка от {date}</b>\n\n"

    if supply.items:
        for item in supply.items:
            product_name = item.product.name if item.product else "Удалён"
            brand_name = item.product.brand.name if item.product and item.product.brand else ""
            text += f"• {brand_name} | {product_name}\n"
            text += f"  {item.quantity} шт. × {item.purchase_price}₽ = {format_price(item.quantity * item.purchase_price)}\n"

    text += f"\n💰 <b>Итого: {format_price(supply.total_amount)}</b>"

    if supply.notes:
        text += f"\n📝 {supply.notes}"

    await callback.message.edit_text(
        text,
        reply_markup=AdminKeyboards.supply_detail_back(),
        parse_mode="HTML"
    )


@supplies_router.callback_query(F.data == "admin:supply:add_category")
async def supply_add_category_start(callback: CallbackQuery, is_admin: bool, state: FSMContext):
    """Start adding category from supply flow"""
    if not is_admin:
        await callback.answer("⛔️ Нет доступа", show_alert=True)
        return

    await state.set_state(AdminStates.supply_add_category_name)

    await callback.message.edit_text(
        "📁 <b>Создание категории</b>\n\n"
        "Введите название категории:",
        parse_mode="HTML"
    )


@supplies_router.message(AdminStates.supply_add_category_name)
async def supply_add_category_name(message: Message, db: Database, state: FSMContext):
    """Process category name in supply flow"""
    name = message.text.strip()

    if len(name) < 2:
        await message.answer("❌ Название должно быть не менее 2 символов. Попробуйте снова:")
        return

    await db.create_category(name=name)
    await state.set_state(None)

    categories = await db.get_all_categories()

    await message.answer(
        f"✅ Категория <b>{name}</b> создана!\n\n"
        "📥 <b>Добавление товаров в закупку</b>\n\n"
        "Выберите категорию:",
        reply_markup=AdminKeyboards.select_category_for_supply(categories),
        parse_mode="HTML"
    )


@supplies_router.callback_query(F.data.startswith("admin:supply:add_brand:"))
async def supply_add_brand_start(callback: CallbackQuery, db: Database, is_admin: bool, state: FSMContext):
    """Start adding brand from supply flow"""
    if not is_admin:
        await callback.answer("⛔️ Нет доступа", show_alert=True)
        return

    category_id = int(callback.data.split(":")[-1])
    category = await db.get_category_by_id(category_id)

    if not category:
        await callback.answer("❌ Категория не найдена", show_alert=True)
        return

    await state.set_state(AdminStates.supply_add_brand_name)
    await state.update_data(supply_new_brand_category_id=category_id)

    await callback.message.edit_text(
        f"🏷 <b>Создание бренда</b>\n\n"
        f"Категория: {category.name}\n\n"
        f"Введите название бренда:",
        parse_mode="HTML"
    )


@supplies_router.message(AdminStates.supply_add_brand_name)
async def supply_add_brand_name(message: Message, db: Database, state: FSMContext):
    """Process brand name in supply flow"""
    name = message.text.strip()

    if len(name) < 2:
        await message.answer("❌ Название должно быть не менее 2 символов. Попробуйте снова:")
        return

    data = await state.get_data()
    category_id = data.get("supply_new_brand_category_id")

    await db.create_brand(category_id=category_id, name=name)
    await state.set_state(None)

    brands = await db.get_brands_by_category(category_id)

    await message.answer(
        f"✅ Бренд <b>{name}</b> создан!\n\n"
        "📥 <b>Добавление товаров в закупку</b>\n\n"
        "Выберите бренд:",
        reply_markup=AdminKeyboards.select_brand_for_supply(brands, category_id),
        parse_mode="HTML"
    )
