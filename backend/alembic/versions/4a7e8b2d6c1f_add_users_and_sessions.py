"""add_users_and_sessions

Add users and user_sessions tables for Phase 2 Authentication & User Management.

Stores user accounts with role-based access control (admin/editor/writer) and
session management for JWT token tracking.

Revision ID: 4a7e8b2d6c1f
Revises: d160586f5e0f
Create Date: 2025-10-30 22:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '4a7e8b2d6c1f'
down_revision: Union[str, None] = 'd160586f5e0f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Create users and user_sessions tables for authentication system.

    Users table stores:
    - User credentials (email, password_hash)
    - User profile (full_name)
    - Access control (role: admin/editor/writer)
    - Account status (is_active)
    - Timestamps (created_at, updated_at with trigger)

    User_sessions table stores:
    - Session tokens for JWT authentication
    - Token expiration tracking
    - Foreign key relationship to users (CASCADE delete)
    """

    # Create users table
    op.create_table(
        'users',
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False,
                  server_default=sa.text('uuid_generate_v4()')),
        sa.Column('email', sa.String(length=255), nullable=False),
        sa.Column('hashed_password', sa.String(length=255), nullable=False),
        sa.Column('full_name', sa.String(length=255), nullable=True),
        sa.Column('role', sa.String(length=20), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.text('TRUE')),
        sa.Column('is_superuser', sa.Boolean(), nullable=False, server_default=sa.text('FALSE')),
        sa.Column('created_at', sa.DateTime(), nullable=False,
                  server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(), nullable=False,
                  server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.CheckConstraint(
            "role IN ('admin', 'editor', 'writer')",
            name='valid_user_role'
        ),
        sa.PrimaryKeyConstraint('user_id'),
        sa.UniqueConstraint('email')
    )

    # Create indexes for users table
    op.create_index('idx_users_email', 'users', ['email'], unique=False)
    op.create_index('idx_users_role', 'users', ['role'], unique=False)
    op.create_index('idx_users_is_active', 'users', ['is_active'], unique=False)

    # Create trigger function for updating updated_at timestamp
    op.execute("""
        CREATE OR REPLACE FUNCTION update_users_updated_at()
        RETURNS TRIGGER AS $$
        BEGIN
            NEW.updated_at = CURRENT_TIMESTAMP;
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
    """)

    # Create trigger on users table
    op.execute("""
        CREATE TRIGGER trigger_update_users_updated_at
        BEFORE UPDATE ON users
        FOR EACH ROW
        EXECUTE FUNCTION update_users_updated_at();
    """)

    # Create user_sessions table
    op.create_table(
        'user_sessions',
        sa.Column('session_id', postgresql.UUID(as_uuid=True), nullable=False,
                  server_default=sa.text('uuid_generate_v4()')),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('access_token', sa.String(length=500), nullable=False),
        sa.Column('refresh_token', sa.String(length=500), nullable=True),
        sa.Column('expires_at', sa.DateTime(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False,
                  server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('ip_address', sa.String(length=45), nullable=True),
        sa.Column('user_agent', sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(
            ['user_id'],
            ['users.user_id'],
            name='fk_user_sessions_user_id',
            ondelete='CASCADE'
        ),
        sa.PrimaryKeyConstraint('session_id')
    )

    # Create indexes for user_sessions table
    op.create_index('idx_user_sessions_user_id', 'user_sessions', ['user_id'], unique=False)
    op.create_index('idx_user_sessions_access_token', 'user_sessions', ['access_token'], unique=False)
    op.create_index('idx_user_sessions_expires_at', 'user_sessions', ['expires_at'], unique=False)


def downgrade() -> None:
    """
    Drop users and user_sessions tables and associated indexes/triggers.
    """
    # Drop indexes from user_sessions first
    op.drop_index('idx_user_sessions_expires_at', table_name='user_sessions')
    op.drop_index('idx_user_sessions_access_token', table_name='user_sessions')
    op.drop_index('idx_user_sessions_user_id', table_name='user_sessions')

    # Drop user_sessions table (must drop before users due to FK)
    op.drop_table('user_sessions')

    # Drop trigger and trigger function
    op.execute('DROP TRIGGER IF EXISTS trigger_update_users_updated_at ON users;')
    op.execute('DROP FUNCTION IF EXISTS update_users_updated_at();')

    # Drop indexes from users table
    op.drop_index('idx_users_is_active', table_name='users')
    op.drop_index('idx_users_role', table_name='users')
    op.drop_index('idx_users_email', table_name='users')

    # Drop users table
    op.drop_table('users')
