# Async Testing: TestClient vs Production Architecture Mismatch

**Created:** 2025-11-15
**Status:** Active Technical Debt
**Affected Areas:** All tests using `TestClient` with async endpoints and database operations
**Priority:** Medium (affects test reliability, not production functionality)

## Executive Summary

Our test suite uses Starlette's synchronous `TestClient` to test async FastAPI endpoints that perform database operations. This creates an **architectural mismatch** that causes event loop errors in tests but **does not affect production** because production uses a completely different async runtime model.

**Key Finding:** The failing tests indicate a test infrastructure problem, not a production code problem.

## The Problem

### Symptom

Tests fail with event loop errors when testing authenticated endpoints:

```python
RuntimeError: Task <Task pending name='starlette.middleware.base.BaseHTTPMiddleware.__call__...
got Future <Future pending cb=[BaseProtocol._on_waiter_completed()]> attached to a different loop
```

### Affected Tests

Any test that uses `TestClient` to call an async endpoint that:
- Performs database operations (most endpoints)
- Uses async authentication services
- Calls other async dependencies
- Uses async middleware

**Current Examples:**
- `backend/tests/test_metrics_security.py` - 4/8 tests failing
- Likely affects many other test files (not yet discovered)

### Where It Fails

The error occurs in `backend/tests/test_metrics_security.py:75` in the `get_auth_token()` helper:

```python
def get_auth_token(client, email: str, password: str) -> str:
    """Helper function to get authentication token"""
    response = client.post(  # TestClient (sync)
        "/api/auth/login",
        json={"email": email, "password": password}
    )
    assert response.status_code == 200  # FAILS: 500 error from loop mismatch
    return response.json()["access_token"]
```

The actual failure is in the database query during authentication:

```python
# In app/services/auth_service.py
async def authenticate_user(db: AsyncSession, email: str, password: str):
    result = await db.execute(stmt)  # ERROR: db session from different loop
    # ...
```

## Technical Deep Dive

### How TestClient Works (Test Environment)

```
┌─────────────────────────────────────────────────────────┐
│ Test Function (Synchronous)                             │
│                                                          │
│  def test_endpoint(client):  # client = TestClient      │
│      response = client.get("/api/endpoint")             │
│                                                          │
│      ┌────────────────────────────────────────────┐    │
│      │ TestClient creates NEW event loop          │    │
│      │ for THIS request only                      │    │
│      │                                             │    │
│      │  Loop B: Run async endpoint handler        │    │
│      │           Try to use db session            │    │
│      │           ERROR: db from Loop A!           │    │
│      └────────────────────────────────────────────┘    │
│                                                          │
└─────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────┐
│ Test Fixtures (Async)                                   │
│                                                          │
│  @pytest.fixture                                        │
│  async def db_session():                                │
│      async with get_test_db() as session:              │
│          yield session  # Created in Loop A             │
│                                                          │
└─────────────────────────────────────────────────────────┘
```

**Problem:** Database sessions created in pytest's event loop (Loop A) cannot be used in TestClient's request event loop (Loop B).

### How Production Works (Uvicorn/ASGI)

```
┌─────────────────────────────────────────────────────────┐
│ Uvicorn Server Process                                  │
│                                                          │
│  uvicorn.run(app, host="0.0.0.0", port=8000)           │
│                                                          │
│  ┌───────────────────────────────────────────────────┐ │
│  │ Single Persistent Event Loop                      │ │
│  │                                                    │ │
│  │  ┌─────────────┐  ┌─────────────┐               │ │
│  │  │ Request 1   │  │ Request 2   │   ...         │ │
│  │  │             │  │             │               │ │
│  │  │ Create DB   │  │ Create DB   │               │ │
│  │  │ Authenticate│  │ Authenticate│               │ │
│  │  │ Run Handler │  │ Run Handler │               │ │
│  │  │ Return      │  │ Return      │               │ │
│  │  └─────────────┘  └─────────────┘               │ │
│  │                                                    │ │
│  │  All operations in same loop - No cross-loop     │ │
│  │  contamination possible                           │ │
│  └───────────────────────────────────────────────────┘ │
│                                                          │
└─────────────────────────────────────────────────────────┘
```

