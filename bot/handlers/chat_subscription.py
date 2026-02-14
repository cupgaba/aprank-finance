import asyncio
import logging

from aiogram import Bot, F, Router
from aiogram.enums import ChatMemberStatus
from aiogram.types import (
    CallbackQuery,
    ChatMemberUpdated,
    ChatPermissions,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)

from ..database import get_db
from ..services import SubscriptionGuardService

logger = logging.getLogger(__name__)

chat_subscription_router = Router()


async def _resolve_channel_url(bot: Bot, channel_id: int) -> str | None:
    """Build best-effort public URL for channel subscription button."""
    try:
        chat = await bot.get_chat(channel_id)
    except Exception as e:
        logger.warning("[sub_guard] Failed to load chat for channel_id=%s err=%s", channel_id, e)
        return None

    if getattr(chat, "username", None):
        return f"https://t.me/{chat.username}"

    invite_link = getattr(chat, "invite_link", None)
    if invite_link:
        return invite_link

    try:
        created = await bot.create_chat_invite_link(chat_id=channel_id, creates_join_request=False)
        if created and getattr(created, "invite_link", None):
            return created.invite_link
    except Exception as e:
        logger.warning(
            "[sub_guard] Failed to create invite link for channel_id=%s err=%s",
            channel_id,
            e,
        )

    return None


async def _verify_keyboard(bot: Bot, chat_id: int, user_id: int, channels: list[int]) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []

    for index, channel_id in enumerate(channels, start=1):
        url = await _resolve_channel_url(bot, channel_id)
        if not url:
            continue
        rows.append([
            InlineKeyboardButton(
                text=f"📢 Подписаться {index}",
                url=url,
            )
        ])

    rows.append([
        InlineKeyboardButton(
            text="✅ Подписался",
            callback_data=f"market_sub:check:{chat_id}:{user_id}",
        )
    ])

    return InlineKeyboardMarkup(inline_keyboard=rows)


