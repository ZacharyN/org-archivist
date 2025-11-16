# Outputs API DatabaseService Dependency Injection Issue

**Date:** 2025-11-03
**Status:** 🔴 BLOCKING - 40+ API tests failing
**Severity:** P0 - Critical
**Impact:** Blocks test verification tasks (4efe00cf, 3dd07b54)

---

## Executive Summary

The outputs API endpoints instantiate `DatabaseService` directly instead of using dependency injection, causing all 40+ API tests to fail with 500 errors. The service tries to connect to `localhost:5432` instead of using the test database fixtures, making the endpoints untestable.

**Current State:**
- ✅ Authentication works (fixture isolation issue fixed)
- ❌ Outputs API endpoints fail with database connection errors (500)
- ❌ 40+ API tests blocked
- ❌ 15 E2E tests will fail when they reach outputs operations
- ❌ Cannot verify Phase 4 completion (150/150 tests target)

---

## Problem Description

### Symptom

```python
# Test execution:
INFO     app.api.outputs:outputs.py:132 Creating output 'New Grant Proposal' for user writer@test.com
INFO     app.services.database:database.py:35 DatabaseService initialized
ERROR    app.services.database:database.py:53 Failed to create database pool:
         Multiple exceptions: [Errno 111] Connect call failed ('::1', 5432, 0, 0),
         [Errno 111] Connect call failed ('127.0.0.1', 5432)
ERROR    app.api.outputs:outputs.py:165 Failed to create output: Multiple exceptions...
Response: 500 Internal Server Error
```