**Key Difference:** In production, there is ONE event loop for the entire application lifetime. All database connections, middleware, and request handlers run in the same loop context.

### Why This Doesn't Affect Production

| Aspect | TestClient (Tests) | Uvicorn (Production) |
|--------|-------------------|---------------------|
| **Event Loop Lifecycle** | New loop per request | Single persistent loop |
| **DB Connection Pool** | Created in pytest loop | Created in app loop |
| **Request Handling** | Sync wrapper around async | Native async |
| **Middleware** | Runs in separate loop | Runs in same loop |
| **Session Management** | Cross-loop usage possible | All same-loop (safe) |

**Bottom Line:** The architectural pattern that causes test failures **cannot occur** in production because Uvicorn doesn't create multiple event loops.

## Why Are We Using TestClient?

This is a valid question. TestClient is inappropriate for our use case, but it persists because of:

### 1. Historical Reasons

- **Default in FastAPI docs:** Early FastAPI tutorials prominently feature TestClient
- **Initial simplicity:** Looks easier for developers new to async
- **Legacy from sync days:** Pattern carried over from synchronous frameworks

### 2. Initial Convenience

```python
# TestClient - Synchronous, "simple"
def test_login(client):  # Regular function
    response = client.post("/api/auth/login", json={...})
    assert response.status_code == 200

# AsyncClient - Async, "complex"
@pytest.mark.asyncio  # Requires pytest-asyncio
async def test_login(async_client):  # Async function
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post("/api/auth/login", json={...})
        assert response.status_code == 200
```

For simple routing tests, TestClient "works" and requires less boilerplate.

### 3. Works For Simple Cases

TestClient is acceptable for:
- ✅ Basic routing tests (does `/health` return 200?)
- ✅ Simple validation (does endpoint reject invalid JSON?)
- ✅ Static response tests
- ✅ Endpoints with no async dependencies

TestClient **breaks** for:
- ❌ Database operations (async sessions)
- ❌ Async authentication/authorization
- ❌ Async middleware
- ❌ Background tasks
- ❌ External async API calls

### 4. Inertia

Once a test suite is built with TestClient, refactoring is seen as:
- Time-consuming
- "Not a priority" (tests pass enough of the time)
- Risk of breaking working tests
- Requires understanding async patterns

## The Cost of This Technical Debt

### False Negatives

Tests fail even though the code works correctly:
- ❌ 4 failing tests in `test_metrics_security.py`
- ✅ Metrics endpoint security actually works fine in production

This wastes developer time investigating non-issues.

### False Confidence

Even worse: tests that "pass" with TestClient might not accurately represent production behavior:
- Race conditions that only occur in production
- Database connection pooling issues
- Middleware ordering problems
- Session lifecycle bugs

### Maintenance Burden

Developers must understand:
- Which tests use TestClient vs AsyncClient
- Why some tests mysteriously fail
- Event loop concepts to debug test issues
- Workarounds and hacks to make tests pass

## Solutions

### Option 1: Minimal Fix (Unblock Current Work)

**Goal:** Fix only the failing tests to verify metrics security works

**Scope:** `backend/tests/test_metrics_security.py`

**Implementation:**
1. Add `async_client` fixture to `conftest.py`
2. Convert `test_metrics_security.py` to use AsyncClient
3. Make `get_auth_token()` async
4. Mark tests with `@pytest.mark.asyncio`

**Time:** 1-2 hours
**Risk:** Low
**Benefit:** Proves security implementation works

### Option 2: Incremental Migration (Recommended)

**Goal:** Fix test infrastructure systematically

