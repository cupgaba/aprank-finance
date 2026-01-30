from aiogram import Router, F, Bot
from aiogram.types import CallbackQuery
from aiogram.fsm.context import FSMContext

from ...database import Database
from ...database.models import User
from ...keyboards.admin import AdminKeyboards
from ...services.logger import LoggerService
from ...utils.formatting import format_reservation

reservations_router = Router()


@reservations_router.callback_query(F.data == "admin:reserve:active")
async def active_reservations(callback: CallbackQuery, db: Database, is_admin: bool):
    """Show active reservations"""
    if not is_admin:
        await callback.answer("⛔️ Нет доступа", show_alert=True)
        return

    reservations = await db.get_active_reservations()

    if not reservations:
        await callback.message.edit_text(
            "🔔 <b>Активные резервы</b>\n\n"
            "Нет активных резервов.",
            reply_markup=AdminKeyboards.reservations_menu(),
            parse_mode="HTML"
        )
        return

    await callback.message.edit_text(
        f"🔔 <b>Активные резервы</b> ({len(reservations)})\n\n"
        "Выберите резерв для просмотра:",
        reply_markup=AdminKeyboards.reservations_list(reservations),
        parse_mode="HTML"
    )


@reservations_router.callback_query(F.data == "admin:reserve:expiring")
async def expiring_reservations(callback: CallbackQuery, db: Database, is_admin: bool):
    """Show expiring reservations"""
    if not is_admin:
        await callback.answer("⛔️ Нет доступа", show_alert=True)
        return

    reservations = await db.get_expiring_reservations(hours=4)

    if not reservations:
        await callback.message.edit_text(
            "⏰ <b>Истекающие резервы</b>\n\n"
            "Нет резервов, истекающих в ближайшие 4 часа.",
            reply_markup=AdminKeyboards.reservations_menu(),
            parse_mode="HTML"
        )
        return

    await callback.message.edit_text(
        f"⏰ <b>Истекающие резервы</b> ({len(reservations)})\n\n"
        "Выберите резерв для просмотра:",
        reply_markup=AdminKeyboards.reservations_list(reservations),
        parse_mode="HTML"
    )


@reservations_router.callback_query(F.data.startswith("admin:reserve:view:"))
async def view_reservation(callback: CallbackQuery, db: Database, is_admin: bool):
    """View reservation details"""
    if not is_admin:
        await callback.answer("⛔️ Нет доступа", show_alert=True)
        return

    reservation_id = int(callback.data.split(":")[-1])

    # Get fresh reservation data
    reservations = await db.get_active_reservations()
    reservation = next((r for r in reservations if r.id == reservation_id), None)

    if not reservation:
        await callback.answer("❌ Резерв не найден или уже завершён", show_alert=True)
        return

    text = format_reservation(reservation, for_admin=True)

    await callback.message.edit_text(
        text,
        reply_markup=AdminKeyboards.reservation_actions(reservation),
        parse_mode="HTML"
    )


@reservations_router.callback_query(F.data.startswith("admin:reserve:complete:"))
async def complete_reservation(
    callback: CallbackQuery,
    db: Database,
    user: User,
    bot: Bot,
    is_admin: bool
):
    """Complete reservation (product sold)"""
    if not is_admin:
        await callback.answer("⛔️ Нет доступа", show_alert=True)
        return

    reservation_id = int(callback.data.split(":")[-1])

    # Get reservation first for logging
    reservations = await db.get_active_reservations()
    reservation = next((r for r in reservations if r.id == reservation_id), None)

    if not reservation:
        await callback.answer("❌ Резерв не найден или уже завершён", show_alert=True)
        return

    # Complete reservation
    await db.complete_reservation(reservation_id)

    # Log completion
    logger = LoggerService(bot)
    await logger.log_reservation_completed(reservation, user)

    await callback.answer("✅ Резерв завершён")

    # Return to active reservations
    reservations = await db.get_active_reservations()

    if not reservations:
        await callback.message.edit_text(
            "🔔 <b>Активные резервы</b>\n\n"
            "Нет активных резервов.",
            reply_markup=AdminKeyboards.reservations_menu(),
            parse_mode="HTML"
        )
    else:
        await callback.message.edit_text(
            f"🔔 <b>Активные резервы</b> ({len(reservations)})\n\n"
            "Выберите резерв для просмотра:",
            reply_markup=AdminKeyboards.reservations_list(reservations),
            parse_mode="HTML"
        )


@reservations_router.callback_query(F.data.startswith("admin:reserve:cancel:"))
async def cancel_reservation(
    callback: CallbackQuery,
    db: Database,
    user: User,
    bot: Bot,
    is_admin: bool
):
    """Cancel reservation"""
    if not is_admin:
        await callback.answer("⛔️ Нет доступа", show_alert=True)
        return

    reservation_id = int(callback.data.split(":")[-1])

    # Get reservation first for logging
    reservations = await db.get_active_reservations()
    reservation = next((r for r in reservations if r.id == reservation_id), None)

    if not reservation:
        await callback.answer("❌ Резерв не найден или уже завершён", show_alert=True)
        return

    # Cancel reservation (returns product to stock)
    await db.cancel_reservation(reservation_id)

    # Log cancellation
    logger = LoggerService(bot)
    await logger.log_reservation_cancelled(reservation, user)

    # Notify user about cancellation
    try:
        await bot.send_message(
            chat_id=reservation.user.telegram_id,
            text=(
                f"❌ <b>Ваш резерв отменён</b>\n\n"
                f"Товар: {reservation.product.full_name}\n\n"
                f"Товар возвращён в продажу."
            ),
            parse_mode="HTML"
        )
    except Exception:
        pass

    await callback.answer("✅ Резерв отменён, товар возвращён в наличие")

    # Return to active reservations
    reservations = await db.get_active_reservations()

    if not reservations:
        await callback.message.edit_text(
            "🔔 <b>Активные резервы</b>\n\n"
            "Нет активных резервов.",
            reply_markup=AdminKeyboards.reservations_menu(),
            parse_mode="HTML"
        )
    else:
        await callback.message.edit_text(
            f"🔔 <b>Активные резервы</b> ({len(reservations)})\n\n"
            "Выберите резерв для просмотра:",
            reply_markup=AdminKeyboards.reservations_list(reservations),
            parse_mode="HTML"
        )
