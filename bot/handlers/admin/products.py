from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext

from ...database import Database
from ...database.models import User
from ...keyboards.admin import AdminKeyboards
from ...keyboards.common import CommonKeyboards
from ...states.admin import AdminStates
from ...services.logger import LoggerService
from ...utils.formatting import format_product

products_router = Router()


@products_router.callback_query(F.data == "admin:all_products")
async def list_all_products(callback: CallbackQuery, db: Database, is_admin: bool):
    """List all products"""
    if not is_admin:
        await callback.answer("⛔️ Нет доступа", show_alert=True)
        return

    products = await db.get_all_products()

    if not products:
        await callback.message.edit_text(
            "📦 <b>Все товары</b>\n\n"
            "Товары пока не добавлены.",
            reply_markup=AdminKeyboards.products_list([]),
            parse_mode="HTML"
        )
    else:
        await callback.message.edit_text(
            f"📦 <b>Все товары</b> ({len(products)} шт.)\n\n"
            "Выберите товар:",
            reply_markup=AdminKeyboards.products_list(products),
            parse_mode="HTML"
        )


@products_router.callback_query(F.data == "admin:add_product")
async def add_product_select_category(callback: CallbackQuery, db: Database, is_admin: bool):
    """Start adding product - select category"""
    if not is_admin:
        await callback.answer("⛔️ Нет доступа", show_alert=True)
        return

    categories = await db.get_all_categories()

    if not categories:
        await callback.answer("❌ Сначала создайте категорию", show_alert=True)
        return

    await callback.message.edit_text(
        "📦 <b>Добавление товара</b>\n\n"
        "Выберите категорию:",
        reply_markup=AdminKeyboards.select_category_for_product(categories),
        parse_mode="HTML"
    )


@products_router.callback_query(F.data.startswith("admin:product:select_cat:"))
async def add_product_select_brand(callback: CallbackQuery, db: Database, is_admin: bool):
    """Select brand for new product"""
    if not is_admin:
        await callback.answer("⛔️ Нет доступа", show_alert=True)
        return

    category_id = int(callback.data.split(":")[-1])
    brands = await db.get_brands_by_category(category_id)

    if not brands:
        await callback.answer("❌ В этой категории нет брендов. Сначала создайте бренд.", show_alert=True)
        return

    await callback.message.edit_text(
        "📦 <b>Добавление товара</b>\n\n"
        "Выберите бренд:",
        reply_markup=AdminKeyboards.select_brand_for_product(brands),
        parse_mode="HTML"
    )


@products_router.callback_query(F.data.startswith("admin:add_product:"))
async def add_product_start(callback: CallbackQuery, db: Database, is_admin: bool, state: FSMContext):
    """Start adding product to brand"""
    if not is_admin:
        await callback.answer("⛔️ Нет доступа", show_alert=True)
        return

    brand_id = int(callback.data.split(":")[-1])
    brand = await db.get_brand_by_id(brand_id)

    if not brand:
        await callback.answer("❌ Бренд не найден", show_alert=True)
        return

    await state.set_state(AdminStates.add_product_name)
    await state.update_data(brand_id=brand_id)

    await callback.message.edit_text(
        f"📦 <b>Добавление товара</b>\n\n"
        f"Бренд: {brand.name}\n\n"
        f"Введите название товара (вкус):",
        parse_mode="HTML"
    )
    await callback.message.answer(
        "Ожидаю название...",
        reply_markup=CommonKeyboards.cancel()
    )


