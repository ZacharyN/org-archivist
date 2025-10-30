"""
Writing Styles API endpoints

This module provides API endpoints for managing writing styles:
- POST /api/writing-styles/analyze - Analyze samples to create style prompt
- GET /api/writing-styles - List writing styles with filtering
- POST /api/writing-styles - Create a new writing style
- GET /api/writing-styles/{style_id} - Get a specific writing style
- PUT /api/writing-styles/{style_id} - Update a writing style
- DELETE /api/writing-styles/{style_id} - Delete a writing style
"""

import logging
from typing import Optional
from uuid import uuid4
from datetime import datetime

from fastapi import APIRouter, HTTPException, Query, status
from fastapi.responses import JSONResponse

from ..models.writing_style import (
    StyleAnalysisRequest,
    StyleAnalysisResponse,
    WritingStyle,
    WritingStyleCreateRequest,
    WritingStyleUpdateRequest,
    WritingStyleListResponse,
    WritingStyleResponse,
)
from ..models.common import ErrorResponse
from ..services.style_analysis import StyleAnalysisService
from ..services.database import get_database_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/writing-styles", tags=["Writing Styles"])

# Initialize services
style_analysis_service = StyleAnalysisService()


@router.post(
    "/analyze",
    response_model=StyleAnalysisResponse,
    status_code=status.HTTP_200_OK,
    responses={
        400: {"model": ErrorResponse, "description": "Invalid request"},
        500: {"model": ErrorResponse, "description": "Analysis failed"},
    },
    summary="Analyze writing samples",
    description="""
    Analyze 3-7 writing samples to generate a style prompt.

    This endpoint uses Claude AI to analyze:
    - Vocabulary selection and complexity
    - Sentence structure and variety
    - Thought composition and logic
    - Paragraph structure and flow
    - Transitions and connective phrases
    - Tone and formality
    - Perspective (1st/3rd person)
    - Data integration approach

    Requirements:
    - Minimum 3 samples, maximum 7 samples
    - Each sample must have at least 200 words
    - Total recommended: 1000-10000 words combined

    Returns a draft style prompt ready for review and customization.
    """,
)
async def analyze_samples(request: StyleAnalysisRequest) -> StyleAnalysisResponse:
    """
    Analyze writing samples to generate a style prompt

    Args:
        request: Analysis request with samples and style type

    Returns:
        StyleAnalysisResponse with generated style prompt and analysis

    Raises:
        HTTPException: If analysis fails or validation errors
    """
    try:
        logger.info(
            f"Analyzing {len(request.samples)} samples for style type: {request.style_type}"
        )

        # Perform AI analysis
        response = await style_analysis_service.analyze_samples(
            samples=request.samples,
            style_type=request.style_type,
            style_name=request.style_name,
        )

        logger.info(
            f"Analysis complete. Generated {response.word_count} word style prompt in {response.generation_time:.2f}s"
        )

        return response

    except ValueError as e:
        logger.error(f"Validation error in analyze_samples: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Failed to analyze samples: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Analysis failed: {str(e)}"
        )


