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

    # TODO: Initialize database connections
    # TODO: Initialize Qdrant client
    # TODO: Load embedding model
    # TODO: Initialize Claude client

    logger.info("Backend started successfully")

    yield

    # Shutdown
    logger.info("Shutting down Org Archivist backend...")

    # TODO: Close database connections
    # TODO: Close Qdrant client
    # TODO: Cleanup resources

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

# Register API routers
from app.api import query, chat, prompts

app.include_router(query.router)
app.include_router(chat.router)
app.include_router(prompts.router)


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
    }


# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request, exc: Exception) -> JSONResponse:
    """
    Global exception handler for uncaught errors
    """
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "detail": str(exc) if app.debug else "An unexpected error occurred",
        },
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info",
    )
