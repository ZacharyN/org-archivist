# Testing Plan: ML Dependencies Removal

**Branch**: `chore/remove-ml-dependencies`
**Date**: 2025-10-30
**Changes**: Removed PyTorch/sentence-transformers, migrated to modular LlamaIndex

---

## Objective

Validate that removing ML dependencies and migrating to modular LlamaIndex packages maintains all functionality while eliminating unnecessary dependencies.

## Pre-Testing Setup

### 1. Clean Environment Setup

```bash
# Stop and remove all containers
docker-compose down -v

# Remove old images to force rebuild
docker rmi org-archivist-backend:latest
docker rmi org-archivist-qdrant:latest

# Rebuild with new dependencies
docker-compose build --no-cache

# Start services
docker-compose up -d

# Check all services are running
docker-compose ps
```

### 2. Verify Environment Variables

Check `.env` file has correct settings:
```bash
# Embedding configuration (no local models)
EMBEDDING_PROVIDER=openai  # or voyage
OPENAI_API_KEY=sk-...
# VOYAGE_API_KEY=pa-...  # if using Voyage

# Reranking DISABLED
ENABLE_RERANKING=false
```

---

## Test Suite

### Phase 1: Dependency Verification ✅

**Purpose**: Confirm no ML packages are installed

```bash
# Test 1.1: Check installed packages in Docker
docker exec -it org-archivist-backend pip list | grep -E "(torch|transformers|sentence)"

# Expected: NO results (no torch, transformers, sentence-transformers)

# Test 1.2: Verify LlamaIndex modules
docker exec -it org-archivist-backend pip list | grep llama-index

# Expected output:
# llama-index-core                0.12.x or higher
# llama-index-embeddings-openai   0.3.x or higher
# llama-index-embeddings-voyageai 0.2.x or higher

# Test 1.3: Check image size (should be smaller)
docker images | grep org-archivist-backend
```

**Success Criteria**:
- ✅ No torch, transformers, or sentence-transformers packages
- ✅ Modular LlamaIndex packages present
- ✅ Image size reduced by ~400-500MB

---

### Phase 2: Import Validation ✅

**Purpose**: Verify all Python imports work correctly

```bash
# Test 2.1: Test all imports in dependencies.py
docker exec -it org-archivist-backend python3 -c "
from app.dependencies import (
    get_retrieval_engine,
    get_vector_store,
    get_embedding_model,
    get_chunking_service
)
print('✓ All dependency imports successful')
"

# Test 2.2: Test chunking service imports
docker exec -it org-archivist-backend python3 -c "
from app.services.chunking_service import (
    ChunkingService,
    ChunkingConfig,
    ChunkingStrategy
)
from llama_index.core.schema import Document, TextNode
from llama_index.core.node_parser import SentenceSplitter, SemanticSplitterNodeParser
print('✓ Chunking service imports successful')
"

# Test 2.3: Test embedding imports
docker exec -it org-archivist-backend python3 -c "
from llama_index.embeddings.openai import OpenAIEmbedding
from llama_index.embeddings.voyageai import VoyageEmbedding
from llama_index.core.embeddings import BaseEmbedding
print('✓ Embedding imports successful')
"

# Test 2.4: Test retrieval engine imports
docker exec -it org-archivist-backend python3 -c "
from app.services.retrieval_engine import RetrievalEngine, RetrievalConfig
print('✓ Retrieval engine imports successful')
"
```

**Success Criteria**:
- ✅ All import statements succeed
- ✅ No ImportError or ModuleNotFoundError
- ✅ Core functionality classes load correctly

---

### Phase 3: Chunking Functionality Tests

**Purpose**: Validate text chunking with all strategies