**Expected:** Test should use test database fixtures at `postgres-test:5432`
**Actual:** DatabaseService connects to `localhost:5432` (doesn't exist)

---

## Root Cause

### Current Implementation (Problematic)

**File:** `backend/app/api/outputs.py`

```python
@router.post("", response_model=OutputResponse, status_code=201)
async def create_output(
    request: CreateOutputRequest,
    current_user: User = Depends(get_current_user)
):
    """Create a new output"""
    logger.info(f"Creating output '{request.title}' for user {current_user.email}")

    # ❌ PROBLEM: Creates new DatabaseService instance
    # This ignores test fixtures and uses production DATABASE_URL
    db_service = DatabaseService()

    try:
        # ... rest of implementation
```

**Issues:**
1. `DatabaseService()` creates its own database connection pool
2. Reads `DATABASE_URL` from environment (production config)
3. Test fixtures cannot override this connection
4. Tests fail because `localhost:5432` doesn't exist in test environment
5. Cannot mock or inject test database

---

## Why This Happens

### Architecture Mismatch

**Authentication Endpoints (Working):**
```python
# backend/app/api/auth.py
@router.post("/login")
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db)  # ✅ Injected, can be overridden
):
    # Uses injected db session
    result = await db.execute(select(User).where(...))
```

**Outputs Endpoints (Broken):**
```python
# backend/app/api/outputs.py
@router.post("")
async def create_output(
    request: CreateOutputRequest,
    current_user: User = Depends(get_current_user)
    # ❌ No db parameter - creates own connection
):
    db_service = DatabaseService()  # ❌ Not injectable
```

### Test Fixture Override Flow

```
┌─────────────────────────────────────────────────────┐
│ Test Fixture (conftest.py)                         │
│ - Creates test database at postgres-test:5432      │
│ - Overrides get_db() dependency                    │
│ - app.dependency_overrides[get_db] = test_session  │
└─────────────────────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────┐
│ Auth Endpoint (WORKING)                             │
│ - Receives db via Depends(get_db)                  │
│ - Gets test database session                       │
│ - ✅ Tests pass                                     │
└─────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────┐
│ Outputs Endpoint (BROKEN)                           │
│ - Creates DatabaseService() directly               │
│ - Reads DATABASE_URL from environment              │
│ - Tries to connect to localhost:5432              │
│ - ❌ Connection fails → 500 error                  │
└─────────────────────────────────────────────────────┘
```

---

## Recommended Solution

### Option A: Use FastAPI Dependency Injection (RECOMMENDED)

**Pros:**
- ✅ Follows FastAPI best practices
- ✅ Fully testable with fixture overrides
- ✅ Consistent with auth endpoints
- ✅ No changes to DatabaseService needed
- ✅ Production code benefits from DI

**Cons:**
- Requires refactoring all outputs endpoint functions
- Medium effort (4-6 hours for all endpoints)

**Implementation:**

#### 1. Create DatabaseService Dependency

```python
# backend/app/dependencies.py (or new file)

from app.services.database import DatabaseService

async def get_database_service() -> DatabaseService:
    """
    Dependency that provides DatabaseService instance.
    Can be overridden in tests.
    """
    return DatabaseService()
```

#### 2. Update Outputs Endpoints

```python
# backend/app/api/outputs.py

from app.dependencies import get_database_service

@router.post("", response_model=OutputResponse, status_code=201)
async def create_output(
    request: CreateOutputRequest,
    current_user: User = Depends(get_current_user),
    db_service: DatabaseService = Depends(get_database_service)  # ✅ Injected
):
    """Create a new output"""
    logger.info(f"Creating output '{request.title}' for user {current_user.email}")

    try:
        output_id = await db_service.create_output(
            user_id=str(current_user.user_id),
            output_type=request.output_type,
            # ... rest of fields
        )
        # ... rest of implementation
```

#### 3. Update Test Fixtures

```python
# backend/tests/conftest.py

@pytest.fixture
def client(mock_engine, db_session):
    """Create test client with mocked dependencies"""
    from app.api.auth import get_db as auth_get_db
    from app.dependencies import get_database_service
    from app.services.database import DatabaseService

    # Override auth database
    async def override_auth_get_db():
        yield db_session

    # Override DatabaseService to use test database
    async def override_database_service():
        # Create DatabaseService that uses test DATABASE_URL
        # Or mock it entirely for unit tests
        return MockDatabaseService(db_session)

    app.dependency_overrides[auth_get_db] = override_auth_get_db
    app.dependency_overrides[get_db] = override_auth_get_db
    app.dependency_overrides[get_database_service] = override_database_service

    app.router.lifespan_context = mock_lifespan

    with TestClient(app) as client:
        yield client

    app.dependency_overrides.clear()
```

#### 4. Create Mock DatabaseService (Optional)

For true unit tests, mock the entire DatabaseService:

```python
# backend/tests/conftest.py

class MockDatabaseService:
    """Mock DatabaseService for testing"""

    def __init__(self, session):
        self.session = session
        self.outputs = []

    async def create_output(self, **kwargs):
        """Mock create_output that uses test session"""
        output_id = str(uuid4())
        self.outputs.append({"id": output_id, **kwargs})
        return output_id

    async def get_output(self, output_id: str):
        """Mock get_output"""
        return next((o for o in self.outputs if o["id"] == output_id), None)

    # ... implement other methods as needed
```

---

### Option B: Environment Variable Override (Quick Fix)

**Pros:**
- ✅ Minimal code changes
- ✅ Quick to implement (1-2 hours)

**Cons:**
- ❌ Not true dependency injection
- ❌ Less testable
- ❌ Tight coupling to environment
- ❌ Not recommended for production code

**Implementation:**

```python
# backend/tests/conftest.py

import os

# Set before importing app modules
os.environ["DATABASE_URL"] = TEST_DATABASE_URL

from app.main import app
# ... rest of fixtures
```

**Not recommended** - this is a workaround, not a proper solution.

---

### Option C: Hybrid Approach

Use dependency injection for new code, but allow DatabaseService to accept an optional session:

```python
# backend/app/services/database.py

class DatabaseService:
    def __init__(self, session: Optional[AsyncSession] = None):
        if session:
            self.session = session
            self._owns_session = False
        else:
            # Create own connection pool
            self._engine = create_async_engine(DATABASE_URL)
            self._owns_session = True
```

```python
# backend/app/api/outputs.py

@router.post("")
async def create_output(
    request: CreateOutputRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    db_service = DatabaseService(session=db)  # ✅ Uses injected session
```

---

## Comparison Matrix

| Solution | Testability | Effort | Production Quality | Recommendation |
|----------|-------------|--------|-------------------|----------------|
| **Option A: FastAPI DI** | ⭐⭐⭐⭐⭐ | Medium (4-6h) | ⭐⭐⭐⭐⭐ | ✅ **BEST** |
| **Option B: Env Override** | ⭐⭐ | Low (1-2h) | ⭐⭐ | ❌ Workaround |
| **Option C: Hybrid** | ⭐⭐⭐⭐ | Medium (3-5h) | ⭐⭐⭐⭐ | Alternative |

---

## Implementation Plan (Option A - Recommended)

### Phase 1: Create Dependency (30 min)
1. Add `get_database_service()` to `backend/app/dependencies.py`
2. Test dependency in isolation

### Phase 2: Update Endpoints (2-3 hours)
Update all outputs endpoints in `backend/app/api/outputs.py`:
- `create_output()` - POST /api/outputs
- `get_output()` - GET /api/outputs/{output_id}
- `update_output()` - PUT /api/outputs/{output_id}
- `delete_output()` - DELETE /api/outputs/{output_id}
- `list_outputs()` - GET /api/outputs
- `get_outputs_by_funder()` - GET /api/outputs/by-funder/{funder_id}
- `get_outputs_by_style()` - GET /api/outputs/by-style/{style_id}
- Any other endpoints using DatabaseService

**For each endpoint:**
1. Add `db_service: DatabaseService = Depends(get_database_service)` parameter
2. Remove `db_service = DatabaseService()` line
3. Test endpoint still works in development

### Phase 3: Update Test Fixtures (1-2 hours)
1. Create `MockDatabaseService` class
2. Update `client` fixture to override `get_database_service`
3. Verify override works with simple test

### Phase 4: Verify Tests Pass (1-2 hours)
1. Run single test: `test_create_output_authenticated_user`
2. Fix any issues
3. Run all create tests: `pytest -k test_create`
4. Run all outputs API tests: `pytest backend/tests/test_outputs_api.py`
5. Verify 40/40 tests passing

### Phase 5: Run E2E Tests (1 hour)
1. Run E2E tests: `pytest backend/tests/test_outputs_e2e.py`
2. Fix any E2E-specific issues
3. Verify 15/15 E2E tests passing

---

## Success Criteria

- ✅ All outputs endpoints accept `DatabaseService` via dependency injection
- ✅ Test fixtures can override database service
- ✅ 40/40 outputs API tests passing
- ✅ 15/15 E2E tests passing (after lifespan fix)
- ✅ No hardcoded `DatabaseService()` instantiation in endpoints
- ✅ Production code maintains same functionality
- ✅ Can achieve 150/150 tests passing for Phase 4

---

## Estimated Effort

**Total:** 6-9 hours

- Phase 1 (Dependency): 30 minutes
- Phase 2 (Endpoints): 2-3 hours
- Phase 3 (Test Fixtures): 1-2 hours
- Phase 4 (API Tests): 1-2 hours
- Phase 5 (E2E Tests): 1 hour
- Buffer for issues: 1 hour

---

## Impact on Downstream Tasks

### ✅ Unblocks:
- Task `4efe00cf` - "Verify E2E workflow tests pass"
- Task `3dd07b54` - "Run full Phase 4 test suite with coverage report"

### 🎯 Enables:
- 40+ outputs API tests to pass
- 15 E2E tests to reach outputs operations
- Achievement of 150/150 Phase 4 test target
- Coverage targets for outputs API (currently 23% → target 90%)

---

## Files to Modify

### Application Code:
- `backend/app/dependencies.py` - Add `get_database_service()` dependency
- `backend/app/api/outputs.py` - Update all endpoint functions (8-10 endpoints)

### Test Code:
- `backend/tests/conftest.py` - Add `MockDatabaseService` and override
- `backend/tests/test_outputs_api.py` - May need minor adjustments

---

## Related Issues

- ✅ **FIXED:** Authentication fixture isolation (Task e7ab5d90)
- 🔴 **THIS ISSUE:** DatabaseService dependency injection
- ⏳ **WAITING:** E2E tests (blocked by this + lifespan fix)
- ⏳ **WAITING:** Phase 4 final verification (blocked by this)

---

## References

- FastAPI Dependency Injection: https://fastapi.tiangolo.com/tutorial/dependencies/
- Testing with Dependencies: https://fastapi.tiangolo.com/advanced/testing-dependencies/
- Authentication fixture fix: `/docs/test-auth-fixture-isolation-issue.md`
- Test verification report: `/TEST_AUTH_FIX_VERIFICATION.md`

---

## Notes

**Production Impact:** None - this only affects test execution. Production code will work the same way after the fix, just with better architecture.

**Testing Strategy:** After implementing DI, we can choose between:
1. **Integration tests:** Override with real DatabaseService using test database
2. **Unit tests:** Override with MockDatabaseService for faster execution

Recommend starting with integration tests (option 1) to verify full stack works, then add unit tests for edge cases.
