"""
Semantic Chunking Service

This module provides semantic chunking functionality using LlamaIndex node parsers.
Supports multiple chunking strategies:
- SentenceSplitter: Splits text while respecting sentence boundaries
- SemanticSplitterNodeParser: Adaptive chunking based on semantic similarity
- TokenTextSplitter: Fixed token-based chunking

Architecture follows the strategy pattern for different chunking approaches.
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Optional
from dataclasses import dataclass
from enum import Enum
import logging

from llama_index.core.schema import Document as LlamaDocument, TextNode
from llama_index.core.node_parser import (
    SentenceSplitter,
    SemanticSplitterNodeParser,
    TokenTextSplitter,
)
from llama_index.embeddings.openai import OpenAIEmbedding


logger = logging.getLogger(__name__)


class ChunkingStrategy(Enum):
    """Available chunking strategies"""
    SENTENCE = "sentence"  # Sentence boundary aware
    SEMANTIC = "semantic"  # Semantic similarity based
    TOKEN = "token"  # Fixed token count


@dataclass
class ChunkingConfig:
    """Configuration for chunking operations"""
    strategy: ChunkingStrategy = ChunkingStrategy.SEMANTIC
    chunk_size: int = 512  # Target chunk size (chars for sentence, tokens for token)
    chunk_overlap: int = 50  # Overlap between chunks

    # SemanticSplitter specific
    buffer_size: int = 1  # Number of sentences to compare
    breakpoint_percentile_threshold: int = 95  # Percentile for breakpoint detection

    # SentenceWindow specific (for future use)
    window_size: int = 3  # Sentences on either side


class ChunkingService:
    """
    Main chunking service orchestrator

    Provides semantic chunking using LlamaIndex node parsers.
    Converts text into semantically coherent chunks for RAG.
    """

    def __init__(self, config: Optional[ChunkingConfig] = None):
        """
        Initialize chunking service

        Args:
            config: ChunkingConfig instance (uses defaults if None)
        """
        self.config = config or ChunkingConfig()
        self.embedding_model = None

        # Initialize embedding model only if using semantic strategy
        if self.config.strategy == ChunkingStrategy.SEMANTIC:
            self._initialize_embedding_model()

        self.node_parser = self._create_node_parser()

        logger.info(
            f"ChunkingService initialized with {self.config.strategy.value} strategy"
        )

    def _initialize_embedding_model(self):
        """Initialize embedding model for semantic chunking"""
        try:
            # Import settings only when needed for semantic chunking
            from app.config import settings

            # Use OpenAI embeddings for semantic similarity
            # Alternative: HuggingFaceEmbedding for local models
            self.embedding_model = OpenAIEmbedding(
                model=settings.EMBEDDING_MODEL,
                api_key=settings.OPENAI_API_KEY
            )
            logger.debug(f"Initialized embedding model: {settings.EMBEDDING_MODEL}")
        except Exception as e:
            logger.error(f"Failed to initialize embedding model: {e}")
            # Fallback to sentence splitter if embedding model fails
            logger.warning("Falling back to SentenceSplitter strategy")
            self.config.strategy = ChunkingStrategy.SENTENCE

    def _create_node_parser(self):
        """
        Create appropriate node parser based on strategy

        Returns:
            Configured node parser instance
        """
        if self.config.strategy == ChunkingStrategy.SEMANTIC:
            if not self.embedding_model:
                logger.warning("No embedding model available, using SentenceSplitter")
                return self._create_sentence_splitter()

            return SemanticSplitterNodeParser(
                buffer_size=self.config.buffer_size,
                breakpoint_percentile_threshold=self.config.breakpoint_percentile_threshold,
                embed_model=self.embedding_model
            )

        elif self.config.strategy == ChunkingStrategy.SENTENCE:
            return self._create_sentence_splitter()

        elif self.config.strategy == ChunkingStrategy.TOKEN:
            return TokenTextSplitter(
                chunk_size=self.config.chunk_size,
                chunk_overlap=self.config.chunk_overlap,
                separator=" "
            )

        else:
            raise ValueError(f"Unknown chunking strategy: {self.config.strategy}")

    def _create_sentence_splitter(self):
        """Create SentenceSplitter with current config"""
        return SentenceSplitter(
            chunk_size=self.config.chunk_size,
            chunk_overlap=self.config.chunk_overlap
        )

    def chunk_text(
        self,
        text: str,
        metadata: Optional[Dict] = None
    ) -> List[Dict]:
        """
        Chunk text into semantically coherent pieces

        Args:
            text: Raw text to chunk
            metadata: Optional metadata to attach to each chunk

        Returns:
            List of chunk dictionaries with text, metadata, and chunk info
        """
        if not text or not text.strip():
            logger.warning("Empty text provided to chunk_text")
            return []

        try:
            # Create LlamaIndex Document
            doc = LlamaDocument(
                text=text,
                metadata=metadata or {}
            )

            # Get nodes from document
            nodes = self.node_parser.get_nodes_from_documents(
                [doc],
                show_progress=False
            )

            # Convert nodes to our chunk format
            chunks = []
            for i, node in enumerate(nodes):
                chunk = {
                    'text': node.get_content(),
                    'chunk_index': i,
                    'char_count': len(node.get_content()),
                    'word_count': len(node.get_content().split()),
                    'metadata': {
                        **node.metadata,
                        'chunk_index': i,
                        'node_id': node.node_id,
                        'chunking_strategy': self.config.strategy.value
                    }
                }
                chunks.append(chunk)

            logger.info(
                f"Created {len(chunks)} chunks using {self.config.strategy.value} strategy"
            )

            return chunks

        except Exception as e:
            logger.error(f"Error during chunking: {e}", exc_info=True)
            # Fallback to simple splitting
            return self._fallback_chunking(text, metadata)

    def _fallback_chunking(
        self,
        text: str,
        metadata: Optional[Dict] = None
    ) -> List[Dict]:
        """
        Fallback chunking using simple character-based splitting

        Args:
            text: Text to chunk
            metadata: Metadata to attach

        Returns:
            List of chunk dictionaries
        """
        logger.warning("Using fallback chunking strategy")

        chunks = []
        chunk_size = 1000  # Default fallback size
        overlap = 100

        for i, start in enumerate(range(0, len(text), chunk_size - overlap)):
            chunk_text = text[start:start + chunk_size]

            chunk = {
                'text': chunk_text,
                'chunk_index': i,
                'char_count': len(chunk_text),
                'word_count': len(chunk_text.split()),
                'metadata': {
                    **(metadata or {}),
                    'chunk_index': i,
                    'chunking_strategy': 'fallback'
                }
            }
            chunks.append(chunk)

        return chunks


class ChunkingServiceFactory:
    """Factory for creating configured ChunkingService instances"""

    @staticmethod
    def create_service(
        strategy: Optional[ChunkingStrategy] = None,
        **config_kwargs
    ) -> ChunkingService:
        """
        Create a ChunkingService with specified configuration

        Args:
            strategy: ChunkingStrategy enum (defaults to config settings)
            **config_kwargs: Additional ChunkingConfig parameters

        Returns:
            Configured ChunkingService instance
        """
        # Import settings only when needed
        from app.config import settings

        # Use strategy from settings if not provided
        if strategy is None:
            strategy_str = getattr(settings, 'CHUNKING_STRATEGY', 'semantic')
            strategy = ChunkingStrategy(strategy_str)

        # Create config with overrides
        config = ChunkingConfig(
            strategy=strategy,
            chunk_size=config_kwargs.get('chunk_size', settings.chunk_size),
            chunk_overlap=config_kwargs.get('chunk_overlap', settings.chunk_overlap),
            buffer_size=config_kwargs.get('buffer_size', 1),
            breakpoint_percentile_threshold=config_kwargs.get(
                'breakpoint_percentile_threshold', 95
            )
        )

        return ChunkingService(config)

    @staticmethod
    def create_semantic_service() -> ChunkingService:
        """Create service with semantic chunking strategy"""
        config = ChunkingConfig(strategy=ChunkingStrategy.SEMANTIC)
        return ChunkingService(config)

    @staticmethod
    def create_sentence_service() -> ChunkingService:
        """Create service with sentence-based chunking strategy"""
        config = ChunkingConfig(strategy=ChunkingStrategy.SENTENCE)
        return ChunkingService(config)
