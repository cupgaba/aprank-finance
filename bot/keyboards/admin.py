from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import ReplyKeyboardBuilder, InlineKeyboardBuilder
from typing import Sequence, Optional

from ..database.models import Category, Brand, Product, Reservation, WriteOffReason


class AdminKeyboards:
    # ==================== MAIN MENU ====================

    @staticmethod
    def main_menu() -> ReplyKeyboardMarkup:
        """Admin main menu"""
        builder = ReplyKeyboardBuilder()
        builder.row(
            KeyboardButton(text="📦 Товары"),
            KeyboardButton(text="📊 Статистика")
        )
        builder.row(
            KeyboardButton(text="📥 Закупки"),
            KeyboardButton(text="💰 Продажи")
        )
        builder.row(
            KeyboardButton(text="📤 Списания"),
            KeyboardButton(text="📢 Публикации")
        )
        builder.row(
            KeyboardButton(text="🔔 Резервы"),
            KeyboardButton(text="⚙️ Настройки")
        )
        return builder.as_markup(resize_keyboard=True)

    # ==================== PRODUCTS ====================

    @staticmethod
    def products_menu() -> InlineKeyboardMarkup:
        """Products management menu"""
        builder = InlineKeyboardBuilder()
        builder.row(InlineKeyboardButton(text="📁 Категории", callback_data="admin:categories"))
        builder.row(InlineKeyboardButton(text="📦 Все товары", callback_data="admin:all_products"))
        builder.row(InlineKeyboardButton(text="➕ Добавить товар", callback_data="admin:add_product"))
        builder.row(InlineKeyboardButton(text="🔍 Поиск товара", callback_data="admin:search_product"))
        builder.row(InlineKeyboardButton(text="⚠️ Мало на складе", callback_data="admin:low_stock"))
        return builder.as_markup()

    @staticmethod
    def categories_list(categories: Sequence[Category], action: str = "view") -> InlineKeyboardMarkup:
        """List of categories"""
        builder = InlineKeyboardBuilder()
        for cat in categories:
            builder.row(InlineKeyboardButton(
                text=f"📁 {cat.name}",
                callback_data=f"admin:category:{action}:{cat.id}"
            ))
        builder.row(InlineKeyboardButton(text="➕ Добавить категорию", callback_data="admin:add_category"))
        builder.row(InlineKeyboardButton(text="◀️ Назад", callback_data="admin:products_menu"))
        return builder.as_markup()

    @staticmethod
    def category_actions(category_id: int) -> InlineKeyboardMarkup:
        """Category actions"""
        builder = InlineKeyboardBuilder()
        builder.row(InlineKeyboardButton(text="🏷 Бренды категории", callback_data=f"admin:category:brands:{category_id}"))
        builder.row(InlineKeyboardButton(text="🗑 Удалить", callback_data=f"admin:category:delete:{category_id}"))
        builder.row(InlineKeyboardButton(text="◀️ Назад", callback_data="admin:categories"))
        return builder.as_markup()

    @staticmethod
    def brands_list(brands: Sequence[Brand], category_id: Optional[int] = None, action: str = "view") -> InlineKeyboardMarkup:
        """List of brands"""
        builder = InlineKeyboardBuilder()
        for brand in brands:
            builder.row(InlineKeyboardButton(
                text=f"🏷 {brand.name}",
                callback_data=f"admin:brand:{action}:{brand.id}"
            ))
        if category_id:
            builder.row(InlineKeyboardButton(
                text="➕ Добавить бренд",
                callback_data=f"admin:add_brand:{category_id}"
            ))
            builder.row(InlineKeyboardButton(
                text="◀️ Назад",
                callback_data=f"admin:category:view:{category_id}"
            ))
        else:
            builder.row(InlineKeyboardButton(text="◀️ Назад", callback_data="admin:products_menu"))
        return builder.as_markup()

    @staticmethod
    def brand_actions(brand_id: int, category_id: int) -> InlineKeyboardMarkup:
        """Brand actions"""
        builder = InlineKeyboardBuilder()
        builder.row(InlineKeyboardButton(text="📦 Товары бренда", callback_data=f"admin:brand:products:{brand_id}"))
        builder.row(InlineKeyboardButton(text="➕ Добавить товар", callback_data=f"admin:add_product:{brand_id}"))
        builder.row(InlineKeyboardButton(text="🗑 Удалить", callback_data=f"admin:brand:delete:{brand_id}"))
        builder.row(InlineKeyboardButton(text="◀️ Назад", callback_data=f"admin:category:brands:{category_id}"))
        return builder.as_markup()

    @staticmethod
    def products_list(
        products: Sequence[Product],
        brand_id: Optional[int] = None,
        action: str = "view",
        back_callback: str = "admin:products_menu",
        page: int = 0,
        per_page: int = 10,
        show_category: bool = False
    ) -> InlineKeyboardMarkup:
        """List of products with pagination"""
        builder = InlineKeyboardBuilder()

        # Pagination
        total = len(products)
        start = page * per_page
        end = start + per_page
        page_products = products[start:end]

        for product in page_products:
            status = "✅" if product.quantity > 0 else "❌"
            if show_category and hasattr(product, 'brand') and product.brand:
                cat_name = product.brand.category.name if hasattr(product.brand, 'category') else ""
                text = f"{status} {cat_name} | {product.name} ({product.quantity} шт.)"
            else:
                text = f"{status} {product.name} ({product.quantity} шт.)"
            builder.row(InlineKeyboardButton(
                text=text,
                callback_data=f"admin:product:{action}:{product.id}"
            ))

        # Pagination buttons
        if total > per_page:
            nav_buttons = []
            if page > 0:
                nav_buttons.append(InlineKeyboardButton(text="◀️", callback_data=f"admin:products_page:{page-1}"))
            nav_buttons.append(InlineKeyboardButton(text=f"{page+1}/{(total-1)//per_page+1}", callback_data="noop"))
            if end < total:
                nav_buttons.append(InlineKeyboardButton(text="▶️", callback_data=f"admin:products_page:{page+1}"))
            builder.row(*nav_buttons)

        if brand_id:
            builder.row(InlineKeyboardButton(
                text="➕ Добавить товар",
                callback_data=f"admin:add_product:{brand_id}"
            ))
        builder.row(InlineKeyboardButton(text="◀️ Назад", callback_data=back_callback))
        return builder.as_markup()

    @staticmethod
    def product_actions(product: Product) -> InlineKeyboardMarkup:
        """Product actions"""
        builder = InlineKeyboardBuilder()
        builder.row(InlineKeyboardButton(text="✏️ Изменить цену продажи", callback_data=f"admin:product:edit_sale_price:{product.id}"))
        builder.row(InlineKeyboardButton(text="💵 Изменить цену закупки", callback_data=f"admin:product:edit_purchase_price:{product.id}"))
        builder.row(InlineKeyboardButton(text="📦 Изменить остаток", callback_data=f"admin:product:edit_quantity:{product.id}"))
        builder.row(InlineKeyboardButton(text="🖼 Изменить фото", callback_data=f"admin:product:edit_photo:{product.id}"))
        builder.row(InlineKeyboardButton(text="📢 Опубликовать в канал", callback_data=f"admin:product:publish:{product.id}"))
        builder.row(InlineKeyboardButton(text="💰 Продать", callback_data=f"admin:product:sell:{product.id}"))
        builder.row(InlineKeyboardButton(text="📤 Списать", callback_data=f"admin:product:writeoff:{product.id}"))
        builder.row(InlineKeyboardButton(text="🗑 Удалить товар", callback_data=f"admin:product:delete:{product.id}"))
        builder.row(InlineKeyboardButton(text="◀️ Назад", callback_data=f"admin:brand:products:{product.brand_id}"))
        return builder.as_markup()

    # ==================== STATISTICS ====================

    @staticmethod
    def statistics_menu() -> InlineKeyboardMarkup:
        """Statistics menu"""
        builder = InlineKeyboardBuilder()
        builder.row(InlineKeyboardButton(text="📈 Сегодня", callback_data="admin:stats:today"))
        builder.row(InlineKeyboardButton(text="📊 Неделя", callback_data="admin:stats:week"))
        builder.row(InlineKeyboardButton(text="📉 Месяц", callback_data="admin:stats:month"))
        builder.row(InlineKeyboardButton(text="📋 Топ товаров", callback_data="admin:stats:top"))
        builder.row(InlineKeyboardButton(text="📦 Остатки", callback_data="admin:stats:stock"))
        return builder.as_markup()

    # ==================== SUPPLIES ====================

    @staticmethod
    def supplies_menu() -> InlineKeyboardMarkup:
        """Supplies menu"""
        builder = InlineKeyboardBuilder()
        builder.row(InlineKeyboardButton(text="➕ Новая закупка", callback_data="admin:supply:new"))
        builder.row(InlineKeyboardButton(text="📋 История закупок", callback_data="admin:supply:history"))
        return builder.as_markup()

    @staticmethod
    def supply_cart(has_items: bool = False, delivery: float = 0, expenses: float = 0) -> InlineKeyboardMarkup:
        """Supply cart actions"""
        builder = InlineKeyboardBuilder()
        builder.row(InlineKeyboardButton(text="➕ Добавить товары", callback_data="admin:supply:add_item"))
        if has_items:
            delivery_text = f"🚚 Доставка: {delivery}₽" if delivery > 0 else "🚚 Добавить доставку"
            expenses_text = f"📋 Расходы: {expenses}₽" if expenses > 0 else "📋 Добавить расходы"
            builder.row(InlineKeyboardButton(text=delivery_text, callback_data="admin:supply:delivery"))
            builder.row(InlineKeyboardButton(text=expenses_text, callback_data="admin:supply:expenses"))
            builder.row(InlineKeyboardButton(text="✅ Завершить закупку", callback_data="admin:supply:finish"))
        builder.row(InlineKeyboardButton(text="❌ Отменить", callback_data="admin:supply:cancel"))
        return builder.as_markup()

    @staticmethod
    def supply_confirm() -> InlineKeyboardMarkup:
        """Confirm supply"""
        builder = InlineKeyboardBuilder()
        builder.row(InlineKeyboardButton(text="✅ Подтвердить", callback_data="admin:supply:confirm"))
        builder.row(InlineKeyboardButton(text="◀️ Назад", callback_data="admin:supply:back_to_cart"))
        return builder.as_markup()

    @staticmethod
    def supply_history_list(supplies: Sequence, page: int = 0, per_page: int = 10) -> InlineKeyboardMarkup:
        """Supply history with pagination"""
        builder = InlineKeyboardBuilder()

        total = len(supplies)
        start = page * per_page
        end = start + per_page
        page_supplies = supplies[start:end]

        for supply in page_supplies:
            date = supply.created_at.strftime("%d.%m %H:%M")
            items_count = len(supply.items) if hasattr(supply, 'items') and supply.items else 0
            builder.row(InlineKeyboardButton(
                text=f"📦 {date} - {items_count} поз. - {supply.total_amount:.0f}₽",
                callback_data=f"admin:supply:view:{supply.id}"
            ))

        # Pagination buttons
        if total > per_page:
            nav_buttons = []
            if page > 0:
                nav_buttons.append(InlineKeyboardButton(text="◀️", callback_data=f"admin:supply:page:{page-1}"))
            nav_buttons.append(InlineKeyboardButton(text=f"{page+1}/{(total-1)//per_page+1}", callback_data="noop"))
            if end < total:
                nav_buttons.append(InlineKeyboardButton(text="▶️", callback_data=f"admin:supply:page:{page+1}"))
            builder.row(*nav_buttons)

        builder.row(InlineKeyboardButton(text="◀️ Назад", callback_data="admin:supplies_menu"))
        return builder.as_markup()

    @staticmethod
    def supply_detail_back() -> InlineKeyboardMarkup:
        """Back from supply detail"""
        builder = InlineKeyboardBuilder()
        builder.row(InlineKeyboardButton(text="◀️ К списку закупок", callback_data="admin:supply:history"))
        return builder.as_markup()

    # ==================== SALES ====================

    @staticmethod
    def sales_menu() -> InlineKeyboardMarkup:
        """Sales menu"""
        builder = InlineKeyboardBuilder()
        builder.row(InlineKeyboardButton(text="➕ Добавить продажу", callback_data="admin:sale:new"))
        builder.row(InlineKeyboardButton(text="📋 Продажи за сегодня", callback_data="admin:sale:today"))
        builder.row(InlineKeyboardButton(text="📊 История продаж", callback_data="admin:sale:history"))
        return builder.as_markup()

    @staticmethod
    def sale_quantity(product_id: int, max_qty: int) -> InlineKeyboardMarkup:
        """Select quantity for sale"""
        builder = InlineKeyboardBuilder()
        row = []
        for i in range(1, min(max_qty + 1, 6)):
            row.append(InlineKeyboardButton(text=str(i), callback_data=f"admin:sale:qty:{product_id}:{i}"))
        if row:
            builder.row(*row)
        if max_qty > 5:
            builder.row(InlineKeyboardButton(text="Другое количество", callback_data=f"admin:sale:qty_custom:{product_id}"))
        builder.row(InlineKeyboardButton(text="❌ Отмена", callback_data="admin:sales_menu"))
        return builder.as_markup()

    # ==================== WRITE-OFFS ====================

    @staticmethod
    def writeoffs_menu() -> InlineKeyboardMarkup:
        """Write-offs menu"""
        builder = InlineKeyboardBuilder()
        builder.row(InlineKeyboardButton(text="➕ Новое списание", callback_data="admin:writeoff:new"))
        builder.row(InlineKeyboardButton(text="📋 История списаний", callback_data="admin:writeoff:history"))
        return builder.as_markup()

    @staticmethod
    def writeoff_reason() -> InlineKeyboardMarkup:
        """Select write-off reason"""
        builder = InlineKeyboardBuilder()
        reasons = [
            ("🔴 Брак", WriteOffReason.DEFECT.value),
            ("🟠 Бракираж", WriteOffReason.DAMAGE.value),
            ("🟡 Потеря", WriteOffReason.LOSS.value),
            ("⚪️ Другое", WriteOffReason.OTHER.value),
        ]
        for text, value in reasons:
            builder.row(InlineKeyboardButton(text=text, callback_data=f"admin:writeoff:reason:{value}"))
        builder.row(InlineKeyboardButton(text="❌ Отмена", callback_data="admin:writeoffs_menu"))
        return builder.as_markup()

    # ==================== PUBLICATIONS ====================

    @staticmethod
    def publications_menu() -> InlineKeyboardMarkup:
        """Publications menu"""
        builder = InlineKeyboardBuilder()
        builder.row(InlineKeyboardButton(text="📢 Опубликовать товар", callback_data="admin:publish:select"))
        builder.row(InlineKeyboardButton(text="📋 Опубликовать прайс", callback_data="admin:publish:pricelist"))
        return builder.as_markup()

    @staticmethod
    def publish_confirm(product_id: int) -> InlineKeyboardMarkup:
        """Confirm publication"""
        builder = InlineKeyboardBuilder()
        builder.row(
            InlineKeyboardButton(text="✅ Опубликовать", callback_data=f"admin:publish:confirm:{product_id}"),
            InlineKeyboardButton(text="❌ Отмена", callback_data="admin:publications_menu")
        )
        return builder.as_markup()

    # ==================== RESERVATIONS ====================

    @staticmethod
    def reservations_menu() -> InlineKeyboardMarkup:
        """Reservations menu"""
        builder = InlineKeyboardBuilder()
        builder.row(InlineKeyboardButton(text="📋 Активные резервы", callback_data="admin:reserve:active"))
        builder.row(InlineKeyboardButton(text="⏰ Истекающие скоро", callback_data="admin:reserve:expiring"))
        return builder.as_markup()

    @staticmethod
    def reservation_actions(reservation: Reservation) -> InlineKeyboardMarkup:
        """Reservation actions"""
        builder = InlineKeyboardBuilder()
        builder.row(InlineKeyboardButton(
            text="✅ Завершить (продан)",
            callback_data=f"admin:reserve:complete:{reservation.id}"
        ))
        builder.row(InlineKeyboardButton(
            text="❌ Отменить резерв",
            callback_data=f"admin:reserve:cancel:{reservation.id}"
        ))
        builder.row(InlineKeyboardButton(text="◀️ Назад", callback_data="admin:reserve:active"))
        return builder.as_markup()

    @staticmethod
    def reservations_list(reservations: Sequence[Reservation]) -> InlineKeyboardMarkup:
        """List of reservations"""
        builder = InlineKeyboardBuilder()
        for res in reservations:
            builder.row(InlineKeyboardButton(
                text=f"🔔 {res.product.name} - {res.user.full_name}",
                callback_data=f"admin:reserve:view:{res.id}"
            ))
        builder.row(InlineKeyboardButton(text="◀️ Назад", callback_data="admin:reservations_menu"))
        return builder.as_markup()

    # ==================== SETTINGS ====================

    @staticmethod
    def settings_menu() -> InlineKeyboardMarkup:
        """Settings menu"""
        builder = InlineKeyboardBuilder()
        builder.row(InlineKeyboardButton(text="👥 Управление админами", callback_data="admin:settings:admins"))
        builder.row(InlineKeyboardButton(text="📢 Настройки канала", callback_data="admin:settings:channel"))
        builder.row(InlineKeyboardButton(text="⏰ Настройки напоминаний", callback_data="admin:settings:reminders"))
        return builder.as_markup()

    @staticmethod
    def select_category_for_brand(categories: Sequence[Category]) -> InlineKeyboardMarkup:
        """Select category when adding brand"""
        builder = InlineKeyboardBuilder()
        for cat in categories:
            builder.row(InlineKeyboardButton(
                text=f"📁 {cat.name}",
                callback_data=f"admin:brand:select_cat:{cat.id}"
            ))
        builder.row(InlineKeyboardButton(text="❌ Отмена", callback_data="admin:products_menu"))
        return builder.as_markup()

    @staticmethod
    def select_brand_for_product(brands: Sequence[Brand]) -> InlineKeyboardMarkup:
        """Select brand when adding product"""
        builder = InlineKeyboardBuilder()
        for brand in brands:
            builder.row(InlineKeyboardButton(
                text=f"🏷 {brand.name}",
                callback_data=f"admin:product:select_brand:{brand.id}"
            ))
        builder.row(InlineKeyboardButton(text="❌ Отмена", callback_data="admin:products_menu"))
        return builder.as_markup()

    @staticmethod
    def select_category_for_product(categories: Sequence[Category]) -> InlineKeyboardMarkup:
        """Select category when adding product (to then select brand)"""
        builder = InlineKeyboardBuilder()
        for cat in categories:
            builder.row(InlineKeyboardButton(
                text=f"📁 {cat.name}",
                callback_data=f"admin:product:select_cat:{cat.id}"
            ))
        builder.row(InlineKeyboardButton(text="❌ Отмена", callback_data="admin:products_menu"))
        return builder.as_markup()

    # ==================== SUPPLY SELECTION ====================

    @staticmethod
    def select_category_for_supply(categories: Sequence[Category]) -> InlineKeyboardMarkup:
        """Select category for supply"""
        builder = InlineKeyboardBuilder()
        for cat in categories:
            builder.row(InlineKeyboardButton(
                text=f"📁 {cat.name}",
                callback_data=f"admin:supply:select_cat:{cat.id}"
            ))
        builder.row(InlineKeyboardButton(text="➕ Создать категорию", callback_data="admin:supply:add_category"))
        builder.row(InlineKeyboardButton(text="◀️ Назад в корзину", callback_data="admin:supply:back_to_cart"))
        return builder.as_markup()

    @staticmethod
    def select_brand_for_supply(brands: Sequence[Brand], category_id: int) -> InlineKeyboardMarkup:
        """Select brand for supply"""
        builder = InlineKeyboardBuilder()
        for brand in brands:
            builder.row(InlineKeyboardButton(
                text=f"🏷 {brand.name}",
                callback_data=f"admin:supply:select_brand:{brand.id}"
            ))
        builder.row(InlineKeyboardButton(text="➕ Создать бренд", callback_data=f"admin:supply:add_brand:{category_id}"))
        builder.row(InlineKeyboardButton(text="◀️ Назад", callback_data="admin:supply:add_item"))
        return builder.as_markup()

    # ==================== SALE SELECTION ====================

    @staticmethod
    def select_category_for_sale(categories: Sequence[Category]) -> InlineKeyboardMarkup:
        """Select category for sale"""
        builder = InlineKeyboardBuilder()
        for cat in categories:
            builder.row(InlineKeyboardButton(
                text=f"📁 {cat.name}",
                callback_data=f"admin:sale:select_cat:{cat.id}"
            ))
        builder.row(InlineKeyboardButton(text="❌ Отмена", callback_data="admin:sales_menu"))
        return builder.as_markup()

    @staticmethod
    def select_brand_for_sale(brands: Sequence[Brand]) -> InlineKeyboardMarkup:
        """Select brand for sale"""
        builder = InlineKeyboardBuilder()
        for brand in brands:
            builder.row(InlineKeyboardButton(
                text=f"🏷 {brand.name}",
                callback_data=f"admin:sale:select_brand:{brand.id}"
            ))
        builder.row(InlineKeyboardButton(text="❌ Отмена", callback_data="admin:sales_menu"))
        return builder.as_markup()

    # ==================== WRITEOFF SELECTION ====================

    @staticmethod
    def select_category_for_writeoff(categories: Sequence[Category]) -> InlineKeyboardMarkup:
        """Select category for writeoff"""
        builder = InlineKeyboardBuilder()
        for cat in categories:
            builder.row(InlineKeyboardButton(
                text=f"📁 {cat.name}",
                callback_data=f"admin:writeoff:select_cat:{cat.id}"
            ))
        builder.row(InlineKeyboardButton(text="❌ Отмена", callback_data="admin:writeoffs_menu"))
        return builder.as_markup()

    @staticmethod
    def select_brand_for_writeoff(brands: Sequence[Brand]) -> InlineKeyboardMarkup:
        """Select brand for writeoff"""
        builder = InlineKeyboardBuilder()
        for brand in brands:
            builder.row(InlineKeyboardButton(
                text=f"🏷 {brand.name}",
                callback_data=f"admin:writeoff:select_brand:{brand.id}"
            ))
        builder.row(InlineKeyboardButton(text="❌ Отмена", callback_data="admin:writeoffs_menu"))
        return builder.as_markup()
