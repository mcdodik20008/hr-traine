"""Tests for database models"""
import pytest
from datetime import datetime, timedelta
from app.database.models import (
    User, OnboardingStep, CandidateProfile, OnboardingSubmission,
    UserRole, StepType
)


class TestUser:
    """Test User model"""
    
    @pytest.mark.asyncio
    async def test_user_creation(self, test_session, sample_user):
        """Test creating a user"""
        assert sample_user.id is not None
        assert sample_user.telegram_id == 12345
        assert sample_user.username == "testuser"
        assert sample_user.full_name == "Test User"
        assert sample_user.role == UserRole.STUDENT
    
    @pytest.mark.asyncio
    async def test_user_unique_telegram_id(self, test_session):
        """Test that telegram_id must be unique"""
        user1 = User(telegram_id=99999, username="user1", full_name="User 1")
        test_session.add(user1)
        await test_session.commit()
        
        user2 = User(telegram_id=99999, username="user2", full_name="User 2")
        test_session.add(user2)
        
        with pytest.raises(Exception):  # Should raise IntegrityError
            await test_session.commit()


class TestOnboardingStep:
    """Test OnboardingStep model"""
    
    @pytest.mark.asyncio
    async def test_onboarding_step_creation(self, test_session, sample_onboarding_step):
        """Test creating a lab step"""
        assert sample_onboarding_step.id is not None
        assert sample_onboarding_step.title == "Test Step"
        assert sample_onboarding_step.order == 1
        assert sample_onboarding_step.step_type == StepType.CONTENT
        assert sample_onboarding_step.estimated_duration == 30


class TestCandidateProfile:
    """Test CandidateProfile model"""
    
    @pytest.mark.asyncio
    async def test_candidate_creation(self, test_session, sample_candidate):
        """Test creating a candidate profile"""
        assert sample_candidate.id is not None
        assert sample_candidate.name == "Test Candidate"
        assert sample_candidate.psychotype == "Target"


class TestOnboardingSubmission:
    """Test OnboardingSubmission model"""
    
    @pytest.mark.asyncio
    async def test_submission_creation(self, test_session, sample_user, sample_onboarding_step):
        """Test creating a submission"""
        submission = OnboardingSubmission(
            user_id=sample_user.id,
            step_id=sample_onboarding_step.id,
            text_answer="Test answer",
            status="pending"
        )
        test_session.add(submission)
        await test_session.commit()
        
        assert submission.id is not None
        assert submission.user_id == sample_user.id
        assert submission.step_id == sample_onboarding_step.id
    
    @pytest.mark.asyncio
    async def test_get_completion_time_minutes(self, test_session, sample_user, sample_onboarding_step):
        """Test calculating completion time"""
        started_at = datetime.now()
        created_at = started_at + timedelta(minutes=45)
        
        submission = OnboardingSubmission(
            user_id=sample_user.id,
            step_id=sample_onboarding_step.id,
            started_at=started_at,
            created_at=created_at,
            status="pending"
        )
        
        completion_time = submission.get_completion_time_minutes()
        assert completion_time == pytest.approx(45.0, abs=0.1)
    
    @pytest.mark.asyncio
    async def test_get_completion_time_no_dates(self, test_session, sample_user, sample_onboarding_step):
        """Test completion time calculation with missing dates"""
        submission = OnboardingSubmission(
            user_id=sample_user.id,
            step_id=sample_onboarding_step.id,
            status="pending"
        )
        
        completion_time = submission.get_completion_time_minutes()
        assert completion_time == 0
    
    @pytest.mark.asyncio
    async def test_submission_relationships(self, test_session, sample_user, sample_onboarding_step):
        """Test submission relationships"""
        submission = OnboardingSubmission(
            user_id=sample_user.id,
            step_id=sample_onboarding_step.id,
            text_answer="Test",
            status="pending"
        )
        test_session.add(submission)
        await test_session.commit()
        await test_session.refresh(submission)
        
        assert submission.user is not None
        assert submission.user.id == sample_user.id
        assert submission.step is not None
        assert submission.step.id == sample_onboarding_step.id

