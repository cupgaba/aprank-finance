from aiogram import Router, F
from aiogram.types import CallbackQuery
from datetime import datetime, timedelta

from ...database import Database
from ...keyboards.admin import AdminKeyboards
from ...utils.formatting import format_statistics, format_price

statistics_router = Router()


@statistics_router.callback_query(F.data == "admin:stats:today")
async def stats_today(callback: CallbackQuery, db: Database, is_admin: bool):
    """Today's statistics"""
    if not is_admin:
        await callback.answer("⛔️ Нет доступа", show_alert=True)
        return

    today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    stats = await db.get_sales_statistics(today)

    text = format_statistics(stats, "сегодня")

    await callback.message.edit_text(
        text,
        reply_markup=AdminKeyboards.statistics_menu(),
        parse_mode="HTML"
    )


@statistics_router.callback_query(F.data == "admin:stats:week")
async def stats_week(callback: CallbackQuery, db: Database, is_admin: bool):
    """Week statistics"""
    if not is_admin:
        await callback.answer("⛔️ Нет доступа", show_alert=True)
        return

    week_ago = datetime.utcnow() - timedelta(days=7)
    stats = await db.get_sales_statistics(week_ago)

    text = format_statistics(stats, "неделю")

    await callback.message.edit_text(
        text,
        reply_markup=AdminKeyboards.statistics_menu(),
        parse_mode="HTML"
    )


@statistics_router.callback_query(F.data == "admin:stats:month")
async def stats_month(callback: CallbackQuery, db: Database, is_admin: bool):
    """Month statistics"""
    if not is_admin:
        await callback.answer("⛔️ Нет доступа", show_alert=True)
        return

    month_ago = datetime.utcnow() - timedelta(days=30)
    stats = await db.get_sales_statistics(month_ago)

    text = format_statistics(stats, "месяц")

    await callback.message.edit_text(
        text,
        reply_markup=AdminKeyboards.statistics_menu(),
        parse_mode="HTML"
    )


@statistics_router.callback_query(F.data == "admin:stats:top")
async def stats_top_products(callback: CallbackQuery, db: Database, is_admin: bool):
    """Top selling products"""
    if not is_admin:
        await callback.answer("⛔️ Нет доступа", show_alert=True)
        return

    # Get sales for last 30 days
    month_ago = datetime.utcnow() - timedelta(days=30)
    sales = await db.get_sales_by_period(month_ago)

    if not sales:
        await callback.message.edit_text(
            "📋 <b>Топ товаров</b>\n\n"
            "За последний месяц продаж не было.",
            reply_markup=AdminKeyboards.statistics_menu(),
            parse_mode="HTML"
        )
        return

    # Count sales by product
    product_sales = {}
    for sale in sales:
        pid = sale.product_id
        if pid not in product_sales:
            product_sales[pid] = {
                "product": sale.product,
                "quantity": 0,
                "revenue": 0,
                "profit": 0
            }
        product_sales[pid]["quantity"] += sale.quantity
        product_sales[pid]["revenue"] += sale.sale_price * sale.quantity
        product_sales[pid]["profit"] += sale.profit

    # Sort by quantity
    sorted_products = sorted(
        product_sales.values(),
        key=lambda x: x["quantity"],
        reverse=True
    )[:10]

    text = "📋 <b>Топ-10 товаров (за месяц)</b>\n\n"
    for i, item in enumerate(sorted_products, 1):
        product = item["product"]
        text += (
            f"{i}. {product.brand.name} - {product.name}\n"
            f"   Продано: {item['quantity']} шт. | "
            f"Прибыль: {format_price(item['profit'])}\n\n"
        )

    await callback.message.edit_text(
        text,
        reply_markup=AdminKeyboards.statistics_menu(),
        parse_mode="HTML"
    )


@statistics_router.callback_query(F.data == "admin:stats:stock")
async def stats_stock(callback: CallbackQuery, db: Database, is_admin: bool):
    """Stock overview"""
    if not is_admin:
        await callback.answer("⛔️ Нет доступа", show_alert=True)
        return

    products = await db.get_all_products()

    if not products:
        await callback.message.edit_text(
            "📦 <b>Остатки</b>\n\n"
            "Товаров нет.",
            reply_markup=AdminKeyboards.statistics_menu(),
            parse_mode="HTML"
        )
        return

    total_items = sum(p.quantity for p in products)
    total_cost = sum(p.quantity * p.purchase_price for p in products)
    total_value = sum(p.quantity * p.sale_price for p in products)
    potential_profit = total_value - total_cost

    in_stock = sum(1 for p in products if p.quantity > 0)
    out_of_stock = sum(1 for p in products if p.quantity == 0)
    low_stock = sum(1 for p in products if 0 < p.quantity <= 3)

    text = (
        f"📦 <b>Остатки на складе</b>\n\n"
        f"📊 Всего позиций: {len(products)}\n"
        f"✅ В наличии: {in_stock}\n"
        f"⚠️ Мало (≤3): {low_stock}\n"
        f"❌ Нет в наличии: {out_of_stock}\n\n"
        f"📦 Всего единиц: {total_items} шт.\n"
        f"💵 Себестоимость: {format_price(total_cost)}\n"
        f"💰 Стоимость продажи: {format_price(total_value)}\n"
        f"📈 Потенциальная прибыль: {format_price(potential_profit)}"
    )

    await callback.message.edit_text(
        text,
        reply_markup=AdminKeyboards.statistics_menu(),
        parse_mode="HTML"
    )
