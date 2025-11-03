# Test Infrastructure Issues - Auth Path & Async Driver

**Date Created**: 2025-11-03
**Status**: ⏸️ Blocked - Awaiting Fix
**Severity**: 🔴 HIGH - Blocks all API/E2E test execution
**Related Task**: Archon Project "Phase 4 Testing Fixes" - Task TBD
**Prerequisites**: ✅ ENUM fix completed (Task 78ed3c60-77d7-4eee-b9d5-5d07ba391b0e)

---

## Issue Summary

After successfully fixing the SQLAlchemy ENUM configuration issue, two additional problems prevent the API test suite from running:

1. **Auth Endpoint 404**: Test helper tries wrong authentication path
2. **Async Driver Error**: Application loads sync `psycopg2` instead of async `asyncpg` driver

These issues block **100% of API endpoint tests** and **100% of E2E workflow tests** from executing.

---

## Issue 1: Authentication Endpoint Path Mismatch

### The Problem

Tests fail during authentication setup with:
```
WARNING: Not found [a14b8f5d-a225-4ca7-a6ce-a5d89c19e18a]: /api/v1/auth/login
HTTP Request: POST http://testserver/api/v1/auth/login "HTTP/1.1 404 Not Found"
token = None
```

Result: `headers = {'Authorization': 'Bearer None'}` causes subsequent API calls to fail.

### Root Cause

The `get_auth_token()` helper function in test files is requesting `/api/v1/auth/login`, but this endpoint doesn't exist or is mounted at a different path.

**Evidence from test output**:
```python
# From test_outputs_api.py (inferred from error)
def get_auth_token(client, email: str, password: str):
    response = client.post(
        "/api/v1/auth/login",  # ❌ This path returns 404
        json={"username": email, "password": password}
    )
    return response.json().get("access_token")
```

### Why This Matters

**Impact on Testing**:
- ❌ Cannot authenticate test users
- ❌ All authenticated endpoint tests fail (40 API tests)
- ❌ All E2E workflow tests fail (15 tests)
- ❌ Cannot test role-based permissions (Writer/Editor/Admin)
- ❌ Total blockage: **55 tests** affected

**Impact on Development**:
- Cannot validate API security
- Cannot test multi-user scenarios
- Cannot verify permission enforcement
- Regression risks increase without test coverage

### Suspected Fix

**Option A: Correct the Auth Path** (Most Likely)

Find the actual auth endpoint by checking:
```bash
# Check what auth routes are registered
grep -r "auth/login\|/login\|/token" backend/app/api/auth.py
grep -r "router.post.*login" backend/app/api/auth.py
```

Likely scenarios:
1. Path is `/api/auth/login` (no `v1` prefix)
2. Path is `/auth/login` (no `api` prefix)
3. Path is `/api/v1/token` (OAuth2 standard)
4. Auth uses OAuth2 token endpoint pattern

**Expected fix in test_outputs_api.py**:
```python
def get_auth_token(client, email: str, password: str):
    # Check actual auth endpoint path first!
    # Likely one of:
    # - /api/auth/login
    # - /auth/token
    # - /api/v1/token
    response = client.post(
        "/api/auth/login",  # ✅ Corrected path
        json={"username": email, "password": password}
    )
    if response.status_code != 200:
        return None
    return response.json().get("access_token")
```

**Option B: Auth Endpoint Missing** (Less Likely)

If no login endpoint exists, may need to:
1. Create login endpoint in `backend/app/api/auth.py`
2. Or use test-specific authentication bypass
3. Or mock JWT token generation for tests

### Investigation Steps

1. **Find the actual auth endpoint**:
   ```bash
   # Check auth router
   grep -n "router.post\|@router.post" backend/app/api/auth.py

   # Check how auth is mounted in main.py
   grep -n "auth" backend/app/main.py | grep -i "include\|mount"
   ```

2. **Check auth API documentation**:
   - Look at `backend/app/api/auth.py` for available endpoints
   - Check if using FastAPI OAuth2PasswordBearer (uses `/token`)
   - Verify request body format (username/password vs email/password)

3. **Test the correct path**:
   ```bash
   # Once found, test manually
   curl -X POST http://localhost:8000/api/auth/login \
     -H "Content-Type: application/json" \
     -d '{"username": "test@test.com", "password": "password"}'
   ```

