from aiogram.fsm.state import State, StatesGroup


class AdminStates(StatesGroup):
    # Category states
    add_category_name = State()
    add_category_description = State()
    edit_category_name = State()

    # Brand states
    add_brand_name = State()
    add_brand_description = State()
    edit_brand_name = State()

    # Product states
    add_product_name = State()
    add_product_purchase_price = State()
    add_product_sale_price = State()
    add_product_quantity = State()
    add_product_photo = State()

    edit_product_sale_price = State()
    edit_product_purchase_price = State()
    edit_product_quantity = State()
    edit_product_photo = State()

    # Supply states
    supply_select_category = State()
    supply_select_brand = State()
    supply_enter_products = State()
    supply_enter_delivery = State()
    supply_enter_expenses = State()
    supply_confirm = State()
    supply_add_category_name = State()
    supply_add_brand_name = State()
    supply_edit_item = State()

    # Sale states
    sale_select_category = State()
    sale_select_brand = State()
    sale_select_product = State()
    sale_enter_quantity = State()
    sale_enter_price = State()
    sale_search = State()
    sale_edit_price = State()

    # Search states
    search_product = State()

    # Write-off states
    writeoff_select_category = State()
    writeoff_select_brand = State()
    writeoff_select_product = State()
    writeoff_select_reason = State()
    writeoff_enter_quantity = State()
    writeoff_enter_notes = State()

    # Pricelist config states
    pricelist_set_header = State()
    pricelist_set_footer = State()
    pricelist_set_photo = State()

    # Pricelist auto-publish settings states
    pricelist_set_time1 = State()
    pricelist_set_time2 = State()
    pricelist_set_time3 = State()

    # Settings states
    settings_reminder_time = State()
    settings_low_stock_custom = State()
    settings_reservation_custom = State()

    # Contacts settings states
    contacts_set_text = State()
    contacts_set_contact = State()
    contacts_set_hours = State()

    # Marketplace subscription guard states
    market_sub_chat_id = State()
    market_sub_channels = State()

    # Ban states
    ban_user_id = State()
