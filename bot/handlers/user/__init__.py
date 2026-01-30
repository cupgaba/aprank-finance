from aiogram import Router

from .menu import menu_router
from .pricelist import pricelist_router
from .reservations import reservations_router
from .search import search_router

user_router = Router()

# Include all user routers
user_router.include_router(menu_router)
user_router.include_router(pricelist_router)
user_router.include_router(reservations_router)
user_router.include_router(search_router)
