from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import ReplyKeyboardBuilder, InlineKeyboardBuilder


class CommonKeyboards:
    @staticmethod
    def cancel() -> ReplyKeyboardMarkup:
        """Cancel button keyboard"""
        builder = ReplyKeyboardBuilder()
        builder.add(KeyboardButton(text="❌ Отмена"))
        return builder.as_markup(resize_keyboard=True)

    @staticmethod
    def cancel_inline() -> InlineKeyboardMarkup:
        """Cancel button inline keyboard"""
        builder = InlineKeyboardBuilder()
        builder.add(InlineKeyboardButton(text="❌ Отмена", callback_data="cancel"))
        return builder.as_markup()

    @staticmethod
    def confirm(action: str = "confirm") -> InlineKeyboardMarkup:
        """Confirm/Cancel inline keyboard"""
        builder = InlineKeyboardBuilder()
        builder.row(
            InlineKeyboardButton(text="✅ Подтвердить", callback_data=f"{action}:yes"),
            InlineKeyboardButton(text="❌ Отмена", callback_data=f"{action}:no")
        )
        return builder.as_markup()

    @staticmethod
    def back(callback_data: str = "back") -> InlineKeyboardMarkup:
        """Back button"""
        builder = InlineKeyboardBuilder()
        builder.add(InlineKeyboardButton(text="◀️ Назад", callback_data=callback_data))
        return builder.as_markup()

    @staticmethod
    def skip() -> ReplyKeyboardMarkup:
        """Skip and cancel buttons"""
        builder = ReplyKeyboardBuilder()
        builder.row(
            KeyboardButton(text="⏭ Пропустить"),
            KeyboardButton(text="❌ Отмена")
        )
        return builder.as_markup(resize_keyboard=True)

    @staticmethod
    def yes_no(prefix: str = "") -> InlineKeyboardMarkup:
        """Yes/No buttons"""
        builder = InlineKeyboardBuilder()
        builder.row(
            InlineKeyboardButton(text="✅ Да", callback_data=f"{prefix}yes" if prefix else "yes"),
            InlineKeyboardButton(text="❌ Нет", callback_data=f"{prefix}no" if prefix else "no")
        )
        return builder.as_markup()

    @staticmethod
    def pagination(
        current_page: int,
        total_pages: int,
        prefix: str
    ) -> InlineKeyboardMarkup:
        """Pagination keyboard"""
        builder = InlineKeyboardBuilder()
        buttons = []

        if current_page > 1:
            buttons.append(InlineKeyboardButton(
                text="◀️",
                callback_data=f"{prefix}:page:{current_page - 1}"
            ))

        buttons.append(InlineKeyboardButton(
            text=f"{current_page}/{total_pages}",
            callback_data="noop"
        ))

        if current_page < total_pages:
            buttons.append(InlineKeyboardButton(
                text="▶️",
                callback_data=f"{prefix}:page:{current_page + 1}"
            ))

        builder.row(*buttons)
        return builder.as_markup()

    @staticmethod
    def request_contact() -> ReplyKeyboardMarkup:
        """Request contact keyboard"""
        builder = ReplyKeyboardBuilder()
        builder.add(KeyboardButton(text="📱 Отправить контакт", request_contact=True))
        builder.add(KeyboardButton(text="❌ Отмена"))
        builder.adjust(1)
        return builder.as_markup(resize_keyboard=True, one_time_keyboard=True)

    @staticmethod
    def remove() -> ReplyKeyboardMarkup:
        """Remove keyboard"""
        from aiogram.types import ReplyKeyboardRemove
        return ReplyKeyboardRemove()
