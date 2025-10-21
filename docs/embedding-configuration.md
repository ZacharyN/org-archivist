# Embedding Model Configuration

## Overview

Org Archivist uses **API-based embedding models** (OpenAI or Voyage AI) to convert document text into vector representations for semantic search. This document explains the configuration, supported models, and best practices.

**Important:** Local embeddings are no longer supported as of this version. API-based embeddings provide better quality, simpler deployment, and negligible cost for typical nonprofit usage.

---

## Supported Providers

### OpenAI (Recommended)

**Recommended Model:** `text-embedding-3-small`

**Why OpenAI:**
- Excellent quality-to-cost ratio
- Widely tested and documented
- Simple API integration
- Most organizations already have OpenAI accounts

**Available Models:**

| Model | Dimensions | Cost per 1K tokens | Best For |
|-------|------------|-------------------|----------|
| `text-embedding-3-small` | 1536 | $0.00002 | Most use cases (recommended) |
| `text-embedding-3-large` | 3072 | $0.00013 | Higher quality requirements |
| `text-embedding-ada-002` | 1536 | $0.00010 | Legacy (use 3-small instead) |

### Voyage AI (Alternative)

**Recommended Model:** `voyage-large-2`

**Why Voyage:**
- Optimized specifically for retrieval/RAG use cases
- Same Anthropic ecosystem as Claude
- Excellent performance on retrieval benchmarks
- Supports longer context (16K tokens)

**Available Models:**

| Model | Dimensions | Cost per 1K tokens | Best For |
|-------|------------|-------------------|----------|
| `voyage-large-2` | 1536 | $0.00012 | General retrieval (recommended) |
| `voyage-code-2` | 1536 | $0.00012 | Code and technical docs |

---

## Cost Analysis

### Example: Typical Nonprofit Usage

**Initial Processing (500 documents, ~250K words):**
- Total tokens: ~330,000
- OpenAI 3-small: 330K × $0.00002 = **$0.0066** (less than 1 cent!)
- Voyage: 330K × $0.00012 = **$0.04**

**Ongoing Queries (1000 queries/month, ~50 tokens each):**
- Total tokens: ~50,000/month
- OpenAI 3-small: 50K × $0.00002 = **$0.001/month**
- Voyage: 50K × $0.00012 = **$0.006/month**

**Total First Year:**
- OpenAI: **~$0.02** (2 cents)
- Voyage: **~$0.11** (11 cents)

**For context:** A single $50K grant proposal justifies these costs thousands of times over. Embedding costs are negligible compared to staff time.

---

## Configuration

### Environment Variables

Edit your `.env` file:

```bash
# Choose provider (required)
EMBEDDING_PROVIDER=openai

# Specify model (required)
EMBEDDING_MODEL=text-embedding-3-small

# Dimensions must match model (required)
EMBEDDING_DIMENSIONS=1536

# API key for chosen provider (required)
OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxx
# or
VOYAGE_API_KEY=pa-xxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

### Configuration Examples

**Option 1: OpenAI (Recommended)**
```bash
EMBEDDING_PROVIDER=openai
EMBEDDING_MODEL=text-embedding-3-small
EMBEDDING_DIMENSIONS=1536
OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

**Option 2: OpenAI (Higher Quality)**
```bash
EMBEDDING_PROVIDER=openai
EMBEDDING_MODEL=text-embedding-3-large
EMBEDDING_DIMENSIONS=3072
OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

**Option 3: Voyage AI**
```bash
EMBEDDING_PROVIDER=voyage
EMBEDDING_MODEL=voyage-large-2
EMBEDDING_DIMENSIONS=1536
VOYAGE_API_KEY=pa-xxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

---

## Getting API Keys

### OpenAI

1. Go to https://platform.openai.com/api-keys
2. Sign up or log in
3. Click "Create new secret key"
4. Copy the key (starts with `sk-`)
5. Add to `.env` as `OPENAI_API_KEY=sk-...`

**Note:** Requires credit card on file, but costs are pay-as-you-go (see cost analysis above).

### Voyage AI

1. Go to https://www.voyageai.com/
2. Sign up for an account
3. Navigate to API Keys section
4. Generate a new API key (starts with `pa-`)
5. Add to `.env` as `VOYAGE_API_KEY=pa-...`

**Note:** May require approval for API access.

---

## Why No Local Embeddings?

Previous versions supported local embedding models (e.g., BAAI/bge-large-en-v1.5). We removed this for several reasons:

### 1. **Operational Complexity**
- Local models require downloading 1-2GB of model weights
- Need to manage PyTorch/TensorFlow dependencies
- Require GPU for decent performance (CPU is very slow)
- Deployment becomes significantly more complex

### 2. **Quality Gap**
- API models (OpenAI, Voyage) are state-of-the-art
- Continuously improved by providers
- Local models lag 6-12 months behind in quality
- For critical grant applications, quality matters

### 3. **Cost is Negligible**
- As shown above: <$1 per year for typical usage
- Staff time saved far exceeds API costs
- Simplifies budgeting and procurement

### 4. **Performance**
- API embeddings: ~50ms per request
- Local embeddings (CPU): ~500-1000ms per request
- Local embeddings (GPU): Need dedicated GPU hardware

### 5. **Simplicity for Nonprofits**
- Most nonprofits don't have ML engineers on staff
- Single API key is much simpler than model deployment
- Less training required for IT staff

---

## Switching Providers

If you need to switch providers (e.g., OpenAI → Voyage), follow these steps:

### 1. Update Configuration

Edit `.env`:
```bash
# Change from OpenAI
EMBEDDING_PROVIDER=openai
EMBEDDING_MODEL=text-embedding-3-small
EMBEDDING_DIMENSIONS=1536

# To Voyage
EMBEDDING_PROVIDER=voyage
EMBEDDING_MODEL=voyage-large-2
EMBEDDING_DIMENSIONS=1536
```

