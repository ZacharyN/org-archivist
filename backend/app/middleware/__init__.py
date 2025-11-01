"""
Authentication and authorization middleware for FastAPI
"""

from app.middleware.auth import (
    get_current_user,
    get_current_active_user,
    require_role,
    require_admin,
    require_editor,
    require_writer,
    oauth2_scheme
)

# Import middleware configuration functions using importlib to avoid circular imports
import importlib.util
import sys
from pathlib import Path

# Load middleware.py module from parent directory
middleware_py_path = Path(__file__).parent.parent / "middleware.py"
spec = importlib.util.spec_from_file_location("app_middleware", middleware_py_path)
middleware_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(middleware_module)

configure_middleware = middleware_module.configure_middleware
configure_exception_handlers = middleware_module.configure_exception_handlers

__all__ = [
    "get_current_user",
    "get_current_active_user",
    "require_role",
    "require_admin",
    "require_editor",
    "require_writer",
    "oauth2_scheme",
    "configure_middleware",
    "configure_exception_handlers"
]