@products_router.callback_query(F.data.startswith("admin:product:select_brand:"))
async def product_brand_selected(callback: CallbackQuery, db: Database, is_admin: bool, state: FSMContext):
    """Brand selected for new product"""
    if not is_admin:
        await callback.answer("⛔️ Нет доступа", show_alert=True)
        return

    brand_id = int(callback.data.split(":")[-1])
    brand = await db.get_brand_by_id(brand_id)

    if not brand:
        await callback.answer("❌ Бренд не найден", show_alert=True)
        return

    await state.set_state(AdminStates.add_product_name)
    await state.update_data(brand_id=brand_id)

    await callback.message.edit_text(
        f"📦 <b>Добавление товара</b>\n\n"
        f"Бренд: {brand.name}\n\n"
        f"Введите название товара (вкус):",
        parse_mode="HTML"
    )


@products_router.message(AdminStates.add_product_name)
async def add_product_name(message: Message, state: FSMContext):
    """Process product name"""
    name = message.text.strip()
    if len(name) < 2:
        await message.answer("❌ Название должно быть не менее 2 символов. Попробуйте снова:")
        return

    await state.update_data(name=name)
    await state.set_state(AdminStates.add_product_purchase_price)

    await message.answer(
        f"📦 Название: <b>{name}</b>\n\n"
        f"Введите цену закупки (число):",
        reply_markup=CommonKeyboards.cancel(),
        parse_mode="HTML"
    )


@products_router.message(AdminStates.add_product_purchase_price)
async def add_product_purchase_price(message: Message, state: FSMContext):
    """Process purchase price"""
    try:
        price = float(message.text.strip().replace(",", ".").replace(" ", ""))
        if price < 0:
            raise ValueError()
    except ValueError:
        await message.answer("❌ Введите корректную цену (число). Попробуйте снова:")
        return

    await state.update_data(purchase_price=price)
    await state.set_state(AdminStates.add_product_sale_price)

    await message.answer(
        f"💵 Цена закупки: <b>{price}₽</b>\n\n"
        f"Введите цену продажи:",
        reply_markup=CommonKeyboards.cancel(),
        parse_mode="HTML"
    )


@products_router.message(AdminStates.add_product_sale_price)
async def add_product_sale_price(message: Message, state: FSMContext):
    """Process sale price"""
    try:
        price = float(message.text.strip().replace(",", ".").replace(" ", ""))
        if price < 0:
            raise ValueError()
    except ValueError:
        await message.answer("❌ Введите корректную цену (число). Попробуйте снова:")
        return

    await state.update_data(sale_price=price)
    await state.set_state(AdminStates.add_product_quantity)

    await message.answer(
        f"💰 Цена продажи: <b>{price}₽</b>\n\n"
        f"Введите количество:",
        reply_markup=CommonKeyboards.cancel(),
        parse_mode="HTML"
    )


@products_router.message(AdminStates.add_product_quantity)
async def add_product_quantity(message: Message, state: FSMContext):
    """Process quantity"""
    try:
        quantity = int(message.text.strip())
        if quantity < 0:
            raise ValueError()
    except ValueError:
        await message.answer("❌ Введите корректное количество (целое число). Попробуйте снова:")
        return

    await state.update_data(quantity=quantity)
    await state.set_state(AdminStates.add_product_photo)

    await message.answer(
        f"📊 Количество: <b>{quantity} шт.</b>\n\n"
        f"Отправьте фото товара или нажмите 'Пропустить':",
        reply_markup=CommonKeyboards.skip(),
        parse_mode="HTML"
    )


@products_router.message(AdminStates.add_product_photo, F.photo)
async def add_product_photo(message: Message, db: Database, user: User, bot: Bot, state: FSMContext):
    """Process product photo and create product"""
    data = await state.get_data()

    # Get photo file_id
    photo_file_id = message.photo[-1].file_id

    # Create product
    product = await db.create_product(
        brand_id=data["brand_id"],
        name=data["name"],
        purchase_price=data["purchase_price"],
        sale_price=data["sale_price"],
        quantity=data["quantity"],
        photo_file_id=photo_file_id
    )

    # Log creation
    logger = LoggerService(bot)
    await logger.log_product_created(product, user)

    await state.clear()
    await message.answer(
        f"✅ Товар успешно создан!\n\n"
        f"{format_product(product, show_purchase_price=True)}",
        reply_markup=AdminKeyboards.main_menu(),
        parse_mode="HTML"
    )


