from aiogram import Router, types
from aiogram.fsm.context import FSMContext
from app.bot.states import RegistrationStates
from app.database.base import get_session
from app.database.models import User
from sqlalchemy.future import select

router = Router()

@router.message(RegistrationStates.waiting_for_name)
async def process_name(message: types.Message, state: FSMContext):
    full_name = message.text
    user_id = message.from_user.id
    username = message.from_user.username

    # Save to DB
    async for session in get_session():
        # Check if user exists
        result = await session.execute(select(User).where(User.telegram_id == user_id))
        user = result.scalar_one_or_none()
        
        if not user:
            user = User(telegram_id=user_id, username=username, full_name=full_name)
            session.add(user)
        else:
            user.full_name = full_name
        
        await session.commit()
    
    await message.answer(f"Nice to meet you, {full_name}! You are now registered.")
    await state.clear()
