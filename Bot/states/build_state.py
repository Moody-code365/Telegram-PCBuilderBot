from aiogram.fsm.state import StatesGroup, State

class BuildPC(StatesGroup):
    budget = State()
    purpose = State()
    form_factor = State()
    preferences = State()