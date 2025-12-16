import os
import re
from datetime import datetime
from aiogram import Router, types, Bot
from aiogram.fsm.context import FSMContext
from aiogram.filters import Command
from app.bot.states import OnboardingStates
from app.core.search_map import SearchMapValidator
from app.core.llm_client import llm_client
from app.database.base import get_session
from app.database.models import OnboardingSubmission, User, OnboardingStep, StepType
from sqlalchemy.future import select
from sqlalchemy import and_

router = Router()

async def get_next_step(user_id: int, session):
    """
    Определяем следующий шаг онбординга по уже выполненным шагам.
    """
    result = await session.execute(
        select(OnboardingSubmission.step_id).where(
            and_(
                OnboardingSubmission.user_id == user_id,
                OnboardingSubmission.status.in_(["checked", "approved", "pending"])
            )
        )
    )
    completed_step_ids = result.scalars().all()

    steps_result = await session.execute(select(OnboardingStep).order_by(OnboardingStep.order))
    all_steps = steps_result.scalars().all()

    for step in all_steps:
        if step.id not in completed_step_ids:
            return step
    return None

async def show_step(message: types.Message, step: OnboardingStep, state: FSMContext):
    text = f"<b>Шаг {step.order}: {step.title}</b>\n\n"
    text += f"{step.description}\n\n"

    if step.content_url:
        text += f"🔗 <a href='{step.content_url}'>Материал</a>\n"

    text += f"<i>Оценочное время: {step.estimated_duration} мин</i>"

    step_started_at = datetime.now()
    await state.update_data(
        current_step_id=step.id,
        step_type=step.step_type,
        step_started_at=step_started_at,
        estimated_duration=step.estimated_duration
    )

    if step.step_type in [StepType.CONTENT, StepType.OFFLINE, StepType.CONFIRMATION]:
        keyboard = types.ReplyKeyboardMarkup(
            keyboard=[[types.KeyboardButton(text="Готово ✅")]],
            resize_keyboard=True
        )
        await message.answer(text, parse_mode="HTML", reply_markup=keyboard)
    elif step.step_type in [StepType.TEXT_INPUT, StepType.QUESTION, StepType.SELF_REPORT]:
        await message.answer(text + "\n\n👇 Напиши свой ответ ниже:", parse_mode="HTML", reply_markup=types.ReplyKeyboardRemove())
    elif step.step_type == StepType.EVALUATION:
        await message.answer(
            text + "\n\nНажми кнопку, чтобы получить оценку по предыдущему ответу.",
            parse_mode="HTML",
            reply_markup=types.ReplyKeyboardMarkup(
                keyboard=[[types.KeyboardButton(text="Оценить результат")]],
                resize_keyboard=True
            ),
        )
    elif step.step_type == StepType.FILE_UPLOAD:
        await message.answer(text + "\n\n👇 Загрузите файл карты поиска (Excel):", parse_mode="HTML", reply_markup=types.ReplyKeyboardRemove())

    await state.set_state(OnboardingStates.processing_step)

async def evaluate_answer(previous_answer: str, step_description: str) -> dict:
    """
    Запрашиваем у LLM оценку ответа. Возвращаем словарь с score и comment.
    """
    if not previous_answer:
        return {"score": None, "comment": "Нет ответа для оценки"}

    prompt = f"""
Ты наставник для HR-стажёра. Оцени его ответ по шагу онбординга.

Описание шага:
{step_description}

Ответ стажёра:
\"\"\"{previous_answer}\"\"\"

Верни кратко оценку в формате:
Оценка (1-5): X
Комментарий: <кратко, 1-2 предложения>
"""
    try:
        feedback = await llm_client.generate_response(prompt)
    except Exception as e:
        feedback = f"LLM недоступен: {e}"

    score = None
    if feedback:
        match = re.search(r'([1-5])', feedback)
        if match:
            score = float(match.group(1))

    return {"score": score, "comment": feedback}

@router.message(Command("onboarding"))
@router.message(Command("labs"))  # совместимость со старой командой
async def cmd_onboarding(message: types.Message, state: FSMContext):
    async for session in get_session():
        result = await session.execute(select(User).where(User.telegram_id == message.from_user.id))
        user = result.scalar_one_or_none()
        if not user:
            await message.answer("Сначала зарегистрируйся через /start")
            return

        step = await get_next_step(user.id, session)
        if not step:
            await message.answer("🎉 Онбординг завершён! Отличная работа!")
            return

        await show_step(message, step, state)

