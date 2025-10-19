"""
System configuration-related Pydantic models
"""
from typing import Optional
from pydantic import BaseModel, Field


class LLMModelConfig(BaseModel):
    """
    LLM model configuration
    """
    model_name: str = Field(
        default="claude-sonnet-4-5-20250929",
        description="Claude model identifier"
    )
    temperature: float = Field(
        default=0.3,
        ge=0.0,
        le=1.0,
        description="Generation temperature"
    )
    max_tokens: int = Field(
        default=4096,
        ge=512,
        le=8192,
        description="Maximum tokens per response"
    )


class RAGConfig(BaseModel):
    """
    RAG pipeline configuration
    """
    embedding_model: str = Field(
        default="bge-large-en-v1.5",
        description="Embedding model identifier"
    )
    chunk_size: int = Field(
        default=500,
        ge=100,
        le=1000,
        description="Target chunk size in tokens"
    )
    chunk_overlap: int = Field(
        default=50,
        ge=0,
        le=200,
        description="Chunk overlap in tokens"
    )
    default_retrieval_count: int = Field(
        default=5,
        ge=1,
        le=20,
        description="Default number of chunks to retrieve"
    )
    similarity_threshold: float = Field(
        default=0.7,
        ge=0.0,
        le=1.0,
        description="Minimum similarity score for retrieval"
    )
    recency_weight: float = Field(
        default=0.7,
        ge=0.0,
        le=1.0,
        description="Default recency bias weight"
    )


class UserPreferences(BaseModel):
    """
    User preference settings
    """
    default_audience: Optional[str] = Field(None, description="Default audience type")
    default_section: Optional[str] = Field(None, description="Default section type")
    default_tone: Optional[str] = Field(None, description="Default tone level")
    citation_style: str = Field(default="numbered", description="Citation style preference")
    auto_save_interval: int = Field(
        default=60,
        ge=10,
        le=300,
        description="Auto-save interval in seconds"
    )


class SystemConfiguration(BaseModel):
    """
    Complete system configuration
    """
    llm_config: LLMModelConfig = Field(default_factory=LLMModelConfig)
    rag_config: RAGConfig = Field(default_factory=RAGConfig)
    user_preferences: UserPreferences = Field(default_factory=UserPreferences)


class ConfigUpdateRequest(BaseModel):
    """
    Request model for updating configuration
    """
    llm_config: Optional[LLMModelConfig] = Field(None, description="Model configuration updates")
    rag_config: Optional[RAGConfig] = Field(None, description="RAG configuration updates")
    user_preferences: Optional[UserPreferences] = Field(None, description="User preference updates")


class ConfigResponse(BaseModel):
    """
    Response model for configuration endpoints
    """
    config: SystemConfiguration = Field(..., description="Current configuration")
    success: bool = Field(True, description="Operation success")
    message: str = Field(..., description="Status message")
