"""
Dependency injection for FastAPI endpoints

Provides shared instances of services and clients:
- RetrievalEngine for RAG queries
- Vector store (Qdrant)
- Embedding model
- Query cache
- Authentication dependencies for endpoint protection

This module uses the singleton pattern for expensive resources.
"""
import logging
from functools import lru_cache
from typing import Optional, Callable

from fastapi import Header, HTTPException, status, Depends
from llama_index.embeddings.openai import OpenAIEmbedding
from llama_index.embeddings.voyageai import VoyageEmbedding
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

from app.config import get_settings
from app.services.vector_store import QdrantStore, VectorStoreConfig
from app.services.retrieval_engine import RetrievalEngine, RetrievalConfig
from app.services.query_cache import QueryCache, CachedRetrievalEngine
from app.services.chunking_service import ChunkingService, ChunkingConfig
from app.services.generation_service import GenerationService, GenerationConfig
from app.services.database import DatabaseService, get_database_service
from app.services.document_processor import DocumentProcessor, ProcessorFactory, FileType
from app.services.extractors.pdf_extractor import PDFExtractor
from app.services.extractors.docx_extractor import DOCXExtractor
from app.services.extractors.txt_extractor import TXTExtractor
from app.services.auth_service import AuthService
from app.db.models import User, UserRole

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
        grpc_port=settings.qdrant_grpc_port,
        collection_name=settings.qdrant_collection_name,
        vector_size=settings.embedding_dimensions,
        api_key=settings.qdrant_api_key,
        prefer_grpc=False  # Use HTTP for simplicity
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


@lru_cache()
def get_generation_service() -> GenerationService:
    """
    Get or create generation service instance (singleton)

    Returns:
        GenerationService instance for Claude API integration
    """
    settings = get_settings()

    config = GenerationConfig(
        model=settings.claude_model,
        temperature=settings.claude_temperature,
        max_tokens=settings.claude_max_tokens,
        timeout=settings.claude_timeout_seconds,
        max_retries=settings.claude_max_retries,
        retry_delay=settings.claude_retry_delay_seconds
    )

    service = GenerationService(config)
    logger.info(f"Generation service initialized: {settings.claude_model}")

    return service


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


async def get_generator() -> GenerationService:
    """
    FastAPI dependency for generation service

    Usage:
        @app.get("/endpoint")
        async def endpoint(generator: GenerationService = Depends(get_generator)):
            result = await generator.generate(...)
    """
    return get_generation_service()


@lru_cache()
def get_chunking_service() -> ChunkingService:
    """
    Get or create chunking service instance (singleton)

    Returns:
        ChunkingService instance for semantic chunking
    """
    settings = get_settings()

    # Create chunking config from settings
    config = ChunkingConfig(
        chunk_size=settings.chunk_size,
        chunk_overlap=settings.chunk_overlap,
    )

    # Create chunking service (will use sentence strategy by default)
    from app.services.chunking_service import ChunkingServiceFactory
    service = ChunkingServiceFactory.create_service()

    logger.info(f"Chunking service initialized: chunk_size={config.chunk_size}, overlap={config.chunk_overlap}")

    return service


@lru_cache()
def get_document_processor() -> DocumentProcessor:
    """
    Get or create document processor instance (singleton)

    Initializes:
    - Vector store (Qdrant)
    - Embedding model
    - Chunking service
    - Text extractors for PDF, DOCX, TXT

    Returns:
        DocumentProcessor ready for document processing
    """
    # Get dependencies
    vector_store = get_vector_store()
    embedding_model = get_embedding_model()
    chunking_service = get_chunking_service()

    # Create processor
    processor = ProcessorFactory.create_processor(
        vector_store=vector_store,
        embedding_model=embedding_model,
        chunking_service=chunking_service
    )

    # Register extractors
    processor.register_extractor(FileType.PDF, PDFExtractor())
    processor.register_extractor(FileType.DOCX, DOCXExtractor())
    processor.register_extractor(FileType.TXT, TXTExtractor())

    logger.info("Document processor initialized with PDF, DOCX, TXT extractors")

    return processor


async def get_processor() -> DocumentProcessor:
    """
    FastAPI dependency for document processor

    Usage:
        @app.post("/upload")
        async def upload(processor: DocumentProcessor = Depends(get_processor)):
            result = await processor.process_document(...)
    """
    return get_document_processor()


async def get_database() -> DatabaseService:
    """
    FastAPI dependency for database service

    Usage:
        @app.post("/endpoint")
        async def endpoint(db: DatabaseService = Depends(get_database)):
            await db.insert_document(...)
    """
    db = get_database_service()
    if not db.pool:
        await db.connect()
    return db


