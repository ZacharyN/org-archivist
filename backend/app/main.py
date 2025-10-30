"""
Main FastAPI application for Org Archivist backend
"""
import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """
    Application lifespan manager for startup/shutdown tasks
    """
    # Startup
    logger.info("Starting Org Archivist backend...")
    logger.info("Initializing services...")

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

# Configure CORS middleware
# TODO: Load allowed origins from environment config
ALLOWED_ORIGINS = [
    "http://localhost:8501",  # Streamlit default
    "http://localhost:3000",  # Development frontend
    "http://127.0.0.1:8501",
    "http://127.0.0.1:3000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configure custom middleware and exception handlers
from app.middleware import configure_middleware, configure_exception_handlers

metrics_middleware = configure_middleware(app)
configure_exception_handlers(app)

# Register API routers
from app.api import auth, users, query, chat, prompts, config, documents

app.include_router(auth.router)
app.include_router(users.router)
app.include_router(query.router)
app.include_router(chat.router)
app.include_router(prompts.router)
app.include_router(config.router)
app.include_router(documents.router)


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
