"""add collection_flow and evaluation fields

Revision ID: 20251215_collection_flow
Revises: 20251207_onboarding
Create Date: 2025-12-15 22:20:00

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '20251215_collection_flow'
down_revision = '20251207_onboarding'
branch_labels = None
depends_on = None


def upgrade():
    # Add new fields to onboarding_steps table
    op.add_column('onboarding_steps', sa.Column('collection_flow', sa.Text(), nullable=True))
    op.add_column('onboarding_steps', sa.Column('excel_sheet', sa.String(), nullable=True))
    op.add_column('onboarding_steps', sa.Column('evaluation_prompt', sa.Text(), nullable=True))
    op.add_column('onboarding_steps', sa.Column('evaluation_criteria', sa.Text(), nullable=True))
    op.add_column('onboarding_steps', sa.Column('passing_score', sa.Float(), server_default='3.0'))


def downgrade():
    # Remove the added columns
    op.drop_column('onboarding_steps', 'passing_score')
    op.drop_column('onboarding_steps', 'evaluation_criteria')
    op.drop_column('onboarding_steps', 'evaluation_prompt')
    op.drop_column('onboarding_steps', 'excel_sheet')
    op.drop_column('onboarding_steps', 'collection_flow')
