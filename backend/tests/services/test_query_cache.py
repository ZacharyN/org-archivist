"""
Tests for Query Result Cache

Tests caching functionality including:
- Cache hit/miss behavior
- TTL expiration
- LRU eviction
- Thread safety
- Cache invalidation
- Metrics tracking
"""

import pytest
import asyncio
import time
import threading
from typing import List

from app.services.query_cache import (
    QueryCache,
    CachedRetrievalEngine,
    CacheEntry,
    CacheMetrics
)
from app.services.retrieval_engine import RetrievalResult
from app.models.document import DocumentFilters


# ============================================================================
# Mock Objects
# ============================================================================

class MockRetrievalEngine:
    """Mock retrieval engine for testing"""

    def __init__(self):
        self.call_count = 0
        self.last_query = None

    async def retrieve(
        self,
        query: str,
        top_k: int = 5,
        filters: DocumentFilters = None,
        recency_weight: float = None
    ) -> List[RetrievalResult]:
        """Mock retrieve method"""
        self.call_count += 1
        self.last_query = query

        # Return dummy results
        return [
            RetrievalResult(
                chunk_id=f"chunk_{i}",
                text=f"Result {i} for query: {query}",
                score=0.9 - (i * 0.1),
                metadata={"doc_id": f"doc_{i}"},
                doc_id=f"doc_{i}",
                chunk_index=0
            )
            for i in range(top_k)
        ]


# ============================================================================
# Cache Key Generation Tests
# ============================================================================

def test_cache_key_generation():
    """Test that cache keys are generated consistently"""
    cache = QueryCache(max_size=10, ttl_seconds=60)

    # Same parameters should generate same key
    key1 = cache._generate_cache_key("test query", top_k=5, filters=None, recency_weight=0.7)
    key2 = cache._generate_cache_key("test query", top_k=5, filters=None, recency_weight=0.7)

    assert key1 == key2, "Same parameters should generate same cache key"


def test_cache_key_different_params():
    """Test that different parameters generate different keys"""
    cache = QueryCache(max_size=10, ttl_seconds=60)

    key1 = cache._generate_cache_key("query 1", top_k=5, filters=None, recency_weight=0.7)
    key2 = cache._generate_cache_key("query 2", top_k=5, filters=None, recency_weight=0.7)
    key3 = cache._generate_cache_key("query 1", top_k=10, filters=None, recency_weight=0.7)

    assert key1 != key2, "Different queries should have different keys"
    assert key1 != key3, "Different top_k should have different keys"


def test_cache_key_with_filters():
    """Test cache key generation with filters"""
    cache = QueryCache(max_size=10, ttl_seconds=60)

    filters1 = DocumentFilters(doc_types=["Grant Proposal"])
    filters2 = DocumentFilters(doc_types=["Annual Report"])

    key1 = cache._generate_cache_key("test", top_k=5, filters=filters1, recency_weight=0.7)
    key2 = cache._generate_cache_key("test", top_k=5, filters=filters2, recency_weight=0.7)

    assert key1 != key2, "Different filters should have different keys"


def test_cache_key_normalization():
    """Test that queries are normalized (case-insensitive, whitespace)"""
    cache = QueryCache(max_size=10, ttl_seconds=60)

    # These should generate the SAME key (normalized)
    key1 = cache._generate_cache_key("Test Query", top_k=5, filters=None, recency_weight=0.7)
    key2 = cache._generate_cache_key("test query", top_k=5, filters=None, recency_weight=0.7)
    key3 = cache._generate_cache_key("  test   query  ", top_k=5, filters=None, recency_weight=0.7)

    assert key1 == key2, "Case should be normalized"
    assert key1 == key3, "Whitespace should be normalized"


# ============================================================================
# Basic Cache Operations Tests
# ============================================================================

def test_cache_put_and_get():
    """Test basic put and get operations"""
    cache = QueryCache(max_size=10, ttl_seconds=60)

    # Create mock results
    results = [
        RetrievalResult(
            chunk_id="chunk_1",
            text="Test result",
            score=0.9,
            metadata={"doc_id": "doc_1"}
        )
    ]

    # Put in cache
    cache.put(query="test query", results=results, top_k=5)

    # Get from cache
    cached_results = cache.get(query="test query", top_k=5)

    assert cached_results is not None, "Should retrieve cached results"
    assert len(cached_results) == 1
    assert cached_results[0].chunk_id == "chunk_1"