---

## Issue 2: Async Driver Configuration Error

### The Problem

API requests fail with:
```
ERROR: Request [d9a39eed-a53d-4c98-870c-0428e2e2d33d] failed:
error=The asyncio extension requires an async driver to be used.
The loaded 'psycopg2' is not async. duration=13.32ms
```

Full error shows SQLAlchemy's async session trying to use sync `psycopg2` driver instead of async `asyncpg`.

### Root Cause

**FastAPI app uses async SQLAlchemy** but somewhere in the test configuration, the database connection is being initialized with the **synchronous `psycopg2` driver** instead of the asynchronous `asyncpg` driver.

**Where the mismatch occurs**:
1. Test fixtures in `conftest.py` create async database sessions
2. But application code initializes with sync driver during TestClient startup
3. Environment variable `TEST_DATABASE_URL` may be malformed
4. Database session dependency override may be incorrect

### Why This Matters

**Impact on Architecture**:
- ❌ FastAPI async endpoints cannot function with sync driver
- ❌ Defeats purpose of async SQLAlchemy (performance benefits lost)
- ❌ Database operations will block event loop
- ❌ Production-dev parity broken (prod uses async, tests use sync)

**Impact on Testing**:
- ❌ Cannot test any database operations in API context
- ❌ All API endpoint tests fail (40 tests)
- ❌ All E2E workflow tests fail (15 tests)
- ❌ Database integration tests may pass but not reflect real behavior

**Impact on Production**:
- ⚠️ Tests pass with sync driver but production uses async
- ⚠️ Bugs in async code paths won't be caught
- ⚠️ Performance issues won't be detected
- ⚠️ Concurrency bugs only appear in production

### Suspected Fix

**Option A: Fix DATABASE_URL in Test Environment** (Most Likely)

The connection string needs to use the **asyncpg driver**, not psycopg2.

**Check current configuration**:
```bash
# Look at test database URL format
grep "DATABASE_URL\|POSTGRES" backend/tests/conftest.py
grep "DATABASE_URL" pytest.ini
grep "TEST_DATABASE_URL" .env
```

**Expected format**:
```python
# ❌ WRONG - Uses psycopg2 (sync driver)
DATABASE_URL = "postgresql://user:pass@host:port/dbname"

# ✅ CORRECT - Uses asyncpg (async driver)
DATABASE_URL = "postgresql+asyncpg://user:pass@host:port/dbname"
#              ^^^^^^^^^^^^^^^^^ This part is critical!
```

**Fix location**: `backend/tests/conftest.py`
```python
# Current (suspected issue)
TEST_DATABASE_URL = "postgresql://test_user:test_password@postgres-test:5432/org_archivist_test"

# Fixed
TEST_DATABASE_URL = "postgresql+asyncpg://test_user:test_password@postgres-test:5432/org_archivist_test"
```

**Option B: Fix Database Session Fixture** (Also Likely)

The test fixtures may be creating sessions incorrectly.

**Check conftest.py**:
```python
# Make sure using create_async_engine, not create_engine
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession

@pytest_asyncio.fixture(scope="function")
async def db_engine():
    # Must use postgresql+asyncpg:// URL here
    engine = create_async_engine(
        TEST_DATABASE_URL,  # Must have +asyncpg
        echo=False,
        pool_pre_ping=True,
    )
    yield engine
    await engine.dispose()

@pytest_asyncio.fixture(scope="function")
async def db_session(db_engine):
    # Must use AsyncSession
    async with AsyncSession(db_engine) as session:
        yield session
        await session.rollback()
```

**Option C: Fix Dependency Override** (Less Likely)

The `get_db` dependency override in tests may be incorrect.

**Check test setup**:
```python
# In test files or conftest.py
@pytest.fixture
def client(db_session):
    app.dependency_overrides[get_db] = lambda: db_session
    #                                  ^^^^^^^^^^^^^^^^^^
    # This override must return async session
    with TestClient(app) as tc:
        yield tc
    app.dependency_overrides.clear()
```

### Investigation Steps

1. **Check all DATABASE_URL occurrences**:
   ```bash
   # Find where URLs are defined
   grep -r "postgresql://" backend/tests/
   grep -r "DATABASE_URL" backend/tests/
   grep -r "DATABASE_URL" pytest.ini
   grep -r "TEST_DATABASE_URL" .env
   ```

