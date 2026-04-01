"""
Состояния для опроса предпочтений пользователя.
"""

from aiogram.fsm.state import State, StatesGroup


class PreferencesState(StatesGroup):
    """Состояния для опроса предпочтений."""
    
    choosing_cpu_brand = State()
    choosing_gpu_brand = State()
    choosing_gpu_need = State()
    confirming_preferences = State()
