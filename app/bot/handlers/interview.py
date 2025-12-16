import json
from aiogram import Router, types, F
from aiogram.fsm.context import FSMContext
from app.bot.states import InterviewStates
from app.core.llm_client import llm_client
from app.database.base import get_session
from app.database.models import CandidateProfile, InterviewSession, User
from sqlalchemy.future import select

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
            f"Interview started with {candidate.name} {emoji}\n"
            f"<b>Psychotype:</b> {candidate.psychotype or 'Target'}\n\n"
            f"<b>Resume:</b> {candidate.resume_text}\n\n"
            f"Say 'Hello' to start. Type /stop to finish.",
            parse_mode="HTML",
            reply_markup=types.ReplyKeyboardRemove()
        )
        await state.set_state(InterviewStates.in_interview)

@router.message(InterviewStates.in_interview)
async def process_chat(message: types.Message, state: FSMContext):
    if message.text.lower() in ["/stop", "stop", "finish"]:
        data = await state.get_data()
        interview_id = data.get("interview_id")
        if interview_id:
            from datetime import datetime
            async for session in get_session():
                result = await session.execute(select(InterviewSession).where(InterviewSession.id == interview_id))
                interview_row = result.scalar_one_or_none()
                if interview_row:
                    interview_row.end_time = interview_row.end_time or datetime.now()
                    await session.commit()
        await message.answer("Interview finished.")
        await state.clear()
        return

    data = await state.get_data()
    resume = data.get("candidate_resume")
    psychotype = data.get("candidate_psychotype", "Target")
    history = data.get("history", [])
    interview_id = data.get("interview_id")
    
    # User message
    history.append({"role": "user", "parts": [message.text]})
    
    # Generate response with psychotype
    response_text = await llm_client.simulate_candidate(resume, message.text, history, psychotype)
    
    history.append({"role": "model", "parts": [response_text]})
    await state.update_data(history=history)
    
    if interview_id:
        await _persist_chat(interview_id, message.text, response_text)
    
    await message.answer(response_text)

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
