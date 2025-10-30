"""
Authentication and authorization middleware for FastAPI
"""

from backend.app.middleware.auth import (
    get_current_user,
    get_current_active_user,
    require_role,
    require_admin,
    require_editor,
    require_writer,
    oauth2_scheme
)

__all__ = [
    "get_current_user",
    "get_current_active_user",
    "require_role",
    "require_admin",
    "require_editor",
    "require_writer",
    "oauth2_scheme"
]
