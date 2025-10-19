# Qdrant Vector Database Configuration

This directory contains configuration files and initialization scripts for the Qdrant vector database.

## Directory Structure

```
docker/qdrant/
├── config/
│   └── config.yaml          # Qdrant server configuration
├── scripts/
│   └── init_collection.py   # Collection initialization script
└── README.md                # This file
```

## Configuration Files

### `config/config.yaml`

Main Qdrant server configuration file that sets:
- HTTP API port (6333) and gRPC port (6334)
- Storage paths and performance settings
- HNSW index parameters for optimal vector search
- Logging and telemetry settings

This file is mounted as read-only into the Qdrant container.

### `scripts/init_collection.py`

Python script to initialize the vector database collection for storing document embeddings.

**Features:**
- Automatically detects vector dimensions based on embedding model
- Supports multiple embedding providers (OpenAI, Voyage, Local)
- Checks for existing collections before creating
- Provides option to recreate collection if needed
- Displays collection information and statistics

## Usage

### 1. Start Qdrant Container

```bash
# Start just Qdrant
docker-compose up -d qdrant

# Or start all services
docker-compose up -d
```

### 2. Initialize Collection

**Option A: Run from host (requires qdrant-client)**

```bash
# Install dependencies
pip install qdrant-client

# Set environment variables
export QDRANT_HOST=localhost
export QDRANT_PORT=6333
export QDRANT_COLLECTION_NAME=foundation_docs
export EMBEDDING_MODEL=bge-large-en-v1.5

# Run initialization script
python docker/qdrant/scripts/init_collection.py
```

**Option B: Run from backend container (preferred)**

```bash
# Once backend container is running
docker exec -it org-archivist-backend python /app/scripts/init_collection.py
```

**Option C: Initialize automatically on backend startup**

The backend application should automatically initialize the collection on first run.

## Embedding Model Support

The initialization script supports various embedding models with different dimensions:

| Provider | Model | Dimensions | Notes |
|----------|-------|------------|-------|
| OpenAI | text-embedding-3-small | 1536 | Good balance of quality and cost |
| OpenAI | text-embedding-3-large | 3072 | Highest quality |
| OpenAI | text-embedding-ada-002 | 1536 | Legacy model |
| Voyage AI | voyage-large-2 | 1536 | Optimized for retrieval |
| Voyage AI | voyage-code-2 | 1536 | Optimized for code |
| Local | bge-large-en-v1.5 | 1024 | Free, runs locally |
| Local | bge-small-en-v1.5 | 384 | Faster, smaller |
| Local | bge-base-en-v1.5 | 768 | Middle ground |

## HNSW Index Parameters

The configuration uses HNSW (Hierarchical Navigable Small World) indexing for fast vector search:

- **m = 16**: Number of edges per node (higher = better accuracy, more memory)
- **ef_construct = 100**: Construction time/quality trade-off
- **full_scan_threshold = 10000**: Use full scan for small datasets

These can be tuned in `config/config.yaml` based on your performance requirements.

## Accessing Qdrant

### Web UI (Dashboard)

Visit: http://localhost:6333/dashboard

The Qdrant dashboard provides:
- Collection browsing
- Point inspection
- Search testing
- Performance metrics

### API Endpoints

- **HTTP API**: http://localhost:6333
- **gRPC API**: localhost:6334
- **Health Check**: http://localhost:6333/health
- **Metrics**: http://localhost:6333/metrics

### Example API Calls

```bash
# Health check
curl http://localhost:6333/health

# List collections
curl http://localhost:6333/collections

# Get collection info
curl http://localhost:6333/collections/foundation_docs
```

## Troubleshooting

### Collection creation fails

**Symptoms**: Error when running init script

**Solutions**:
1. Check Qdrant is running: `docker ps | grep qdrant`
2. Check Qdrant health: `curl http://localhost:6333/health`
3. Check logs: `docker logs org-archivist-qdrant`

### Wrong vector dimensions

**Symptoms**: "Vector dimension mismatch" error

**Solutions**:
1. Verify `EMBEDDING_MODEL` matches your actual model
2. Set `EMBEDDING_DIMENSIONS` explicitly in `.env`
3. Recreate collection with correct dimensions

### Performance issues

**Symptoms**: Slow search queries

**Solutions**:
1. Increase `m` parameter in `config.yaml` (try 32 or 64)
2. Increase `ef_construct` (try 200)
3. Enable quantization (see config comments)
4. Consider adding more RAM to Docker

## Data Persistence

Vector data is stored in a Docker named volume: `org-archivist-qdrant-storage`

### Backup

```bash
# Backup Qdrant data
docker run --rm -v org-archivist-qdrant-storage:/data -v $(pwd):/backup alpine tar czf /backup/qdrant-backup.tar.gz -C /data .
```

### Restore

```bash
# Restore Qdrant data
docker run --rm -v org-archivist-qdrant-storage:/data -v $(pwd):/backup alpine tar xzf /backup/qdrant-backup.tar.gz -C /data
```

### Reset

```bash
# Delete all data and start fresh
docker-compose down
docker volume rm org-archivist-qdrant-storage
docker-compose up -d qdrant
python docker/qdrant/scripts/init_collection.py
```

## References

- [Qdrant Documentation](https://qdrant.tech/documentation/)
- [HNSW Algorithm](https://arxiv.org/abs/1603.09320)
- [Python Client Docs](https://qdrant.tech/documentation/frameworks/python/)
