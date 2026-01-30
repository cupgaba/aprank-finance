from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import ReplyKeyboardBuilder, InlineKeyboardBuilder
from typing import Sequence

from ..database.models import Category, Brand, Product, Reservation


class UserKeyboards:
    @staticmethod
    def main_menu() -> ReplyKeyboardMarkup:
        """User main menu"""
        builder = ReplyKeyboardBuilder()
        builder.row(
            KeyboardButton(text="📋 Прайс-лист"),
            KeyboardButton(text="🔍 Поиск")
        )
        builder.row(
            KeyboardButton(text="📌 Мои резервы"),
            KeyboardButton(text="📞 Контакты")
        )
        return builder.as_markup(resize_keyboard=True)

    @staticmethod
    def pricelist_categories(categories: Sequence[Category]) -> InlineKeyboardMarkup:
        """Categories for price list"""
        builder = InlineKeyboardBuilder()
        builder.row(InlineKeyboardButton(text="📋 Весь прайс-лист", callback_data="user:pricelist:all"))
        for cat in categories:
            builder.row(InlineKeyboardButton(
                text=f"📁 {cat.name}",
                callback_data=f"user:pricelist:cat:{cat.id}"
            ))
        return builder.as_markup()

    @staticmethod
    def pricelist_brands(brands: Sequence[Brand], category_id: int) -> InlineKeyboardMarkup:
        """Brands for price list"""
        builder = InlineKeyboardBuilder()
        for brand in brands:
            builder.row(InlineKeyboardButton(
                text=f"🏷 {brand.name}",
                callback_data=f"user:pricelist:brand:{brand.id}"
            ))
        builder.row(InlineKeyboardButton(text="◀️ Назад", callback_data="user:pricelist:menu"))
        return builder.as_markup()

    @staticmethod
    def products_list(
        products: Sequence[Product],
        back_callback: str = "user:pricelist:menu"
    ) -> InlineKeyboardMarkup:
        """Products list with reserve option"""
        builder = InlineKeyboardBuilder()
        for product in products:
            if product.quantity > 0:
                builder.row(InlineKeyboardButton(
                    text=f"📌 Резерв: {product.name}",
                    callback_data=f"user:reserve:{product.id}"
                ))
        builder.row(InlineKeyboardButton(text="◀️ Назад", callback_data=back_callback))
        return builder.as_markup()

    @staticmethod
    def reserve_confirm(product_id: int) -> InlineKeyboardMarkup:
        """Confirm reservation"""
        builder = InlineKeyboardBuilder()
        builder.row(
            InlineKeyboardButton(text="✅ Подтвердить", callback_data=f"user:reserve:confirm:{product_id}"),
            InlineKeyboardButton(text="❌ Отмена", callback_data="user:pricelist:menu")
        )
        return builder.as_markup()

    @staticmethod
    def reservation_cancel(reservation_id: int) -> InlineKeyboardMarkup:
        """Cancel reservation button"""
        builder = InlineKeyboardBuilder()
        builder.row(InlineKeyboardButton(
            text="❌ Отменить резерв",
            callback_data=f"user:reserve:cancel:{reservation_id}"
        ))
        return builder.as_markup()

    @staticmethod
    def my_reservations(reservations: Sequence[Reservation]) -> InlineKeyboardMarkup:
        """User's reservations list"""
        builder = InlineKeyboardBuilder()
        for res in reservations:
            expires = res.expires_at.strftime("%d.%m %H:%M")
            builder.row(InlineKeyboardButton(
                text=f"🔔 {res.product.name} (до {expires})",
                callback_data=f"user:reserve:view:{res.id}"
            ))
        return builder.as_markup()

    @staticmethod
    def search_results(products: Sequence[Product]) -> InlineKeyboardMarkup:
        """Search results"""
        builder = InlineKeyboardBuilder()
        for product in products:
            status = "✅" if product.quantity > 0 else "❌"
            text = f"{status} {product.brand.name} - {product.name}"
            if product.quantity > 0:
                builder.row(InlineKeyboardButton(
                    text=text,
                    callback_data=f"user:product:{product.id}"
                ))
            else:
                builder.row(InlineKeyboardButton(
                    text=text,
                    callback_data="user:product:unavailable"
                ))
        return builder.as_markup()

    @staticmethod
    def product_view(product: Product) -> InlineKeyboardMarkup:
        """Product view with reserve option"""
        builder = InlineKeyboardBuilder()
        if product.quantity > 0:
            builder.row(InlineKeyboardButton(
                text="📌 Зарезервировать",
                callback_data=f"user:reserve:{product.id}"
            ))
        builder.row(InlineKeyboardButton(text="◀️ Назад", callback_data="user:pricelist:menu"))
        return builder.as_markup()
