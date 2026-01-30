from aiogram import Router, F
from aiogram.types import CallbackQuery

from ...database import Database
from ...keyboards.user import UserKeyboards
from ...utils.formatting import format_pricelist, format_product

pricelist_router = Router()


@pricelist_router.callback_query(F.data == "user:pricelist:menu")
async def pricelist_menu(callback: CallbackQuery, db: Database):
    """Price list menu"""
    categories = await db.get_all_categories()

    await callback.message.edit_text(
        "📋 <b>Прайс-лист</b>\n\n"
        "Выберите категорию или получите весь прайс:",
        reply_markup=UserKeyboards.pricelist_categories(categories),
        parse_mode="HTML"
    )


@pricelist_router.callback_query(F.data == "user:pricelist:all")
async def full_pricelist(callback: CallbackQuery, db: Database):
    """Full price list"""
    products = await db.get_all_products(in_stock_only=True)

    if not products:
        await callback.message.edit_text(
            "📋 <b>Прайс-лист</b>\n\n"
            "К сожалению, сейчас нет товаров в наличии.",
            reply_markup=UserKeyboards.pricelist_categories([]),
            parse_mode="HTML"
        )
        return

    text = format_pricelist(products)

    # Split if too long
    max_length = 4000
    if len(text) > max_length:
        # Send first part
        await callback.message.edit_text(
            text[:max_length] + "\n\n<i>...продолжение в следующем сообщении</i>",
            parse_mode="HTML"
        )
        # Send remaining parts
        remaining = text[max_length:]
        while remaining:
            part = remaining[:max_length]
            remaining = remaining[max_length:]
            await callback.message.answer(
                part,
                parse_mode="HTML"
            )

        # Send keyboard in last message
        categories = await db.get_all_categories()
        await callback.message.answer(
            "Выберите категорию:",
            reply_markup=UserKeyboards.pricelist_categories(categories)
        )
    else:
        categories = await db.get_all_categories()
        await callback.message.edit_text(
            text,
            reply_markup=UserKeyboards.pricelist_categories(categories),
            parse_mode="HTML"
        )


@pricelist_router.callback_query(F.data.startswith("user:pricelist:cat:"))
async def category_pricelist(callback: CallbackQuery, db: Database):
    """Price list by category"""
    category_id = int(callback.data.split(":")[-1])
    category = await db.get_category_by_id(category_id)

    if not category:
        await callback.answer("❌ Категория не найдена", show_alert=True)
        return

    brands = await db.get_brands_by_category(category_id)

    if not brands:
        await callback.answer("❌ В этой категории нет товаров", show_alert=True)
        return

    await callback.message.edit_text(
        f"📁 <b>{category.name}</b>\n\n"
        "Выберите бренд:",
        reply_markup=UserKeyboards.pricelist_brands(brands, category_id),
        parse_mode="HTML"
    )


@pricelist_router.callback_query(F.data.startswith("user:pricelist:brand:"))
async def brand_pricelist(callback: CallbackQuery, db: Database):
    """Price list by brand"""
    brand_id = int(callback.data.split(":")[-1])
    brand = await db.get_brand_by_id(brand_id)

    if not brand:
        await callback.answer("❌ Бренд не найден", show_alert=True)
        return

    products = await db.get_products_by_brand(brand_id, available_only=True)
    products = [p for p in products if p.quantity > 0]

    if not products:
        await callback.message.edit_text(
            f"🏷 <b>{brand.name}</b>\n\n"
            "К сожалению, сейчас нет товаров в наличии.",
            reply_markup=UserKeyboards.products_list(
                [],
                back_callback=f"user:pricelist:cat:{brand.category_id}"
            ),
            parse_mode="HTML"
        )
        return

    text = format_pricelist(products, brand=brand)

    await callback.message.edit_text(
        text,
        reply_markup=UserKeyboards.products_list(
            products,
            back_callback=f"user:pricelist:cat:{brand.category_id}"
        ),
        parse_mode="HTML"
    )


@pricelist_router.callback_query(F.data.startswith("user:product:"))
async def view_product(callback: CallbackQuery, db: Database):
    """View product details"""
    if callback.data == "user:product:unavailable":
        await callback.answer("❌ Товар закончился", show_alert=True)
        return

    product_id = int(callback.data.split(":")[-1])
    product = await db.get_product_by_id(product_id)

    if not product:
        await callback.answer("❌ Товар не найден", show_alert=True)
        return

    text = format_product(product, show_purchase_price=False)

    if product.photo_file_id:
        await callback.message.delete()
        await callback.message.answer_photo(
            photo=product.photo_file_id,
            caption=text,
            reply_markup=UserKeyboards.product_view(product),
            parse_mode="HTML"
        )
    else:
        await callback.message.edit_text(
            text,
            reply_markup=UserKeyboards.product_view(product),
            parse_mode="HTML"
        )
