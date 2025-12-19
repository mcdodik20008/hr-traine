import json
import logging
from aiogram import Router, types, F
from aiogram.fsm.context import FSMContext
from app.bot.states import InterviewStates
from app.core.llm_client import llm_client
from app.database.base import get_session
from app.database.models import CandidateProfile, InterviewSession, User
from sqlalchemy.future import select

logger = logging.getLogger(__name__)

# RAG Coach - lazy initialization
_rag_coach_instance = None

async def get_rag_coach():
    """Initialize RAG Coach on first use"""
    global _rag_coach_instance
    if _rag_coach_instance is None:
        try:
            from pathlib import Path
            from app.rag.vector_store import FAISSVectorStore
            from app.rag.embeddings import EmbeddingGenerator
            from app.rag.coach import HRCoach
            
            # Try to load existing index
            index_path = Path(__file__).parent.parent.parent / "app" / "data" / "rag_index"
            
            if (index_path / "index.faiss").exists():
                logger.info("📦 Loading RAG Coach...")
                embedding_gen = EmbeddingGenerator()
                vector_store = FAISSVectorStore(dimension=embedding_gen.dimension)
                vector_store.load(index_path)
                _rag_coach_instance = HRCoach(vector_store, embedding_gen)
                logger.info(f"✅ RAG Coach loaded with {vector_store.size} documents")
            else:
                logger.warning("⚠️ RAG index not found. Run: python -m app.scripts.initialize_rag")
        except Exception as e:
            logger.error(f"Failed to load RAG Coach: {e}")
            _rag_coach_instance = None
    
    return _rag_coach_instance

router = Router()

@router.message(F.text == "/interview")
async def cmd_interview(message: types.Message, state: FSMContext):
    # List candidates
    async for session in get_session():
        result = await session.execute(select(CandidateProfile))
        candidates = result.scalars().all()
        
        if not candidates:
            # Create a dummy candidate if none exist
            dummy = CandidateProfile(
                name="John Doe", 
                resume_text="Experienced Sales Manager with 5 years in B2B.",
                category="Sales",
                psychotype="Target"
            )
            session.add(dummy)
            await session.commit()
            candidates = [dummy]
        
        buttons = [[types.KeyboardButton(text=c.name)] for c in candidates]
        keyboard = types.ReplyKeyboardMarkup(keyboard=buttons, one_time_keyboard=True)
        
        await message.answer("Choose a candidate to interview:", reply_markup=keyboard)
        await state.set_state(InterviewStates.choosing_candidate)

@router.message(InterviewStates.choosing_candidate)
async def start_interview(message: types.Message, state: FSMContext):
    candidate_name = message.text
    
    async for session in get_session():
        result = await session.execute(select(CandidateProfile).where(CandidateProfile.name == candidate_name))
        candidate = result.scalar_one_or_none()
        
        if not candidate:
            await message.answer("Candidate not found.")
            return
            
        user_result = await session.execute(select(User).where(User.telegram_id == message.from_user.id))
        user = user_result.scalar_one_or_none()

        # Create session
        interview = InterviewSession(user_id=user.id, candidate_id=candidate.id)
        session.add(interview)
        await session.commit()
        
        await state.update_data(
            interview_id=interview.id, 
            candidate_resume=candidate.resume_text,
            candidate_psychotype=candidate.psychotype or "Target",
            history=[]
        )
        
        psychotype_emoji = {
            "Target": "🎯",
            "Toxic": "☠️",
            "Silent": "🤐",
            "Evasive": "🌫️"
        }
        emoji = psychotype_emoji.get(candidate.psychotype, "👤")
        
        await message.answer(
            f"✅ <b>Интервью с {candidate.name}</b> {emoji}\n"
            f"<b>Психотип:</b> {candidate.psychotype or 'Target'}\n\n"
            f"💬 Поздоровайтесь с кандидатом, чтобы начать интервью.\n"
            f"Бот будет отвечать на ваши вопросы от лица кандидата.\n\n"
            f"🛑 Когда закончите, попрощайтесь с кандидатом.",
            parse_mode="HTML",
            reply_markup=types.ReplyKeyboardRemove()
        )
        await state.set_state(InterviewStates.in_interview)