2. **Verify conftest.py uses async patterns**:
   ```bash
   # Check imports
   grep "from sqlalchemy" backend/tests/conftest.py | grep -i async

   # Check engine creation
   grep "create.*engine" backend/tests/conftest.py

   # Check session creation
   grep "Session" backend/tests/conftest.py
   ```

3. **Check pytest-asyncio configuration**:
   ```bash
   # Verify pytest.ini has correct asyncio mode
   grep "asyncio_mode" pytest.ini
   ```

4. **Test with explicit async URL**:
   ```bash
   # Run test with explicit asyncpg URL
   TEST_DATABASE_URL="postgresql+asyncpg://test_user:test_password@localhost:5433/org_archivist_test" \
     pytest backend/tests/test_outputs_api.py::TestCreateOutput::test_create_output_authenticated_user -v
   ```

---

## Combined Impact Analysis

### Tests Blocked

| Test Category | Count | Status | Impact |
|---------------|-------|--------|--------|
| API Endpoint Tests | 40 | ❌ 0% executed | All require auth + DB |
| E2E Workflow Tests | 15 | ❌ 0% executed | All require auth + DB |
| Database Integration | 32 | ⚠️ May pass | Use direct DB connection |
| Total Blocked | 55 | ❌ Blocked | 100% of API/E2E coverage |

### Business Impact

**Immediate**:
- Cannot validate Phase 4 implementation
- Cannot verify authentication/authorization
- Cannot test role-based access control
- Cannot validate API contract compliance

**Long-term**:
- Regression risks increase
- Production bugs more likely
- Performance issues undetected
- Security vulnerabilities possible

### Development Velocity Impact

**Current State**:
- ✅ ENUM fix: Complete (1 blocker resolved)
- ❌ Auth path: Blocking 55 tests
- ❌ Async driver: Blocking 55 tests
- 📊 Overall test execution: **0% of API/E2E tests running**

**After Fix**:
- 🎯 Expected: 55/55 tests executable
- 🎯 Target: 90%+ pass rate
- 🎯 Coverage: 80%+ for Phase 4 modules

---

## Recommended Action Plan

### Phase 1: Quick Investigation (15 minutes)

1. **Find auth endpoint**:
   ```bash
   grep -n "router.post.*login\|router.post.*token" backend/app/api/auth.py
   grep -n "include_router.*auth" backend/app/main.py
   ```

2. **Check DATABASE_URL formats**:
   ```bash
   grep -r "postgresql://" backend/tests/ | grep -v "asyncpg"
   ```

3. **Document findings** in issue tracker

### Phase 2: Fix Auth Path (30 minutes)

1. Correct `get_auth_token()` helper function
2. Update all test files using auth
3. Verify auth request body format
4. Test single auth flow works

### Phase 3: Fix Async Driver (45 minutes)

1. Update all `postgresql://` to `postgresql+asyncpg://`
2. Verify conftest.py uses async engine/session
3. Check dependency overrides are async-compatible
4. Test single database operation works

### Phase 4: Validation (30 minutes)

1. Run single API test end-to-end
2. Run all 40 API endpoint tests
3. Run all 15 E2E workflow tests
4. Measure and document coverage

**Total Estimated Time**: 2 hours

---

## Success Criteria

### Auth Path Fix Complete When:
- [ ] `get_auth_token()` returns valid JWT token
- [ ] No 404 errors on auth endpoint
- [ ] Test users can authenticate
- [ ] Authorization header contains valid token

### Async Driver Fix Complete When:
- [ ] No "psycopg2 is not async" errors
- [ ] All DATABASE_URLs use `postgresql+asyncpg://` format
- [ ] Database operations complete without blocking
- [ ] Async fixtures work correctly with TestClient

### Overall Success When:
- [ ] At least 1 API test passes end-to-end
- [ ] No authentication failures
- [ ] No database driver errors
- [ ] Can execute full test suite (may have other failures)

---

## Related Documentation

- **ENUM Fix**: `/docs/sqlalchemy-enum-configuration-issue.md` (✅ Completed)
- **PostgreSQL Setup**: `/docs/postgresql-enum-types-issue.md`
- **Migration Summary**: `POSTGRESQL_MIGRATION_SUMMARY.md`
- **Test Configuration**: `pytest.ini`, `backend/tests/conftest.py`

