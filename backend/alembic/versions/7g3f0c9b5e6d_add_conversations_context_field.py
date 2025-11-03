"""add_conversations_context_field

Add context JSONB field to conversations table for Phase 5 Context Persistence.

Stores conversation state including writing style, audience, section, tone,
document filters, artifacts, and session metadata. Enables context restoration
across sessions.

Revision ID: 7g3f0c9b5e6d
Revises: 6f2e9b3a4d5c
Create Date: 2025-11-03 14:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '7g3f0c9b5e6d'
down_revision: Union[str, None] = '6f2e9b3a4d5c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Add context JSONB column to conversations table.

    The context field stores:
    - writing_style_id: UUID string
    - audience: String (e.g., "Federal RFP", "Foundation Grant")
    - section: String (e.g., "Organizational Capacity", "Program Description")
    - tone: String (e.g., "formal", "warm", "conversational")
    - filters: Object with doc_types, years, programs, outcome arrays
    - artifacts: Array of artifact versions with content and metadata
    - last_query: String (most recent user query)
    - session_metadata: Object with started_at, last_active timestamps
    """
    # Add context column with default empty JSON object
    op.add_column(
        'conversations',
        sa.Column(
            'context',
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb")
        )
    )

    # Create index on writing_style_id within context for quick lookups
    op.create_index(
        'idx_conversations_context_writing_style',
        'conversations',
        [sa.text("(context->>'writing_style_id')")],
        unique=False
    )


def downgrade() -> None:
    """
    Remove context field and associated index from conversations table.
    """
    # Drop index first
    op.drop_index('idx_conversations_context_writing_style', table_name='conversations')

    # Drop context column
    op.drop_column('conversations', 'context')
