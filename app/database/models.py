from sqlalchemy import Column, Integer, String, Text, ForeignKey, DateTime, Boolean, Float, Enum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from pgvector.sqlalchemy import Vector
import enum
from app.database.base import Base

class UserRole(str, enum.Enum):
    STUDENT = "student"
    EXPERT = "expert"
    ADMIN = "admin"

class StepType(str, enum.Enum):
    CONTENT = "content"         # Изучение материала
    FILE_UPLOAD = "file_upload" # Загрузка файла (например, карта поиска)
    TEXT_INPUT = "text_input"   # Ввод текста / ответ на вопрос
    OFFLINE = "offline"         # Оффлайн активность
    QUESTION = "question"       # Контрольный вопрос перед материалом
    SELF_REPORT = "self_report" # Рассказ, что понял
    EVALUATION = "evaluation"   # Оценка результата (LLM/эксперт)
    CONFIRMATION = "confirmation" # Подтверждение выполнения (установка ПО, изучение документа)

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    telegram_id = Column(Integer, unique=True, index=True, nullable=False)
    username = Column(String, nullable=True)
    full_name = Column(String, nullable=True)
    role = Column(String, default=UserRole.STUDENT)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    onboarding_submissions = relationship("OnboardingSubmission", back_populates="user")
    interviews = relationship("InterviewSession", back_populates="user")

class OnboardingStep(Base):
    __tablename__ = "onboarding_steps"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    order = Column(Integer, unique=True, nullable=False)
    step_type = Column(String, default=StepType.CONTENT)
    estimated_duration = Column(Integer, default=0)  # in minutes
    content_url = Column(String, nullable=True)      # Link to material
    
    # Новые поля для структурированного ввода и LLM оценки
    collection_flow = Column(Text, nullable=True)  # JSON конфигурация диалога
    excel_sheet = Column(String, nullable=True)  # Название листа Excel для заполнения
    evaluation_prompt = Column(Text, nullable=True)  # LLM prompt для оценки
    evaluation_criteria = Column(Text, nullable=True)  # JSON с критериями оценки
    passing_score = Column(Float, default=3.0)  # Минимальный балл для прохождения
    
    submissions = relationship("OnboardingSubmission", back_populates="step")

class OnboardingSubmission(Base):
    __tablename__ = "onboarding_submissions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    step_id = Column(Integer, ForeignKey("onboarding_steps.id"))
    file_path = Column(String, nullable=True)  # Nullable для текстовых шагов
    text_answer = Column(Text, nullable=True)  # Ответ пользователя
    
    auto_check_result = Column(Text, nullable=True)  # JSON или текст (LLM/автопроверка)
    expert_score = Column(Integer, nullable=True)    # 1-5
    expert_comment = Column(Text, nullable=True)
    status = Column(String, default="pending")       # pending, checked, approved, rejected
    
    started_at = Column(DateTime(timezone=True), nullable=True)  # Когда начал
    created_at = Column(DateTime(timezone=True), server_default=func.now())  # Когда завершил/отправил
    time_warning = Column(String, nullable=True)  # "too_fast", "too_slow", or None
    evaluation_score = Column(Float, nullable=True)  # оценка шага (LLM/эксперт)
    evaluation_notes = Column(Text, nullable=True)   # пояснения к оценке

    user = relationship("User", back_populates="onboarding_submissions")
    step = relationship("OnboardingStep", back_populates="submissions")
    
    def get_completion_time_minutes(self) -> float:
        """Calculate completion time in minutes"""
        if not self.started_at or not self.created_at:
            return 0
        delta = self.created_at - self.started_at
        return delta.total_seconds() / 60

class CandidateProfile(Base):
    __tablename__ = "candidate_profiles"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    resume_text = Column(Text, nullable=False)
    category = Column(String, nullable=True) # e.g. "Sales", "IT"
    psychotype = Column(String, nullable=True) # "Target", "Toxic", "Silent"
    embedding = Column(Vector(768)) # For semantic search if needed

    interviews = relationship("InterviewSession", back_populates="candidate")

class InterviewSession(Base):
    __tablename__ = "interview_sessions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    candidate_id = Column(Integer, ForeignKey("candidate_profiles.id"))
    
    start_time = Column(DateTime(timezone=True), server_default=func.now())
    end_time = Column(DateTime(timezone=True), nullable=True)
    transcript = Column(Text, nullable=True) # Full dialogue
    chat_history = Column(Text, nullable=True) # JSON с сообщениями
    auto_feedback = Column(Text, nullable=True)
    expert_score = Column(Integer, nullable=True)
    expert_comment = Column(Text, nullable=True)
    is_passed = Column(Boolean, default=False)

    user = relationship("User", back_populates="interviews")
    candidate = relationship("CandidateProfile", back_populates="interviews")
