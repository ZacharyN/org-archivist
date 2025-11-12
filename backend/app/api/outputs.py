"""
Outputs API endpoints

This module provides API endpoints for managing outputs (generated grant content):
- POST /api/outputs - Create new output
- GET /api/outputs - List outputs with filtering
- GET /api/outputs/stats - Get statistics and analytics
- GET /api/outputs/{output_id} - Get a specific output
- PUT /api/outputs/{output_id} - Update an output (success tracking)
- DELETE /api/outputs/{output_id} - Delete an output
"""

import logging
from typing import Optional, List
from uuid import UUID, uuid4
from datetime import datetime, date

from fastapi import APIRouter, HTTPException, Query, status, Depends
from fastapi.responses import JSONResponse

from ..models.output import (
    OutputCreateRequest,
    OutputUpdateRequest,
    OutputResponse,
    OutputListResponse,
    OutputStatsResponse,
    OutputType,
    OutputStatus,
)
from ..models.common import ErrorResponse, PaginationMetadata
from ..services.database import DatabaseService
from ..services.success_tracking import SuccessTrackingService, StatusTransitionError
from ..api.auth import get_current_user_from_token, get_db
from ..dependencies import get_database
from ..db.models import User, UserRole
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/outputs", tags=["Outputs"])


async def check_output_permission(
    output_id: UUID,
    user: User,
    db: DatabaseService,
    action: str = "view"
) -> dict:
    """
    Check if user has permission to access an output

    Args:
        output_id: Output ID to check
        user: Current authenticated user
        db: Database service instance
        action: Action being performed (view, edit, delete)

    Returns:
        Output data if permission granted

    Raises:
        HTTPException: If output not found or permission denied
    """
    output = await db.get_output(output_id)

    if not output:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Output {output_id} not found"
        )

    # Admins can access everything
    if user.role == UserRole.ADMIN:
        return output

    # Editors can view and edit (but not delete unless owner)
    if user.role == UserRole.EDITOR:
        if action == "delete" and output["created_by"] != user.email:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only output owner or admin can delete"
            )
        return output

    # Writers can only access their own outputs
    if output["created_by"] != user.email:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only access your own outputs"
        )

    return output


@router.post(
    "",
    response_model=OutputResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        401: {"model": ErrorResponse, "description": "Unauthorized"},
        422: {"model": ErrorResponse, "description": "Validation error"},
        500: {"model": ErrorResponse, "description": "Server error"},
    },
    summary="Create new output",
    description="""
    Create a new output (generated grant content).

    Automatically sets:
    - created_by: Current authenticated user's email
    - output_id: Generated UUID
    - created_at/updated_at: Current timestamp

    Requires authentication. All users can create outputs.
    """,
)
async def create_output(
    request: OutputCreateRequest,
    user: User = Depends(get_current_user_from_token),
    db: DatabaseService = Depends(get_database)
) -> OutputResponse:
    """
    Create a new output

    Args:
        request: Output creation request
        user: Current authenticated user
        db: Database service instance

    Returns:
        Created output data

    Raises:
        HTTPException: If creation fails
    """
    try:
        logger.info(f"Creating output '{request.title}' for user {user.email}")

        output_id = uuid4()

        # Create output in database
        result = await db.create_output(
            output_id=output_id,
            conversation_id=UUID(request.conversation_id) if request.conversation_id else None,
            output_type=request.output_type.value,
            title=request.title,
            content=request.content,
            word_count=request.word_count,
            status=request.status.value,
            writing_style_id=UUID(request.writing_style_id) if request.writing_style_id else None,
            funder_name=request.funder_name,
            requested_amount=float(request.requested_amount) if request.requested_amount else None,
            awarded_amount=float(request.awarded_amount) if request.awarded_amount else None,
            submission_date=request.submission_date.isoformat() if request.submission_date else None,
            decision_date=request.decision_date.isoformat() if request.decision_date else None,
            success_notes=request.success_notes,
            metadata=request.metadata,
            created_by=user.email,
        )

        # Fetch full output data
        output = await db.get_output(output_id)

        logger.info(f"Created output {output_id}")

        return OutputResponse(**output)

    except Exception as e:
        logger.error(f"Failed to create output: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create output: {str(e)}"
        )


