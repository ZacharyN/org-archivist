"""
Program Management API endpoints

This module provides API endpoints for managing programs (organizational categories):
- GET /api/programs - List all programs with optional filtering
- GET /api/programs/{program_id} - Get a specific program
- POST /api/programs - Create a new program (Editor+)
- PUT /api/programs/{program_id} - Update a program (Admin only)
- DELETE /api/programs/{program_id} - Delete a program (Admin only)

Authorization:
- List/Get programs: Any authenticated user (Writer+)
- Create program: Editor role or higher
- Update program: Admin role only
- Delete program: Admin role only
"""

import logging
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, status, Depends

from ..models.program import (
    ProgramCreate,
    ProgramUpdate,
    ProgramResponse,
    ProgramListResponse,
    ProgramDeleteResponse,
)
from ..models.common import ErrorResponse
from ..dependencies import get_database
from ..middleware.auth import get_current_active_user, require_editor, require_admin
from ..services.database import DatabaseService
from ..db.models import User

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/programs", tags=["Program Management"])


@router.get(
    "/active",
    response_model=list[str],
    summary="Get active program names",
    description="""
    Get list of active program names for dropdowns/autocomplete.

    Returns just the names in alphabetical order for easy frontend use.
    Requires authentication (any authenticated user).
    """
)
async def get_active_program_names(
    db: DatabaseService = Depends(get_database),
    current_user: User = Depends(get_current_active_user),
) -> list[str]:
    """
    Get list of active program names for dropdowns/autocomplete.

    This endpoint is optimized for frontend forms where you just need
    a simple list of program names (not full program objects).

    Requires any authenticated user (Writer+).

    Args:
        db: Database service dependency
        current_user: Current authenticated user

    Returns:
        List of active program names in alphabetical order

    Raises:
        HTTPException: 401 if not authenticated
        HTTPException: 500 if database error occurs
    """
    try:
        programs = await db.list_programs(active_only=True)
        # Return sorted list of just the names
        program_names = sorted([p['name'] for p in programs])

        logger.info(f"Retrieved {len(program_names)} active program names")
        return program_names

    except Exception as e:
        logger.error(f"Failed to get active program names: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get active program names: {str(e)}"
        )


@router.get(
    "",
    response_model=ProgramListResponse,
    summary="List all programs",
    description="Retrieve all programs with optional filtering by active status. Requires authentication."
)
async def list_programs(
    active_only: bool = Query(False, description="Only return active programs"),
    skip: int = Query(0, ge=0, description="Pagination offset"),
    limit: int = Query(100, ge=1, le=1000, description="Max results"),
    db: DatabaseService = Depends(get_database),
    current_user: User = Depends(get_current_active_user),
) -> ProgramListResponse:
    """
    List all programs with optional filtering

    Requires any authenticated user (Writer+).

    Args:
        active_only: Filter to only active programs
        skip: Number of records to skip (pagination)
        limit: Maximum number of records to return
        db: Database service dependency
        current_user: Current authenticated user

    Returns:
        ProgramListResponse with programs list and statistics

    Raises:
        HTTPException: 401 if not authenticated
        HTTPException: 500 if database error occurs
    """
    try:
        # Get programs list
        programs = await db.list_programs(
            active_only=active_only,
            skip=skip,
            limit=limit
        )

        # Get program statistics
        stats = await db.get_program_stats()

        logger.info(
            f"Listed {len(programs)} programs "
            f"(active_only={active_only}, skip={skip}, limit={limit})"
        )

        return ProgramListResponse(
            programs=[ProgramResponse(**p) for p in programs],
            total=stats['total'],
            active_count=stats['active_count'],
            inactive_count=stats['inactive_count']
        )

    except Exception as e:
        logger.error(f"Failed to list programs: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list programs: {str(e)}"
        )


@router.get(
    "/{program_id}",
    response_model=ProgramResponse,
    responses={
        400: {"model": ErrorResponse, "description": "Invalid program ID format"},
        404: {"model": ErrorResponse, "description": "Program not found"}
    },
    summary="Get program by ID",
    description="Retrieve a specific program by its UUID. Requires authentication."
)
async def get_program(
    program_id: str,
    db: DatabaseService = Depends(get_database),
    current_user: User = Depends(get_current_active_user),
) -> ProgramResponse:
    """
    Get a specific program by ID

    Requires any authenticated user (Writer+).

    Args:
        program_id: Program UUID string
        db: Database service dependency
        current_user: Current authenticated user

    Returns:
        ProgramResponse with program details

    Raises:
        HTTPException: 400 if program_id is not a valid UUID
        HTTPException: 401 if not authenticated
        HTTPException: 404 if program not found
        HTTPException: 500 if database error occurs
    """
    # Validate UUID format
    try:
        program_uuid = UUID(program_id)
    except ValueError:
        logger.warning(f"Invalid program ID format: {program_id}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid program ID format: {program_id}. Must be a valid UUID."
        )

    try:
        # Get program from database
        program = await db.get_program(program_uuid)

        if not program:
            logger.warning(f"Program not found: {program_id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Program {program_id} not found"
            )

        logger.info(f"Retrieved program: {program_id}")
        return ProgramResponse(**program)

    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        logger.error(f"Failed to get program {program_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get program: {str(e)}"
        )


