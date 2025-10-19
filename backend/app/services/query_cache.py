"""
Query Result Cache Service

Implements LRU caching for retrieval engine results with:
- Time-to-live (TTL) expiration
- Thread-safe operations
- Cache hit/miss metrics
- Memory-efficient size limits
- Cache invalidation

This cache significantly improves performance for repeated queries.
"""

import hashlib
import json
import time
import threading
from typing import List, Optional, Dict, Any
from collections import OrderedDict
from dataclasses import dataclass
import logging

from app.services.retrieval_engine import RetrievalResult
from app.models.document import DocumentFilters


logger = logging.getLogger(__name__)


@dataclass
class CacheEntry:
    """
    Single cache entry with TTL and metadata
    """
    results: List[RetrievalResult]
    timestamp: float  # Unix timestamp when cached
    access_count: int  # Number of times accessed
    query: str  # Original query (for debugging)


@dataclass
class CacheMetrics:
    """
    Cache performance metrics
    """
    hits: int = 0
    misses: int = 0
    evictions: int = 0
    invalidations: int = 0
    total_queries: int = 0

    @property
    def hit_rate(self) -> float:
        """Calculate cache hit rate"""
        if self.total_queries == 0:
            return 0.0
        return self.hits / self.total_queries

    @property
    def miss_rate(self) -> float:
        """Calculate cache miss rate"""
        if self.total_queries == 0:
            return 0.0
        return self.misses / self.total_queries


