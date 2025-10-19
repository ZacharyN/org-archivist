"""
Query and Generation API endpoints

This module provides endpoints for content generation using RAG:
- POST /api/query - Non-streaming generation
- POST /api/query/stream - Streaming generation with Server-Sent Events
"""

import time
import logging
from typing import AsyncIterator, List
from fastapi import APIRouter, HTTPException, status, Depends
from fastapi.responses import StreamingResponse
import json
import asyncio

from ..models.query import QueryRequest, QueryResponse, Source, ResponseMetadata
from ..models.common import ErrorResponse
from ..services.retrieval_engine import RetrievalEngine, RetrievalResult
from ..dependencies import get_engine

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/query", tags=["Query & Generation"])


def convert_results_to_sources(results: List[RetrievalResult]) -> List[Source]:
    """
    Convert RetrievalResult objects to Source objects for API response

    Args:
        results: List of RetrievalResult from retrieval engine

    Returns:
        List of Source objects with citation numbers
    """
    sources = []

    for i, result in enumerate(results):
        # Extract metadata fields with defaults
        filename = result.metadata.get("filename", f"doc_{result.doc_id}")
        doc_type = result.metadata.get("doc_type", "Unknown")
        year = result.metadata.get("year", None)

        # Create Source object
        source = Source(
            id=i + 1,  # Citation number (1-indexed)
            filename=filename,
            doc_type=doc_type,
            year=year,
            excerpt=result.text[:500],  # Limit excerpt length
            relevance=result.score,
            chunk_index=result.chunk_index
        )
        sources.append(source)

    return sources


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
async def query_generate(
    request: QueryRequest,
    engine: RetrievalEngine = Depends(get_engine)
) -> QueryResponse:
    """
    Generate content using RAG (non-streaming).

    Args:
        request: Query parameters including query text, audience, section, tone, etc.
        engine: RetrievalEngine instance (injected)

    Returns:
        QueryResponse with generated text, sources, confidence score, and metadata

    Raises:
        HTTPException: If generation fails or request is invalid
    """
    try:
        # 1. Validate request
        if not request.query or not request.query.strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Query text is required"
            )

        logger.info(f"Query request: {request.query[:100]}...")
        logger.info(f"Audience: {request.audience}, Section: {request.section}")

        # 2. Retrieve relevant context using RetrievalEngine
        retrieval_start = time.time()

        try:
            results = await engine.retrieve(
                query=request.query,
                top_k=request.max_sources,
                filters=request.filters,
                recency_weight=request.recency_weight
            )
            retrieval_time_ms = (time.time() - retrieval_start) * 1000

            logger.info(
                f"Retrieved {len(results)} chunks in {retrieval_time_ms:.1f}ms"
            )

            # Convert results to sources
            sources = convert_results_to_sources(results)

        except Exception as e:
            logger.error(f"Retrieval failed: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Retrieval failed: {str(e)}"
            )

        # 3. Generate response using Claude (TODO: implement generation service)
        generation_start = time.time()

        # STUB: Claude generation will be implemented in a separate task
        # For now, create a stub response that shows the retrieved context
        context_preview = "\n\n".join([
            f"[{s.id}] {s.filename} ({s.doc_type}, {s.year}):\n{s.excerpt[:200]}..."
            for s in sources[:3]
        ])

        stub_text = f"""Based on the query "{request.query}", here is generated content for {request.audience} audience in {request.tone} tone.

This is a stub response showing that the RAG retrieval pipeline is working. The Claude generation service will be implemented in a separate task.

Retrieved Context ({len(sources)} sources):
{context_preview}

The full response would include:
- Audience-appropriate language ({request.audience})
- Section-specific structure ({request.section})
- Proper tone ({request.tone})
- Content synthesized from the {len(sources)} retrieved sources
- Inline citations {'[1], [2], etc.' if request.include_citations else '(citations disabled)'}

Note: The actual Claude API integration for content generation is pending implementation.
"""
        generation_time_ms = (time.time() - generation_start) * 1000

        # 4. Validate quality (TODO: implement quality validator)
        # validator = get_quality_validator()
        # validation = validator.validate(...)

        logger.info(f"Response generated in {generation_time_ms:.1f}ms")

        return QueryResponse(
            text=stub_text,
            sources=sources,
            confidence=0.85,  # Stub confidence
            quality_issues=[
                "Note: Using stub generation. Claude API integration pending."
            ],
            metadata=ResponseMetadata(
                model="claude-sonnet-4.5-stub",
                tokens_used=0,  # TODO: count actual tokens
                generation_time=generation_time_ms / 1000,  # Convert to seconds
                temperature=request.temperature
            )
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Query generation failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Generation failed: {str(e)}"
        )