@router.get(
    "",
    response_model=WritingStyleListResponse,
    summary="List writing styles",
    description="""
    Retrieve all writing styles with optional filtering.

    Query parameters:
    - type: Filter by style type (grant, proposal, report, general)
    - active: Filter by active status (true/false)
    - search: Search in name and description
    - created_by: Filter by creator user ID

    Returns a list of all matching writing styles.
    """,
)
async def list_writing_styles(
    type: Optional[str] = Query(None, description="Filter by style type"),
    active: Optional[bool] = Query(None, description="Filter by active status"),
    search: Optional[str] = Query(None, description="Search in name and description"),
    created_by: Optional[str] = Query(None, description="Filter by creator"),
) -> WritingStyleListResponse:
    """
    List all writing styles with optional filtering

    Args:
        type: Filter by style type
        active: Filter by active status
        search: Search term for name and description
        created_by: Filter by creator user ID

    Returns:
        WritingStyleListResponse with list of styles and counts
    """
    try:
        db = get_database_service()

        # Get styles from database with filters
        styles_data = await db.list_writing_styles(
            style_type=type,
            active=active,
            search=search,
            created_by=created_by,
        )

        # Convert to WritingStyle models
        from datetime import datetime as dt
        styles = []
        for style_data in styles_data:
            style = WritingStyle(
                style_id=style_data["style_id"],
                name=style_data["name"],
                type=style_data["type"],
                description=style_data["description"],
                prompt_content="",  # Not included in list view for performance
                samples=[],  # Not included in list view
                analysis_metadata=None,  # Not included in list view
                sample_count=style_data["sample_count"],
                active=style_data["active"],
                created_at=dt.fromisoformat(style_data["created_at"]),
                updated_at=dt.fromisoformat(style_data["updated_at"]) if style_data["updated_at"] else None,
                created_by=style_data["created_by"],
            )
            styles.append(style)

        # Count active styles
        active_count = sum(1 for style in styles if style.active)

        return WritingStyleListResponse(
            styles=styles,
            total=len(styles),
            active_count=active_count,
        )

    except Exception as e:
        logger.error(f"Failed to list writing styles: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve writing styles: {str(e)}"
        )


@router.post(
    "",
    response_model=WritingStyleResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        400: {"model": ErrorResponse, "description": "Invalid request"},
        409: {"model": ErrorResponse, "description": "Style name already exists"},
    },
    summary="Create writing style",
    description="""
    Create a new writing style.

    The style can be created from AI-generated analysis or manually.
    Style types: grant, proposal, report, general

    The prompt_content should be 1000-2000 words of style guidelines.
    """,
)
async def create_writing_style(
    request: WritingStyleCreateRequest,
) -> WritingStyleResponse:
    """
    Create a new writing style

    Args:
        request: Style creation data

    Returns:
        WritingStyleResponse with created style

    Raises:
        HTTPException: If validation fails or name already exists
    """
    try:
        db = get_database_service()

        # Check if name already exists
        existing = await db.get_writing_style_by_name(request.name)
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Writing style with name '{request.name}' already exists"
            )

        # Generate ID and timestamps
        style_id = str(uuid4())
        now = datetime.utcnow()

        # Calculate sample count if samples provided
        sample_count = len(request.samples) if request.samples else 0

        # Insert into database
        from uuid import UUID
        await db.create_writing_style(
            style_id=UUID(style_id),
            name=request.name,
            style_type=request.type,
            prompt_content=request.prompt_content,
            description=request.description,
            samples=request.samples or [],
            analysis_metadata=request.analysis_metadata,
            sample_count=sample_count,
            created_by=None,  # TODO: Get from auth context when implemented
        )

        # Create response model
        style = WritingStyle(
            style_id=style_id,
            name=request.name,
            type=request.type,
            description=request.description,
            prompt_content=request.prompt_content,
            samples=request.samples or [],
            analysis_metadata=request.analysis_metadata,
            sample_count=sample_count,
            active=True,
            created_at=now,
            updated_at=now,
            created_by=None,
        )

        logger.info(f"Created writing style '{request.name}' with ID {style_id}")

        return WritingStyleResponse(
            style=style,
            success=True,
            message=f"Writing style '{request.name}' created successfully",
        )

    except HTTPException:
        raise
    except ValueError as e:
        logger.error(f"Validation error in create_writing_style: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Failed to create writing style: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create writing style: {str(e)}"
        )


