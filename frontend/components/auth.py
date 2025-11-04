"""
Authentication UI components and guards for Streamlit pages.

This module provides authentication guards, session validation, and user profile components
for protecting pages and managing user sessions in the Streamlit frontend.
"""

import streamlit as st
from typing import Optional, Dict, Any, List
import logging

# Import from parent directory
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.api_client import get_api_client, AuthenticationError, APIError

logger = logging.getLogger(__name__)


def validate_and_refresh_session() -> bool:
    """
    Validate current session with backend and refresh if needed.

    This function:
    1. Checks if user has a token
    2. Validates the session with backend using /api/auth/session
    3. Updates session state with fresh user data
    4. Handles token refresh automatically via APIClient

    Returns:
        True if session is valid, False otherwise
    """
    try:
        client = get_api_client()

        # Check if we have a token
        if not client.token_manager.access_token:
            logger.debug("No access token found in session")
            return False

        # Validate session with backend (this will auto-refresh if needed)
        response = client.validate_session()

        if response and response.get('valid'):
            # Update session state with fresh user data
            user = response.get('user')
            if user:
                st.session_state.authenticated = True
                st.session_state.user = user
                st.session_state.user_role = user.get('role', 'writer')
                logger.debug(f"Session validated for user: {user.get('email')}")
                return True

        return False

    except AuthenticationError as e:
        logger.warning(f"Session validation failed: {e.message}")
        # Clear invalid session
        _clear_session()
        return False
    except Exception as e:
        logger.error(f"Unexpected error during session validation: {e}")
        return False


def _clear_session():
    """Clear all session state related to authentication."""
    keys_to_clear = ['authenticated', 'user', 'user_role', 'api_token', 'refresh_token', 'token_expires_at']
    for key in keys_to_clear:
        if key in st.session_state:
            del st.session_state[key]
    logger.info("Cleared session state")


def require_authentication(
    role: Optional[str] = None,
    allowed_roles: Optional[List[str]] = None,
    validate_session: bool = True
) -> bool:
    """
    Authentication guard to protect pages - validates session and checks role permissions.

    This guard:
    1. Validates the session with the backend (optional)
    2. Checks if user is authenticated
    3. Verifies role permissions if specified
    4. Redirects to login if authentication fails

    Args:
        role: Single required role (admin, editor, writer)
        allowed_roles: List of allowed roles (alternative to single role)
        validate_session: Whether to validate session with backend (default: True)

    Returns:
        True if authenticated and authorized

    Raises:
        st.stop() if authentication or authorization fails

    Example:
        # At top of protected page:
        require_authentication()  # Any authenticated user
        require_authentication(role="admin")  # Admin only
        require_authentication(allowed_roles=["admin", "editor"])  # Admin or editor
    """
    # Validate session with backend if requested
    if validate_session:
        session_valid = validate_and_refresh_session()
        if not session_valid:
            st.error("⛔ Your session has expired or is invalid. Please log in again.")
            st.page_link("app.py", label="Go to Login", icon="🔐")
            st.stop()
            return False
    else:
        # Just check local session state
        if not st.session_state.get('authenticated', False):
            st.error("⛔ Please log in to access this page.")
            st.page_link("app.py", label="Go to Login", icon="🔐")
            st.stop()
            return False

    # Check role permissions
    if role:
        user_role = st.session_state.get('user_role', '').lower()
        if user_role != role.lower():
            st.error(f"⛔ This page requires {role.upper()} role. Your role: {user_role.upper()}")
            st.page_link("app.py", label="Go to Home", icon="🏠")
            st.stop()
            return False

    if allowed_roles:
        user_role = st.session_state.get('user_role', '').lower()
        allowed_roles_lower = [r.lower() for r in allowed_roles]
        if user_role not in allowed_roles_lower:
            st.error(f"⛔ This page requires one of these roles: {', '.join([r.upper() for r in allowed_roles])}. Your role: {user_role.upper()}")
            st.page_link("app.py", label="Go to Home", icon="🏠")
            st.stop()
            return False

    return True


