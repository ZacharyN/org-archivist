"""
Authentication and Authorization Middleware for FastAPI

Provides FastAPI dependencies for:
- Token extraction and validation
- User authentication
- Role-based access control (RBAC)
- Permission checking

Usage:
    from backend.app.middleware.auth import get_current_user, require_admin

    @app.get("/protected")
    async def protected_route(user: User = Depends(get_current_user)):
        return {"user": user.email}

    @app.get("/admin-only")
    async def admin_route(user: User = Depends(require_admin)):
        return {"message": "Admin access granted"}
"""

from typing import Optional
import logging

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.models import User, UserRole
from backend.app.services.session_service import SessionService
from backend.app.db.session import get_db

logger = logging.getLogger(__name__)

# OAuth2 scheme for token extraction
# This will extract the token from the Authorization header: "Bearer <token>"
oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl="/api/v1/auth/login",
    scheme_name="JWT",
    auto_error=True
)


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db)
) -> User:
    """
    FastAPI dependency to get the current authenticated user from a JWT token

    Validates the token and returns the associated user.
    Raises 401 if token is invalid or session is expired.

    Args:
        token: JWT access token from Authorization header
        db: Database session

    Returns:
        User object if authentication successful

    Raises:
        HTTPException: 401 if token is invalid or expired
    """
    # Validate session and get user
    user = await SessionService.validate_session(
        db=db,
        access_token=token,
        refresh_activity=True  # Extend session on activity
    )

    if not user:
        logger.warning(f"Authentication failed: invalid or expired token")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials. Token may be invalid or expired.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    logger.debug(f"User authenticated: {user.email} (role: {user.role.value})")
    return user


async def get_current_active_user(
    current_user: User = Depends(get_current_user)
) -> User:
    """
    FastAPI dependency to ensure the current user is active

    Checks if the authenticated user's account is active.
    Raises 403 if user is inactive.

    Args:
        current_user: Current authenticated user

    Returns:
        User object if active

    Raises:
        HTTPException: 403 if user account is inactive
    """
    if not current_user.is_active:
        logger.warning(f"Inactive user attempted access: {current_user.email}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Your account is inactive. Please contact an administrator."
        )

    return current_user


def require_role(required_role: UserRole):
    """
    Factory function to create a dependency that requires a specific role or higher

    Role hierarchy: ADMIN > EDITOR > WRITER
    - ADMIN can access ADMIN, EDITOR, and WRITER endpoints
    - EDITOR can access EDITOR and WRITER endpoints
    - WRITER can only access WRITER endpoints

    Args:
        required_role: The minimum role required

    Returns:
        FastAPI dependency function that checks user role

    Example:
        @app.get("/editor-content")
        async def editor_content(user: User = Depends(require_role(UserRole.EDITOR))):
            return {"message": "Editor access granted"}
    """
    async def role_checker(current_user: User = Depends(get_current_active_user)) -> User:
        """
        Check if the current user has the required role or higher privileges

        Args:
            current_user: Current authenticated and active user

        Returns:
            User object if authorized

        Raises:
            HTTPException: 403 if user lacks required role
        """
        # Role hierarchy mapping
        role_hierarchy = {
            UserRole.WRITER: 1,
            UserRole.EDITOR: 2,
            UserRole.ADMIN: 3
        }

        user_level = role_hierarchy.get(current_user.role, 0)
        required_level = role_hierarchy.get(required_role, 0)

        # Superusers bypass role checks
        if current_user.is_superuser:
            logger.debug(f"Superuser access granted: {current_user.email}")
            return current_user

        # Check role hierarchy
        if user_level < required_level:
            logger.warning(
                f"Access denied: {current_user.email} (role: {current_user.role.value}) "
                f"attempted to access {required_role.value} endpoint"
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied. This endpoint requires {required_role.value} role or higher. "
                       f"Your role: {current_user.role.value}"
            )

        logger.debug(
            f"Role check passed: {current_user.email} (role: {current_user.role.value}) "
            f"accessing {required_role.value} endpoint"
        )
        return current_user

    return role_checker


# Convenience dependencies for common role requirements
# These can be used directly in route definitions

async def require_writer(
    current_user: User = Depends(require_role(UserRole.WRITER))
) -> User:
    """
    FastAPI dependency to require WRITER role or higher

    This is the minimum role for authenticated users who can create content.

    Usage:
        @app.post("/content")
        async def create_content(user: User = Depends(require_writer)):
            return {"message": "Content creation allowed"}
    """
    return current_user


async def require_editor(
    current_user: User = Depends(require_role(UserRole.EDITOR))
) -> User:
    """
    FastAPI dependency to require EDITOR role or higher

    Editors can review and edit content created by writers.

    Usage:
        @app.put("/content/{id}")
        async def edit_content(
            id: str,
            user: User = Depends(require_editor)
        ):
            return {"message": "Content editing allowed"}
    """
    return current_user


async def require_admin(
    current_user: User = Depends(require_role(UserRole.ADMIN))
) -> User:
    """
    FastAPI dependency to require ADMIN role

    Admins have full access to all features including user management.

    Usage:
        @app.delete("/users/{id}")
        async def delete_user(
            id: str,
            user: User = Depends(require_admin)
        ):
            return {"message": "User deletion allowed"}
    """
    return current_user


# Optional dependency for routes that support both authenticated and anonymous access

async def get_optional_user(
    token: Optional[str] = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db)
) -> Optional[User]:
    """
    FastAPI dependency to optionally get the current user

    Returns the user if a valid token is provided, or None if not authenticated.
    Does not raise an error if no token is provided.

    Useful for routes that provide different content for authenticated vs anonymous users.

    Args:
        token: Optional JWT access token from Authorization header
        db: Database session

    Returns:
        User object if authenticated, None otherwise

    Usage:
        @app.get("/content")
        async def get_content(user: Optional[User] = Depends(get_optional_user)):
            if user:
                return {"content": "Premium content"}
            return {"content": "Public content"}
    """
    if not token:
        return None

    try:
        user = await SessionService.validate_session(
            db=db,
            access_token=token,
            refresh_activity=True
        )
        return user
    except Exception as e:
        logger.debug(f"Optional auth failed: {e}")
        return None


def has_permission(user: User, permission: str) -> bool:
    """
    Check if a user has a specific permission

    This is a helper function for more granular permission checks beyond roles.
    Can be extended to support permission-based access control in addition to RBAC.

    Args:
        user: User object to check
        permission: Permission string to check (e.g., "documents:delete")

    Returns:
        True if user has permission, False otherwise

    Example:
        if has_permission(user, "documents:delete"):
            # Allow deletion
            pass
    """
    # For now, use role-based permissions
    # This can be extended with a permission table in the future

    permission_map = {
        UserRole.WRITER: [
            "documents:read",
            "documents:create",
            "conversations:read",
            "conversations:create"
        ],
        UserRole.EDITOR: [
            "documents:read",
            "documents:create",
            "documents:update",
            "documents:delete",
            "conversations:read",
            "conversations:create",
            "conversations:update",
            "templates:read",
            "templates:create",
            "templates:update"
        ],
        UserRole.ADMIN: [
            "*"  # Admins have all permissions
        ]
    }

    # Superusers have all permissions
    if user.is_superuser:
        return True

    # Get permissions for user role
    user_permissions = permission_map.get(user.role, [])

    # Check for wildcard or specific permission
    return "*" in user_permissions or permission in user_permissions
