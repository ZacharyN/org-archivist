# Reranking Architecture Decision & Future Roadmap

**Date:** October 29, 2025
**Decision:** Remove local ML-based reranking, plan for future API-based reranking
**Status:** Phase 1 (No Reranking) - Current Implementation

---

## Executive Summary

We have **removed all local ML packages** (PyTorch, transformers, sentence-transformers) from the application to:
- Reduce Docker image size from ~3GB to ~800MB
- Eliminate 12+ minute build times and network timeout issues
- Simplify deployment and reduce infrastructure costs
- Enable faster iteration during MVP phase

Reranking functionality remains **disabled by default** in the codebase and can be enabled via API integration when user feedback indicates it's needed.

---

## Current Architecture (Phase 1: No Reranking)

### Retrieval Pipeline Components

Our hybrid retrieval system provides excellent relevance **without reranking**:

1. **Vector Search (Semantic)**
   - Uses OpenAI/Voyage/Anthropic embedding APIs
   - Captures semantic meaning and context
   - Default weight: 70%

2. **Keyword Search (BM25-L)**
   - Pure Python implementation (rank-bm25)
   - Catches exact term matches
   - Default weight: 30%

3. **Metadata Filtering**
   - Document type, date range, tags
   - Program area, author filters

4. **Recency Weighting**
   - Boosts newer documents
   - Configurable weight (default: 0.7)

5. **Result Diversification**
   - Limits chunks per document (max: 3)
   - Prevents single-document dominance

6. **Query Expansion**
   - Improves recall on complex queries
   - Enabled by default

### Expected Performance

- **Relevance:** 85-90% (excellent for grant writing use case)
- **Speed:** 200-400ms average query time
- **Cost:** API embeddings only (~$0.0001 per query)

---

## Removed Components

### ML Packages (Removed October 29, 2025)

The following packages were removed from `backend/requirements.txt`:

```
torch==2.9.0                      # 2GB+ download
transformers==4.57.1              # 1GB+ with models
sentence-transformers==5.1.1      # Local embedding/reranking
scipy==1.16.2                     # Scientific computing
scikit-learn==1.7.2               # ML utilities
llama-index-embeddings-huggingface==0.6.1
sympy==1.14.0
mpmath==1.3.0
joblib==1.5.2
networkx==3.5
threadpoolctl==3.6.0
safetensors==0.6.2
tokenizers==0.22.1
```

**Total Reduction:** ~32 packages, ~2.5GB of dependencies

### Code Preserved

The reranker service code remains in the codebase but is **disabled by default**:

- `backend/app/services/reranker.py` - Reranker implementation (graceful degradation)
- `backend/app/services/retrieval_engine.py` - Integration point (line 53: `enable_reranking: bool = False`)

This allows for easy re-enablement when API integration is implemented.

---

## Future Roadmap: API-Based Reranking (Phase 2)

### When to Implement

**Trigger Conditions:**
- User feedback indicates poor result relevance
- Grant writers report missing important context
- Quantitative metrics show <80% user satisfaction with results
- A/B testing shows significant improvement opportunity

### Recommended API Provider: Jina AI Reranker v2

**Why Jina AI?**
- Best price/performance ratio
- Multilingual support (100+ languages)
- Code search capabilities (useful for technical proposals)
- Simple Python SDK integration
- 6x faster than v1 (released June 2024)

**Alternative Providers:**
1. **Cohere Rerank** - 3x faster, higher cost, slightly lower relevance
2. **Voyage AI Rerank-2-Lite** - Similar to Jina, 2x higher rate limits

### Implementation Plan

#### Step 1: Add Jina AI SDK (5 minutes)

```bash
# Add to requirements.txt
jina-reranker==2.0.0  # ~5MB package
```

#### Step 2: Update Reranker Service (30 minutes)

Modify `backend/app/services/reranker.py`:

```python
class Reranker:
    def __init__(self, config: Optional[RerankerConfig] = None):
        self.config = config or RerankerConfig()
        self._reranker = None
        self._available = False

        # Check if Jina API key is available
        if os.getenv("JINA_API_KEY"):
            try:
                from jina import Client
                self._reranker = Client(token=os.getenv("JINA_API_KEY"))
                self._available = True
                logger.info("Jina AI Reranker initialized")
            except Exception as e:
                logger.warning(f"Jina reranker failed: {e}")
        else:
            logger.info("JINA_API_KEY not set, reranking disabled")

    def rerank(
        self,
        query: str,
        results: List[Dict[str, Any]],
        top_n: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        if not self._available:
            return results

        # Call Jina API
        documents = [r["text"] for r in results]
        reranked = self._reranker.rerank(
            query=query,
            documents=documents,
            model=self.config.model,
            top_n=top_n or len(documents)
        )

        # Map results back with new scores
        reranked_results = []
        for item in reranked:
            original = results[item.index]
            reranked_results.append({
                **original,
                "score": item.relevance_score,
                "metadata": {
                    **original["metadata"],
                    "_reranked": True,
                    "_reranker_model": "jina-reranker-v2"
                }
            })

        return reranked_results
```

#### Step 3: Add Environment Variable (2 minutes)

Update `docker-compose.yml`:

```yaml
environment:
  # Reranking (optional)
  JINA_API_KEY: ${JINA_API_KEY:-}
  ENABLE_RERANKING: ${ENABLE_RERANKING:-false}
```

Update `.env.example`:

