"""
User Management API endpoints

This module provides endpoints for user CRUD operations:
- GET /api/v1/users - List all users (Admin only)
- POST /api/v1/users - Create new user (Admin only)
- GET /api/v1/users/{user_id} - Get specific user details
- PUT /api/v1/users/{user_id} - Update user (Admin only)
- DELETE /api/v1/users/{user_id} - Deactivate user (Admin only)
"""

from typing import Optional, List
from uuid import UUID
from math import ceil
from fastapi import APIRouter, HTTPException, status, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, or_
import logging

from backend.app.models.user import (
    UserCreateRequest,
    UserUpdateRequest,
    UserResponse,
    UserListResponse,
    UserDeleteResponse,
)
from backend.app.models.common import ErrorResponse
from backend.app.services.auth_service import AuthService
from backend.app.middleware.auth import require_admin, get_current_user
from backend.app.db.session import get_db
from backend.app.db.models import User, UserRole

router = APIRouter(prefix="/api/v1/users", tags=["User Management"])
logger = logging.getLogger(__name__)


def _user_to_response(user: User) -> UserResponse:
    """
    Convert User model to UserResponse

    Args:
        user: User database model

    Returns:
        UserResponse with user information
    """
    return UserResponse(
        user_id=str(user.user_id),
        email=user.email,
        full_name=user.full_name,
        role=user.role.value,
        is_active=user.is_active,
        is_superuser=user.is_superuser,
        created_at=user.created_at,
        updated_at=user.updated_at,
    )


@router.get(
    "",
    response_model=UserListResponse,
    status_code=status.HTTP_200_OK,
    responses={
        401: {"model": ErrorResponse, "description": "Not authenticated"},
        403: {"model": ErrorResponse, "description": "Not authorized (Admin only)"},
    },
    summary="List all users",
    description="""
    Retrieve a paginated list of all users in the system.

    **Admin only** - Requires ADMIN role to access.

    Features:
    - Pagination with configurable page size
    - Filter by role (admin, editor, writer)
    - Filter by active status
    - Search by email or name
    - Returns total count and page metadata

    Use cases:
    - User administration dashboard
    - User role management
    - Account monitoring
    """,
)
async def list_users(
    page: int = Query(1, ge=1, description="Page number (1-indexed)"),
    page_size: int = Query(10, ge=1, le=100, description="Number of users per page"),
    role: Optional[UserRole] = Query(None, description="Filter by role"),
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    search: Optional[str] = Query(None, description="Search by email or name"),
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> UserListResponse:
    """
    List all users with pagination and filtering

    Args:
        page: Page number (1-indexed)
        page_size: Number of users per page (max 100)
        role: Filter by specific role
        is_active: Filter by active status
        search: Search query for email or name
        current_user: Current authenticated admin user (injected)
        db: Database session (injected)

    Returns:
        UserListResponse with paginated user list
    """
    logger.info(
        f"Admin {current_user.email} listing users (page={page}, "
        f"page_size={page_size}, role={role}, is_active={is_active}, search={search})"
    )

    # Build query with filters
    query = select(User)

    # Apply role filter
    if role is not None:
        query = query.where(User.role == role)

    # Apply active status filter
    if is_active is not None:
        query = query.where(User.is_active == is_active)

    # Apply search filter
    if search:
        search_pattern = f"%{search}%"
        query = query.where(
            or_(
                User.email.ilike(search_pattern),
                User.full_name.ilike(search_pattern)
            )
        )

    # Get total count
    count_query = select(func.count()).select_from(query.subquery())
    count_result = await db.execute(count_query)
    total = count_result.scalar() or 0

    # Calculate pagination
    offset = (page - 1) * page_size
    total_pages = ceil(total / page_size) if total > 0 else 1

    # Apply pagination and sorting
    query = query.order_by(User.created_at.desc()).offset(offset).limit(page_size)

    # Execute query
    result = await db.execute(query)
    users = result.scalars().all()

    # Convert to response models
    user_responses = [_user_to_response(user) for user in users]

    logger.info(f"Returned {len(user_responses)} users (total: {total})")

    return UserListResponse(
        users=user_responses,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


@router.post(
    "",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        400: {"model": ErrorResponse, "description": "Invalid user data"},
        401: {"model": ErrorResponse, "description": "Not authenticated"},
        403: {"model": ErrorResponse, "description": "Not authorized (Admin only)"},
        409: {"model": ErrorResponse, "description": "Email already exists"},
    },
    summary="Create new user",
    description="""
    Create a new user account.

    **Admin only** - Requires ADMIN role to access.

    Features:
    - Set initial password (hashed securely)
    - Assign role (admin, editor, writer)
    - Set active status
    - Grant superuser privileges

    The password is hashed using bcrypt before storage.
    Email addresses must be unique across all users.
    """,
)
async def create_user(
    user_data: UserCreateRequest,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> UserResponse:
    """
    Create a new user

    Args:
        user_data: User creation data including password
        current_user: Current authenticated admin user (injected)
        db: Database session (injected)

    Returns:
        UserResponse with created user information

    Raises:
        HTTPException 409: If email already exists
        HTTPException 400: If user data is invalid
    """
    logger.info(f"Admin {current_user.email} creating user: {user_data.email}")

    # Check if email already exists
    stmt = select(User).where(User.email == user_data.email)
    result = await db.execute(stmt)
    existing_user = result.scalar_one_or_none()

    if existing_user:
        logger.warning(f"Attempted to create user with existing email: {user_data.email}")
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"User with email {user_data.email} already exists",
        )

    # Hash password
    hashed_password = AuthService.hash_password(user_data.password)

    # Create new user
    new_user = User(
        email=user_data.email,
        hashed_password=hashed_password,
        full_name=user_data.full_name,
        role=user_data.role,
        is_active=user_data.is_active,
        is_superuser=user_data.is_superuser,
    )

    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)

    logger.info(
        f"User created successfully: {new_user.email} "
        f"(role: {new_user.role.value}, id: {new_user.user_id})"
    )

    return _user_to_response(new_user)


