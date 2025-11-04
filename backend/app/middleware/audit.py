"""
Audit Logging Middleware

This middleware intercepts HTTP requests and logs important actions to the audit_log table
for security, compliance, and debugging purposes.

Logs:
- Document uploads/deletions
- Output creations/updates/deletions
- Writing style changes
- User authentication events
- Success tracking updates
- Role changes
- Conversation create/delete
"""

import logging
import re
import asyncio
from typing import Optional, Dict, Any, Tuple
from uuid import uuid4
from datetime import datetime

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger(__name__)


class AuditLoggingMiddleware(BaseHTTPMiddleware):
    """
    Middleware to log all important actions to audit_log table

    Features:
    - Pattern-based endpoint matching
    - Async, non-blocking database writes
    - Graceful error handling (doesn't break requests)
    - Extracts user_id, entity information, and request details
    - <10ms overhead per request (async writes)
    """

    # Patterns for auditable endpoints: (regex_pattern, event_type, entity_type)
    AUDIT_PATTERNS = [
        # Document operations
        (r"^POST /api/documents/upload$", "document.upload", "document"),
        (r"^DELETE /api/documents/([0-9a-f-]{36})$", "document.delete", "document"),

        # Output operations
        (r"^POST /api/outputs/?$", "output.create", "output"),
        (r"^PUT /api/outputs/([0-9a-f-]{36})$", "output.update", "output"),
        (r"^DELETE /api/outputs/([0-9a-f-]{36})$", "output.delete", "output"),

        # Success tracking operations
        (r"^PUT /api/outputs/([0-9a-f-]{36})/success$", "success_tracking.update", "success_tracking"),
        (r"^PATCH /api/outputs/([0-9a-f-]{36})/success$", "success_tracking.update", "success_tracking"),

        # Writing style operations
        (r"^POST /api/writing-styles/?$", "writing_style.create", "writing_style"),
        (r"^PUT /api/writing-styles/([0-9a-f-]{36})$", "writing_style.update", "writing_style"),
        (r"^DELETE /api/writing-styles/([0-9a-f-]{36})$", "writing_style.delete", "writing_style"),

        # Authentication operations
        (r"^POST /api/auth/login/?$", "user.login", "user"),
        (r"^POST /api/auth/logout/?$", "user.logout", "user"),
        (r"^POST /api/auth/refresh/?$", "user.token_refresh", "user"),

        # User management operations
        (r"^PUT /api/users/([^/]+)/role$", "user.role_change", "user"),
        (r"^POST /api/users/?$", "user.create", "user"),
        (r"^DELETE /api/users/([^/]+)$", "user.delete", "user"),

        # Conversation operations
        (r"^POST /api/chat/?$", "conversation.create", "conversation"),
        (r"^DELETE /api/chat/([0-9a-f-]{36})$", "conversation.delete", "conversation"),
    ]

    def __init__(self, app):
        """Initialize audit logging middleware"""
        super().__init__(app)
        logger.info("AuditLoggingMiddleware initialized")

    async def dispatch(self, request: Request, call_next) -> Response:
        """
        Middleware dispatch method

        Intercepts requests, processes them, and logs auditable actions
        to the audit_log table asynchronously.
        """
        # Extract user from request state (set by auth middleware)
        user_id = self._extract_user_id(request)

        # Build request signature for pattern matching
        method = request.method
        path = request.url.path
        signature = f"{method} {path}"

        # Check if this request is auditable
        audit_info = self._match_audit_pattern(signature)

        # Process the request
        response = await call_next(request)

        # Log audit entry if auditable and successful (2xx status)
        if audit_info and 200 <= response.status_code < 300:
            # Schedule async audit logging (don't await - non-blocking)
            asyncio.create_task(
                self._log_audit_entry(
                    request=request,
                    response=response,
                    event_type=audit_info["event_type"],
                    entity_type=audit_info["entity_type"],
                    entity_id=audit_info.get("entity_id"),
                    user_id=user_id
                )
            )

        return response

    def _match_audit_pattern(self, signature: str) -> Optional[Dict[str, Any]]:
        """
        Match request signature against audit patterns

        Args:
            signature: HTTP method + path (e.g., "POST /api/documents/upload")

        Returns:
            Dict with event_type, entity_type, and optional entity_id
            None if no match found
        """
        for pattern, event_type, entity_type in self.AUDIT_PATTERNS:
            match = re.match(pattern, signature)
            if match:
                # Extract entity ID from URL if captured by regex group
                entity_id = match.group(1) if match.groups() else None

                return {
                    "event_type": event_type,
                    "entity_type": entity_type,
                    "entity_id": entity_id
                }

        return None

    def _extract_user_id(self, request: Request) -> Optional[str]:
        """
        Extract user ID from request

        The auth middleware sets request.state.user when a user is authenticated.

        Args:
            request: FastAPI request object

        Returns:
            User ID string or None if not authenticated
        """
        if hasattr(request.state, "user"):
            user = request.state.user
            # Handle different user object structures
            if hasattr(user, "user_id"):
                return user.user_id
            elif hasattr(user, "username"):
                return user.username
            elif isinstance(user, dict):
                return user.get("user_id") or user.get("username")

        return None

    def _extract_entity_id_from_response(
        self,
        response: Response,
        entity_type: str
    ) -> Optional[str]:
        """
        Extract entity ID from response body

        For CREATE operations, the entity ID is typically in the response body.
        This method attempts to parse the response and extract relevant IDs.

        Args:
            response: FastAPI response object
            entity_type: Type of entity (document, output, etc.)

        Returns:
            Entity ID string or None if not found
        """
        # This is a simplified implementation
        # In a real scenario, you might need to parse response.body
        # For now, we'll handle this in the endpoint itself or extract from URL
        return None

    async def _log_audit_entry(
        self,
        request: Request,
        response: Response,
        event_type: str,
        entity_type: str,
        entity_id: Optional[str],
        user_id: Optional[str]
    ) -> None:
        """
        Write audit log entry to database

        This method runs asynchronously and doesn't block the request.
        Errors are logged but don't affect the request processing.

        Args:
            request: FastAPI request object
            response: FastAPI response object
            event_type: Type of event (e.g., "document.upload")
            entity_type: Type of entity (e.g., "document")
            entity_id: ID of affected entity (optional)
            user_id: ID of user performing action (optional)
        """
        try:
            # Import here to avoid circular dependency
            from app.services.database import get_database_service

            # Build details dictionary with request/response metadata
            details = {
                "ip_address": request.client.host if request.client else None,
                "user_agent": request.headers.get("user-agent"),
                "method": request.method,
                "path": request.url.path,
                "query_params": dict(request.query_params) if request.query_params else None,
                "status_code": response.status_code,
                "request_id": getattr(request.state, "request_id", None),
            }

            # Add referer if available (useful for tracking user flow)
            referer = request.headers.get("referer")
            if referer:
                details["referer"] = referer

            # Get database service and create audit log
            db = get_database_service()

            await db.create_audit_log(
                event_type=event_type,
                entity_type=entity_type,
                entity_id=entity_id,
                user_id=user_id,
                details=details
            )

            logger.debug(
                f"Audit log created: {event_type} by {user_id or 'anonymous'} "
                f"on {entity_type} {entity_id or 'N/A'}"
            )

        except Exception as e:
            # Log error but don't raise - audit logging failures should never break requests
            logger.error(
                f"Failed to create audit log entry: {str(e)}",
                exc_info=True
            )