```bash
# Test 3.1: Sentence Chunking
docker exec -it org-archivist-backend python3 <<'EOF'
from app.services.chunking_service import ChunkingService, ChunkingConfig, ChunkingStrategy

config = ChunkingConfig(
    strategy=ChunkingStrategy.SENTENCE,
    chunk_size=200,
    chunk_overlap=20
)
service = ChunkingService(config)

text = """This is a test document for sentence chunking.
It has multiple sentences. Each sentence should be respected.
The chunking should maintain sentence boundaries."""

chunks = service.chunk_text(text)
print(f"✓ Sentence chunking: {len(chunks)} chunks created")
for i, chunk in enumerate(chunks):
    print(f"  Chunk {i+1}: {len(chunk['text'])} chars")
EOF

# Test 3.2: Semantic Chunking
docker exec -it org-archivist-backend python3 <<'EOF'
from app.services.chunking_service import ChunkingService, ChunkingConfig, ChunkingStrategy

config = ChunkingConfig(
    strategy=ChunkingStrategy.SEMANTIC,
    chunk_size=300
)
service = ChunkingService(config)

text = """Grant writing requires careful planning. First, identify your target audience.
Second, articulate clear objectives. Third, develop a realistic budget.

Financial sustainability is crucial for nonprofits. Revenue diversification reduces risk.
Multiple funding sources provide stability. Strategic planning guides growth."""

chunks = service.chunk_text(text)
print(f"✓ Semantic chunking: {len(chunks)} chunks created")
for i, chunk in enumerate(chunks):
    print(f"  Chunk {i+1}: {len(chunk['text'])} chars")
EOF

# Test 3.3: Token Chunking
docker exec -it org-archivist-backend python3 <<'EOF'
from app.services.chunking_service import ChunkingService, ChunkingConfig, ChunkingStrategy

config = ChunkingConfig(
    strategy=ChunkingStrategy.TOKEN,
    chunk_size=100,
    chunk_overlap=10
)
service = ChunkingService(config)

text = "Lorem ipsum " * 100  # Generate long text

chunks = service.chunk_text(text)
print(f"✓ Token chunking: {len(chunks)} chunks created")
EOF
```

**Success Criteria**:
- ✅ All three chunking strategies work
- ✅ Chunks are created with appropriate sizes
- ✅ No errors or exceptions

---

### Phase 4: Embedding Generation Tests

**Purpose**: Verify embeddings are generated correctly via APIs

**Prerequisites**: Valid API keys in `.env`

```bash
# Test 4.1: OpenAI Embeddings
docker exec -it org-archivist-backend python3 <<'EOF'
import os
from llama_index.embeddings.openai import OpenAIEmbedding

# Check API key is set
if not os.getenv("OPENAI_API_KEY"):
    print("⚠ OPENAI_API_KEY not set, skipping test")
    exit(0)

embed_model = OpenAIEmbedding(
    model="text-embedding-3-small",
    api_key=os.getenv("OPENAI_API_KEY")
)

text = "This is a test document about grant writing for nonprofits."
embedding = embed_model.get_text_embedding(text)

print(f"✓ OpenAI embedding generated: {len(embedding)} dimensions")
print(f"  Model: text-embedding-3-small")
print(f"  Sample values: {embedding[:5]}")
EOF

# Test 4.2: Voyage Embeddings (if configured)
docker exec -it org-archivist-backend python3 <<'EOF'
import os
from llama_index.embeddings.voyageai import VoyageEmbedding

# Check API key is set
if not os.getenv("VOYAGE_API_KEY"):
    print("⚠ VOYAGE_API_KEY not set, skipping test")
    exit(0)

embed_model = VoyageEmbedding(
    model_name="voyage-large-2",
    voyage_api_key=os.getenv("VOYAGE_API_KEY")
)

text = "This is a test document about grant writing for nonprofits."
embedding = embed_model.get_text_embedding(text)

print(f"✓ Voyage embedding generated: {len(embedding)} dimensions")
print(f"  Model: voyage-large-2")
EOF

# Test 4.3: Batch Embedding Generation
docker exec -it org-archivist-backend python3 <<'EOF'
import os
from llama_index.embeddings.openai import OpenAIEmbedding

if not os.getenv("OPENAI_API_KEY"):
    print("⚠ OPENAI_API_KEY not set, skipping test")
    exit(0)

embed_model = OpenAIEmbedding(model="text-embedding-3-small")

texts = [
    "Grant proposal guidelines",
    "Nonprofit financial planning",
    "Community impact assessment",
    "Budget development strategies"
]

embeddings = embed_model.get_text_embedding_batch(texts)
print(f"✓ Batch embeddings generated: {len(embeddings)} embeddings")
print(f"  Each embedding: {len(embeddings[0])} dimensions")
EOF
```

