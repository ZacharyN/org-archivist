"""
Dependency injection for FastAPI endpoints

Provides shared instances of services and clients:
- RetrievalEngine for RAG queries
- Vector store (Qdrant)
- Embedding model
- Query cache

This module uses the singleton pattern for expensive resources.
"""
import logging
from functools import lru_cache
from typing import Optional

from llama_index.embeddings.openai import OpenAIEmbedding
from llama_index.embeddings.voyageai import VoyageEmbedding

from app.config import get_settings
from app.services.vector_store import QdrantStore, VectorStoreConfig
from app.services.retrieval_engine import RetrievalEngine, RetrievalConfig
from app.services.query_cache import QueryCache, CachedRetrievalEngine
from app.services.chunking_service import ChunkingService, ChunkingConfig

logger = logging.getLogger(__name__)


@lru_cache()
def get_vector_store() -> QdrantStore:
    """
    Get or create vector store instance (singleton)

    Returns:
        QdrantStore instance connected to Qdrant
    """
    settings = get_settings()

    config = VectorStoreConfig(
        host=settings.qdrant_host,
        port=settings.qdrant_port,
        collection_name=settings.qdrant_collection_name,
        vector_dimensions=settings.embedding_dimensions,
        use_grpc=False  # Use HTTP for simplicity
    )

    store = QdrantStore(config)
    logger.info(f"Vector store initialized: {settings.qdrant_host}:{settings.qdrant_port}")

    return store


@lru_cache()
def get_embedding_model():
    """
    Get or create embedding model instance (singleton)

    Returns:
        Embedding model based on settings configuration
    """
    settings = get_settings()

    if settings.embedding_provider == "openai":
        model = OpenAIEmbedding(
            model=settings.embedding_model,
            api_key=settings.openai_api_key
        )
        logger.info(f"OpenAI embedding model initialized: {settings.embedding_model}")

    elif settings.embedding_provider == "voyage":
        model = VoyageEmbedding(
            model_name=settings.embedding_model,
            voyage_api_key=settings.voyage_api_key
        )
        logger.info(f"Voyage embedding model initialized: {settings.embedding_model}")

    else:  # local
        # For local models, we'd use HuggingFaceEmbedding
        # For now, fall back to OpenAI if available
        if settings.openai_api_key:
            model = OpenAIEmbedding(
                model="text-embedding-3-small",
                api_key=settings.openai_api_key
            )
            logger.warning("Local embedding not implemented, using OpenAI as fallback")
        else:
            raise ValueError(
                "No embedding model available. Set OPENAI_API_KEY or VOYAGE_API_KEY"
            )

    return model


@lru_cache()
def get_query_cache() -> Optional[QueryCache]:
    """
    Get or create query cache instance (singleton)

    Returns:
        QueryCache instance if caching is enabled, None otherwise
    """
    settings = get_settings()

    if not settings.enable_cache:
        logger.info("Query cache disabled")
        return None

    cache = QueryCache(
        max_size=settings.cache_max_size,
        ttl_seconds=settings.query_cache_ttl,
        enable_metrics=True
    )

    logger.info(
        f"Query cache initialized: max_size={settings.cache_max_size}, "
        f"ttl={settings.query_cache_ttl}s"
    )

    return cache


@lru_cache()
def get_retrieval_engine() -> RetrievalEngine:
    """
    Get or create retrieval engine instance (singleton)

    Initializes:
    - Vector store (Qdrant)
    - Embedding model
    - Query cache (if enabled)
    - Retrieval configuration

    Returns:
        CachedRetrievalEngine if caching enabled, otherwise RetrievalEngine
    """
    settings = get_settings()

    # Get dependencies
    vector_store = get_vector_store()
    embedding_model = get_embedding_model()
    query_cache = get_query_cache()

    # Create retrieval config from settings
    config = RetrievalConfig(
        vector_weight=settings.vector_search_weight,
        keyword_weight=settings.keyword_search_weight,
        recency_weight=settings.default_recency_weight,
        max_per_doc=3,  # Limit chunks per document for diversity
        enable_reranking=settings.enable_reranking,
        expand_query=True  # Enable query expansion
    )

    # Create base retrieval engine
    engine = RetrievalEngine(
        vector_store=vector_store,
        embedding_model=embedding_model,
        config=config
    )

    logger.info(
        f"Retrieval engine initialized: "
        f"vector_weight={config.vector_weight}, "
        f"keyword_weight={config.keyword_weight}, "
        f"recency_weight={config.recency_weight}"
    )

    # Wrap with caching if enabled
    if query_cache:
        cached_engine = CachedRetrievalEngine(
            retrieval_engine=engine,
            cache=query_cache,
            enable_cache=True
        )
        logger.info("Retrieval engine wrapped with query cache")
        return cached_engine

    return engine


async def get_initialized_retrieval_engine() -> RetrievalEngine:
    """
    Get retrieval engine and ensure BM25 index is built

    This is an async dependency that can be used in endpoints.
    Builds the BM25 index on first call for keyword search capability.

    Returns:
        Initialized RetrievalEngine ready for queries
    """
    engine = get_retrieval_engine()

    # Build BM25 index if not already built
    # (This checks if index exists before building)
    if not hasattr(engine, '_bm25_index_built'):
        try:
            logger.info("Building BM25 index for keyword search...")
            await engine.build_bm25_index()
            engine._bm25_index_built = True
            logger.info("BM25 index built successfully")
        except Exception as e:
            logger.error(f"Failed to build BM25 index: {e}")
            # Continue without BM25 (engine will use vector search only)

    return engine


# Dependency functions for FastAPI
async def get_engine() -> RetrievalEngine:
    """
    FastAPI dependency for retrieval engine

    Usage:
        @app.get("/endpoint")
        async def endpoint(engine: RetrievalEngine = Depends(get_engine)):
            results = await engine.retrieve(...)
    """
    return await get_initialized_retrieval_engine()