@products_router.message(AdminStates.add_product_photo, F.text == "⏭ Пропустить")
async def add_product_skip_photo(message: Message, db: Database, user: User, bot: Bot, state: FSMContext):
    """Skip photo and create product"""
    data = await state.get_data()

    # Create product without photo
    product = await db.create_product(
        brand_id=data["brand_id"],
        name=data["name"],
        purchase_price=data["purchase_price"],
        sale_price=data["sale_price"],
        quantity=data["quantity"]
    )

    # Log creation
    logger = LoggerService(bot)
    await logger.log_product_created(product, user)

    await state.clear()
    await message.answer(
        f"✅ Товар успешно создан!\n\n"
        f"{format_product(product, show_purchase_price=True)}",
        reply_markup=AdminKeyboards.main_menu(),
        parse_mode="HTML"
    )


@products_router.callback_query(F.data.startswith("admin:product:view:"))
async def view_product(callback: CallbackQuery, db: Database, is_admin: bool):
    """View product details"""
    if not is_admin:
        await callback.answer("⛔️ Нет доступа", show_alert=True)
        return

    product_id = int(callback.data.split(":")[-1])
    product = await db.get_product_by_id(product_id)

    if not product:
        await callback.answer("❌ Товар не найден", show_alert=True)
        return

    text = format_product(product, show_purchase_price=True)

    if product.photo_file_id:
        await callback.message.delete()
        await callback.message.answer_photo(
            photo=product.photo_file_id,
            caption=text,
            reply_markup=AdminKeyboards.product_actions(product),
            parse_mode="HTML"
        )
    else:
        await callback.message.edit_text(
            text,
            reply_markup=AdminKeyboards.product_actions(product),
            parse_mode="HTML"
        )


@products_router.callback_query(F.data.startswith("admin:product:edit_sale_price:"))
async def edit_sale_price_start(callback: CallbackQuery, db: Database, is_admin: bool, state: FSMContext):
    """Start editing sale price"""
    if not is_admin:
        await callback.answer("⛔️ Нет доступа", show_alert=True)
        return

    product_id = int(callback.data.split(":")[-1])
    product = await db.get_product_by_id(product_id)

    if not product:
        await callback.answer("❌ Товар не найден", show_alert=True)
        return

    await state.set_state(AdminStates.edit_product_sale_price)
    await state.update_data(product_id=product_id, old_price=product.sale_price)

    await callback.message.edit_text(
        f"✏️ <b>Изменение цены продажи</b>\n\n"
        f"Товар: {product.full_name}\n"
        f"Текущая цена: {product.sale_price}₽\n\n"
        f"Введите новую цену:",
        parse_mode="HTML"
    )


@products_router.message(AdminStates.edit_product_sale_price)
async def edit_sale_price(message: Message, db: Database, user: User, bot: Bot, state: FSMContext):
    """Process new sale price"""
    try:
        price = float(message.text.strip().replace(",", ".").replace(" ", ""))
        if price < 0:
            raise ValueError()
    except ValueError:
        await message.answer("❌ Введите корректную цену. Попробуйте снова:")
        return

    data = await state.get_data()
    product_id = data["product_id"]
    old_price = data["old_price"]

    product = await db.update_product(product_id, sale_price=price)

    # Log change
    logger = LoggerService(bot)
    await logger.log_product_updated(product, user, "sale_price", old_price, price)

    await state.clear()
    await message.answer(
        f"✅ Цена продажи изменена!\n\n"
        f"Товар: {product.full_name}\n"
        f"Новая цена: {price}₽",
        reply_markup=AdminKeyboards.main_menu(),
        parse_mode="HTML"
    )