async def _apply_join_restriction(bot: Bot, chat_id: int, user_id: int):
    """Restrict newly joined member and send verification prompt."""
    logger.info("[sub_guard] Join flow started chat_id=%s user_id=%s", chat_id, user_id)

    db = await get_db()
    settings = await db.get_settings()
    config = SubscriptionGuardService.get_chat_config(settings, chat_id)
    if not config or not config.channels:
        logger.info(
            "[sub_guard] No config/channels for chat_id=%s. Restriction skipped.",
            chat_id,
        )
        return

    logger.info(
        "[sub_guard] Config found for chat_id=%s channels=%s",
        chat_id,
        config.channels,
    )

    # Avoid duplicate prompts when both chat_member and service message arrive
    try:
        current_member = await bot.get_chat_member(chat_id=chat_id, user_id=user_id)
        if current_member.status == ChatMemberStatus.RESTRICTED and getattr(current_member, "can_send_messages", True) is False:
            logger.info(
                "[sub_guard] User already restricted chat_id=%s user_id=%s. Skip duplicate prompt.",
                chat_id,
                user_id,
            )
            return
    except Exception as e:
        logger.warning(
            "[sub_guard] Failed to pre-check member state chat_id=%s user_id=%s err=%s",
            chat_id,
            user_id,
            e,
        )

    try:
        await bot.restrict_chat_member(
            chat_id=chat_id,
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
        logger.info("[sub_guard] User restricted chat_id=%s user_id=%s", chat_id, user_id)
    except Exception as e:
        logger.exception(
            "[sub_guard] Failed to restrict user chat_id=%s user_id=%s err=%s",
            chat_id,
            user_id,
            e,
        )
        return

    try:
        prompt_message = await bot.send_message(
            chat_id=chat_id,
            text="Для того чтобы писать в беседе, вам нужно подписаться на канал.",
            reply_markup=await _verify_keyboard(bot, chat_id, user_id, config.channels),
        )
        logger.info("[sub_guard] Prompt sent chat_id=%s user_id=%s", chat_id, user_id)
        asyncio.create_task(_delete_prompt_later(bot, chat_id, prompt_message.message_id, delay_seconds=60))
    except Exception as e:
        logger.exception(
            "[sub_guard] Failed to send prompt chat_id=%s user_id=%s err=%s",
            chat_id,
            user_id,
            e,
        )


async def _delete_prompt_later(bot: Bot, chat_id: int, message_id: int, delay_seconds: int = 60):
    await asyncio.sleep(delay_seconds)
    try:
        await bot.delete_message(chat_id=chat_id, message_id=message_id)
        logger.info("[sub_guard] Prompt auto-deleted chat_id=%s message_id=%s", chat_id, message_id)
    except Exception as e:
        logger.debug("[sub_guard] Prompt was not deleted chat_id=%s message_id=%s err=%s", chat_id, message_id, e)



@chat_subscription_router.chat_member()
async def on_user_joined_market_chat(event: ChatMemberUpdated, bot: Bot):
    if not event.new_chat_member:
        logger.info("[sub_guard] chat_member update without new_chat_member chat_id=%s", event.chat.id)
        return

    old_status = event.old_chat_member.status if event.old_chat_member else None
    new_status = event.new_chat_member.status

    logger.info(
        "[sub_guard] chat_member update chat_id=%s user_id=%s old_status=%s new_status=%s",
        event.chat.id,
        event.new_chat_member.user.id,
        old_status,
        new_status,
    )

    is_join_event = (
        old_status in {ChatMemberStatus.LEFT, ChatMemberStatus.KICKED}
        and new_status in {ChatMemberStatus.MEMBER, ChatMemberStatus.RESTRICTED}
    )
    if not is_join_event:
        logger.info(
            "[sub_guard] chat_member not treated as join chat_id=%s user_id=%s",
            event.chat.id,
            event.new_chat_member.user.id,
        )
        return

    await _apply_join_restriction(
        bot=bot,
        chat_id=event.chat.id,
        user_id=event.new_chat_member.user.id,
    )


@chat_subscription_router.message(F.new_chat_members)
async def on_new_chat_members_message(message: Message, bot: Bot):
    """Fallback for chats where chat_member updates may not arrive."""
    if not message.new_chat_members:
        logger.info("[sub_guard] new_chat_members handler called without members chat_id=%s", message.chat.id)
        return

    logger.info(
        "[sub_guard] service new_chat_members chat_id=%s count=%s member_ids=%s",
        message.chat.id,
        len(message.new_chat_members),
        [m.id for m in message.new_chat_members],
    )

    for member in message.new_chat_members:
        if member.is_bot:
            logger.info("[sub_guard] Skipping bot join chat_id=%s user_id=%s", message.chat.id, member.id)
            continue
        await _apply_join_restriction(bot=bot, chat_id=message.chat.id, user_id=member.id)


@chat_subscription_router.callback_query(F.data.startswith("market_sub:check:"))
async def verify_market_subscription(callback: CallbackQuery, bot: Bot):
    _, _, chat_id_raw, user_id_raw = callback.data.split(":")
    chat_id = int(chat_id_raw)
    target_user_id = int(user_id_raw)

    logger.info(
        "[sub_guard] Verify clicked chat_id=%s target_user_id=%s clicker_id=%s",
        chat_id,
        target_user_id,
        callback.from_user.id,
    )

    if callback.from_user.id != target_user_id:
        await callback.answer("Эта кнопка не для вас", show_alert=True)
        return

    db = await get_db()
    settings = await db.get_settings()
    config = SubscriptionGuardService.get_chat_config(settings, chat_id)
    if not config or not config.channels:
        logger.info("[sub_guard] Verify failed: no config for chat_id=%s", chat_id)
        await callback.answer("Проверка отключена", show_alert=True)
        return

    for channel_id in config.channels:
        try:
            member = await bot.get_chat_member(chat_id=channel_id, user_id=target_user_id)
        except Exception as e:
            logger.exception(
                "[sub_guard] Verify API error channel_id=%s user_id=%s err=%s",
                channel_id,
                target_user_id,
                e,
            )
            await callback.answer(
                "Не удалось проверить подписку. Убедитесь, что бот админ в канале.",
                show_alert=True,
            )
            return

        if member.status in {ChatMemberStatus.LEFT, ChatMemberStatus.KICKED}:
            logger.info(
                "[sub_guard] Verify failed: not subscribed channel_id=%s user_id=%s status=%s",
                channel_id,
                target_user_id,
                member.status,
            )
            await callback.answer("Вы ещё не подписались на все каналы", show_alert=True)
            return

    try:
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
        logger.info("[sub_guard] Access granted chat_id=%s user_id=%s", chat_id, target_user_id)
    except Exception as e:
        logger.exception(
            "[sub_guard] Failed to grant access chat_id=%s user_id=%s err=%s",
            chat_id,
            target_user_id,
            e,
        )
        await callback.answer("Не удалось открыть доступ, попробуйте ещё раз", show_alert=True)
        return

    await callback.answer("✅ Доступ открыт", show_alert=False)
    try:
        await callback.message.delete()
    except Exception:
        pass