@router.get(
    "/{style_id}",
    response_model=WritingStyleResponse,
    responses={
        404: {"model": ErrorResponse, "description": "Style not found"},
    },
    summary="Get writing style",
    description="Retrieve a specific writing style by ID",
)
async def get_writing_style(style_id: str) -> WritingStyleResponse:
    """
    Get a specific writing style

    Args:
        style_id: Style ID (UUID)

    Returns:
        WritingStyleResponse with the writing style

    Raises:
        HTTPException: If style not found
    """
    try:
        db = get_database_service()

        # Get style from database
        from uuid import UUID
        style_data = await db.get_writing_style(UUID(style_id))

        if not style_data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Writing style {style_id} not found"
            )

        # Convert to WritingStyle model
        from datetime import datetime as dt
        style = WritingStyle(
            style_id=style_data["style_id"],
            name=style_data["name"],
            type=style_data["type"],
            description=style_data["description"],
            prompt_content=style_data["prompt_content"],
            samples=style_data["samples"] or [],
            analysis_metadata=style_data["analysis_metadata"],
            sample_count=style_data["sample_count"],
            active=style_data["active"],
            created_at=dt.fromisoformat(style_data["created_at"]),
            updated_at=dt.fromisoformat(style_data["updated_at"]) if style_data["updated_at"] else None,
            created_by=style_data["created_by"],
        )

        return WritingStyleResponse(
            style=style,
            success=True,
            message="Writing style retrieved successfully",
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get writing style {style_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve writing style: {str(e)}"
        )


@router.put(
    "/{style_id}",
    response_model=WritingStyleResponse,
    responses={
        404: {"model": ErrorResponse, "description": "Style not found"},
        400: {"model": ErrorResponse, "description": "Invalid request"},
    },
    summary="Update writing style",
    description="""
    Update an existing writing style.

    Only provided fields will be updated. The updated_at timestamp
    is automatically set to the current time.
    """,
)
async def update_writing_style(
    style_id: str,
    request: WritingStyleUpdateRequest,
) -> WritingStyleResponse:
    """
    Update an existing writing style

    Args:
        style_id: Style ID (UUID)
        request: Update data (only provided fields are updated)

    Returns:
        WritingStyleResponse with updated style

    Raises:
        HTTPException: If style not found or validation fails
    """
    try:
        db = get_database_service()

        # Update in database
        from uuid import UUID
        updated_data = await db.update_writing_style(
            style_id=UUID(style_id),
            name=request.name,
            description=request.description,
            prompt_content=request.prompt_content,
            active=request.active,
        )

        if not updated_data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Writing style {style_id} not found"
            )

        # Get full style data for response
        style_data = await db.get_writing_style(UUID(style_id))

        # Convert to WritingStyle model
        from datetime import datetime as dt
        style = WritingStyle(
            style_id=style_data["style_id"],
            name=style_data["name"],
            type=style_data["type"],
            description=style_data["description"],
            prompt_content=style_data["prompt_content"],
            samples=style_data["samples"] or [],
            analysis_metadata=style_data["analysis_metadata"],
            sample_count=style_data["sample_count"],
            active=style_data["active"],
            created_at=dt.fromisoformat(style_data["created_at"]),
            updated_at=dt.fromisoformat(style_data["updated_at"]) if style_data["updated_at"] else None,
            created_by=style_data["created_by"],
        )

        logger.info(f"Updated writing style '{style.name}' (ID: {style_id})")

        return WritingStyleResponse(
            style=style,
            success=True,
            message=f"Writing style '{style.name}' updated successfully",
        )

    except HTTPException:
        raise
    except ValueError as e:
        logger.error(f"Validation error in update_writing_style: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Failed to update writing style {style_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update writing style: {str(e)}"
        )


@router.delete(
    "/{style_id}",
    responses={
        404: {"model": ErrorResponse, "description": "Style not found"},
    },
    summary="Delete writing style",
    description="Delete a writing style permanently",
)
async def delete_writing_style(style_id: str) -> dict:
    """
    Delete a writing style

    Args:
        style_id: Style ID (UUID)

    Returns:
        Success message

    Raises:
        HTTPException: If style not found
    """
    try:
        db = get_database_service()

        # Get style to confirm it exists and get name for message
        from uuid import UUID
        style_data = await db.get_writing_style(UUID(style_id))
        if not style_data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Writing style {style_id} not found"
            )

        # Delete from database
        await db.delete_writing_style(UUID(style_id))

        logger.info(f"Deleted writing style '{style_data['name']}' (ID: {style_id})")

        return {
            "success": True,
            "message": f"Writing style '{style_data['name']}' deleted successfully",
            "style_id": style_id,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete writing style {style_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete writing style: {str(e)}"
        )
