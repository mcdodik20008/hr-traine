"""Add onboarding tables and chat history

Revision ID: 20251207_onboarding
Revises: 6cee592f9ee6
Create Date: 2025-12-07
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "20251207_onboarding"
down_revision = "6cee592f9ee6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "onboarding_steps",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column("title", sa.String(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("order", sa.Integer(), nullable=False, unique=True),
        sa.Column("step_type", sa.String(), nullable=True),
        sa.Column("estimated_duration", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("content_url", sa.String(), nullable=True),
    )

    op.create_table(
        "onboarding_submissions",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id")),
        sa.Column("step_id", sa.Integer(), sa.ForeignKey("onboarding_steps.id")),
        sa.Column("file_path", sa.String(), nullable=True),
        sa.Column("text_answer", sa.Text(), nullable=True),
        sa.Column("auto_check_result", sa.Text(), nullable=True),
        sa.Column("expert_score", sa.Integer(), nullable=True),
        sa.Column("expert_comment", sa.Text(), nullable=True),
        sa.Column("status", sa.String(), nullable=True, server_default="pending"),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("time_warning", sa.String(), nullable=True),
        sa.Column("evaluation_score", sa.Float(), nullable=True),
        sa.Column("evaluation_notes", sa.Text(), nullable=True),
    )

    op.add_column("interview_sessions", sa.Column("chat_history", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("interview_sessions", "chat_history")
    op.drop_table("onboarding_submissions")
    op.drop_table("onboarding_steps")

