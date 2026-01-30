from aiogram.fsm.state import State, StatesGroup


class UserStates(StatesGroup):
    # Search states
    search_query = State()

    # Reservation states
    reserve_confirm = State()
    reserve_contact = State()