@router.get(
    "/{user_id}",
    response_model=UserResponse,
    status_code=status.HTTP_200_OK,
    responses={
        401: {"model": ErrorResponse, "description": "Not authenticated"},
        404: {"model": ErrorResponse, "description": "User not found"},
    },
    summary="Get user by ID",
    description="""
    Retrieve detailed information about a specific user.

    **Authenticated users** can view their own profile.
    **Admin users** can view any user's profile.

    Returns complete user information including role and account status.
    """,
)
async def get_user(
    user_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> UserResponse:
    """
    Get a specific user by ID

    Args:
        user_id: UUID of the user to retrieve
        current_user: Current authenticated user (injected)
        db: Database session (injected)

    Returns:
        UserResponse with user information

    Raises:
        HTTPException 404: If user not found
        HTTPException 403: If non-admin tries to view another user
    """
    logger.debug(f"User {current_user.email} requesting user details for {user_id}")

    # Query user
    stmt = select(User).where(User.user_id == user_id)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()

    if not user:
        logger.warning(f"User not found: {user_id}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with ID {user_id} not found",
        )

    # Check permissions: users can only view themselves unless they're admin
    if user.user_id != current_user.user_id and not AuthService.is_admin(current_user):
        logger.warning(
            f"Non-admin user {current_user.email} attempted to view "
            f"another user {user.email}"
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only view your own profile",
        )

    logger.debug(f"User details retrieved: {user.email}")

    return _user_to_response(user)


@router.put(
    "/{user_id}",
    response_model=UserResponse,
    status_code=status.HTTP_200_OK,
    responses={
        400: {"model": ErrorResponse, "description": "Invalid update data"},
        401: {"model": ErrorResponse, "description": "Not authenticated"},
        403: {"model": ErrorResponse, "description": "Not authorized (Admin only)"},
        404: {"model": ErrorResponse, "description": "User not found"},
        409: {"model": ErrorResponse, "description": "Email already exists"},
    },
    summary="Update user",
    description="""
    Update user information.

    **Admin only** - Requires ADMIN role to access.

    Updatable fields:
    - Email address
    - Full name
    - Password (will be hashed)
    - Role
    - Active status
    - Superuser status

    Only provided fields will be updated - omitted fields remain unchanged.
    Password changes are hashed using bcrypt.
    """,
)
async def update_user(
    user_id: UUID,
    user_data: UserUpdateRequest,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> UserResponse:
    """
    Update a user

    Args:
        user_id: UUID of the user to update
        user_data: User update data (only provided fields are updated)
        current_user: Current authenticated admin user (injected)
        db: Database session (injected)

    Returns:
        UserResponse with updated user information

    Raises:
        HTTPException 404: If user not found
        HTTPException 409: If new email already exists
        HTTPException 400: If update data is invalid
    """
    logger.info(f"Admin {current_user.email} updating user: {user_id}")

    # Query user
    stmt = select(User).where(User.user_id == user_id)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()

    if not user:
        logger.warning(f"User not found for update: {user_id}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with ID {user_id} not found",
        )

    # Track what's being updated
    updates = []

    # Update email if provided
    if user_data.email is not None and user_data.email != user.email:
        # Check if new email already exists
        stmt = select(User).where(User.email == user_data.email)
        result = await db.execute(stmt)
        existing_user = result.scalar_one_or_none()

        if existing_user:
            logger.warning(f"Attempted to update to existing email: {user_data.email}")
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Email {user_data.email} is already in use",
            )

        user.email = user_data.email
        updates.append("email")

    # Update full name if provided
    if user_data.full_name is not None:
        user.full_name = user_data.full_name
        updates.append("full_name")

    # Update password if provided
    if user_data.password is not None:
        user.hashed_password = AuthService.hash_password(user_data.password)
        updates.append("password")

    # Update role if provided
    if user_data.role is not None:
        user.role = user_data.role
        updates.append("role")

    # Update active status if provided
    if user_data.is_active is not None:
        user.is_active = user_data.is_active
        updates.append("is_active")

    # Update superuser status if provided
    if user_data.is_superuser is not None:
        user.is_superuser = user_data.is_superuser
        updates.append("is_superuser")

    # Commit changes
    await db.commit()
    await db.refresh(user)

    logger.info(
        f"User updated successfully: {user.email} "
        f"(fields: {', '.join(updates) if updates else 'none'})"
    )

    return _user_to_response(user)


@router.delete(
    "/{user_id}",
    response_model=UserDeleteResponse,
    status_code=status.HTTP_200_OK,
    responses={
        401: {"model": ErrorResponse, "description": "Not authenticated"},
        403: {"model": ErrorResponse, "description": "Not authorized (Admin only)"},
        404: {"model": ErrorResponse, "description": "User not found"},
        409: {"model": ErrorResponse, "description": "Cannot delete own account"},
    },
    summary="Deactivate user",
    description="""
    Deactivate a user account.

    **Admin only** - Requires ADMIN role to access.

    This endpoint deactivates the user rather than permanently deleting them:
    - Sets is_active to False
    - User cannot login
    - User data is preserved for audit purposes
    - All active sessions are invalidated

    **Note:** Admins cannot deactivate their own account.

    To permanently delete a user (not recommended), use database operations directly.
    """,
)
async def delete_user(
    user_id: UUID,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> UserDeleteResponse:
    """
    Deactivate a user (soft delete)

    Args:
        user_id: UUID of the user to deactivate
        current_user: Current authenticated admin user (injected)
        db: Database session (injected)

    Returns:
        UserDeleteResponse confirming deactivation

    Raises:
        HTTPException 404: If user not found
        HTTPException 409: If trying to delete own account
    """
    logger.info(f"Admin {current_user.email} deactivating user: {user_id}")

    # Prevent self-deletion
    if user_id == current_user.user_id:
        logger.warning(f"Admin {current_user.email} attempted to delete own account")
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="You cannot deactivate your own account",
        )

    # Query user
    stmt = select(User).where(User.user_id == user_id)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()

    if not user:
        logger.warning(f"User not found for deletion: {user_id}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with ID {user_id} not found",
        )

    # Deactivate user
    user.is_active = False
    await db.commit()

    # Invalidate all user sessions
    from backend.app.services.session_service import SessionService
    session_count = await SessionService.expire_all_user_sessions(db, user_id)

    logger.info(
        f"User deactivated successfully: {user.email} "
        f"({session_count} sessions invalidated)"
    )

    return UserDeleteResponse(
        message="User account deactivated successfully",
        user_id=str(user.user_id),
        email=user.email,
    )
