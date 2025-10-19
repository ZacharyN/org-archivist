"""
Custom middleware for logging, error handling, and request timing.

This module provides:
- Request/response logging
- Request timing and metrics
- Request ID tracking
- Comprehensive error handling
"""

import logging
import time
import uuid
from typing import Callable

from fastapi import Request, Response, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """
    Middleware for logging all HTTP requests and responses.
    Includes request ID tracking and timing metrics.
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Generate unique request ID
        request_id = str(uuid.uuid4())

        # Add request ID to request state for use in handlers
        request.state.request_id = request_id

        # Log incoming request
        logger.info(
            f"Request [{request_id}] started: {request.method} {request.url.path}"
        )

        # Record start time
        start_time = time.time()

        try:
            # Process request
            response = await call_next(request)

            # Calculate request duration
            duration_ms = (time.time() - start_time) * 1000

            # Add request ID and timing to response headers
            response.headers["X-Request-ID"] = request_id
            response.headers["X-Process-Time"] = f"{duration_ms:.2f}ms"

            # Log response
            logger.info(
                f"Request [{request_id}] completed: "
                f"status={response.status_code} "
                f"duration={duration_ms:.2f}ms"
            )

            return response

        except Exception as exc:
            # Calculate duration even for failed requests
            duration_ms = (time.time() - start_time) * 1000

            # Log error
            logger.error(
                f"Request [{request_id}] failed: "
                f"error={str(exc)} "
                f"duration={duration_ms:.2f}ms",
                exc_info=True
            )

            # Return error response
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={
                    "error": "Internal server error",
                    "request_id": request_id,
                    "detail": str(exc) if logger.isEnabledFor(logging.DEBUG) else None
                },
                headers={
                    "X-Request-ID": request_id,
                    "X-Process-Time": f"{duration_ms:.2f}ms"
                }
            )


class MetricsMiddleware(BaseHTTPMiddleware):
    """
    Middleware for collecting request metrics.
    Tracks request counts, response times, and error rates.
    """

    def __init__(self, app: ASGIApp):
        super().__init__(app)
        self.request_count = 0
        self.error_count = 0
        self.total_duration = 0.0

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Increment request counter
        self.request_count += 1

        # Record start time
        start_time = time.time()

        # Process request
        response = await call_next(request)

        # Calculate duration
        duration = time.time() - start_time
        self.total_duration += duration

        # Track errors (4xx and 5xx status codes)
        if response.status_code >= 400:
            self.error_count += 1

        # Add metrics to response headers (for monitoring)
        response.headers["X-Request-Count"] = str(self.request_count)
        response.headers["X-Error-Rate"] = f"{(self.error_count / self.request_count * 100):.2f}%"

        if self.request_count > 0:
            avg_duration_ms = (self.total_duration / self.request_count) * 1000
            response.headers["X-Avg-Response-Time"] = f"{avg_duration_ms:.2f}ms"

        return response

    def get_metrics(self) -> dict:
        """Get current metrics snapshot."""
        return {
            "total_requests": self.request_count,
            "total_errors": self.error_count,
            "error_rate": f"{(self.error_count / max(self.request_count, 1) * 100):.2f}%",
            "avg_response_time_ms": f"{(self.total_duration / max(self.request_count, 1) * 1000):.2f}",
            "total_duration_seconds": f"{self.total_duration:.2f}"
        }


# Exception handlers for common HTTP errors

async def validation_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Handle validation errors (422 Unprocessable Entity)."""
    request_id = getattr(request.state, "request_id", "unknown")

    logger.warning(
        f"Validation error [{request_id}]: {str(exc)}"
    )

    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "error": "Validation error",
            "request_id": request_id,
            "detail": str(exc)
        },
        headers={"X-Request-ID": request_id}
    )


async def not_found_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Handle 404 Not Found errors."""
    request_id = getattr(request.state, "request_id", "unknown")

    logger.warning(
        f"Not found [{request_id}]: {request.url.path}"
    )

    return JSONResponse(
        status_code=status.HTTP_404_NOT_FOUND,
        content={
            "error": "Resource not found",
            "request_id": request_id,
            "path": str(request.url.path)
        },
        headers={"X-Request-ID": request_id}
    )


async def method_not_allowed_handler(request: Request, exc: Exception) -> JSONResponse:
    """Handle 405 Method Not Allowed errors."""
    request_id = getattr(request.state, "request_id", "unknown")

    logger.warning(
        f"Method not allowed [{request_id}]: {request.method} {request.url.path}"
    )

    return JSONResponse(
        status_code=status.HTTP_405_METHOD_NOT_ALLOWED,
        content={
            "error": "Method not allowed",
            "request_id": request_id,
            "method": request.method,
            "path": str(request.url.path)
        },
        headers={"X-Request-ID": request_id}
    )


async def internal_server_error_handler(request: Request, exc: Exception) -> JSONResponse:
    """Handle 500 Internal Server Error."""
    request_id = getattr(request.state, "request_id", "unknown")

    logger.error(
        f"Internal server error [{request_id}]: {str(exc)}",
        exc_info=True
    )

    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": "Internal server error",
            "request_id": request_id,
            "detail": str(exc) if logger.isEnabledFor(logging.DEBUG) else "An unexpected error occurred"
        },
        headers={"X-Request-ID": request_id}
    )


async def rate_limit_exceeded_handler(request: Request, exc: Exception) -> JSONResponse:
    """Handle 429 Rate Limit Exceeded errors."""
    request_id = getattr(request.state, "request_id", "unknown")

    logger.warning(
        f"Rate limit exceeded [{request_id}]: {request.client.host if request.client else 'unknown'}"
    )

    return JSONResponse(
        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        content={
            "error": "Rate limit exceeded",
            "request_id": request_id,
            "detail": "Too many requests. Please try again later."
        },
        headers={
            "X-Request-ID": request_id,
            "Retry-After": "60"  # Suggest retry after 60 seconds
        }
    )


def configure_middleware(app):
    """
    Configure all middleware for the FastAPI application.

    Args:
        app: FastAPI application instance

    Returns:
        MetricsMiddleware instance for external metrics access
    """
    # Add middleware (order matters - they execute in reverse order)
    metrics_middleware = MetricsMiddleware(app)
    app.add_middleware(MetricsMiddleware)
    app.add_middleware(RequestLoggingMiddleware)

    logger.info("Middleware configured successfully")

    return metrics_middleware


def configure_exception_handlers(app):
    """
    Configure exception handlers for the FastAPI application.

    Args:
        app: FastAPI application instance
    """
    from fastapi.exceptions import RequestValidationError
    from starlette.exceptions import HTTPException

    # Register exception handlers
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(404, not_found_exception_handler)
    app.add_exception_handler(405, method_not_allowed_handler)
    app.add_exception_handler(500, internal_server_error_handler)
    app.add_exception_handler(429, rate_limit_exceeded_handler)

    # Generic HTTP exception handler
    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException):
        request_id = getattr(request.state, "request_id", "unknown")

        logger.warning(
            f"HTTP exception [{request_id}]: status={exc.status_code} detail={exc.detail}"
        )

        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": exc.detail,
                "request_id": request_id,
                "status_code": exc.status_code
            },
            headers={"X-Request-ID": request_id}
        )

    logger.info("Exception handlers configured successfully")
