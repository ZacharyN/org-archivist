"""
Qdrant Vector Store Service

Handles all interactions with Qdrant vector database:
- Storing document chunks with embeddings
- Retrieving similar chunks via vector search
- Managing collections
- Deleting documents and their chunks
"""
import logging
from typing import List, Dict, Optional, Any
from dataclasses import dataclass
from uuid import uuid4

from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance,
    VectorParams,
    PointStruct,
    Filter,
    FieldCondition,
    MatchValue,
    SearchRequest,
)
from qdrant_client.http import models

from app.config import settings

logger = logging.getLogger(__name__)


@dataclass
class VectorStoreConfig:
    """Configuration for Qdrant vector store"""
    host: str
    port: int
    grpc_port: int
    collection_name: str
    vector_size: int
    distance: Distance = Distance.COSINE
    api_key: Optional[str] = None
    timeout: int = 60
    prefer_grpc: bool = True


class QdrantStore:
    """
    Qdrant vector store implementation

    Manages document chunks in Qdrant vector database with:
    - Automatic collection creation
    - Batch operations for efficiency
    - Metadata filtering
    - Connection management with health checks
    """

    def __init__(self, config: Optional[VectorStoreConfig] = None):
        """
        Initialize Qdrant client

        Args:
            config: Optional VectorStoreConfig. If None, loads from settings
        """
        self.config = config or self._load_default_config()
        self.client = self._create_client()
        self.collection_name = self.config.collection_name

        logger.info(
            f"QdrantStore initialized: {self.config.host}:{self.config.port}, "
            f"collection={self.collection_name}"
        )

    def _load_default_config(self) -> VectorStoreConfig:
        """Load configuration from settings"""
        return VectorStoreConfig(
            host=settings.qdrant_host,
            port=settings.qdrant_port,
            grpc_port=settings.qdrant_grpc_port,
            collection_name=settings.qdrant_collection_name,
            vector_size=settings.embedding_dimensions,
            api_key=settings.qdrant_api_key,
        )

    def _create_client(self) -> QdrantClient:
        """
        Create Qdrant client with connection error handling

        Returns:
            Configured QdrantClient instance

        Raises:
            ConnectionError: If unable to connect to Qdrant
        """
        try:
            # Determine connection method
            if self.config.api_key:
                # Cloud connection
                client = QdrantClient(
                    url=f"https://{self.config.host}",
                    api_key=self.config.api_key,
                    timeout=self.config.timeout,
                    prefer_grpc=self.config.prefer_grpc,
                )
            else:
                # Local connection
                client = QdrantClient(
                    host=self.config.host,
                    port=self.config.port,
                    grpc_port=self.config.grpc_port,
                    timeout=self.config.timeout,
                    prefer_grpc=self.config.prefer_grpc,
                )

            # Test connection
            client.get_collections()
            logger.debug("Successfully connected to Qdrant")

            return client

        except Exception as e:
            error_msg = f"Failed to connect to Qdrant at {self.config.host}:{self.config.port}: {str(e)}"
            logger.error(error_msg)
            raise ConnectionError(error_msg) from e

    def ensure_collection_exists(self) -> bool:
        """
        Ensure collection exists, create if not

        Returns:
            True if collection exists or was created successfully

        Raises:
            RuntimeError: If collection creation fails
        """
        try:
            # Check if collection exists
            collections = self.client.get_collections().collections
            collection_names = [col.name for col in collections]

            if self.collection_name in collection_names:
                logger.debug(f"Collection '{self.collection_name}' already exists")
                return True

            # Create collection
            logger.info(f"Creating collection '{self.collection_name}'")
            self.client.create_collection(
                collection_name=self.collection_name,
                vectors_config=VectorParams(
                    size=self.config.vector_size,
                    distance=self.config.distance,
                ),
            )

            logger.info(f"Collection '{self.collection_name}' created successfully")
            return True

        except Exception as e:
            error_msg = f"Failed to ensure collection exists: {str(e)}"
            logger.error(error_msg)
            raise RuntimeError(error_msg) from e

    async def store_chunks(
        self,
        chunks: List[Dict[str, Any]],
        batch_size: int = 100
    ) -> Dict[str, Any]:
        """
        Store document chunks with embeddings in Qdrant

        Args:
            chunks: List of chunk dictionaries with keys:
                - chunk_id: Unique chunk identifier
                - text: Chunk text content
                - embedding: Vector embedding (list of floats)
                - metadata: Dict of metadata (doc_id, chunk_index, etc.)
            batch_size: Number of chunks to upload per batch

        Returns:
            Dict with status and stats:
                - success: bool
                - chunks_stored: int
                - collection: str
                - message: str

        Raises:
            ValueError: If chunks are invalid
            RuntimeError: If storage operation fails
        """
        if not chunks:
            return {
                "success": True,
                "chunks_stored": 0,
                "collection": self.collection_name,
                "message": "No chunks to store"
            }

        try:
            # Ensure collection exists
            self.ensure_collection_exists()

            # Validate chunks
            self._validate_chunks(chunks)

            # Prepare points for batch upload
            points = []
            for chunk in chunks:
                point = PointStruct(
                    id=chunk.get("chunk_id", str(uuid4())),
                    vector=chunk["embedding"],
                    payload={
                        "text": chunk["text"],
                        **chunk.get("metadata", {})
                    }
                )
                points.append(point)

            # Upload in batches
            total_stored = 0
            for i in range(0, len(points), batch_size):
                batch = points[i:i + batch_size]
                self.client.upsert(
                    collection_name=self.collection_name,
                    points=batch,
                )
                total_stored += len(batch)
                logger.debug(f"Uploaded batch {i // batch_size + 1}: {len(batch)} chunks")

            logger.info(f"Successfully stored {total_stored} chunks in '{self.collection_name}'")

            return {
                "success": True,
                "chunks_stored": total_stored,
                "collection": self.collection_name,
                "message": f"Stored {total_stored} chunks successfully"
            }

        except ValueError as e:
            logger.error(f"Validation error: {str(e)}")
            raise
        except Exception as e:
            error_msg = f"Failed to store chunks: {str(e)}"
            logger.error(error_msg)
            raise RuntimeError(error_msg) from e

    def _validate_chunks(self, chunks: List[Dict[str, Any]]) -> None:
        """
        Validate chunk structure

        Args:
            chunks: List of chunk dictionaries

        Raises:
            ValueError: If chunks are invalid
        """
        for i, chunk in enumerate(chunks):
            if "embedding" not in chunk:
                raise ValueError(f"Chunk {i} missing 'embedding' field")

            if "text" not in chunk:
                raise ValueError(f"Chunk {i} missing 'text' field")

            embedding = chunk["embedding"]
            if not isinstance(embedding, list):
                raise ValueError(f"Chunk {i} embedding must be a list")

            if len(embedding) != self.config.vector_size:
                raise ValueError(
                    f"Chunk {i} embedding dimension mismatch: "
                    f"expected {self.config.vector_size}, got {len(embedding)}"
                )

    async def search_similar(
        self,
        query_vector: List[float],
        limit: int = 5,
        score_threshold: Optional[float] = None,
        filter_conditions: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Search for similar chunks using vector similarity

        Args:
            query_vector: Query embedding vector
            limit: Maximum number of results
            score_threshold: Minimum similarity score (0-1)
            filter_conditions: Optional metadata filters
                Example: {"doc_id": "123", "year": 2023}

        Returns:
            List of matching chunks with scores:
                - id: Chunk ID
                - score: Similarity score
                - text: Chunk text
                - metadata: Chunk metadata
        """
        try:
            # Build filter if provided
            query_filter = None
            if filter_conditions:
                query_filter = self._build_filter(filter_conditions)

            # Execute search
            results = self.client.search(
                collection_name=self.collection_name,
                query_vector=query_vector,
                limit=limit,
                score_threshold=score_threshold,
                query_filter=query_filter,
            )

            # Format results
            formatted_results = []
            for result in results:
                formatted_results.append({
                    "id": result.id,
                    "score": result.score,
                    "text": result.payload.get("text", ""),
                    "metadata": {
                        k: v for k, v in result.payload.items()
                        if k != "text"
                    }
                })

            logger.debug(f"Found {len(formatted_results)} similar chunks")
            return formatted_results

        except Exception as e:
            error_msg = f"Search failed: {str(e)}"
            logger.error(error_msg)
            raise RuntimeError(error_msg) from e

    def _build_filter(self, conditions: Dict[str, Any]) -> Filter:
        """
        Build Qdrant filter from conditions

        Args:
            conditions: Dict of field: value pairs

        Returns:
            Qdrant Filter object
        """
        field_conditions = []
        for field, value in conditions.items():
            field_conditions.append(
                FieldCondition(
                    key=field,
                    match=MatchValue(value=value)
                )
            )

        return Filter(must=field_conditions)

    async def delete_document(self, doc_id: str) -> Dict[str, Any]:
        """
        Delete all chunks associated with a document

        Args:
            doc_id: Document ID

        Returns:
            Dict with deletion status:
                - success: bool
                - deleted_count: int
                - doc_id: str
                - message: str
        """
        try:
            # Delete points with matching doc_id
            result = self.client.delete(
                collection_name=self.collection_name,
                points_selector=models.FilterSelector(
                    filter=Filter(
                        must=[
                            FieldCondition(
                                key="doc_id",
                                match=MatchValue(value=doc_id)
                            )
                        ]
                    )
                )
            )

            logger.info(f"Deleted chunks for document '{doc_id}'")

            return {
                "success": True,
                "deleted_count": result.points_deleted if hasattr(result, 'points_deleted') else "unknown",
                "doc_id": doc_id,
                "message": f"Deleted all chunks for document {doc_id}"
            }

        except Exception as e:
            error_msg = f"Failed to delete document {doc_id}: {str(e)}"
            logger.error(error_msg)
            raise RuntimeError(error_msg) from e

    def get_collection_info(self) -> Dict[str, Any]:
        """
        Get information about the current collection

        Returns:
            Dict with collection info:
                - name: Collection name
                - vectors_count: Number of vectors
                - indexed_vectors_count: Number of indexed vectors
                - points_count: Total points
                - status: Collection status
                - config: Collection configuration
        """
        try:
            info = self.client.get_collection(self.collection_name)

            return {
                "name": self.collection_name,
                "vectors_count": info.vectors_count,
                "indexed_vectors_count": info.indexed_vectors_count,
                "points_count": info.points_count,
                "status": info.status,
                "config": {
                    "vector_size": self.config.vector_size,
                    "distance": self.config.distance.value,
                }
            }

        except Exception as e:
            error_msg = f"Failed to get collection info: {str(e)}"
            logger.error(error_msg)
            raise RuntimeError(error_msg) from e

    def health_check(self) -> Dict[str, Any]:
        """
        Check connection health

        Returns:
            Dict with health status:
                - healthy: bool
                - connected: bool
                - collection_exists: bool
                - message: str
        """
        try:
            # Test connection
            self.client.get_collections()
            connected = True

            # Check collection
            collections = self.client.get_collections().collections
            collection_names = [col.name for col in collections]
            collection_exists = self.collection_name in collection_names

            healthy = connected and collection_exists

            return {
                "healthy": healthy,
                "connected": connected,
                "collection_exists": collection_exists,
                "message": "Healthy" if healthy else "Collection does not exist"
            }

        except Exception as e:
            logger.error(f"Health check failed: {str(e)}")
            return {
                "healthy": False,
                "connected": False,
                "collection_exists": False,
                "message": f"Connection failed: {str(e)}"
            }


class VectorStoreFactory:
    """Factory for creating VectorStore instances"""

    @staticmethod
    def create_store(config: Optional[VectorStoreConfig] = None) -> QdrantStore:
        """
        Create a QdrantStore instance

        Args:
            config: Optional custom configuration

        Returns:
            Configured QdrantStore instance
        """
        return QdrantStore(config=config)

    @staticmethod
    def create_from_settings() -> QdrantStore:
        """
        Create QdrantStore from application settings

        Returns:
            QdrantStore configured from settings
        """
        return QdrantStore()
