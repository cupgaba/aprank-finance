from typing import Optional
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

            text = format_pricelist(
                products,
                header=settings.pricelist_header,
                show_quantities=settings.pricelist_show_quantities,
                show_brands=settings.pricelist_show_brands,
                footer=settings.pricelist_footer,
            )

            photo_file_id = settings.pricelist_photo_file_id

            # If there's a photo, send photo + text
            if photo_file_id:
                # Caption limit is 1024 chars, so if text is longer split it
                if len(text) <= 1024:
                    await self.bot.send_photo(
                        chat_id=self.channel_id,
                        photo=photo_file_id,
                        caption=text,
                        parse_mode="HTML"
                    )
                else:
                    # Split text: first part as photo caption, rest as follow-up
                    caption, remaining = self._split_text_for_caption(text, 1024)
                    await self.bot.send_photo(
                        chat_id=self.channel_id,
                        photo=photo_file_id,
                        caption=caption,
                        parse_mode="HTML"
                    )
                    if remaining:
                        await self._send_long_text(remaining)
            else:
                await self._send_long_text(text)

            return True

        except Exception as e:
            print(f"Failed to publish pricelist: {e}")
            return False

    @staticmethod
    def _split_text_for_caption(text: str, max_caption: int = 1024) -> tuple[str, str]:
        """Split text into caption + remaining, breaking at line boundary"""
        if len(text) <= max_caption:
            return text, ""

        # Find last newline within the limit
        cut_pos = text.rfind("\n", 0, max_caption)
        if cut_pos <= 0:
            # No good line break found, cut at limit
            cut_pos = max_caption

        caption = text[:cut_pos].rstrip()
        remaining = text[cut_pos:].lstrip("\n")
        return caption, remaining

    async def _send_long_text(self, text: str) -> None:
        """Send text to channel, splitting if too long"""
        max_length = 4096
        if len(text) <= max_length:
            await self.bot.send_message(
                chat_id=self.channel_id,
                text=text,
                parse_mode="HTML"
            )
        else:
            parts = []
            current_part = ""
            for line in text.split("\n"):
                if len(current_part) + len(line) + 1 > max_length:
                    parts.append(current_part)
                    current_part = line
                else:
                    current_part += "\n" + line if current_part else line
            if current_part:
                parts.append(current_part)

            for part in parts:
                await self.bot.send_message(
                    chat_id=self.channel_id,
                    text=part,
                    parse_mode="HTML"
                )
