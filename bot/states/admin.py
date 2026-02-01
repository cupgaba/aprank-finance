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

    # Sale states
    sale_select_category = State()
    sale_select_brand = State()
    sale_select_product = State()
    sale_enter_quantity = State()
    sale_enter_price = State()

    # Write-off states
    writeoff_select_category = State()
    writeoff_select_brand = State()
    writeoff_select_product = State()
    writeoff_select_reason = State()
    writeoff_enter_quantity = State()
    writeoff_enter_notes = State()

    # Publication states
    publish_select_category = State()
    publish_select_brand = State()
    publish_select_product = State()
    publish_add_photo = State()
    publish_confirm = State()

    # Settings states
    settings_add_admin = State()
    settings_channel_id = State()
    settings_log_channel_id = State()
    settings_reminder_time = State()