---

## Files to Review

### For Auth Path Issue:
1. `backend/app/api/auth.py` - Find actual auth endpoint
2. `backend/app/main.py` - Check how auth router is mounted
3. `backend/tests/test_outputs_api.py` - Fix get_auth_token() helper
4. `backend/tests/test_outputs_e2e.py` - May also have auth helpers

### For Async Driver Issue:
1. `backend/tests/conftest.py` - Check DATABASE_URL and fixtures
2. `pytest.ini` - Check asyncio configuration
3. `.env` - Check TEST_DATABASE_URL format
4. `backend/app/db/session.py` - Check async session configuration

---

## Technical Deep Dive

### Why +asyncpg Matters

**PostgreSQL driver landscape**:
- **psycopg2** (sync): Traditional blocking driver
- **psycopg3** (hybrid): Both sync and async modes
- **asyncpg** (async): Pure async driver, fastest performance

**SQLAlchemy async support**:
- Requires async driver to work
- Uses `asyncio` for concurrent operations
- Dialect specified in URL: `postgresql+asyncpg://`

**URL format breakdown**:
```
postgresql+asyncpg://user:pass@host:port/database
^^^^^^^^^^ ^^^^^^^^
│          │
│          └─ Dialect: asyncpg driver
└──────────── Database: PostgreSQL
```

### Why TestClient + Async Is Tricky

**FastAPI TestClient** uses `requests` library which is **synchronous**, but creates an event loop to run async endpoints. This works fine, but:

1. Database sessions must be async-aware
2. Dependency overrides must maintain async pattern
3. Lifespan events must be mocked or handled
4. Event loop management must be correct

**Common pitfall**:
```python
# ❌ WRONG - Creates sync session
@pytest.fixture
def client(db_session):
    app.dependency_overrides[get_db] = lambda: db_session
    with TestClient(app) as tc:
        yield tc

# ✅ CORRECT - Uses async session properly
@pytest.fixture
def client(db_session):
    async def override_get_db():
        yield db_session
    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as tc:
        yield tc
```

---

## Potential Edge Cases

### Auth Endpoint Variations

The auth endpoint could be:
1. Using FastAPI OAuth2PasswordBearer (standard `/token`)
2. Custom login endpoint with different request schema
3. Using form data instead of JSON
4. Requiring additional headers (X-API-Key, etc.)
5. Returning different token formats (JWT vs opaque token)

### Database URL Variations

The URL might need:
1. SSL parameters: `?ssl=require`
2. Connection pooling config: `?pool_size=10`
3. Different host in Docker vs local: `postgres-test` vs `localhost`
4. Port differences: 5433 (test) vs 5432 (prod)

---

## Future Improvements

### After Immediate Fix:

1. **Document auth endpoint** in API documentation
2. **Centralize test helpers** (DRY principle)
3. **Add auth fixture** to conftest.py
4. **Create database URL builder** to ensure consistency
5. **Add connection pooling** for test performance

### Test Infrastructure Hardening:

1. **Add database connection checks** in conftest
2. **Validate URLs** before test execution
3. **Add better error messages** for common misconfigurations
4. **Create test environment validator** script
5. **Document test setup** in README

---

## Summary Checklist

### Current State:
- [x] PostgreSQL test database running
- [x] Alembic migrations applied
- [x] ENUM types created and working
- [x] SQLAlchemy ENUM configuration fixed
- [ ] Auth endpoint path corrected
- [ ] Async database driver configured
- [ ] API tests executable

### To Complete:
- [ ] Fix auth path in test helpers
- [ ] Change all URLs to postgresql+asyncpg://
- [ ] Verify conftest.py async configuration
- [ ] Test single API endpoint works
- [ ] Run full test suite
- [ ] Document final configuration

---

**Last Updated**: 2025-11-03
**Status**: Ready for Implementation
**Priority**: P0 - CRITICAL (Blocks all API/E2E testing)
**Estimated Time**: 2 hours
**Dependencies**: ✅ ENUM fix complete

---

**Next Action**: Begin Phase 1 investigation to identify exact auth path and database URL issues.
