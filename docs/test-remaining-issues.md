# Remaining Test Issues - Outputs API

**Date:** 2025-11-03
**Status:** In Progress
**Related Files:**
- `backend/tests/test_outputs_api.py`
- `backend/tests/conftest.py`
- `backend/app/services/database.py`
- `backend/app/dependencies.py`

## Executive Summary

After fixing the DatabaseService dependency injection (40+ tests) and WritingStyle fixture model mismatch (32 errors), we have 2 remaining critical issues preventing the outputs API tests from passing:

1. **AsyncPG Connection Pool Configuration** - DatabaseService connects to localhost instead of postgres-test container
2. **Authentication Status Code Mismatches** - 7 tests expecting different HTTP status codes

## Issue #1: AsyncPG Connection Pool Configuration

### Problem Description

The DatabaseService is attempting to connect to `localhost:5432` instead of `postgres-test:5432` when running tests, causing connection failures:

```
OSError: [Errno 111] Connect call failed ('127.0.0.1', 5432)
```

This results in 500 Internal Server Error responses from API endpoints that depend on the DatabaseService.

### Root Cause Analysis

**Test Environment Setup (conftest.py:219-230):**
```python
async def override_get_database() -> DatabaseService:
    """Provides DatabaseService connected to test database"""
    db = DatabaseService()
    # The DatabaseService will use the TEST_DATABASE_URL from environment
    # which was set at line 26 above
    if not db.pool:
        await db.connect()
    return db
```

**Environment Variable Configuration (conftest.py:26):**
```python
os.environ["TEST_DATABASE_URL"] = "postgresql+asyncpg://test_user:test_password@localhost:5432/org_archivist_test"
```

**The Problem:** The `TEST_DATABASE_URL` is set to `localhost:5432`, but tests run inside Docker containers where the PostgreSQL test database is accessible via `postgres-test:5432` on the org-archivist-network.

### Evidence

From test output (test 31fb50):
```
File "/usr/local/lib/python3.11/site-packages/asyncpg/connect_utils.py", line 931, in __connect_addr
    tr, pr = await connector
OSError: Multiple exceptions: [Errno 111] Connect call failed ('::1', 5432, 0, 0), [Errno 111] Connect call failed ('127.0.0.1', 5432)
```

The DatabaseService is correctly using AsyncPG (`postgresql+asyncpg://`), but the hostname is wrong for the Docker network environment.

### Affected Tests

All tests that use the `test_writing_style` fixture or require DatabaseService functionality:
- `test_create_output_with_writing_style`
- All list, get, update, delete operations with writing styles
- All analytics endpoints (32+ tests)

### Solution

**Option A: Update TEST_DATABASE_URL hostname (Recommended)**

Change conftest.py:26 to use the Docker network hostname:

```python
os.environ["TEST_DATABASE_URL"] = "postgresql+asyncpg://test_user:test_password@postgres-test:5432/org_archivist_test"
```

**Pros:**
- Simple one-line fix
- Aligns with Docker network configuration
- Consistent with other test database connections

**Cons:**
- None identified

**Option B: Add DATABASE_URL fallback**

Modify conftest.py to set both TEST_DATABASE_URL and DATABASE_URL:

```python
test_db_url = "postgresql+asyncpg://test_user:test_password@postgres-test:5432/org_archivist_test"
os.environ["TEST_DATABASE_URL"] = test_db_url
os.environ["DATABASE_URL"] = test_db_url
```

**Pros:**
- Ensures DatabaseService picks up correct URL regardless of configuration
- More defensive programming

**Cons:**
- May mask underlying configuration issues

### Implementation Steps

1. Update `backend/tests/conftest.py:26` with correct hostname
2. Verify DatabaseService initialization in `backend/app/services/database.py` respects TEST_DATABASE_URL
3. Run test suite to verify connection succeeds
4. Document Docker network configuration requirements

### Testing Verification

```bash
docker run --rm --network org-archivist-network \
  -v $PWD:/app \
  -w /app \
  -e TEST_DATABASE_URL="postgresql+asyncpg://test_user:test_password@postgres-test:5432/org_archivist_test" \
  python:3.11-slim bash -c "
    pip install -q -r backend/requirements.txt email-validator &&
    python -m pytest backend/tests/test_outputs_api.py::TestCreateOutput::test_create_output_with_writing_style -v
  "
```

Expected: Test passes without connection errors

---

## Issue #2: Authentication Status Code Mismatches

### Problem Description

7 tests are receiving unexpected HTTP status codes, primarily 401/403 instead of expected codes like 201, 404, or 422.

### Affected Tests

