from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext

from ...database import Database
from ...database.models import User
from ...keyboards.admin import AdminKeyboards
from ...states.admin import AdminStates
from ...services.channel import ChannelService
from ...utils.formatting import format_product, format_channel_post

publications_router = Router()


@publications_router.callback_query(F.data == "admin:publish:select")
async def publish_select_start(callback: CallbackQuery, db: Database, is_admin: bool, state: FSMContext):
    """Start publishing - select category"""
    if not is_admin:
        await callback.answer("⛔️ Нет доступа", show_alert=True)
        return

    categories = await db.get_all_categories()

    if not categories:
        await callback.answer("❌ Нет категорий", show_alert=True)
        return

    await state.set_state(AdminStates.publish_select_category)

    await callback.message.edit_text(
        "📢 <b>Публикация товара</b>\n\n"
        "Выберите категорию:",
        reply_markup=AdminKeyboards.select_category_for_product(categories),
        parse_mode="HTML"
    )


@publications_router.callback_query(
    AdminStates.publish_select_category,
    F.data.startswith("admin:product:select_cat:")
)
async def publish_category_selected(callback: CallbackQuery, db: Database, state: FSMContext):
    """Category selected for publication"""
    category_id = int(callback.data.split(":")[-1])
    brands = await db.get_brands_by_category(category_id)

    if not brands:
        await callback.answer("❌ В этой категории нет брендов", show_alert=True)
        return

    await state.set_state(AdminStates.publish_select_brand)

    await callback.message.edit_text(
        "📢 <b>Публикация товара</b>\n\n"
        "Выберите бренд:",
        reply_markup=AdminKeyboards.select_brand_for_product(brands),
        parse_mode="HTML"
    )


@publications_router.callback_query(
    AdminStates.publish_select_brand,
    F.data.startswith("admin:product:select_brand:")
)
async def publish_brand_selected(callback: CallbackQuery, db: Database, state: FSMContext):
    """Brand selected for publication"""
    brand_id = int(callback.data.split(":")[-1])
    products = await db.get_products_by_brand(brand_id)

    # Filter only products with stock
    products = [p for p in products if p.quantity > 0]

    if not products:
        await callback.answer("❌ Нет товаров для публикации", show_alert=True)
        return

    await state.set_state(AdminStates.publish_select_product)

    await callback.message.edit_text(
        "📢 <b>Публикация товара</b>\n\n"
        "Выберите товар:",
        reply_markup=AdminKeyboards.products_list(
            products,
            brand_id,
            action="publish",
            back_callback="admin:publications_menu"
        ),
        parse_mode="HTML"
    )


@publications_router.callback_query(
    AdminStates.publish_select_product,
    F.data.startswith("admin:product:publish:")
)
async def publish_product_selected(callback: CallbackQuery, db: Database, state: FSMContext):
    """Product selected for publication"""
    product_id = int(callback.data.split(":")[-1])
    product = await db.get_product_by_id(product_id)

    if not product:
        await callback.answer("❌ Товар не найден", show_alert=True)
        return

    await state.update_data(product_id=product_id)
    await state.set_state(AdminStates.publish_confirm)

    # Show preview
    preview = format_channel_post(product)

    text = (
        f"📢 <b>Предпросмотр публикации</b>\n\n"
        f"{'─' * 20}\n"
        f"{preview}\n"
        f"{'─' * 20}\n\n"
        f"Опубликовать в канал?"
    )

    if product.photo_file_id:
        await callback.message.delete()
        await callback.message.answer_photo(
            photo=product.photo_file_id,
            caption=text,
            reply_markup=AdminKeyboards.publish_confirm(product_id),
            parse_mode="HTML"
        )
    else:
        await callback.message.edit_text(
            text,
            reply_markup=AdminKeyboards.publish_confirm(product_id),
            parse_mode="HTML"
        )


@publications_router.callback_query(F.data.startswith("admin:publish:confirm:"))
async def publish_confirm(callback: CallbackQuery, db: Database, bot: Bot, is_admin: bool, state: FSMContext):
    """Confirm and publish"""
    if not is_admin:
        await callback.answer("⛔️ Нет доступа", show_alert=True)
        return

    product_id = int(callback.data.split(":")[-1])
    product = await db.get_product_by_id(product_id)

    if not product:
        await callback.answer("❌ Товар не найден", show_alert=True)
        return

    # Publish to channel
    channel_service = ChannelService(bot, db)
    post = await channel_service.publish_product(product)

    await state.clear()

    if post:
        await callback.answer("✅ Опубликовано!")
        try:
            await callback.message.delete()
        except:
            pass
        await callback.message.answer(
            f"✅ Товар <b>{product.full_name}</b> опубликован в канал!",
            reply_markup=AdminKeyboards.main_menu(),
            parse_mode="HTML"
        )
    else:
        await callback.answer("❌ Ошибка публикации. Проверьте настройки канала.", show_alert=True)


@publications_router.callback_query(F.data.startswith("admin:product:publish:"))
async def quick_publish_product(callback: CallbackQuery, db: Database, bot: Bot, is_admin: bool, state: FSMContext):
    """Quick publish from product view"""
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

    # Show preview
    preview = format_channel_post(product)

    text = (
        f"📢 <b>Предпросмотр публикации</b>\n\n"
        f"{'─' * 20}\n"
        f"{preview}\n"
        f"{'─' * 20}\n\n"
        f"Опубликовать в канал?"
    )

    await callback.message.edit_text(
        text,
        reply_markup=AdminKeyboards.publish_confirm(product_id),
        parse_mode="HTML"
    )


@publications_router.callback_query(F.data == "admin:publish:pricelist")
async def publish_pricelist(callback: CallbackQuery, db: Database, bot: Bot, is_admin: bool):
    """Publish full pricelist to channel"""
    if not is_admin:
        await callback.answer("⛔️ Нет доступа", show_alert=True)
        return

    channel_service = ChannelService(bot, db)
    success = await channel_service.publish_pricelist()

    if success:
        await callback.answer("✅ Прайс-лист опубликован!")
        await callback.message.edit_text(
            "✅ Прайс-лист успешно опубликован в канал!",
            reply_markup=AdminKeyboards.publications_menu(),
            parse_mode="HTML"
        )
    else:
        await callback.answer("❌ Ошибка публикации. Проверьте настройки канала.", show_alert=True)
