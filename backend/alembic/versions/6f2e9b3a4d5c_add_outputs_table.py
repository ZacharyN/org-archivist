"""add_outputs_table

Add outputs table for Phase 4 Past Outputs Dashboard.

Stores generated grant content with success tracking for monitoring proposal
outcomes, calculating success rates, and improving future submissions.

Revision ID: 6f2e9b3a4d5c
Revises: 5b9c3d8e1f4a
Create Date: 2025-11-01 16:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '6f2e9b3a4d5c'
down_revision: Union[str, None] = '5b9c3d8e1f4a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Create outputs table for storing generated content and tracking success.

    This table stores:
    - Generated content (title, content, word_count)
    - Content classification (output_type: grant_proposal, budget_narrative, etc.)
    - Status tracking (draft, submitted, pending, awarded, not_awarded)
    - Success tracking (funder_name, amounts, dates, notes)
    - Relationships (conversation_id, writing_style_id, created_by)
    - Metadata (sources, confidence, generation parameters as JSONB)
    """
    op.create_table(
        'outputs',
        sa.Column('output_id', postgresql.UUID(as_uuid=True), nullable=False,
                  server_default=sa.text('uuid_generate_v4()')),
        sa.Column('conversation_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('output_type', sa.String(length=50), nullable=False),
        sa.Column('title', sa.String(length=500), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('word_count', sa.Integer(), nullable=True),
        sa.Column('status', sa.String(length=50), nullable=False,
                  server_default=sa.text("'draft'")),
        sa.Column('writing_style_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('funder_name', sa.String(length=255), nullable=True),
        sa.Column('requested_amount', sa.Numeric(precision=12, scale=2), nullable=True),
        sa.Column('awarded_amount', sa.Numeric(precision=12, scale=2), nullable=True),
        sa.Column('submission_date', sa.Date(), nullable=True),
        sa.Column('decision_date', sa.Date(), nullable=True),
        sa.Column('success_notes', sa.Text(), nullable=True),
        sa.Column('metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('created_by', sa.String(length=100), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False,
                  server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(), nullable=False,
                  server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.CheckConstraint(
            "output_type IN ('grant_proposal', 'budget_narrative', 'program_description', 'impact_summary', 'other')",
            name='valid_output_type'
        ),
        sa.CheckConstraint(
            "status IN ('draft', 'submitted', 'pending', 'awarded', 'not_awarded')",
            name='valid_status'
        ),
        sa.ForeignKeyConstraint(
            ['conversation_id'],
            ['conversations.conversation_id'],
            name='fk_outputs_conversation_id',
            ondelete='SET NULL'
        ),
        sa.ForeignKeyConstraint(
            ['writing_style_id'],
            ['writing_styles.style_id'],
            name='fk_outputs_writing_style_id',
            ondelete='SET NULL'
        ),
        sa.PrimaryKeyConstraint('output_id')
    )

    # Create indexes for common queries
    op.create_index('idx_outputs_conversation_id', 'outputs', ['conversation_id'], unique=False)
    op.create_index('idx_outputs_output_type', 'outputs', ['output_type'], unique=False)
    op.create_index('idx_outputs_status', 'outputs', ['status'], unique=False)
    op.create_index('idx_outputs_writing_style_id', 'outputs', ['writing_style_id'], unique=False)
    op.create_index('idx_outputs_created_by', 'outputs', ['created_by'], unique=False)
    op.create_index('idx_outputs_created_at', 'outputs', ['created_at'], unique=False)

    # Create trigger function for updating updated_at timestamp
    op.execute("""
        CREATE OR REPLACE FUNCTION update_outputs_updated_at()
        RETURNS TRIGGER AS $$
        BEGIN
            NEW.updated_at = CURRENT_TIMESTAMP;
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
    """)

    # Create trigger on outputs table
    op.execute("""
        CREATE TRIGGER trigger_update_outputs_updated_at
        BEFORE UPDATE ON outputs
        FOR EACH ROW
        EXECUTE FUNCTION update_outputs_updated_at();
    """)


def downgrade() -> None:
    """
    Drop outputs table and associated indexes/triggers.
    """
    # Drop trigger and trigger function
    op.execute('DROP TRIGGER IF EXISTS trigger_update_outputs_updated_at ON outputs;')
    op.execute('DROP FUNCTION IF EXISTS update_outputs_updated_at();')

    # Drop indexes
    op.drop_index('idx_outputs_created_at', table_name='outputs')
    op.drop_index('idx_outputs_created_by', table_name='outputs')
    op.drop_index('idx_outputs_writing_style_id', table_name='outputs')
    op.drop_index('idx_outputs_status', table_name='outputs')
    op.drop_index('idx_outputs_output_type', table_name='outputs')
    op.drop_index('idx_outputs_conversation_id', table_name='outputs')

    # Drop table
    op.drop_table('outputs')
