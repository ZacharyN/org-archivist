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
from ..services.generation_service import GenerationService
from ..dependencies import get_engine, get_generator

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
    engine: RetrievalEngine = Depends(get_engine),
    generator: GenerationService = Depends(get_generator)
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

        # 3. Generate response using Claude API
        generation_start = time.time()

        try:
            result = await generator.generate(
                query=request.query,
                sources=sources,
                audience=request.audience,
                section=request.section,
                tone=request.tone,
                include_citations=request.include_citations,
                custom_instructions=request.custom_instructions,
                temperature=request.temperature,
                max_tokens=request.max_tokens
            )

            generated_text = result["text"]
            generation_time = result["generation_time"]
            tokens_used = result["tokens_used"]
            model = result["model"]

            logger.info(
                f"Generated {len(generated_text)} chars in {generation_time:.2f}s, "
                f"{tokens_used} tokens used"
            )

        except Exception as e:
            logger.error(f"Generation failed: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Generation failed: {str(e)}"
            )

        # 4. Validate citations and quality
        quality_issues = []

        if request.include_citations:
            citation_validation = generator.validate_citations(generated_text, sources)

            if not citation_validation["valid"]:
                quality_issues.append(
                    f"Warning: Found {len(citation_validation['invalid_citations'])} "
                    f"invalid citation(s)"
                )

            if citation_validation["uncited_sources"]:
                logger.debug(
                    f"{len(citation_validation['uncited_sources'])} sources were not cited"
                )

        # Calculate confidence score based on various factors
        # Simple heuristic: high if we have sources, citations are valid, and text is substantive
        confidence = 0.8
        if sources:
            confidence += 0.1
        if request.include_citations and citation_validation.get("total_citations", 0) > 0:
            confidence += 0.05
        if len(generated_text) > 200:
            confidence += 0.05
        confidence = min(confidence, 1.0)

        logger.info(f"Response generated with confidence: {confidence:.2f}")

        return QueryResponse(
            text=generated_text,
            sources=sources,
            confidence=confidence,
            quality_issues=quality_issues if quality_issues else None,
            metadata=ResponseMetadata(
                model=model,
                tokens_used=tokens_used,
                generation_time=generation_time,
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
    engine: RetrievalEngine,
    generator: GenerationService
) -> AsyncIterator[str]:
    """
    Async generator for streaming responses.

    Yields Server-Sent Event formatted chunks.

    Args:
        request: Query request parameters
        engine: RetrievalEngine instance
        generator: GenerationService instance
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
            "model": request.max_tokens,
            "sources_count": len(sources),
            "retrieval_time_ms": retrieval_time_ms
        }
        yield f"data: {json.dumps(metadata)}\n\n"

        # 3. Stream generated content using Claude API
        full_text = ""
        tokens_used = 0
        model_name = ""

        try:
            async for event in generator.generate_stream(
                query=request.query,
                sources=sources,
                audience=request.audience,
                section=request.section,
                tone=request.tone,
                include_citations=request.include_citations,
                custom_instructions=request.custom_instructions,
                temperature=request.temperature,
                max_tokens=request.max_tokens
            ):
                # Handle different event types from Claude streaming API
                if event.type == "message_start":
                    # Extract model info
                    model_name = event.message.model
                    logger.debug(f"Streaming started with model: {model_name}")

                elif event.type == "content_block_start":
                    # Content block starting
                    pass

                elif event.type == "content_block_delta":
                    # Stream text delta
                    if hasattr(event.delta, 'text'):
                        text_chunk = event.delta.text
                        full_text += text_chunk

                        chunk = {
                            "type": "content",
                            "text": text_chunk
                        }
                        yield f"data: {json.dumps(chunk)}\n\n"

                elif event.type == "content_block_stop":
                    # Content block complete
                    pass

                elif event.type == "message_delta":
                    # Message metadata update (e.g., stop reason)
                    if hasattr(event, 'usage'):
                        tokens_used = event.usage.output_tokens

                elif event.type == "message_stop":
                    # Stream complete
                    logger.info(f"Streaming complete: {len(full_text)} chars, {tokens_used} tokens")

        except Exception as e:
            logger.error(f"Streaming generation failed: {e}")
            error = {
                "type": "error",
                "message": f"Generation failed: {str(e)}"
            }
            yield f"data: {json.dumps(error)}\n\n"
            return

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

        # 4. Validate citations
        quality_issues = []
        citation_validation = {}

        if request.include_citations:
            citation_validation = generator.validate_citations(full_text, sources)

            if not citation_validation["valid"]:
                quality_issues.append(
                    f"Warning: Found {len(citation_validation['invalid_citations'])} "
                    f"invalid citation(s)"
                )

        # Calculate confidence score
        confidence = 0.8
        if sources:
            confidence += 0.1
        if request.include_citations and citation_validation.get("total_citations", 0) > 0:
            confidence += 0.05
        if len(full_text) > 200:
            confidence += 0.05
        confidence = min(confidence, 1.0)

        # Send completion event
        completion = {
            "type": "done",
            "confidence": confidence,
            "quality_issues": quality_issues if quality_issues else None,
            "tokens_used": tokens_used,
            "model": model_name
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
    data: {"type": "content", "text": "chunk"}

    ```
    """,
)
async def query_generate_stream(
    request: QueryRequest,
    engine: RetrievalEngine = Depends(get_engine),
    generator: GenerationService = Depends(get_generator)
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
            generate_stream(request, engine, generator),
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
