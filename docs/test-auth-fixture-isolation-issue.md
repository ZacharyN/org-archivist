# Test Authentication Fixture Isolation Issue

**Status:** 🔴 BLOCKING
**Severity:** P0 - Critical
**Impact:** 55 API and E2E tests cannot execute (100% of Phase 4 integration tests)
**Date Identified:** 2025-11-03
**Last Updated:** 2025-11-03

---

## Executive Summary

API and E2E tests fail during authentication with "Invalid credentials" errors despite test users being properly created in the database. The root cause is a transaction/session isolation issue between async test fixtures and the sync TestClient, causing authentication queries to not see test data committed in the fixture context.

**Current State:**
- ✅ Async driver issue FIXED (DATABASE_URL now uses `postgresql+asyncpg://`)
- ✅ ENUM configuration FIXED (using values instead of names)
- ✅ Auth endpoint path FIXED (`/api/auth/login` instead of `/api/v1/auth/login`)
- ❌ Authentication fails with HTTP 401 - test users not visible to login endpoint

---

## Problem Description

### Symptom
```python
# Test output:
INFO     app.api.auth:auth.py:214 Login attempt for email: writer@test.com
WARNING  app.api.auth:auth.py:224 Login failed: Invalid credentials for writer@test.com
```

The login endpoint cannot find test users that were created by the `test_users` fixture, despite:
- Users being successfully created with `AuthService.hash_password()`
- Database connection being established
- No errors during user creation

### Root Cause

The issue stems from mixing **async fixtures** with **sync TestClient**:

1. **Test Users Created in Async Context:**
   ```python
   @pytest_asyncio.fixture(scope="function")
   async def test_users(db_session):  # async fixture
       # Create users with hashed passwords
       writer = User(
           email="writer@test.com",
           hashed_password=AuthService.hash_password("WriterPass123!"),
           ...
       )
       db_session.add(writer)
       await db_session.commit()  # Commit in async transaction
       return users
   ```

2. **Login Endpoint Uses Different Connection:**
   ```python
   # The auth module creates its own engine
   _engine = create_async_engine(settings.database_url)

   # Login endpoint uses this engine, which may not see fixture data
   async def login(form_data, db: AsyncSession = Depends(get_db)):
       user = await db.execute(select(User).where(User.email == email))
       # Returns None - user not found!
   ```

3. **Transaction Isolation Problem:**
   - Test fixture uses `db_session` with rollback strategy
   - Auth module creates separate connection pool
   - Even with dependency override, transactions may be isolated
   - TestClient runs synchronously, potentially outside fixture transaction context

---

## Technical Details

### Current Test Architecture

```
┌─────────────────────────────────────────────────┐
│ Test Fixture (Async)                            │
│ ┌─────────────────────────────────────────────┐ │
│ │ db_session (AsyncSession)                   │ │
│ │ - Transaction with rollback                 │ │
│ │ - Creates test users                        │ │
│ │ - Commits within transaction                │ │
│ └─────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────┐
│ TestClient (Sync) → FastAPI App                 │
│ ┌─────────────────────────────────────────────┐ │
│ │ Auth Module get_db()                        │ │
│ │ - Creates new AsyncSession from engine      │ │
│ │ - May not see fixture transaction data     │ │
│ │ - Queries return None for test users       │ │
│ └─────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────┘
```

### Failed Approaches

1. **Dependency Override (Current):**
   ```python
   # In conftest.py
   app.dependency_overrides[auth_get_db] = override_auth_get_db
   ```
   **Issue:** Override happens after auth module initializes its engine

2. **DATABASE_URL Environment Variable:**
   ```python
   os.environ["DATABASE_URL"] = TEST_DATABASE_URL
   ```
   **Issue:** Fixes driver issue but doesn't solve transaction isolation

---

## Recommended Solutions

### Option A: Disable Transaction Rollback for API Tests (RECOMMENDED)

**Pros:**
- Most reliable for integration testing
- Matches production behavior
- No mixing of async/sync contexts
- Used by FastAPI/Starlette test patterns

**Cons:**
- Tests must manually clean up data
- Slightly slower test execution

**Implementation:**
```python
@pytest_asyncio.fixture(scope="function")
async def db_engine():
    """Create test database engine WITHOUT transaction rollback"""
    engine = create_async_engine(TEST_DATABASE_URL, echo=False, poolclass=NullPool)

    # Create all tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    # Clean up - drop all data
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    await engine.dispose()


@pytest_asyncio.fixture(scope="function")
async def db_session(db_engine):
    """Create session that commits directly to database"""
    async_session = async_sessionmaker(
        bind=db_engine,
        class_=AsyncSession,
        expire_on_commit=False
    )

    async with async_session() as session:
        yield session
        # No rollback - data persists for TestClient


@pytest.fixture
def client(db_session):
    """Override auth get_db with committed session"""
    from app.api.auth import get_db as auth_get_db

    async def override_get_db():
        # Return the same session that has committed data
        yield db_session

    app.dependency_overrides[auth_get_db] = override_get_db
    app.router.lifespan_context = mock_lifespan

    with TestClient(app) as client:
        yield client

    app.dependency_overrides.clear()
```

**Migration Path:**
1. Update `db_session` fixture to remove transaction rollback
2. Add cleanup logic to drop tables after each test
3. Verify test isolation with parallel test runs
4. Update 55 API/E2E tests to work with committed data

