"""Tests for bot handlers"""
import pytest
from unittest.mock import AsyncMock, Mock, patch
from datetime import datetime
from app.bot.handlers import registration, onboarding, interview, expert, common
from app.database.models import User, UserRole, OnboardingStep, StepType, CandidateProfile, OnboardingSubmission
from app.bot.states import RegistrationStates, OnboardingStates, InterviewStates


class TestRegistrationHandlers:
    """Test registration handlers"""
    
    @pytest.mark.asyncio
    async def test_cmd_start(self, mock_message, mock_state):
        """Test /start command"""
        await common.cmd_start(mock_message, mock_state)
        
        mock_message.answer.assert_called_once()
        mock_state.set_state.assert_called_once_with(RegistrationStates.waiting_for_name)
    
    @pytest.mark.asyncio
    async def test_cmd_help(self, mock_message):
        """Test /help command"""
        await common.cmd_help(mock_message)
        
        mock_message.answer.assert_called_once()
        call_args = mock_message.answer.call_args[0][0]
        assert "/start" in call_args
        assert "/onboarding" in call_args
    
    @pytest.mark.asyncio
    async def test_process_name_new_user(self, mock_message, mock_state, test_session, mocker):
        """Test processing name for new user"""
        mock_message.text = "John Doe"
        mock_message.from_user.id = 99999
        mock_message.from_user.username = "johndoe"
        
        # Mock get_session
        async def mock_get_session():
            yield test_session
        
        mocker.patch('app.bot.handlers.registration.get_session', mock_get_session)
        
        await registration.process_name(mock_message, mock_state)
        
        mock_message.answer.assert_called_once()
        assert "John Doe" in mock_message.answer.call_args[0][0]
        mock_state.clear.assert_called_once()
        
        # Verify user was created
        from sqlalchemy.future import select
        result = await test_session.execute(select(User).where(User.telegram_id == 99999))
        user = result.scalar_one_or_none()
        assert user is not None
        assert user.full_name == "John Doe"
    
    @pytest.mark.asyncio
    async def test_process_name_existing_user(self, mock_message, mock_state, test_session, sample_user, mocker):
        """Test processing name for existing user"""
        mock_message.text = "Updated Name"
        mock_message.from_user.id = sample_user.telegram_id
        
        async def mock_get_session():
            yield test_session
        
        mocker.patch('app.bot.handlers.registration.get_session', mock_get_session)
        
        await registration.process_name(mock_message, mock_state)
        
        # Verify user was updated
        await test_session.refresh(sample_user)
        assert sample_user.full_name == "Updated Name"


class TestOnboardingHandlers:
    """Test onboarding handlers"""
    
    @pytest.mark.asyncio
    async def test_cmd_onboarding_user_not_found(self, mock_message, mock_state, test_session, mocker):
        """Test /onboarding when user is not registered"""
        mock_message.from_user.id = 99999
        
        async def mock_get_session():
            yield test_session
        
        mocker.patch('app.bot.handlers.labs.get_session', mock_get_session)
        
        await onboarding.cmd_onboarding(mock_message, mock_state)
        
        mock_message.answer.assert_called_once()
        assert "зарегистр" in mock_message.answer.call_args[0][0].lower()
    
    @pytest.mark.asyncio
    async def test_cmd_onboarding_all_steps_completed(self, mock_message, mock_state, test_session, sample_user, sample_onboarding_step, mocker):
        """Test /onboarding when all steps are completed"""
        
        # Create completed submission
        submission = OnboardingSubmission(
            user_id=sample_user.id,
            step_id=sample_onboarding_step.id,
            status="approved"
        )
        test_session.add(submission)
        await test_session.commit()
        
        async def mock_get_session():
            yield test_session
        
        mocker.patch('app.bot.handlers.labs.get_session', mock_get_session)
        
        await onboarding.cmd_onboarding(mock_message, mock_state)
        
        mock_message.answer.assert_called_once()
        text = mock_message.answer.call_args[0][0].lower()
        assert "заверш" in text or "готово" in text or "great job" in text
    
    @pytest.mark.asyncio
    async def test_cmd_onboarding_show_next_step(self, mock_message, mock_state, test_session, sample_user, sample_onboarding_step, mocker):
        """Test /onboarding showing next step"""
        async def mock_get_session():
            yield test_session
        
        mocker.patch('app.bot.handlers.labs.get_session', mock_get_session)
        
        await onboarding.cmd_onboarding(mock_message, mock_state)
        
        # Should show step information
        assert mock_message.answer.called
        call_args = mock_message.answer.call_args[0][0]
        assert sample_onboarding_step.title in call_args or "Шаг" in call_args or "Step" in call_args