async def generate_stream(
    request: QueryRequest,
    engine: RetrievalEngine
) -> AsyncIterator[str]:
    """
    Async generator for streaming responses.

    Yields Server-Sent Event formatted chunks.

    Args:
        request: Query request parameters
        engine: RetrievalEngine instance
    """
    try:
        logger.info(f"Streaming query request: {request.query[:100]}...")

        # 1. Retrieve context (non-streaming)
        retrieval_start = time.time()

        try:
            results = await engine.retrieve(
                query=request.query,
                top_k=request.max_sources,
                filters=request.filters,
                recency_weight=request.recency_weight
            )
            retrieval_time_ms = (time.time() - retrieval_start) * 1000

            # Convert to sources
            sources = convert_results_to_sources(results)

            logger.info(
                f"Retrieved {len(sources)} sources in {retrieval_time_ms:.1f}ms"
            )

        except Exception as e:
            logger.error(f"Retrieval failed: {e}")
            error = {
                "type": "error",
                "message": f"Retrieval failed: {str(e)}"
            }
            yield f"data: {json.dumps(error)}\n\n"
            return

        # 2. Send metadata first
        metadata = {
            "type": "metadata",
            "model": "claude-sonnet-4.5-stub",
            "sources_count": len(sources),
            "retrieval_time_ms": retrieval_time_ms
        }
        yield f"data: {json.dumps(metadata)}\n\n"

        # 3. Stream generated content
        # TODO: Implement actual Claude streaming API integration
        # For now, show retrieved context in a streaming manner

        context_preview = f"""Based on the query "{request.query}", here is generated content for {request.audience} audience.

This is a stub streaming response showing that RAG retrieval is working. The Claude streaming API integration will be implemented in a separate task.

Retrieved {len(sources)} relevant sources:

"""
        # Stream the intro
        words = context_preview.split()
        for i, word in enumerate(words):
            chunk = {
                "type": "content",
                "text": word + " ",
                "index": i
            }
            yield f"data: {json.dumps(chunk)}\n\n"
            await asyncio.sleep(0.01)  # Fast streaming for demo

        # Stream each source preview
        for source in sources[:3]:  # Show first 3 sources
            source_text = f"\n\n[{source.id}] {source.filename} ({source.doc_type}, {source.year}):\n{source.excerpt[:200]}...\n"
            words = source_text.split()
            for word in words:
                chunk = {
                    "type": "content",
                    "text": word + " ",
                    "index": 0
                }
                yield f"data: {json.dumps(chunk)}\n\n"
                await asyncio.sleep(0.01)

        # Send sources metadata
        sources_data = {
            "type": "sources",
            "sources": [
                {
                    "id": s.id,
                    "filename": s.filename,
                    "doc_type": s.doc_type,
                    "year": s.year,
                    "excerpt": s.excerpt[:300],
                    "relevance": s.relevance,
                    "chunk_index": s.chunk_index
                }
                for s in sources
            ]
        }
        yield f"data: {json.dumps(sources_data)}\n\n"

        # Send completion event
        completion = {
            "type": "done",
            "confidence": 0.85,
            "quality_issues": [
                "Note: Using stub generation. Claude streaming API integration pending."
            ]
        }
        yield f"data: {json.dumps(completion)}\n\n"

    except Exception as e:
        logger.error(f"Streaming generation failed: {e}", exc_info=True)
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
async def query_generate_stream(
    request: QueryRequest,
    engine: RetrievalEngine = Depends(get_engine)
) -> StreamingResponse:
    """
    Generate content using RAG with streaming response.

    Args:
        request: Query parameters including query text, audience, section, tone, etc.
        engine: RetrievalEngine instance (injected)

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

        logger.info(f"Starting streaming response for query: {request.query[:100]}...")

        return StreamingResponse(
            generate_stream(request, engine),
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
        logger.error(f"Streaming setup failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Streaming setup failed: {str(e)}"
        )
