from aiogram.fsm.state import State, StatesGroup


class BookingStates(StatesGroup):
    choosing_service_category = State()
    choosing_service = State()
    choosing_nail_length = State()
    choosing_nail_shape = State()
    choosing_coating_type = State()
    choosing_date = State()
    choosing_time = State()
    entering_name = State()
    entering_phone = State()
    entering_comment = State()
    confirming = State()