def require_role(allowed_roles: list[str]) -> bool:
    """
    Check if user has one of the allowed roles.

    DEPRECATED: Use require_authentication(allowed_roles=[...]) instead.

    Args:
        allowed_roles: List of allowed roles

    Returns:
        True if user has required role, False otherwise
    """
    user_role = st.session_state.get('user_role')

    if user_role not in allowed_roles:
        st.error(f"⛔ This action requires one of these roles: {', '.join(allowed_roles)}")
        return False

    return True


def get_current_user() -> Optional[Dict[str, Any]]:
    """
    Get current authenticated user from session state.

    Returns:
        User dict or None if not authenticated
    """
    return st.session_state.get('user')


def is_authenticated() -> bool:
    """
    Check if user is authenticated (local session state only).

    Returns:
        True if authenticated, False otherwise
    """
    return st.session_state.get('authenticated', False)


def logout():
    """
    Logout the current user and clear session.

    This function:
    1. Calls the backend logout endpoint
    2. Clears all local session state
    3. Clears tokens from TokenManager

    Returns:
        None
    """
    try:
        client = get_api_client()
        # Attempt backend logout (best effort)
        try:
            client.logout()
            logger.info("Successfully logged out from backend")
        except Exception as e:
            logger.warning(f"Backend logout failed (continuing anyway): {e}")

        # Clear all session state
        _clear_session()
        logger.info("User logged out successfully")

    except Exception as e:
        logger.error(f"Error during logout: {e}")
        # Clear session anyway
        _clear_session()


def show_user_profile(location: str = "sidebar", show_logout: bool = True) -> None:
    """
    Display user profile information in UI.

    Args:
        location: Where to display ("sidebar" or "main")
        show_logout: Whether to show logout button

    Example:
        # In a page:
        show_user_profile(location="main", show_logout=False)
    """
    user = get_current_user()

    if not user:
        return

    # Get user info
    full_name = user.get('full_name') or user.get('name') or user.get('email', 'User')
    email = user.get('email', '')
    role = user.get('role', 'writer')
    user_id = user.get('user_id', '')

    if location == "sidebar":
        st.sidebar.markdown("### 👤 User Profile")
        st.sidebar.markdown(f"**{full_name}**")
        if email and full_name != email:
            st.sidebar.markdown(f"*{email}*")
        st.sidebar.markdown(f"**Role:** {role.title()}")

        if show_logout:
            st.sidebar.markdown("---")
            if st.sidebar.button("🚪 Logout", use_container_width=True, type="secondary"):
                logout()
                st.rerun()

    else:  # main content area
        col1, col2, col3 = st.columns([1, 2, 1])

        with col2:
            st.markdown("### 👤 User Profile")

            with st.container():
                st.markdown(f"**Name:** {full_name}")
                st.markdown(f"**Email:** {email}")
                st.markdown(f"**Role:** {role.title()}")
                if user_id:
                    st.markdown(f"**User ID:** `{user_id}`")

            if show_logout:
                st.markdown("---")
                if st.button("🚪 Logout", use_container_width=True, type="secondary"):
                    logout()
                    st.rerun()


def get_user_role() -> Optional[str]:
    """
    Get the current user's role.

    Returns:
        User role string (admin, editor, writer) or None if not authenticated
    """
    user = get_current_user()
    if user:
        return user.get('role')
    return None


def check_permission(action: str) -> bool:
    """
    Check if current user has permission for an action.

    This is a simple role-based permission system.
    Can be extended in the future for more granular permissions.

    Args:
        action: Action to check (e.g., "documents:delete", "users:manage")

    Returns:
        True if user has permission, False otherwise

    Example:
        if check_permission("users:manage"):
            # Show admin panel
            pass
    """
    user_role = get_user_role()

    if not user_role:
        return False

    # Simple permission map (can be extended)
    permissions = {
        'admin': [
            'users:manage',
            'documents:delete',
            'documents:update',
            'documents:create',
            'templates:delete',
            'templates:update',
            'templates:create',
            'system:configure',
        ],
        'editor': [
            'documents:update',
            'documents:create',
            'templates:update',
            'templates:create',
        ],
        'writer': [
            'documents:create',
            'templates:create',
        ]
    }

    user_permissions = permissions.get(user_role.lower(), [])

    # Admin has wildcard permissions
    if user_role.lower() == 'admin':
        return True

    return action in user_permissions
