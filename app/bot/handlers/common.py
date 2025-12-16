from aiogram import Router, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from app.bot.states import RegistrationStates

router = Router()

@router.message(Command("start"))
async def cmd_start(message: types.Message, state: FSMContext):
    keyboard = types.ReplyKeyboardMarkup(
        keyboard=[
            [types.KeyboardButton(text="/onboarding")],
            [types.KeyboardButton(text="🤖 /interview")],
            [types.KeyboardButton(text="🧑‍💼 /expert"), types.KeyboardButton(text="ℹ️ /help")],
        ],
        resize_keyboard=True,
    )

    text = (
        "Привет! Это HR Training Bot.\n\n"
        "Что ожидается от кандидата:\n"
        "• Пройти онбординг: ответить на вводный вопрос, изучить материалы, рассказать что понял, пройти автооценку и загрузить карту поиска.\n"
        "• Потренировать интервью с виртуальным кандидатом.\n"
        "• При необходимости отправить задания на экспертную проверку.\n\n"
        "Напиши, пожалуйста, своё полное имя для регистрации. "
        "Если нужно — можешь сразу выбрать процесс на клавиатуре ниже."
    )

    await message.answer(text, reply_markup=keyboard)
    await state.set_state(RegistrationStates.waiting_for_name)

@router.message(Command("help"))
async def cmd_help(message: types.Message):
    await message.answer(
        "Available commands:\n"
        "/start - Start the bot\n"
        "/onboarding - Пройти онбординг (alias /labs)\n"
        "/interview - Start interview training\n"
        "/expert - Expert review\n"
        "/help - This help"
    )