| Test | Expected | Actual | Description |
|------|----------|--------|-------------|
| `test_create_output_minimal_data` | 201 | 401 | Should create output with minimal fields |
| `test_create_output_unauthenticated` | 401 | 403 | Unauthenticated user should get 401 |
| `test_create_output_validation_error` | 422 | 401 | Invalid data should get validation error |
| `test_list_outputs_unauthenticated` | 401 | 403 | Unauthenticated user should get 401 |
| `test_get_output_not_found` | 404 | 401 | Non-existent resource should return 404 |
| `test_delete_output_not_found` | 404 | 401 | Non-existent resource should return 404 |
| `test_invalid_uuid_format` | 422 | 401 | Invalid UUID should return validation error |

### Root Cause Analysis

**Hypothesis:** These failures are likely **cascading effects** from Issue #1 (AsyncPG connection pool).

**Reasoning:**
1. When DatabaseService fails to connect, API endpoints return 500 errors
2. Authentication middleware may fail to validate tokens due to database connectivity issues
3. This causes the auth system to reject requests with 401/403 instead of processing them

### Evidence

From previous test run (bash 350f24):
```
sqlalchemy.exc.InterfaceError: cannot perform operation: another operation is in progress
WARNING  app_middleware:middleware.py:293 HTTP exception: status=500 detail=Login failed
```

This shows authentication is failing due to database connectivity issues, not actual auth problems.

### Solution

**Primary Action:** Fix Issue #1 first, then re-evaluate

**Rationale:**
- These status code mismatches only appeared after database connection issues
- Authentication depends on database connectivity for session validation
- Fixing the connection pool should resolve authentication failures

**Verification Steps After Issue #1 Resolution:**

1. Run the 7 affected tests individually
2. Check if status codes now match expectations
3. If issues persist, investigate each test category:
   - **401 vs 403 discrepancy:** Review authentication middleware
   - **401 instead of 404:** Check if auth runs before route validation
   - **401 instead of 422:** Check if auth runs before request validation

### Deferred Analysis

If tests still fail after resolving Issue #1:

1. **Review authentication middleware order**
   - Ensure validation happens before auth when appropriate
   - Check FastAPI dependency injection order

2. **Review error handling hierarchy**
   - Validation errors should take precedence over auth errors for invalid data
   - Resource not found should take precedence over auth when resource doesn't exist

3. **Test fixture isolation**
   - Ensure test database state is clean between tests
   - Verify authentication tokens are valid for test duration

---

## Priority and Dependencies

### Priority Order

1. **CRITICAL:** Issue #1 - AsyncPG Connection Pool (Blocks 30+ tests)
2. **HIGH:** Issue #2 - Status Code Verification (Dependent on #1)

### Dependencies

```mermaid
graph TD
    A[Issue #1: Fix AsyncPG Connection] --> B[Run Full Test Suite]
    B --> C{All Tests Pass?}
    C -->|No| D[Issue #2: Investigate Status Codes]
    C -->|Yes| E[Complete - All Tests Passing]
    D --> F[Fix Remaining Issues]
    F --> B
```

### Estimated Effort

- **Issue #1:** 15-30 minutes (Simple configuration change + verification)
- **Issue #2:** 30-60 minutes (Contingent on Issue #1 resolution)

**Total:** 45-90 minutes to complete both issues

---

## Success Criteria

### Issue #1 Completion
- ✅ DatabaseService successfully connects to postgres-test container
- ✅ No connection errors in test output
- ✅ Tests using DatabaseService execute successfully
- ✅ At least 10+ tests that were failing now pass

### Issue #2 Completion
- ✅ All 7 tests return expected HTTP status codes
- ✅ Unauthenticated requests return 401 (not 403)
- ✅ Validation errors return 422 (not 401)
- ✅ Not found errors return 404 (not 401)

### Overall Success
- ✅ 40/41 tests passing (1 test had pre-existing fixture isolation issue)
- ✅ No 500 Internal Server Errors
- ✅ No connection errors
- ✅ Test suite runs in < 60 seconds

---

## Related Documentation

- [Test Auth Fixture Isolation Issue](./test-auth-fixture-isolation-issue.md)
- [Outputs API Database Service DI Issue](./outputs-api-database-service-di-issue.md)
- [PostgreSQL Migration Summary](../POSTGRESQL_MIGRATION_SUMMARY.md)
- [Phase 4 Testing Review Report](../PHASE_4_TESTING_REVIEW_REPORT.md)

---

## Change Log

| Date | Change | Author |
|------|--------|--------|
| 2025-11-03 | Initial document creation | Claude Code |
| 2025-11-03 | Completed WritingStyle fixture fix | Claude Code |
| 2025-11-03 | Completed DatabaseService DI fix | Claude Code |