@router.post(
    "",
    response_model=ProgramResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        400: {"model": ErrorResponse, "description": "Validation error"},
        409: {"model": ErrorResponse, "description": "Program name already exists"}
    },
    summary="Create new program",
    description="Create a new program. Requires Editor role or higher."
)
async def create_program(
    program: ProgramCreate,
    db: DatabaseService = Depends(get_database),
    current_user: User = Depends(require_editor),
) -> ProgramResponse:
    """
    Create a new program

    Requires Editor role or higher. The current user will be recorded as the creator.

    Args:
        program: Program creation request with name, description, etc.
        db: Database service dependency
        current_user: Current authenticated user (Editor+)

    Returns:
        ProgramResponse with created program details

    Raises:
        HTTPException: 400 if validation fails
        HTTPException: 409 if program name already exists
        HTTPException: 500 if database error occurs
    """
    try:
        # Create program with current user as creator
        created = await db.create_program(
            name=program.name,
            description=program.description,
            display_order=program.display_order,
            active=program.active,
            created_by=current_user.user_id
        )

        logger.info(
            f"Program created: {created['program_id']} (name: '{program.name}') "
            f"by {current_user.email}"
        )

        return ProgramResponse(**created)

    except ValueError as e:
        # Duplicate name error
        logger.warning(f"Program creation failed - duplicate name: {program.name}")
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Failed to create program: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create program: {str(e)}"
        )


@router.put(
    "/{program_id}",
    response_model=ProgramResponse,
    responses={
        400: {"model": ErrorResponse, "description": "Invalid program ID format"},
        404: {"model": ErrorResponse, "description": "Program not found"},
        409: {"model": ErrorResponse, "description": "Program name conflict"}
    },
    summary="Update program",
    description="Update an existing program. Requires Admin role."
)
async def update_program(
    program_id: str,
    program: ProgramUpdate,
    db: DatabaseService = Depends(get_database),
    current_user: User = Depends(require_admin),
) -> ProgramResponse:
    """
    Update an existing program

    Requires Admin role. Only admins can update programs to prevent
    accidental renames that could affect existing documents.

    Args:
        program_id: Program UUID string
        program: Program update request with fields to update
        db: Database service dependency
        current_user: Current authenticated user (Admin)

    Returns:
        ProgramResponse with updated program details

    Raises:
        HTTPException: 400 if program_id is not a valid UUID
        HTTPException: 404 if program not found
        HTTPException: 409 if name conflict with another program
        HTTPException: 500 if database error occurs
    """
    # Validate UUID format
    try:
        program_uuid = UUID(program_id)
    except ValueError:
        logger.warning(f"Invalid program ID format: {program_id}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid program ID format: {program_id}. Must be a valid UUID."
        )

    try:
        # Update program
        updated = await db.update_program(
            program_id=program_uuid,
            name=program.name,
            description=program.description,
            display_order=program.display_order,
            active=program.active
        )

        if not updated:
            logger.warning(f"Program not found for update: {program_id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Program {program_id} not found"
            )

        logger.info(
            f"Program updated: {program_id} by {current_user.email}"
        )

        return ProgramResponse(**updated)

    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except ValueError as e:
        # Name conflict error
        logger.warning(f"Program update failed - name conflict: {program_id}")
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Failed to update program {program_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update program: {str(e)}"
        )


@router.delete(
    "/{program_id}",
    response_model=ProgramDeleteResponse,
    responses={
        400: {"model": ErrorResponse, "description": "Invalid program ID format"},
        404: {"model": ErrorResponse, "description": "Program not found"},
        409: {"model": ErrorResponse, "description": "Program in use and force=false"}
    },
    summary="Delete program",
    description="""
    Delete a program. Requires Admin role.

    By default, deletion fails if documents are associated with this program.
    Use force=true to delete anyway (sets program_id to NULL on documents).
    """
)
async def delete_program(
    program_id: str,
    force: bool = Query(
        False,
        description="Force delete even if documents use this program"
    ),
    db: DatabaseService = Depends(get_database),
    current_user: User = Depends(require_admin),
) -> ProgramDeleteResponse:
    """
    Delete a program

    Requires Admin role. This is a dangerous operation.

    By default, deletion fails if any documents are associated with this program.
    If force=true, the program is deleted and associated documents have their
    program_id set to NULL.

    Args:
        program_id: Program UUID string
        force: Force delete even if documents use this program
        db: Database service dependency
        current_user: Current authenticated user (Admin)

    Returns:
        ProgramDeleteResponse with deletion status and impact information

    Raises:
        HTTPException: 400 if program_id is not a valid UUID
        HTTPException: 404 if program not found
        HTTPException: 409 if program in use and force=false
        HTTPException: 500 if database error occurs
    """
    # Validate UUID format
    try:
        program_uuid = UUID(program_id)
    except ValueError:
        logger.warning(f"Invalid program ID format: {program_id}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid program ID format: {program_id}. Must be a valid UUID."
        )

    try:
        # Delete program
        deleted, doc_count = await db.delete_program(
            program_id=program_uuid,
            force=force
        )

        if not deleted:
            logger.warning(f"Program not found for deletion: {program_id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Program {program_id} not found"
            )

        logger.info(
            f"Program deleted: {program_id} by {current_user.email} "
            f"(affected {doc_count} documents, force={force})"
        )

        return ProgramDeleteResponse(
            success=True,
            message="Program deleted successfully",
            program_id=program_id,
            documents_affected=doc_count
        )

    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except ValueError as e:
        # Program in use error (when force=false)
        logger.warning(
            f"Program deletion failed - program in use: {program_id} "
            f"(use force=true to delete anyway)"
        )
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Failed to delete program {program_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete program: {str(e)}"
        )