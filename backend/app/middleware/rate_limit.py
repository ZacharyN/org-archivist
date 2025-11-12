"""
Rate Limiting Middleware for FastAPI

Implements rate limiting to protect against:
- Brute force login attempts
- API abuse and overuse
- Accidental infinite loops in client code
- Cost inflation from excessive Claude API calls

Features:
- IP-based rate limiting for unauthenticated endpoints
- User-based rate limiting for authenticated endpoints
- Different limits for different endpoint categories
- Configurable rate limits via settings
- Clear error messages with retry-after headers
"""

import logging
import time
import json
from typing import Callable, Dict, Tuple, Optional
from datetime import datetime, timedelta

from fastapi import Request, Response, HTTPException, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp
from aiolimiter import AsyncLimiter

from app.config import get_settings

logger = logging.getLogger(__name__)


class RateLimitExceeded(HTTPException):
    """Custom exception for rate limit exceeded"""

    def __init__(self, retry_after: int = 60):
        super().__init__(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Rate limit exceeded. Please try again later.",
            headers={"Retry-After": str(retry_after)}
        )


class RateLimitConfig:
    """
    Configuration for rate limits per endpoint category

    Rate limits are defined as (max_requests, time_window_seconds)
    """

    # Authentication endpoints (per IP)
    LOGIN_LIMIT = (5, 60)  # 5 requests per minute per IP
    REGISTER_LIMIT = (3, 3600)  # 3 requests per hour per IP
    REFRESH_LIMIT = (10, 60)  # 10 requests per minute per IP

    # Generation endpoints (per user)
    GENERATION_LIMIT = (10, 60)  # 10 requests per minute per user
    QUERY_LIMIT = (20, 60)  # 20 requests per minute per user

    # Document operations (per user)
    UPLOAD_LIMIT = (10, 60)  # 10 uploads per minute per user
    DELETE_LIMIT = (20, 60)  # 20 deletes per minute per user

    # Read endpoints (per user)
    READ_LIMIT = (100, 60)  # 100 requests per minute per user

    # Health/metrics endpoints (per IP)
    HEALTH_LIMIT = (60, 60)  # 60 requests per minute per IP

    # Default fallback for unclassified endpoints (per user)
    DEFAULT_LIMIT = (30, 60)  # 30 requests per minute


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Middleware for rate limiting API requests

    Implements different rate limits based on:
    - Endpoint path/pattern
    - User authentication status (IP vs User ID)
    - HTTP method
    """

    def __init__(self, app: ASGIApp):
        super().__init__(app)
        self.limiters: Dict[str, AsyncLimiter] = {}
        self.settings = get_settings()

        # Track when limiters were created for cleanup
        self.limiter_created_at: Dict[str, datetime] = {}

        # Cleanup interval (remove stale limiters after 1 hour)
        self.cleanup_interval = timedelta(hours=1)
        self.last_cleanup = datetime.now()

        logger.info("Rate limiting middleware initialized")

    def _get_client_identifier(self, request: Request) -> Tuple[str, str]:
        """
        Get client identifier for rate limiting

        Returns:
            Tuple of (identifier_type, identifier_value)
            - For authenticated requests: ("user", user_id)
            - For unauthenticated requests: ("ip", ip_address)
        """
        # Check if user is authenticated (will be set by auth middleware)
        user = getattr(request.state, "user", None)

        if user and hasattr(user, "user_id"):
            # Use user ID for authenticated requests
            return ("user", str(user.user_id))

        # Fall back to IP address for unauthenticated requests
        # Handle proxy headers (X-Forwarded-For, X-Real-IP)
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            # Take first IP if multiple proxies
            ip = forwarded.split(",")[0].strip()
        else:
            ip = request.headers.get("X-Real-IP") or \
                 (request.client.host if request.client else "unknown")

        return ("ip", ip)

    def _get_rate_limit_config(self, request: Request) -> Tuple[int, int]:
        """
        Get rate limit configuration for the request

        Returns:
            Tuple of (max_requests, time_window_seconds)
        """
        path = request.url.path
        method = request.method

        # Authentication endpoints (stricter limits)
        if path.startswith("/api/auth/login"):
            return RateLimitConfig.LOGIN_LIMIT
        elif path.startswith("/api/auth/register"):
            return RateLimitConfig.REGISTER_LIMIT
        elif path.startswith("/api/auth/refresh"):
            return RateLimitConfig.REFRESH_LIMIT

        # Generation endpoints (moderate limits, expensive operations)
        elif path.startswith("/api/query") or path.startswith("/api/chat"):
            return RateLimitConfig.GENERATION_LIMIT

        # Document operations
        elif path.startswith("/api/documents"):
            if method == "POST" and "upload" in path:
                return RateLimitConfig.UPLOAD_LIMIT
            elif method == "DELETE":
                return RateLimitConfig.DELETE_LIMIT
            else:
                return RateLimitConfig.READ_LIMIT

        # Writing styles, prompts, outputs (read-heavy)
        elif any(path.startswith(p) for p in [
            "/api/writing-styles",
            "/api/prompts",
            "/api/outputs"
        ]):
            if method in ["GET", "HEAD"]:
                return RateLimitConfig.READ_LIMIT
            else:
                return RateLimitConfig.QUERY_LIMIT

        # Health and metrics (very permissive)
        elif path.startswith("/api/health") or path.startswith("/api/metrics"):
            return RateLimitConfig.HEALTH_LIMIT

        # Default rate limit for other endpoints
        else:
            return RateLimitConfig.DEFAULT_LIMIT

    def _get_limiter_key(
        self,
        identifier_type: str,
        identifier_value: str,
        max_requests: int,
        time_window: int
    ) -> str:
        """Generate unique key for rate limiter"""
        return f"{identifier_type}:{identifier_value}:{max_requests}:{time_window}"

    async def _get_or_create_limiter(
        self,
        identifier_type: str,
        identifier_value: str,
        max_requests: int,
        time_window: int
    ) -> AsyncLimiter:
        """
        Get existing limiter or create new one for client

        Args:
            identifier_type: Type of identifier (user/ip)
            identifier_value: Client identifier
            max_requests: Maximum requests allowed
            time_window: Time window in seconds

        Returns:
            AsyncLimiter instance
        """
        key = self._get_limiter_key(
            identifier_type,
            identifier_value,
            max_requests,
            time_window
        )

        # Create new limiter if doesn't exist
        if key not in self.limiters:
            self.limiters[key] = AsyncLimiter(
                max_rate=max_requests,
                time_period=time_window
            )
            self.limiter_created_at[key] = datetime.now()

            logger.debug(
                f"Created rate limiter for {identifier_type}:{identifier_value} "
                f"({max_requests} requests per {time_window}s)"
            )

        return self.limiters[key]

    def _cleanup_stale_limiters(self):
        """Remove limiters that haven't been used recently"""
        now = datetime.now()

        # Only cleanup periodically
        if now - self.last_cleanup < self.cleanup_interval:
            return

        # Find stale limiters
        stale_keys = []
        for key, created_at in self.limiter_created_at.items():
            if now - created_at > self.cleanup_interval:
                stale_keys.append(key)

        # Remove stale limiters
        for key in stale_keys:
            del self.limiters[key]
            del self.limiter_created_at[key]

        if stale_keys:
            logger.info(f"Cleaned up {len(stale_keys)} stale rate limiters")

        self.last_cleanup = now

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Process request with rate limiting

        Args:
            request: Incoming request
            call_next: Next middleware/handler

        Returns:
            Response from handler or 429 if rate limited
        """
        # Check if rate limiting is enabled
        if not self.settings.enable_rate_limiting:
            return await call_next(request)

        # Skip rate limiting for certain paths (docs, openapi)
        if request.url.path in ["/", "/docs", "/redoc", "/openapi.json"]:
            return await call_next(request)

        # Get client identifier
        identifier_type, identifier_value = self._get_client_identifier(request)

        # Get rate limit config for this endpoint
        max_requests, time_window = self._get_rate_limit_config(request)

        # Get or create limiter for this client
        limiter = await self._get_or_create_limiter(
            identifier_type,
            identifier_value,
            max_requests,
            time_window
        )

        # Check rate limit
        try:
            async with limiter:
                # Request allowed - proceed
                response = await call_next(request)

                # Add rate limit headers
                response.headers["X-RateLimit-Limit"] = str(max_requests)
                response.headers["X-RateLimit-Window"] = f"{time_window}s"
                response.headers["X-RateLimit-Type"] = identifier_type

                return response

        except Exception as e:
            # Rate limit exceeded
            logger.warning(
                f"Rate limit exceeded for {identifier_type}:{identifier_value} "
                f"on {request.method} {request.url.path}"
            )

            # Calculate retry-after (time until next request allowed)
            retry_after = time_window

            # Return 429 response with proper JSON formatting
            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={
                    "error": "Rate limit exceeded",
                    "detail": f"Maximum {max_requests} requests per {time_window} seconds. "
                              f"Please try again in {retry_after} seconds.",
                    "retry_after": retry_after,
                    "limit": max_requests,
                    "window": f"{time_window}s"
                },
                headers={
                    "Retry-After": str(retry_after),
                    "X-RateLimit-Limit": str(max_requests),
                    "X-RateLimit-Window": f"{time_window}s",
                    "X-RateLimit-Type": identifier_type
                }
            )

        finally:
            # Periodic cleanup of stale limiters
            self._cleanup_stale_limiters()


def configure_rate_limiting(app):
    """
    Configure rate limiting middleware for the application

    Args:
        app: FastAPI application instance
    """
    # Add rate limiting middleware
    app.add_middleware(RateLimitMiddleware)

    logger.info("Rate limiting configured successfully")