**Success Criteria**:
- ✅ Single embeddings generated successfully
- ✅ Batch embeddings work correctly
- ✅ Correct embedding dimensions (1536 for OpenAI)
- ✅ No API errors or timeouts

---

### Phase 5: Document Processing Pipeline

**Purpose**: Test end-to-end document ingestion with new dependencies

```bash
# Test 5.1: Upload and process a PDF document via API
curl -X POST http://localhost:8000/api/v1/documents/upload \
  -F "file=@backend/tests/fixtures/sample.pdf" \
  -F "title=Test Document" \
  -F "document_type=grant_proposal" \
  -H "Authorization: Bearer YOUR_TOKEN_HERE"

# Expected: 200 OK with document_id

# Test 5.2: Verify document was chunked and embedded
docker exec -it org-archivist-backend python3 <<'EOF'
import asyncio
from app.services.vector_store import QdrantStore, VectorStoreConfig
from app.config import get_settings

async def check_vectors():
    settings = get_settings()
    config = VectorStoreConfig(
        host=settings.qdrant_host,
        port=settings.qdrant_port,
        collection_name=settings.qdrant_collection_name
    )
    store = QdrantStore(config)
    await store.connect()

    count = await store.count()
    print(f"✓ Vector store contains {count} chunks")

    await store.close()

asyncio.run(check_vectors())
EOF

# Test 5.3: Test document processing service directly
docker exec -it org-archivist-backend python3 <<'EOF'
import asyncio
from app.services.document_processor import DocumentProcessor
from app.services.extractors.txt_extractor import TXTExtractor

async def test_processing():
    extractor = TXTExtractor()
    processor = DocumentProcessor(extractor=extractor)

    # Create test file
    test_content = """
    Grant Proposal: Education Initiative

    We seek funding for an education program serving 500 students.
    The program will provide tutoring, mentorship, and career guidance.
    Expected outcomes include improved graduation rates and college readiness.

    Budget: $50,000 over 12 months
    Timeline: September 2025 - August 2026
    """

    with open("/tmp/test.txt", "w") as f:
        f.write(test_content)

    # Process document
    result = await processor.process_file(
        file_path="/tmp/test.txt",
        metadata={"title": "Test Grant", "type": "proposal"}
    )

    print(f"✓ Document processed successfully")
    print(f"  Chunks created: {len(result.chunks)}")
    print(f"  Has embeddings: {result.chunks[0].embedding is not None}")
    print(f"  Chunk 1 length: {len(result.chunks[0].text)} chars")

asyncio.run(test_processing())
EOF
```

**Success Criteria**:
- ✅ Documents upload successfully
- ✅ Text is chunked correctly
- ✅ Embeddings are generated and stored
- ✅ Metadata is preserved

---

### Phase 6: Retrieval Engine Tests

**Purpose**: Validate search functionality with new dependencies

