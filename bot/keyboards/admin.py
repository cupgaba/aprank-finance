from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import ReplyKeyboardBuilder, InlineKeyboardBuilder
from typing import Sequence, Optional

from ..database.models import Category, Brand, Product, Reservation, WriteOffReason, BotSettings


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
        builder.row(InlineKeyboardButton(text="➕ Добавить бренд", callback_data=f"admin:add_brand:{category_id}"))
        builder.row(InlineKeyboardButton(text="🗑 Удалить категорию", callback_data=f"admin:category:delete:{category_id}"))
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
                nav_cb = f"admin:brand_products_page:{brand_id}:{page-1}" if brand_id else f"admin:products_page:{page-1}"
                nav_buttons.append(InlineKeyboardButton(text="◀️", callback_data=nav_cb))
            nav_buttons.append(InlineKeyboardButton(text=f"{page+1}/{(total-1)//per_page+1}", callback_data="noop"))
            if end < total:
                nav_cb = f"admin:brand_products_page:{brand_id}:{page+1}" if brand_id else f"admin:products_page:{page+1}"
                nav_buttons.append(InlineKeyboardButton(text="▶️", callback_data=nav_cb))
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
        builder.row(InlineKeyboardButton(text="📊 Эта неделя", callback_data="admin:stats:this_week"))
        builder.row(InlineKeyboardButton(text="📊 Прошлая неделя", callback_data="admin:stats:last_week"))
        builder.row(InlineKeyboardButton(text="📉 Этот месяц", callback_data="admin:stats:this_month"))
        builder.row(InlineKeyboardButton(text="📉 Прошлый месяц", callback_data="admin:stats:last_month"))
        builder.row(InlineKeyboardButton(text="📋 За всё время", callback_data="admin:stats:all_time"))
        builder.row(InlineKeyboardButton(text="📦 Остатки на складе", callback_data="admin:stats:stock"))
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
    def supply_cart(has_items: bool = False, delivery: float = 0, expenses: float = 0, items_count: int = 0, page: int = 0, per_page: int = 8) -> InlineKeyboardMarkup:
        """Supply cart actions"""
        builder = InlineKeyboardBuilder()
        builder.row(InlineKeyboardButton(text="➕ Добавить товары", callback_data="admin:supply:add_item"))
        if has_items:
            builder.row(InlineKeyboardButton(
                text=f"✏️ Редактировать закупку ({items_count} поз.)",
                callback_data="admin:supply:edit_items"
            ))
            # Text pagination for cart display
            if items_count > per_page:
                total_pages = (items_count - 1) // per_page + 1
                nav = []
                if page > 0:
                    nav.append(InlineKeyboardButton(text="◀️", callback_data=f"admin:supply:cart_page:{page-1}"))
                nav.append(InlineKeyboardButton(text=f"{page+1}/{total_pages}", callback_data="noop"))
                if page + 1 < total_pages:
                    nav.append(InlineKeyboardButton(text="▶️", callback_data=f"admin:supply:cart_page:{page+1}"))
                builder.row(*nav)
            delivery_text = f"🚚 Доставка: {delivery}₽" if delivery > 0 else "🚚 Добавить доставку"
            expenses_text = f"📋 Расходы: {expenses}₽" if expenses > 0 else "📋 Добавить расходы"
            builder.row(InlineKeyboardButton(text=delivery_text, callback_data="admin:supply:delivery"))
            builder.row(InlineKeyboardButton(text=expenses_text, callback_data="admin:supply:expenses"))
            builder.row(InlineKeyboardButton(text="✅ Завершить закупку", callback_data="admin:supply:finish"))
        builder.row(InlineKeyboardButton(text="❌ Отменить", callback_data="admin:supply:cancel"))
        return builder.as_markup()

    @staticmethod
    def supply_edit_items(items: list, page: int = 0) -> InlineKeyboardMarkup:
        """Edit items list with pagination, edit and delete buttons"""
        builder = InlineKeyboardBuilder()
        per_page = 8
        total = len(items)
        start = page * per_page
        end = min(start + per_page, total)

        for idx in range(start, end):
            item = items[idx]
            name = item['name'][:20]
            builder.row(
                InlineKeyboardButton(
                    text=f"{idx+1}. {name} x{item['quantity']} ({item['purchase_price']}₽)",
                    callback_data=f"admin:supply:edit_item:{idx}"
                ),
                InlineKeyboardButton(
                    text="🗑",
                    callback_data=f"admin:supply:del_item:{idx}"
                )
            )

        # Pagination
        if total > per_page:
            nav = []
            if page > 0:
                nav.append(InlineKeyboardButton(text="◀️", callback_data=f"admin:supply:edit_page:{page-1}"))
            nav.append(InlineKeyboardButton(text=f"{page+1}/{(total-1)//per_page+1}", callback_data="noop"))
            if end < total:
                nav.append(InlineKeyboardButton(text="▶️", callback_data=f"admin:supply:edit_page:{page+1}"))
            builder.row(*nav)

        builder.row(InlineKeyboardButton(text="◀️ Назад в корзину", callback_data="admin:supply:back_to_cart"))
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
        builder.row(InlineKeyboardButton(text="🔍 Быстрая продажа (поиск)", callback_data="admin:sale:search"))
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
    def sales_history_list(sales: Sequence, page: int = 0, per_page: int = 10) -> InlineKeyboardMarkup:
        """Sales history list with pagination"""
        builder = InlineKeyboardBuilder()

        total = len(sales)
        start = page * per_page
        end = start + per_page
        page_sales = sales[start:end]

        for sale in page_sales:
            date_str = sale.sold_at.strftime("%d.%m %H:%M")
            builder.row(InlineKeyboardButton(
                text=f"💸 {date_str} • {sale.product.name} x{sale.quantity} • {sale.sale_price:.0f}₽",
                callback_data=f"admin:sale:view:{sale.id}"
            ))

        if total > per_page:
            nav_buttons = []
            if page > 0:
                nav_buttons.append(InlineKeyboardButton(text="◀️", callback_data=f"admin:sale:history:page:{page-1}"))
            nav_buttons.append(InlineKeyboardButton(text=f"{page+1}/{(total-1)//per_page+1}", callback_data="noop"))
            if end < total:
                nav_buttons.append(InlineKeyboardButton(text="▶️", callback_data=f"admin:sale:history:page:{page+1}"))
            builder.row(*nav_buttons)

        builder.row(InlineKeyboardButton(text="◀️ Назад", callback_data="admin:sales_menu"))
        return builder.as_markup()

    @staticmethod
    def sale_manage(sale_id: int) -> InlineKeyboardMarkup:
        """Manage completed sale"""
        builder = InlineKeyboardBuilder()
        builder.row(InlineKeyboardButton(text="✏️ Изменить цену", callback_data=f"admin:sale:edit_price:{sale_id}"))
        builder.row(InlineKeyboardButton(text="🗑 Удалить продажу (вернуть остаток)", callback_data=f"admin:sale:delete:{sale_id}"))
        builder.row(InlineKeyboardButton(text="◀️ К истории", callback_data="admin:sale:history"))
        return builder.as_markup()



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
        builder.row(InlineKeyboardButton(text="📋 Опубликовать прайс", callback_data="admin:publish:pricelist"))
        builder.row(InlineKeyboardButton(text="⚙️ Настройка шаблона прайса", callback_data="admin:publish:config"))
        builder.row(InlineKeyboardButton(text="⏰ Автопубликация прайса", callback_data="admin:publish:auto"))
        return builder.as_markup()

    @staticmethod
    def pricelist_config(s: 'BotSettings') -> InlineKeyboardMarkup:
        """Pricelist template config menu"""
        builder = InlineKeyboardBuilder()

        header = s.pricelist_header or "ПРАЙС-ЛИСТ"
        builder.row(InlineKeyboardButton(
            text=f"📝 Заголовок: {header[:30]}{'...' if len(header) > 30 else ''}",
            callback_data="admin:publish:config:header"
        ))

        qty_icon = "✅" if s.pricelist_show_quantities else "❌"
        builder.row(InlineKeyboardButton(
            text=f"{qty_icon} Показывать количество",
            callback_data="admin:publish:config:toggle_qty"
        ))

        brands_icon = "✅" if s.pricelist_show_brands else "❌"
        builder.row(InlineKeyboardButton(
            text=f"{brands_icon} Группировать по брендам",
            callback_data="admin:publish:config:toggle_brands"
        ))

        footer = s.pricelist_footer
        footer_text = f"📝 Подпись: {footer[:30]}{'...' if footer and len(footer) > 30 else ''}" if footer else "📝 Подпись: не задана"
        builder.row(InlineKeyboardButton(
            text=footer_text,
            callback_data="admin:publish:config:footer"
        ))

        photo_text = "🖼 Фото: установлено" if s.pricelist_photo_file_id else "🖼 Фото: не задано"
        builder.row(InlineKeyboardButton(
            text=photo_text,
            callback_data="admin:publish:config:photo"
        ))

        builder.row(InlineKeyboardButton(text="👁 Предпросмотр", callback_data="admin:publish:preview"))
        builder.row(InlineKeyboardButton(text="◀️ Назад", callback_data="admin:publications_menu"))
        return builder.as_markup()

    @staticmethod
    def pricelist_auto(s: 'BotSettings') -> InlineKeyboardMarkup:
        """Pricelist auto-publish settings"""
        builder = InlineKeyboardBuilder()

        status = "✅ Вкл" if s.pricelist_auto_enabled else "❌ Выкл"
        builder.row(InlineKeyboardButton(
            text=f"Автопубликация: {status}",
            callback_data="admin:publish:auto:toggle"
        ))

        # Frequency selection
        freq = s.pricelist_auto_frequency
        freq_buttons = []
        for v in [1, 2, 3]:
            icon = "✅ " if v == freq else ""
            freq_buttons.append(InlineKeyboardButton(
                text=f"{icon}{v}x/день",
                callback_data=f"admin:publish:auto:freq:{v}"
            ))
        builder.row(*freq_buttons)

        # Time slots
        builder.row(InlineKeyboardButton(
            text=f"⏰ Время 1: {s.pricelist_time1_hour:02d}:{s.pricelist_time1_minute:02d}",
            callback_data="admin:publish:auto:time1"
        ))
        if freq >= 2:
            builder.row(InlineKeyboardButton(
                text=f"⏰ Время 2: {s.pricelist_time2_hour:02d}:{s.pricelist_time2_minute:02d}",
                callback_data="admin:publish:auto:time2"
            ))
        if freq >= 3:
            builder.row(InlineKeyboardButton(
                text=f"⏰ Время 3: {s.pricelist_time3_hour:02d}:{s.pricelist_time3_minute:02d}",
                callback_data="admin:publish:auto:time3"
            ))

        builder.row(InlineKeyboardButton(text="◀️ Назад", callback_data="admin:publications_menu"))
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
        builder.row(InlineKeyboardButton(text="📋 Настройка логирования", callback_data="admin:settings:logging"))
        builder.row(InlineKeyboardButton(text="⏰ Настройки напоминаний", callback_data="admin:settings:reminders"))
        builder.row(InlineKeyboardButton(text="📦 Порог низкого остатка", callback_data="admin:settings:low_stock"))
        builder.row(InlineKeyboardButton(text="🔔 Время резерва", callback_data="admin:settings:reservation"))
        builder.row(InlineKeyboardButton(text="📌 Макс. резервов", callback_data="admin:settings:max_reservations"))
        builder.row(InlineKeyboardButton(text="📞 Контакты", callback_data="admin:settings:contacts"))
        builder.row(InlineKeyboardButton(text="📣 Рассылка", callback_data="admin:settings:broadcast"))
        builder.row(InlineKeyboardButton(text="🛡 Подписка для бесед", callback_data="admin:settings:market_subs"))
        builder.row(InlineKeyboardButton(text="🚫 Управление банами", callback_data="admin:settings:bans"))
        return builder.as_markup()

    @staticmethod
    def settings_logging(s: BotSettings) -> InlineKeyboardMarkup:
        """Logging settings menu"""
        builder = InlineKeyboardBuilder()

        def toggle(enabled: bool, name: str, key: str):
            icon = "✅" if enabled else "❌"
            builder.row(InlineKeyboardButton(
                text=f"{icon} {name}",
                callback_data=f"admin:settings:log_toggle:{key}"
            ))

        toggle(s.log_sales, "Продажи", "log_sales")
        toggle(s.log_supplies, "Закупки", "log_supplies")
        toggle(s.log_writeoffs, "Списания", "log_writeoffs")
        toggle(s.log_products, "Товары (создание/изменение/удаление)", "log_products")
        toggle(s.log_reservations, "Резервы", "log_reservations")
        builder.row(InlineKeyboardButton(text="◀️ Назад", callback_data="admin:settings_menu"))
        return builder.as_markup()

    @staticmethod
    def settings_reminders(s: BotSettings) -> InlineKeyboardMarkup:
        """Reminders settings menu"""
        builder = InlineKeyboardBuilder()
        status = "✅ Вкл" if s.reminder_enabled else "❌ Выкл"
        builder.row(InlineKeyboardButton(
            text=f"Напоминание: {status}",
            callback_data="admin:settings:reminder_toggle"
        ))
        builder.row(InlineKeyboardButton(
            text=f"⏰ Время: {s.reminder_hour:02d}:{s.reminder_minute:02d}",
            callback_data="admin:settings:reminder_time"
        ))
        builder.row(InlineKeyboardButton(text="◀️ Назад", callback_data="admin:settings_menu"))
        return builder.as_markup()

    @staticmethod
    def settings_low_stock(threshold: int) -> InlineKeyboardMarkup:
        """Low stock threshold settings"""
        builder = InlineKeyboardBuilder()
        builder.row(InlineKeyboardButton(
            text=f"Текущий порог: {threshold} шт.",
            callback_data="noop"
        ))
        row = []
        for v in [1, 2, 3, 5, 10]:
            icon = "✅ " if v == threshold else ""
            row.append(InlineKeyboardButton(
                text=f"{icon}{v}",
                callback_data=f"admin:settings:set_low_stock:{v}"
            ))
        builder.row(*row)
        builder.row(InlineKeyboardButton(text="◀️ Назад", callback_data="admin:settings_menu"))
        return builder.as_markup()

    @staticmethod
    def settings_reservation(hours: int) -> InlineKeyboardMarkup:
        """Reservation time settings"""
        builder = InlineKeyboardBuilder()
        builder.row(InlineKeyboardButton(
            text=f"Текущее время: {hours} ч.",
            callback_data="noop"
        ))
        row = []
        for v in [6, 12, 24, 48, 72]:
            icon = "✅ " if v == hours else ""
            row.append(InlineKeyboardButton(
                text=f"{icon}{v}ч",
                callback_data=f"admin:settings:set_reservation:{v}"
            ))
        builder.row(*row)
        builder.row(InlineKeyboardButton(text="◀️ Назад", callback_data="admin:settings_menu"))
        return builder.as_markup()

    @staticmethod
    def settings_max_reservations(current: int) -> InlineKeyboardMarkup:
        """Max reservations per user settings"""
        builder = InlineKeyboardBuilder()
        builder.row(InlineKeyboardButton(
            text=f"Текущий лимит: {current}",
            callback_data="noop"
        ))
        row = []
        for v in [1, 2, 3, 5, 10]:
            icon = "✅ " if v == current else ""
            row.append(InlineKeyboardButton(
                text=f"{icon}{v}",
                callback_data=f"admin:settings:set_max_res:{v}"
            ))
        builder.row(*row)
        builder.row(InlineKeyboardButton(text="◀️ Назад", callback_data="admin:settings_menu"))
        return builder.as_markup()

    @staticmethod
    def contacts_settings(s: BotSettings) -> InlineKeyboardMarkup:
        """Contacts settings menu"""
        builder = InlineKeyboardBuilder()
        text_status = "✅" if s.contacts_text else "❌"
        contact_status = "✅" if s.contacts_contact else "❌"
        hours_status = "✅" if s.contacts_work_hours else "❌"
        builder.row(InlineKeyboardButton(
            text=f"{text_status} Текст",
            callback_data="admin:settings:contacts:text"
        ))
        builder.row(InlineKeyboardButton(
            text=f"{contact_status} Контакт",
            callback_data="admin:settings:contacts:contact"
        ))
        builder.row(InlineKeyboardButton(
            text=f"{hours_status} Время работы",
            callback_data="admin:settings:contacts:hours"
        ))
        builder.row(InlineKeyboardButton(text="👁 Предпросмотр", callback_data="admin:settings:contacts:preview"))
        builder.row(InlineKeyboardButton(text="◀️ Назад", callback_data="admin:settings_menu"))
        return builder.as_markup()


    @staticmethod
    def market_subscriptions_list(configs: Sequence) -> InlineKeyboardMarkup:
        """Marketplace chats subscription settings list"""
        builder = InlineKeyboardBuilder()
        if configs:
            for cfg in configs:
                channels_count = len(cfg.channels) if getattr(cfg, "channels", None) else 0
                builder.row(InlineKeyboardButton(
                    text=f"💬 {cfg.chat_id} • каналов: {channels_count}",
                    callback_data=f"admin:settings:market_sub:edit:{cfg.chat_id}"
                ))
        else:
            builder.row(InlineKeyboardButton(text="Пока нет бесед", callback_data="noop"))

        builder.row(InlineKeyboardButton(text="➕ Добавить беседу", callback_data="admin:settings:market_sub:add"))
        builder.row(InlineKeyboardButton(text="◀️ Назад", callback_data="admin:settings_menu"))
        return builder.as_markup()

    @staticmethod
    def market_subscription_actions(chat_id: int, channels: Sequence[int]) -> InlineKeyboardMarkup:
        """Actions for specific marketplace chat config"""
        builder = InlineKeyboardBuilder()
        channels_text = ", ".join(str(c) for c in channels) if channels else "не заданы"
        builder.row(InlineKeyboardButton(text=f"📡 Каналы: {channels_text[:48]}", callback_data="noop"))
        builder.row(InlineKeyboardButton(
            text="✏️ Изменить каналы",
            callback_data=f"admin:settings:market_sub:set_channels:{chat_id}"
        ))
        builder.row(InlineKeyboardButton(
            text="🗑 Удалить беседу",
            callback_data=f"admin:settings:market_sub:delete:{chat_id}"
        ))
        builder.row(InlineKeyboardButton(text="◀️ Назад", callback_data="admin:settings:market_subs"))
        return builder.as_markup()

    @staticmethod
    def ban_management(banned_users: Sequence = None) -> InlineKeyboardMarkup:
        """Ban management menu"""
        builder = InlineKeyboardBuilder()
        builder.row(InlineKeyboardButton(text="🚫 Забанить пользователя", callback_data="admin:ban:add"))
        if banned_users:
            for u in banned_users:
                name = u.full_name
                builder.row(InlineKeyboardButton(
                    text=f"❌ {name} (@{u.username or u.telegram_id})",
                    callback_data=f"admin:ban:remove:{u.telegram_id}"
                ))
        builder.row(InlineKeyboardButton(text="◀️ Назад", callback_data="admin:settings_menu"))
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
