from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext

from ...database import Database
from ...database.models import User
from ...keyboards.user import UserKeyboards
from ...keyboards.common import CommonKeyboards
from ...states.user import UserStates
from ...services.scheduler import SchedulerService
from ...services.logger import LoggerService
from ...config import settings
from ...utils.formatting import format_reservation, format_product

reservations_router = Router()


@reservations_router.callback_query(F.data.startswith("user:reserve:"))
async def reserve_product_start(callback: CallbackQuery, db: Database, user: User, state: FSMContext):
    """Start reservation process"""
    # Handle view and cancel separately
    if callback.data.startswith("user:reserve:view:"):
        return await view_reservation(callback, db, user)
    if callback.data.startswith("user:reserve:cancel:"):
        return await cancel_reservation(callback, db, user)
    if callback.data.startswith("user:reserve:confirm:"):
        return await confirm_reservation(callback, db, user, state)

    product_id = int(callback.data.split(":")[-1])
    product = await db.get_product_by_id(product_id)

    if not product:
        await callback.answer("❌ Товар не найден", show_alert=True)
        return

    if product.quantity <= 0:
        await callback.answer("❌ Товар закончился", show_alert=True)
        return

    # Check if user already has active reservation for this product
    user_reservations = await db.get_user_reservations(user.id)
    for res in user_reservations:
        if res.product_id == product_id:
            await callback.answer("❌ У вас уже есть резерв на этот товар", show_alert=True)
            return

    await state.update_data(product_id=product_id)

    s = await db.get_settings()
    text = (
        f"📌 <b>Резервирование товара</b>\n\n"
        f"{format_product(product)}\n\n"
        f"⏰ Резерв действует {s.reservation_hours} часов.\n\n"
        f"Подтвердить резервирование?"
    )

    await callback.message.edit_text(
        text,
        reply_markup=UserKeyboards.reserve_confirm(product_id),
        parse_mode="HTML"
    )


async def confirm_reservation(callback: CallbackQuery, db: Database, user: User, state: FSMContext):
    """Confirm reservation"""
    product_id = int(callback.data.split(":")[-1])
    product = await db.get_product_by_id(product_id)

    if not product:
        await callback.answer("❌ Товар не найден", show_alert=True)
        return

    if product.quantity <= 0:
        await callback.answer("❌ Товар закончился", show_alert=True)
        return

    # Check if user has phone
    if not user.phone:
        await state.set_state(UserStates.reserve_contact)
        await state.update_data(product_id=product_id)

        await callback.message.edit_text(
            "📱 <b>Контактная информация</b>\n\n"
            "Для резервирования необходим ваш номер телефона.\n"
            "Нажмите кнопку ниже, чтобы отправить контакт:",
            parse_mode="HTML"
        )
        await callback.message.answer(
            "Отправьте контакт:",
            reply_markup=CommonKeyboards.request_contact()
        )
        return

    # Create reservation
    s = await db.get_settings()
    reservation = await db.create_reservation(
        product_id=product_id,
        user_id=user.id,
        hours=s.reservation_hours
    )

    if not reservation:
        await callback.answer("❌ Ошибка создания резерва", show_alert=True)
        return

    await state.clear()

    # Notify admins
    bot = callback.bot
    scheduler = SchedulerService(bot, db)
    await scheduler.notify_new_reservation(reservation)

    # Log reservation
    logger = LoggerService(bot, db)
    await logger.log_reservation_created(reservation)

    await callback.message.edit_text(
        f"✅ <b>Товар зарезервирован!</b>\n\n"
        f"{format_reservation(reservation)}\n\n"
        f"Администратор свяжется с вами для завершения покупки.",
        parse_mode="HTML"
    )

    await callback.message.answer(
        "Вернуться в меню:",
        reply_markup=UserKeyboards.main_menu()
    )


@reservations_router.message(UserStates.reserve_contact, F.contact)
async def process_contact(message: Message, db: Database, user: User, bot: Bot, state: FSMContext):
    """Process contact for reservation"""
    data = await state.get_data()
    product_id = data.get("product_id")

    if not product_id:
        await state.clear()
        await message.answer(
            "❌ Ошибка. Попробуйте снова.",
            reply_markup=UserKeyboards.main_menu()
        )
        return

    # Save phone
    phone = message.contact.phone_number
    await db.set_user_phone(user.telegram_id, phone)

    # Create reservation
    s = await db.get_settings()
    reservation = await db.create_reservation(
        product_id=product_id,
        user_id=user.id,
        hours=s.reservation_hours
    )

    if not reservation:
        await state.clear()
        await message.answer(
            "❌ Ошибка создания резерва. Возможно, товар закончился.",
            reply_markup=UserKeyboards.main_menu()
        )
        return

    await state.clear()

    # Notify admins
    scheduler = SchedulerService(bot, db)
    await scheduler.notify_new_reservation(reservation)

    # Log reservation
    logger = LoggerService(bot, db)
    await logger.log_reservation_created(reservation)

    await message.answer(
        f"✅ <b>Товар зарезервирован!</b>\n\n"
        f"{format_reservation(reservation)}\n\n"
        f"Администратор свяжется с вами для завершения покупки.",
        reply_markup=UserKeyboards.main_menu(),
        parse_mode="HTML"
    )


async def view_reservation(callback: CallbackQuery, db: Database, user: User):
    """View user's reservation"""
    reservation_id = int(callback.data.split(":")[-1])

    user_reservations = await db.get_user_reservations(user.id)
    reservation = next((r for r in user_reservations if r.id == reservation_id), None)

    if not reservation:
        await callback.answer("❌ Резерв не найден", show_alert=True)
        return

    text = format_reservation(reservation)

    await callback.message.edit_text(
        text,
        reply_markup=UserKeyboards.reservation_cancel(reservation_id),
        parse_mode="HTML"
    )


async def cancel_reservation(callback: CallbackQuery, db: Database, user: User):
    """Cancel user's reservation"""
    reservation_id = int(callback.data.split(":")[-1])

    user_reservations = await db.get_user_reservations(user.id)
    reservation = next((r for r in user_reservations if r.id == reservation_id), None)

    if not reservation:
        await callback.answer("❌ Резерв не найден", show_alert=True)
        return

    # Cancel reservation
    await db.cancel_reservation(reservation_id)

    # Log
    bot = callback.bot
    logger = LoggerService(bot, db)
    await logger.log_reservation_cancelled(reservation)

    await callback.answer("✅ Резерв отменён")

    # Show updated reservations
    reservations = await db.get_user_reservations(user.id)

    if not reservations:
        await callback.message.edit_text(
            "📌 <b>Мои резервы</b>\n\n"
            "У вас нет активных резервов.",
            parse_mode="HTML"
        )
    else:
        await callback.message.edit_text(
            f"📌 <b>Мои резервы</b> ({len(reservations)})\n\n"
            "Выберите резерв для просмотра:",
            reply_markup=UserKeyboards.my_reservations(reservations),
            parse_mode="HTML"
        )