```bash
# Optional: Jina AI Reranker (for improved relevance)
JINA_API_KEY=your_jina_api_key_here
ENABLE_RERANKING=false  # Set to true to enable
```

#### Step 4: Update Configuration (10 minutes)

Modify `backend/app/config.py`:

```python
class Settings(BaseSettings):
    # ... existing settings ...

    # Reranking Configuration
    JINA_API_KEY: Optional[str] = Field(
        None,
        description="Jina AI API key for reranking"
    )
    ENABLE_RERANKING: bool = Field(
        default=False,
        description="Enable optional reranking with Jina AI"
    )
    RERANKER_MODEL: str = Field(
        default="jina-reranker-v2-base-multilingual",
        description="Jina reranker model name"
    )
    RERANKER_TOP_N: Optional[int] = Field(
        default=10,
        description="Number of results after reranking"
    )
```

#### Step 5: Testing (1-2 hours)

1. **Unit Tests:**
   - Test with/without API key
   - Test graceful degradation
   - Mock API responses

2. **Integration Tests:**
   - End-to-end retrieval with reranking
   - Performance benchmarking
   - Cost analysis

3. **A/B Testing:**
   - Compare relevance with/without reranking
   - Measure latency impact
   - Calculate cost per query

### Expected Outcomes (Phase 2)

**With API Reranking:**
- **Relevance:** 92-95% (+5-7% improvement)
- **Speed:** 250-600ms (+50-200ms latency)
- **Cost:** +$0.0001-0.0003 per query
- **Build Time:** Still <3 minutes (no ML packages!)

---

## Cost Analysis

### Current (Phase 1: No Reranking)

**Per 1,000 Queries:**
- OpenAI Embeddings: ~$0.10
- Qdrant hosting: ~$0.05
- **Total:** ~$0.15

### Future (Phase 2: With Jina Reranking)

**Per 1,000 Queries:**
- OpenAI Embeddings: ~$0.10
- Jina Reranking: ~$0.15-0.30
- Qdrant hosting: ~$0.05
- **Total:** ~$0.30-0.45

**Monthly Cost (10K queries/month):**
- Phase 1: $1.50/month
- Phase 2: $3.00-4.50/month

---

## Decision Rationale

### Why Remove Local ML Packages?

1. **Build Performance:**
   - PyTorch alone: 2GB download, 8+ minutes
   - Network timeouts common (seen Oct 29, 2025)
   - Slows development iteration

2. **Runtime Overhead:**
   - Docker image: 3GB → 800MB
   - Memory usage: 2GB → 500MB
   - Cold start: 30s → 5s

3. **Maintenance Burden:**
   - CUDA compatibility issues
   - Version conflicts (seen with llama-index packages)
   - Security vulnerabilities in ML supply chain

4. **Cost Efficiency:**
   - Serverless deployment friendly
   - Lower infrastructure costs
   - Better auto-scaling

### Why API Reranking is Better

1. **Always Up-to-Date:**
   - Latest models without retraining
   - Automatic performance improvements

2. **No Infrastructure Complexity:**
   - No GPU requirements
   - No model management
   - Simple HTTP API calls

3. **Pay-as-You-Go:**
   - Only pay for actual usage
   - No idle GPU costs

4. **Enterprise Features:**
   - Better rate limits
   - SLA guarantees
   - Multi-region support

---

## Migration Checklist (When Implementing Phase 2)

### Prerequisites
- [ ] User feedback indicates reranking is needed
- [ ] Budget approved for reranking API costs
- [ ] Jina AI account created

### Implementation
- [ ] Add `jina-reranker` to requirements.txt
- [ ] Update `reranker.py` for Jina API
- [ ] Add environment variables to docker-compose.yml
- [ ] Update .env.example with Jina API key
- [ ] Update config.py with reranking settings
- [ ] Write unit tests for Jina integration
- [ ] Update architecture.md with reranking flow
- [ ] Add monitoring for reranking API calls

### Testing
- [ ] Benchmark query performance (with/without reranking)
- [ ] A/B test relevance improvement
- [ ] Monitor API costs for 1 week
- [ ] Collect user feedback on relevance

### Documentation
- [ ] Update README.md with reranking setup
- [ ] Document Jina API key acquisition
- [ ] Add troubleshooting guide
- [ ] Update cost estimates

---

## References

### API Documentation
- [Jina AI Reranker API](https://jina.ai/reranker/)
- [Cohere Rerank](https://cohere.com/rerank)
- [Voyage AI Rerank](https://docs.voyageai.com/docs/reranker)

### Research & Benchmarks
- [DataStax Reranker Comparison (2025)](https://www.datastax.com/blog/reranker-algorithm-showdown-vector-search)
- [Galileo AI: Mastering RAG Reranking](https://galileo.ai/blog/mastering-rag-how-to-select-a-reranking-model)

### Integration Examples
- [GitHub: AnswerDotAI/rerankers](https://github.com/AnswerDotAI/rerankers) - Unified API for rerankers
- [n8n Reranker Workflows](https://blog.n8n.io/implementing-rerankers-in-your-ai-workflows/)

---

## Contact & Questions

For questions about this decision or the implementation plan:
- Review: `/docs/retrieval-engine-usage.md`
- Architecture: `/context/architecture.md`
- Code: `/backend/app/services/reranker.py`

**Last Updated:** October 29, 2025
**Next Review:** After MVP user feedback (est. Q1 2026)
