"""baseline_schema

Creates the complete baseline database schema for org-archivist.

This migration creates all core tables, indexes, constraints, functions,
and triggers needed for the application. Previously, this was handled by
docker/postgres/init/01-init-database.sql, but has been migrated to Alembic
for better version control and rollback capabilities.

Revision ID: 2e0140e533a8
Revises:
Create Date: 2025-10-21 18:40:57.795322

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '2e0140e533a8'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Create the complete baseline schema.

    Creates:
    - PostgreSQL extensions (uuid-ossp, pg_trgm)
    - 8 core tables with constraints
    - All indexes
    - update_updated_at_column() function
    - Triggers for auto-updating timestamps
    """

    # =========================================================================
    # Enable PostgreSQL Extensions
    # =========================================================================
    op.execute('CREATE EXTENSION IF NOT EXISTS "uuid-ossp"')
    op.execute('CREATE EXTENSION IF NOT EXISTS "pg_trgm"')

    # =========================================================================
    # Create documents table
    # =========================================================================
    op.create_table(
        'documents',
        sa.Column('doc_id', postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text('uuid_generate_v4()')),
        sa.Column('filename', sa.String(255), nullable=False),
        sa.Column('doc_type', sa.String(50), nullable=False),
        sa.Column('year', sa.Integer, nullable=True),
        sa.Column('outcome', sa.String(50), nullable=True),
        sa.Column('notes', sa.Text, nullable=True),
        sa.Column('upload_date', sa.TIMESTAMP, nullable=False,
                  server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('file_size', sa.Integer, nullable=True),
        sa.Column('chunks_count', sa.Integer, nullable=True, server_default=sa.text('0')),
        sa.Column('created_by', sa.String(100), nullable=True),
        sa.Column('updated_at', sa.TIMESTAMP, nullable=True,
                  server_default=sa.text('CURRENT_TIMESTAMP')),

        # Constraints
        sa.CheckConstraint(
            "year >= 2000 AND year <= EXTRACT(YEAR FROM CURRENT_DATE) + 1",
            name='valid_year'
        ),
        sa.CheckConstraint(
            "doc_type IN ('Grant Proposal', 'Annual Report', 'Program Description', "
            "'Impact Report', 'Strategic Plan', 'Other')",
            name='valid_doc_type'
        ),
        sa.CheckConstraint(
            "outcome IN ('N/A', 'Funded', 'Not Funded', 'Pending', 'Final Report')",
            name='valid_outcome'
        )
    )

    # Create indexes for documents table
    op.create_index('idx_documents_filename', 'documents', ['filename'])
    op.create_index('idx_documents_doc_type', 'documents', ['doc_type'])
    op.create_index('idx_documents_year', 'documents', ['year'])
    op.create_index('idx_documents_upload_date', 'documents', ['upload_date'])

    # =========================================================================
    # Create document_programs table (many-to-many junction)
    # =========================================================================
    op.create_table(
        'document_programs',
        sa.Column('doc_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('program', sa.String(100), nullable=False),

        sa.PrimaryKeyConstraint('doc_id', 'program'),
        sa.ForeignKeyConstraint(['doc_id'], ['documents.doc_id'], ondelete='CASCADE'),
        sa.CheckConstraint(
            "program IN ('Early Childhood', 'Youth Development', 'Family Support', "
            "'Education', 'Health', 'General')",
            name='valid_program'
        )
    )

    op.create_index('idx_document_programs_program', 'document_programs', ['program'])

    # =========================================================================
    # Create document_tags table (many-to-many junction)
    # =========================================================================
    op.create_table(
        'document_tags',
        sa.Column('doc_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('tag', sa.String(100), nullable=False),

        sa.PrimaryKeyConstraint('doc_id', 'tag'),
        sa.ForeignKeyConstraint(['doc_id'], ['documents.doc_id'], ondelete='CASCADE')
    )

    op.create_index('idx_document_tags_tag', 'document_tags', ['tag'])

    # =========================================================================
    # Create prompt_templates table
    # =========================================================================
    op.create_table(
        'prompt_templates',
        sa.Column('prompt_id', postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text('uuid_generate_v4()')),
        sa.Column('name', sa.String(100), nullable=False, unique=True),
        sa.Column('category', sa.String(50), nullable=False),
        sa.Column('content', sa.Text, nullable=False),
        sa.Column('variables', postgresql.JSONB, nullable=True),
        sa.Column('active', sa.Boolean, nullable=True, server_default=sa.text('true')),
        sa.Column('created_at', sa.TIMESTAMP, nullable=False,
                  server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.TIMESTAMP, nullable=False,
                  server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('version', sa.Integer, nullable=True, server_default=sa.text('1')),

        sa.CheckConstraint(
            "category IN ('Brand Voice', 'Audience-Specific', 'Section-Specific', 'General')",
            name='valid_category'
        )
    )

    op.create_index('idx_prompt_templates_category', 'prompt_templates', ['category'])
    op.create_index('idx_prompt_templates_active', 'prompt_templates', ['active'])

    # =========================================================================
    # Create conversations table
    # =========================================================================
    op.create_table(
        'conversations',
        sa.Column('conversation_id', postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text('uuid_generate_v4()')),
        sa.Column('name', sa.String(255), nullable=True),
        sa.Column('created_at', sa.TIMESTAMP, nullable=False,
                  server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.TIMESTAMP, nullable=False,
                  server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('user_id', sa.String(100), nullable=True),
        sa.Column('metadata', postgresql.JSONB, nullable=True)
    )

    op.create_index('idx_conversations_user_id', 'conversations', ['user_id'])
    op.create_index('idx_conversations_updated_at', 'conversations', ['updated_at'])

    # =========================================================================
    # Create messages table
    # =========================================================================
    op.create_table(
        'messages',
        sa.Column('message_id', postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text('uuid_generate_v4()')),
        sa.Column('conversation_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('role', sa.String(20), nullable=False),
        sa.Column('content', sa.Text, nullable=False),
        sa.Column('sources', postgresql.JSONB, nullable=True),
        sa.Column('metadata', postgresql.JSONB, nullable=True),
        sa.Column('created_at', sa.TIMESTAMP, nullable=False,
                  server_default=sa.text('CURRENT_TIMESTAMP')),

        sa.ForeignKeyConstraint(['conversation_id'], ['conversations.conversation_id'],
                                ondelete='CASCADE'),
        sa.CheckConstraint(
            "role IN ('user', 'assistant')",
            name='valid_role'
        )
    )

    op.create_index('idx_messages_conversation_id', 'messages', ['conversation_id'])
    op.create_index('idx_messages_created_at', 'messages', ['created_at'])

    # =========================================================================
    # Create system_config table
    # =========================================================================
    op.create_table(
        'system_config',
        sa.Column('key', sa.String(100), primary_key=True),
        sa.Column('value', postgresql.JSONB, nullable=False),
        sa.Column('description', sa.Text, nullable=True),
        sa.Column('updated_at', sa.TIMESTAMP, nullable=False,
                  server_default=sa.text('CURRENT_TIMESTAMP'))
    )

    # =========================================================================
    # Create audit_log table
    # =========================================================================
    op.create_table(
        'audit_log',
        sa.Column('log_id', postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text('uuid_generate_v4()')),
        sa.Column('event_type', sa.String(50), nullable=False),
        sa.Column('entity_type', sa.String(50), nullable=True),
        sa.Column('entity_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('user_id', sa.String(100), nullable=True),
        sa.Column('details', postgresql.JSONB, nullable=True),
        sa.Column('created_at', sa.TIMESTAMP, nullable=False,
                  server_default=sa.text('CURRENT_TIMESTAMP'))
    )

    op.create_index('idx_audit_log_event_type', 'audit_log', ['event_type'])
    op.create_index('idx_audit_log_entity_type', 'audit_log', ['entity_type'])
    op.create_index('idx_audit_log_created_at', 'audit_log', ['created_at'])

    # =========================================================================
    # Create update_updated_at_column() function
    # =========================================================================
    op.execute("""
        CREATE OR REPLACE FUNCTION update_updated_at_column()
        RETURNS TRIGGER AS $$
        BEGIN
            NEW.updated_at = CURRENT_TIMESTAMP;
            RETURN NEW;
        END;
        $$ language 'plpgsql';
    """)

    # =========================================================================
    # Create triggers for auto-updating updated_at timestamps
    # =========================================================================
    op.execute("""
        CREATE TRIGGER update_documents_updated_at
        BEFORE UPDATE ON documents
        FOR EACH ROW
        EXECUTE FUNCTION update_updated_at_column();
    """)

    op.execute("""
        CREATE TRIGGER update_prompt_templates_updated_at
        BEFORE UPDATE ON prompt_templates
        FOR EACH ROW
        EXECUTE FUNCTION update_updated_at_column();
    """)

    op.execute("""
        CREATE TRIGGER update_conversations_updated_at
        BEFORE UPDATE ON conversations
        FOR EACH ROW
        EXECUTE FUNCTION update_updated_at_column();
    """)

    op.execute("""
        CREATE TRIGGER update_system_config_updated_at
        BEFORE UPDATE ON system_config
        FOR EACH ROW
        EXECUTE FUNCTION update_updated_at_column();
    """)


def downgrade() -> None:
    """
    Drop all schema objects created by this migration.

    This provides a clean rollback path if needed.
    """

    # Drop triggers
    op.execute('DROP TRIGGER IF EXISTS update_system_config_updated_at ON system_config')
    op.execute('DROP TRIGGER IF EXISTS update_conversations_updated_at ON conversations')
    op.execute('DROP TRIGGER IF EXISTS update_prompt_templates_updated_at ON prompt_templates')
    op.execute('DROP TRIGGER IF EXISTS update_documents_updated_at ON documents')

    # Drop function
    op.execute('DROP FUNCTION IF EXISTS update_updated_at_column()')

    # Drop tables (in reverse order to respect foreign keys)
    op.drop_table('audit_log')
    op.drop_table('system_config')
    op.drop_table('messages')
    op.drop_table('conversations')
    op.drop_table('prompt_templates')
    op.drop_table('document_tags')
    op.drop_table('document_programs')
    op.drop_table('documents')

    # Drop extensions
    op.execute('DROP EXTENSION IF EXISTS pg_trgm')
    op.execute('DROP EXTENSION IF EXISTS "uuid-ossp"')
