"""
Document Processing Service

This module provides the core document processing pipeline for the Org Archivist system.
It handles text extraction from various file formats (PDF, DOCX, TXT), semantic chunking,
metadata extraction, and storage in the vector database.

Architecture follows the factory pattern for different file type processors.
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


class FileType(Enum):
    """Supported file types for document processing"""
    PDF = "pdf"
    DOCX = "docx"
    TXT = "txt"


@dataclass
class ProcessingResult:
    """Result of document processing operation"""
    success: bool
    doc_id: str
    chunks_created: int
    message: str
    error: Optional[str] = None


@dataclass
class DocumentChunk:
    """Represents a single chunk of document text"""
    chunk_id: str
    text: str
    chunk_index: int
    metadata: Dict
    embedding: Optional[List[float]] = None


class TextExtractor(ABC):
    """Abstract base class for text extraction"""

    @abstractmethod
    def extract(self, content: bytes, filename: str) -> str:
        """
        Extract text from file content

        Args:
            content: Raw file bytes
            filename: Original filename (for context/error messages)

        Returns:
            Extracted text as string

        Raises:
            ValueError: If extraction fails
        """
        pass

    @abstractmethod
    def validate(self, content: bytes) -> Tuple[bool, Optional[str]]:
        """
        Validate that content can be processed

        Args:
            content: Raw file bytes

        Returns:
            Tuple of (is_valid, error_message)
        """
        pass


class DocumentProcessor:
    """
    Main document processing orchestrator

    Coordinates the document processing pipeline:
    1. Extract text from file (via appropriate TextExtractor)
    2. Classify document type
    3. Enrich metadata from content
    4. Create semantic chunks
    5. Generate embeddings
    6. Store in vector database

    Uses factory pattern to select appropriate text extractor based on file type.
    """

    def __init__(
        self,
        vector_store,  # Will be VectorStore instance (to be implemented)
        embedding_model,  # Will be EmbeddingModel instance
        chunking_service=None,  # ChunkingService instance (recommended)
        node_parser=None,  # DEPRECATED: Will be NodeParser instance (LlamaIndex)
    ):
        """
        Initialize document processor

        Args:
            vector_store: Vector database client for storing embeddings
            embedding_model: Model for generating embeddings
            chunking_service: ChunkingService instance for semantic chunking (recommended)
            node_parser: DEPRECATED - Use chunking_service instead
        """
        self.vector_store = vector_store
        self.embedding_model = embedding_model
        self.chunking_service = chunking_service
        self.node_parser = node_parser  # Keep for backward compatibility

        # Registry of text extractors (to be populated with actual implementations)
        self._text_extractors: Dict[FileType, TextExtractor] = {}

        logger.info("DocumentProcessor initialized")

    def register_extractor(self, file_type: FileType, extractor: TextExtractor) -> None:
        """
        Register a text extractor for a file type

        Args:
            file_type: File type enum value
            extractor: TextExtractor implementation
        """
        self._text_extractors[file_type] = extractor
        logger.debug(f"Registered extractor for {file_type.value}")

    async def process_document(
        self,
        file_content: bytes,
        filename: str,
        metadata: Dict,
    ) -> ProcessingResult:
        """
        Main processing pipeline for document ingestion

        Args:
            file_content: Raw file bytes
            filename: Original filename
            metadata: Document metadata (doc_type, year, programs, etc.)

        Returns:
            ProcessingResult with success status and details

        Raises:
            ValueError: If file type is unsupported or processing fails
        """
        try:
            logger.info(f"Processing document: {filename}")

            # 1. Determine file type and get extractor
            file_type = self._get_file_type(filename)
            extractor = self._get_extractor(file_type)

            # 2. Validate file content
            is_valid, error_msg = extractor.validate(file_content)
            if not is_valid:
                return ProcessingResult(
                    success=False,
                    doc_id="",
                    chunks_created=0,
                    message="Validation failed",
                    error=error_msg
                )

            # 3. Extract text
            text = await self._extract_text(extractor, file_content, filename)
            logger.debug(f"Extracted {len(text)} characters from {filename}")

            # 4. Classify document (enhance doc_type if needed)
            doc_type = self._classify_document(text, metadata)

            # 5. Enrich metadata from content (includes file properties, structure, filename parsing)
            enriched_metadata = self._enrich_metadata(
                text,
                metadata,
                filename,
                file_content=file_content,
                file_extractor=extractor
            )

            # 6. Create document chunks
            chunks = await self._chunk_document(text, enriched_metadata)
            logger.info(f"Created {len(chunks)} chunks from {filename}")

            # 7. Generate embeddings for each chunk
            await self._generate_embeddings(chunks)

            # 8. Store in vector database
            await self._store_chunks(chunks)

            doc_id = enriched_metadata.get('doc_id', 'unknown')

            return ProcessingResult(
                success=True,
                doc_id=doc_id,
                chunks_created=len(chunks),
                message=f"Successfully processed {filename}",
                error=None
            )

        except Exception as e:
            logger.error(f"Error processing {filename}: {str(e)}", exc_info=True)
            return ProcessingResult(
                success=False,
                doc_id="",
                chunks_created=0,
                message="Processing failed",
                error=str(e)
            )

    def _get_file_type(self, filename: str) -> FileType:
        """
        Determine file type from filename extension

        Args:
            filename: Name of file

        Returns:
            FileType enum value

        Raises:
            ValueError: If file extension is not supported
        """
        extension = Path(filename).suffix.lower().lstrip('.')

        try:
            return FileType(extension)
        except ValueError:
            raise ValueError(
                f"Unsupported file type: .{extension}. "
                f"Supported types: {', '.join(ft.value for ft in FileType)}"
            )

    def _get_extractor(self, file_type: FileType) -> TextExtractor:
        """
        Get appropriate text extractor for file type

        Args:
            file_type: Type of file to process

        Returns:
            TextExtractor instance

        Raises:
            ValueError: If no extractor registered for file type
        """
        extractor = self._text_extractors.get(file_type)
        if not extractor:
            raise ValueError(
                f"No extractor registered for {file_type.value}. "
                "Use register_extractor() to add one."
            )
        return extractor

    async def _extract_text(
        self,
        extractor: TextExtractor,
        content: bytes,
        filename: str
    ) -> str:
        """
        Extract text using appropriate extractor

        Args:
            extractor: TextExtractor instance
            content: File bytes
            filename: Original filename

        Returns:
            Extracted text
        """
        return extractor.extract(content, filename)

    def _classify_document(self, text: str, metadata: Dict) -> str:
        """
        Auto-classify or enhance document type classification

        This is a placeholder for more sophisticated classification logic.
        Could use LLM or ML model to determine document type from content.

        Args:
            text: Extracted document text
            metadata: Provided metadata

        Returns:
            Document type classification
        """
        # For now, trust user-provided doc_type
        # Future: Use LLM or keyword matching to auto-classify
        doc_type = metadata.get('doc_type', 'Unknown')

        logger.debug(f"Document classified as: {doc_type}")
        return doc_type

    def _enrich_metadata(
        self,
        text: str,
        metadata: Dict,
        filename: str,
        file_content: Optional[bytes] = None,
        file_extractor: Optional[TextExtractor] = None
    ) -> Dict:
        """
        Enrich metadata with information extracted from content

        Uses MetadataExtractor to extract comprehensive metadata from:
        - File properties (size, dates)
        - Document structure (page count, word count)
        - Filename patterns
        - File-specific metadata (PDF/DOCX properties)

        Args:
            text: Document text
            metadata: Original metadata
            filename: Filename
            file_content: Raw file bytes (optional, for file property extraction)
            file_extractor: File-specific extractor (optional, for PDF/DOCX metadata)

        Returns:
            Enriched metadata dictionary
        """
        # Import here to avoid circular dependency
        from .metadata_extractor import MetadataExtractorFactory

        # Create metadata extractor
        extractor = MetadataExtractorFactory.create_extractor()

        # Extract comprehensive metadata
        extracted = extractor.extract(
            user_metadata=metadata,
            file_content=file_content or b'',
            filename=filename,
            text=text,
            file_extractor=file_extractor
        )

        # Convert to dictionary
        enriched = extracted.to_dict()

        # Validate metadata
        is_valid, warnings = extractor.validate_metadata(extracted)
        if not is_valid:
            logger.warning(f"Metadata validation warnings for {filename}: {warnings}")
            enriched['validation_warnings'] = warnings

        logger.info(f"Metadata enrichment complete for {filename}")

        return enriched

    async def _chunk_document(
        self,
        text: str,
        metadata: Dict
    ) -> List[DocumentChunk]:
        """
        Split document into semantic chunks

        Uses configured chunking service (ChunkingService with LlamaIndex)

        Args:
            text: Full document text
            metadata: Document metadata

        Returns:
            List of DocumentChunk objects
        """
        # Use chunking service if available, otherwise fallback
        if self.chunking_service:
            try:
                # Get chunks from chunking service
                chunk_dicts = self.chunking_service.chunk_text(text, metadata)

                # Convert to DocumentChunk objects
                chunks = []
                doc_id = metadata.get('doc_id', 'unknown')

                for chunk_dict in chunk_dicts:
                    chunk = DocumentChunk(
                        chunk_id=f"{doc_id}_{chunk_dict['chunk_index']}",
                        text=chunk_dict['text'],
                        chunk_index=chunk_dict['chunk_index'],
                        metadata=chunk_dict['metadata'],
                        embedding=None
                    )
                    chunks.append(chunk)

                logger.info(f"Chunked via ChunkingService: {len(chunks)} chunks created")
                return chunks

            except Exception as e:
                logger.error(f"Chunking service failed: {e}, using fallback")
                # Fall through to fallback chunking

        # Fallback: simple chunking
        logger.warning("Using fallback chunking (no chunking service available)")
        chunks = []
        chunk_size = 1000  # characters

        for i, start in enumerate(range(0, len(text), chunk_size)):
            chunk_text = text[start:start + chunk_size]
            chunk = DocumentChunk(
                chunk_id=f"{metadata.get('doc_id', 'unknown')}_{i}",
                text=chunk_text,
                chunk_index=i,
                metadata={**metadata, 'chunk_index': i},
                embedding=None
            )
            chunks.append(chunk)

        return chunks

    async def _generate_embeddings(self, chunks: List[DocumentChunk]) -> None:
        """
        Generate embeddings for all chunks

        Modifies chunks in-place, adding embedding vectors

        Args:
            chunks: List of DocumentChunk objects
        """
        if not self.embedding_model:
            logger.warning("No embedding model available, skipping embedding generation")
            return

        if not chunks:
            logger.debug("No chunks to generate embeddings for")
            return

        try:
            # Extract text from all chunks for batch processing
            texts = [chunk.text for chunk in chunks]

            logger.info(f"Generating embeddings for {len(chunks)} chunks using {type(self.embedding_model).__name__}")

            # Generate embeddings in batch for efficiency
            # LlamaIndex embedding models support get_text_embedding_batch()
            embeddings = self.embedding_model.get_text_embedding_batch(texts)

            # Assign embeddings to chunks
            for chunk, embedding in zip(chunks, embeddings):
                chunk.embedding = embedding

            logger.info(f"Successfully generated {len(embeddings)} embeddings (dimensions: {len(embeddings[0]) if embeddings else 0})")

        except Exception as e:
            logger.error(f"Failed to generate embeddings: {e}")
            # Don't fail the entire pipeline - continue with None embeddings
            # This allows the document to be stored even if embedding generation fails
            logger.warning("Continuing without embeddings - chunks will have None embeddings")

    async def _store_chunks(self, chunks: List[DocumentChunk]) -> None:
        """
        Store chunks in vector database

        Args:
            chunks: List of DocumentChunk objects with embeddings
        """
        # This will be implemented when we have vector_store
        # await self.vector_store.add_chunks(chunks)

        logger.debug(f"Stored {len(chunks)} chunks in vector database (placeholder)")


class ProcessorFactory:
    """
    Factory for creating configured DocumentProcessor instances

    Handles dependency injection and configuration
    """

    @staticmethod
    def create_processor(
        vector_store=None,
        embedding_model=None,
        chunking_service=None,
        node_parser=None
    ) -> DocumentProcessor:
        """
        Create a DocumentProcessor with all dependencies

        Args:
            vector_store: Optional vector store instance
            embedding_model: Optional embedding model instance
            chunking_service: Optional ChunkingService instance (recommended)
            node_parser: Optional node parser instance (deprecated)

        Returns:
            Configured DocumentProcessor instance
        """
        processor = DocumentProcessor(
            vector_store=vector_store,
            embedding_model=embedding_model,
            chunking_service=chunking_service,
            node_parser=node_parser
        )

        return processor