class QueryCache:
    """
    LRU cache with TTL for retrieval engine query results

    Thread-safe implementation using locks.
    Automatically evicts expired entries and enforces size limits.
    """

    def __init__(
        self,
        max_size: int = 1000,
        ttl_seconds: int = 3600,  # 1 hour default
        enable_metrics: bool = True
    ):
        """
        Initialize query cache

        Args:
            max_size: Maximum number of entries (LRU eviction when exceeded)
            ttl_seconds: Time-to-live for cache entries in seconds
            enable_metrics: Whether to track cache metrics
        """
        self.max_size = max_size
        self.ttl_seconds = ttl_seconds
        self.enable_metrics = enable_metrics

        # Cache storage (OrderedDict for LRU ordering)
        self._cache: OrderedDict[str, CacheEntry] = OrderedDict()

        # Thread safety
        self._lock = threading.RLock()

        # Metrics
        self._metrics = CacheMetrics()

        logger.info(
            f"QueryCache initialized: max_size={max_size}, "
            f"ttl={ttl_seconds}s, metrics={enable_metrics}"
        )

    def _generate_cache_key(
        self,
        query: str,
        top_k: int,
        filters: Optional[DocumentFilters],
        recency_weight: Optional[float],
        **kwargs
    ) -> str:
        """
        Generate deterministic cache key from query parameters

        Cache key is a hash of all parameters that affect results:
        - Query text
        - top_k
        - Filters (if any)
        - Recency weight
        - Any other retrieval parameters

        Args:
            query: Query string
            top_k: Number of results
            filters: Document filters
            recency_weight: Recency weighting
            **kwargs: Additional parameters

        Returns:
            MD5 hash as cache key
        """
        # Build a dictionary of all parameters
        # Normalize query: collapse all whitespace into single spaces
        normalized_query = ' '.join(query.lower().split())
        params = {
            "query": normalized_query,
            "top_k": top_k,
            "recency_weight": recency_weight
        }

        # Add filters if present
        if filters:
            # Convert Pydantic model to dict, handling None values
            # Use model_dump() for Pydantic models (not asdict which is for dataclasses)
            filter_dict = {
                k: v for k, v in filters.model_dump().items()
                if v is not None
            }
            params["filters"] = filter_dict

        # Add any additional kwargs
        params.update(kwargs)

        # Create deterministic JSON string (sorted keys)
        params_json = json.dumps(params, sort_keys=True)

        # Hash to create cache key
        cache_key = hashlib.md5(params_json.encode()).hexdigest()

        return cache_key

    def get(
        self,
        query: str,
        top_k: int,
        filters: Optional[DocumentFilters] = None,
        recency_weight: Optional[float] = None,
        **kwargs
    ) -> Optional[List[RetrievalResult]]:
        """
        Retrieve results from cache if available and not expired

        Args:
            query: Query string
            top_k: Number of results
            filters: Document filters
            recency_weight: Recency weighting
            **kwargs: Additional parameters

        Returns:
            Cached results if found and valid, None otherwise
        """
        cache_key = self._generate_cache_key(
            query, top_k, filters, recency_weight, **kwargs
        )

        with self._lock:
            # Update metrics
            if self.enable_metrics:
                self._metrics.total_queries += 1

            # Check if key exists
            if cache_key not in self._cache:
                if self.enable_metrics:
                    self._metrics.misses += 1
                logger.debug(f"Cache MISS: {query[:50]}...")
                return None

            # Get entry
            entry = self._cache[cache_key]

            # Check if expired
            current_time = time.time()
            age_seconds = current_time - entry.timestamp

            if age_seconds > self.ttl_seconds:
                # Expired - remove and return None
                del self._cache[cache_key]
                if self.enable_metrics:
                    self._metrics.misses += 1
                    self._metrics.evictions += 1
                logger.debug(
                    f"Cache MISS (expired): {query[:50]}... "
                    f"(age: {age_seconds:.1f}s > TTL: {self.ttl_seconds}s)"
                )
                return None

            # Valid cache hit - move to end (most recently used)
            self._cache.move_to_end(cache_key)

            # Update entry access count
            entry.access_count += 1

            # Update metrics
            if self.enable_metrics:
                self._metrics.hits += 1

            logger.debug(
                f"Cache HIT: {query[:50]}... "
                f"(age: {age_seconds:.1f}s, access_count: {entry.access_count})"
            )

            return entry.results

    def put(
        self,
        query: str,
        results: List[RetrievalResult],
        top_k: int,
        filters: Optional[DocumentFilters] = None,
        recency_weight: Optional[float] = None,
        **kwargs
    ):
        """
        Store results in cache

        Args:
            query: Query string
            results: Retrieval results to cache
            top_k: Number of results
            filters: Document filters
            recency_weight: Recency weighting
            **kwargs: Additional parameters
        """
        cache_key = self._generate_cache_key(
            query, top_k, filters, recency_weight, **kwargs
        )

        with self._lock:
            # Check if we need to evict (LRU)
            if len(self._cache) >= self.max_size and cache_key not in self._cache:
                # Remove least recently used (first item)
                evicted_key, evicted_entry = self._cache.popitem(last=False)
                if self.enable_metrics:
                    self._metrics.evictions += 1
                logger.debug(
                    f"Cache EVICT (LRU): {evicted_entry.query[:50]}... "
                    f"(access_count: {evicted_entry.access_count})"
                )

            # Create cache entry
            entry = CacheEntry(
                results=results,
                timestamp=time.time(),
                access_count=0,
                query=query
            )

            # Store in cache (adds to end - most recently used)
            self._cache[cache_key] = entry

            logger.debug(
                f"Cache PUT: {query[:50]}... "
                f"({len(results)} results, cache_size={len(self._cache)})"
            )

    def invalidate_all(self):
        """
        Invalidate (clear) entire cache

        Call this when documents are added/removed to ensure cache freshness.
        """
        with self._lock:
            num_entries = len(self._cache)
            self._cache.clear()

            if self.enable_metrics:
                self._metrics.invalidations += num_entries

            logger.info(f"Cache invalidated: {num_entries} entries cleared")

    def invalidate_by_doc_id(self, doc_id: str):
        """
        Invalidate cache entries that may contain a specific document

        This is a conservative approach - we can't easily determine which
        queries returned a specific document, so we invalidate all.

        Future improvement: Track doc_ids in cache entries for selective invalidation.

        Args:
            doc_id: Document ID that was added/modified/deleted
        """
        # For now, just invalidate all (simple but safe)
        self.invalidate_all()
        logger.info(f"Cache invalidated due to document change: {doc_id}")

    def cleanup_expired(self):
        """
        Remove all expired entries from cache

        Can be called periodically to free memory.
        """
        with self._lock:
            current_time = time.time()
            expired_keys = []

            # Find expired entries
            for cache_key, entry in self._cache.items():
                age_seconds = current_time - entry.timestamp
                if age_seconds > self.ttl_seconds:
                    expired_keys.append(cache_key)

            # Remove expired entries
            for cache_key in expired_keys:
                del self._cache[cache_key]
                if self.enable_metrics:
                    self._metrics.evictions += 1

            if expired_keys:
                logger.info(
                    f"Cache cleanup: {len(expired_keys)} expired entries removed"
                )

    def get_metrics(self) -> CacheMetrics:
        """
        Get current cache metrics

        Returns:
            CacheMetrics object with hit/miss stats
        """
        with self._lock:
            # Return a copy to prevent external modification
            return CacheMetrics(
                hits=self._metrics.hits,
                misses=self._metrics.misses,
                evictions=self._metrics.evictions,
                invalidations=self._metrics.invalidations,
                total_queries=self._metrics.total_queries
            )

    def get_stats(self) -> Dict[str, Any]:
        """
        Get comprehensive cache statistics

        Returns:
            Dictionary with cache stats
        """
        with self._lock:
            metrics = self.get_metrics()

            return {
                "cache_size": len(self._cache),
                "max_size": self.max_size,
                "ttl_seconds": self.ttl_seconds,
                "hits": metrics.hits,
                "misses": metrics.misses,
                "evictions": metrics.evictions,
                "invalidations": metrics.invalidations,
                "total_queries": metrics.total_queries,
                "hit_rate": f"{metrics.hit_rate:.2%}",
                "miss_rate": f"{metrics.miss_rate:.2%}",
            }

    def reset_metrics(self):
        """Reset all cache metrics to zero"""
        with self._lock:
            self._metrics = CacheMetrics()
            logger.info("Cache metrics reset")

    def __len__(self) -> int:
        """Return current number of cache entries"""
        with self._lock:
            return len(self._cache)

    def __repr__(self) -> str:
        """String representation of cache"""
        with self._lock:
            metrics = self.get_metrics()
            return (
                f"QueryCache(size={len(self._cache)}/{self.max_size}, "
                f"hit_rate={metrics.hit_rate:.2%}, "
                f"ttl={self.ttl_seconds}s)"
            )