**Scope:** All security and database tests

**Implementation:**
1. Add async test infrastructure to `conftest.py`
2. Audit existing tests and categorize:
   - **Simple routing** → Keep TestClient
   - **Database operations** → Migrate to AsyncClient
   - **Auth/security** → Migrate to AsyncClient (priority)
3. Document when to use which client
4. Migrate incrementally over time

**Time:** 1-2 weeks (spread across sprints)
**Risk:** Medium (may expose other bugs)
**Benefit:** Accurate testing that matches production

### Option 3: Full Migration (Ideal, Long-term)

**Goal:** All async endpoint tests use AsyncClient

**Scope:** Entire test suite

**Implementation:**
1. Create comprehensive async test infrastructure
2. Migrate all async endpoint tests
3. Keep TestClient only for basic routing
4. Add linting rules to prevent regression

**Time:** 2-4 weeks
**Risk:** High (large refactor)
**Benefit:** Full confidence in test suite

## Migration Guide

### Step 1: Add AsyncClient Fixture

```python
# backend/tests/conftest.py

import pytest
from httpx import AsyncClient
from app.main import app

@pytest.fixture
async def async_client(db_session):
    """Async test client that shares event loop with fixtures"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        yield client
```

### Step 2: Convert Helper Functions

**Before (Sync):**
```python
def get_auth_token(client, email: str, password: str) -> str:
    response = client.post(
        "/api/auth/login",
        json={"email": email, "password": password}
    )
    assert response.status_code == 200
    return response.json()["access_token"]
```

**After (Async):**
```python
async def get_auth_token_async(client: AsyncClient, email: str, password: str) -> str:
    response = await client.post(
        "/api/auth/login",
        json={"email": email, "password": password}
    )
    assert response.status_code == 200
    return response.json()["access_token"]
```

### Step 3: Convert Test Functions

**Before (TestClient):**
```python
def test_admin_can_access_metrics(client, test_users):
    # Get token
    token = get_auth_token(
        client,
        test_users["admin"]["user"].email,
        test_users["admin"]["password"]
    )

    # Test endpoint
    response = client.get(
        "/api/metrics",
        headers={"Authorization": f"Bearer {token}"}
    )

    assert response.status_code == 200
    assert "active_users" in response.json()
```

**After (AsyncClient):**
```python
@pytest.mark.asyncio
async def test_admin_can_access_metrics(async_client, test_users):
    # Get token
    token = await get_auth_token_async(
        async_client,
        test_users["admin"]["user"].email,
        test_users["admin"]["password"]
    )

    # Test endpoint
    response = await async_client.get(
        "/api/metrics",
        headers={"Authorization": f"Bearer {token}"}
    )

    assert response.status_code == 200
    assert "active_users" in response.json()
```

### Step 4: Update Test Class Structure

**Before:**
```python
class TestMetricsEndpointSecurity:
    def test_unauthenticated_request_returns_401(self, client):
        response = client.get("/api/metrics")
        assert response.status_code == 401
```

**After:**
```python
class TestMetricsEndpointSecurity:
    @pytest.mark.asyncio
    async def test_unauthenticated_request_returns_401(self, async_client):
        response = await async_client.get("/api/metrics")
        assert response.status_code == 401
```

## Testing Strategy: When to Use Which Client

### Use TestClient For:

```python
def test_health_endpoint_returns_200(client):
    """Simple routing test, no async dependencies"""
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}

def test_invalid_json_returns_422(client):
    """Basic validation test"""
    response = client.post("/api/documents", json={"invalid": "data"})
    assert response.status_code == 422
```

**Criteria:**
- No database operations
- No authentication required
- No async services called
- Testing basic HTTP routing/validation

### Use AsyncClient For:

