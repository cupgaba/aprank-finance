from aiogram import Router, F
from aiogram.types import Message
from aiogram.fsm.context import FSMContext

from ...database import Database
from ...keyboards.user import UserKeyboards
from ...states.user import UserStates
from ...utils.formatting import format_product_short

search_router = Router()


@search_router.message(UserStates.search_query)
async def process_search(message: Message, db: Database, state: FSMContext):
    """Process search query"""
    query = message.text.strip()

    if len(query) < 2:
        await message.answer(
            "❌ Введите минимум 2 символа для поиска.\n\n"
            "Попробуйте ещё раз:"
        )
        return

    # Search products
    products = await db.search_products(query)

    await state.clear()

    if not products:
        await message.answer(
            f"🔍 <b>Поиск: {query}</b>\n\n"
            f"Ничего не найдено.\n\n"
            f"Попробуйте другой запрос или посмотрите прайс-лист.",
            reply_markup=UserKeyboards.main_menu(),
            parse_mode="HTML"
        )
        return

    text = f"🔍 <b>Поиск: {query}</b>\n\n"
    text += f"Найдено: {len(products)} товаров\n\n"

    for product in products[:20]:  # Limit to 20 results
        text += format_product_short(product) + "\n"

    if len(products) > 20:
        text += f"\n<i>...и ещё {len(products) - 20} товаров</i>"

    await message.answer(
        text,
        reply_markup=UserKeyboards.search_results(products[:10]),
        parse_mode="HTML"
    )
