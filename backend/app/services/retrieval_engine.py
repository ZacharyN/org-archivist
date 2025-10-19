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
from qdrant_client.models import Filter, FieldCondition, MatchAny, MatchValue, Range
from rank_bm25 import BM25L

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

        # BM25 index (will be populated when building index)
        self._bm25_index: Optional[BM25L] = None
        self._bm25_corpus: List[str] = []  # Original texts for retrieval
        self._bm25_metadata: List[Dict[str, Any]] = []  # Metadata for each document
        self._bm25_tokenized: List[List[str]] = []  # Tokenized corpus for indexing

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
        Perform vector similarity search using Qdrant

        Args:
            query_embedding: Query vector
            top_k: Number of results
            filters: Document metadata filters

        Returns:
            List of RetrievalResult objects sorted by relevance
        """
        try:
            # Build Qdrant filter from DocumentFilters
            qdrant_filter = self._build_qdrant_filter(filters) if filters else None

            # Call vector store search
            search_results = await self.vector_store.search_similar(
                query_vector=query_embedding,
                limit=top_k,
                score_threshold=None,  # No hard threshold, we'll apply ranking later
                filter_conditions=None  # Direct filter not used, we use filter object
            )

            # If we have a filter, we need to use the client's search with filter
            if qdrant_filter:
                # Use the QdrantStore's client directly for filtered search
                search_results = self.vector_store.client.search(
                    collection_name=self.vector_store.collection_name,
                    query_vector=query_embedding,
                    limit=top_k,
                    query_filter=qdrant_filter,
                )

                # Format results manually (same as search_similar does)
                formatted_results = []
                for result in search_results:
                    formatted_results.append({
                        "id": result.id,
                        "score": result.score,
                        "text": result.payload.get("text", ""),
                        "metadata": {
                            k: v for k, v in result.payload.items()
                            if k != "text"
                        }
                    })
                search_results = formatted_results

            # Convert to RetrievalResult objects
            retrieval_results = []
            for result in search_results:
                retrieval_result = RetrievalResult(
                    chunk_id=str(result["id"]),
                    text=result["text"],
                    score=result["score"],
                    metadata=result["metadata"],
                    doc_id=result["metadata"].get("doc_id"),
                    chunk_index=result["metadata"].get("chunk_index")
                )
                retrieval_results.append(retrieval_result)

            logger.info(f"Vector search found {len(retrieval_results)} results")
            return retrieval_results

        except Exception as e:
            logger.error(f"Vector search error: {e}", exc_info=True)
            # Return empty results instead of failing the entire retrieval
            return []

    async def _keyword_search(
        self,
        query: str,
        top_k: int,
        filters: Optional[DocumentFilters] = None
    ) -> List[RetrievalResult]:
        """
        Perform BM25 keyword search

        Uses rank-bm25 library for efficient keyword-based retrieval.
        Applies metadata filtering after BM25 scoring.

        Args:
            query: Query text
            top_k: Number of results
            filters: Metadata filters

        Returns:
            List of RetrievalResult objects sorted by BM25 score
        """
        try:
            # Check if BM25 index exists
            if self._bm25_index is None or not self._bm25_corpus:
                logger.warning("BM25 index not built. Building from vector store...")
                await self._build_bm25_index()

                if self._bm25_index is None:
                    logger.warning("BM25 index still empty after build attempt")
                    return []

            # Tokenize query (same preprocessing as corpus)
            tokenized_query = self._tokenize(query)

            logger.debug(f"Query: '{query}' -> Tokens: {tokenized_query}")

            if not tokenized_query:
                logger.warning(f"Query tokenization resulted in empty tokens for query: '{query}'")
                return []

            # Get BM25 scores for all documents
            doc_scores = self._bm25_index.get_scores(tokenized_query)

            logger.debug(f"BM25 scores for {len(doc_scores)} documents: {doc_scores[:5] if len(doc_scores) > 5 else doc_scores}")

            # Create list of (index, score, text, metadata) tuples
            scored_docs = [
                (i, score, self._bm25_corpus[i], self._bm25_metadata[i])
                for i, score in enumerate(doc_scores)
                if score > 0  # Only include documents with non-zero scores
            ]

            logger.debug(f"Found {len(scored_docs)} documents with non-zero scores")

            # Sort by score descending
            scored_docs.sort(key=lambda x: x[1], reverse=True)

            # Apply metadata filtering if provided
            if filters:
                scored_docs = self._filter_bm25_results(scored_docs, filters)

            # Take top-k results
            scored_docs = scored_docs[:top_k]

            # Convert to RetrievalResult objects
            results = []
            for idx, score, text, metadata in scored_docs:
                result = RetrievalResult(
                    chunk_id=metadata.get("chunk_id", f"bm25_{idx}"),
                    text=text,
                    score=float(score),
                    metadata=metadata,
                    doc_id=metadata.get("doc_id"),
                    chunk_index=metadata.get("chunk_index")
                )
                results.append(result)

            logger.info(f"BM25 keyword search returned {len(results)} results")
            return results

        except Exception as e:
            logger.error(f"BM25 keyword search error: {e}", exc_info=True)
            # Return empty results instead of failing
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

    async def build_bm25_index(self):
        """
        Public method to manually build or rebuild BM25 index

        Call this method after adding/removing documents to refresh the index.
        """
        await self._build_bm25_index()

    def _build_qdrant_filter(self, filters: DocumentFilters) -> Optional[Filter]:
        """
        Build Qdrant Filter object from DocumentFilters

        Supports filtering by:
        - doc_types: List of document types
        - years: List of specific years
        - programs: List of programs
        - outcomes: List of outcomes
        - date_range: Tuple of (start_year, end_year)
        - exclude_docs: List of document IDs to exclude

        Args:
            filters: DocumentFilters model

        Returns:
            Qdrant Filter object or None if no filters
        """
        if not filters:
            return None

        must_conditions = []
        must_not_conditions = []

        # Filter by document types (e.g., ["Grant Proposal", "Annual Report"])
        if filters.doc_types:
            must_conditions.append(
                FieldCondition(
                    key="doc_type",
                    match=MatchAny(any=filters.doc_types)
                )
            )

        # Filter by specific years (e.g., [2022, 2023, 2024])
        if filters.years:
            must_conditions.append(
                FieldCondition(
                    key="year",
                    match=MatchAny(any=filters.years)
                )
            )

        # Filter by year range (e.g., (2020, 2024))
        if filters.date_range:
            start_year, end_year = filters.date_range
            must_conditions.append(
                FieldCondition(
                    key="year",
                    range=Range(
                        gte=start_year,
                        lte=end_year
                    )
                )
            )

        # Filter by programs (e.g., ["Early Childhood", "Youth Development"])
        # Note: Programs are stored as arrays, need to check if program is in array
        if filters.programs:
            # For array fields, we match if ANY of the filter values are in the field
            for program in filters.programs:
                must_conditions.append(
                    FieldCondition(
                        key="programs",
                        match=MatchAny(any=[program])
                    )
                )

        # Filter by outcomes (e.g., ["Funded", "Pending"])
        if filters.outcomes:
            must_conditions.append(
                FieldCondition(
                    key="outcome",
                    match=MatchAny(any=filters.outcomes)
                )
            )

        # Exclude specific documents
        if filters.exclude_docs:
            for doc_id in filters.exclude_docs:
                must_not_conditions.append(
                    FieldCondition(
                        key="doc_id",
                        match=MatchValue(value=doc_id)
                    )
                )

        # Build final filter
        if not must_conditions and not must_not_conditions:
            return None

        filter_kwargs = {}
        if must_conditions:
            filter_kwargs["must"] = must_conditions
        if must_not_conditions:
            filter_kwargs["must_not"] = must_not_conditions

        qdrant_filter = Filter(**filter_kwargs)

        logger.debug(
            f"Built Qdrant filter: {len(must_conditions)} must conditions, "
            f"{len(must_not_conditions)} must_not conditions"
        )

        return qdrant_filter

    def _tokenize(self, text: str) -> List[str]:
        """
        Tokenize text for BM25 indexing/search

        Applies basic preprocessing:
        - Lowercase
        - Remove punctuation
        - Split on whitespace
        - Filter out empty strings

        Args:
            text: Text to tokenize

        Returns:
            List of tokens
        """
        # Lowercase
        text = text.lower()

        # Remove punctuation and special characters
        text = re.sub(r'[^\w\s]', ' ', text)

        # Split on whitespace
        tokens = text.split()

        # Filter out empty strings
        tokens = [t for t in tokens if t]

        return tokens

    async def _build_bm25_index(self):
        """
        Build BM25 index from vector store

        Fetches all document chunks from Qdrant and builds BM25 index.
        This should be called once during initialization or when documents are added.
        """
        try:
            logger.info("Building BM25 index from vector store...")

            # Fetch all documents from Qdrant
            # Note: This is a simplified approach. For production, you'd want to:
            # 1. Cache the BM25 index to disk
            # 2. Update incrementally when documents are added/removed
            # 3. Use a more efficient storage mechanism

            # Get collection info to know how many points we have
            collection_info = self.vector_store.client.get_collection(
                collection_name=self.vector_store.collection_name
            )

            total_points = collection_info.points_count
            logger.info(f"Total points in collection: {total_points}")

            if total_points == 0:
                logger.warning("No documents in vector store to build BM25 index")
                return

            # Scroll through all points (fetch in batches)
            # Qdrant scroll API is efficient for large collections
            offset = None
            batch_size = 100

            corpus = []
            metadata_list = []
            tokenized_corpus = []

            while True:
                # Scroll through points
                results, next_offset = self.vector_store.client.scroll(
                    collection_name=self.vector_store.collection_name,
                    limit=batch_size,
                    offset=offset,
                    with_payload=True,
                    with_vectors=False  # Don't need vectors for BM25
                )

                # Process batch
                for point in results:
                    text = point.payload.get("text", "")
                    if text:
                        corpus.append(text)

                        # Extract metadata (exclude text field)
                        metadata = {k: v for k, v in point.payload.items() if k != "text"}
                        metadata["chunk_id"] = str(point.id)
                        metadata_list.append(metadata)

                        # Tokenize for BM25
                        tokens = self._tokenize(text)
                        tokenized_corpus.append(tokens)

                # Check if we've reached the end
                if next_offset is None:
                    break

                offset = next_offset

            # Build BM25 index
            if tokenized_corpus:
                self._bm25_corpus = corpus
                self._bm25_metadata = metadata_list
                self._bm25_tokenized = tokenized_corpus
                self._bm25_index = BM25L(tokenized_corpus)

                logger.info(f"BM25 index built successfully with {len(corpus)} documents")
            else:
                logger.warning("No documents found to build BM25 index")

        except Exception as e:
            logger.error(f"Error building BM25 index: {e}", exc_info=True)

    def _filter_bm25_results(
        self,
        scored_docs: List[Tuple[int, float, str, Dict[str, Any]]],
        filters: DocumentFilters
    ) -> List[Tuple[int, float, str, Dict[str, Any]]]:
        """
        Apply metadata filters to BM25 search results

        Args:
            scored_docs: List of (index, score, text, metadata) tuples
            filters: DocumentFilters to apply

        Returns:
            Filtered list of scored documents
        """
        filtered = []

        for idx, score, text, metadata in scored_docs:
            # Check each filter condition
            if filters.doc_types:
                if metadata.get("doc_type") not in filters.doc_types:
                    continue

            if filters.years:
                if metadata.get("year") not in filters.years:
                    continue

            if filters.date_range:
                start_year, end_year = filters.date_range
                doc_year = metadata.get("year")
                if doc_year is None or not (start_year <= doc_year <= end_year):
                    continue

            if filters.programs:
                # Programs stored as array, check if any program matches
                doc_programs = metadata.get("programs", [])
                if not any(p in doc_programs for p in filters.programs):
                    continue

            if filters.outcomes:
                if metadata.get("outcome") not in filters.outcomes:
                    continue

            if filters.exclude_docs:
                if metadata.get("doc_id") in filters.exclude_docs:
                    continue

            # Passed all filters
            filtered.append((idx, score, text, metadata))

        logger.debug(
            f"Filtered BM25 results from {len(scored_docs)} to {len(filtered)}"
        )

        return filtered

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
