"""
Document Management API endpoints

This module provides endpoints for document upload and management:
- POST /api/documents/upload - Upload and process documents
- GET /api/documents - List all documents with filters
- GET /api/documents/{doc_id} - Get document details
- DELETE /api/documents/{doc_id} - Delete document
- GET /api/documents/stats - Get library statistics
"""

from typing import Optional
from fastapi import APIRouter, File, Form, UploadFile, HTTPException, Query, status
from uuid import uuid4
from datetime import datetime
import json

from ..models.document import (
    DocumentMetadata,
    DocumentUploadResponse,
    DocumentInfo,
    DocumentListResponse,
    DocumentFilters,
    DocumentStats,
)
from ..models.common import ErrorResponse

router = APIRouter(prefix="/api/documents", tags=["Document Management"])


# In-memory document storage (TODO: Replace with database)
documents_store = {}


@router.post(
    "/upload",
    response_model=DocumentUploadResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        400: {"model": ErrorResponse, "description": "Invalid file or metadata"},
        413: {"model": ErrorResponse, "description": "File too large"},
    },
    summary="Upload and process document",
    description="""
    Upload a document with metadata for processing and indexing.

    Accepts:
    - File: PDF, DOCX, or TXT format
    - Metadata: Document classification and tagging information

    The document processing pipeline:
    1. Validate file type and size
    2. Extract text content
    3. Classify document type (if not provided)
    4. Chunk text semantically
    5. Generate embeddings for each chunk
    6. Store chunks in vector database
    7. Save metadata to database

    Returns document ID and number of chunks created.
    """,
)
async def upload_document(
    file: UploadFile = File(..., description="Document file (PDF, DOCX, TXT)"),
    metadata: str = Form(..., description="Document metadata as JSON string"),
) -> DocumentUploadResponse:
    """
    Upload and process a document.

    Args:
        file: Uploaded file
        metadata: JSON string with DocumentMetadata

    Returns:
        DocumentUploadResponse with doc_id and processing details

    Raises:
        HTTPException: If file is invalid or processing fails
    """
    try:
        # Parse metadata
        try:
            metadata_dict = json.loads(metadata)
            doc_metadata = DocumentMetadata(**metadata_dict)
        except json.JSONDecodeError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid metadata JSON"
            )
        except ValueError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid metadata: {str(e)}"
            )

        # Validate file type
        allowed_types = ["application/pdf", "application/vnd.openxmlformats-officedocument.wordprocessingml.document", "text/plain"]
        allowed_extensions = [".pdf", ".docx", ".txt"]

        if file.content_type not in allowed_types and not any(file.filename.endswith(ext) for ext in allowed_extensions):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unsupported file type. Allowed: PDF, DOCX, TXT"
            )

        # TODO: Check file size
        # if file.size > MAX_FILE_SIZE:
        #     raise HTTPException(
        #         status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
        #         detail=f"File too large. Maximum: {MAX_FILE_SIZE} bytes"
        #     )

        # Read file content
        content = await file.read()
        file_size = len(content)

        # Generate document ID
        doc_id = str(uuid4())

        # TODO: Implement actual document processing
        # 1. Extract text
        # processor = get_document_processor()
        # text = await processor.extract_text(content, file.filename)

        # 2. Process document
        # result = await processor.process_document(
        #     file_content=content,
        #     filename=file.filename,
        #     metadata=doc_metadata.dict()
        # )

        # Stub: Simulate processing
        chunks_created = 12  # Simulated chunk count

        # Store document info
        documents_store[doc_id] = DocumentInfo(
            doc_id=doc_id,
            filename=file.filename,
            doc_type=doc_metadata.doc_type,
            year=doc_metadata.year,
            programs=doc_metadata.programs,
            tags=doc_metadata.tags,
            outcome=doc_metadata.outcome,
            chunks_count=chunks_created,
            upload_date=datetime.utcnow(),
            file_size=file_size,
        )

        return DocumentUploadResponse(
            success=True,
            doc_id=doc_id,
            filename=file.filename,
            chunks_created=chunks_created,
            message=f"Document '{file.filename}' uploaded and processed successfully"
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Document processing failed: {str(e)}"
        )


