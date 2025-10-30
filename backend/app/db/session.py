"""
Database session management for async SQLAlchemy

Provides:
- Async database engine configuration
- Async session factory
- FastAPI dependency for database sessions
"""

from typing import AsyncGenerator
import logging

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    AsyncEngine,
    create_async_engine,
    async_sessionmaker
)
from sqlalchemy.pool import NullPool

from backend.app.config import get_settings

settings = get_settings()
logger = logging.getLogger(__name__)

# Create async engine
# Note: PostgreSQL async requires asyncpg driver
# Connection string should be: postgresql+asyncpg://user:password@host:port/database
engine: AsyncEngine = create_async_engine(
    settings.database_url.replace("postgresql://", "postgresql+asyncpg://"),
    echo=settings.debug,  # Log all SQL statements in debug mode
    future=True,
    pool_pre_ping=True,  # Verify connections before using them
    pool_size=5,  # Number of connections to maintain
    max_overflow=10,  # Maximum number of connections to create above pool_size
    poolclass=NullPool if settings.is_testing else None,  # Disable pooling in tests
)

# Create async session factory
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,  # Don't expire objects after commit
    autocommit=False,
    autoflush=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI dependency that provides a database session

    Yields an async database session and ensures it's closed after use.
    Handles rollback on exceptions.

    Usage:
        @app.get("/items")
        async def get_items(db: AsyncSession = Depends(get_db)):
            result = await db.execute(select(Item))
            return result.scalars().all()

    Yields:
        AsyncSession: Database session

    Example:
        from fastapi import Depends
        from backend.app.db.session import get_db

        @app.get("/users")
        async def get_users(db: AsyncSession = Depends(get_db)):
            stmt = select(User)
            result = await db.execute(stmt)
            return result.scalars().all()
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception as e:
            await session.rollback()
            logger.error(f"Database session error: {e}")
            raise
        finally:
            await session.close()


async def init_db():
    """
    Initialize the database

    Creates all tables defined in the models.
    Should only be used in development. Use Alembic migrations in production.
    """
    from backend.app.db.models import Base

    async with engine.begin() as conn:
        logger.info("Creating database tables...")
        await conn.run_sync(Base.metadata.create_all)
        logger.info("Database tables created successfully")


async def close_db():
    """
    Close the database engine

    Should be called on application shutdown.
    """
    await engine.dispose()
    logger.info("Database engine disposed")
