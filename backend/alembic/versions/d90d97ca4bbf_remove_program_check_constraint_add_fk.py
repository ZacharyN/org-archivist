"""remove_program_check_constraint_add_fk

Revision ID: d90d97ca4bbf
Revises: 9i5h2e1d7f8g
Create Date: 2025-11-14 20:13:35.397920

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd90d97ca4bbf'
down_revision: Union[str, None] = '9i5h2e1d7f8g'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Remove CHECK constraint and add foreign key to programs table.

    This migration:
    1. Drops the hardcoded CHECK constraint on document_programs.program
    2. Verifies no orphaned data exists (programs not in programs table)
    3. Adds a foreign key constraint to programs.name
    4. Adds an index for foreign key performance
    """

    # Step 1: Drop the existing CHECK constraint
    op.drop_constraint('valid_program', 'document_programs', type_='check')

    # Step 2: Verify all existing programs are in programs table
    # This query will fail the migration if orphaned data exists
    op.execute("""
        -- Verify no orphaned programs before adding FK
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1
                FROM document_programs dp
                LEFT JOIN programs p ON dp.program = p.name
                WHERE p.name IS NULL
            ) THEN
                RAISE EXCEPTION 'Found document_programs entries with programs not in programs table. Clean up data before applying this migration.';
            END IF;
        END $$;
    """)

    # Step 3: Add foreign key constraint
    op.create_foreign_key(
        'fk_document_programs_program',
        'document_programs',  # source table
        'programs',           # target table
        ['program'],          # source column
        ['name'],             # target column
        ondelete='RESTRICT'   # prevent deletion of programs in use
    )

    # Step 4: Add index for foreign key performance
    op.create_index(
        'idx_document_programs_program_fk',
        'document_programs',
        ['program']
    )


def downgrade() -> None:
    """
    Restore CHECK constraint and remove foreign key.

    This rollback:
    1. Drops the foreign key index
    2. Drops the foreign key constraint
    3. Restores the original CHECK constraint
    """

    # Step 1: Drop the foreign key index
    op.drop_index('idx_document_programs_program_fk', 'document_programs')

    # Step 2: Drop the foreign key constraint
    op.drop_constraint('fk_document_programs_program', 'document_programs', type_='foreignkey')

    # Step 3: Restore original CHECK constraint
    op.create_check_constraint(
        'valid_program',
        'document_programs',
        "program IN ('Early Childhood', 'Youth Development', 'Family Support', 'Education', 'Health', 'General')"
    )
