from aiogram.fsm.state import State, StatesGroup

class RegistrationStates(StatesGroup):
    waiting_for_name = State()
    waiting_for_role = State() # Optional, if we allow self-selection or code

class OnboardingStates(StatesGroup):
    choosing_step = State()
    processing_step = State()

class InterviewStates(StatesGroup):
    choosing_candidate = State()
    in_interview = State()
    feedback = State()
