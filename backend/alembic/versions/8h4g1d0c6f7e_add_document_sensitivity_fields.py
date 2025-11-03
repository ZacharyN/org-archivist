"""add_document_sensitivity_fields

Add sensitivity validation fields to documents table for Phase 5.

Adds fields to track document sensitivity classification, validation status,
and confirmation details. Enforces sensitivity checks before document upload
to prevent accidental upload of confidential content.

Revision ID: 8h4g1d0c6f7e
Revises: 7g3f0c9b5e6d
Create Date: 2025-11-03 15:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '8h4g1d0c6f7e'
down_revision: Union[str, None] = '7g3f0c9b5e6d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Add sensitivity validation fields to documents table.

    Adds five new columns:
    - is_sensitive: Boolean flag indicating if document contains sensitive data
    - sensitivity_level: Classification level (low, medium, high)
    - sensitivity_notes: Optional notes about why document is marked sensitive
    - sensitivity_confirmed_at: Timestamp when sensitivity was confirmed
    - sensitivity_confirmed_by: User who confirmed the sensitivity classification

    Existing documents default to is_sensitive=false for backward compatibility.
    """
    # Add is_sensitive column with default false
    op.add_column(
        'documents',
        sa.Column(
            'is_sensitive',
            sa.Boolean(),
            nullable=False,
            server_default=sa.text('false')
        )
    )

    # Add sensitivity_level column with CHECK constraint
    op.add_column(
        'documents',
        sa.Column(
            'sensitivity_level',
            sa.String(length=20),
            nullable=True
        )
    )

    # Add CHECK constraint for sensitivity_level values
    op.create_check_constraint(
        'valid_sensitivity_level',
        'documents',
        "sensitivity_level IN ('low', 'medium', 'high') OR sensitivity_level IS NULL"
    )

    # Add sensitivity_notes column
    op.add_column(
        'documents',
        sa.Column(
            'sensitivity_notes',
            sa.Text(),
            nullable=True
        )
    )

    # Add sensitivity_confirmed_at timestamp
    op.add_column(
        'documents',
        sa.Column(
            'sensitivity_confirmed_at',
            sa.DateTime(),
            nullable=True
        )
    )

    # Add sensitivity_confirmed_by user identifier
    op.add_column(
        'documents',
        sa.Column(
            'sensitivity_confirmed_by',
            sa.String(length=100),
            nullable=True
        )
    )

    # Create composite index on (is_sensitive, sensitivity_level) for common queries
    op.create_index(
        'idx_documents_sensitivity',
        'documents',
        ['is_sensitive', 'sensitivity_level'],
        unique=False
    )


def downgrade() -> None:
    """
    Remove sensitivity validation fields from documents table.
    """
    # Drop index first
    op.drop_index('idx_documents_sensitivity', table_name='documents')

    # Drop columns in reverse order
    op.drop_column('documents', 'sensitivity_confirmed_by')
    op.drop_column('documents', 'sensitivity_confirmed_at')
    op.drop_column('documents', 'sensitivity_notes')

    # Drop CHECK constraint before dropping the column
    op.drop_constraint('valid_sensitivity_level', 'documents', type_='check')
    op.drop_column('documents', 'sensitivity_level')

    op.drop_column('documents', 'is_sensitive')
