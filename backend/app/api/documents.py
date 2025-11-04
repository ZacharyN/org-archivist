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
from fastapi import APIRouter, File, Form, UploadFile, HTTPException, Query, status, Depends
from uuid import uuid4, UUID
from datetime import datetime
import json
import logging

from ..models.document import (
    DocumentMetadata,
    DocumentUploadResponse,
    DocumentInfo,
    DocumentListResponse,
    DocumentFilters,
    DocumentStats,
)
from ..models.common import ErrorResponse
from ..dependencies import get_processor, get_database
from ..services.document_processor import DocumentProcessor
from ..services.database import DatabaseService

router = APIRouter(prefix="/api/documents", tags=["Document Management"])
logger = logging.getLogger(__name__)


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
    sensitivity_confirmed: bool = Form(..., description="Confirmation that document sensitivity has been reviewed"),
    processor: DocumentProcessor = Depends(get_processor),
    db: DatabaseService = Depends(get_database),
) -> DocumentUploadResponse:
    """
    Upload and process a document.

    Args:
        file: Uploaded file
        metadata: JSON string with DocumentMetadata
        sensitivity_confirmed: Confirmation that document is appropriate for upload
        processor: Document processor service (injected)
        db: Database service (injected)

    Returns:
        DocumentUploadResponse with doc_id and processing details

    Raises:
        HTTPException: If file is invalid or processing fails
    """
    start_time = datetime.utcnow()
    logger.info(f"Starting document upload: {file.filename}")

    try:
        # Validate sensitivity confirmation (Phase 5: Security validation)
        if not sensitivity_confirmed:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "error": "Sensitivity confirmation required",
                    "message": "Only upload public-facing documents. Do not upload confidential, financial, or sensitive operational documents.",
                    "action": "Please confirm that this document is appropriate for upload."
                }
            )

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
        allowed_types = [
            "application/pdf",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            "text/plain"
        ]
        allowed_extensions = [".pdf", ".docx", ".txt"]

        if file.content_type not in allowed_types and not any(
            file.filename.endswith(ext) for ext in allowed_extensions
        ):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unsupported file type. Allowed: PDF, DOCX, TXT"
            )

        # Read file content
        content = await file.read()
        file_size = len(content)

        # Check file size (10MB limit)
        MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
        if file_size > MAX_FILE_SIZE:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"File too large ({file_size} bytes). Maximum: {MAX_FILE_SIZE} bytes (10MB)"
            )

        if file_size == 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="File is empty"
            )

        logger.info(f"Processing document: {file.filename} ({file_size} bytes)")

        # Process document through full pipeline
        # This includes: text extraction -> chunking -> embedding -> vector storage
        result = await processor.process_document(
            file_content=content,
            filename=file.filename,
            metadata=doc_metadata.model_dump()
        )

        if not result.success:
            logger.error(f"Document processing failed: {result.error}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Document processing failed: {result.error}"
            )

        doc_id = UUID(result.doc_id)
        logger.info(
            f"Document processed successfully: {doc_id} "
            f"({result.chunks_created} chunks created)"
        )

        # Save document metadata to PostgreSQL
        try:
            await db.insert_document(
                doc_id=doc_id,
                filename=file.filename,
                doc_type=doc_metadata.doc_type,
                year=doc_metadata.year,
                outcome=doc_metadata.outcome,
                notes=doc_metadata.notes,
                file_size=file_size,
                chunks_count=result.chunks_created,
                programs=doc_metadata.programs,
                tags=doc_metadata.tags,
                created_by=None,  # TODO: Add user authentication
                # Phase 5: Document sensitivity fields
                is_sensitive=False,  # Default to false for confirmed public documents
                sensitivity_level="low",  # Default to low for public documents
                sensitivity_confirmed_at=datetime.utcnow(),
                sensitivity_confirmed_by=None,  # TODO: Add user ID when auth is implemented
            )
            logger.info(f"Document metadata saved to database: {doc_id}")
        except Exception as db_error:
            logger.error(f"Failed to save document metadata: {db_error}")
            # Attempt to clean up vector store
            try:
                from ..services.vector_store import get_vector_store
                vector_store = get_vector_store()
                await vector_store.delete_document(str(doc_id))
                logger.info(f"Cleaned up vector store after database failure: {doc_id}")
            except Exception as cleanup_error:
                logger.error(f"Failed to cleanup vector store: {cleanup_error}")

            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to save document metadata: {str(db_error)}"
            )

        elapsed = (datetime.utcnow() - start_time).total_seconds()
        logger.info(
            f"Document upload complete: {doc_id} "
            f"(elapsed: {elapsed:.2f}s)"
        )

        return DocumentUploadResponse(
            success=True,
            doc_id=str(doc_id),
            filename=file.filename,
            chunks_created=result.chunks_created,
            message=result.message
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error during document upload: {str(e)}", exc_info=True)
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
    db: DatabaseService = Depends(get_database),
) -> DocumentListResponse:
    """
    List documents with optional filtering.

    Args:
        doc_type: Filter by document type
        year: Filter by year
        program: Filter by program (not implemented yet - requires join)
        outcome: Filter by outcome
        search: Search term for filename
        skip: Pagination offset
        limit: Page size
        db: Database service (injected)

    Returns:
        DocumentListResponse with filtered documents
    """
    try:
        # Get documents from database
        documents_list = await db.list_documents(
            skip=skip,
            limit=limit,
            doc_type=doc_type,
            year=year,
            outcome=outcome,
            search=search,
        )

        # TODO: Implement program filtering (requires JOIN with document_programs)
        # For now, filter in memory if program is specified
        if program:
            documents_list = [
                doc for doc in documents_list
                if program in doc.get("programs", [])
            ]

        # Get total count
        stats = await db.get_stats()
        total = stats["total_documents"]

        # Convert to DocumentInfo models
        documents = [
            DocumentInfo(
                doc_id=doc["doc_id"],
                filename=doc["filename"],
                doc_type=doc["doc_type"],
                year=doc["year"],
                programs=doc.get("programs", []),
                tags=doc.get("tags", []),
                outcome=doc["outcome"],
                chunks_count=doc["chunks_count"],
                upload_date=datetime.fromisoformat(doc["upload_date"]),
                file_size=doc["file_size"],
            )
            for doc in documents_list
        ]

        return DocumentListResponse(
            documents=documents,
            total=total,
            filtered=len(documents),
        )

    except Exception as e:
        logger.error(f"Failed to list documents: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve documents: {str(e)}"
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
async def get_stats(
    db: DatabaseService = Depends(get_database),
) -> DocumentStats:
    """
    Get document library statistics.

    Args:
        db: Database service (injected)

    Returns:
        DocumentStats with library statistics
    """
    try:
        stats = await db.get_stats()

        return DocumentStats(
            total_documents=stats["total_documents"],
            total_chunks=stats["total_chunks"],
            by_type=stats["by_type"],
            by_year=stats["by_year"],
            by_outcome=stats["by_outcome"],
            avg_chunks_per_doc=stats["avg_chunks_per_doc"],
        )

    except Exception as e:
        logger.error(f"Failed to get stats: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve statistics: {str(e)}"
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
async def get_document(
    doc_id: str,
    db: DatabaseService = Depends(get_database),
) -> DocumentInfo:
    """
    Get document details by ID.

    Args:
        doc_id: Document identifier
        db: Database service (injected)

    Returns:
        DocumentInfo with full document details

    Raises:
        HTTPException: If document not found
    """
    try:
        doc_uuid = UUID(doc_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid document ID format: {doc_id}"
        )

    try:
        doc = await db.get_document(doc_uuid)

        if not doc:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Document {doc_id} not found"
            )

        return DocumentInfo(
            doc_id=doc["doc_id"],
            filename=doc["filename"],
            doc_type=doc["doc_type"],
            year=doc["year"],
            programs=doc.get("programs", []),
            tags=doc.get("tags", []),
            outcome=doc["outcome"],
            chunks_count=doc["chunks_count"],
            upload_date=datetime.fromisoformat(doc["upload_date"]),
            file_size=doc["file_size"],
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get document {doc_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve document: {str(e)}"
        )


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
async def delete_document(
    doc_id: str,
    db: DatabaseService = Depends(get_database),
) -> dict:
    """
    Delete a document.

    Args:
        doc_id: Document identifier
        db: Database service (injected)

    Returns:
        Success message

    Raises:
        HTTPException: If document not found or deletion fails
    """
    try:
        doc_uuid = UUID(doc_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid document ID format: {doc_id}"
        )

    try:
        # Get document info before deletion
        doc = await db.get_document(doc_uuid)

        if not doc:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Document {doc_id} not found"
            )

        filename = doc["filename"]
        chunks_count = doc["chunks_count"]

        # Delete from vector database
        from ..dependencies import get_vector_store
        vector_store = get_vector_store()
        await vector_store.delete_document(doc_id)
        logger.info(f"Deleted chunks from vector store: {doc_id}")

        # Delete from PostgreSQL
        deleted = await db.delete_document(doc_uuid)

        if not deleted:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Document {doc_id} not found"
            )

        logger.info(f"Deleted document from database: {doc_id}")

        return {
            "success": True,
            "message": f"Document '{filename}' deleted successfully",
            "doc_id": doc_id,
            "chunks_deleted": chunks_count,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete document {doc_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Document deletion failed: {str(e)}"
        )