class TestInterviewHandlers:
    """Test interview handlers"""
    
    @pytest.mark.asyncio
    async def test_cmd_interview_no_candidates(self, mock_message, mock_state, test_session, mocker):
        """Test /interview when no candidates exist"""
        async def mock_get_session():
            yield test_session
        
        mocker.patch('app.bot.handlers.interview.get_session', mock_get_session)
        
        await interview.cmd_interview(mock_message, mock_state)
        
        # Should create dummy candidate or show message
        mock_message.answer.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_cmd_interview_with_candidates(self, mock_message, mock_state, test_session, sample_candidate, mocker):
        """Test /interview with existing candidates"""
        async def mock_get_session():
            yield test_session
        
        mocker.patch('app.bot.handlers.interview.get_session', mock_get_session)
        
        await interview.cmd_interview(mock_message, mock_state)
        
        mock_message.answer.assert_called_once()
        mock_state.set_state.assert_called_once_with(InterviewStates.choosing_candidate)
    
    @pytest.mark.asyncio
    async def test_start_interview(self, mock_message, mock_state, test_session, sample_user, sample_candidate, mocker):
        """Test starting interview"""
        mock_message.text = sample_candidate.name
        
        async def mock_get_session():
            yield test_session
        
        mocker.patch('app.bot.handlers.interview.get_session', mock_get_session)
        
        await interview.start_interview(mock_message, mock_state)
        
        mock_message.answer.assert_called_once()
        call_args = mock_message.answer.call_args[0][0]
        assert sample_candidate.name in call_args
        mock_state.set_state.assert_called_once_with(InterviewStates.in_interview)
    
    @pytest.mark.asyncio
    async def test_process_chat_farewell(self, mock_message, mock_state, mocker):
        """Test interview ending with farewell detection"""
        mock_message.text = "Спасибо за интервью, до свидания!"
        
        # Mock state data
        mock_state.get_data = AsyncMock(return_value={
            "candidate_resume": "5 years in sales",
            "candidate_psychotype": "Target",
            "history": [],
            "interview_id": None
        })
        
        # Mock LLM client
        mock_llm = mocker.patch('app.bot.handlers.interview.llm_client')
        mock_llm.detect_interview_farewell = AsyncMock(return_value={
            "is_farewell": True,
            "farewell_message": "Спасибо за интервью!"
        })
        mock_llm.generate_interview_report = AsyncMock(return_value={
            "overall_score": 7.5,
            "category_scores": {"structure": 8},
            "strengths": ["Good questions"],
            "weaknesses": ["Could improve timing"],
            "recommendations": ["Practice more"],
            "detailed_feedback": "Good interview overall."
        })
        
        await interview.process_chat(mock_message, mock_state)
        
        # Should send farewell and report
        assert mock_message.answer.call_count >= 2  # Farewell + Loading + Report
        mock_state.clear.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_process_chat_with_llm(self, mock_message, mock_state, mocker):
        """Test processing chat message with LLM"""
        mock_message.text = "Tell me about yourself"
        
        # Mock state data
        mock_state.get_data = AsyncMock(return_value={
            "candidate_resume": "5 years in sales",
            "candidate_psychotype": "Target",
            "history": [],
            "interview_id": None
        })
        
        # Mock LLM client
        mock_llm = mocker.patch('app.bot.handlers.interview.llm_client')
        mock_llm.detect_interview_farewell = AsyncMock(return_value={
            "is_farewell": False,
            "farewell_message": ""
        })
        mock_llm.simulate_candidate = AsyncMock(return_value="I have 5 years of experience...")
        
        await interview.process_chat(mock_message, mock_state)
        
        mock_message.answer.assert_called_once()
        assert "experience" in mock_message.answer.call_args[0][0].lower() or len(mock_message.answer.call_args[0][0]) > 0


