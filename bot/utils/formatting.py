from typing import Sequence, Optional
from datetime import datetime

from ..database.models import Product, Category, Brand, Reservation, WriteOffReason


def format_price(price: float) -> str:
    """Format price with currency"""
    return f"{price:,.0f}₽".replace(",", " ")


def format_product(product: Product, show_purchase_price: bool = False) -> str:
    """Format product info for display"""
    lines = [
        f"📦 <b>{product.brand.name}</b> - {product.name}",
        f"💰 Цена: {format_price(product.sale_price)}",
    ]

    if show_purchase_price:
        lines.append(f"💵 Закупка: {format_price(product.purchase_price)}")
        lines.append(f"📈 Маржа: {format_price(product.margin)} ({product.margin_percent:.1f}%)")

    lines.append(f"📊 Остаток: {product.quantity} шт.")

    if product.quantity == 0:
        lines.append("❌ <b>Нет в наличии</b>")
    elif product.quantity <= 3:
        lines.append("⚠️ <b>Мало на складе!</b>")

    return "\n".join(lines)


def format_product_short(product: Product) -> str:
    """Short format for lists"""
    status = "✅" if product.quantity > 0 else "❌"
    return f"{status} {product.name} — {format_price(product.sale_price)} ({product.quantity} шт.)"


def format_pricelist(
    products: Sequence[Product],
    category: Optional[Category] = None,
    brand: Optional[Brand] = None
) -> str:
    """Format price list"""
    lines = ["📋 <b>ПРАЙС-ЛИСТ</b>"]

    if category:
        lines.append(f"📁 Категория: {category.name}")
    if brand:
        lines.append(f"🏷 Бренд: {brand.name}")

    lines.append("")

    if not products:
        lines.append("Товары не найдены")
        return "\n".join(lines)

    # Group by brand if no specific brand selected
    if not brand:
        grouped = {}
        for product in products:
            brand_name = product.brand.name
            if brand_name not in grouped:
                grouped[brand_name] = []
            grouped[brand_name].append(product)

        for brand_name, brand_products in sorted(grouped.items()):
            lines.append(f"\n<b>🏷 {brand_name}</b>")
            for p in sorted(brand_products, key=lambda x: x.name):
                lines.append(format_product_short(p))
    else:
        for p in sorted(products, key=lambda x: x.name):
            lines.append(format_product_short(p))

    # Add timestamp
    lines.append(f"\n🕐 Обновлено: {datetime.now().strftime('%d.%m.%Y %H:%M')}")

    return "\n".join(lines)


def format_statistics(stats: dict, period_name: str = "период") -> str:
    """Format statistics"""
    lines = [
        f"📊 <b>Статистика за {period_name}</b>",
        "",
        f"💰 Выручка: {format_price(stats['total_revenue'])}",
        f"💵 Себестоимость: {format_price(stats['total_cost'])}",
        f"📈 Прибыль: {format_price(stats['total_profit'])}",
        "",
        f"📦 Продано товаров: {stats['total_items']} шт.",
        f"🧾 Количество продаж: {stats['sales_count']}",
    ]

    if stats['total_revenue'] > 0:
        profit_percent = (stats['total_profit'] / stats['total_revenue']) * 100
        lines.append(f"📊 Рентабельность: {profit_percent:.1f}%")

    return "\n".join(lines)


def format_reservation(reservation: Reservation, for_admin: bool = False) -> str:
    """Format reservation info"""
    product = reservation.product
    user = reservation.user

    lines = [
        f"🔔 <b>Резервирование #{reservation.id}</b>",
        "",
        f"📦 Товар: {product.brand.name} - {product.name}",
        f"💰 Цена: {format_price(product.sale_price)}",
        f"📊 Количество: {reservation.quantity} шт.",
        "",
        f"⏰ Истекает: {reservation.expires_at.strftime('%d.%m.%Y %H:%M')}",
    ]

    if for_admin:
        lines.extend([
            "",
            f"👤 Покупатель: {user.full_name}",
            f"🆔 Username: @{user.username}" if user.username else "",
            f"📱 Телефон: {user.phone}" if user.phone else "📱 Телефон: не указан",
        ])

    if reservation.notes:
        lines.append(f"📝 Заметки: {reservation.notes}")

    return "\n".join(filter(None, lines))


def format_writeoff_reason(reason: WriteOffReason) -> str:
    """Format write-off reason"""
    reasons = {
        WriteOffReason.DEFECT: "🔴 Брак",
        WriteOffReason.DAMAGE: "🟠 Бракираж",
        WriteOffReason.LOSS: "🟡 Потеря",
        WriteOffReason.OTHER: "⚪️ Другое",
    }
    return reasons.get(reason, str(reason))


def format_supply_item(product: Product, quantity: int, price: float) -> str:
    """Format supply item"""
    total = quantity * price
    return f"• {product.name} x{quantity} по {format_price(price)} = {format_price(total)}"


def format_channel_post(product: Product, is_sold: bool = False) -> str:
    """Format channel publication post"""
    if is_sold:
        return (
            f"❌ <s>{product.brand.name} - {product.name}</s>\n"
            f"<b>ПРОДАНО</b>"
        )

    lines = [
        f"🆕 <b>В НАЛИЧИИ</b>",
        "",
        f"🏷 <b>{product.brand.name}</b>",
        f"📦 {product.name}",
        "",
        f"💰 Цена: <b>{format_price(product.sale_price)}</b>",
    ]

    if product.quantity > 1:
        lines.append(f"📊 Количество: {product.quantity} шт.")

    return "\n".join(lines)
