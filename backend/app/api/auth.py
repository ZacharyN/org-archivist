"""
Authentication API endpoints

This module provides API endpoints for user authentication and session management:
- POST /api/auth/register - Create new user account
- POST /api/auth/login - Authenticate and create session
- POST /api/auth/logout - Invalidate session
- GET /api/auth/session - Validate current session
- GET /api/auth/me - Get current user details
"""

import logging
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, HTTPException, Header, status, Depends
from fastapi.responses import JSONResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy import select

from ..models.auth import (
    RegisterRequest,
    LoginRequest,
    LoginResponse,
    LogoutResponse,
    SessionResponse,
    UserResponse,
)
from ..models.common import ErrorResponse
from ..services.auth_service import AuthService
from ..db.models import User, UserRole
from ..config import get_settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/auth", tags=["Authentication"])
security = HTTPBearer()

# Lazy initialization of database engine
_engine = None
_async_session_maker = None


def _get_engine():
    """Lazy initialize database engine"""
    global _engine, _async_session_maker
    if _engine is None:
        settings = get_settings()
        # Convert database URL to use async driver (asyncpg)
        database_url = settings.database_url.replace("postgresql://", "postgresql+asyncpg://")
        _engine = create_async_engine(database_url)
        _async_session_maker = async_sessionmaker(_engine, class_=AsyncSession, expire_on_commit=False)
    return _async_session_maker


async def get_db():
    """Dependency for getting async database session"""
    session_maker = _get_engine()
    async with session_maker() as session:
        try:
            yield session
        finally:
            await session.close()


async def get_current_user_from_token(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db)
) -> User:
    """
    Dependency for getting the current authenticated user from token

    Args:
        credentials: HTTP Authorization credentials with Bearer token
        db: Database session

    Returns:
        User object if authenticated

    Raises:
        HTTPException: If authentication fails
    """
    token = credentials.credentials
    user = await AuthService.validate_session(db, token)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired session",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return user


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        400: {"model": ErrorResponse, "description": "Invalid request or user already exists"},
        422: {"model": ErrorResponse, "description": "Validation error"},
    },
    summary="Register new user",
    description="""
    Create a new user account.

    Requirements:
    - Email must be unique
    - Password must be at least 8 characters
    - Role must be one of: admin, editor, writer

    Returns the created user profile (without password).
    """,
)
async def register(
    request: RegisterRequest,
    db: AsyncSession = Depends(get_db)
) -> UserResponse:
    """
    Register a new user account

    Args:
        request: Registration request with email, password, name, and role
        db: Database session

    Returns:
        UserResponse with created user profile

    Raises:
        HTTPException: If user already exists or validation fails
    """
    try:
        logger.info(f"Registration attempt for email: {request.email}")

        # Check if user already exists
        stmt = select(User).where(User.email == request.email)
        result = await db.execute(stmt)
        existing_user = result.scalar_one_or_none()

        if existing_user:
            logger.warning(f"Registration failed: Email already exists: {request.email}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered"
            )

        # Hash password
        hashed_password = AuthService.hash_password(request.password)

        # Create user
        new_user = User(
            email=request.email,
            hashed_password=hashed_password,
            full_name=request.full_name,
            role=UserRole(request.role),
            is_active=True,
            is_superuser=False
        )

        db.add(new_user)
        await db.commit()
        await db.refresh(new_user)

        logger.info(f"User registered successfully: {new_user.user_id}")

        return UserResponse.model_validate(new_user)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Registration failed: {str(e)}", exc_info=True)
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create user account"
        )