class TestExpertHandlers:
    """Test expert handlers"""
    
    @pytest.mark.asyncio
    async def test_cmd_expert_no_pending(self, mock_message, mock_state, test_session, mocker):
        """Test /expert when no pending submissions"""
        async def mock_get_session():
            yield test_session
        
        mocker.patch('app.bot.handlers.expert.get_session', mock_get_session)
        
        await expert.cmd_expert(mock_message, mock_state)
        
        mock_message.answer.assert_called_once()
        assert "no pending" in mock_message.answer.call_args[0][0].lower() or "pending" in mock_message.answer.call_args[0][0].lower()
    
    @pytest.mark.asyncio
    async def test_cmd_review_invalid_id(self, mock_message, mock_state):
        """Test /review with invalid ID"""
        mock_message.text = "/review abc"
        
        await expert.cmd_review(mock_message, mock_state)
        
        mock_message.answer.assert_called_once()
        assert "usage" in mock_message.answer.call_args[0][0].lower() or "invalid" in mock_message.answer.call_args[0][0].lower()
    
    @pytest.mark.asyncio
    async def test_cmd_review_not_found(self, mock_message, mock_state, test_session, mocker):
        """Test /review with non-existent submission ID"""
        mock_message.text = "/review 99999"
        
        async def mock_get_session():
            yield test_session
        
        mocker.patch('app.bot.handlers.expert.get_session', mock_get_session)
        
        await expert.cmd_review(mock_message, mock_state)
        
        mock_message.answer.assert_called_once()
        assert "not found" in mock_message.answer.call_args[0][0].lower()
    
    @pytest.mark.asyncio
    async def test_process_grading_invalid_score(self, mock_message, mock_state):
        """Test grading with invalid score"""
        mock_message.text = "10 Invalid score"
        mock_state.get_data = AsyncMock(return_value={"submission_id": 1})
        
        await expert.process_grading(mock_message, mock_state)
        
        mock_message.answer.assert_called_once()
        assert "between 1 and 5" in mock_message.answer.call_args[0][0].lower() or "1-5" in mock_message.answer.call_args[0][0].lower()
    
    @pytest.mark.asyncio
    async def test_process_grading_valid(self, mock_message, mock_state, test_session, sample_user, sample_onboarding_step, mocker):
        """Test grading with valid score"""
        from app.database.models import OnboardingSubmission
        
        submission = OnboardingSubmission(
            user_id=sample_user.id,
            step_id=sample_onboarding_step.id,
            status="checked"
        )
        test_session.add(submission)
        await test_session.commit()
        await test_session.refresh(submission)
        
        mock_message.text = "5 Excellent work"
        mock_state.get_data = AsyncMock(return_value={"submission_id": submission.id})
        
        async def mock_get_session():
            yield test_session
        
        mocker.patch('app.bot.handlers.expert.get_session', mock_get_session)
        
        await expert.process_grading(mock_message, mock_state)
        
        # Verify submission was updated
        await test_session.refresh(submission)
        assert submission.expert_score == 5
        assert submission.expert_comment == "Excellent work"
        assert submission.status == "approved"  # Score >= 3
        
        mock_state.clear.assert_called_once()

