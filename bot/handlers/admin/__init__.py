from aiogram import Router

from .menu import menu_router
from .categories import categories_router
from .brands import brands_router
from .products import products_router
from .supplies import supplies_router
from .sales import sales_router
from .writeoffs import writeoffs_router
from .statistics import statistics_router
from .publications import publications_router
from .reservations import reservations_router

admin_router = Router()

# Include all admin routers
admin_router.include_router(menu_router)
admin_router.include_router(categories_router)
admin_router.include_router(brands_router)
admin_router.include_router(products_router)
admin_router.include_router(supplies_router)
admin_router.include_router(sales_router)
admin_router.include_router(writeoffs_router)
admin_router.include_router(statistics_router)
admin_router.include_router(publications_router)
admin_router.include_router(reservations_router)
