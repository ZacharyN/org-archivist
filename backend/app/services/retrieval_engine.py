"""
Retrieval Engine Service

Implements hybrid search combining:
- Vector similarity search (semantic)
- Keyword search (BM25)
- Metadata filtering
- Recency weighting
- Result diversification
- Optional re-ranking

Orchestrates the complete retrieval pipeline for RAG.
"""
import logging
import re
from typing import List, Dict, Optional, Any, Tuple
from dataclasses import dataclass
from datetime import datetime
from collections import defaultdict

from llama_index.core.embeddings import BaseEmbedding

from app.models.query import QueryRequest
from app.models.document import DocumentFilters
from app.services.vector_store import QdrantStore

logger = logging.getLogger(__name__)


@dataclass
class RetrievalResult:
    """
    Single retrieval result with score and metadata
    """
    chunk_id: str
    text: str
    score: float
    metadata: Dict[str, Any]
    doc_id: Optional[str] = None
    chunk_index: Optional[int] = None


@dataclass
class RetrievalConfig:
    """Configuration for retrieval engine"""
    vector_weight: float = 0.7  # Weight for vector search results
    keyword_weight: float = 0.3  # Weight for keyword search results
    recency_weight: float = 0.7  # Weight for recency boosting (0-1)
    max_per_doc: int = 3  # Max chunks per document (diversification)
    enable_reranking: bool = False  # Enable optional reranking
    expand_query: bool = True  # Enable query expansion