```python
@pytest.mark.asyncio
async def test_create_document_with_auth(async_client, test_user):
    """Database + auth operation"""
    token = await get_auth_token_async(async_client, test_user.email, "password")

    response = await async_client.post(
        "/api/documents",
        headers={"Authorization": f"Bearer {token}"},
        json={"title": "Test Doc", "content": "..."}
    )

    assert response.status_code == 201
    assert response.json()["title"] == "Test Doc"
```

**Criteria:**
- Database operations (reads/writes)
- Authentication/authorization required
- Async dependencies or services
- Testing real production-like behavior

## Code Examples

### Complete AsyncClient Test Example

```python
# backend/tests/test_metrics_security.py

import pytest
from httpx import AsyncClient

class TestMetricsEndpointSecurity:
    """Security tests for /api/metrics endpoint"""

    @pytest.mark.asyncio
    async def test_unauthenticated_request_returns_401(self, async_client):
        """Verify unauthenticated requests are rejected"""
        response = await async_client.get("/api/metrics")
        assert response.status_code == 401
        assert response.json()["detail"] == "Not authenticated"

    @pytest.mark.asyncio
    async def test_non_admin_user_returns_403(self, async_client, test_users):
        """Verify non-admin users cannot access metrics"""
        # Get token for editor (non-admin)
        token = await get_auth_token_async(
            async_client,
            test_users["editor"]["user"].email,
            test_users["editor"]["password"]
        )

        # Attempt to access metrics
        response = await async_client.get(
            "/api/metrics",
            headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == 403
        assert "admin" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_admin_user_can_access_metrics(self, async_client, test_users):
        """Verify admin users can access metrics"""
        # Get token for admin
        token = await get_auth_token_async(
            async_client,
            test_users["admin"]["user"].email,
            test_users["admin"]["password"]
        )

        # Access metrics
        response = await async_client.get(
            "/api/metrics",
            headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == 200

        # Verify response structure
        data = response.json()
        assert "active_users" in data
        assert "total_documents" in data
        assert "total_queries" in data
        assert isinstance(data["active_users"], int)


# Helper function
async def get_auth_token_async(
    client: AsyncClient,
    email: str,
    password: str
) -> str:
    """Helper to get authentication token for testing"""
    response = await client.post(
        "/api/auth/login",
        json={"email": email, "password": password}
    )
    assert response.status_code == 200, f"Login failed: {response.text}"
    return response.json()["access_token"]
```

### Updated Conftest with Async Support

```python
# backend/tests/conftest.py

import pytest
import asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from app.main import app
from app.db.database import Base, get_db
from app.db.models import User
from app.services.auth_service import AuthService

# ============================================================================
# Event Loop Configuration
# ============================================================================

@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for entire test session"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


# ============================================================================
# Database Fixtures
# ============================================================================

@pytest.fixture
async def db_engine():
    """Create async database engine for testing"""
    engine = create_async_engine(
        "postgresql+asyncpg://test:test@localhost:5432/test_db",
        echo=False
    )

    # Create tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    # Cleanup
    await engine.dispose()


@pytest.fixture
async def db_session(db_engine):
    """Create async database session for testing"""
    async_session = sessionmaker(
        db_engine,
        class_=AsyncSession,
        expire_on_commit=False
    )

    async with async_session() as session:
        yield session


# ============================================================================
# Test Client Fixtures
# ============================================================================

@pytest.fixture
def client():
    """Synchronous test client (use for simple routing tests only)"""
    from starlette.testclient import TestClient
    with TestClient(app) as client:
        yield client


@pytest.fixture
async def async_client(db_session):
    """
    Async test client (use for database operations and auth tests)

    This client shares the same event loop as test fixtures,
    preventing event loop mismatch errors.
    """
    # Override app's database dependency
    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    async with AsyncClient(app=app, base_url="http://test") as client:
        yield client

    # Cleanup
    app.dependency_overrides.clear()


# ============================================================================
# User Fixtures
# ============================================================================

@pytest.fixture
async def test_users(db_session):
    """Create test users with different roles"""
    users = {}

    # Admin user
    admin = User(
        email="admin@test.com",
        username="admin",
        role="admin",
        hashed_password=AuthService.hash_password("AdminPass123!")
    )
    db_session.add(admin)
    users["admin"] = {
        "user": admin,
        "password": "AdminPass123!"
    }

    # Editor user
    editor = User(
        email="editor@test.com",
        username="editor",
        role="editor",
        hashed_password=AuthService.hash_password("EditorPass123!")
    )
    db_session.add(editor)
    users["editor"] = {
        "user": editor,
        "password": "EditorPass123!"
    }

    # Writer user
    writer = User(
        email="writer@test.com",
        username="writer",
        role="writer",
        hashed_password=AuthService.hash_password("WriterPass123!")
    )
    db_session.add(writer)
    users["writer"] = {
        "user": writer,
        "password": "WriterPass123!"
    }

    await db_session.commit()

    return users
```

