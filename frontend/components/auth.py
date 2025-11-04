"""
Authentication UI components.
"""

import streamlit as st
from typing import Optional, Dict, Any


def require_authentication(role: Optional[str] = None) -> bool:
    """
    Decorator/check to require authentication for a page.

    Args:
        role: Optional required role (administrator, editor, writer)

    Returns:
        True if authenticated and authorized, False otherwise
    """
    if not st.session_state.get('authenticated', False):
        st.error("⛔ Please log in to access this page.")
        st.page_link("app.py", label="Go to Login", icon="🔐")
        st.stop()
        return False

    if role and st.session_state.get('user_role') != role:
        st.error(f"⛔ This page requires {role} role.")
        st.page_link("app.py", label="Go to Home", icon="🏠")
        st.stop()
        return False

    return True


def require_role(allowed_roles: list[str]) -> bool:
    """
    Check if user has one of the allowed roles.

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
    Get current authenticated user.

    Returns:
        User dict or None if not authenticated
    """
    return st.session_state.get('user')


def is_authenticated() -> bool:
    """
    Check if user is authenticated.

    Returns:
        True if authenticated, False otherwise
    """
    return st.session_state.get('authenticated', False)
