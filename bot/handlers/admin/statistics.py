from aiogram import Router, F
from aiogram.types import CallbackQuery
from datetime import datetime, timedelta

from ...database import Database
from ...keyboards.admin import AdminKeyboards
from ...utils.formatting import format_price, format_writeoff_reason

statistics_router = Router()


def _get_period_dates(period: str) -> tuple:
    """Get start and end dates for a period"""
    now = datetime.utcnow()
    today = now.replace(hour=0, minute=0, second=0, microsecond=0)

    if period == "today":
        return today, None, "сегодня"
    elif period == "this_week":
        start = today - timedelta(days=today.weekday())
        return start, None, "эту неделю"
    elif period == "last_week":
        this_monday = today - timedelta(days=today.weekday())
        last_monday = this_monday - timedelta(days=7)
        last_sunday = this_monday - timedelta(seconds=1)
        return last_monday, last_sunday, "прошлую неделю"
    elif period == "this_month":
        start = today.replace(day=1)
        return start, None, "этот месяц"
    elif period == "last_month":
        first_of_this_month = today.replace(day=1)
        last_day_prev_month = first_of_this_month - timedelta(days=1)
        first_of_prev_month = last_day_prev_month.replace(day=1)
        return first_of_prev_month, first_of_this_month - timedelta(seconds=1), "прошлый месяц"
    elif period == "all_time":
        return None, None, "всё время"
    else:
        return today, None, "сегодня"


def _format_full_statistics(stats: dict, period_name: str) -> str:
    """Format comprehensive statistics"""
    lines = [f"📊 <b>Статистика за {period_name}</b>"]

    # Sales section
    lines.append("")
    lines.append("━━━ 💰 <b>ПРОДАЖИ</b> ━━━")
    if stats["sales_count"] > 0:
        lines.append(f"🧾 Продаж: {stats['sales_count']}")
        lines.append(f"📦 Продано товаров: {stats['total_items_sold']} шт.")
        lines.append(f"💰 Выручка: {format_price(stats['total_revenue'])}")
        lines.append(f"💵 Себестоимость: {format_price(stats['total_cost'])}")
        lines.append(f"📈 Прибыль: {format_price(stats['total_profit'])}")
        if stats['total_revenue'] > 0:
            margin = (stats['total_profit'] / stats['total_revenue']) * 100
            lines.append(f"📊 Рентабельность: {margin:.1f}%")
        if stats['sales_count'] > 0:
            avg_check = stats['total_revenue'] / stats['sales_count']
            lines.append(f"💳 Средний чек: {format_price(avg_check)}")
    else:
        lines.append("Продаж нет")

    # Top products
    if stats["top_products"]:
        lines.append("")
        lines.append("━━━ 🏆 <b>ТОП ТОВАРОВ</b> ━━━")
        for i, item in enumerate(stats["top_products"], 1):
            product = item["product"]
            name = f"{product.brand.name} - {product.name}" if product.brand else product.name
            lines.append(
                f"{i}. {name}\n"
                f"   {item['quantity']} шт. | {format_price(item['revenue'])} | "
                f"прибыль {format_price(item['profit'])}"
            )

    # Supplies section
    lines.append("")
    lines.append("━━━ 📥 <b>ЗАКУПКИ</b> ━━━")
    if stats["supplies_count"] > 0:
        lines.append(f"📋 Закупок: {stats['supplies_count']}")
        lines.append(f"📦 Закуплено товаров: {stats['total_supply_items']} шт.")
        lines.append(f"💵 Сумма закупок: {format_price(stats['total_supply_amount'])}")
    else:
        lines.append("Закупок нет")

    # Write-offs section
    lines.append("")
    lines.append("━━━ 📤 <b>СПИСАНИЯ</b> ━━━")
    if stats["writeoffs_count"] > 0:
        lines.append(f"📋 Списаний: {stats['writeoffs_count']}")
        lines.append(f"📦 Списано товаров: {stats['total_writeoff_items']} шт.")
        lines.append(f"💸 Убыток: {format_price(stats['total_writeoff_loss'])}")

        if stats["writeoff_reasons"]:
            lines.append("")
            lines.append("<b>По причинам:</b>")
            for reason, data in stats["writeoff_reasons"].items():
                reason_name = format_writeoff_reason(reason)
                lines.append(
                    f"  {reason_name}: {data['quantity']} шт. "
                    f"({format_price(data['loss'])})"
                )
    else:
        lines.append("Списаний нет")

    # Summary
    if stats["sales_count"] > 0 or stats["writeoffs_count"] > 0:
        lines.append("")
        lines.append("━━━ 📋 <b>ИТОГО</b> ━━━")
        net_result = stats["total_profit"] - stats["total_writeoff_loss"]
        lines.append(f"📈 Прибыль от продаж: {format_price(stats['total_profit'])}")
        lines.append(f"📤 Убыток от списаний: {format_price(stats['total_writeoff_loss'])}")
        emoji = "📈" if net_result >= 0 else "📉"
        lines.append(f"{emoji} Чистый результат: {format_price(net_result)}")

    return "\n".join(lines)


