import pytest
import os
from unittest.mock import Mock, AsyncMock, MagicMock
from datetime import datetime
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.pool import StaticPool
from app.database.base import Base, get_session
from app.database.models import User, OnboardingStep, CandidateProfile, OnboardingSubmission, UserRole, StepType

# Use in-memory SQLite for tests (Note: pgvector not supported, but models should still work)
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

@pytest.fixture(scope="function")
async def test_engine():
    """Create test database engine"""
    engine = create_async_engine(
        TEST_DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        echo=False
    )
    
    async with engine.begin() as conn:
        # Create tables, but skip Vector type (not supported in SQLite)
        # Create a custom metadata without Vector columns
        from sqlalchemy import MetaData, Table, Column, Integer, String, Text, ForeignKey, DateTime, Boolean, Float
        
        # Create new metadata for test database
        test_metadata = MetaData()
        
        # Recreate all tables without Vector columns
        Table('users', test_metadata,
            Column('id', Integer, primary_key=True),
            Column('telegram_id', Integer, unique=True, nullable=False),
            Column('username', String, nullable=True),
            Column('full_name', String, nullable=True),
            Column('role', String, default='student'),
            Column('created_at', DateTime(timezone=True)),
        )
        
        Table('onboarding_steps', test_metadata,
            Column('id', Integer, primary_key=True),
            Column('title', String, nullable=False),
            Column('description', Text, nullable=True),
            Column('order', Integer, unique=True, nullable=False),
            Column('step_type', String, default='content'),
            Column('estimated_duration', Integer, default=0),
            Column('content_url', String, nullable=True),
        )
        
        # Create candidate_profiles with a dummy embedding column (as TEXT for SQLite)
        Table('candidate_profiles', test_metadata,
            Column('id', Integer, primary_key=True),
            Column('name', String, nullable=False),
            Column('resume_text', Text, nullable=False),
            Column('category', String, nullable=True),
            Column('psychotype', String, nullable=True),
            Column('embedding', Text, nullable=True),  # Use Text instead of Vector for SQLite
        )
        
        Table('interview_sessions', test_metadata,
            Column('id', Integer, primary_key=True),
            Column('user_id', Integer, ForeignKey('users.id')),
            Column('candidate_id', Integer, ForeignKey('candidate_profiles.id')),
            Column('start_time', DateTime(timezone=True)),
            Column('end_time', DateTime(timezone=True), nullable=True),
            Column('transcript', Text, nullable=True),
            Column('chat_history', Text, nullable=True),
            Column('auto_feedback', Text, nullable=True),
            Column('expert_score', Integer, nullable=True),
            Column('expert_comment', Text, nullable=True),
            Column('is_passed', Boolean, default=False),
        )
        
        Table('onboarding_submissions', test_metadata,
            Column('id', Integer, primary_key=True),
            Column('user_id', Integer, ForeignKey('users.id')),
            Column('step_id', Integer, ForeignKey('onboarding_steps.id')),
            Column('file_path', String, nullable=True),
            Column('text_answer', Text, nullable=True),
            Column('auto_check_result', Text, nullable=True),
            Column('expert_score', Integer, nullable=True),
            Column('expert_comment', Text, nullable=True),
            Column('status', String, default='pending'),
            Column('started_at', DateTime(timezone=True), nullable=True),
            Column('created_at', DateTime(timezone=True)),
            Column('time_warning', String, nullable=True),
            Column('evaluation_score', Float, nullable=True),
            Column('evaluation_notes', Text, nullable=True),
        )
        
        # Create all tables
        await conn.run_sync(test_metadata.create_all)
    
    yield engine
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    
    await engine.dispose()

@pytest.fixture
async def test_session(test_engine):
    """Create test database session"""
    async_session = async_sessionmaker(
        test_engine, class_=AsyncSession, expire_on_commit=False
    )
    
    async with async_session() as session:
        yield session

@pytest.fixture
def mock_message():
    """Mock Telegram message"""
    message = Mock()
    message.from_user = Mock()
    message.from_user.id = 12345
    message.from_user.username = "testuser"
    message.text = "/start"
    message.answer = AsyncMock()
    message.answer_document = AsyncMock()
    message.document = None
    return message

@pytest.fixture
def mock_state():
    """Mock FSM state"""
    state = AsyncMock()
    state.get_data = AsyncMock(return_value={})
    state.update_data = AsyncMock()
    state.set_state = AsyncMock()
    state.clear = AsyncMock()
    return state

@pytest.fixture
def mock_bot():
    """Mock Telegram bot"""
    bot = AsyncMock()
    bot.get_file = AsyncMock()
    bot.download_file = AsyncMock()
    return bot

@pytest.fixture
async def sample_user(test_session):
    """Create sample user in test database"""
    user = User(
        telegram_id=12345,
        username="testuser",
        full_name="Test User",
        role=UserRole.STUDENT
    )
    test_session.add(user)
    await test_session.commit()
    await test_session.refresh(user)
    return user

@pytest.fixture
async def sample_onboarding_step(test_session):
    """Create sample onboarding step in test database"""
    step = OnboardingStep(
        title="Test Step",
        description="Test Description",
        order=1,
        step_type=StepType.CONTENT,
        estimated_duration=30
    )
    test_session.add(step)
    await test_session.commit()
    await test_session.refresh(step)
    return step

@pytest.fixture
async def sample_candidate(test_session):
    """Create sample candidate in test database"""
    candidate = CandidateProfile(
        name="Test Candidate",
        resume_text="Test resume text",
        category="Test",
        psychotype="Target"
    )
    test_session.add(candidate)
    await test_session.commit()
    await test_session.refresh(candidate)
    return candidate

# Mock environment variables for tests
@pytest.fixture(autouse=True)
def mock_env(monkeypatch):
    """Mock environment variables"""
    monkeypatch.setenv("BOT_TOKEN", "test_token")
    monkeypatch.setenv("GEMINI_API_KEY", "test_gemini_key")
    monkeypatch.setenv("POSTGRES_USER", "postgres")
    monkeypatch.setenv("POSTGRES_PASSWORD", "postgres")
    monkeypatch.setenv("POSTGRES_DB", "test_db")
    monkeypatch.setenv("POSTGRES_HOST", "localhost")
    monkeypatch.setenv("POSTGRES_PORT", "5432")