```bash
# Test 6.1: Vector search
docker exec -it org-archivist-backend python3 <<'EOF'
import asyncio
from app.dependencies import get_retrieval_engine

async def test_search():
    engine = await get_retrieval_engine()

    query = "grant writing best practices"
    results = await engine.retrieve(query, top_k=5)

    print(f"✓ Vector search successful")
    print(f"  Query: {query}")
    print(f"  Results: {len(results)}")

    if results:
        print(f"  Top result score: {results[0].score:.4f}")
        print(f"  Top result preview: {results[0].text[:100]}...")

asyncio.run(test_search())
EOF

# Test 6.2: Hybrid search (vector + keyword)
docker exec -it org-archivist-backend python3 <<'EOF'
import asyncio
from app.dependencies import get_retrieval_engine

async def test_hybrid():
    engine = await get_retrieval_engine()

    query = "education funding"
    results = await engine.retrieve(query, top_k=5)

    print(f"✓ Hybrid search successful")
    print(f"  Results: {len(results)}")

    # Verify results have both vector and keyword scores
    if results:
        result = results[0]
        has_metadata = 'vector_score' in str(result.metadata) or 'keyword_score' in str(result.metadata)
        print(f"  Has scoring metadata: {has_metadata}")

asyncio.run(test_hybrid())
EOF

# Test 6.3: Metadata filtering
docker exec -it org-archivist-backend python3 <<'EOF'
import asyncio
from app.dependencies import get_retrieval_engine
from app.models.document import DocumentFilters

async def test_filtering():
    engine = await get_retrieval_engine()

    filters = DocumentFilters(document_type="grant_proposal")
    results = await engine.retrieve(
        query="community impact",
        top_k=5,
        filters=filters
    )

    print(f"✓ Filtered search successful")
    print(f"  Results: {len(results)}")
    if results:
        print(f"  Result types match filter: {all('grant' in str(r.metadata) for r in results)}")

asyncio.run(test_filtering())
EOF
```

**Success Criteria**:
- ✅ Vector search returns relevant results
- ✅ Hybrid search combines vector + keyword
- ✅ Filtering works correctly
- ✅ Scores are calculated properly

---

### Phase 7: Integration Tests

**Purpose**: Run existing test suite to catch regressions

```bash
# Test 7.1: Run unit tests
docker exec -it org-archivist-backend pytest backend/tests/ -v --tb=short

# Test 7.2: Run E2E document processing tests
docker exec -it org-archivist-backend pytest backend/tests/test_e2e_document_processing.py -v

# Test 7.3: Run retrieval engine tests
docker exec -it org-archivist-backend pytest backend/tests/test_retrieval_engine.py -v

# Test 7.4: Run chunking service tests
docker exec -it org-archivist-backend pytest backend/tests/test_chunking_service.py -v -k "not semantic"
# Note: Semantic chunking tests may need OpenAI API
```

**Success Criteria**:
- ✅ All unit tests pass
- ✅ No new test failures introduced
- ✅ E2E tests complete successfully

---

### Phase 8: API Endpoint Tests

**Purpose**: Verify all API endpoints work correctly

```bash
# Test 8.1: Health check
curl http://localhost:8000/health
# Expected: {"status": "healthy"}

# Test 8.2: Search endpoint
curl -X POST http://localhost:8000/api/v1/search \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{
    "query": "grant proposal guidelines",
    "top_k": 5
  }'
# Expected: 200 OK with results

# Test 8.3: Document upload endpoint
curl -X POST http://localhost:8000/api/v1/documents/upload \
  -F "file=@backend/tests/fixtures/sample.txt" \
  -F "title=API Test Document" \
  -H "Authorization: Bearer YOUR_TOKEN"
# Expected: 200 OK with document_id

# Test 8.4: Document list endpoint
curl http://localhost:8000/api/v1/documents \
  -H "Authorization: Bearer YOUR_TOKEN"
# Expected: 200 OK with document list
```

**Success Criteria**:
- ✅ All endpoints return expected status codes
- ✅ Search returns relevant results
- ✅ Upload and retrieval work correctly

---

### Phase 9: Performance Validation

**Purpose**: Confirm no performance degradation