def test_cache_miss():
    """Test cache miss for non-existent query"""
    cache = QueryCache(max_size=10, ttl_seconds=60)

    # Try to get non-existent query
    cached_results = cache.get(query="nonexistent query", top_k=5)

    assert cached_results is None, "Should return None for cache miss"


def test_cache_hit_updates_access_count():
    """Test that cache hits update access count"""
    cache = QueryCache(max_size=10, ttl_seconds=60)

    results = [RetrievalResult(chunk_id="1", text="test", score=0.9, metadata={})]

    cache.put(query="test", results=results, top_k=5)

    # Access multiple times
    cache.get(query="test", top_k=5)
    cache.get(query="test", top_k=5)
    cache.get(query="test", top_k=5)

    # Check metrics
    metrics = cache.get_metrics()
    assert metrics.hits == 3, "Should track 3 cache hits"


# ============================================================================
# TTL (Time-To-Live) Tests
# ============================================================================

def test_cache_ttl_expiration():
    """Test that entries expire after TTL"""
    cache = QueryCache(max_size=10, ttl_seconds=1)  # 1 second TTL

    results = [RetrievalResult(chunk_id="1", text="test", score=0.9, metadata={})]

    cache.put(query="test", results=results, top_k=5)

    # Should be cached immediately
    cached = cache.get(query="test", top_k=5)
    assert cached is not None, "Should be cached immediately"

    # Wait for expiration
    time.sleep(1.5)

    # Should be expired now
    cached = cache.get(query="test", top_k=5)
    assert cached is None, "Should be expired after TTL"


def test_cache_ttl_not_expired():
    """Test that entries don't expire before TTL"""
    cache = QueryCache(max_size=10, ttl_seconds=5)  # 5 second TTL

    results = [RetrievalResult(chunk_id="1", text="test", score=0.9, metadata={})]

    cache.put(query="test", results=results, top_k=5)

    # Wait but not past TTL
    time.sleep(2)

    # Should still be cached
    cached = cache.get(query="test", top_k=5)
    assert cached is not None, "Should not be expired yet"


# ============================================================================
# LRU Eviction Tests
# ============================================================================

def test_cache_lru_eviction():
    """Test that LRU eviction works correctly"""
    cache = QueryCache(max_size=3, ttl_seconds=60)  # Small cache

    # Fill cache
    for i in range(3):
        results = [RetrievalResult(chunk_id=f"{i}", text=f"test{i}", score=0.9, metadata={})]
        cache.put(query=f"query{i}", results=results, top_k=5)

    assert len(cache) == 3, "Cache should be full"

    # Add one more - should evict least recently used (query0)
    results = [RetrievalResult(chunk_id="3", text="test3", score=0.9, metadata={})]
    cache.put(query="query3", results=results, top_k=5)

    assert len(cache) == 3, "Cache should still be at max size"

    # query0 should be evicted (least recently used)
    cached = cache.get(query="query0", top_k=5)
    assert cached is None, "query0 should be evicted"

    # query1, query2, query3 should still be cached
    assert cache.get(query="query1", top_k=5) is not None
    assert cache.get(query="query2", top_k=5) is not None
    assert cache.get(query="query3", top_k=5) is not None


def test_cache_lru_refresh():
    """Test that accessing an entry refreshes its LRU position"""
    cache = QueryCache(max_size=3, ttl_seconds=60)

    # Fill cache
    for i in range(3):
        results = [RetrievalResult(chunk_id=f"{i}", text=f"test{i}", score=0.9, metadata={})]
        cache.put(query=f"query{i}", results=results, top_k=5)

    # Access query0 (should move to most recently used)
    cache.get(query="query0", top_k=5)

    # Add new entry - should evict query1 (now least recently used)
    results = [RetrievalResult(chunk_id="3", text="test3", score=0.9, metadata={})]
    cache.put(query="query3", results=results, top_k=5)

    # query1 should be evicted
    assert cache.get(query="query1", top_k=5) is None

    # query0, query2, query3 should still be cached
    assert cache.get(query="query0", top_k=5) is not None
    assert cache.get(query="query2", top_k=5) is not None
    assert cache.get(query="query3", top_k=5) is not None


# ============================================================================
# Cache Invalidation Tests
# ============================================================================