@router.message(Command("get_report"))
async def cmd_get_report(message: types.Message, bot: Bot):
    """Команда для получения Excel отчета по онбордингу в любое время"""
    async for session in get_session():
        result = await session.execute(select(User).where(User.telegram_id == message.from_user.id))
        user = result.scalar_one_or_none()
        if not user:
            await message.answer("❌ Сначала зарегистрируйся через /start")
            return
        
        await message.answer("⏳ Генерирую отчет по онбордингу с AI-оценками...\n\nЭто может занять 30-60 секунд ⏱️")
        
        try:
            from app.bot.reports.simple_report_generator import SimpleOnboardingReportGenerator
            from sqlalchemy.orm import selectinload
            
            # Получаем все submissions пользователя
            submissions_result = await session.execute(
                select(OnboardingSubmission)
                .where(OnboardingSubmission.user_id == user.id)
                .options(selectinload(OnboardingSubmission.step))
                .options(selectinload(OnboardingSubmission.user))
            )
            all_submissions = submissions_result.scalars().all()
            
            if not all_submissions:
                await message.answer("⚠️ У тебя пока нет выполненных шагов онбординга.\nНачни с команды /onboarding")
                return
            
            # Генерируем Excel с LLM оценками (асинхронно)
            generator = SimpleOnboardingReportGenerator(all_submissions)
            excel_bytes = await generator.generate_async()
            
            # Отправляем файл
            from aiogram.types import BufferedInputFile
            file = BufferedInputFile(
                excel_bytes,
                filename=f"Отчет_онбординг_{user.full_name or 'стажер'}_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx"
            )
            
            completed_count = len(all_submissions)
            await bot.send_document(
                message.chat.id,
                file,
                caption=f"✅ Твой AI-отчет по онбордингу готов!\n\n📊 Выполнено шагов: {completed_count}/36\n🤖 Оценка от AI\n📅 Дата: {datetime.now().strftime('%d.%m.%Y %H:%M')}"
            )
        except Exception as e:
            import traceback
            error_details = traceback.format_exc()
            print(f"Report generation error: {error_details}")
            await message.answer(f"⚠️ Ошибка при генерации отчета: {str(e)}\nПопробуй позже или обратись к наставнику.")


