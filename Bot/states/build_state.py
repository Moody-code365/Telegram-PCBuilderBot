from aiogram.fsm.state import StatesGroup, State

class BuildPC(StatesGroup):
    budget = State()
    usage = State()
    preferences = State()