"""
Authentication API endpoints

This module provides endpoints for user authentication and session management:
- POST /api/v1/auth/login - User login (email + password)
- POST /api/v1/auth/logout - User logout (invalidate session)
- GET /api/v1/auth/me - Get current user information
- POST /api/v1/auth/refresh - Refresh access token using refresh token
"""

from typing import Optional
from fastapi import APIRouter, HTTPException, status, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession
import logging

from backend.app.models.auth import (
    LoginRequest,
    LoginResponse,
    RefreshRequest,
    RefreshResponse,
    UserInfoResponse,
    LogoutResponse,
)
from backend.app.models.common import ErrorResponse
from backend.app.services.auth_service import AuthService
from backend.app.services.session_service import SessionService
from backend.app.middleware.auth import get_current_user, get_current_active_user
from backend.app.db.session import get_db
from backend.app.db.models import User

router = APIRouter(prefix="/api/v1/auth", tags=["Authentication"])
logger = logging.getLogger(__name__)


def _get_client_info(request: Request) -> tuple[Optional[str], Optional[str]]:
    """
    Extract client IP address and user agent from request

    Args:
        request: FastAPI request object

    Returns:
        Tuple of (ip_address, user_agent)
    """
    # Get IP address (handle X-Forwarded-For for proxies)
    ip_address = request.client.host if request.client else None
    if forwarded := request.headers.get("X-Forwarded-For"):
        ip_address = forwarded.split(",")[0].strip()

    # Get user agent
    user_agent = request.headers.get("User-Agent")

    return ip_address, user_agent


@router.post(
    "/login",
    response_model=LoginResponse,
    status_code=status.HTTP_200_OK,
    responses={
        401: {
            "model": ErrorResponse,
            "description": "Invalid credentials or inactive account"
        },
        422: {
            "model": ErrorResponse,
            "description": "Invalid request format"
        },
    },
    summary="User login",
    description="""
    Authenticate a user with email and password.

    Process:
    1. Validates email and password
    2. Checks if user account is active
    3. Creates a new session with JWT tokens
    4. Returns user information and authentication tokens

    The access token should be included in subsequent requests as:
    `Authorization: Bearer <access_token>`

    Access tokens expire based on session timeout configuration.
    Use the refresh token to obtain new access tokens without re-authenticating.
    """,
)
async def login(
    login_data: LoginRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> LoginResponse:
    """
    Login endpoint - authenticate user and create session

    Args:
        login_data: Login credentials (email and password)
        request: FastAPI request object (for extracting client info)
        db: Database session (injected)

    Returns:
        LoginResponse with user info and authentication tokens

    Raises:
        HTTPException 401: If credentials are invalid or account is inactive
    """
    # Get client information for session tracking
    ip_address, user_agent = _get_client_info(request)

    # Attempt login
    result = await AuthService.login(
        db=db,
        email=login_data.email,
        password=login_data.password,
        ip_address=ip_address,
        user_agent=user_agent,
    )

    if not result:
        logger.warning(f"Failed login attempt for email: {login_data.email}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password, or account is inactive",
            headers={"WWW-Authenticate": "Bearer"},
        )

    logger.info(f"Successful login: {login_data.email} (role: {result['role']})")

    return LoginResponse(**result)


@router.post(
    "/logout",
    response_model=LogoutResponse,
    status_code=status.HTTP_200_OK,
    responses={
        401: {
            "model": ErrorResponse,
            "description": "Invalid or expired token"
        },
    },
    summary="User logout",
    description="""
    Logout the current user by invalidating their session.

    This endpoint:
    1. Validates the provided access token
    2. Deletes the session from the database
    3. Invalidates both access and refresh tokens

    After logout, the tokens can no longer be used for authentication.
    The user must login again to obtain new tokens.
    """,
)
async def logout(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> LogoutResponse:
    """
    Logout endpoint - invalidate current session

    Args:
        current_user: Current authenticated user (injected by middleware)
        db: Database session (injected)

    Returns:
        LogoutResponse confirming successful logout
    """
    # Get all user sessions and expire them
    count = await SessionService.expire_all_user_sessions(db=db, user_id=current_user.user_id)

    logger.info(f"User logged out: {current_user.email} ({count} sessions expired)")

    return LogoutResponse(
        message=f"Successfully logged out ({count} sessions terminated)"
    )


@router.get(
    "/me",
    response_model=UserInfoResponse,
    status_code=status.HTTP_200_OK,
    responses={
        401: {
            "model": ErrorResponse,
            "description": "Invalid or expired token"
        },
    },
    summary="Get current user information",
    description="""
    Retrieve information about the currently authenticated user.

    Returns:
    - User ID, email, and full name
    - Role and permissions
    - Account status
    - Creation timestamp

    This endpoint requires a valid access token in the Authorization header.
    """,
)
async def get_current_user_info(
    current_user: User = Depends(get_current_active_user),
) -> UserInfoResponse:
    """
    Get current user information endpoint

    Args:
        current_user: Current authenticated user (injected by middleware)

    Returns:
        UserInfoResponse with current user's profile information
    """
    logger.debug(f"User info requested: {current_user.email}")

    return UserInfoResponse(
        user_id=str(current_user.user_id),
        email=current_user.email,
        full_name=current_user.full_name,
        role=current_user.role.value,
        is_active=current_user.is_active,
        is_superuser=current_user.is_superuser,
        created_at=current_user.created_at,
    )


@router.post(
    "/refresh",
    response_model=RefreshResponse,
    status_code=status.HTTP_200_OK,
    responses={
        401: {
            "model": ErrorResponse,
            "description": "Invalid or expired refresh token"
        },
    },
    summary="Refresh access token",
    description="""
    Obtain a new access token using a refresh token.

    Process:
    1. Validates the provided refresh token
    2. Deletes the old session (token rotation for security)
    3. Creates a new session with fresh tokens
    4. Returns new access and refresh tokens

    Token Rotation:
    - Both access and refresh tokens are rotated on each refresh
    - Old tokens are immediately invalidated
    - This prevents token reuse and improves security

    Use this endpoint when:
    - Access token has expired
    - Approaching token expiration
    - Implementing automatic token refresh in client apps
    """,
)
async def refresh_token(
    refresh_data: RefreshRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> RefreshResponse:
    """
    Refresh token endpoint - obtain new tokens using refresh token

    Args:
        refresh_data: Refresh token request
        request: FastAPI request object (for extracting client info)
        db: Database session (injected)

    Returns:
        RefreshResponse with new access and refresh tokens

    Raises:
        HTTPException 401: If refresh token is invalid or expired
    """
    # Get client information for new session
    ip_address, user_agent = _get_client_info(request)

    # Attempt to refresh session
    new_session = await SessionService.refresh_session(
        db=db,
        refresh_token=refresh_data.refresh_token,
        ip_address=ip_address,
        user_agent=user_agent,
    )

    if not new_session:
        logger.warning("Failed token refresh attempt")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token. Please login again.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    logger.info(f"Token refreshed for user: {new_session.user_id}")

    return RefreshResponse(
        access_token=new_session.access_token,
        refresh_token=new_session.refresh_token,
        expires_at=new_session.expires_at.isoformat(),
        token_type="bearer",
    )