@router.message(OnboardingStates.processing_step)
async def process_step_action(message: types.Message, state: FSMContext, bot: Bot):
    data = await state.get_data()
    step_id = data.get("current_step_id")
    step_type = data.get("step_type")
    last_text_answer = data.get("last_text_answer")

    if not step_id:
        await message.answer("Сессия истекла. Введи /onboarding ещё раз.")
        return

    async for session in get_session():
        result = await session.execute(select(User).where(User.telegram_id == message.from_user.id))
        user = result.scalar_one_or_none()

        step_result = await session.execute(select(OnboardingStep).where(OnboardingStep.id == step_id))
        step = step_result.scalar_one_or_none()

        submission = OnboardingSubmission(
            user_id=user.id,
            step_id=step_id,
            status="checked",
            started_at=data.get("step_started_at")
        )
        submission.created_at = datetime.now()

        estimated_duration = data.get("estimated_duration", 0)
        if submission.started_at and estimated_duration > 0:
            completion_time = submission.get_completion_time_minutes()
            if completion_time < estimated_duration * 0.3:
                submission.time_warning = "too_fast"
                await message.answer(
                    f"⚠️ Очень быстро ({completion_time:.1f} мин при норме {estimated_duration}). Проверь, всё ли сделал.",
                    parse_mode="HTML"
                )
            elif completion_time > estimated_duration * 3:
                submission.time_warning = "too_slow"
                await message.answer(
                    f"ℹ️ Долго ({completion_time:.1f} мин при норме {estimated_duration}). Отметим это в прогрессе.",
                    parse_mode="HTML"
                )

        if step_type in [StepType.CONTENT, StepType.OFFLINE, StepType.CONFIRMATION]:
            if message.text != "Готово ✅":
                await message.answer("Нажми 'Готово ✅', когда завершишь шаг.")
                return
            submission.text_answer = "Completed"
            await message.answer("Отмечено как выполнено.", reply_markup=types.ReplyKeyboardRemove())

        elif step_type in [StepType.TEXT_INPUT, StepType.QUESTION, StepType.SELF_REPORT]:
            if not message.text:
                await message.answer("Нужен текстовый ответ.")
                return
            submission.text_answer = message.text
            await state.update_data(last_text_answer=message.text)
            await message.answer("Ответ сохранён.")

        elif step_type == StepType.EVALUATION:
            # оценка предыдущего ответа (last_text_answer)
            if message.text and message.text.lower() in ["/skip", "пропустить"]:
                submission.status = "pending"
                submission.text_answer = last_text_answer
                submission.evaluation_notes = "Оценка пропущена пользователем"
                await message.answer("Оценку пропустили. Двигаемся дальше.", reply_markup=types.ReplyKeyboardRemove())
            else:
                feedback = await evaluate_answer(last_text_answer, step.description or "")
                submission.text_answer = last_text_answer
                submission.evaluation_score = feedback["score"]
                submission.evaluation_notes = feedback["comment"]
                submission.auto_check_result = feedback["comment"]
                await message.answer(f"Оценка: {feedback['comment']}", reply_markup=types.ReplyKeyboardRemove())

        elif step_type == StepType.FILE_UPLOAD:
            if not message.document:
                await message.answer("Загрузи Excel-файл карты поиска.")
                return

            document = message.document
            file_name = document.file_name

            if not (file_name.endswith('.xlsx') or file_name.endswith('.xls')):
                await message.answer("Нужен Excel файл (.xlsx или .xls).")
                return

            file = await bot.get_file(document.file_id)
            os.makedirs("uploads", exist_ok=True)
            destination = f"uploads/{user.id}_{step_id}_{file_name}"
            await bot.download_file(file.file_path, destination)

            validator = SearchMapValidator(destination)
            if not validator.load():
                await message.answer(f"Ошибка загрузки файла: {validator.get_summary()}")
                return

            report = validator.validate_content()
            submission.file_path = destination

            llm_report = await validator.validate_with_llm()
            auto_check_summary = f"Basic check: {report}\nLLM check: {llm_report}"
            submission.auto_check_result = auto_check_summary

            feedback_parts = []
            if not report["valid"]:
                feedback_parts.append(f"⚠️ <b>Basic validation issues:</b>\n{report['errors']}")
                submission.status = "pending"

            if not llm_report.get("valid", True):
                issues = llm_report.get("issues", [])
                suggestions = llm_report.get("suggestions", [])

                feedback_parts.append(f"\n🤖 <b>LLM Validation found issues:</b>")
                for issue in issues[:3]:
                    feedback_parts.append(f"• {issue}")

                if suggestions:
                    feedback_parts.append(f"\n💡 <b>Suggestions:</b>")
                    for suggestion in suggestions[:2]:
                        feedback_parts.append(f"• {suggestion}")

                submission.status = "pending"

            if feedback_parts:
                await message.answer("\n".join(feedback_parts) + "\n\n✅ Отправлено на проверку эксперту.", parse_mode="HTML")
            else:
                await message.answer("✅ Файл принят! Автопроверка пройдена.", parse_mode="HTML")

        session.add(submission)
        await session.commit()

        next_step = await get_next_step(user.id, session)
        if next_step:
            await message.answer("Переходим к следующему шагу...")
            await show_step(message, next_step, state)
        else:
            # Онбординг завершён - генерируем Excel отчет
            await message.answer("🎉 Онбординг завершён! Отличная работа!\n\n⏳ Генерирую AI-отчет...\nЭто займет около минуты ⏱️")
            
            try:
                # Получаем все submissions пользователя
                from app.bot.reports.simple_report_generator import SimpleOnboardingReportGenerator
                from sqlalchemy.orm import selectinload
                
                submissions_result = await session.execute(
                    select(OnboardingSubmission)
                    .where(OnboardingSubmission.user_id == user.id)
                    .options(selectinload(OnboardingSubmission.step))
                    .options(selectinload(OnboardingSubmission.user))
                )
                all_submissions = submissions_result.scalars().all()
                
                if all_submissions:
                    # Генерируем Excel с LLM оценками (асинхронно)
                    generator = SimpleOnboardingReportGenerator(all_submissions)
                    excel_bytes = await generator.generate_async()
                    
                    # Отправляем файл
                    from aiogram.types import BufferedInputFile
                    file = BufferedInputFile(
                        excel_bytes,
                        filename=f"Отчет_онбординг_{user.full_name or 'стажер'}_{datetime.now().strftime('%Y%m%d')}.xlsx"
                    )
                    await bot.send_document(
                        message.chat.id,
                        file,
                        caption="✅ Вот твой AI-отчет по онбордингу! Все твои ответы оценены искусственным интеллектом 🤖"
                    )
                else:
                    await message.answer("⚠️ Не удалось найти данные для генерации отчета.")
            except Exception as e:
                import traceback
                error_details = traceback.format_exc()
                print(f"Completion report generation error: {error_details}")
                await message.answer(f"⚠️ Ошибка при генерации отчета: {str(e)}\nОбратись к наставнику.")
            
            await state.clear()