@products_router.callback_query(F.data.startswith("admin:product:edit_purchase_price:"))
async def edit_purchase_price_start(callback: CallbackQuery, db: Database, is_admin: bool, state: FSMContext):
    """Start editing purchase price"""
    if not is_admin:
        await callback.answer("⛔️ Нет доступа", show_alert=True)
        return

    product_id = int(callback.data.split(":")[-1])
    product = await db.get_product_by_id(product_id)

    if not product:
        await callback.answer("❌ Товар не найден", show_alert=True)
        return

    await state.set_state(AdminStates.edit_product_purchase_price)
    await state.update_data(product_id=product_id, old_price=product.purchase_price)

    await callback.message.edit_text(
        f"✏️ <b>Изменение цены закупки</b>\n\n"
        f"Товар: {product.full_name}\n"
        f"Текущая цена: {product.purchase_price}₽\n\n"
        f"Введите новую цену:",
        parse_mode="HTML"
    )


@products_router.message(AdminStates.edit_product_purchase_price)
async def edit_purchase_price(message: Message, db: Database, user: User, bot: Bot, state: FSMContext):
    """Process new purchase price"""
    try:
        price = float(message.text.strip().replace(",", ".").replace(" ", ""))
        if price < 0:
            raise ValueError()
    except ValueError:
        await message.answer("❌ Введите корректную цену. Попробуйте снова:")
        return

    data = await state.get_data()
    product_id = data["product_id"]
    old_price = data["old_price"]

    product = await db.update_product(product_id, purchase_price=price)

    # Log change
    logger = LoggerService(bot)
    await logger.log_product_updated(product, user, "purchase_price", old_price, price)

    await state.clear()
    await message.answer(
        f"✅ Цена закупки изменена!\n\n"
        f"Товар: {product.full_name}\n"
        f"Новая цена: {price}₽",
        reply_markup=AdminKeyboards.main_menu(),
        parse_mode="HTML"
    )


@products_router.callback_query(F.data.startswith("admin:product:edit_quantity:"))
async def edit_quantity_start(callback: CallbackQuery, db: Database, is_admin: bool, state: FSMContext):
    """Start editing quantity"""
    if not is_admin:
        await callback.answer("⛔️ Нет доступа", show_alert=True)
        return

    product_id = int(callback.data.split(":")[-1])
    product = await db.get_product_by_id(product_id)

    if not product:
        await callback.answer("❌ Товар не найден", show_alert=True)
        return

    await state.set_state(AdminStates.edit_product_quantity)
    await state.update_data(product_id=product_id, old_quantity=product.quantity)

    await callback.message.edit_text(
        f"✏️ <b>Изменение остатка</b>\n\n"
        f"Товар: {product.full_name}\n"
        f"Текущий остаток: {product.quantity} шт.\n\n"
        f"Введите новое количество:",
        parse_mode="HTML"
    )


@products_router.message(AdminStates.edit_product_quantity)
async def edit_quantity(message: Message, db: Database, user: User, bot: Bot, state: FSMContext):
    """Process new quantity"""
    try:
        quantity = int(message.text.strip())
        if quantity < 0:
            raise ValueError()
    except ValueError:
        await message.answer("❌ Введите корректное количество. Попробуйте снова:")
        return

    data = await state.get_data()
    product_id = data["product_id"]
    old_quantity = data["old_quantity"]

    product = await db.update_product(product_id, quantity=quantity)

    # Log change
    logger = LoggerService(bot)
    await logger.log_product_updated(product, user, "quantity", old_quantity, quantity)

    await state.clear()
    await message.answer(
        f"✅ Остаток изменён!\n\n"
        f"Товар: {product.full_name}\n"
        f"Новый остаток: {quantity} шт.",
        reply_markup=AdminKeyboards.main_menu(),
        parse_mode="HTML"
    )


