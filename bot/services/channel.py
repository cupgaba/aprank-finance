from typing import Optional
import json
from aiogram import Bot

from ..config import settings
from ..database import Database
from ..database.models import BotSettings
from ..utils.formatting import format_channel_post, format_pricelist


class ChannelService:
    """Service for managing channel publications"""

    def __init__(self, bot: Bot, db: Database):
        self.bot = bot
        self.db = db
        self.channel_id = settings.CHANNEL_ID

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
            print(f"Failed to mark product sold: {e}")
            return False

    async def _delete_old_pricelist(self, settings: BotSettings):
        """Delete previous pricelist messages from channel"""
        if not settings.pricelist_last_message_ids:
            return

        try:
            msg_ids = json.loads(settings.pricelist_last_message_ids)
            for msg_id in msg_ids:
                try:
                    await self.bot.delete_message(chat_id=self.channel_id, message_id=msg_id)
                except Exception:
                    pass
        except (json.JSONDecodeError, TypeError):
            pass

    async def publish_pricelist(self, settings: Optional[BotSettings] = None) -> bool:
        """Publish full price list to channel with template settings"""
        if not self.channel_id:
            return False

        try:
            # Get all products in stock
            products = await self.db.get_all_products(in_stock_only=True)

            if not products:
                return False

            # Get template settings
            if settings is None:
                settings = await self.db.get_settings()

            # Delete old pricelist messages
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

            # If there's a photo, send photo + text
            if photo_file_id:
                # Caption limit is 1024 chars, so if text is longer split it
                if len(text) <= 1024:
                    msg = await self.bot.send_photo(
                        chat_id=self.channel_id,
                        photo=photo_file_id,
                        caption=text,
                        parse_mode="HTML"
                    )
                    sent_message_ids.append(msg.message_id)
                else:
                    # Split text: first part as photo caption, rest as follow-up
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

            # Save message IDs for future deletion
            await self.db.update_settings(
                pricelist_last_message_ids=json.dumps(sent_message_ids)
            )

            return True

        except Exception as e:
            print(f"Failed to publish pricelist: {e}")
            return False

    @staticmethod
    def _find_category_break(text: str, max_pos: int) -> int:
        """Find last category block start within max_pos.
        Category blocks start with: \\n━━━━━\\n📁
        Returns position to cut at (before the block), or -1 if not found."""
        search_area = text[:max_pos]
        # Find the opening separator followed by category icon
        marker = "\n━━━━━\n📁"
        pos = search_area.rfind(marker)
        if pos > 0:
            # Go back to include the empty line before separator
            if pos >= 2 and text[pos-1:pos+1] == "\n\n":
                return pos - 1
            return pos
        return -1

    @staticmethod
    def _split_text_for_caption(text: str, max_caption: int = 1024) -> tuple[str, str]:
        """Split text into caption + remaining, breaking at category boundary"""
        if len(text) <= max_caption:
            return text, ""

        # Try to split at category boundary first
        cut_pos = ChannelService._find_category_break(text, max_caption)

        if cut_pos <= 0:
            # No category break found, fall back to last newline
            cut_pos = text.rfind("\n", 0, max_caption)
        if cut_pos <= 0:
            cut_pos = max_caption

        caption = text[:cut_pos].rstrip()
        remaining = text[cut_pos:].lstrip("\n")
        return caption, remaining

    async def _send_long_text(self, text: str) -> list[int]:
        """Send text to channel, splitting at category boundaries if too long. Returns message IDs."""
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
        """Split text into parts, preferring category boundaries"""
        if len(text) <= max_length:
            return [text]

        parts = []
        remaining = text

        while remaining:
            if len(remaining) <= max_length:
                parts.append(remaining)
                break

            # Try category boundary first
            cut_pos = ChannelService._find_category_break(remaining, max_length)

            if cut_pos <= 0:
                # Fall back to last newline
                cut_pos = remaining.rfind("\n", 0, max_length)
            if cut_pos <= 0:
                cut_pos = max_length

            parts.append(remaining[:cut_pos].rstrip())
            remaining = remaining[cut_pos:].lstrip("\n")

        return parts