@router.get(
    "",
    response_model=OutputListResponse,
    responses={
        401: {"model": ErrorResponse, "description": "Unauthorized"},
        500: {"model": ErrorResponse, "description": "Server error"},
    },
    summary="List outputs",
    description="""
    List outputs with optional filtering and search.

    Filters:
    - output_type: Filter by type(s)
    - status: Filter by status(es)
    - writing_style_id: Filter by writing style
    - funder_name: Filter by funder (partial match)
    - search: Full-text search in title, content, funder_name, success_notes

    Permissions:
    - Writers: See only their own outputs
    - Editors: See all outputs
    - Admins: See all outputs

    Results are paginated with skip/limit.
    """,
)
async def list_outputs(
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(10, ge=1, le=100, description="Maximum number of records"),
    output_type: Optional[List[OutputType]] = Query(None, description="Filter by output type(s)"),
    status: Optional[List[OutputStatus]] = Query(None, description="Filter by status(es)"),
    writing_style_id: Optional[str] = Query(None, description="Filter by writing style ID"),
    funder_name: Optional[str] = Query(None, description="Filter by funder name (partial)"),
    search: Optional[str] = Query(None, description="Search in title, content, etc."),
    user: User = Depends(get_current_user_from_token),
    db: DatabaseService = Depends(get_database)
) -> OutputListResponse:
    """
    List outputs with filtering

    Args:
        skip: Pagination offset
        limit: Max results
        output_type: Filter by type(s)
        status: Filter by status(es)
        writing_style_id: Filter by style
        funder_name: Filter by funder
        search: Full-text search
        user: Current authenticated user
        db: Database service instance

    Returns:
        Paginated list of outputs
    """
    try:

        # Convert enums to strings
        type_filter = [t.value for t in output_type] if output_type else None
        status_filter = [s.value for s in status] if status else None

        # Writers can only see their own outputs
        created_by_filter = user.email if user.role == UserRole.WRITER else None

        # Use search or list based on whether search query provided
        if search:
            outputs = await db.search_outputs(
                query=search,
                output_type=type_filter,
                status=status_filter,
                skip=skip,
                limit=limit,
            )
        else:
            outputs = await db.list_outputs(
                output_type=type_filter,
                status=status_filter,
                created_by=created_by_filter,
                writing_style_id=writing_style_id,
                funder_name=funder_name,
                skip=skip,
                limit=limit,
            )

        # Get total count
        # NOTE: In production, you'd want a separate count query with filters applied
        # For now, using the returned count as total
        total_count = len(outputs)

        # Convert to response models
        output_responses = [OutputResponse(**output) for output in outputs]

        # Calculate pagination metadata
        pagination = PaginationMetadata.calculate(
            total=total_count,
            skip=skip,
            limit=limit
        )

        return OutputListResponse(
            outputs=output_responses,
            pagination=pagination,
        )

    except Exception as e:
        logger.error(f"Failed to list outputs: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list outputs: {str(e)}"
        )


@router.get(
    "/stats",
    response_model=OutputStatsResponse,
    responses={
        401: {"model": ErrorResponse, "description": "Unauthorized"},
        500: {"model": ErrorResponse, "description": "Server error"},
    },
    summary="Get output statistics",
    description="""
    Get statistics and analytics for outputs.

    Returns:
    - Total outputs count
    - Counts by output type
    - Counts by status
    - Success rate (awarded / submitted)
    - Total requested amount
    - Total awarded amount
    - Average requested and awarded amounts

    Permissions:
    - Writers: See stats for their own outputs
    - Editors/Admins: See stats for all outputs

    Can be filtered by output_type for more targeted analytics.
    """,
)
async def get_stats(
    output_type: Optional[List[OutputType]] = Query(None, description="Filter by output type(s)"),
    user: User = Depends(get_current_user_from_token),
    db: DatabaseService = Depends(get_database)
) -> OutputStatsResponse:
    """
    Get output statistics

    Args:
        output_type: Optional filter by type(s)
        user: Current authenticated user
        db: Database service instance

    Returns:
        Statistics and analytics
    """
    try:

        # Convert enums to strings
        type_filter = [t.value for t in output_type] if output_type else None

        # Writers can only see their own stats
        created_by_filter = user.email if user.role == UserRole.WRITER else None

        stats = await db.get_outputs_stats(
            output_type=type_filter,
            created_by=created_by_filter,
        )

        return OutputStatsResponse(**stats)

    except Exception as e:
        logger.error(f"Failed to get output stats: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get output stats: {str(e)}"
        )


