"""add_writing_styles_user_fk

Add foreign key constraint to writing_styles.created_by referencing users.user_id.

This migration completes the writing_styles table schema by adding the foreign key
constraint that was deferred when the table was created, waiting for the users table.

Revision ID: 5b9c3d8e1f4a
Revises: 4a7e8b2d6c1f
Create Date: 2025-10-31 03:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '5b9c3d8e1f4a'
down_revision: Union[str, None] = '4a7e8b2d6c1f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Add foreign key constraint to writing_styles.created_by.

    This links the created_by column to users.user_id, enforcing referential integrity.
    The constraint is nullable, allowing writing_styles records to exist without
    a specific user (e.g., system-generated styles).

    Note: This migration assumes:
    - Both writing_styles and users tables exist
    - created_by column is already UUID type
    - Any existing created_by values are either NULL or valid user_ids
    """
    op.create_foreign_key(
        constraint_name='fk_writing_styles_created_by',
        source_table='writing_styles',
        referent_table='users',
        local_cols=['created_by'],
        remote_cols=['user_id'],
        ondelete='SET NULL'  # If user is deleted, set created_by to NULL
    )


def downgrade() -> None:
    """
    Remove foreign key constraint from writing_styles.created_by.

    This reverts the table to its previous state where created_by was a plain UUID
    column without referential integrity enforcement.
    """
    op.drop_constraint(
        constraint_name='fk_writing_styles_created_by',
        table_name='writing_styles',
        type_='foreignkey'
    )