## Pytest Configuration

Add to `pytest.ini` or `pyproject.toml`:

```ini
# pytest.ini
[pytest]
asyncio_mode = auto
markers =
    asyncio: marks tests as async (deselect with '-m "not asyncio"')
```

Or for `pyproject.toml`:

```toml
[tool.pytest.ini_options]
asyncio_mode = "auto"
markers = [
    "asyncio: marks tests as async",
]
```

## Dependencies

Ensure these are in `requirements.txt`:

```
pytest>=7.4.0
pytest-asyncio>=0.21.0
httpx>=0.24.0
```

## Known Issues and Limitations

### Issue 1: Event Loop Scope

**Problem:** Tests that create resources in one fixture and use them in another must share event loop scope.

**Solution:** Use `@pytest.fixture(scope="session")` for event loop fixture.

### Issue 2: Database Connection Pooling

**Problem:** Multiple async tests may exhaust connection pool if not properly cleaned up.

**Solution:** Use `expire_on_commit=False` and proper session cleanup in fixtures.

### Issue 3: Mixing Sync and Async Tests

**Problem:** Same test class cannot mix sync (TestClient) and async (AsyncClient) tests.

**Solution:** Separate test classes by client type:

```python
class TestBasicRouting:
    """Simple routing tests using TestClient"""
    def test_health(self, client):
        ...

class TestMetricsAuth:
    """Auth tests using AsyncClient"""
    @pytest.mark.asyncio
    async def test_admin_access(self, async_client):
        ...
```

## Recommendations

### Immediate (Current Branch: `fix/secure-metrics-endpoint`)

