from aiogram import Router, F, Bot
from aiogram.types import ChatMemberUpdated, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, ChatPermissions
from aiogram.enums import ChatMemberStatus

from ..database import get_db
from ..services import SubscriptionGuardService

chat_subscription_router = Router()


def _verify_keyboard(chat_id: int, user_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(
        text="✅ Подписался",
        callback_data=f"market_sub:check:{chat_id}:{user_id}"
    )]])


@chat_subscription_router.chat_member()
async def on_user_joined_market_chat(event: ChatMemberUpdated, bot: Bot):
    if not event.new_chat_member:
        return

    old_status = event.old_chat_member.status if event.old_chat_member else None
    new_status = event.new_chat_member.status

    is_join_event = (
        old_status in {ChatMemberStatus.LEFT, ChatMemberStatus.KICKED}
        and new_status in {ChatMemberStatus.MEMBER, ChatMemberStatus.RESTRICTED}
    )
    if not is_join_event:
        return

    db = await get_db()
    settings = await db.get_settings()
    config = SubscriptionGuardService.get_chat_config(settings, event.chat.id)
    if not config or not config.channels:
        return

    user_id = event.new_chat_member.user.id

    await bot.restrict_chat_member(
        chat_id=event.chat.id,
        user_id=user_id,
        permissions=ChatPermissions(
            can_send_messages=False,
            can_send_audios=False,
            can_send_documents=False,
            can_send_photos=False,
            can_send_videos=False,
            can_send_video_notes=False,
            can_send_voice_notes=False,
            can_send_polls=False,
            can_send_other_messages=False,
            can_add_web_page_previews=False,
            can_change_info=False,
            can_invite_users=False,
            can_pin_messages=False,
            can_manage_topics=False,
        ),
    )

    await bot.send_message(
        chat_id=event.chat.id,
        text=(
            "Для того чтобы писать в беседе, вам нужно подписаться на канал."
        ),
        reply_markup=_verify_keyboard(event.chat.id, user_id),
    )


@chat_subscription_router.callback_query(F.data.startswith("market_sub:check:"))
async def verify_market_subscription(callback: CallbackQuery, bot: Bot):
    _, _, chat_id_raw, user_id_raw = callback.data.split(":")
    chat_id = int(chat_id_raw)
    target_user_id = int(user_id_raw)

    if callback.from_user.id != target_user_id:
        await callback.answer("Эта кнопка не для вас", show_alert=True)
        return

    db = await get_db()
    settings = await db.get_settings()
    config = SubscriptionGuardService.get_chat_config(settings, chat_id)
    if not config or not config.channels:
        await callback.answer("Проверка отключена", show_alert=True)
        return

    for channel_id in config.channels:
        member = await bot.get_chat_member(chat_id=channel_id, user_id=target_user_id)
        if member.status in {ChatMemberStatus.LEFT, ChatMemberStatus.KICKED}:
            await callback.answer("Вы ещё не подписались на все каналы", show_alert=True)
            return

    await bot.restrict_chat_member(
        chat_id=chat_id,
        user_id=target_user_id,
        permissions=ChatPermissions(
            can_send_messages=True,
            can_send_audios=True,
            can_send_documents=True,
            can_send_photos=True,
            can_send_videos=True,
            can_send_video_notes=True,
            can_send_voice_notes=True,
            can_send_polls=True,
            can_send_other_messages=True,
            can_add_web_page_previews=True,
            can_change_info=False,
            can_invite_users=True,
            can_pin_messages=False,
            can_manage_topics=False,
        ),
    )

    await callback.answer("✅ Доступ открыт", show_alert=False)
    try:
        await callback.message.delete()
    except Exception:
        pass
