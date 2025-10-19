"""
Reranker Service

Implements optional reranking using cross-encoder models to improve
retrieval result quality by analyzing query-document relevance at a deeper level.

Supports:
- LlamaIndex SentenceTransformerRerank (cross-encoder models)
- Multiple model options with speed/accuracy tradeoffs
- Optional dependency (graceful degradation if not available)
"""
import logging
from typing import List, Optional, Dict, Any
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class RerankerModel(str, Enum):
    """
    Available reranker models with speed/accuracy tradeoffs

    Based on sentence-transformers cross-encoder models:
    https://www.sbert.net/docs/pretrained-models/ce-msmarco.html
    """
    # Fastest, lowest accuracy
    TINY_BERT = "cross-encoder/ms-marco-TinyBERT-L-2-v2"  # Default in LlamaIndex

    # Balanced speed/accuracy (recommended)
    MINI_LM_L2 = "cross-encoder/ms-marco-MiniLM-L-2-v2"
    MINI_LM_L6 = "cross-encoder/ms-marco-MiniLM-L-6-v2"
    MINI_LM_L12 = "cross-encoder/ms-marco-MiniLM-L-12-v2"

    # Higher accuracy, slower
    ELECTRA_BASE = "cross-encoder/ms-marco-electra-base"

    # Multilingual support
    JINA_V2_BASE = "jinaai/jina-reranker-v2-base-multilingual"


@dataclass
class RerankerConfig:
    """Configuration for reranking"""
    model: str = RerankerModel.MINI_LM_L2.value  # Balanced default
    top_n: Optional[int] = None  # Number of results after reranking (None = keep all)
    batch_size: int = 32  # Batch size for inference
    use_fp16: bool = True  # Use FP16 for faster inference (if GPU available)


class Reranker:
    """
    Reranker using cross-encoder models for improved relevance scoring

    Rerankers analyze the query and document together to produce a more
    accurate relevance score than embedding-based similarity alone.
    They are slower but more precise, making them ideal for reranking
    a smaller candidate set.
    """

    def __init__(self, config: Optional[RerankerConfig] = None):
        """
        Initialize reranker

        Args:
            config: Reranker configuration
        """
        self.config = config or RerankerConfig()
        self._reranker = None
        self._available = False

        # Try to initialize LlamaIndex reranker
        try:
            self._initialize_reranker()
            self._available = True
            logger.info(
                f"Reranker initialized with model: {self.config.model}, "
                f"top_n: {self.config.top_n}"
            )
        except Exception as e:
            logger.warning(
                f"Reranker initialization failed: {e}. "
                f"Reranking will be disabled. Install llama-index-postprocessor-sentence-transformer "
                f"to enable reranking."
            )
            self._available = False

    def _initialize_reranker(self):
        """
        Initialize LlamaIndex SentenceTransformerRerank

        Raises ImportError if dependencies not available
        """
        try:
            from llama_index.core.postprocessor import SentenceTransformerRerank

            # Initialize reranker with config
            self._reranker = SentenceTransformerRerank(
                model=self.config.model,
                top_n=self.config.top_n or 100  # Large default if not specified
            )

            logger.debug(f"SentenceTransformerRerank initialized: {self.config.model}")

        except ImportError as e:
            logger.warning(
                f"Failed to import SentenceTransformerRerank: {e}. "
                f"Install with: pip install llama-index-postprocessor-sentence-transformer"
            )
            raise

    def is_available(self) -> bool:
        """Check if reranker is available"""
        return self._available

    def rerank(
        self,
        query: str,
        results: List[Dict[str, Any]],
        top_n: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Rerank results using cross-encoder model

        Args:
            query: Original query string
            results: List of results with 'text' and 'score' fields
            top_n: Override number of results to return (None = use config)

        Returns:
            Reranked results with updated scores
        """
        if not self._available or not self._reranker:
            logger.warning("Reranker not available, returning original results")
            return results

        if not results:
            return results

        try:
            # Import LlamaIndex node types
            from llama_index.core.schema import NodeWithScore, TextNode

            # Convert results to LlamaIndex nodes
            nodes_with_score = []
            for i, result in enumerate(results):
                # Create TextNode with text content
                text_node = TextNode(
                    text=result.get("text", ""),
                    id_=result.get("chunk_id", f"node_{i}"),
                    metadata=result.get("metadata", {})
                )

                # Wrap in NodeWithScore
                node_with_score = NodeWithScore(
                    node=text_node,
                    score=result.get("score", 0.0)
                )
                nodes_with_score.append(node_with_score)

            logger.debug(f"Reranking {len(nodes_with_score)} results for query: '{query[:50]}...'")

            # Rerank using cross-encoder
            # Note: postprocess_nodes expects query as query_str parameter
            reranked_nodes = self._reranker.postprocess_nodes(
                nodes=nodes_with_score,
                query_str=query
            )

            # Convert back to result format
            reranked_results = []
            for node_with_score in reranked_nodes:
                result = {
                    "chunk_id": node_with_score.node.id_,
                    "text": node_with_score.node.text,
                    "score": node_with_score.score,
                    "metadata": {
                        **node_with_score.node.metadata,
                        "_reranked": True,
                        "_reranker_model": self.config.model,
                    }
                }
                reranked_results.append(result)

            # Apply top_n if specified
            final_top_n = top_n or self.config.top_n
            if final_top_n and len(reranked_results) > final_top_n:
                reranked_results = reranked_results[:final_top_n]

            logger.info(
                f"Reranked {len(results)} results to {len(reranked_results)} results "
                f"(model: {self.config.model})"
            )

            return reranked_results

        except Exception as e:
            logger.error(f"Reranking error: {e}", exc_info=True)
            # Return original results on error
            return results


class RerankerFactory:
    """Factory for creating Reranker instances"""

    @staticmethod
    def create_reranker(
        model: Optional[str] = None,
        top_n: Optional[int] = None,
        config: Optional[RerankerConfig] = None
    ) -> Reranker:
        """
        Create a Reranker instance

        Args:
            model: Model name (overrides config)
            top_n: Top N results (overrides config)
            config: Full RerankerConfig (lowest priority)

        Returns:
            Configured Reranker instance
        """
        # Build config with overrides
        if config is None:
            config = RerankerConfig()

        if model:
            config.model = model
        if top_n is not None:
            config.top_n = top_n

        return Reranker(config=config)

    @staticmethod
    def create_from_settings(settings) -> Optional[Reranker]:
        """
        Create Reranker from application settings

        Args:
            settings: Application settings object

        Returns:
            Reranker instance if enabled, None otherwise
        """
        # Check if reranking is enabled in settings
        enable_reranking = getattr(settings, 'ENABLE_RERANKING', False)

        if not enable_reranking:
            logger.info("Reranking disabled in settings")
            return None

        # Get reranker config from settings
        reranker_model = getattr(
            settings,
            'RERANKER_MODEL',
            RerankerModel.MINI_LM_L2.value
        )
        reranker_top_n = getattr(settings, 'RERANKER_TOP_N', None)

        config = RerankerConfig(
            model=reranker_model,
            top_n=reranker_top_n
        )

        return Reranker(config=config)
