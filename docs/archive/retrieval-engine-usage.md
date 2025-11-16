# Retrieval Engine Usage Guide

**Comprehensive guide for using the Org Archivist Retrieval Engine**

---

## Table of Contents

1. [Overview](#overview)
2. [Architecture](#architecture)
3. [Getting Started](#getting-started)
4. [Configuration](#configuration)
5. [Query Examples](#query-examples)
6. [Metadata Filtering](#metadata-filtering)
7. [Best Practices](#best-practices)
8. [Performance Tuning](#performance-tuning)
9. [Caching](#caching)
10. [Troubleshooting](#troubleshooting)
11. [API Reference](#api-reference)

---

## Overview

The Retrieval Engine is the core component of the Org Archivist RAG (Retrieval-Augmented Generation) system. It combines multiple search techniques to find the most relevant content from your document library.

### Key Features

- **Hybrid Search**: Combines vector similarity (semantic) with keyword search (BM25)
- **Metadata Filtering**: Filter by document type, year, program, outcome, etc.
- **Recency Weighting**: Boost recent documents while still retrieving relevant older content
- **Result Diversification**: Limit chunks per document to ensure variety
- **Optional Reranking**: Use cross-encoder models for improved relevance
- **Query Caching**: LRU cache with TTL for repeated queries
- **Performance**: Sub-second retrieval for most queries

### Use Cases

Perfect for:
- Finding relevant content for grant proposal sections
- Locating organizational capacity information
- Retrieving program descriptions and outcomes
- Gathering budget and financial data
- Pulling citations from past successful proposals

---

## Architecture

### Retrieval Pipeline

The retrieval engine processes queries through multiple stages:

```
1. Query Processing
   ↓
2. Query Embedding Generation
   ↓
3. Vector Similarity Search (semantic)
   ↓
4. BM25 Keyword Search (exact matches)
   ↓
5. Hybrid Score Combination
   ↓
6. Recency Weighting (boost recent docs)
   ↓
7. Result Diversification (limit per doc)
   ↓
8. Optional Reranking (cross-encoder)
   ↓
9. Return Top-K Results
```

### Components

- **Vector Store (Qdrant)**: Stores document embeddings for semantic search
- **BM25 Index**: In-memory index for keyword-based retrieval
- **Embedding Model**: OpenAI text-embedding-3-small (or configurable)
- **Reranker** (optional): Cross-encoder models for improved ranking
- **Cache Layer**: LRU cache for repeated queries

---

## Getting Started

### Basic Usage

```python
from app.services.retrieval_engine import RetrievalEngine, RetrievalConfig
from app.services.vector_store import QdrantStore, VectorStoreConfig
from llama_index.embeddings.openai import OpenAIEmbedding

# Initialize vector store
vector_store_config = VectorStoreConfig(
    host="localhost",
    port=6333,
    collection_name="org_archivist_docs"
)
vector_store = QdrantStore(vector_store_config)

# Initialize embedding model
embedding_model = OpenAIEmbedding(
    model="text-embedding-3-small",
    api_key="your-api-key"
)

# Create retrieval engine
engine = RetrievalEngine(
    vector_store=vector_store,
    embedding_model=embedding_model
)

# Build BM25 index (required for keyword search)
await engine.build_bm25_index()

# Perform retrieval
results = await engine.retrieve(
    query="organizational capacity and staff qualifications",
    top_k=5
)

# Process results
for result in results:
    print(f"Score: {result.score:.4f}")
    print(f"Document: {result.metadata['filename']}")
    print(f"Text: {result.text[:200]}...")
    print("---")
```

### With Caching

```python
from app.services.query_cache import CachedRetrievalEngine, QueryCache

# Create cache (1 hour TTL, 1000 entry max)
cache = QueryCache(
    max_size=1000,
    ttl_seconds=3600,
    enable_metrics=True
)

# Wrap engine with caching
cached_engine = CachedRetrievalEngine(
    retrieval_engine=engine,
    cache=cache
)

# Use cached engine (same interface)
results = await cached_engine.retrieve(
    query="program evaluation and outcomes",
    top_k=5
)

# Check cache stats
stats = cached_engine.get_cache_stats()
print(f"Cache hit rate: {stats['hit_rate']}")
```

---

## Configuration

### RetrievalConfig Options

```python
from app.services.retrieval_engine import RetrievalConfig

config = RetrievalConfig(
    # Hybrid search weights (must sum to 1.0)
    vector_weight=0.7,      # Weight for semantic similarity (default: 0.7)
    keyword_weight=0.3,     # Weight for keyword matching (default: 0.3)

    # Recency weighting
    recency_weight=0.7,     # How much to boost recent docs (0-1, default: 0.7)

    # Result diversification
    max_per_doc=3,          # Max chunks per document (default: 3)

    # Optional features
    enable_reranking=False, # Use cross-encoder reranking (default: False)
    expand_query=True       # Expand abbreviations (default: True)
)

engine = RetrievalEngine(
    vector_store=vector_store,
    embedding_model=embedding_model,
    config=config
)
```

### Configuration Recommendations

**For Semantic-Heavy Queries** (concepts, meaning):
```python
config = RetrievalConfig(
    vector_weight=0.9,
    keyword_weight=0.1,
    recency_weight=0.7
)
```

**For Keyword-Heavy Queries** (exact terms, names):
```python
config = RetrievalConfig(
    vector_weight=0.3,
    keyword_weight=0.7,
    recency_weight=0.5
)
```

**For Balanced Retrieval** (default):
```python
config = RetrievalConfig(
    vector_weight=0.7,
    keyword_weight=0.3,
    recency_weight=0.7
)
```

**For Historical Research** (prioritize older docs):
```python
config = RetrievalConfig(
    vector_weight=0.7,
    keyword_weight=0.3,
    recency_weight=0.0  # Disable recency boost
)
```

---

## Query Examples

### Example 1: Organizational Capacity Section

**Scenario**: Writing organizational capacity for a federal DoED grant.

```python
query = """
We need content for the organizational capacity section covering
staff qualifications, governance structure, track record, and financial stability.
"""

filters = DocumentFilters(
    doc_types=["Grant Proposal", "Annual Report"],
    date_range=(2022, 2024),  # Recent documents
    outcomes=["Funded", "N/A"]  # Exclude unfunded proposals
)

results = await engine.retrieve(
    query=query,
    top_k=5,
    filters=filters,
    recency_weight=0.8  # Emphasize recent content
)
```

**Expected Results**:
- Organizational capacity sections from funded proposals
- Annual reports with staff and governance information
- Recent financial data and track record
- High relevance scores (> 0.7) for top results

### Example 2: Program Description

**Scenario**: Foundation grant program description for early childhood.

```python
query = "early childhood program activities evidence-based outcomes"

filters = DocumentFilters(
    programs=["Early Childhood"],
    doc_types=["Grant Proposal", "Program Description", "Annual Report"]
)

results = await engine.retrieve(
    query=query,
    top_k=5,
    filters=filters,
    recency_weight=0.6
)
```

**Expected Results**:
- Program descriptions with activities and timelines
- Evidence-based practices and outcomes
- Early childhood specific content
- Mix of proposals and reports

### Example 3: Budget Information

**Scenario**: Need budget narrative and cost justification.

```python
query = "budget costs personnel expenses sustainability funding"

filters = DocumentFilters(
    doc_types=["Grant Proposal"],
    outcomes=["Funded"]  # Only funded proposals
)

results = await engine.retrieve(
    query=query,
    top_k=3,
    filters=filters
)
```

**Expected Results**:
- Budget narratives from successful proposals
- Cost breakdowns and justifications
- Sustainability plans
- Personnel costs and FTE details

### Example 4: Simple Keyword Search

**Scenario**: Find mentions of specific partner organization.

```python
# Use higher keyword weight for exact matches
engine.config.keyword_weight = 0.7
engine.config.vector_weight = 0.3

query = "University of Nebraska partnership collaboration"

results = await engine.retrieve(query=query, top_k=5)
```

### Example 5: Broad Concept Search

**Scenario**: Find content about youth development approach.

```python
# Use higher vector weight for semantic matching
engine.config.vector_weight = 0.9
engine.config.keyword_weight = 0.1

query = "youth development leadership mentorship empowerment"

results = await engine.retrieve(query=query, top_k=5)
```

---

## Metadata Filtering

### Available Filters

```python
from app.models.document import DocumentFilters

filters = DocumentFilters(
    # Filter by document types (list)
    doc_types=["Grant Proposal", "Annual Report"],

    # Filter by specific years (list)
    years=[2023, 2024],

    # OR filter by year range (tuple)
    date_range=(2020, 2024),

    # Filter by program areas (list)
    programs=["Early Childhood", "Youth Development"],

    # Filter by outcome status (list)
    outcomes=["Funded", "Pending"],

    # Exclude specific documents (list of doc_ids)
    exclude_docs=["doc-id-1", "doc-id-2"]
)
```

### Filter Examples

**Recent Funded Proposals Only**:
```python
filters = DocumentFilters(
    doc_types=["Grant Proposal"],
    date_range=(2022, 2024),
    outcomes=["Funded"]
)
```

**Early Childhood Content (Any Type)**:
```python
filters = DocumentFilters(
    programs=["Early Childhood"]
)
```

**Annual Reports from Last 5 Years**:
```python
filters = DocumentFilters(
    doc_types=["Annual Report"],
    date_range=(2019, 2024)
)
```

**Exclude Failed Proposals**:
```python
filters = DocumentFilters(
    outcomes=["Funded", "Pending", "N/A"]  # Implicitly excludes "Not Funded"
)
```

---

## Best Practices

### Query Formulation

**✅ DO:**
- Use specific, descriptive queries (5-15 words)
- Include key concepts and terminology
- Combine broad concepts with specific terms
- Use natural language phrases
- Example: "organizational capacity board governance financial management"

**❌ DON'T:**
- Use single-word queries (too broad)
- Include filler words like "find me", "search for"
- Use overly long queries (>50 words)
- Mix unrelated concepts
- Example: "stuff about our organization" (too vague)

### Query Optimization Tips

1. **Start Broad, Then Filter**: Use a broad query with metadata filters rather than overly specific queries

   ```python
   # Good
   query = "program evaluation outcomes"
   filters = DocumentFilters(programs=["Early Childhood"])

   # Less effective
   query = "early childhood program evaluation outcomes assessment"
   ```

2. **Use Domain Terminology**: Include grant writing terms
   - Good: "organizational capacity", "logic model", "sustainability plan"
   - Avoid: "company info", "project plan", "future funding"

3. **Combine Semantic and Keyword**: Design queries that work for both
   - "staff qualifications expertise experience" (semantic + keywords)

### Filter Strategy

1. **Progressive Filtering**: Start without filters, add if needed

   ```python
   # Try 1: No filters
   results = await engine.retrieve(query, top_k=5)

   # Try 2: If results too old, add date filter
   if max(r.metadata['year'] for r in results) < 2020:
       filters = DocumentFilters(date_range=(2020, 2024))
       results = await engine.retrieve(query, top_k=5, filters=filters)
   ```

2. **Balance Specificity**: Too many filters = no results

   ```python
   # Too restrictive (may return nothing)
   filters = DocumentFilters(
       doc_types=["Grant Proposal"],
       years=[2024],
       programs=["Early Childhood"],
       outcomes=["Funded"]
   )

   # Better (more likely to return results)
   filters = DocumentFilters(
       doc_types=["Grant Proposal"],
       date_range=(2022, 2024),
       programs=["Early Childhood"]
   )
   ```

### Result Interpretation

**Understanding Scores**:
- **0.8 - 1.0**: Highly relevant, likely excellent match
- **0.6 - 0.8**: Good relevance, useful content
- **0.4 - 0.6**: Moderate relevance, may be tangentially related
- **< 0.4**: Low relevance, likely not useful

**Checking Result Quality**:
```python
results = await engine.retrieve(query, top_k=5)

# Check if results are good
if results[0].score > 0.7:
    print("✓ High confidence results")
elif results[0].score > 0.5:
    print("⚠ Moderate confidence, review carefully")
else:
    print("✗ Low confidence, try refining query")

# Check diversity (unique documents)
unique_docs = len(set(r.metadata['doc_id'] for r in results))
if unique_docs >= 3:
    print(f"✓ Good diversity: {unique_docs} different documents")
```

---

## Performance Tuning

### Latency Optimization

**Target**: < 1 second for most queries

1. **Enable Caching**:
   ```python
   cached_engine = CachedRetrievalEngine(engine)
   # Second+ calls: ~0ms (cache hit)
   ```

2. **Reduce top_k**: Fewer results = faster retrieval
   ```python
   # Fast (50-100ms typical)
   results = await engine.retrieve(query, top_k=3)

   # Slower (200-500ms typical)
   results = await engine.retrieve(query, top_k=20)
   ```

3. **Use Filters**: Filtered search is faster
   ```python
   # Searches smaller subset
   filters = DocumentFilters(doc_types=["Grant Proposal"])
   results = await engine.retrieve(query, top_k=5, filters=filters)
   ```

### Throughput Optimization

**Target**: > 10 queries per second

1. **Use Concurrent Requests**:
   ```python
   queries = ["query1", "query2", "query3"]

   # Run concurrently
   results = await asyncio.gather(*[
       engine.retrieve(q, top_k=5) for q in queries
   ])
   ```

2. **Batch Query Processing**:
   ```python
   async def batch_retrieve(queries: List[str], batch_size: int = 5):
       results = []
       for i in range(0, len(queries), batch_size):
           batch = queries[i:i+batch_size]
           batch_results = await asyncio.gather(*[
               engine.retrieve(q, top_k=5) for q in batch
           ])
           results.extend(batch_results)
       return results
   ```

### Memory Optimization

1. **Limit Cache Size**:
   ```python
   cache = QueryCache(
       max_size=500,  # Reduce if memory constrained
       ttl_seconds=1800  # 30 minutes
   )
   ```

2. **Periodic Cache Cleanup**:
   ```python
   # Clean expired entries periodically
   import schedule

   schedule.every(15).minutes.do(lambda: cache.cleanup_expired())
   ```

### Accuracy Tuning

**Improve Relevance**:

1. **Adjust Hybrid Weights**: Test different configurations
   ```python
   # If semantic matches are better
   config.vector_weight = 0.8
   config.keyword_weight = 0.2

   # If keyword matches are better
   config.vector_weight = 0.5
   config.keyword_weight = 0.5
   ```

2. **Enable Reranking** (slower but more accurate):
   ```python
   from app.services.reranker import Reranker

   reranker = Reranker(model="cross-encoder/ms-marco-MiniLM-L-2-v2")
   engine = RetrievalEngine(
       vector_store=vector_store,
       embedding_model=embedding_model,
       reranker=reranker,
       config=RetrievalConfig(enable_reranking=True)
   )
   ```

3. **Tune Recency Weight**: Adjust based on use case
   ```python
   # For current proposals (emphasize recent)
   results = await engine.retrieve(query, recency_weight=0.9)

   # For historical analysis (no recency bias)
   results = await engine.retrieve(query, recency_weight=0.0)
   ```

---

## Caching

### Cache Configuration

```python
from app.services.query_cache import QueryCache, CachedRetrievalEngine

# Create cache with custom settings
cache = QueryCache(
    max_size=1000,        # Maximum entries (LRU eviction)
    ttl_seconds=3600,     # 1 hour time-to-live
    enable_metrics=True   # Track hit/miss rates
)

# Wrap engine
cached_engine = CachedRetrievalEngine(
    retrieval_engine=engine,
    cache=cache,
    enable_cache=True
)
```

### Cache Management

**Check Cache Stats**:
```python
stats = cached_engine.get_cache_stats()
print(f"Cache size: {stats['cache_size']}/{stats['max_size']}")
print(f"Hit rate: {stats['hit_rate']}")
print(f"Hits: {stats['hits']}, Misses: {stats['misses']}")
```

**Invalidate Cache** (after adding/removing documents):
```python
# Invalidate entire cache
cached_engine.invalidate_cache()

# Or directly on cache
cache.invalidate_all()
```

**Manual Cache Cleanup**:
```python
# Remove expired entries
cache.cleanup_expired()

# Reset metrics
cache.reset_metrics()
```

### Cache Performance

**Expected Performance**:
- Cache hit: < 1ms
- Cache miss + retrieval: 100-500ms (depending on query)
- Typical hit rate after warmup: 40-60%

**Monitoring**:
```python
# Log cache stats periodically
import logging
logger = logging.getLogger(__name__)

async def log_cache_stats():
    stats = cache.get_stats()
    logger.info(
        f"Cache: {stats['cache_size']} entries, "
        f"hit_rate={stats['hit_rate']}, "
        f"queries={stats['total_queries']}"
    )
```

---

## Troubleshooting

### No Results Returned

**Symptoms**: `retrieve()` returns empty list

**Possible Causes**:

1. **Filters Too Restrictive**
   ```python
   # Check if filters exclude all documents
   results = await engine.retrieve(query, top_k=5, filters=None)
   if results:
       print("Filters were too restrictive")
   ```

2. **BM25 Index Not Built**
   ```python
   # Rebuild index
   await engine.build_bm25_index()
   ```

3. **No Documents in Vector Store**
   ```python
   # Check collection
   info = await vector_store.get_collection_info()
   print(f"Documents in store: {info['vectors_count']}")
   ```

### Low Relevance Scores

**Symptoms**: Top results have scores < 0.5

**Solutions**:

1. **Refine Query**: Make query more specific
   ```python
   # Vague
   query = "information about programs"

   # Specific
   query = "early childhood education program activities and outcomes"
   ```

2. **Adjust Weights**: Try different hybrid weights
   ```python
   # Increase keyword weight for exact matching
   engine.config.keyword_weight = 0.5
   engine.config.vector_weight = 0.5
   ```

3. **Check Document Quality**: Ensure documents are relevant
   ```python
   # Review what's in the collection
   for result in results:
       print(f"Doc: {result.metadata['filename']}")
       print(f"Type: {result.metadata['doc_type']}")
   ```

### Slow Retrieval

**Symptoms**: Queries take > 2 seconds

**Solutions**:

1. **Enable Caching**
   ```python
   cached_engine = CachedRetrievalEngine(engine)
   ```

2. **Reduce top_k**
   ```python
   # Try with fewer results
   results = await engine.retrieve(query, top_k=3)
   ```

3. **Add Filters** (searches smaller subset)
   ```python
   filters = DocumentFilters(doc_types=["Grant Proposal"])
   ```

4. **Disable Reranking** (if enabled)
   ```python
   engine.config.enable_reranking = False
   ```

### Cache Not Working

**Symptoms**: Cache hit rate always 0%

**Possible Causes**:

1. **Cache Disabled**
   ```python
   # Check if enabled
   print(f"Cache enabled: {cached_engine.enable_cache}")
   ```

2. **TTL Too Short**
   ```python
   # Increase TTL
   cache.ttl_seconds = 7200  # 2 hours
   ```

3. **Queries Always Different** (parameters vary)
   ```python
   # Ensure consistent parameters for cache hits
   # Different top_k = different cache key
   results1 = await engine.retrieve(query, top_k=5)
   results2 = await engine.retrieve(query, top_k=5)  # Cache hit
   results3 = await engine.retrieve(query, top_k=10)  # Cache miss
   ```

### Memory Issues

**Symptoms**: High memory usage, slow performance

**Solutions**:

1. **Reduce Cache Size**
   ```python
   cache = QueryCache(max_size=500)  # Down from 1000
   ```

2. **Cleanup Expired Entries**
   ```python
   cache.cleanup_expired()
   ```

3. **Rebuild BM25 Index** (frees memory from old entries)
   ```python
   await engine.build_bm25_index()
   ```

---

## API Reference

### RetrievalEngine

**Class**: `app.services.retrieval_engine.RetrievalEngine`

#### Constructor

```python
RetrievalEngine(
    vector_store: QdrantStore,
    embedding_model: BaseEmbedding,
    config: Optional[RetrievalConfig] = None,
    reranker: Optional[Reranker] = None
)
```

**Parameters**:
- `vector_store`: Qdrant vector store instance
- `embedding_model`: Embedding model for query encoding
- `config`: Optional retrieval configuration
- `reranker`: Optional reranker for improved results

#### Methods

##### `retrieve()`

Perform retrieval with all pipeline stages.

```python
async def retrieve(
    query: str,
    top_k: int = 5,
    filters: Optional[DocumentFilters] = None,
    recency_weight: Optional[float] = None
) -> List[RetrievalResult]
```

**Parameters**:
- `query`: Query string (5-50 words recommended)
- `top_k`: Number of results to return (1-20)
- `filters`: Optional metadata filters
- `recency_weight`: Override default recency weight (0-1)

**Returns**: List of `RetrievalResult` objects sorted by score

**Example**:
```python
results = await engine.retrieve(
    query="organizational capacity governance",
    top_k=5,
    filters=DocumentFilters(doc_types=["Grant Proposal"]),
    recency_weight=0.8
)
```

##### `build_bm25_index()`

Build or rebuild BM25 keyword search index.

```python
async def build_bm25_index() -> None
```

**When to Call**:
- After engine initialization (required)
- After adding/removing documents
- Periodically to refresh index

**Example**:
```python
await engine.build_bm25_index()
```

### RetrievalResult

**Class**: `app.services.retrieval_engine.RetrievalResult`

**Attributes**:
- `chunk_id` (str): Unique chunk identifier
- `text` (str): Retrieved text content
- `score` (float): Relevance score (0-1+)
- `metadata` (Dict): Document metadata
- `doc_id` (str): Document ID
- `chunk_index` (int): Chunk position in document

**Example**:
```python
result = results[0]
print(f"Score: {result.score:.4f}")
print(f"From: {result.metadata['filename']}")
print(f"Year: {result.metadata['year']}")
print(f"Text: {result.text[:200]}...")
```

### RetrievalConfig

**Class**: `app.services.retrieval_engine.RetrievalConfig`

**Attributes**:
- `vector_weight` (float): Weight for vector search (0-1)
- `keyword_weight` (float): Weight for keyword search (0-1)
- `recency_weight` (float): Recency boost strength (0-1)
- `max_per_doc` (int): Max chunks per document
- `enable_reranking` (bool): Enable cross-encoder reranking
- `expand_query` (bool): Expand abbreviations

### QueryCache

**Class**: `app.services.query_cache.QueryCache`

#### Methods

##### `get()`

Get cached results if available.

```python
def get(
    query: str,
    top_k: int,
    filters: Optional[DocumentFilters] = None,
    recency_weight: Optional[float] = None,
    **kwargs
) -> Optional[List[RetrievalResult]]
```

##### `put()`

Store results in cache.

```python
def put(
    query: str,
    results: List[RetrievalResult],
    top_k: int,
    filters: Optional[DocumentFilters] = None,
    recency_weight: Optional[float] = None,
    **kwargs
) -> None
```

##### `get_stats()`

Get cache statistics.

```python
def get_stats() -> Dict[str, Any]
```

**Returns**:
```python
{
    'cache_size': 150,
    'max_size': 1000,
    'hit_rate': '45.2%',
    'hits': 45,
    'misses': 55,
    'total_queries': 100
}
```

---

## Additional Resources

- **Architecture Documentation**: `context/architecture.md`
- **API Endpoints**: `backend/app/api/query.py`
- **Integration Tests**: `backend/tests/test_retrieval_engine.py`
- **Performance Benchmarks**: Run `python backend/benchmark_retrieval_engine.py`

---

## Support

For issues or questions:
1. Check this usage guide first
2. Review integration tests for examples
3. Check application logs for error details
4. File an issue on GitHub

---

**Last Updated**: 2025-10-19
**Version**: 1.0.0
