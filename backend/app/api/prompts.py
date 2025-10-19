"""
Prompt Management API endpoints

This module provides CRUD operations for prompt templates:
- GET /api/prompts - List all prompt templates
- POST /api/prompts - Create a new prompt template
- GET /api/prompts/{prompt_id} - Get a specific prompt template
- PUT /api/prompts/{prompt_id} - Update a prompt template
- DELETE /api/prompts/{prompt_id} - Delete a prompt template
"""

from typing import Optional
from fastapi import APIRouter, HTTPException, Query, status
from uuid import uuid4
from datetime import datetime

from ..models.prompt import (
    PromptTemplate,
    PromptCreateRequest,
    PromptUpdateRequest,
    PromptListResponse,
    PromptResponse,
)
from ..models.common import ErrorResponse

router = APIRouter(prefix="/api/prompts", tags=["Prompt Management"])


# In-memory prompt storage (TODO: Replace with database)
prompts_store = {}


def _initialize_default_prompts():
    """Initialize with some default prompt templates"""
    if not prompts_store:
        defaults = [
            {
                "name": "Federal RFP",
                "category": "audience",
                "content": """Federal RFP Style Requirements:
- Highly structured with clear sections matching RFP requirements
- Technical, formal language
- Third-person perspective
- Heavy emphasis on data, metrics, and evidence-based practices
- Explicit connections to federal priorities and regulations
- Comprehensive detail on evaluation and sustainability
- Budget justification with clear cost-benefit analysis""",
                "variables": [],
            },
            {
                "name": "Foundation Grant",
                "category": "audience",
                "content": """Foundation Grant Style Requirements:
- Clear theory of change and logic model
- Balance of quantitative data and qualitative stories
- Emphasis on community partnerships and engagement
- Professional but accessible tone
- First-person organizational voice acceptable
- Focus on innovation and lessons learned
- Realistic about challenges and mitigation strategies""",
                "variables": [],
            },
            {
                "name": "Organizational Capacity",
                "category": "section",
                "content": """Required Elements:
- Organizational history and mission alignment
- Governance structure and board composition
- Staff qualifications and expertise
- Organizational track record and past successes
- Financial stability and management
- Administrative systems and infrastructure
- Quality assurance and continuous improvement processes

Structure: Start with brief organizational overview, then address each capacity area with specific evidence.""",
                "variables": ["organization_name", "years_established"],
            },
        ]

        for default in defaults:
            prompt_id = str(uuid4())
            prompts_store[prompt_id] = PromptTemplate(
                id=prompt_id,
                name=default["name"],
                category=default["category"],
                content=default["content"],
                variables=default["variables"],
                active=True,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
                version=1,
            )


# Initialize defaults on module load
_initialize_default_prompts()


@router.get(
    "",
    response_model=PromptListResponse,
    summary="List prompt templates",
    description="""
    Retrieve all prompt templates with optional filtering.

    Query parameters:
    - category: Filter by category (audience, section, brand_voice, custom)
    - active: Filter by active status (true/false)
    - search: Search in name and content

    Returns a list of all matching prompt templates.
    """,
)
async def list_prompts(
    category: Optional[str] = Query(None, description="Filter by category"),
    active: Optional[bool] = Query(None, description="Filter by active status"),
    search: Optional[str] = Query(None, description="Search in name and content"),
) -> PromptListResponse:
    """
    List all prompt templates with optional filtering.

    Args:
        category: Filter by category
        active: Filter by active status
        search: Search term for name and content

    Returns:
        PromptListResponse with list of prompts and total count
    """
    prompts = list(prompts_store.values())

    # Apply filters
    if category:
        prompts = [p for p in prompts if p.category == category]

    if active is not None:
        prompts = [p for p in prompts if p.active == active]

    if search:
        search_lower = search.lower()
        prompts = [
            p
            for p in prompts
            if search_lower in p.name.lower() or search_lower in p.content.lower()
        ]

    return PromptListResponse(prompts=prompts, total=len(prompts))


