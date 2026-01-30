from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext

from ...database import Database
from ...database.models import User, WriteOffReason
from ...keyboards.admin import AdminKeyboards
from ...keyboards.common import CommonKeyboards
from ...states.admin import AdminStates
from ...services.logger import LoggerService
from ...utils.formatting import format_writeoff_reason, format_price

writeoffs_router = Router()


@writeoffs_router.callback_query(F.data == "admin:writeoff:new")
async def new_writeoff_start(callback: CallbackQuery, db: Database, is_admin: bool, state: FSMContext):
    """Start new write-off"""
    if not is_admin:
        await callback.answer("⛔️ Нет доступа", show_alert=True)
        return

    categories = await db.get_all_categories()

    if not categories:
        await callback.answer("❌ Нет категорий", show_alert=True)
        return

    await state.set_state(AdminStates.writeoff_select_category)

    await callback.message.edit_text(
        "📤 <b>Новое списание</b>\n\n"
        "Выберите категорию товара:",
        reply_markup=AdminKeyboards.select_category_for_product(categories),
        parse_mode="HTML"
    )


@writeoffs_router.callback_query(
    AdminStates.writeoff_select_category,
    F.data.startswith("admin:product:select_cat:")
)
async def writeoff_category_selected(callback: CallbackQuery, db: Database, state: FSMContext):
    """Category selected for write-off"""
    category_id = int(callback.data.split(":")[-1])
    brands = await db.get_brands_by_category(category_id)

    if not brands:
        await callback.answer("❌ В этой категории нет брендов", show_alert=True)
        return

    await state.set_state(AdminStates.writeoff_select_brand)

    await callback.message.edit_text(
        "📤 <b>Новое списание</b>\n\n"
        "Выберите бренд:",
        reply_markup=AdminKeyboards.select_brand_for_product(brands),
        parse_mode="HTML"
    )


@writeoffs_router.callback_query(
    AdminStates.writeoff_select_brand,
    F.data.startswith("admin:product:select_brand:")
)
async def writeoff_brand_selected(callback: CallbackQuery, db: Database, state: FSMContext):
    """Brand selected for write-off"""
    brand_id = int(callback.data.split(":")[-1])
    products = await db.get_products_by_brand(brand_id)

    # Filter only products with stock
    products = [p for p in products if p.quantity > 0]

    if not products:
        await callback.answer("❌ Нет товаров для списания", show_alert=True)
        return

    await state.set_state(AdminStates.writeoff_select_product)

    await callback.message.edit_text(
        "📤 <b>Новое списание</b>\n\n"
        "Выберите товар:",
        reply_markup=AdminKeyboards.products_list(
            products,
            brand_id,
            action="writeoff",
            back_callback="admin:writeoffs_menu"
        ),
        parse_mode="HTML"
    )


@writeoffs_router.callback_query(
    AdminStates.writeoff_select_product,
    F.data.startswith("admin:product:writeoff:")
)
async def writeoff_product_selected(callback: CallbackQuery, db: Database, state: FSMContext):
    """Product selected for write-off"""
    product_id = int(callback.data.split(":")[-1])
    product = await db.get_product_by_id(product_id)

    if not product:
        await callback.answer("❌ Товар не найден", show_alert=True)
        return

    if product.quantity <= 0:
        await callback.answer("❌ Товар отсутствует на складе", show_alert=True)
        return

    await state.update_data(product_id=product_id)
    await state.set_state(AdminStates.writeoff_select_reason)

    await callback.message.edit_text(
        f"📤 <b>Списание товара</b>\n\n"
        f"Товар: {product.full_name}\n"
        f"В наличии: {product.quantity} шт.\n\n"
        f"Выберите причину списания:",
        reply_markup=AdminKeyboards.writeoff_reason(),
        parse_mode="HTML"
    )