@router.get(
    "/{output_id}",
    response_model=OutputResponse,
    responses={
        401: {"model": ErrorResponse, "description": "Unauthorized"},
        403: {"model": ErrorResponse, "description": "Permission denied"},
        404: {"model": ErrorResponse, "description": "Output not found"},
        500: {"model": ErrorResponse, "description": "Server error"},
    },
    summary="Get output by ID",
    description="""
    Get a specific output by ID.

    Permissions:
    - Writers: Can only view their own outputs
    - Editors/Admins: Can view all outputs
    """,
)
async def get_output(
    output_id: UUID,
    user: User = Depends(get_current_user_from_token),
    db: DatabaseService = Depends(get_database)
) -> OutputResponse:
    """
    Get a specific output

    Args:
        output_id: Output UUID
        user: Current authenticated user
        db: Database service instance

    Returns:
        Output data

    Raises:
        HTTPException: If not found or permission denied
    """
    output = await check_output_permission(output_id, user, db, action="view")
    return OutputResponse(**output)


@router.put(
    "/{output_id}",
    response_model=OutputResponse,
    responses={
        401: {"model": ErrorResponse, "description": "Unauthorized"},
        403: {"model": ErrorResponse, "description": "Permission denied"},
        404: {"model": ErrorResponse, "description": "Output not found"},
        422: {"model": ErrorResponse, "description": "Validation error"},
        500: {"model": ErrorResponse, "description": "Server error"},
    },
    summary="Update output",
    description="""
    Update an output (partial updates supported).

    Common use cases:
    - Update status (draft → submitted → pending → awarded/not_awarded)
    - Add success tracking (requested_amount, awarded_amount, dates, notes)
    - Update content/title

    Permissions:
    - Writers: Can only update their own outputs
    - Editors: Can update all outputs
    - Admins: Can update all outputs
    """,
)
async def update_output(
    output_id: UUID,
    request: OutputUpdateRequest,
    user: User = Depends(get_current_user_from_token),
    db: DatabaseService = Depends(get_database)
) -> OutputResponse:
    """
    Update an output

    Args:
        output_id: Output UUID
        request: Update request (partial fields)
        user: Current authenticated user
        db: Database service instance

    Returns:
        Updated output data

    Raises:
        HTTPException: If not found, permission denied, or update fails
    """
    # Check permissions
    output_data = await check_output_permission(output_id, user, db, action="edit")

    try:
        logger.info(f"Updating output {output_id} by user {user.email}")

        success_tracking = SuccessTrackingService(db)

        # Validate status transition if status is being updated
        if request.status is not None:
            current_status = output_data["status"]
            new_status = request.status.value

            # Admins can override status transitions
            allow_override = user.role == UserRole.ADMIN

            try:
                success_tracking.validate_status_transition(
                    current_status,
                    new_status,
                    allow_override=allow_override
                )
            except StatusTransitionError as e:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=str(e)
                )

        # Build update dict from request (only non-None fields)
        updates = {}
        if request.output_type is not None:
            updates["output_type"] = request.output_type.value
        if request.title is not None:
            updates["title"] = request.title
        if request.content is not None:
            updates["content"] = request.content
        if request.word_count is not None:
            updates["word_count"] = request.word_count
        if request.status is not None:
            updates["status"] = request.status.value
        if request.writing_style_id is not None:
            updates["writing_style_id"] = UUID(request.writing_style_id)
        if request.funder_name is not None:
            updates["funder_name"] = request.funder_name
        if request.requested_amount is not None:
            updates["requested_amount"] = float(request.requested_amount)
        if request.awarded_amount is not None:
            updates["awarded_amount"] = float(request.awarded_amount)
        if request.submission_date is not None:
            updates["submission_date"] = request.submission_date.isoformat()
        if request.decision_date is not None:
            updates["decision_date"] = request.decision_date.isoformat()
        if request.success_notes is not None:
            updates["success_notes"] = request.success_notes
        if request.metadata is not None:
            updates["metadata"] = request.metadata

        # Validate outcome data and log warnings
        if request.status is not None:
            warnings = success_tracking.validate_outcome_data(
                status=request.status.value,
                funder_name=request.funder_name or output_data.get("funder_name"),
                requested_amount=request.requested_amount or output_data.get("requested_amount"),
                awarded_amount=request.awarded_amount or output_data.get("awarded_amount"),
                submission_date=request.submission_date or output_data.get("submission_date"),
                decision_date=request.decision_date or output_data.get("decision_date"),
            )

            if warnings:
                logger.warning(f"Output {output_id} data validation warnings: {warnings}")

        # Perform update
        result = await db.update_output(output_id, **updates)

        if not result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Output {output_id} not found"
            )

        # Fetch full updated output
        output = await db.get_output(output_id)

        logger.info(f"Updated output {output_id}")

        return OutputResponse(**output)

    except HTTPException:
        raise
    except StatusTransitionError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Failed to update output {output_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update output: {str(e)}"
        )