def test_cache_invalidate_all():
    """Test invalidating entire cache"""
    cache = QueryCache(max_size=10, ttl_seconds=60)

    # Add multiple entries
    for i in range(5):
        results = [RetrievalResult(chunk_id=f"{i}", text=f"test{i}", score=0.9, metadata={})]
        cache.put(query=f"query{i}", results=results, top_k=5)

    assert len(cache) == 5, "Should have 5 entries"

    # Invalidate all
    cache.invalidate_all()

    assert len(cache) == 0, "Cache should be empty after invalidation"

    # All queries should miss
    for i in range(5):
        assert cache.get(query=f"query{i}", top_k=5) is None


def test_cache_cleanup_expired():
    """Test cleanup of expired entries"""
    cache = QueryCache(max_size=10, ttl_seconds=1)  # 1 second TTL

    # Add entries
    for i in range(5):
        results = [RetrievalResult(chunk_id=f"{i}", text=f"test{i}", score=0.9, metadata={})]
        cache.put(query=f"query{i}", results=results, top_k=5)

    assert len(cache) == 5

    # Wait for expiration
    time.sleep(1.5)

    # Cleanup expired
    cache.cleanup_expired()

    assert len(cache) == 0, "All entries should be expired and removed"


# ============================================================================
# Metrics Tests
# ============================================================================

def test_cache_metrics():
    """Test cache metrics tracking"""
    cache = QueryCache(max_size=10, ttl_seconds=60, enable_metrics=True)

    results = [RetrievalResult(chunk_id="1", text="test", score=0.9, metadata={})]

    # Cache miss
    cache.get(query="test", top_k=5)

    metrics = cache.get_metrics()
    assert metrics.total_queries == 1
    assert metrics.misses == 1
    assert metrics.hits == 0

    # Put in cache
    cache.put(query="test", results=results, top_k=5)

    # Cache hit
    cache.get(query="test", top_k=5)

    metrics = cache.get_metrics()
    assert metrics.total_queries == 2
    assert metrics.misses == 1
    assert metrics.hits == 1
    assert metrics.hit_rate == 0.5


def test_cache_metrics_eviction():
    """Test that evictions are tracked in metrics"""
    cache = QueryCache(max_size=2, ttl_seconds=60, enable_metrics=True)

    # Fill cache and trigger eviction
    for i in range(3):
        results = [RetrievalResult(chunk_id=f"{i}", text=f"test{i}", score=0.9, metadata={})]
        cache.put(query=f"query{i}", results=results, top_k=5)

    metrics = cache.get_metrics()
    assert metrics.evictions == 1, "Should track 1 eviction"


def test_cache_stats():
    """Test cache statistics reporting"""
    cache = QueryCache(max_size=10, ttl_seconds=60)

    stats = cache.get_stats()

    assert "cache_size" in stats
    assert "max_size" in stats
    assert "hit_rate" in stats
    assert stats["max_size"] == 10
    assert stats["ttl_seconds"] == 60


# ============================================================================
# Thread Safety Tests
# ============================================================================

def test_cache_thread_safety():
    """Test that cache operations are thread-safe"""
    cache = QueryCache(max_size=100, ttl_seconds=60)

    results = [RetrievalResult(chunk_id="1", text="test", score=0.9, metadata={})]

    # Function to put entries concurrently
    def put_worker(worker_id: int):
        for i in range(10):
            cache.put(
                query=f"worker{worker_id}_query{i}",
                results=results,
                top_k=5
            )

    # Function to get entries concurrently
    def get_worker(worker_id: int):
        for i in range(10):
            cache.get(
                query=f"worker{worker_id}_query{i}",
                top_k=5
            )

    # Run concurrent puts
    put_threads = [threading.Thread(target=put_worker, args=(i,)) for i in range(5)]
    for t in put_threads:
        t.start()
    for t in put_threads:
        t.join()

    # Run concurrent gets
    get_threads = [threading.Thread(target=get_worker, args=(i,)) for i in range(5)]
    for t in get_threads:
        t.start()
    for t in get_threads:
        t.join()

    # Cache should be in consistent state
    assert len(cache) > 0
    assert len(cache) <= cache.max_size

    print(f"[OK] Thread safety test: Cache has {len(cache)} entries after concurrent operations")


# ============================================================================
# CachedRetrievalEngine Tests
# ============================================================================