@writeoffs_router.callback_query(
    AdminStates.writeoff_select_reason,
    F.data.startswith("admin:writeoff:reason:")
)
async def writeoff_reason_selected(callback: CallbackQuery, db: Database, state: FSMContext):
    """Reason selected for write-off"""
    reason_value = callback.data.split(":")[-1]
    reason = WriteOffReason(reason_value)

    await state.update_data(reason=reason)
    await state.set_state(AdminStates.writeoff_enter_quantity)

    data = await state.get_data()
    product = await db.get_product_by_id(data["product_id"])

    await callback.message.edit_text(
        f"📤 <b>Списание товара</b>\n\n"
        f"Товар: {product.full_name}\n"
        f"Причина: {format_writeoff_reason(reason)}\n"
        f"В наличии: {product.quantity} шт.\n\n"
        f"Введите количество для списания:",
        parse_mode="HTML"
    )


@writeoffs_router.message(AdminStates.writeoff_enter_quantity)
async def writeoff_quantity_entered(message: Message, db: Database, state: FSMContext):
    """Quantity entered for write-off"""
    try:
        quantity = int(message.text.strip())
        if quantity <= 0:
            raise ValueError()
    except ValueError:
        await message.answer("❌ Введите корректное количество:")
        return

    data = await state.get_data()
    product = await db.get_product_by_id(data["product_id"])

    if quantity > product.quantity:
        await message.answer(f"❌ Недостаточно товара. В наличии: {product.quantity} шт.")
        return

    await state.update_data(quantity=quantity)
    await state.set_state(AdminStates.writeoff_enter_notes)

    await message.answer(
        f"📤 <b>Списание товара</b>\n\n"
        f"Товар: {product.full_name}\n"
        f"Причина: {format_writeoff_reason(data['reason'])}\n"
        f"Количество: {quantity} шт.\n\n"
        f"Добавьте комментарий или отправьте 'Пропустить':",
        reply_markup=CommonKeyboards.skip(),
        parse_mode="HTML"
    )


@writeoffs_router.message(AdminStates.writeoff_enter_notes)
async def writeoff_notes_entered(
    message: Message,
    db: Database,
    user: User,
    bot: Bot,
    state: FSMContext
):
    """Notes entered, complete write-off"""
    data = await state.get_data()

    notes = None
    if message.text.strip() != "⏭ Пропустить":
        notes = message.text.strip()

    # Create write-off
    writeoff = await db.create_write_off(
        product_id=data["product_id"],
        quantity=data["quantity"],
        reason=data["reason"],
        notes=notes,
        created_by_id=user.id
    )

    if not writeoff:
        await message.answer("❌ Ошибка при создании списания")
        return

    # Log write-off
    logger = LoggerService(bot)
    await logger.log_writeoff(writeoff, user)

    await state.clear()

    product = await db.get_product_by_id(data["product_id"])
    loss = data["quantity"] * product.purchase_price

    await message.answer(
        f"✅ <b>Списание оформлено!</b>\n\n"
        f"Товар: {product.full_name}\n"
        f"Причина: {format_writeoff_reason(data['reason'])}\n"
        f"Количество: {data['quantity']} шт.\n"
        f"Убыток: {format_price(loss)}\n"
        f"{'📝 ' + notes if notes else ''}",
        reply_markup=AdminKeyboards.main_menu(),
        parse_mode="HTML"
    )


@writeoffs_router.callback_query(F.data == "admin:writeoff:history")
async def writeoff_history(callback: CallbackQuery, db: Database, is_admin: bool):
    """Show write-off history"""
    if not is_admin:
        await callback.answer("⛔️ Нет доступа", show_alert=True)
        return

    writeoffs = await db.get_write_offs(limit=20)

    if not writeoffs:
        await callback.message.edit_text(
            "📤 <b>История списаний</b>\n\n"
            "Списаний пока не было.",
            reply_markup=AdminKeyboards.writeoffs_menu(),
            parse_mode="HTML"
        )
        return

    text = "📤 <b>История списаний</b>\n\n"
    total_loss = 0

    for wo in writeoffs:
        date = wo.created_at.strftime("%d.%m.%Y")
        loss = wo.quantity * wo.product.purchase_price
        total_loss += loss
        text += f"• {date} - {wo.product.name} x{wo.quantity} ({format_writeoff_reason(wo.reason)})\n"

    text += f"\n📊 Общий убыток: {format_price(total_loss)}"

    await callback.message.edit_text(
        text,
        reply_markup=AdminKeyboards.writeoffs_menu(),
        parse_mode="HTML"
    )
