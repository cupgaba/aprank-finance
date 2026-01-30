from typing import Optional
from aiogram import Bot
from aiogram.types import InputMediaPhoto

from ..config import settings
from ..database import Database
from ..database.models import Product, ChannelPost
from ..utils.formatting import format_channel_post, format_pricelist


class ChannelService:
    """Service for managing channel publications"""

    def __init__(self, bot: Bot, db: Database):
        self.bot = bot
        self.db = db
        self.channel_id = settings.CHANNEL_ID

    async def publish_product(self, product: Product) -> Optional[ChannelPost]:
        """Publish product to channel"""
        if not self.channel_id:
            return None

        try:
            text = format_channel_post(product)

            if product.photo_file_id:
                message = await self.bot.send_photo(
                    chat_id=self.channel_id,
                    photo=product.photo_file_id,
                    caption=text,
                    parse_mode="HTML"
                )
            else:
                message = await self.bot.send_message(
                    chat_id=self.channel_id,
                    text=text,
                    parse_mode="HTML"
                )

            # Save channel post to database
            channel_post = await self.db.create_channel_post(
                product_id=product.id,
                message_id=message.message_id,
                channel_id=self.channel_id
            )

            return channel_post

        except Exception as e:
            print(f"Failed to publish product: {e}")
            return None

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

    async def publish_pricelist(self) -> bool:
        """Publish full price list to channel"""
        if not self.channel_id:
            return False

        try:
            # Get all products in stock
            products = await self.db.get_all_products(in_stock_only=True)

            if not products:
                return False

            text = format_pricelist(products)

            # Split message if too long
            max_length = 4096
            if len(text) > max_length:
                # Send multiple messages
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
            else:
                await self.bot.send_message(
                    chat_id=self.channel_id,
                    text=text,
                    parse_mode="HTML"
                )

            return True

        except Exception as e:
            print(f"Failed to publish pricelist: {e}")
            return False
