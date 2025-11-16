# Org Archivist Test Suite

Comprehensive test suite for the Org Archivist backend API, covering authentication, document processing, AI chat, outputs management, and Phase 5 features (context persistence, sensitivity validation, audit logging).

## Directory Structure

```
tests/
├── conftest.py          # Shared fixtures (database, client, mock services)
├── api/                 # API endpoint tests (production critical)
├── services/            # Service layer tests (production critical)
├── models/              # Model and database tests (production critical)
├── e2e/                 # End-to-end integration tests (production critical)
├── validation/          # Compliance and validation tests
└── archive/             # Experimental/deprecated tests (not run in CI)
```

## Test Categories

### API Tests (`api/`)
API endpoint tests validating request/response contracts, authentication, authorization, and error handling.

**Files:**
- `test_auth.py` - Authentication endpoints (login, logout, session management)
- `test_chat.py` - AI chat endpoints
- `test_documents.py` - Document upload/management endpoints
- `test_health.py` - Health check endpoints
- `test_outputs_api.py` - Outputs API (CRUD, analytics, filtering)
- `test_prompts.py` - Prompt management endpoints
- `test_query.py` - Query endpoints
- `test_rate_limiting.py` - Rate limiting middleware
- `test_metrics_security.py` - Metrics endpoint security (admin-only)
- `test_writing_styles.py` - Writing styles API

**Run:**
```bash
pytest tests/api/ -v
```

### Service Tests (`services/`)
Service layer business logic tests, validating core functionality independent of API layer.

**Files:**
- `test_retrieval_engine.py` - Retrieval engine (vector/keyword search, hybrid scoring)
- `test_document_processor.py` - Document processing pipeline
- `test_query_cache.py` - Query caching service
- `test_success_tracking.py` - Success tracking service

**Run:**
```bash
pytest tests/services/ -v
```

### Model Tests (`models/`)
Database model and configuration tests.

**Files:**
- `test_config.py` - Configuration management
- `test_output_models.py` - Output data models
- `test_output_database.py` - Database operations for outputs

**Run:**
```bash
pytest tests/models/ -v
```

### E2E Tests (`e2e/`)
End-to-end integration tests validating complete workflows across multiple components.

**Files:**
- `test_e2e_document_processing.py` - Full document processing pipeline
- `test_outputs_e2e.py` - Outputs feature E2E workflows
- `test_conversation_context.py` - **Phase 5:** Conversation context persistence
- `test_document_sensitivity.py` - **Phase 5:** Document sensitivity validation
- `test_audit_logging.py` - **Phase 5:** Comprehensive audit logging
- `test_audit.py` - Audit system validation

**Run:**
```bash
pytest tests/e2e/ -v
```

### Validation Tests (`validation/`)
Specific validation and compliance tests.

**Files:**
- `test_document_program_validation.py` - Document-program relationship validation
- `test_audit_logging_minimal.py` - Minimal audit logging validation

**Run:**
```bash
pytest tests/validation/ -v
```

### Archive (`archive/`)
Experimental and development tests. See [archive/README.md](archive/README.md) for details.

**Not run in CI/CD pipeline.**

## Running Tests

### All Production Tests
Run all tests except archived ones:
```bash
pytest tests/ --ignore=tests/archive/ -v
```

### Quick Test (No Coverage)
```bash
pytest tests/ --ignore=tests/archive/ --no-cov -v
```

### With Coverage Report
```bash
pytest tests/ --ignore=tests/archive/ --cov=app --cov-report=html --cov-report=term
```

### Specific Test Category
```bash
# API tests only
pytest tests/api/ -v

# Service tests only
pytest tests/services/ -v

# E2E tests only
pytest tests/e2e/ -v
```

### Specific Test File
```bash
pytest tests/api/test_auth.py -v
```

### Specific Test Function
```bash
pytest tests/api/test_auth.py::test_login_success -v
```

### Run Tests in Parallel
```bash
pytest tests/ --ignore=tests/archive/ -n auto
```

### Docker Test Environment
Run tests in isolated Docker container (recommended for CI/CD):

```bash
docker run --rm --network org-archivist-network \
  -v $(pwd)/backend:/app -w /app \
  python:3.11-slim bash -c "
    pip install -q -r requirements.txt &&
    python -m pytest tests/ --ignore=tests/archive/ -v
  "
```

## Test Fixtures

Shared test fixtures are defined in `conftest.py`:

- **`db_engine`** - PostgreSQL test database engine (creates/drops tables per test)
- **`db_session`** - Async database session for test data
- **`client`** - FastAPI TestClient for API requests
- **`authenticated_user`** - User with authentication session
- **`admin_user`** - Admin user for privileged operations
- **Mock services** - Retrieval engine, vector store, embedding models

## Writing New Tests

### Test File Naming
- Prefix with `test_`
- Place in appropriate directory based on test type
- Use descriptive names (e.g., `test_outputs_api.py`, `test_retrieval_engine.py`)

### Test Function Naming
- Prefix with `test_`
- Use descriptive names indicating what is being tested
- Examples: `test_login_success`, `test_unauthorized_access_blocked`

### Using Fixtures
```python
import pytest

def test_example(client, db_session, authenticated_user):
    """Test with shared fixtures."""
    response = client.get(
        "/api/endpoint",
        headers={"Authorization": f"Bearer {authenticated_user['token']}"}
    )
    assert response.status_code == 200
```

### Async Tests
```python
import pytest_asyncio

@pytest.mark.asyncio
async def test_async_example(db_session):
    """Async test example."""
    result = await some_async_function()
    assert result is not None
```

## Test Standards

### Coverage Goals
- **Overall:** ≥80% code coverage
- **Critical paths:** ≥90% (auth, document processing, audit logging)
- **API endpoints:** 100% happy path + error cases

### Test Structure
1. **Arrange** - Set up test data and mocks
2. **Act** - Execute the function/endpoint being tested
3. **Assert** - Validate results, side effects, and error handling

### What to Test
- ✅ Happy path (successful operations)
- ✅ Error cases (invalid input, unauthorized access, not found)
- ✅ Edge cases (empty data, max limits, special characters)
- ✅ Authorization (role-based access control)
- ✅ Data validation (request/response schemas)
- ✅ Side effects (database changes, audit logs, cache updates)

### What Not to Test
- ❌ Third-party library internals
- ❌ Framework behavior (FastAPI, SQLAlchemy)
- ❌ Trivial getters/setters
- ❌ Mock implementations

## CI/CD Integration

### GitHub Actions
Tests are run automatically on:
- Pull requests to `main`
- Pushes to `main`
- Manual workflow dispatch

### Test Stages
1. **Lint** - Code quality checks (ruff, mypy)
2. **Unit/Integration** - Fast tests (API, services, models)
3. **E2E** - Full integration tests (slower, database required)
4. **Coverage** - Generate coverage report and enforce minimums

## Troubleshooting

### Tests Failing Locally
1. Ensure PostgreSQL test database is running
2. Check environment variables are set (see `conftest.py`)
3. Verify dependencies are installed: `pip install -r requirements.txt`
4. Check Docker network if running in containers

### Import Errors
- Ensure `backend/` is in Python path
- Check `__init__.py` files exist in test directories
- Verify relative imports use correct paths

### Database Connection Errors
- Verify `TEST_DATABASE_URL` environment variable
- Ensure PostgreSQL test container is running
- Check network connectivity (Docker network for containers)

### Flaky Tests
- Check for race conditions in async code
- Ensure proper test isolation (database cleanup)
- Review fixture scopes (function vs. module)
- Use `pytest-xdist` for parallel test debugging

## Phase 5 Features

The following Phase 5 features have comprehensive test coverage:

### Conversation Context Persistence (`e2e/test_conversation_context.py`)
- Multi-turn conversation tracking
- Context retrieval and continuation
- Context expiration and cleanup

### Document Sensitivity Validation (`e2e/test_document_sensitivity.py`)
- Sensitivity level enforcement
- Upload validation with confirmation
- Audit logging of sensitivity decisions

### Audit Logging (`e2e/test_audit_logging.py`, `validation/test_audit_logging_minimal.py`)
- Event capture for all critical actions
- Audit log querying with filters
- Admin-only access control
- Non-blocking audit failures

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

## Maintenance

### Regular Tasks
- Review test coverage reports weekly
- Update tests when adding new features
- Archive experimental tests when no longer needed
- Clean up deprecated tests quarterly

### Before Frontend Development
- ✅ Ensure all API endpoint tests pass
- ✅ Validate authentication and authorization flows
- ✅ Confirm request/response schemas match API documentation
- ✅ Test error responses are properly formatted

Last updated: 2025-11-16
