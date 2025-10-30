"""
Database migration utilities for running Alembic migrations on application startup
"""
import asyncio
import logging
import subprocess
import time
from pathlib import Path
from typing import Optional

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

logger = logging.getLogger(__name__)


class MigrationError(Exception):
    """Exception raised when migration operations fail"""
    pass


async def wait_for_database(
    database_url: str,
    max_attempts: int = 3,
    retry_delay_seconds: int = 5,
    timeout_seconds: int = 60
) -> bool:
    """
    Wait for database to be available before running migrations

    Args:
        database_url: Database connection URL
        max_attempts: Maximum number of connection attempts
        retry_delay_seconds: Delay between retry attempts
        timeout_seconds: Timeout for each connection attempt

    Returns:
        bool: True if database is available, False otherwise
    """
    logger.info("Checking database connectivity...")

    # Convert PostgreSQL URL to async format if needed
    if database_url.startswith("postgresql://"):
        async_url = database_url.replace("postgresql://", "postgresql+asyncpg://", 1)
    else:
        async_url = database_url

    for attempt in range(1, max_attempts + 1):
        try:
            # Create temporary engine for connection test
            engine = create_async_engine(async_url, echo=False)

            async with engine.begin() as conn:
                # Simple connectivity check
                await conn.execute(text("SELECT 1"))

            await engine.dispose()
            logger.info("✓ Database connection successful")
            return True

        except Exception as e:
            logger.warning(
                f"Database connection attempt {attempt}/{max_attempts} failed: {e}"
            )

            if attempt < max_attempts:
                logger.info(f"Retrying in {retry_delay_seconds} seconds...")
                await asyncio.sleep(retry_delay_seconds)
            else:
                logger.error("Failed to connect to database after all retry attempts")
                return False

    return False


def run_alembic_upgrade(
    alembic_config_path: Optional[Path] = None,
    timeout_seconds: int = 60
) -> tuple[bool, str]:
    """
    Run Alembic upgrade to head synchronously

    Args:
        alembic_config_path: Path to alembic.ini file (defaults to backend/alembic.ini)
        timeout_seconds: Timeout for the migration operation

    Returns:
        tuple[bool, str]: (success, output_message)
    """
    # Determine alembic.ini location
    if alembic_config_path is None:
        # Try to find alembic.ini in the backend directory
        backend_dir = Path(__file__).parent.parent.parent
        alembic_config_path = backend_dir / "alembic.ini"

    if not alembic_config_path.exists():
        error_msg = f"Alembic config not found at {alembic_config_path}"
        logger.error(error_msg)
        return False, error_msg

    logger.info(f"Running migrations from: {alembic_config_path}")

    try:
        # Run alembic upgrade head
        result = subprocess.run(
            ["alembic", "-c", str(alembic_config_path), "upgrade", "head"],
            cwd=alembic_config_path.parent,
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
            check=False
        )

        # Log the output
        if result.stdout:
            logger.info(f"Alembic output:\n{result.stdout}")

        if result.returncode == 0:
            logger.info("✓ Migrations completed successfully")
            return True, result.stdout
        else:
            error_msg = f"Migration failed with exit code {result.returncode}"
            if result.stderr:
                error_msg += f"\nError: {result.stderr}"
                logger.error(f"Alembic error:\n{result.stderr}")
            return False, error_msg

    except subprocess.TimeoutExpired:
        error_msg = f"Migration timed out after {timeout_seconds} seconds"
        logger.error(error_msg)
        return False, error_msg

    except FileNotFoundError:
        error_msg = (
            "Alembic command not found. Make sure alembic is installed: "
            "pip install alembic"
        )
        logger.error(error_msg)
        return False, error_msg

    except Exception as e:
        error_msg = f"Unexpected error during migration: {e}"
        logger.error(error_msg, exc_info=True)
        return False, error_msg


async def run_migrations_with_retry(
    database_url: str,
    max_attempts: int = 3,
    retry_delay_seconds: int = 5,
    timeout_seconds: int = 60,
    alembic_config_path: Optional[Path] = None
) -> None:
    """
    Run database migrations with retry logic and connection checking

    Args:
        database_url: Database connection URL
        max_attempts: Maximum number of retry attempts
        retry_delay_seconds: Delay between retry attempts
        timeout_seconds: Timeout for migration operations
        alembic_config_path: Path to alembic.ini file

    Raises:
        MigrationError: If migrations fail after all retry attempts
    """
    logger.info("Starting database migration process...")

    # First, wait for database to be available
    db_available = await wait_for_database(
        database_url=database_url,
        max_attempts=max_attempts,
        retry_delay_seconds=retry_delay_seconds,
        timeout_seconds=timeout_seconds
    )

    if not db_available:
        raise MigrationError(
            "Database is not available. Cannot run migrations. "
            "Please check your database connection settings."
        )

    # Try to run migrations with retry
    for attempt in range(1, max_attempts + 1):
        logger.info(f"Migration attempt {attempt}/{max_attempts}...")

        # Run migrations in executor to avoid blocking
        loop = asyncio.get_event_loop()
        success, output = await loop.run_in_executor(
            None,
            run_alembic_upgrade,
            alembic_config_path,
            timeout_seconds
        )

        if success:
            logger.info("Database migrations completed successfully")
            return

        # Migration failed
        logger.error(f"Migration attempt {attempt} failed: {output}")

        if attempt < max_attempts:
            logger.info(f"Retrying in {retry_delay_seconds} seconds...")
            await asyncio.sleep(retry_delay_seconds)
        else:
            raise MigrationError(
                f"Failed to run migrations after {max_attempts} attempts. "
                f"Last error: {output}"
            )


async def run_startup_migrations(
    database_url: str,
    disable_auto_migrations: bool = False,
    max_attempts: int = 3,
    retry_delay_seconds: int = 5,
    timeout_seconds: int = 60
) -> None:
    """
    Run migrations on application startup (if not disabled)

    Args:
        database_url: Database connection URL
        disable_auto_migrations: If True, skip migrations
        max_attempts: Maximum number of retry attempts
        retry_delay_seconds: Delay between retry attempts
        timeout_seconds: Timeout for migration operations

    Raises:
        MigrationError: If migrations fail (only when auto-migrations enabled)
    """
    if disable_auto_migrations:
        logger.info("Automatic migrations are disabled (DISABLE_AUTO_MIGRATIONS=true)")
        logger.info("Run migrations manually with: alembic upgrade head")
        return

    logger.info("Automatic migrations enabled - running migrations...")

    try:
        await run_migrations_with_retry(
            database_url=database_url,
            max_attempts=max_attempts,
            retry_delay_seconds=retry_delay_seconds,
            timeout_seconds=timeout_seconds
        )
    except MigrationError as e:
        logger.error(f"Migration failed: {e}")
        logger.error(
            "Application startup will continue, but database may not be up to date. "
            "Please run migrations manually: alembic upgrade head"
        )
        # Re-raise to allow application to decide whether to continue or exit
        raise
