"""baseline_schema

Baseline migration capturing the current database schema.

This migration does nothing on upgrade/downgrade because the schema
already exists in the database (created by docker/postgres/init/01-init-database.sql).

This establishes the starting point for future Alembic migrations.

Revision ID: 2e0140e533a8
Revises: 
Create Date: 2025-10-21 18:40:57.795322

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '2e0140e533a8'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Baseline migration - no changes needed.
    
    The current schema already exists in the database via
    docker/postgres/init/01-init-database.sql
    
    This migration establishes the baseline for future migrations.
    """
    # No operations - schema already exists
    pass


def downgrade() -> None:
    """
    Baseline migration - no downgrade possible.
    
    This is the initial state of the database.
    """
    # No operations - this is the baseline
    pass