@router.delete(
    "/{output_id}",
    status_code=status.HTTP_200_OK,
    responses={
        401: {"model": ErrorResponse, "description": "Unauthorized"},
        403: {"model": ErrorResponse, "description": "Permission denied"},
        404: {"model": ErrorResponse, "description": "Output not found"},
        500: {"model": ErrorResponse, "description": "Server error"},
    },
    summary="Delete output",
    description="""
    Delete an output permanently.

    Permissions:
    - Writers: Can only delete their own outputs
    - Editors: Can only delete their own outputs
    - Admins: Can delete any output

    This action cannot be undone.
    """,
)
async def delete_output(
    output_id: UUID,
    user: User = Depends(get_current_user_from_token),
    db: DatabaseService = Depends(get_database)
) -> dict:
    """
    Delete an output

    Args:
        output_id: Output UUID
        user: Current authenticated user
        db: Database service instance

    Returns:
        Success message

    Raises:
        HTTPException: If not found, permission denied, or deletion fails
    """
    # Check permissions (delete has stricter rules)
    await check_output_permission(output_id, user, db, action="delete")

    try:
        logger.info(f"Deleting output {output_id} by user {user.email}")

        deleted = await db.delete_output(output_id)

        if not deleted:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Output {output_id} not found"
            )

        logger.info(f"Deleted output {output_id}")

        return {"message": f"Output {output_id} deleted successfully"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete output {output_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete output: {str(e)}"
        )


# ======================
# Success Tracking & Analytics Endpoints
# ======================


@router.get(
    "/analytics/style/{style_id}",
    response_model=dict,
    responses={
        401: {"model": ErrorResponse, "description": "Unauthorized"},
        500: {"model": ErrorResponse, "description": "Server error"},
    },
    summary="Get success rate by writing style",
    description="""
    Calculate success rate for outputs using a specific writing style.

    Returns metrics including:
    - Total outputs using the style
    - Number submitted, awarded, not awarded
    - Success rate percentage
    - Total and average amounts

    Permissions:
    - All authenticated users can access this endpoint
    """,
)
async def get_success_rate_by_style(
    style_id: UUID,
    start_date: Optional[datetime] = Query(None, description="Start date filter"),
    end_date: Optional[datetime] = Query(None, description="End date filter"),
    user: User = Depends(get_current_user_from_token),
    db: DatabaseService = Depends(get_database)
) -> dict:
    """
    Get success rate for a writing style

    Args:
        style_id: Writing style UUID
        start_date: Optional start date filter
        end_date: Optional end date filter
        user: Current authenticated user
        db: Database service instance

    Returns:
        Success rate metrics for the style
    """
    try:
        success_tracking = SuccessTrackingService(db)

        metrics = await success_tracking.calculate_success_rate_by_style(
            style_id=style_id,
            start_date=start_date,
            end_date=end_date,
        )

        return metrics

    except Exception as e:
        logger.error(f"Failed to get success rate by style {style_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get success rate by style: {str(e)}"
        )


@router.get(
    "/analytics/funder/{funder_name}",
    response_model=dict,
    responses={
        401: {"model": ErrorResponse, "description": "Unauthorized"},
        500: {"model": ErrorResponse, "description": "Server error"},
    },
    summary="Get success rate by funder",
    description="""
    Calculate success rate for a specific funder.

    Returns metrics including:
    - Total outputs submitted to funder
    - Number awarded, not awarded
    - Success rate percentage
    - Total and average award amounts

    Permissions:
    - All authenticated users can access this endpoint
    """,
)
async def get_success_rate_by_funder(
    funder_name: str,
    start_date: Optional[datetime] = Query(None, description="Start date filter"),
    end_date: Optional[datetime] = Query(None, description="End date filter"),
    user: User = Depends(get_current_user_from_token),
    db: DatabaseService = Depends(get_database)
) -> dict:
    """
    Get success rate for a funder

    Args:
        funder_name: Funder name (partial match)
        start_date: Optional start date filter
        end_date: Optional end date filter
        user: Current authenticated user
        db: Database service instance

    Returns:
        Success rate metrics for the funder
    """
    try:
        success_tracking = SuccessTrackingService(db)

        metrics = await success_tracking.calculate_success_rate_by_funder(
            funder_name=funder_name,
            start_date=start_date,
            end_date=end_date,
        )

        return metrics

    except Exception as e:
        logger.error(f"Failed to get success rate by funder {funder_name}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get success rate by funder: {str(e)}"
        )


@router.get(
    "/analytics/year/{year}",
    response_model=dict,
    responses={
        401: {"model": ErrorResponse, "description": "Unauthorized"},
        500: {"model": ErrorResponse, "description": "Server error"},
    },
    summary="Get success rate by year",
    description="""
    Calculate success rate for outputs in a specific year.

    Returns metrics including:
    - Total outputs submitted in the year
    - Number awarded, not awarded
    - Success rate percentage
    - Total and average award amounts

    Permissions:
    - All authenticated users can access this endpoint
    """,
)
async def get_success_rate_by_year(
    year: int,
    user: User = Depends(get_current_user_from_token),
    db: DatabaseService = Depends(get_database)
) -> dict:
    """
    Get success rate for a specific year

    Args:
        year: Year to analyze
        user: Current authenticated user
        db: Database service instance

    Returns:
        Success rate metrics for the year
    """
    try:
        success_tracking = SuccessTrackingService(db)

        metrics = await success_tracking.calculate_success_rate_by_year(year=year)

        return metrics

    except Exception as e:
        logger.error(f"Failed to get success rate by year {year}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get success rate by year: {str(e)}"
        )


@router.get(
    "/analytics/summary",
    response_model=dict,
    responses={
        401: {"model": ErrorResponse, "description": "Unauthorized"},
        500: {"model": ErrorResponse, "description": "Server error"},
    },
    summary="Get comprehensive success metrics summary",
    description="""
    Get comprehensive success metrics including:
    - Overall statistics (from /stats endpoint)
    - Top performing writing styles
    - Top funders by success rate
    - Year-over-year trends

    Permissions:
    - Writers: See summary for their own outputs
    - Editors/Admins: See summary for all outputs

    This is a comprehensive dashboard-ready endpoint.
    """,
)
async def get_success_metrics_summary(
    user: User = Depends(get_current_user_from_token),
    db: DatabaseService = Depends(get_database)
) -> dict:
    """
    Get comprehensive success metrics summary

    Args:
        user: Current authenticated user
        db: Database service instance

    Returns:
        Comprehensive metrics summary
    """
    try:
        success_tracking = SuccessTrackingService(db)

        # Writers can only see their own metrics
        created_by_filter = user.email if user.role == UserRole.WRITER else None

        metrics = await success_tracking.get_success_metrics_summary(
            created_by=created_by_filter
        )

        return metrics

    except Exception as e:
        logger.error(f"Failed to get success metrics summary: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get success metrics summary: {str(e)}"
        )


@router.get(
    "/analytics/funders",
    response_model=List[dict],
    responses={
        401: {"model": ErrorResponse, "description": "Unauthorized"},
        500: {"model": ErrorResponse, "description": "Server error"},
    },
    summary="Get funder performance metrics",
    description="""
    Get performance metrics for all funders, ordered by success rate.

    Returns list of funders with:
    - Total submissions
    - Award/rejection/pending counts
    - Success rate percentage
    - Total and average award amounts

    Permissions:
    - Writers: See funders they've submitted to
    - Editors/Admins: See all funders

    Useful for identifying which funders to prioritize.
    """,
)
async def get_funder_performance(
    limit: int = Query(10, ge=1, le=50, description="Maximum number of funders"),
    user: User = Depends(get_current_user_from_token),
    db: DatabaseService = Depends(get_database)
) -> List[dict]:
    """
    Get performance metrics for funders

    Args:
        limit: Maximum number of funders to return
        user: Current authenticated user
        db: Database service instance

    Returns:
        List of funder performance metrics
    """
    try:
        success_tracking = SuccessTrackingService(db)

        # Writers can only see their own funder performance
        created_by_filter = user.email if user.role == UserRole.WRITER else None

        funders = await success_tracking.get_funder_performance(
            limit=limit,
            created_by=created_by_filter,
        )

        return funders

    except Exception as e:
        logger.error(f"Failed to get funder performance: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get funder performance: {str(e)}"
        )