```bash
# Test 9.1: Embedding generation latency
docker exec -it org-archivist-backend python3 <<'EOF'
import asyncio
import time
from app.dependencies import get_embedding_model

async def benchmark():
    model = await get_embedding_model()

    text = "Grant writing requires careful attention to detail and clear communication of organizational goals."

    # Warmup
    await model.aget_text_embedding(text)

    # Benchmark
    start = time.time()
    for _ in range(10):
        embedding = await model.aget_text_embedding(text)
    elapsed = (time.time() - start) / 10

    print(f"✓ Average embedding time: {elapsed*1000:.1f}ms")
    print(f"  Expected: <500ms (API call latency)")

asyncio.run(benchmark())
EOF

# Test 9.2: Search query latency
docker exec -it org-archivist-backend python3 <<'EOF'
import asyncio
import time
from app.dependencies import get_retrieval_engine

async def benchmark():
    engine = await get_retrieval_engine()

    # Warmup
    await engine.retrieve("test query", top_k=5)

    # Benchmark
    queries = [
        "grant writing",
        "budget planning",
        "community impact",
        "nonprofit governance",
        "fundraising strategies"
    ]

    start = time.time()
    for query in queries:
        results = await engine.retrieve(query, top_k=5)
    elapsed = (time.time() - start) / len(queries)

    print(f"✓ Average search time: {elapsed*1000:.1f}ms")
    print(f"  Expected: <400ms per query")

asyncio.run(benchmark())
EOF
```

**Success Criteria**:
- ✅ Embedding generation: <500ms
- ✅ Search queries: <400ms average
- ✅ No significant degradation from baseline

---

### Phase 10: Docker Build Performance

**Purpose**: Verify build improvements

```bash
# Test 10.1: Measure build time
time docker-compose build --no-cache backend

# Test 10.2: Check image size
docker images org-archivist-backend --format "table {{.Repository}}\t{{.Tag}}\t{{.Size}}"

# Test 10.3: Check startup time
docker-compose down && time docker-compose up -d
docker-compose logs backend | grep "Application startup complete"
```

**Success Criteria**:
- ✅ Build time reduced by ~2-3 minutes
- ✅ Image size reduced by ~400-500MB
- ✅ Startup time: <10 seconds

---

## Regression Testing Checklist

Test the following scenarios that might be affected:

- [ ] Document upload (PDF)
- [ ] Document upload (DOCX)
- [ ] Document upload (TXT)
- [ ] Search with filters
- [ ] Search with date range
- [ ] Recency-weighted search
- [ ] Multi-document search
- [ ] Query caching
- [ ] Metadata extraction
- [ ] Chunk boundary handling
- [ ] Large document processing (>100 pages)
- [ ] Batch operations
- [ ] Error handling (invalid files)
- [ ] Error handling (API failures)
- [ ] Concurrent requests

---

## Rollback Plan

If critical issues are found:

```bash
# 1. Switch back to main branch
git checkout main

# 2. Rebuild containers
docker-compose down -v
docker-compose build --no-cache
docker-compose up -d

# 3. Verify old dependencies
docker exec -it org-archivist-backend pip list | grep "llama-index\|sentence"
```

---

## Success Criteria Summary

✅ **Dependencies**: No PyTorch/ML packages, only modular LlamaIndex
✅ **Imports**: All Python imports successful
✅ **Chunking**: All strategies work correctly
✅ **Embeddings**: API-based embeddings generate correctly
✅ **Processing**: Document pipeline functions end-to-end
✅ **Search**: Retrieval engine returns relevant results
✅ **Tests**: All unit/integration tests pass
✅ **APIs**: All endpoints respond correctly
✅ **Performance**: No degradation in user-facing latency
✅ **Build**: Faster builds, smaller images

---

## Sign-off

- [ ] All Phase 1-10 tests completed
- [ ] Regression checklist verified
- [ ] Performance within acceptable range
- [ ] No critical bugs identified
- [ ] Documentation updated
- [ ] Ready to merge to main

**Tested by**: _______________
**Date**: _______________
**Notes**: _______________