@router.post(
    "/login",
    response_model=LoginResponse,
    status_code=status.HTTP_200_OK,
    responses={
        401: {"model": ErrorResponse, "description": "Invalid credentials"},
        422: {"model": ErrorResponse, "description": "Validation error"},
    },
    summary="User login",
    description="""
    Authenticate user and create a new session.

    Returns access token, refresh token, and user profile on successful authentication.
    Tokens should be included in subsequent requests using the Authorization header:
    `Authorization: Bearer <access_token>`
    """,
)
async def login(
    request: LoginRequest,
    db: AsyncSession = Depends(get_db)
) -> LoginResponse:
    """
    Authenticate user and create session

    Args:
        request: Login request with email and password
        db: Database session

    Returns:
        LoginResponse with tokens and user profile

    Raises:
        HTTPException: If authentication fails
    """
    try:
        logger.info(f"Login attempt for email: {request.email}")

        # Authenticate and create session
        auth_result = await AuthService.login(
            db=db,
            email=request.email,
            password=request.password
        )

        if not auth_result:
            logger.warning(f"Login failed: Invalid credentials for {request.email}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password"
            )

        # Get user details
        user_id = UUID(auth_result["user_id"])
        stmt = select(User).where(User.user_id == user_id)
        result = await db.execute(stmt)
        user = result.scalar_one()

        logger.info(f"Login successful for user: {user_id}")

        return LoginResponse(
            access_token=auth_result["access_token"],
            refresh_token=auth_result["refresh_token"],
            token_type="bearer",
            expires_at=auth_result["expires_at"],
            user=UserResponse.model_validate(user)
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Login failed: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Login failed"
        )


@router.post(
    "/logout",
    response_model=LogoutResponse,
    status_code=status.HTTP_200_OK,
    responses={
        401: {"model": ErrorResponse, "description": "Invalid or expired session"},
    },
    summary="User logout",
    description="""
    Invalidate the current user session.

    Requires valid authentication token in the Authorization header.
    """,
)
async def logout(
    current_user: User = Depends(get_current_user_from_token),
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db)
) -> LogoutResponse:
    """
    Logout user and invalidate session

    Args:
        current_user: Current authenticated user (from dependency)
        credentials: Authorization credentials
        db: Database session

    Returns:
        LogoutResponse with success status
    """
    try:
        token = credentials.credentials
        logger.info(f"Logout attempt for user: {current_user.user_id}")

        success = await AuthService.logout(db, token)

        if not success:
            logger.warning(f"Logout failed: Session not found for user {current_user.user_id}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Session not found"
            )

        logger.info(f"Logout successful for user: {current_user.user_id}")

        return LogoutResponse(
            success=True,
            message="Successfully logged out"
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Logout failed: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Logout failed"
        )


@router.get(
    "/session",
    response_model=SessionResponse,
    status_code=status.HTTP_200_OK,
    responses={
        401: {"model": ErrorResponse, "description": "Invalid or expired session"},
    },
    summary="Validate session",
    description="""
    Validate the current session and return user information.

    Requires valid authentication token in the Authorization header.
    Returns user profile if session is valid.
    """,
)
async def validate_session(
    current_user: User = Depends(get_current_user_from_token)
) -> SessionResponse:
    """
    Validate current session

    Args:
        current_user: Current authenticated user (from dependency)

    Returns:
        SessionResponse with user profile
    """
    logger.info(f"Session validation for user: {current_user.user_id}")

    return SessionResponse(
        valid=True,
        user=UserResponse.model_validate(current_user),
        message="Session is valid"
    )


@router.get(
    "/me",
    response_model=UserResponse,
    status_code=status.HTTP_200_OK,
    responses={
        401: {"model": ErrorResponse, "description": "Invalid or expired session"},
    },
    summary="Get current user",
    description="""
    Get the current authenticated user's profile information.

    Requires valid authentication token in the Authorization header.
    """,
)
async def get_current_user(
    current_user: User = Depends(get_current_user_from_token)
) -> UserResponse:
    """
    Get current user profile

    Args:
        current_user: Current authenticated user (from dependency)

    Returns:
        UserResponse with user profile
    """
    logger.info(f"Profile request for user: {current_user.user_id}")

    return UserResponse.model_validate(current_user)