@pytest.mark.asyncio
async def test_cached_retrieval_engine_cache_miss():
    """Test CachedRetrievalEngine with cache miss"""
    mock_engine = MockRetrievalEngine()
    cache = QueryCache(max_size=10, ttl_seconds=60)
    cached_engine = CachedRetrievalEngine(mock_engine, cache=cache)

    # First call - cache miss
    results = await cached_engine.retrieve(query="test query", top_k=5)

    assert len(results) == 5
    assert mock_engine.call_count == 1, "Should call underlying engine on cache miss"

    # Check cache was populated
    metrics = cache.get_metrics()
    assert metrics.misses == 1


@pytest.mark.asyncio
async def test_cached_retrieval_engine_cache_hit():
    """Test CachedRetrievalEngine with cache hit"""
    mock_engine = MockRetrievalEngine()
    cache = QueryCache(max_size=10, ttl_seconds=60)
    cached_engine = CachedRetrievalEngine(mock_engine, cache=cache)

    # First call - cache miss
    await cached_engine.retrieve(query="test query", top_k=5)

    # Second call - should be cache hit
    results = await cached_engine.retrieve(query="test query", top_k=5)

    assert len(results) == 5
    assert mock_engine.call_count == 1, "Should not call engine again on cache hit"

    # Check cache metrics
    metrics = cache.get_metrics()
    assert metrics.hits == 1
    assert metrics.misses == 1


@pytest.mark.asyncio
async def test_cached_retrieval_engine_different_params():
    """Test that different parameters cause cache miss"""
    mock_engine = MockRetrievalEngine()
    cache = QueryCache(max_size=10, ttl_seconds=60)
    cached_engine = CachedRetrievalEngine(mock_engine, cache=cache)

    # Call with different parameters
    await cached_engine.retrieve(query="test", top_k=5)
    await cached_engine.retrieve(query="test", top_k=10)  # Different top_k
    await cached_engine.retrieve(query="other", top_k=5)  # Different query

    # Should have called engine 3 times (3 different cache keys)
    assert mock_engine.call_count == 3


@pytest.mark.asyncio
async def test_cached_retrieval_engine_disabled():
    """Test CachedRetrievalEngine with caching disabled"""
    mock_engine = MockRetrievalEngine()
    cached_engine = CachedRetrievalEngine(mock_engine, enable_cache=False)

    # Multiple calls with same params
    await cached_engine.retrieve(query="test", top_k=5)
    await cached_engine.retrieve(query="test", top_k=5)
    await cached_engine.retrieve(query="test", top_k=5)

    # Should call engine every time (no caching)
    assert mock_engine.call_count == 3


@pytest.mark.asyncio
async def test_cached_retrieval_engine_invalidation():
    """Test cache invalidation in CachedRetrievalEngine"""
    mock_engine = MockRetrievalEngine()
    cache = QueryCache(max_size=10, ttl_seconds=60)
    cached_engine = CachedRetrievalEngine(mock_engine, cache=cache)

    # Populate cache
    await cached_engine.retrieve(query="test", top_k=5)

    # Should be cached
    await cached_engine.retrieve(query="test", top_k=5)
    assert mock_engine.call_count == 1

    # Invalidate cache
    cached_engine.invalidate_cache()

    # Should call engine again (cache miss after invalidation)
    await cached_engine.retrieve(query="test", top_k=5)
    assert mock_engine.call_count == 2


# ============================================================================
# Performance Tests
# ============================================================================

def test_cache_performance():
    """Test cache performance with many entries"""
    import time

    cache = QueryCache(max_size=1000, ttl_seconds=60)

    results = [RetrievalResult(chunk_id="1", text="test", score=0.9, metadata={})]

    # Benchmark puts
    start = time.perf_counter()
    for i in range(1000):
        cache.put(query=f"query{i}", results=results, top_k=5)
    put_time = time.perf_counter() - start

    # Benchmark gets (hits)
    start = time.perf_counter()
    for i in range(1000):
        cache.get(query=f"query{i}", top_k=5)
    get_time = time.perf_counter() - start

    print(f"\n[Performance] 1000 puts: {put_time*1000:.2f}ms ({put_time/1000*1000:.3f}ms each)")
    print(f"[Performance] 1000 gets: {get_time*1000:.2f}ms ({get_time/1000*1000:.3f}ms each)")

    # Should be fast (under 1 second for 1000 operations)
    assert put_time < 1.0, "Puts should be fast"
    assert get_time < 1.0, "Gets should be fast"


if __name__ == "__main__":
    """
    Run tests with pytest:

        pytest backend/tests/test_query_cache.py -v

    Or run with this script:

        python backend/tests/test_query_cache.py
    """
    pytest.main([__file__, "-v", "-s"])