@router.post(
    "",
    response_model=PromptResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        400: {"model": ErrorResponse, "description": "Invalid request"},
    },
    summary="Create prompt template",
    description="""
    Create a new prompt template.

    The template can be used for:
    - Audience-specific prompts (category: audience)
    - Section-specific prompts (category: section)
    - Brand voice definitions (category: brand_voice)
    - Custom prompts (category: custom)

    Variables in the content should use {variable_name} syntax.
    """,
)
async def create_prompt(request: PromptCreateRequest) -> PromptResponse:
    """
    Create a new prompt template.

    Args:
        request: Prompt creation data

    Returns:
        PromptResponse with created prompt

    Raises:
        HTTPException: If validation fails
    """
    try:
        # Generate ID and timestamps
        prompt_id = str(uuid4())
        now = datetime.utcnow()

        # Create prompt template
        prompt = PromptTemplate(
            id=prompt_id,
            name=request.name,
            category=request.category,
            content=request.content,
            variables=request.variables,
            active=True,
            created_at=now,
            updated_at=now,
            version=1,
        )

        # Store in memory
        prompts_store[prompt_id] = prompt

        return PromptResponse(
            prompt=prompt,
            success=True,
            message=f"Prompt template '{request.name}' created successfully",
        )

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create prompt: {str(e)}",
        )


@router.get(
    "/{prompt_id}",
    response_model=PromptResponse,
    responses={
        404: {"model": ErrorResponse, "description": "Prompt not found"},
    },
    summary="Get prompt template",
    description="Retrieve a specific prompt template by ID",
)
async def get_prompt(prompt_id: str) -> PromptResponse:
    """
    Get a specific prompt template.

    Args:
        prompt_id: Prompt template ID

    Returns:
        PromptResponse with the prompt template

    Raises:
        HTTPException: If prompt not found
    """
    if prompt_id not in prompts_store:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Prompt template {prompt_id} not found",
        )

    prompt = prompts_store[prompt_id]

    return PromptResponse(
        prompt=prompt,
        success=True,
        message="Prompt template retrieved successfully",
    )


@router.put(
    "/{prompt_id}",
    response_model=PromptResponse,
    responses={
        404: {"model": ErrorResponse, "description": "Prompt not found"},
        400: {"model": ErrorResponse, "description": "Invalid request"},
    },
    summary="Update prompt template",
    description="""
    Update an existing prompt template.

    Only provided fields will be updated. The version number is automatically
    incremented on each update.
    """,
)
async def update_prompt(
    prompt_id: str, request: PromptUpdateRequest
) -> PromptResponse:
    """
    Update an existing prompt template.

    Args:
        prompt_id: Prompt template ID
        request: Update data (only provided fields are updated)

    Returns:
        PromptResponse with updated prompt

    Raises:
        HTTPException: If prompt not found or validation fails
    """
    if prompt_id not in prompts_store:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Prompt template {prompt_id} not found",
        )

    try:
        prompt = prompts_store[prompt_id]

        # Update fields if provided
        if request.name is not None:
            prompt.name = request.name

        if request.content is not None:
            prompt.content = request.content

        if request.variables is not None:
            prompt.variables = request.variables

        if request.active is not None:
            prompt.active = request.active

        # Update metadata
        prompt.updated_at = datetime.utcnow()
        prompt.version += 1

        # Store updated prompt
        prompts_store[prompt_id] = prompt

        return PromptResponse(
            prompt=prompt,
            success=True,
            message=f"Prompt template '{prompt.name}' updated successfully",
        )

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update prompt: {str(e)}",
        )


@router.delete(
    "/{prompt_id}",
    responses={
        404: {"model": ErrorResponse, "description": "Prompt not found"},
    },
    summary="Delete prompt template",
    description="Delete a prompt template permanently",
)
async def delete_prompt(prompt_id: str) -> dict:
    """
    Delete a prompt template.

    Args:
        prompt_id: Prompt template ID

    Returns:
        Success message

    Raises:
        HTTPException: If prompt not found
    """
    if prompt_id not in prompts_store:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Prompt template {prompt_id} not found",
        )

    prompt = prompts_store[prompt_id]
    del prompts_store[prompt_id]

    return {
        "success": True,
        "message": f"Prompt template '{prompt.name}' deleted successfully",
        "prompt_id": prompt_id,
    }