async def _show_statistics(callback: CallbackQuery, db: Database, period: str):
    """Generic handler for showing statistics"""
    start_date, end_date, period_name = _get_period_dates(period)
    stats = await db.get_full_statistics(start_date, end_date)
    text = _format_full_statistics(stats, period_name)

    await callback.message.edit_text(
        text,
        reply_markup=AdminKeyboards.statistics_menu(),
        parse_mode="HTML"
    )


@statistics_router.callback_query(F.data == "admin:stats:today")
async def stats_today(callback: CallbackQuery, db: Database, is_admin: bool):
    """Today's statistics"""
    if not is_admin:
        await callback.answer("⛔️ Нет доступа", show_alert=True)
        return
    await _show_statistics(callback, db, "today")


@statistics_router.callback_query(F.data == "admin:stats:this_week")
async def stats_this_week(callback: CallbackQuery, db: Database, is_admin: bool):
    """This week's statistics"""
    if not is_admin:
        await callback.answer("⛔️ Нет доступа", show_alert=True)
        return
    await _show_statistics(callback, db, "this_week")


@statistics_router.callback_query(F.data == "admin:stats:last_week")
async def stats_last_week(callback: CallbackQuery, db: Database, is_admin: bool):
    """Last week's statistics"""
    if not is_admin:
        await callback.answer("⛔️ Нет доступа", show_alert=True)
        return
    await _show_statistics(callback, db, "last_week")


@statistics_router.callback_query(F.data == "admin:stats:this_month")
async def stats_this_month(callback: CallbackQuery, db: Database, is_admin: bool):
    """This month's statistics"""
    if not is_admin:
        await callback.answer("⛔️ Нет доступа", show_alert=True)
        return
    await _show_statistics(callback, db, "this_month")


@statistics_router.callback_query(F.data == "admin:stats:last_month")
async def stats_last_month(callback: CallbackQuery, db: Database, is_admin: bool):
    """Last month's statistics"""
    if not is_admin:
        await callback.answer("⛔️ Нет доступа", show_alert=True)
        return
    await _show_statistics(callback, db, "last_month")


@statistics_router.callback_query(F.data == "admin:stats:all_time")
async def stats_all_time(callback: CallbackQuery, db: Database, is_admin: bool):
    """All time statistics"""
    if not is_admin:
        await callback.answer("⛔️ Нет доступа", show_alert=True)
        return
    await _show_statistics(callback, db, "all_time")


@statistics_router.callback_query(F.data == "admin:stats:stock")
async def stats_stock(callback: CallbackQuery, db: Database, is_admin: bool):
    """Stock overview"""
    if not is_admin:
        await callback.answer("⛔️ Нет доступа", show_alert=True)
        return

    products = await db.get_all_products()
    s = await db.get_settings()

    if not products:
        await callback.message.edit_text(
            "📦 <b>Остатки на складе</b>\n\n"
            "Товаров нет.",
            reply_markup=AdminKeyboards.statistics_menu(),
            parse_mode="HTML"
        )
        return

    total_items = sum(p.quantity for p in products)
    total_cost = sum(p.quantity * p.purchase_price for p in products)
    total_value = sum(p.quantity * p.sale_price for p in products)
    potential_profit = total_value - total_cost

    threshold = s.low_stock_threshold
    in_stock = sum(1 for p in products if p.quantity > 0)
    out_of_stock = sum(1 for p in products if p.quantity == 0)
    low_stock = sum(1 for p in products if 0 < p.quantity <= threshold)

    # Group by category
    by_category = {}
    for p in products:
        if p.quantity > 0 and hasattr(p, 'brand') and p.brand:
            cat_name = p.brand.category.name if hasattr(p.brand, 'category') and p.brand.category else "Без категории"
            if cat_name not in by_category:
                by_category[cat_name] = {"items": 0, "value": 0}
            by_category[cat_name]["items"] += p.quantity
            by_category[cat_name]["value"] += p.quantity * p.sale_price

    text = (
        f"📦 <b>Остатки на складе</b>\n\n"
        f"📊 Всего позиций: {len(products)}\n"
        f"✅ В наличии: {in_stock}\n"
        f"⚠️ Мало ({threshold} шт.): {low_stock}\n"
        f"❌ Нет в наличии: {out_of_stock}\n\n"
        f"📦 Всего единиц: {total_items} шт.\n"
        f"💵 Себестоимость: {format_price(total_cost)}\n"
        f"💰 Стоимость продажи: {format_price(total_value)}\n"
        f"📈 Потенциальная прибыль: {format_price(potential_profit)}"
    )

    if by_category:
        text += "\n\n━━━ <b>По категориям</b> ━━━"
        for cat_name, data in sorted(by_category.items()):
            text += f"\n📁 {cat_name}: {data['items']} шт. ({format_price(data['value'])})"

    await callback.message.edit_text(
        text,
        reply_markup=AdminKeyboards.statistics_menu(),
        parse_mode="HTML"
    )