@router.message(InterviewStates.in_interview)
async def process_chat(message: types.Message, state: FSMContext):
    data = await state.get_data()
    resume = data.get("candidate_resume")
    psychotype = data.get("candidate_psychotype", "Target")
    history = data.get("history", [])
    interview_id = data.get("interview_id")
    
    # User message
    user_message = message.text
    history.append({"role": "user", "parts": [user_message]})
    
    # Check if this is a farewell
    farewell_result = await llm_client.detect_interview_farewell(
        user_message=user_message,
        conversation_history=history,
        resume_text=resume,
        psychotype=psychotype
    )
    
    if farewell_result.get("is_farewell", False):
        # This is a farewell - send farewell message and generate report
        farewell_message = farewell_result.get("farewell_message", "Спасибо за интервью!")
        
        # Add farewell to history
        history.append({"role": "model", "parts": [farewell_message]})
        await state.update_data(history=history)
        
        # Persist farewell in DB
        if interview_id:
            await _persist_chat(interview_id, user_message, farewell_message)
        
        # Send farewell message
        await message.answer(farewell_message)
        
        # Generate interview report
        await message.answer("⏳ Генерирую отчет о проведенном интервью...")
        
        report = await llm_client.generate_interview_report(
            conversation_history=history,
            candidate_resume=resume,
            psychotype=psychotype
        )
        
        # Format and send report
        report_text = _format_interview_report(report)
        await message.answer(report_text, parse_mode="HTML")
        
        # Save report to database
        if interview_id:
            from datetime import datetime
            async for session in get_session():
                result = await session.execute(select(InterviewSession).where(InterviewSession.id == interview_id))
                interview_row = result.scalar_one_or_none()
                if interview_row:
                    interview_row.end_time = datetime.now()
                    interview_row.auto_feedback = json.dumps(report, ensure_ascii=False)
                    interview_row.is_passed = report.get("overall_score", 0) >= 6.0
                    await session.commit()
        
        # Clear state
        await state.clear()
        return
    
    # Not a farewell - analyze question with RAG Coach first
    coach = await get_rag_coach()
    
    if coach:
        try:
            # Analyze interviewer's question
            feedback = await coach.analyze_question(user_message, context=history)
            
            if feedback.get("has_feedback"):
                # Send coaching feedback BEFORE candidate response
                await message.answer(
                    feedback["message"],
                    parse_mode="HTML"
                )
        except Exception as e:
            logger.error(f"RAG Coach error: {e}", exc_info=True)
    
    # Generate normal candidate response
    response_text = await llm_client.simulate_candidate(resume, user_message, history, psychotype)
    
    history.append({"role": "model", "parts": [response_text]})
    await state.update_data(history=history)
    
    if interview_id:
        await _persist_chat(interview_id, user_message, response_text)
    
    await message.answer(response_text)


def _format_interview_report(report: dict) -> str:
    """Форматирует отчет интервью в красивый HTML для Telegram"""
    overall_score = report.get("overall_score", 0)
    category_scores = report.get("category_scores", {})
    strengths = report.get("strengths", [])
    weaknesses = report.get("weaknesses", [])
    recommendations = report.get("recommendations", [])
    detailed_feedback = report.get("detailed_feedback", "")
    
    # Определяем эмодзи по оценке
    if overall_score >= 8:
        score_emoji = "🌟"
    elif overall_score >= 6:
        score_emoji = "✅"
    elif overall_score >= 4:
        score_emoji = "⚠️"
    else:
        score_emoji = "❌"
    
    text = f"""
📊 <b>ОТЧЕТ О ПРОВЕДЕННОМ ИНТЕРВЬЮ</b>

{score_emoji} <b>Общая оценка: {overall_score}/10</b>

<b>📈 Оценки по категориям:</b>
"""
    
    category_names = {
        "structure": "Структура интервью",
        "questions_quality": "Качество вопросов",
        "active_listening": "Активное слушание",
        "psychotype_handling": "Работа с психотипом",
        "professionalism": "Профессионализм"
    }
    
    for key, value in category_scores.items():
        name = category_names.get(key, key)
        text += f"  • {name}: {value}/10\n"
    
    if strengths:
        text += f"\n<b>💪 Сильные стороны:</b>\n"
        for strength in strengths:
            text += f"  ✓ {strength}\n"
    
    if weaknesses:
        text += f"\n<b>⚡️ Области для улучшения:</b>\n"
        for weakness in weaknesses:
            text += f"  • {weakness}\n"
    
    if recommendations:
        text += f"\n<b>💡 Рекомендации:</b>\n"
        for i, rec in enumerate(recommendations, 1):
            text += f"  {i}. {rec}\n"
    
    if detailed_feedback:
        text += f"\n<b>📝 Детальный feedback:</b>\n{detailed_feedback}"
    
    return text.strip()


async def _persist_chat(interview_id: int, user_message: str, bot_reply: str):
    """
    Сохраняем историю чата интервью (текст и JSON) в БД.
    """
    async for session in get_session():
        result = await session.execute(select(InterviewSession).where(InterviewSession.id == interview_id))
        interview_row = result.scalar_one_or_none()
        if not interview_row:
            return

        # transcript как плоский текст
        transcript_parts = interview_row.transcript.split("\n") if interview_row.transcript else []
        transcript_parts.append(f"User: {user_message}")
        transcript_parts.append(f"Bot: {bot_reply}")
        interview_row.transcript = "\n".join(transcript_parts)

        # chat_history как JSON список сообщений
        history = []
        if interview_row.chat_history:
            try:
                history = json.loads(interview_row.chat_history)
            except Exception:
                history = []
        history.append({"role": "user", "content": user_message})
        history.append({"role": "assistant", "content": bot_reply})
        interview_row.chat_history = json.dumps(history, ensure_ascii=False)

        await session.commit()
