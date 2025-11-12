"""
Application configuration using Pydantic Settings
Loads configuration from environment variables and .env file
"""
import os
from functools import lru_cache
from typing import List, Optional

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables
    """

    # Model configuration to load from .env file
    model_config = SettingsConfigDict(
        env_file="../.env" if os.path.exists("../.env") else ".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )

    # =============================================================================
    # API Keys
    # =============================================================================

    anthropic_api_key: str = Field(
        ...,
        description="Anthropic API key for Claude"
    )
    openai_api_key: Optional[str] = Field(
        None,
        description="OpenAI API key (optional, for OpenAI embeddings)"
    )
    voyage_api_key: Optional[str] = Field(
        None,
        description="Voyage AI API key (optional, for Voyage embeddings)"
    )

    # =============================================================================
    # Embedding Configuration
    # =============================================================================

    embedding_provider: str = Field(
        default="openai",
        description="Embedding provider: 'openai' or 'voyage'"
    )
    embedding_model: str = Field(
        default="text-embedding-3-small",
        description="Specific embedding model name"
    )
    embedding_dimensions: int = Field(
        default=1536,
        description="Vector dimensions for embeddings"
    )

    @field_validator('embedding_provider')
    @classmethod
    def validate_embedding_provider(cls, v: str) -> str:
        allowed = ['openai', 'voyage']
        if v.lower() not in allowed:
            raise ValueError(
                f"embedding_provider must be one of: {', '.join(allowed)}. "
                f"Local embeddings are no longer supported. Use OpenAI or Voyage AI."
            )
        return v.lower()

    # =============================================================================
    # Database Configuration
    # =============================================================================

    database_url: str = Field(
        default="postgresql://user:password@postgres:5432/org_archivist",
        description="PostgreSQL connection URL"
    )
    postgres_user: str = Field(default="user", description="PostgreSQL user")
    postgres_password: str = Field(default="password", description="PostgreSQL password")
    postgres_db: str = Field(default="org_archivist", description="PostgreSQL database name")
    postgres_host: str = Field(default="postgres", description="PostgreSQL host")
    postgres_port: int = Field(default=5432, description="PostgreSQL port")

    # =============================================================================
    # Qdrant Configuration
    # =============================================================================

    qdrant_host: str = Field(default="qdrant", description="Qdrant host")
    qdrant_port: int = Field(default=6333, description="Qdrant HTTP port")
    qdrant_grpc_port: int = Field(default=6334, description="Qdrant gRPC port")
    qdrant_collection_name: str = Field(
        default="foundation_docs",
        description="Qdrant collection name"
    )
    qdrant_api_key: Optional[str] = Field(
        None,
        description="Qdrant API key (for Qdrant Cloud)"
    )

    # =============================================================================
    # Application Configuration
    # =============================================================================

    environment: str = Field(
        default="development",
        description="Environment (development, production, testing)"
    )
    backend_host: str = Field(default="0.0.0.0", description="Backend host")
    backend_port: int = Field(default=8000, description="Backend port")
    frontend_host: str = Field(default="0.0.0.0", description="Frontend host")
    frontend_port: int = Field(default=8501, description="Frontend port")
    backend_url: str = Field(
        default="http://backend:8000",
        description="Backend URL for frontend"
    )
    debug: bool = Field(default=False, description="Enable debug mode")
    log_level: str = Field(default="INFO", description="Logging level")

    @field_validator('environment')
    @classmethod
    def validate_environment(cls, v: str) -> str:
        allowed = ['development', 'production', 'testing']
        if v.lower() not in allowed:
            raise ValueError(f"environment must be one of: {', '.join(allowed)}")
        return v.lower()

    @field_validator('log_level')
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        allowed = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
        if v.upper() not in allowed:
            raise ValueError(f"log_level must be one of: {', '.join(allowed)}")
        return v.upper()

    # =============================================================================
    # Claude Model Configuration
    # =============================================================================

    claude_model: str = Field(
        default="claude-sonnet-4-5-20250929",
        description="Default Claude model"
    )
    claude_temperature: float = Field(
        default=0.3,
        ge=0.0,
        le=1.0,
        description="Claude generation temperature"
    )
    claude_max_tokens: int = Field(
        default=4096,
        ge=512,
        le=8192,
        description="Claude max tokens"
    )
    claude_timeout_seconds: int = Field(
        default=60,
        description="Claude API timeout"
    )
    claude_max_retries: int = Field(
        default=3,
        description="Claude API max retries"
    )
    claude_retry_delay_seconds: int = Field(
        default=2,
        description="Claude API retry delay"
    )

    # =============================================================================
    # RAG Configuration
    # =============================================================================

    chunk_size: int = Field(
        default=500,
        ge=100,
        le=2000,
        description="Document chunk size in tokens"
    )
    chunk_overlap: int = Field(
        default=50,
        ge=0,
        le=500,
        description="Chunk overlap in tokens"
    )
    min_chunk_size: int = Field(
        default=100,
        description="Minimum chunk size"
    )
    max_chunk_size: int = Field(
        default=1000,
        description="Maximum chunk size"
    )
    default_top_k: int = Field(
        default=5,
        ge=1,
        le=50,
        description="Default number of chunks to retrieve"
    )
    max_top_k: int = Field(
        default=20,
        description="Maximum allowed top_k value"
    )
    min_similarity_threshold: float = Field(
        default=0.7,
        ge=0.0,
        le=1.0,
        description="Minimum similarity threshold"
    )
    default_recency_weight: float = Field(
        default=0.7,
        ge=0.0,
        le=1.0,
        description="Default recency weight"
    )
    vector_search_weight: float = Field(
        default=0.7,
        ge=0.0,
        le=1.0,
        description="Vector search weight in hybrid search"
    )
    keyword_search_weight: float = Field(
        default=0.3,
        ge=0.0,
        le=1.0,
        description="Keyword search weight in hybrid search"
    )
    max_context_tokens: int = Field(
        default=8000,
        description="Maximum context tokens"
    )
    context_buffer_tokens: int = Field(
        default=1000,
        description="Context buffer tokens"
    )

    # =============================================================================
    # Reranking Configuration
    # =============================================================================

    enable_reranking: bool = Field(
        default=False,
        description="Enable optional reranking with cross-encoder models"
    )
    reranker_model: str = Field(
        default="cross-encoder/ms-marco-MiniLM-L-2-v2",
        description="Reranker model name (cross-encoder from sentence-transformers)"
    )
    reranker_top_n: Optional[int] = Field(
        default=None,
        description="Number of results after reranking (None = keep all)"
    )

    # =============================================================================
    # File Upload Configuration
    # =============================================================================

    max_file_size_mb: int = Field(
        default=50,
        description="Maximum file size in MB"
    )
    max_batch_upload: int = Field(
        default=20,
        description="Maximum files in batch upload"
    )
    allowed_extensions: str = Field(
        default="pdf,docx,txt,doc",
        description="Allowed file extensions (comma-separated)"
    )
    upload_dir: str = Field(
        default="./data/uploads",
        description="Upload directory"
    )
    documents_dir: str = Field(
        default="./data/documents",
        description="Documents directory"
    )

    def get_allowed_extensions_list(self) -> List[str]:
        """Get allowed extensions as a list"""
        return [ext.strip() for ext in self.allowed_extensions.split(',')]

    # =============================================================================
    # Security Configuration
    # =============================================================================

    secret_key: str = Field(
        default="change-me-to-a-random-secret-key",
        description="Secret key for sessions"
    )
    cors_origins: str = Field(
        default="http://localhost:8501,http://localhost:8000",
        description="CORS origins (comma-separated)"
    )
    enable_auth: bool = Field(
        default=False,
        description="Enable authentication"
    )
    session_timeout_minutes: int = Field(
        default=60,
        description="Session timeout in minutes"
    )

    def get_cors_origins_list(self) -> List[str]:
        """Get CORS origins as a list"""
        return [origin.strip() for origin in self.cors_origins.split(',')]

    # =============================================================================
    # Cache Configuration
    # =============================================================================

    enable_cache: bool = Field(default=True, description="Enable caching")
    query_cache_ttl: int = Field(default=3600, description="Query cache TTL in seconds")
    embedding_cache_ttl: int = Field(
        default=86400,
        description="Embedding cache TTL in seconds"
    )
    response_cache_ttl: int = Field(
        default=1800,
        description="Response cache TTL in seconds"
    )
    cache_max_size: int = Field(
        default=1000,
        description="Maximum cache entries"
    )

    # =============================================================================
    # Monitoring & Logging
    # =============================================================================

    enable_request_logging: bool = Field(
        default=True,
        description="Enable request logging"
    )
    log_file: str = Field(
        default="./logs/app.log",
        description="Log file location"
    )
    log_rotation_enabled: bool = Field(
        default=True,
        description="Enable automatic log rotation"
    )
    log_rotation_when: str = Field(
        default="midnight",
        description="When to rotate logs (midnight, H, D, W0-W6, or interval)"
    )
    log_rotation_interval: int = Field(
        default=1,
        description="Rotation interval (1 = daily for 'midnight')"
    )
    log_rotation_backup_count: int = Field(
        default=30,
        ge=1,
        le=365,
        description="Number of backup log files to keep (days of retention)"
    )
    log_max_bytes: int = Field(
        default=10485760,
        ge=1048576,
        description="Max log file size in bytes before rotation (default: 10MB)"
    )
    log_backup_count: int = Field(
        default=10,
        ge=1,
        le=100,
        description="Number of backup files for size-based rotation"
    )
    enable_metrics: bool = Field(
        default=True,
        description="Enable metrics collection"
    )
    sentry_dsn: Optional[str] = Field(
        None,
        description="Sentry DSN for error tracking"
    )

    # =============================================================================
    # Feature Flags
    # =============================================================================

    enable_streaming: bool = Field(default=True, description="Enable streaming responses")
    enable_quality_validation: bool = Field(
        default=True,
        description="Enable quality validation"
    )
    enable_hallucination_detection: bool = Field(
        default=True,
        description="Enable hallucination detection"
    )
    enable_auto_save: bool = Field(
        default=True,
        description="Enable auto-save"
    )
    auto_save_interval: int = Field(
        default=30,
        description="Auto-save interval in seconds"
    )

    # =============================================================================
    # Database Migrations
    # =============================================================================

    disable_auto_migrations: bool = Field(
        default=False,
        description="Disable automatic database migrations on startup"
    )
    migration_timeout_seconds: int = Field(
        default=60,
        description="Timeout for migration operations in seconds"
    )
    migration_retry_attempts: int = Field(
        default=3,
        description="Number of retry attempts for migrations"
    )
    migration_retry_delay_seconds: int = Field(
        default=5,
        description="Delay between migration retry attempts"
    )

    # =============================================================================
    # Development & Testing
    # =============================================================================

    enable_hot_reload: bool = Field(
        default=True,
        description="Enable hot reload"
    )
    enable_api_docs: bool = Field(
        default=True,
        description="Enable API documentation"
    )
    test_database_url: Optional[str] = Field(
        None,
        description="Test database URL"
    )
    mock_mode: bool = Field(
        default=False,
        description="Enable mock mode for testing"
    )

    # =============================================================================
    # Computed Properties
    # =============================================================================

    @property
    def is_development(self) -> bool:
        """Check if running in development mode"""
        return self.environment == "development"

    @property
    def is_production(self) -> bool:
        """Check if running in production mode"""
        return self.environment == "production"

    @property
    def is_testing(self) -> bool:
        """Check if running in test mode"""
        return self.environment == "testing"

    @property
    def max_file_size_bytes(self) -> int:
        """Get max file size in bytes"""
        return self.max_file_size_mb * 1024 * 1024

    def validate_required_api_keys(self) -> None:
        """
        Validate that required API keys are present based on configuration
        Raises ValueError if required keys are missing
        """
        # Anthropic key is always required
        if not self.anthropic_api_key or self.anthropic_api_key.startswith("sk-ant-xxx"):
            raise ValueError("ANTHROPIC_API_KEY is required and must be set to a valid key")

        # Check embedding-specific keys (OpenAI or Voyage)
        if self.embedding_provider == "openai":
            if not self.openai_api_key or self.openai_api_key.startswith("sk-xxx"):
                raise ValueError(
                    "OPENAI_API_KEY is required when using OpenAI embeddings. "
                    "Get your API key from: https://platform.openai.com/api-keys"
                )
        elif self.embedding_provider == "voyage":
            if not self.voyage_api_key or self.voyage_api_key.startswith("pa-xxx"):
                raise ValueError(
                    "VOYAGE_API_KEY is required when using Voyage embeddings. "
                    "Get your API key from: https://www.voyageai.com/"
                )

    def ensure_directories_exist(self) -> None:
        """Create required directories if they don't exist"""
        directories = [
            self.upload_dir,
            self.documents_dir,
            os.path.dirname(self.log_file) if self.log_file else None,
        ]

        for directory in directories:
            if directory and not os.path.exists(directory):
                os.makedirs(directory, exist_ok=True)


@lru_cache()
def get_settings() -> Settings:
    """
    Get cached settings instance
    Uses lru_cache to ensure settings are only loaded once
    """
    settings = Settings()

    # Validate API keys if not in mock mode
    if not settings.mock_mode:
        settings.validate_required_api_keys()

    # Ensure required directories exist
    settings.ensure_directories_exist()

    return settings


# Convenience function to get settings
settings = get_settings()
