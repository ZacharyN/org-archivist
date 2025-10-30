"""add_writing_styles_table

Add writing_styles table for Phase 3 Writing Styles feature.
Stores AI-generated writing style prompts with samples and analysis metadata.

Revision ID: 3f8d9a1c5e2b
Revises: 2e0140e533a8
Create Date: 2025-10-30 19:50:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '3f8d9a1c5e2b'
down_revision: Union[str, None] = '2e0140e533a8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Create writing_styles table for storing AI-generated writing style prompts.

    This table stores:
    - Style metadata (name, type, description)
    - Generated style prompts (1500-2000 words)
    - Original writing samples (JSONB array)
    - AI analysis metadata (JSONB object)
    - Activation status and timestamps
    """
    op.create_table(
        'writing_styles',
        sa.Column('style_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('type', sa.String(length=50), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('prompt_content', sa.Text(), nullable=False),
        sa.Column('samples', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('analysis_metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('sample_count', sa.Integer(), nullable=True),
        sa.Column('active', sa.Boolean(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.Column('created_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.CheckConstraint(
            "type IN ('grant', 'proposal', 'report', 'general')",
            name='valid_style_type'
        ),
        # Foreign key to users table will be added when users table is created
        # sa.ForeignKeyConstraint(['created_by'], ['users.user_id'], ),
        sa.PrimaryKeyConstraint('style_id'),
        sa.UniqueConstraint('name')
    )

    # Create indexes for common queries
    op.create_index('idx_writing_styles_type', 'writing_styles', ['type'], unique=False)
    op.create_index('idx_writing_styles_active', 'writing_styles', ['active'], unique=False)
    op.create_index('idx_writing_styles_created_by', 'writing_styles', ['created_by'], unique=False)


def downgrade() -> None:
    """
    Drop writing_styles table and associated indexes.
    """
    # Drop indexes first
    op.drop_index('idx_writing_styles_created_by', table_name='writing_styles')
    op.drop_index('idx_writing_styles_active', table_name='writing_styles')
    op.drop_index('idx_writing_styles_type', table_name='writing_styles')

    # Drop table
    op.drop_table('writing_styles')