class CachedRetrievalEngine:
    """
    Wrapper around RetrievalEngine that adds caching

    This class provides the same interface as RetrievalEngine but with
    transparent caching of query results.
    """

    def __init__(
        self,
        retrieval_engine,
        cache: Optional[QueryCache] = None,
        enable_cache: bool = True
    ):
        """
        Initialize cached retrieval engine

        Args:
            retrieval_engine: RetrievalEngine instance to wrap
            cache: Optional QueryCache instance (creates default if None)
            enable_cache: Whether caching is enabled
        """
        self.engine = retrieval_engine
        self.enable_cache = enable_cache

        # Create default cache if not provided
        if cache is None and enable_cache:
            cache = QueryCache(
                max_size=1000,
                ttl_seconds=3600,
                enable_metrics=True
            )

        self.cache = cache

        logger.info(
            f"CachedRetrievalEngine initialized: "
            f"caching={'enabled' if enable_cache else 'disabled'}"
        )

    async def retrieve(
        self,
        query: str,
        top_k: int = 5,
        filters: Optional[DocumentFilters] = None,
        recency_weight: Optional[float] = None
    ) -> List[RetrievalResult]:
        """
        Retrieve results with caching

        Checks cache first, falls back to engine if cache miss.

        Args:
            query: Query string
            top_k: Number of results
            filters: Document filters
            recency_weight: Recency weighting

        Returns:
            List of RetrievalResult objects
        """
        # If caching disabled, just call engine
        if not self.enable_cache or self.cache is None:
            return await self.engine.retrieve(
                query=query,
                top_k=top_k,
                filters=filters,
                recency_weight=recency_weight
            )

        # Check cache
        cached_results = self.cache.get(
            query=query,
            top_k=top_k,
            filters=filters,
            recency_weight=recency_weight
        )

        if cached_results is not None:
            # Cache hit - return cached results
            return cached_results

        # Cache miss - retrieve from engine
        results = await self.engine.retrieve(
            query=query,
            top_k=top_k,
            filters=filters,
            recency_weight=recency_weight
        )

        # Store in cache
        self.cache.put(
            query=query,
            results=results,
            top_k=top_k,
            filters=filters,
            recency_weight=recency_weight
        )

        return results

    def invalidate_cache(self):
        """Invalidate entire cache"""
        if self.cache:
            self.cache.invalidate_all()

    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        if self.cache:
            return self.cache.get_stats()
        return {}

    def __getattr__(self, name):
        """
        Proxy all other attributes to underlying engine

        This allows CachedRetrievalEngine to be used as drop-in replacement
        for RetrievalEngine.
        """
        return getattr(self.engine, name)
