"""
Audit Log API endpoints for Phase 5 compliance and security tracking

This module provides API endpoints for querying and retrieving audit logs:
- GET /api/audit/logs - Query audit logs with filtering and pagination (Admin only)
- GET /api/audit/logs/entity/{entity_type}/{entity_id} - Get logs for specific entity (Admin only)
"""

import logging
from typing import Optional, List
from datetime import datetime

from fastapi import APIRouter, HTTPException, Query, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from ..models.audit import (
    AuditLogResponse,
    PaginatedAuditLogResponse,
)
from ..models.common import ErrorResponse
from ..services.database import get_database_service
from ..db.models import User, UserRole
from ..api.auth import get_current_user_from_token

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/audit", tags=["Audit"])
security = HTTPBearer()


def require_admin(user: User) -> None:
    """
    Helper function to require admin role

    Args:
        user: Current authenticated user

    Raises:
        HTTPException: If user is not an admin
    """
    if user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )


@router.get(
    "/logs",
    response_model=PaginatedAuditLogResponse,
    status_code=status.HTTP_200_OK,
    responses={
        403: {"model": ErrorResponse, "description": "Not authorized - Admin access required"},
        422: {"model": ErrorResponse, "description": "Validation error"},
    },
    summary="Query audit logs",
    description="""
    Query audit logs with filtering and pagination (Admin only).

    Supports filtering by:
    - user_id: Filter by user who performed the action
    - event_type: Filter by event type (e.g., 'document.upload', 'output.create')
    - entity_type: Filter by entity type (e.g., 'document', 'output', 'user')
    - start_date: Filter logs after this timestamp
    - end_date: Filter logs before this timestamp

    Results are paginated with a maximum of 100 records per page.
    Results are sorted by created_at DESC (most recent first).

    **Requires Admin role**
    """,
)
async def query_audit_logs(
    user_id: Optional[str] = Query(None, description="Filter by user ID"),
    event_type: Optional[str] = Query(None, description="Filter by event type (e.g., 'document.upload')"),
    entity_type: Optional[str] = Query(None, description="Filter by entity type (e.g., 'document')"),
    start_date: Optional[datetime] = Query(None, description="Filter logs after this timestamp"),
    end_date: Optional[datetime] = Query(None, description="Filter logs before this timestamp"),
    page: int = Query(1, ge=1, description="Page number for pagination"),
    per_page: int = Query(50, ge=1, le=100, description="Number of results per page (max 100)"),
    current_user: User = Depends(get_current_user_from_token),
) -> PaginatedAuditLogResponse:
    """
    Query audit logs with filters and pagination

    Only accessible by Admin users.
    """
    # Require admin role
    require_admin(current_user)

    try:
        # Get database service
        db = get_database_service()

        # Query audit logs
        logs, total_count = await db.query_audit_log(
            user_id=user_id,
            event_type=event_type,
            entity_type=entity_type,
            start_date=start_date,
            end_date=end_date,
            page=page,
            per_page=per_page
        )

        # Calculate total pages
        total_pages = (total_count + per_page - 1) // per_page if total_count > 0 else 0

        # Convert rows to response models
        log_responses = [
            AuditLogResponse(
                log_id=str(log["log_id"]),
                event_type=log["event_type"],
                entity_type=log["entity_type"] or "",
                entity_id=str(log["entity_id"]) if log["entity_id"] else None,
                user_id=log["user_id"],
                details=log["details"] or {},
                created_at=log["created_at"]
            )
            for log in logs
        ]

        logger.info(
            f"Admin {current_user.email} queried audit logs: "
            f"page={page}, per_page={per_page}, total={total_count}"
        )

        return PaginatedAuditLogResponse(
            logs=log_responses,
            total_count=total_count,
            page=page,
            per_page=per_page,
            total_pages=total_pages
        )

    except Exception as e:
        logger.error(f"Failed to query audit logs: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve audit logs"
        )


@router.get(
    "/logs/entity/{entity_type}/{entity_id}",
    response_model=List[AuditLogResponse],
    status_code=status.HTTP_200_OK,
    responses={
        403: {"model": ErrorResponse, "description": "Not authorized - Admin access required"},
        422: {"model": ErrorResponse, "description": "Validation error"},
    },
    summary="Get audit logs for specific entity",
    description="""
    Get all audit logs for a specific entity (Admin only).

    Returns all audit log entries for the specified entity type and ID,
    sorted by created_at DESC (most recent first).

    **Requires Admin role**

    Examples:
    - `/api/audit/logs/entity/document/550e8400-e29b-41d4-a716-446655440000`
    - `/api/audit/logs/entity/output/6a7e5400-e39b-51e5-b817-557766551111`
    """,
)
async def get_entity_audit_logs(
    entity_type: str,
    entity_id: str,
    current_user: User = Depends(get_current_user_from_token),
) -> List[AuditLogResponse]:
    """
    Get all audit logs for a specific entity

    Only accessible by Admin users.
    """
    # Require admin role
    require_admin(current_user)

    try:
        # Get database service
        db = get_database_service()

        # Query entity audit logs
        logs = await db.get_entity_audit_log(
            entity_type=entity_type,
            entity_id=entity_id
        )

        # Convert rows to response models
        log_responses = [
            AuditLogResponse(
                log_id=str(log["log_id"]),
                event_type=log["event_type"],
                entity_type=log["entity_type"] or "",
                entity_id=str(log["entity_id"]) if log["entity_id"] else None,
                user_id=log["user_id"],
                details=log["details"] or {},
                created_at=log["created_at"]
            )
            for log in logs
        ]

        logger.info(
            f"Admin {current_user.email} retrieved {len(log_responses)} audit logs "
            f"for {entity_type}/{entity_id}"
        )

        return log_responses

    except Exception as e:
        logger.error(
            f"Failed to retrieve entity audit logs for {entity_type}/{entity_id}: {str(e)}",
            exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve entity audit logs"
        )