### 2. Re-Process Documents

**Important:** You must re-process all documents because embeddings are not compatible between providers.

```bash
# Option 1: Delete and re-upload documents via UI
# - This is the simplest approach for small libraries (<100 docs)

# Option 2: Script to re-process existing documents
# - Coming soon: migration script for large libraries
```

### 3. Restart Services

```bash
docker-compose restart backend
```

---

## Performance Optimization

### Batch Processing

When uploading multiple documents, embeddings are generated in batches:

```python
# Current implementation (efficient)
chunks = [chunk1, chunk2, ..., chunk100]
embeddings = embedding_model.get_embeddings(chunks)  # Single API call
```

### Caching

Embeddings are cached to avoid re-computing:

- **Query embeddings**: 1 hour TTL
- **Document embeddings**: Permanent (stored in Qdrant)

### Rate Limits

**OpenAI:**
- Free tier: 3,000 requests/minute
- Paid tier: 10,000+ requests/minute

**Voyage:**
- Varies by plan (check Voyage AI dashboard)

For typical usage, rate limits are not a concern.

---

## Troubleshooting

### Error: "OPENAI_API_KEY is required"

**Solution:** Add your OpenAI API key to `.env`:
```bash
OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

### Error: "Invalid API key"

**Solutions:**
1. Check that key is correct (copy-paste from provider)
2. Ensure key starts with correct prefix (`sk-` for OpenAI, `pa-` for Voyage)
3. Verify key has not expired or been revoked
4. Check account has credits/billing set up

### Error: "embedding_provider must be one of: openai, voyage"

**Solution:** Local embeddings are no longer supported. Update `.env`:
```bash
# Change from
EMBEDDING_PROVIDER=local

# To
EMBEDDING_PROVIDER=openai
```

### Error: "Dimension mismatch"

**Solution:** Ensure `EMBEDDING_DIMENSIONS` matches your model:
```bash
# text-embedding-3-small
EMBEDDING_DIMENSIONS=1536

# text-embedding-3-large
EMBEDDING_DIMENSIONS=3072

# voyage-large-2 or voyage-code-2
EMBEDDING_DIMENSIONS=1536
```

### Slow Embedding Generation

**Symptoms:** Document uploads taking >30 seconds

**Solutions:**
1. Check internet connection (API calls require network)
2. Verify API provider status (https://status.openai.com)
3. Consider upgrading to `text-embedding-3-large` if quality is paramount
4. Check rate limits if processing many documents

---

## Advanced Configuration

### Model Selection Criteria

**Choose `text-embedding-3-small` if:**
- You want the best cost-to-quality ratio (recommended)
- You're processing large document libraries (>1000 docs)
- Budget is a concern (though costs are already minimal)

**Choose `text-embedding-3-large` if:**
- You need highest possible retrieval quality
- Working with highly technical or nuanced content
- Budget is not a constraint

**Choose `voyage-large-2` if:**
- You prefer the Anthropic ecosystem (same as Claude)
- You want models specifically optimized for RAG
- You're comparing providers and want to test alternatives

### Qdrant Collection Configuration

Qdrant collections are automatically configured based on your embedding model:

```python
# Automatically set based on EMBEDDING_MODEL
{
    "vectors": {
        "size": 1536,  # or 3072 for 3-large
        "distance": "Cosine"
    },
    "hnsw_config": {
        "m": 16,
        "ef_construct": 100
    }
}
```

If you change models, delete the existing Qdrant collection and let it rebuild:

```bash
# Access Qdrant UI
open http://localhost:6333/dashboard

# Delete collection via UI or API
curl -X DELETE http://localhost:6333/collections/foundation_docs
```

---

## Migration from Local Embeddings

If you're upgrading from a version that used local embeddings:

### 1. Update Configuration

```bash
# In .env, change from:
EMBEDDING_PROVIDER=local
EMBEDDING_MODEL=bge-large-en-v1.5
EMBEDDING_DIMENSIONS=1024

# To:
EMBEDDING_PROVIDER=openai
EMBEDDING_MODEL=text-embedding-3-small
EMBEDDING_DIMENSIONS=1536
```

### 2. Add API Key

```bash
# Add to .env
OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

### 3. Clear Vector Database

```bash
# Delete Qdrant collection
curl -X DELETE http://localhost:6333/collections/foundation_docs

# Or restart Qdrant to clear all data
docker-compose restart qdrant
```

### 4. Re-upload Documents

Upload documents again through the UI. They will be processed with the new embedding model.

---

## Best Practices

1. **Use OpenAI by default** - It's the best tested and most cost-effective option
2. **Keep dimensions consistent** - Don't change models mid-project
3. **Monitor usage** - Check your OpenAI dashboard monthly
4. **Use 3-small for most cases** - Quality is excellent for grant writing
5. **Consider 3-large for technical content** - If working with highly specialized domains
6. **Back up your API keys** - Store securely (password manager)
7. **Set billing alerts** - OpenAI allows setting budget limits

---

## References

- [OpenAI Embeddings Documentation](https://platform.openai.com/docs/guides/embeddings)
- [Voyage AI Documentation](https://docs.voyageai.com/docs/embeddings)
- [Qdrant Vector Database](https://qdrant.tech/documentation/)
- [LlamaIndex Embeddings Guide](https://docs.llamaindex.ai/en/stable/module_guides/models/embeddings.html)

---

## Support

For issues related to embedding configuration:

1. Check this documentation first
2. Review logs: `docker-compose logs backend`
3. Verify API keys in OpenAI/Voyage dashboards
4. Check GitHub issues: https://github.com/yourusername/org-archivist/issues
5. Contact support (for enterprise deployments)
