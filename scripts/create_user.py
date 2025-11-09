#!/usr/bin/env python3
"""
Script to create a user account in the Org Archivist database.

Usage:
    # Interactive mode (prompts for credentials):
    docker exec org-archivist-backend python scripts/create_user.py

    # Using environment variables (for automation):
    docker exec -e USER_EMAIL=user@example.com \
                -e USER_PASSWORD=SecurePassword123 \
                -e USER_FULL_NAME="John Doe" \
                -e USER_ROLE=admin \
                org-archivist-backend python scripts/create_user.py

Note: Never hardcode credentials in this file. Always use environment variables
      or interactive prompts to avoid committing secrets to version control.
"""

import asyncio
import sys
from pathlib import Path

# Run from backend directory
sys.path.insert(0, "/app/backend")

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.ext.asyncio import async_sessionmaker
from sqlalchemy import select

from app.db.models import User, UserRole
from app.services.auth_service import AuthService


async def create_user():
    """Create a new user account."""
    import os
    import getpass

    # Database configuration
    # Use org-archivist-postgres for Docker network connectivity
    DATABASE_URL = os.getenv(
        "DATABASE_URL",
        "postgresql+asyncpg://user:password@org-archivist-postgres:5432/org_archivist"
    )

    # User details from environment variables or prompts
    email = os.getenv("USER_EMAIL") or input("Enter email: ")
    password = os.getenv("USER_PASSWORD") or getpass.getpass("Enter password: ")
    full_name = os.getenv("USER_FULL_NAME") or input("Enter full name: ")
    role_str = os.getenv("USER_ROLE", "admin").upper()
    role = UserRole[role_str]  # Convert string to UserRole enum

    # Create async engine
    engine = create_async_engine(
        DATABASE_URL,
        echo=False,
        pool_pre_ping=True
    )

    # Create session maker
    async_session = async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False
    )

    async with async_session() as session:
        try:
            # Check if user already exists
            stmt = select(User).where(User.email == email)
            result = await session.execute(stmt)
            existing_user = result.scalar_one_or_none()

            if existing_user:
                print(f"✗ User with email {email} already exists!")
                print(f"  User ID: {existing_user.user_id}")
                print(f"  Role: {existing_user.role}")
                print(f"  Created: {existing_user.created_at}")
                return False

            # Hash password
            hashed_password = AuthService.hash_password(password)

            # Create new user
            new_user = User(
                email=email,
                hashed_password=hashed_password,
                full_name=full_name,
                role=role,
                is_active=True,
                is_superuser=True  # Admin user is also superuser
            )

            session.add(new_user)
            await session.commit()
            await session.refresh(new_user)

            print("✓ User account created successfully!")
            print(f"\n  Email: {new_user.email}")
            print(f"  Name: {new_user.full_name}")
            print(f"  Role: {new_user.role}")
            print(f"  User ID: {new_user.user_id}")
            print(f"  Created: {new_user.created_at}")
            print(f"\n  Use the email and password you provided to log in.")

            return True

        except Exception as e:
            print(f"✗ Error creating user: {e}")
            await session.rollback()
            return False
        finally:
            await engine.dispose()


if __name__ == "__main__":
    print("Creating user account for Org Archivist...")
    print("=" * 60)

    result = asyncio.run(create_user())

    if result:
        print("\n" + "=" * 60)
        print("You can now login to the Streamlit frontend with these credentials.")
        sys.exit(0)
    else:
        sys.exit(1)
