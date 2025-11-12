"""create_programs_table

Create programs table to store program definitions dynamically instead of hardcoded CHECK constraints.

Replaces the hardcoded program list in document_programs table with a flexible,
database-backed program management system. Programs can be created, updated,
and managed through the application instead of requiring schema migrations.

Revision ID: 9i5h2e1d7f8g
Revises: 8h4g1d0c6f7e
Create Date: 2025-11-11 19:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '9i5h2e1d7f8g'
down_revision: Union[str, None] = '8h4g1d0c6f7e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Create programs table for dynamic program management.

    Programs table stores:
    - program_id: UUID primary key with auto-generation
    - name: Unique program name (max 100 chars)
    - description: Optional text description of the program
    - display_order: Integer for sorting (default 0, higher = higher priority)
    - active: Boolean flag for active/inactive programs (default true)
    - created_at: Timestamp when program was created
    - updated_at: Timestamp when program was last modified (auto-updated via trigger)
    - created_by: Foreign key to users table (nullable, SET NULL on delete)
    """

    # Create programs table
    op.create_table(
        'programs',
        sa.Column('program_id', postgresql.UUID(as_uuid=True), nullable=False,
                  server_default=sa.text('uuid_generate_v4()')),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('display_order', sa.Integer(), nullable=False,
                  server_default=sa.text('0')),
        sa.Column('active', sa.Boolean(), nullable=False,
                  server_default=sa.text('true')),
        sa.Column('created_at', sa.DateTime(), nullable=False,
                  server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(), nullable=False,
                  server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('created_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.PrimaryKeyConstraint('program_id'),
        sa.UniqueConstraint('name', name='unique_program_name')
    )

    # Add foreign key constraint to users table
    op.create_foreign_key(
        'fk_programs_created_by',
        'programs',
        'users',
        ['created_by'],
        ['user_id'],
        ondelete='SET NULL'
    )

    # Create indexes for efficient lookups and sorting
    op.create_index('idx_programs_name', 'programs', ['name'], unique=False)
    op.create_index('idx_programs_active', 'programs', ['active'], unique=False)
    op.create_index('idx_programs_display_order', 'programs', ['display_order'], unique=False)

    # Create trigger function for updating updated_at timestamp
    op.execute("""
        CREATE OR REPLACE FUNCTION update_programs_updated_at()
        RETURNS TRIGGER AS $$
        BEGIN
            NEW.updated_at = CURRENT_TIMESTAMP;
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
    """)

    # Create trigger on programs table
    op.execute("""
        CREATE TRIGGER trigger_update_programs_updated_at
        BEFORE UPDATE ON programs
        FOR EACH ROW
        EXECUTE FUNCTION update_programs_updated_at();
    """)

    # Seed initial programs from existing hardcoded list
    # These correspond to the programs currently in the document_programs CHECK constraint
    op.execute("""
        INSERT INTO programs (name, description, display_order, active) VALUES
        ('Early Childhood', 'Early childhood development and education programs', 60, true),
        ('Youth Development', 'Youth development and mentoring programs', 50, true),
        ('Family Support', 'Family support and strengthening programs', 40, true),
        ('Education', 'Educational programs and initiatives', 30, true),
        ('Health', 'Health and wellness programs', 20, true),
        ('General', 'General organizational programs', 10, true);
    """)


def downgrade() -> None:
    """
    Drop programs table and associated indexes, triggers, and constraints.
    """
    # Drop trigger and trigger function
    op.execute('DROP TRIGGER IF EXISTS trigger_update_programs_updated_at ON programs;')
    op.execute('DROP FUNCTION IF EXISTS update_programs_updated_at();')

    # Drop indexes
    op.drop_index('idx_programs_display_order', table_name='programs')
    op.drop_index('idx_programs_active', table_name='programs')
    op.drop_index('idx_programs_name', table_name='programs')

    # Drop foreign key constraint
    op.drop_constraint('fk_programs_created_by', 'programs', type_='foreignkey')

    # Drop unique constraint (if it wasn't automatically dropped with table)
    # Note: This is handled by the table drop, but including for clarity

    # Drop programs table
    op.drop_table('programs')
