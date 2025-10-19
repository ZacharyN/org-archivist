# Backend Integration Tests

Comprehensive integration tests for the Org Archivist FastAPI backend.

## Test Coverage

### System Endpoints (`test_health.py`)
- Health check endpoint
- Root API information endpoint
- Metrics endpoint
- Request ID and timing headers
- Error handling (404, 405)

### Document Management (`test_documents.py`)
- Document upload with validation
- List documents with filtering and pagination
- Get document by ID
- Delete documents
- Document statistics
- Document search
- File type validation
- Empty file rejection

### Query & Generation (`test_query.py`)
- Query endpoint with filters
- Streaming query endpoint
- Audience-specific queries
- Query validation
- Response structure validation

### Chat (`test_chat.py`)
- Chat endpoint
- New conversation creation
- Conversation continuation
- Conversation history retrieval
- List conversations
- Delete conversations
- Message validation

### Prompt Management (`test_prompts.py`)
- List prompts with filtering
- Create prompts
- Get prompt by ID
- Update prompts
- Delete prompts
- Prompt validation
- Category validation
- Variable extraction

### Configuration (`test_config.py`)
- Get configuration
- Update configuration (full and partial)
- Configuration validation
- Reset to defaults
- LLM settings
- RAG parameters
- User preferences

## Running Tests

### Run all tests
```bash
cd backend
pytest
```

### Run with coverage report
```bash
pytest --cov=app --cov-report=html
```

### Run specific test file
```bash
pytest tests/test_health.py
```

### Run specific test
```bash
pytest tests/test_health.py::test_health_check
```

### Run with verbose output
```bash
pytest -v
```

### Run only fast tests (skip slow ones)
```bash
pytest -m "not slow"
```

## Test Requirements

- Python 3.11+
- All dependencies from `requirements.txt`
- FastAPI application must be importable

## Test Structure

```
tests/
├── __init__.py
├── README.md
├── conftest.py              # Pytest fixtures and configuration
├── test_health.py          # System endpoints tests
├── test_documents.py       # Document management tests
├── test_query.py           # Query/generation tests
├── test_chat.py            # Chat endpoint tests
├── test_prompts.py         # Prompt management tests
└── test_config.py          # Configuration tests
```

## Coverage Goals

- **Target**: >80% code coverage on critical paths
- **Current**: Run `pytest --cov=app` to see current coverage
- **Report**: HTML coverage report generated in `htmlcov/index.html`

## Writing New Tests

1. Add test file to `tests/` directory with `test_` prefix
2. Use fixtures from `conftest.py` for common test data
3. Follow naming convention: `test_<feature>_<scenario>`
4. Use descriptive docstrings
5. Test both success and failure cases

### Example Test
```python
def test_endpoint_success(client, sample_data):
    """Test that endpoint handles valid data correctly."""
    response = client.post("/api/endpoint", json=sample_data)

    assert response.status_code == 200
    data = response.json()
    assert "expected_field" in data
```

## CI/CD Integration

Tests are designed to run in CI/CD pipelines:

```bash
# Install dependencies
pip install -r requirements.txt

# Run tests with coverage
pytest --cov=app --cov-report=xml --cov-fail-under=80

# Tests will fail if coverage drops below 80%
```

## Troubleshooting

### Import Errors
Ensure you're in the `backend/` directory when running tests:
```bash
cd backend
pytest
```

### Coverage Too Low
Identify untested code:
```bash
pytest --cov=app --cov-report=term-missing
```

### Slow Tests
Run only fast tests:
```bash
pytest -m "not slow"
```

## Test Markers

- `@pytest.mark.integration` - Integration tests
- `@pytest.mark.unit` - Unit tests
- `@pytest.mark.slow` - Slow-running tests
- `@pytest.mark.requires_db` - Requires database
- `@pytest.mark.requires_qdrant` - Requires Qdrant

Use markers to selectively run tests:
```bash
pytest -m integration      # Only integration tests
pytest -m "not slow"       # Skip slow tests
pytest -m "requires_db"    # Only tests needing DB
```