@router.get(
    "",
    response_model=DocumentListResponse,
    summary="List documents",
    description="""
    List all documents with optional filtering and pagination.

    Filters:
    - doc_type: Filter by document type
    - year: Filter by year
    - program: Filter by program
    - outcome: Filter by outcome status
    - search: Search in filename

    Pagination:
    - skip: Number of documents to skip
    - limit: Maximum number of documents to return

    Returns a list of documents with metadata.
    """,
)
async def list_documents(
    doc_type: Optional[str] = Query(None, description="Filter by document type"),
    year: Optional[int] = Query(None, description="Filter by year"),
    program: Optional[str] = Query(None, description="Filter by program"),
    outcome: Optional[str] = Query(None, description="Filter by outcome"),
    search: Optional[str] = Query(None, description="Search in filename"),
    skip: int = Query(0, ge=0, description="Number to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum to return"),
) -> DocumentListResponse:
    """
    List documents with optional filtering.

    Args:
        doc_type: Filter by document type
        year: Filter by year
        program: Filter by program
        outcome: Filter by outcome
        search: Search term for filename
        skip: Pagination offset
        limit: Page size

    Returns:
        DocumentListResponse with filtered documents
    """
    documents = list(documents_store.values())

    # Apply filters
    if doc_type:
        documents = [d for d in documents if d.doc_type == doc_type]

    if year:
        documents = [d for d in documents if d.year == year]

    if program:
        documents = [d for d in documents if program in d.programs]

    if outcome:
        documents = [d for d in documents if d.outcome == outcome]

    if search:
        search_lower = search.lower()
        documents = [d for d in documents if search_lower in d.filename.lower()]

    filtered_count = len(documents)

    # Apply pagination
    documents = documents[skip : skip + limit]

    return DocumentListResponse(
        documents=documents,
        total=len(documents_store),
        filtered=filtered_count,
    )


@router.get(
    "/stats",
    response_model=DocumentStats,
    summary="Get library statistics",
    description="""
    Get statistical information about the document library.

    Returns:
    - Total document and chunk counts
    - Distribution by document type
    - Distribution by year
    - Distribution by outcome
    - Average chunks per document

    Useful for dashboard displays and library health monitoring.
    """,
)
async def get_stats() -> DocumentStats:
    """
    Get document library statistics.

    Returns:
        DocumentStats with library statistics
    """
    documents = list(documents_store.values())

    if not documents:
        return DocumentStats(
            total_documents=0,
            total_chunks=0,
            by_type={},
            by_year={},
            by_outcome={},
            avg_chunks_per_doc=0.0,
        )

    # Calculate statistics
    total_documents = len(documents)
    total_chunks = sum(d.chunks_count for d in documents)

    # Count by type
    by_type = {}
    for doc in documents:
        by_type[doc.doc_type] = by_type.get(doc.doc_type, 0) + 1

    # Count by year
    by_year = {}
    for doc in documents:
        by_year[doc.year] = by_year.get(doc.year, 0) + 1

    # Count by outcome
    by_outcome = {}
    for doc in documents:
        by_outcome[doc.outcome] = by_outcome.get(doc.outcome, 0) + 1

    # Calculate average
    avg_chunks = total_chunks / total_documents if total_documents > 0 else 0.0

    return DocumentStats(
        total_documents=total_documents,
        total_chunks=total_chunks,
        by_type=by_type,
        by_year=by_year,
        by_outcome=by_outcome,
        avg_chunks_per_doc=round(avg_chunks, 2),
    )


@router.get(
    "/{doc_id}",
    response_model=DocumentInfo,
    responses={
        404: {"model": ErrorResponse, "description": "Document not found"},
    },
    summary="Get document details",
    description="Retrieve detailed information about a specific document",
)
async def get_document(doc_id: str) -> DocumentInfo:
    """
    Get document details by ID.

    Args:
        doc_id: Document identifier

    Returns:
        DocumentInfo with full document details

    Raises:
        HTTPException: If document not found
    """
    if doc_id not in documents_store:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document {doc_id} not found"
        )

    return documents_store[doc_id]


@router.delete(
    "/{doc_id}",
    responses={
        404: {"model": ErrorResponse, "description": "Document not found"},
    },
    summary="Delete document",
    description="""
    Delete a document and all associated data.

    This will:
    - Remove document metadata from database
    - Delete all chunks from vector database
    - Remove the original file (if stored)

    This action cannot be undone.
    """,
)
async def delete_document(doc_id: str) -> dict:
    """
    Delete a document.

    Args:
        doc_id: Document identifier

    Returns:
        Success message

    Raises:
        HTTPException: If document not found or deletion fails
    """
    if doc_id not in documents_store:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document {doc_id} not found"
        )

    try:
        document = documents_store[doc_id]

        # TODO: Delete from vector database
        # vector_store = get_vector_store()
        # await vector_store.delete_by_doc_id(doc_id)

        # TODO: Delete file from storage if applicable
        # file_storage = get_file_storage()
        # await file_storage.delete(doc_id)

        # Delete from metadata store
        del documents_store[doc_id]

        return {
            "success": True,
            "message": f"Document '{document.filename}' deleted successfully",
            "doc_id": doc_id,
            "chunks_deleted": document.chunks_count,
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Document deletion failed: {str(e)}"
        )