---

### Option B: Use httpx.AsyncClient Instead of TestClient

**Pros:**
- Fully async testing
- No sync/async mixing issues
- Better for async applications

**Cons:**
- Requires rewriting all test methods as async
- More complex test structure
- Larger refactoring effort

**Implementation:**
```python
@pytest_asyncio.fixture
async def async_client(db_session):
    """Use httpx.AsyncClient for fully async testing"""
    from httpx import AsyncClient
    from app.api.auth import get_db as auth_get_db

    async def override_get_db():
        yield db_session

    app.dependency_overrides[auth_get_db] = override_get_db

    async with AsyncClient(app=app, base_url="http://test") as client:
        yield client

    app.dependency_overrides.clear()


# Test methods become async
@pytest.mark.asyncio
async def test_create_output(async_client, test_users):
    response = await async_client.post("/api/auth/login", json={...})
    assert response.status_code == 200
```

**Migration Path:**
1. Install httpx: `pip install httpx`
2. Convert `client` fixture to `async_client`
3. Convert all test methods to async
4. Update test assertions and helpers

---

### Option C: Session-Level Fixtures with Manual Cleanup

**Pros:**
- Minimal code changes
- Faster test execution (reuse connections)

**Cons:**
- Risk of test pollution
- Requires careful cleanup management
- May hide isolation bugs

**Implementation:**
```python
@pytest_asyncio.fixture(scope="session")
async def db_engine():
    """Session-level engine for all tests"""
    engine = create_async_engine(TEST_DATABASE_URL)
    yield engine
    await engine.dispose()


@pytest_asyncio.fixture(scope="function")
async def db_session(db_engine):
    """Function-level session with manual cleanup"""
    async_session = async_sessionmaker(bind=db_engine, expire_on_commit=False)

    async with async_session() as session:
        yield session
        await session.commit()  # Ensure data is committed

    # Manual cleanup after test
    async with async_session() as cleanup_session:
        await cleanup_session.execute(text("TRUNCATE TABLE users CASCADE"))
        await cleanup_session.commit()
```

---

## Comparison Matrix

| Solution | Reliability | Effort | Speed | Production Parity | Recommendation |
|----------|-------------|--------|-------|-------------------|----------------|
| **Option A** | ⭐⭐⭐⭐⭐ | Medium | Medium | ⭐⭐⭐⭐⭐ | ✅ **BEST** |
| **Option B** | ⭐⭐⭐⭐ | High | Slow | ⭐⭐⭐⭐ | Alternative |
| **Option C** | ⭐⭐⭐ | Low | Fast | ⭐⭐⭐ | Quick fix only |

---

## Implementation Plan (Option A)

### Phase 1: Update Database Fixtures (2-3 hours)
```bash
# Files to modify:
backend/tests/conftest.py
  - Remove transaction rollback from db_session
  - Add table creation/cleanup to db_engine
  - Update client fixture dependency override
```

### Phase 2: Verify Test Isolation (1-2 hours)
```bash
# Run tests in parallel to check isolation
pytest backend/tests/test_outputs_api.py -n 4 -v

# Check for test pollution
pytest backend/tests/test_outputs_api.py --count=3
```

### Phase 3: Update Test Helpers (1 hour)
```bash
# Files to update:
backend/tests/test_outputs_api.py
  - get_auth_token() helper
  - Test data cleanup assertions
```

### Phase 4: Run Full Test Suite (1 hour)
```bash
# Verify all 55 tests pass
pytest backend/tests/test_outputs_api.py -v
pytest backend/tests/test_outputs_e2e.py -v
```

**Total Estimated Effort:** 5-7 hours

---

## Success Criteria

- ✅ All 55 API and E2E tests pass
- ✅ Authentication succeeds with valid credentials
- ✅ Test users visible to login endpoint
- ✅ Tests remain isolated (parallel execution passes)
- ✅ No test data pollution between tests
- ✅ Test execution time < 30 seconds for API suite

---

## Related Files

**Test Configuration:**
- `backend/tests/conftest.py` - Main fixtures file
- `backend/tests/pytest.ini` - Pytest configuration

**Test Files Blocked:**
- `backend/tests/test_outputs_api.py` - 40 tests blocked
- `backend/tests/test_outputs_e2e.py` - 15 tests blocked

**Application Code:**
- `backend/app/api/auth.py` - Authentication endpoint
- `backend/app/api/outputs.py` - Outputs API (requires auth)
- `backend/app/db/session.py` - Database session management

---

## References

- FastAPI Testing Docs: https://fastapi.tiangolo.com/advanced/testing-database/
- SQLAlchemy Async Testing: https://docs.sqlalchemy.org/en/20/orm/extensions/asyncio.html#testing
- pytest-asyncio: https://pytest-asyncio.readthedocs.io/en/latest/

---

## Appendix: Debugging Log

```
2025-11-03 17:42:46 - Login attempt for email: writer@test.com
2025-11-03 17:42:46 - Login failed: Invalid credentials for writer@test.com

Test Result: 401 Unauthorized
Token: None
Expected: 201 Created with valid auth token

Root Cause Analysis:
1. Test fixture creates user in async transaction
2. FastAPI TestClient creates new connection
3. New connection doesn't see uncommitted fixture data
4. Login query returns None (user not found)
5. Authentication fails with "Invalid credentials"
```