@products_router.callback_query(F.data.startswith("admin:product:edit_photo:"))
async def edit_photo_start(callback: CallbackQuery, db: Database, is_admin: bool, state: FSMContext):
    """Start editing photo"""
    if not is_admin:
        await callback.answer("⛔️ Нет доступа", show_alert=True)
        return

    product_id = int(callback.data.split(":")[-1])
    product = await db.get_product_by_id(product_id)

    if not product:
        await callback.answer("❌ Товар не найден", show_alert=True)
        return

    await state.set_state(AdminStates.edit_product_photo)
    await state.update_data(product_id=product_id)

    await callback.message.edit_text(
        f"🖼 <b>Изменение фото</b>\n\n"
        f"Товар: {product.full_name}\n\n"
        f"Отправьте новое фото:",
        parse_mode="HTML"
    )


@products_router.message(AdminStates.edit_product_photo, F.photo)
async def edit_photo(message: Message, db: Database, state: FSMContext):
    """Process new photo"""
    data = await state.get_data()
    product_id = data["product_id"]

    photo_file_id = message.photo[-1].file_id
    product = await db.update_product(product_id, photo_file_id=photo_file_id)

    await state.clear()
    await message.answer(
        f"✅ Фото обновлено!\n\n"
        f"Товар: {product.full_name}",
        reply_markup=AdminKeyboards.main_menu(),
        parse_mode="HTML"
    )


@products_router.callback_query(F.data.startswith("admin:product:delete:"))
async def delete_product(callback: CallbackQuery, db: Database, user: User, bot: Bot, is_admin: bool):
    """Delete product"""
    if not is_admin:
        await callback.answer("⛔️ Нет доступа", show_alert=True)
        return

    product_id = int(callback.data.split(":")[-1])
    product = await db.get_product_by_id(product_id)

    if not product:
        await callback.answer("❌ Товар не найден", show_alert=True)
        return

    brand_id = product.brand_id

    # Log deletion
    logger = LoggerService(bot)
    await logger.log_product_deleted(product, user)

    await db.delete_product(product_id)

    await callback.answer("✅ Товар удалён")

    # Return to brand products list
    products = await db.get_products_by_brand(brand_id)
    brand = await db.get_brand_by_id(brand_id)

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


@products_router.callback_query(F.data == "admin:low_stock")
async def low_stock_products(callback: CallbackQuery, db: Database, is_admin: bool):
    """Show low stock products"""
    if not is_admin:
        await callback.answer("⛔️ Нет доступа", show_alert=True)
        return

    products = await db.get_low_stock_products(threshold=3)

    if not products:
        await callback.message.edit_text(
            "⚠️ <b>Мало на складе</b>\n\n"
            "Все товары в достаточном количестве!",
            reply_markup=AdminKeyboards.products_list([]),
            parse_mode="HTML"
        )
    else:
        await callback.message.edit_text(
            f"⚠️ <b>Мало на складе</b> ({len(products)} позиций)\n\n"
            "Товары с остатком 3 шт. и менее:",
            reply_markup=AdminKeyboards.products_list(products),
            parse_mode="HTML"
        )


@products_router.callback_query(F.data == "admin:search_product")
async def search_product_start(callback: CallbackQuery, is_admin: bool, state: FSMContext):
    """Start product search"""
    if not is_admin:
        await callback.answer("⛔️ Нет доступа", show_alert=True)
        return

    # Using a simple approach - ask for search query in message
    await callback.message.edit_text(
        "🔍 <b>Поиск товара</b>\n\n"
        "Введите название товара для поиска:",
        parse_mode="HTML"
    )
    await callback.message.answer(
        "Ожидаю запрос...",
        reply_markup=CommonKeyboards.cancel()
    )

    # We'll handle search in a separate state/handler or just make it simple
    # For simplicity, let's assume the next text message is a search query
    await state.set_state(AdminStates.add_product_name)  # Reuse state temporarily
    await state.update_data(search_mode=True)


# Note: Search handling would need additional logic
# For now, this is a basic implementation
