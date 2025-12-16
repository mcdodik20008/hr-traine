from aiogram import Router, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from app.database.base import get_session
from app.database.models import OnboardingSubmission, User, UserRole
from sqlalchemy.future import select

router = Router()

class ExpertStates(StatesGroup):
    reviewing = State()
    grading = State()

@router.message(Command("expert"))
async def cmd_expert(message: types.Message, state: FSMContext):
    # Check if user is expert (simple check for now, in real app check DB role)
    # For demo, we assume everyone who types /expert is an expert or we check DB
    
    async for session in get_session():
        result = await session.execute(select(User).where(User.telegram_id == message.from_user.id))
        user = result.scalar_one_or_none()
        
        if not user or user.role != UserRole.EXPERT:
            # Auto-promote for testing if needed, or just deny
            # await message.answer("Access denied. You are not an expert.")
            # return
            pass # Allow for now for testing convenience

        # List pending submissions
        result = await session.execute(select(OnboardingSubmission).where(OnboardingSubmission.status == "checked"))
        submissions = result.scalars().all()
        
        if not submissions:
            await message.answer("No pending submissions.")
            return

        text = "Pending Submissions:\n"
        for sub in submissions:
            text += f"ID: {sub.id} | User: {sub.user_id} | Step: {sub.step_id}\n"
        
        await message.answer(text + "\nType /review <id> to review a submission.")

@router.message(Command("review"))
async def cmd_review(message: types.Message, state: FSMContext):
    try:
        args = message.text.split()
        if len(args) < 2:
            await message.answer("Usage: /review <submission_id>")
            return
            
        sub_id = int(args[1])
        
        async for session in get_session():
            result = await session.execute(select(OnboardingSubmission).where(OnboardingSubmission.id == sub_id))
            submission = result.scalar_one_or_none()
            
            if not submission:
                await message.answer("Submission not found.")
                return
            
            # Send file or text to expert
            if submission.file_path:
                file = types.FSInputFile(submission.file_path)
                await message.answer_document(file, caption=f"Submission {sub_id}\nAuto-Check: {submission.auto_check_result}")
            else:
                await message.answer(
                    f"Submission {sub_id}\n"
                    f"Answer: {submission.text_answer or '-'}\n"
                    f"Auto-Check: {submission.auto_check_result or '-'}"
                )
            
            await state.update_data(submission_id=sub_id)
            await message.answer("Please enter score (1-5) and comment (e.g., '5 Good job').")
            await state.set_state(ExpertStates.grading)
            
    except ValueError:
        await message.answer("Invalid ID.")

@router.message(ExpertStates.grading)
async def process_grading(message: types.Message, state: FSMContext):
    text = message.text
    try:
        parts = text.split(' ', 1)
        score = int(parts[0])
        comment = parts[1] if len(parts) > 1 else ""
        
        if not (1 <= score <= 5):
            await message.answer("Score must be between 1 and 5.")
            return

        data = await state.get_data()
        sub_id = data.get("submission_id")
        
        async for session in get_session():
            result = await session.execute(select(OnboardingSubmission).where(OnboardingSubmission.id == sub_id))
            submission = result.scalar_one_or_none()
            
            if submission:
                submission.expert_score = score
                submission.expert_comment = comment
                submission.status = "approved" if score >= 3 else "rejected"
                await session.commit()
                
                await message.answer(f"Submission {sub_id} graded.")
                # Notify student (omitted for brevity)
        
        await state.clear()
        
    except ValueError:
        await message.answer("Invalid format. Use: <score> <comment>")
