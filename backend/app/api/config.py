"""
System Configuration API endpoints

This module provides endpoints for managing system configuration:
- GET /api/config - Get current system configuration
- PUT /api/config - Update system configuration
"""

from fastapi import APIRouter, HTTPException, status
from datetime import datetime

from ..models.config import (
    SystemConfiguration,
    ConfigUpdateRequest,
    ConfigResponse,
    LLMModelConfig,
    RAGConfig,
    UserPreferences,
)
from ..models.common import ErrorResponse

router = APIRouter(prefix="/api/config", tags=["Configuration"])


# In-memory configuration storage (TODO: Replace with database)
# Initialize with default values
current_config = SystemConfiguration(
    llm_config=LLMModelConfig(),
    rag_config=RAGConfig(),
    user_preferences=UserPreferences(),
)

# Track configuration metadata
config_metadata = {
    "last_updated": datetime.utcnow().isoformat(),
    "update_count": 0,
}


@router.get(
    "",
    response_model=ConfigResponse,
    summary="Get system configuration",
    description="""
    Retrieve the current system configuration.

    Returns all configuration settings including:
    - LLM model parameters (model name, temperature, max tokens)
    - RAG pipeline settings (embedding model, chunking, retrieval)
    - User preferences (defaults, citation style, auto-save)

    This endpoint can be used by the frontend to:
    - Initialize UI with current settings
    - Display configuration in settings page
    - Validate user inputs against current limits
    """,
)
async def get_config() -> ConfigResponse:
    """
    Get current system configuration.

    Returns:
        ConfigResponse with all current settings

    Raises:
        HTTPException: If configuration cannot be retrieved
    """
    try:
        return ConfigResponse(
            config=current_config,
            success=True,
            message="Configuration retrieved successfully",
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve configuration: {str(e)}",
        )


@router.put(
    "",
    response_model=ConfigResponse,
    responses={
        400: {"model": ErrorResponse, "description": "Invalid configuration"},
    },
    summary="Update system configuration",
    description="""
    Update system configuration settings.

    Only provided sections will be updated. For example, you can update
    just the LLM config without affecting RAG or user preferences.

    Each configuration section validates its inputs:
    - Temperature must be between 0.0 and 1.0
    - Max tokens must be between 512 and 8192
    - Chunk size must be between 100 and 1000
    - Retrieval count must be between 1 and 20
    - Similarity threshold must be between 0.0 and 1.0

    The configuration is applied immediately and persists until the next update.

    **Important:** In production, this endpoint should be protected with
    authentication/authorization to prevent unauthorized configuration changes.
    """,
)
async def update_config(request: ConfigUpdateRequest) -> ConfigResponse:
    """
    Update system configuration.

    Args:
        request: Configuration update data (only provided sections are updated)

    Returns:
        ConfigResponse with updated configuration

    Raises:
        HTTPException: If validation fails or update fails
    """
    try:
        global current_config, config_metadata

        # Update LLM config if provided
        if request.llm_config is not None:
            # Validate model name (basic check)
            if not request.llm_config.model_name:
                raise ValueError("Model name cannot be empty")

            current_config.llm_config = request.llm_config

        # Update RAG config if provided
        if request.rag_config is not None:
            # Validate embedding model
            if not request.rag_config.embedding_model:
                raise ValueError("Embedding model cannot be empty")

            # Validate chunk overlap isn't greater than chunk size
            if request.rag_config.chunk_overlap >= request.rag_config.chunk_size:
                raise ValueError("Chunk overlap must be less than chunk size")

            current_config.rag_config = request.rag_config

        # Update user preferences if provided
        if request.user_preferences is not None:
            # Validate citation style
            valid_styles = ["numbered", "footnote", "apa"]
            if request.user_preferences.citation_style not in valid_styles:
                raise ValueError(
                    f"Citation style must be one of: {', '.join(valid_styles)}"
                )

            current_config.user_preferences = request.user_preferences

        # Update metadata
        config_metadata["last_updated"] = datetime.utcnow().isoformat()
        config_metadata["update_count"] += 1

        # TODO: Persist to database
        # await db.save_config(current_config)

        return ConfigResponse(
            config=current_config,
            success=True,
            message="Configuration updated successfully",
        )

    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update configuration: {str(e)}",
        )


@router.get(
    "/metadata",
    summary="Get configuration metadata",
    description="Get metadata about the current configuration (last updated, update count)",
)
async def get_config_metadata() -> dict:
    """
    Get configuration metadata.

    Returns:
        Dictionary with metadata including last_updated and update_count
    """
    return {
        "metadata": config_metadata,
        "success": True,
    }


@router.post(
    "/reset",
    response_model=ConfigResponse,
    summary="Reset configuration to defaults",
    description="""
    Reset all configuration settings to their default values.

    This will:
    - Reset LLM config to default model and parameters
    - Reset RAG config to default chunking and retrieval settings
    - Reset user preferences to defaults

    **Warning:** This action cannot be undone. All custom configuration
    will be lost.
    """,
)
async def reset_config() -> ConfigResponse:
    """
    Reset configuration to defaults.

    Returns:
        ConfigResponse with default configuration

    Raises:
        HTTPException: If reset fails
    """
    try:
        global current_config, config_metadata

        # Reset to defaults
        current_config = SystemConfiguration(
            llm_config=LLMModelConfig(),
            rag_config=RAGConfig(),
            user_preferences=UserPreferences(),
        )

        # Update metadata
        config_metadata["last_updated"] = datetime.utcnow().isoformat()
        config_metadata["update_count"] += 1

        # TODO: Persist to database
        # await db.save_config(current_config)

        return ConfigResponse(
            config=current_config,
            success=True,
            message="Configuration reset to defaults",
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to reset configuration: {str(e)}",
        )
