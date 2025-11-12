"""
Main FastAPI application for Org Archivist backend
"""
import logging
import os
from logging.handlers import TimedRotatingFileHandler, RotatingFileHandler
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import settings


def configure_logging():
    """
    Configure application logging with rotation support

    Sets up both console and file logging with automatic rotation to prevent
    unbounded log file growth. Supports both time-based (daily) and size-based
    rotation strategies.
    """
    # Create logs directory if it doesn't exist
    log_dir = os.path.dirname(settings.log_file)
    if log_dir and not os.path.exists(log_dir):
        os.makedirs(log_dir, exist_ok=True)

    # Configure log format
    log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    formatter = logging.Formatter(log_format)

    # Set up handlers list
    handlers = []

    # Console handler (always enabled)
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    handlers.append(console_handler)

    # File handler with rotation (if enabled)
    if settings.log_rotation_enabled and settings.log_file:
        try:
            # Use TimedRotatingFileHandler for daily rotation
            file_handler = TimedRotatingFileHandler(
                filename=settings.log_file,
                when=settings.log_rotation_when,
                interval=settings.log_rotation_interval,
                backupCount=settings.log_rotation_backup_count,
                encoding='utf-8',
                delay=False,
                utc=False
            )
            file_handler.setFormatter(formatter)
            handlers.append(file_handler)

            # Log rotation configuration on startup
            print(f"Log rotation enabled: {settings.log_file}")
            print(f"  - Rotation: {settings.log_rotation_when} (interval: {settings.log_rotation_interval})")
            print(f"  - Retention: {settings.log_rotation_backup_count} backup files")

        except Exception as e:
            print(f"Warning: Failed to set up file logging: {e}")
            print("Continuing with console logging only")

    # Configure root logger
    logging.basicConfig(
        level=getattr(logging, settings.log_level.upper()),
        format=log_format,
        handlers=handlers,
        force=True  # Override any existing configuration
    )


# Configure logging before creating logger instance
configure_logging()
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """
    Application lifespan manager for startup/shutdown tasks
    """
    # Startup
    logger.info("Starting Org Archivist backend...")
    logger.info("Initializing services...")

    # Run database migrations first (before any database connections)
    from app.utils.migrations import run_startup_migrations, MigrationError

    try:
        await run_startup_migrations(
            database_url=settings.database_url,
            disable_auto_migrations=settings.disable_auto_migrations,
            max_attempts=settings.migration_retry_attempts,
            retry_delay_seconds=settings.migration_retry_delay_seconds,
            timeout_seconds=settings.migration_timeout_seconds
        )
    except MigrationError as e:
        logger.error(f"Failed to run migrations: {e}")
        logger.warning(
            "Application will continue starting, but database may be out of date. "
            "Please check database connectivity and run migrations manually."
        )
        # Continue startup even if migrations fail (allows debugging)
        # In production, you might want to exit here instead

    # Initialize database connection pool
    from app.services.database import get_database_service
    db = get_database_service()
    await db.connect()
    logger.info("Database connection pool initialized")

    # Initialize other services (lazy-loaded on first use)
    # - Vector store (Qdrant)
    # - Embedding model
    # - Claude client
    # These will be initialized when first endpoint is called

    logger.info("Backend started successfully")

    yield

    # Shutdown
    logger.info("Shutting down Org Archivist backend...")

    # Close database connections
    await db.disconnect()
    logger.info("Database connection pool closed")

    # Other resources are cleaned up automatically

    logger.info("Backend shut down complete")


# Initialize FastAPI application
app = FastAPI(
    title="Org Archivist API",
    description="RAG-powered institutional memory system for grant writing assistance",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan,
)

# Configure CORS middleware - Load allowed origins from environment config
# Get CORS origins from settings (loaded from environment variable CORS_ORIGINS)
# Supports comma-separated list for multiple domains
# Default includes development ports, can be extended for production
ALLOWED_ORIGINS = settings.get_cors_origins_list()

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configure custom middleware and exception handlers
from app.middleware import configure_middleware, configure_exception_handlers
from app.middleware.audit import AuditLoggingMiddleware

# Add audit logging middleware (Phase 5)
app.add_middleware(AuditLoggingMiddleware)

metrics_middleware = configure_middleware(app)
configure_exception_handlers(app)

# Register API routers
from app.api import query, chat, prompts, config, documents, writing_styles, auth, outputs, audit

app.include_router(auth.router)
app.include_router(query.router)
app.include_router(chat.router)
app.include_router(prompts.router)
app.include_router(config.router)
app.include_router(documents.router)
app.include_router(writing_styles.router)
app.include_router(outputs.router)
app.include_router(audit.router)


# Health check endpoint
@app.get("/api/health", tags=["System"])
async def health_check() -> dict:
    """
    Health check endpoint to verify service is running

    Returns:
        dict: Health status and service information
    """
    return {
        "status": "healthy",
        "service": "org-archivist-backend",
        "version": "0.1.0",
        "checks": {
            "api": "ok",
            # TODO: Add database check
            # TODO: Add Qdrant check
            # TODO: Add external API checks
        }
    }


# Metrics endpoint
@app.get("/api/metrics", tags=["System"])
async def get_metrics() -> dict:
    """
    Get application metrics

    Returns:
        dict: Current metrics snapshot including request counts, error rates, and timing
    """
    return metrics_middleware.get_metrics()


# Root endpoint
@app.get("/", tags=["System"])
async def root() -> dict:
    """
    Root endpoint with API information
    """
    return {
        "name": "Org Archivist API",
        "version": "0.1.0",
        "description": "RAG-powered grant writing assistance",
        "docs_url": "/docs",
        "health_url": "/api/health",
        "metrics_url": "/api/metrics",
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info",
    )
