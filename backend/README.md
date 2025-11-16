# Org Archivist Backend

FastAPI backend for the Org Archivist RAG system - an AI-powered institutional memory system for grant writing.

## Project Structure

```
backend/
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI application entry point
│   ├── config.py            # Configuration and environment variables
│   ├── api/                 # API route handlers
│   │   ├── __init__.py
│   │   ├── documents.py     # Document management endpoints
│   │   ├── query.py         # Query and generation endpoints
│   │   ├── chat.py          # Chat conversation endpoints
│   │   ├── prompts.py       # Prompt template management
│   │   └── config.py        # System configuration endpoints
│   ├── models/              # Pydantic models
│   │   ├── __init__.py
│   │   ├── document.py      # Document-related schemas
│   │   ├── query.py         # Query/response schemas
│   │   ├── prompt.py        # Prompt template schemas
│   │   └── common.py        # Shared schemas
│   ├── services/            # Business logic
│   │   ├── __init__.py
│   │   ├── document_processor.py  # Document processing pipeline
│   │   ├── retrieval_engine.py    # Hybrid search and retrieval
│   │   ├── generation_service.py  # LLM generation
│   │   ├── prompt_manager.py      # Prompt composition
│   │   ├── quality_validator.py   # Quality checks
│   │   └── citation_manager.py    # Citation handling
│   └── middleware/          # Custom middleware
│       ├── __init__.py
│       ├── logging.py       # Request/response logging
│       └── error_handler.py # Global error handling
├── tests/                   # Test suite
│   ├── __init__.py
│   ├── test_api/           # API endpoint tests
│   ├── test_services/      # Service logic tests
│   └── conftest.py         # Pytest fixtures
├── requirements.txt         # Python dependencies
├── pyproject.toml          # Project configuration
└── README.md               # This file
```

## Installation

### Prerequisites
- Python 3.11+
- Docker and Docker Compose (for dependencies)
- Virtual environment tool (venv, conda, etc.)

### Setup

1. Create and activate virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Set up environment variables (see `../.env.example`):
```bash
cp ../.env.example ../.env
# Edit .env with your API keys and configuration
```

4. Start required services (PostgreSQL, Qdrant):
```bash
cd ..
docker-compose up -d postgres qdrant
```

## Running the Application

### Development Server

Start the FastAPI development server with auto-reload:
```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Or using the Python module:
```bash
python -m uvicorn app.main:app --reload
```

The API will be available at:
- API endpoints: http://localhost:8000/api
- Interactive docs (Swagger UI): http://localhost:8000/docs
- Alternative docs (ReDoc): http://localhost:8000/redoc
- OpenAPI schema: http://localhost:8000/openapi.json

### Production Server

For production, use Gunicorn with Uvicorn workers:
```bash
gunicorn app.main:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000
```

## Development

### Code Style

This project uses:
- **Black** for code formatting (line length: 100)
- **Ruff** for linting
- **MyPy** for type checking

Run formatters and linters:
```bash
# Format code
black app/ tests/

# Lint code
ruff check app/ tests/

# Type check
mypy app/
```

### Testing

Run tests with pytest:
```bash
# Run all tests
pytest

# Run with coverage report
pytest --cov=app --cov-report=html

# Run specific test file
pytest tests/test_api/test_documents.py

# Run with verbose output
pytest -v
```

### Adding New Dependencies

1. Add to `requirements.txt`
2. Update `pyproject.toml` dependencies
3. Install in virtual environment: `pip install -r requirements.txt`

## API Documentation

### Core Endpoints

**Health Check**
- `GET /api/health` - Service health status

**Document Management**
- `POST /api/documents/upload` - Upload documents
- `GET /api/documents` - List documents (with filters)
- `GET /api/documents/{doc_id}` - Get document details
- `DELETE /api/documents/{doc_id}` - Delete document
- `GET /api/documents/stats` - Library statistics

**Query & Generation**
- `POST /api/query` - Generate content (non-streaming)
- `POST /api/query/stream` - Generate content (streaming)

**Chat**
- `POST /api/chat` - Multi-turn conversation

**Prompts**
- `GET /api/prompts` - List prompt templates
- `POST /api/prompts` - Create template
- `PUT /api/prompts/{id}` - Update template
- `DELETE /api/prompts/{id}` - Delete template

**Configuration**
- `GET /api/config` - Get system configuration
- `PUT /api/config` - Update configuration

See `/docs` endpoint for full interactive documentation.

## Architecture

### RAG Pipeline

1. **Document Processing**
   - Text extraction (PDF, DOCX, TXT)
   - Semantic chunking
   - Embedding generation
   - Vector storage in Qdrant

2. **Retrieval**
   - Hybrid search (vector + keyword)
   - Metadata filtering
   - Re-ranking and diversification
   - Top-k selection

3. **Generation**
   - Prompt composition
   - Claude API integration
   - Streaming responses
   - Citation extraction

4. **Quality Validation**
   - Confidence scoring
   - Hallucination detection
   - Completeness checks
   - Source attribution

### Technology Stack

- **Framework**: FastAPI 0.115+
- **Vector DB**: Qdrant
- **Database**: PostgreSQL 15
- **Embeddings**: BAAI/bge-large-en-v1.5 (local) or OpenAI/Voyage
- **LLM**: Anthropic Claude Sonnet 4.5
- **RAG Framework**: LlamaIndex

## Environment Variables

Key configuration variables (see `.env.example`):

```bash
# API Keys
ANTHROPIC_API_KEY=your_key_here
OPENAI_API_KEY=your_key_here  # Optional, for OpenAI embeddings
VOYAGE_API_KEY=your_key_here  # Optional, for Voyage embeddings

# Database
DATABASE_URL=postgresql://user:pass@localhost:5432/org_archivist

# Vector Database
QDRANT_HOST=localhost
QDRANT_PORT=6333

# Embedding Model
EMBEDDING_MODEL=bge-large-en-v1.5  # or openai-text-embedding-3-small

# Application
LOG_LEVEL=INFO
CORS_ORIGINS=http://localhost:3000,http://localhost:8000,http://frontend:3000
```

## Troubleshooting

### Common Issues

**Import errors**
- Ensure virtual environment is activated
- Reinstall dependencies: `pip install -r requirements.txt`

**Database connection errors**
- Verify PostgreSQL is running: `docker ps`
- Check DATABASE_URL in `.env`
- Test connection: `docker exec -it org-archivist-postgres psql -U user -d org_archivist`

**Qdrant connection errors**
- Verify Qdrant is running: `curl http://localhost:6333`
- Check QDRANT_HOST and QDRANT_PORT in `.env`

**API key errors**
- Verify ANTHROPIC_API_KEY is set in `.env`
- Check key validity with Anthropic dashboard

## Contributing

1. Create feature branch from `main`
2. Write tests for new functionality
3. Ensure all tests pass: `pytest`
4. Format and lint code: `black . && ruff check .`
5. Commit with conventional commit messages
6. Push and create pull request

## License

Internal project - Nebraska Children and Families Foundation