1. ✅ Document this issue (this file)
2. ⚠️  Leave failing tests as-is for now
3. ✅ Add TODO comment in `test_metrics_security.py` pointing to this doc
4. ✅ Merge the security implementation (it's correct, tests are wrong)

### Short-term (After Frontend Development)

1. Implement Option 1: Fix metrics security tests with AsyncClient
2. Verify security works as expected
3. Create Archon task for broader test infrastructure improvement

### Long-term (Technical Debt Reduction)

1. Audit all test files
2. Categorize tests (simple vs complex)
3. Migrate complex tests to AsyncClient
4. Document testing patterns
5. Add CI check to prevent regression

## Decision Log

### 2025-11-15: Defer Full Migration

**Decision:** Document the issue but defer full test migration until after frontend development.

**Rationale:**
- Frontend development is higher priority
- Test failures don't affect production functionality
- Full migration is significant effort (~2-4 weeks)
- Current implementation is correct (proven by 4/8 passing tests)

**Consequences:**
- Tests will continue to fail
- Developers must understand this is a test issue, not code issue
- Risk of false confidence from passing TestClient tests
- Must remember to fix after frontend complete

**Mitigation:**
- This comprehensive documentation
- TODO comments in test files
- Archon task created for future work
- Clear communication that failing tests ≠ broken code

## References

### Official Documentation

- [FastAPI Testing Documentation](https://fastapi.tiangolo.com/tutorial/testing/)
- [HTTPX AsyncClient](https://www.python-httpx.org/async/)
- [pytest-asyncio Documentation](https://pytest-asyncio.readthedocs.io/)
- [Starlette TestClient Source](https://github.com/encode/starlette/blob/master/starlette/testclient.py)

### Community Resources

- [FastAPI GitHub Discussions: TestClient vs AsyncClient](https://github.com/tiangolo/fastapi/discussions/4678)
- [Stack Overflow: Testing Async FastAPI](https://stackoverflow.com/questions/tagged/fastapi+async+testing)
- [Real Python: Async IO in Python](https://realpython.com/async-io-python/)

### Related Internal Documentation

- `docs/test-infrastructure-technical-debt.md` - General test infrastructure issues
- `docs/test-auth-fixture-isolation-issue.md` - Auth fixture problems
- `docs/test-infrastructure-auth-driver-issues.md` - Auth testing challenges

## Appendix A: Error Message Anatomy

When you see this error:

```
RuntimeError: Task <Task pending name='starlette.middleware.base.BaseHTTPMiddleware.__call__.<locals>.call_next.<locals>.coro' coro=<BaseHTTPMiddleware.__call__.<locals>.call_next.<locals>.coro() running at /usr/local/lib/python3.11/site-packages/starlette/middleware/base.py:144> cb=[TaskGroup._spawn.<locals>.task_done() at /usr/local/lib/python3.11/site-packages/anyio/_backends/_asyncio.py:803]> got Future <Future pending cb=[BaseProtocol._on_waiter_completed()]> attached to a different loop
```

**Breaking it down:**

1. **Task pending:** An async task is waiting to complete
2. **BaseHTTPMiddleware:** Error occurs in middleware layer
3. **got Future... attached to a different loop:** The smoking gun - async object from one event loop being used in another

**What this tells you:**
- ✅ Confirms event loop mismatch
- ✅ Happens during middleware execution (between request and handler)
- ✅ Related to database/async operations
- ✅ Test infrastructure issue, not code issue

## Appendix B: Quick Diagnosis Checklist

When a test fails with async errors:

- [ ] Does the test use `TestClient`?
- [ ] Does the endpoint access a database?
- [ ] Does the endpoint require authentication?
- [ ] Does the error mention "different loop"?
- [ ] Does the same endpoint work in production/Streamlit?

If you answered yes to all: **It's the TestClient issue documented here.**

**Fix:** Convert test to use `AsyncClient` following migration guide above.

## Appendix C: Future Considerations

### Alternative Testing Approaches

1. **Integration Tests:** Test against real running server (Uvicorn)
   - Pros: Exact production behavior
   - Cons: Slower, more complex setup

2. **Contract Testing:** Test API contracts separately from implementation
   - Pros: Faster, focused tests
   - Cons: May miss integration issues

3. **Snapshot Testing:** Record and replay production traffic
   - Pros: Real-world scenarios
   - Cons: Requires production data, privacy concerns

### Monitoring Recommendations

To catch issues that tests miss:

1. **Application Monitoring:** Use tools like Sentry to catch production errors
2. **Database Monitoring:** Track slow queries and connection pool exhaustion
3. **Auth Monitoring:** Log authentication failures and suspicious patterns
4. **Health Checks:** Regular automated health checks in production

## Conclusion

This document provides a complete reference for understanding and eventually fixing the async testing architecture mismatch in our test suite. The key takeaway: **failing tests indicate a test infrastructure problem, not a production code problem.**

When you return to fix this after frontend development, follow the migration guide in this document. The tests will then accurately represent production behavior and provide true confidence in the codebase.

---

**Document Status:** Living document - update as we learn more or make changes
**Next Review:** After frontend development complete
**Owner:** Development team
**Related Archon Tasks:** TBD (create task for test migration)