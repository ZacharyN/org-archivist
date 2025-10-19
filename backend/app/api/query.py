"""
Query and Generation API endpoints

This module provides endpoints for content generation using RAG:
- POST /api/query - Non-streaming generation
- POST /api/query/stream - Streaming generation with Server-Sent Events
"""

from typing import AsyncIterator
from fastapi import APIRouter, HTTPException, status
from fastapi.responses import StreamingResponse
import json
import asyncio

from ..models.query import QueryRequest, QueryResponse, Source
from ..models.common import ErrorResponse

router = APIRouter(prefix="/api/query", tags=["Query & Generation"])


@router.post(
    "",
    response_model=QueryResponse,
    responses={
        400: {"model": ErrorResponse, "description": "Invalid request"},
        500: {"model": ErrorResponse, "description": "Generation failed"},
    },
    summary="Generate content (non-streaming)",
    description="""
    Generate grant writing content based on a query using RAG.

    This endpoint performs the full RAG pipeline:
    1. Retrieves relevant document chunks from vector database
    2. Constructs prompt with context and parameters
    3. Calls Claude API for generation
    4. Validates response quality
    5. Processes citations

    Returns complete response with text, sources, and quality metrics.
    """,
)
async def query_generate(request: QueryRequest) -> QueryResponse:
    """
    Generate content using RAG (non-streaming).

    Args:
        request: Query parameters including query text, audience, section, tone, etc.

    Returns:
        QueryResponse with generated text, sources, confidence score, and metadata

    Raises:
        HTTPException: If generation fails or request is invalid
    """
    try:
        # TODO: Implement full RAG pipeline
        # 1. Validate request
        if not request.query or not request.query.strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Query text is required"
            )

        # 2. Retrieve relevant context (stub)
        # retrieval_engine = get_retrieval_engine()
        # context = await retrieval_engine.retrieve(
        #     query=request.query,
        #     top_k=request.max_sources,
        #     filters=request.filters,
        #     recency_weight=request.recency_weight
        # )

        # 3. Generate response (stub)
        # generation_service = get_generation_service()
        # response = await generation_service.generate(
        #     query=request.query,
        #     context=context,
        #     parameters=request,
        #     stream=False
        # )

        # 4. Validate quality (stub)
        # validator = get_quality_validator()
        # validation = validator.validate(
        #     query=request.query,
        #     response=response.text,
        #     sources=context,
        #     parameters=request
        # )

        # Stub response for now
        stub_sources = [
            Source(
                id=1,
                filename="example_proposal_2024.pdf",
                doc_type="Grant Proposal",
                year=2024,
                excerpt="Example content from the proposal...",
                relevance=0.95
            ),
            Source(
                id=2,
                filename="annual_report_2023.pdf",
                doc_type="Annual Report",
                year=2023,
                excerpt="Example content from annual report...",
                relevance=0.87
            )
        ]

        stub_text = f"""Based on the query "{request.query}", here is generated content for {request.audience} audience in {request.tone} tone.

This is a stub response that will be replaced with actual Claude-generated content once the full RAG pipeline is implemented.

The response would include:
- Context from retrieved documents
- Audience-appropriate language ({request.audience})
- Section-specific structure ({request.section})
- Proper tone ({request.tone})
- Inline citations [1], [2] if requested

[1] Example citation from first source
[2] Example citation from second source
"""

        return QueryResponse(
            text=stub_text,
            sources=stub_sources,
            confidence=0.85,
            quality_issues=[],
            metadata={
                "model": "claude-sonnet-4.5",
                "tokens_used": 0,
                "retrieval_time_ms": 0,
                "generation_time_ms": 0,
                "sources_retrieved": len(stub_sources),
                "filters_applied": request.filters is not None
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Generation failed: {str(e)}"
        )


async def generate_stream(request: QueryRequest) -> AsyncIterator[str]:
    """
    Async generator for streaming responses.

    Yields Server-Sent Event formatted chunks.
    """
    try:
        # TODO: Implement actual streaming RAG pipeline
        # 1. Retrieve context
        # 2. Build prompt
        # 3. Stream from Claude API
        # 4. Yield chunks as SSE

        # Stub streaming implementation
        stub_response = f"""Based on the query "{request.query}", here is generated content for {request.audience} audience.

This is a stub streaming response. """

        words = stub_response.split()

        # Send metadata first
        metadata = {
            "type": "metadata",
            "model": "claude-sonnet-4.5",
            "sources_count": 2
        }
        yield f"data: {json.dumps(metadata)}\n\n"

        # Stream words with delay to simulate real streaming
        for i, word in enumerate(words):
            chunk = {
                "type": "content",
                "text": word + " ",
                "index": i
            }
            yield f"data: {json.dumps(chunk)}\n\n"
            await asyncio.sleep(0.05)  # Simulate streaming delay

        # Send sources at the end
        sources = {
            "type": "sources",
            "sources": [
                {
                    "id": 1,
                    "filename": "example_proposal_2024.pdf",
                    "doc_type": "Grant Proposal",
                    "year": 2024,
                    "excerpt": "Example content...",
                    "relevance": 0.95
                },
                {
                    "id": 2,
                    "filename": "annual_report_2023.pdf",
                    "doc_type": "Annual Report",
                    "year": 2023,
                    "excerpt": "Example content...",
                    "relevance": 0.87
                }
            ]
        }
        yield f"data: {json.dumps(sources)}\n\n"

        # Send completion event
        completion = {
            "type": "done",
            "confidence": 0.85,
            "quality_issues": []
        }
        yield f"data: {json.dumps(completion)}\n\n"

    except Exception as e:
        error = {
            "type": "error",
            "message": str(e)
        }
        yield f"data: {json.dumps(error)}\n\n"


@router.post(
    "/stream",
    responses={
        400: {"model": ErrorResponse, "description": "Invalid request"},
        500: {"model": ErrorResponse, "description": "Streaming failed"},
    },
    summary="Generate content (streaming)",
    description="""
    Generate grant writing content with streaming response using Server-Sent Events (SSE).

    This endpoint provides real-time streaming of generated content:
    - Immediate feedback as content is generated
    - Lower perceived latency
    - Better UX for long-form content

    The response stream includes multiple event types:
    - `metadata`: Model and configuration info
    - `content`: Text chunks as they're generated
    - `sources`: Retrieved source documents
    - `done`: Completion with quality metrics
    - `error`: Error information if generation fails

    Each event is formatted as Server-Sent Event (SSE):
    ```
    data: {"type": "content", "text": "chunk", "index": 0}

    ```
    """,
)
async def query_generate_stream(request: QueryRequest) -> StreamingResponse:
    """
    Generate content using RAG with streaming response.

    Args:
        request: Query parameters including query text, audience, section, tone, etc.

    Returns:
        StreamingResponse with Server-Sent Events (SSE) format

    Raises:
        HTTPException: If request is invalid
    """
    try:
        # Validate request
        if not request.query or not request.query.strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Query text is required"
            )

        return StreamingResponse(
            generate_stream(request),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",  # Disable nginx buffering
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Streaming setup failed: {str(e)}"
        )
