from typing import Optional
import json
import logging
from aiogram import Bot

from ..config import settings
from ..database import Database
from ..database.models import BotSettings
from ..utils.formatting import format_channel_post, format_pricelist

logger = logging.getLogger(__name__)


class ChannelService:
    """Service for managing channel publications"""

    def __init__(self, bot: Bot, db: Database):
        self.bot = bot
        self.db = db
        self.channel_id = settings.CHANNEL_ID
        self.last_error: Optional[str] = None

    async def mark_product_sold(self, product_id: int) -> bool:
        """Mark product as sold in channel"""
        if not self.channel_id:
            return False

        try:
            # Get channel post
            channel_post = await self.db.get_channel_post_by_product(product_id)
            if not channel_post:
                return False

            # Get product
            product = await self.db.get_product_by_id(product_id)
            if not product:
                return False

            # Update message
            text = format_channel_post(product, is_sold=True)

            if product.photo_file_id:
                await self.bot.edit_message_caption(
                    chat_id=channel_post.channel_id,
                    message_id=channel_post.message_id,
                    caption=text,
                    parse_mode="HTML"
                )
            else:
                await self.bot.edit_message_text(
                    chat_id=channel_post.channel_id,
                    message_id=channel_post.message_id,
                    text=text,
                    parse_mode="HTML"
                )

            # Mark as sold in database
            await self.db.mark_channel_post_sold(channel_post.id)

            return True

        except Exception as e:
            logger.exception("Failed to mark product sold product_id=%s err=%s", product_id, e)
            return False

    async def _delete_old_pricelist(self, s: BotSettings):
        """Delete previous pricelist messages from channel"""
        if not s.pricelist_last_message_ids:
            return

        try:
            msg_ids = json.loads(s.pricelist_last_message_ids)
            for msg_id in msg_ids:
                try:
                    await self.bot.delete_message(chat_id=self.channel_id, message_id=msg_id)
                except Exception as e:
                    logger.warning("Failed to delete pricelist msg id=%s chat_id=%s err=%s", msg_id, self.channel_id, e)
        except (json.JSONDecodeError, TypeError) as e:
            logger.warning("Failed to parse pricelist_last_message_ids value=%r err=%s", s.pricelist_last_message_ids, e)

    async def publish_pricelist(self, settings: Optional[BotSettings] = None) -> bool:
        """Publish full price list to channel with template settings"""
        self.last_error = None

        if not self.channel_id:
            self.last_error = "CHANNEL_ID is not configured"
            logger.error("Pricelist publish aborted: %s", self.last_error)
            return False

        try:
            products = await self.db.get_all_products(in_stock_only=True)
            if not products:
                self.last_error = "No products in stock for pricelist publication"
                logger.warning("Pricelist publish skipped: %s", self.last_error)
                return False

            if settings is None:
                settings = await self.db.get_settings()

            await self._delete_old_pricelist(settings)

            text = format_pricelist(
                products,
                header=settings.pricelist_header,
                show_quantities=settings.pricelist_show_quantities,
                show_brands=settings.pricelist_show_brands,
                footer=settings.pricelist_footer,
            )

            photo_file_id = settings.pricelist_photo_file_id
            sent_message_ids = []

            if photo_file_id:
                if len(text) <= 1024:
                    msg = await self.bot.send_photo(
                        chat_id=self.channel_id,
                        photo=photo_file_id,
                        caption=text,
                        parse_mode="HTML"
                    )
                    sent_message_ids.append(msg.message_id)
                else:
                    caption, remaining = self._split_text_for_caption(text, 1024)
                    msg = await self.bot.send_photo(
                        chat_id=self.channel_id,
                        photo=photo_file_id,
                        caption=caption,
                        parse_mode="HTML"
                    )
                    sent_message_ids.append(msg.message_id)
                    if remaining:
                        ids = await self._send_long_text(remaining)
                        sent_message_ids.extend(ids)
            else:
                ids = await self._send_long_text(text)
                sent_message_ids.extend(ids)

            await self.db.update_settings(
                pricelist_last_message_ids=json.dumps(sent_message_ids)
            )

            logger.info("Pricelist published successfully chat_id=%s messages=%s", self.channel_id, sent_message_ids)
            return True

        except Exception as e:
            self.last_error = str(e)
            logger.exception(
                "Failed to publish pricelist chat_id=%s err=%s",
                self.channel_id,
                e,
            )
            return False

    @staticmethod
    def _find_category_break(text: str, max_pos: int) -> int:
        search_area = text[:max_pos]
        marker = "\n━━━━━\n📁"
        pos = search_area.rfind(marker)
        if pos > 0:
            if pos >= 2 and text[pos-1:pos+1] == "\n\n":
                return pos - 1
            return pos
        return -1

    @staticmethod
    def _split_text_for_caption(text: str, max_caption: int = 1024) -> tuple[str, str]:
        if len(text) <= max_caption:
            return text, ""

        cut_pos = ChannelService._find_category_break(text, max_caption)

        if cut_pos <= 0:
            cut_pos = text.rfind("\n", 0, max_caption)
        if cut_pos <= 0:
            cut_pos = max_caption

        caption = text[:cut_pos].rstrip()
        remaining = text[cut_pos:].lstrip("\n")
        return caption, remaining

    async def _send_long_text(self, text: str) -> list[int]:
        sent_ids = []
        max_length = 4096
        if len(text) <= max_length:
            msg = await self.bot.send_message(
                chat_id=self.channel_id,
                text=text,
                parse_mode="HTML"
            )
            sent_ids.append(msg.message_id)
        else:
            parts = self._split_at_categories(text, max_length)
            for part in parts:
                msg = await self.bot.send_message(
                    chat_id=self.channel_id,
                    text=part.strip(),
                    parse_mode="HTML"
                )
                sent_ids.append(msg.message_id)
        return sent_ids

    @staticmethod
    def _split_at_categories(text: str, max_length: int = 4096) -> list[str]:
        if len(text) <= max_length:
            return [text]

        parts = []
        remaining = text

        while remaining:
            if len(remaining) <= max_length:
                parts.append(remaining)
                break

            cut_pos = ChannelService._find_category_break(remaining, max_length)

            if cut_pos <= 0:
                cut_pos = remaining.rfind("\n", 0, max_length)
            if cut_pos <= 0:
                cut_pos = max_length

            parts.append(remaining[:cut_pos].rstrip())
            remaining = remaining[cut_pos:].lstrip("\n")

        return parts