class RetrievalEngine:
    """
    Retrieval Engine for hybrid document search

    Combines vector similarity search with keyword search (BM25),
    applies metadata filtering, recency weighting, and result diversification.
    """

    def __init__(
        self,
        vector_store: QdrantStore,
        embedding_model: BaseEmbedding,
        config: Optional[RetrievalConfig] = None,
        reranker: Optional[Any] = None  # Future: reranking model
    ):
        """
        Initialize retrieval engine

        Args:
            vector_store: Qdrant vector store instance
            embedding_model: Embedding model for query encoding
            config: Optional retrieval configuration
            reranker: Optional reranking model (for future use)
        """
        self.vector_store = vector_store
        self.embedding_model = embedding_model
        self.config = config or RetrievalConfig()
        self.reranker = reranker

        # BM25 index (will be populated during keyword search implementation)
        self._bm25_index = None

        logger.info(
            f"RetrievalEngine initialized with config: "
            f"vector_weight={self.config.vector_weight}, "
            f"keyword_weight={self.config.keyword_weight}, "
            f"recency_weight={self.config.recency_weight}"
        )

    async def retrieve(
        self,
        query: str,
        top_k: int = 5,
        filters: Optional[DocumentFilters] = None,
        recency_weight: Optional[float] = None
    ) -> List[RetrievalResult]:
        """
        Main retrieval pipeline

        Args:
            query: User query string
            top_k: Number of results to return
            filters: Document metadata filters
            recency_weight: Override default recency weight

        Returns:
            List of RetrievalResult objects sorted by relevance
        """
        logger.info(f"Retrieving documents for query: '{query[:100]}...'")

        try:
            # 1. Process query (clean, expand, prepare)
            processed_query = self._process_query(query)
            logger.debug(f"Processed query: '{processed_query}'")

            # 2. Generate query embedding
            query_embedding = await self._generate_embedding(processed_query)
            logger.debug(f"Generated query embedding: {len(query_embedding)} dimensions")

            # 3. Vector similarity search (placeholder - will implement next)
            vector_results = await self._vector_search(
                query_embedding=query_embedding,
                top_k=top_k * 4,  # Retrieve more for reranking/combination
                filters=filters
            )
            logger.info(f"Vector search returned {len(vector_results)} results")

            # 4. Keyword search (BM25) - placeholder for now
            keyword_results = await self._keyword_search(
                query=processed_query,
                top_k=top_k * 2,
                filters=filters
            )
            logger.info(f"Keyword search returned {len(keyword_results)} results")

            # 5. Combine results with hybrid scoring
            combined_results = self._combine_results(
                vector_results=vector_results,
                keyword_results=keyword_results
            )
            logger.info(f"Combined results: {len(combined_results)} unique chunks")

            # 6. Apply recency weighting
            weight = recency_weight if recency_weight is not None else self.config.recency_weight
            weighted_results = self._apply_recency_weight(combined_results, weight)

            # 7. Diversify results (limit chunks per document)
            diversified_results = self._diversify_results(
                weighted_results,
                max_per_doc=self.config.max_per_doc
            )
            logger.info(f"Diversified to {len(diversified_results)} results")

            # 8. Optional reranking (future implementation)
            if self.config.enable_reranking and self.reranker:
                diversified_results = await self._rerank_results(
                    query=query,
                    results=diversified_results,
                    top_k=top_k * 2
                )
                logger.info("Reranking applied")

            # 9. Return top-k results
            final_results = diversified_results[:top_k]
            logger.info(f"Returning {len(final_results)} final results")

            return final_results

        except Exception as e:
            logger.error(f"Retrieval error: {e}", exc_info=True)
            raise

    def _process_query(self, query: str) -> str:
        """
        Process and clean query text

        Steps:
        - Normalize whitespace
        - Remove special characters (optional)
        - Expand abbreviations (optional)
        - Remove stop words (optional, for keyword search)

        Args:
            query: Raw query string

        Returns:
            Processed query string
        """
        # Normalize whitespace
        processed = re.sub(r'\s+', ' ', query.strip())

        # Remove excessive punctuation
        processed = re.sub(r'[^\w\s.,!?-]', '', processed)

        # Optional: Query expansion
        if self.config.expand_query:
            processed = self._expand_query(processed)

        return processed

    def _expand_query(self, query: str) -> str:
        """
        Expand query with synonyms and related terms

        This is a placeholder for more sophisticated query expansion.
        Future implementations could use:
        - Synonym dictionaries
        - WordNet expansion
        - Domain-specific term expansion
        - LLM-based query expansion

        Args:
            query: Processed query string

        Returns:
            Expanded query string
        """
        # Common abbreviation expansions for grant writing domain
        expansions = {
            'RFP': 'Request for Proposal',
            'LOI': 'Letter of Intent',
            'MOU': 'Memorandum of Understanding',
            'KPI': 'Key Performance Indicator',
            'ROI': 'Return on Investment',
            'ED': 'Executive Director',
            'FTE': 'Full-Time Equivalent',
            'YTD': 'Year to Date',
        }

        # Apply expansions
        for abbr, expansion in expansions.items():
            # Case-insensitive replacement
            pattern = r'\b' + re.escape(abbr) + r'\b'
            if re.search(pattern, query, re.IGNORECASE):
                query = f"{query} {expansion}"

        return query

    async def _generate_embedding(self, text: str) -> List[float]:
        """
        Generate embedding for query text

        Args:
            text: Text to embed

        Returns:
            Embedding vector
        """
        try:
            # Use LlamaIndex embedding model
            embedding = self.embedding_model.get_text_embedding(text)
            return embedding
        except Exception as e:
            logger.error(f"Embedding generation error: {e}", exc_info=True)
            raise

    async def _vector_search(
        self,
        query_embedding: List[float],
        top_k: int,
        filters: Optional[DocumentFilters] = None
    ) -> List[RetrievalResult]:
        """
        Perform vector similarity search

        Placeholder - will be implemented in next task

        Args:
            query_embedding: Query vector
            top_k: Number of results
            filters: Metadata filters

        Returns:
            List of RetrievalResult objects
        """
        # TODO: Implement in next task (task_order: 91)
        logger.debug("Vector search called (placeholder)")
        return []

    async def _keyword_search(
        self,
        query: str,
        top_k: int,
        filters: Optional[DocumentFilters] = None
    ) -> List[RetrievalResult]:
        """
        Perform BM25 keyword search

        Placeholder - will be implemented in task_order: 89

        Args:
            query: Query text
            top_k: Number of results
            filters: Metadata filters

        Returns:
            List of RetrievalResult objects
        """
        # TODO: Implement BM25 keyword search
        logger.debug("Keyword search called (placeholder)")
        return []

    def _combine_results(
        self,
        vector_results: List[RetrievalResult],
        keyword_results: List[RetrievalResult]
    ) -> List[RetrievalResult]:
        """
        Combine vector and keyword search results with weighted scoring

        Placeholder - will be implemented in task_order: 87

        Args:
            vector_results: Results from vector search
            keyword_results: Results from keyword search

        Returns:
            Combined and scored results
        """
        # TODO: Implement hybrid scoring
        logger.debug("Result combination called (placeholder)")

        # For now, just return vector results
        return vector_results

    def _apply_recency_weight(
        self,
        results: List[RetrievalResult],
        recency_weight: float
    ) -> List[RetrievalResult]:
        """
        Apply recency weighting to boost recent documents

        Placeholder - will be implemented in task_order: 85

        Args:
            results: Retrieved results
            recency_weight: Weight for recency (0-1)

        Returns:
            Results with adjusted scores
        """
        # TODO: Implement recency weighting
        logger.debug(f"Recency weighting called with weight={recency_weight} (placeholder)")
        return results

    def _diversify_results(
        self,
        results: List[RetrievalResult],
        max_per_doc: int = 3
    ) -> List[RetrievalResult]:
        """
        Diversify results to limit chunks per document

        Prevents single document from dominating results

        Args:
            results: Retrieved results
            max_per_doc: Maximum chunks per document

        Returns:
            Diversified results
        """
        doc_counts: Dict[str, int] = defaultdict(int)
        diversified = []

        for result in results:
            doc_id = result.metadata.get('doc_id', result.doc_id)

            if doc_id:
                count = doc_counts[doc_id]
                if count < max_per_doc:
                    diversified.append(result)
                    doc_counts[doc_id] = count + 1
            else:
                # No doc_id, include result
                diversified.append(result)

        logger.debug(
            f"Diversified from {len(results)} to {len(diversified)} results "
            f"(max {max_per_doc} per document)"
        )

        return diversified

    async def _rerank_results(
        self,
        query: str,
        results: List[RetrievalResult],
        top_k: int
    ) -> List[RetrievalResult]:
        """
        Optional reranking of results

        Placeholder for future reranking implementation (task_order: 82)

        Args:
            query: Original query
            results: Results to rerank
            top_k: Number of results after reranking

        Returns:
            Reranked results
        """
        # TODO: Implement reranking (optional)
        logger.debug("Reranking called (placeholder)")
        return results


class RetrievalEngineFactory:
    """Factory for creating RetrievalEngine instances"""

    @staticmethod
    def create_engine(
        vector_store: QdrantStore,
        embedding_model: BaseEmbedding,
        config: Optional[RetrievalConfig] = None,
        reranker: Optional[Any] = None
    ) -> RetrievalEngine:
        """
        Create a RetrievalEngine with dependencies

        Args:
            vector_store: Qdrant vector store instance
            embedding_model: Embedding model
            config: Optional retrieval configuration
            reranker: Optional reranking model

        Returns:
            Configured RetrievalEngine instance
        """
        return RetrievalEngine(
            vector_store=vector_store,
            embedding_model=embedding_model,
            config=config,
            reranker=reranker
        )