# ==========================================
# Authentication Dependencies
# ==========================================

# Lazy initialization of auth database engine
_auth_engine = None
_auth_session_maker = None


def _get_auth_engine():
    """Lazy initialize auth database engine"""
    global _auth_engine, _auth_session_maker
    if _auth_engine is None:
        settings = get_settings()
        _auth_engine = create_async_engine(settings.database_url)
        _auth_session_maker = async_sessionmaker(_auth_engine, class_=AsyncSession, expire_on_commit=False)
    return _auth_session_maker


async def get_auth_db():
    """Dependency for getting async database session for auth"""
    session_maker = _get_auth_engine()
    async with session_maker() as session:
        try:
            yield session
        finally:
            await session.close()


async def get_current_user(
    authorization: Optional[str] = Header(None),
    db: AsyncSession = Depends(get_auth_db)
) -> User:
    """
    FastAPI dependency for getting the current authenticated user from Authorization header

    Validates session token and returns User model. Raises HTTPException for invalid tokens.

    Args:
        authorization: Authorization header with "Bearer <token>" format
        db: Database session

    Returns:
        User object if authenticated

    Raises:
        HTTPException: 401 if authentication fails

    Usage:
        @router.get("/protected")
        async def protected_endpoint(current_user: User = Depends(get_current_user)):
            return {"user": current_user.email}
    """
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authorization header",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Parse Bearer token
    parts = authorization.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authorization header format. Expected: Bearer <token>",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = parts[1]

    # Validate session and get user
    user = await AuthService.validate_session(db, token)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired session",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return user


async def get_current_active_user(
    current_user: User = Depends(get_current_user)
) -> User:
    """
    FastAPI dependency that ensures the current user is active

    Args:
        current_user: Current authenticated user (from get_current_user dependency)

    Returns:
        User object if user is active

    Raises:
        HTTPException: 403 if user is not active

    Usage:
        @router.post("/create-content")
        async def create_content(current_user: User = Depends(get_current_active_user)):
            # Only active users can access this endpoint
            return {"message": "Content created"}
    """
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is not active"
        )

    return current_user


def require_role(required_role: str) -> Callable:
    """
    Factory function for role-based access control

    Returns a dependency that checks if the user has the required role or higher.
    Role hierarchy: ADMIN > EDITOR > WRITER

    Args:
        required_role: Required role as string ("admin", "editor", or "writer")

    Returns:
        FastAPI dependency function that validates user role

    Raises:
        HTTPException: 403 if user doesn't have required permissions

    Usage:
        @router.post("/admin-only")
        async def admin_endpoint(current_user: User = Depends(require_role("admin"))):
            return {"action": "performed"}

        @router.put("/edit-content")
        async def edit_content(current_user: User = Depends(require_role("editor"))):
            # Admins and editors can access this
            return {"message": "Content updated"}
    """
    # Convert string to UserRole enum
    role_map = {
        "admin": UserRole.ADMIN,
        "editor": UserRole.EDITOR,
        "writer": UserRole.WRITER
    }

    role_enum = role_map.get(required_role.lower())
    if not role_enum:
        raise ValueError(f"Invalid role: {required_role}. Must be one of: admin, editor, writer")

    async def role_checker(current_user: User = Depends(get_current_active_user)) -> User:
        """Check if user has required role"""
        if not AuthService.has_role(current_user, role_enum):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Insufficient permissions. Required role: {required_role}"
            )
        return current_user

    return role_checker


async def get_optional_user(
    authorization: Optional[str] = Header(None),
    db: AsyncSession = Depends(get_auth_db)
) -> Optional[User]:
    """
    FastAPI dependency for getting the current user if authenticated, None otherwise

    Unlike get_current_user, this does not raise an exception if user is not authenticated.
    Useful for endpoints that have different behavior for authenticated vs. anonymous users.

    Args:
        authorization: Optional Authorization header with "Bearer <token>" format
        db: Database session

    Returns:
        User object if authenticated, None otherwise

    Usage:
        @router.get("/public-or-private")
        async def mixed_endpoint(current_user: Optional[User] = Depends(get_optional_user)):
            if current_user:
                return {"message": f"Hello {current_user.email}"}
            return {"message": "Hello anonymous user"}
    """
    if not authorization:
        return None

    # Parse Bearer token
    parts = authorization.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        return None

    token = parts[1]

    # Validate session and get user
    try:
        user = await AuthService.validate_session(db, token)
        return user
    except Exception:
        return None
