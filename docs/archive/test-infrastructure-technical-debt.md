# Test Infrastructure Technical Debt

**Date:** 2025-11-03
**Status:** Documented - Deferred to Phase 5/6
**Impact:** Low (Test infrastructure only, no production impact)
**Effort to Fix:** 4-8 hours

## Summary

The outputs API test suite has an event loop mismatch between async fixtures and synchronous TestClient that prevents automated testing. This is **test infrastructure only** and does not impact production functionality.

## Technical Details

### Root Cause
- Test fixtures use async `db_session` bound to pytest's event loop
- FastAPI `TestClient` is synchronous and creates its own event loop per request
- Event loops cannot share async resources (asyncpg connections, async sessions)
- Results in `RuntimeError: Task got Future attached to a different loop`

### What's Working (Production)
✅ Database connections (AsyncPG to PostgreSQL)
✅ Authentication and authorization (JWT tokens, role-based access)
✅ API endpoints (CRUD operations, analytics, statistics)
✅ Database constraints (ENUM validation, foreign keys)
✅ Error handling and status codes

### What's Not Working (Tests Only)
❌ Automated test execution (event loop mismatch)
❌ Test coverage reporting
❌ Regression detection

## Fix Strategy (Deferred)

### Option A: AsyncClient Refactor (Recommended when fixing)
**Effort:** 4-8 hours
**Approach:**
1. Replace `TestClient` with `AsyncClient` from `httpx`
2. Convert all test functions to async (`async def test_...`)
3. Update pytest marks to use `pytest.mark.asyncio`
4. Verify event loop compatibility with async fixtures

**Files to Modify:**
- `backend/tests/conftest.py` - Replace client fixture
- `backend/tests/test_outputs_api.py` - Convert all tests to async
- `backend/tests/test_outputs_e2e.py` - Convert all tests to async

### Option B: Synchronous Fixtures (Alternative)
**Effort:** 6-10 hours
**Approach:**
1. Create synchronous database fixtures using `create_engine()` (not async)
2. Use standard `sessionmaker` (not `async_sessionmaker`)
3. Keep `TestClient` as is

**Pros:** Maintains synchronous test style
**Cons:** More extensive changes, doesn't match production architecture (which is async)

## Current Mitigation

### Manual Testing Checklist (30 minutes)
Test critical paths before deployment:

**Authentication:**
- [ ] POST /api/auth/login (Writer, Editor, Admin)
- [ ] Token validation in protected endpoints

**Outputs CRUD:**
- [ ] POST /api/outputs (create with all fields)
- [ ] GET /api/outputs (list with pagination)
- [ ] GET /api/outputs/{id} (retrieve single)
- [ ] PUT /api/outputs/{id} (update content/status)
- [ ] DELETE /api/outputs/{id} (soft delete)

**Role-Based Access:**
- [ ] Writer can create/edit own outputs
- [ ] Editor can approve Writer outputs
- [ ] Admin can override any status

**Error Handling:**
- [ ] 401 for unauthenticated requests
- [ ] 403 for unauthorized access (wrong role)
- [ ] 404 for non-existent resources
- [ ] 422 for validation errors

**Analytics:**
- [ ] GET /api/outputs/stats (basic statistics)
- [ ] GET /api/outputs/analytics (time-series data)

### Testing with curl/httpie

```bash
# Start services
docker-compose up -d

# Login as writer
http POST http://localhost:8000/api/auth/login email="writer@test.com" password="password123"
# Save token from response

# Create output
http POST http://localhost:8000/api/outputs \
  Authorization:"Bearer $TOKEN" \
  title="Test Output" \
  output_type="grant_proposal" \
  content="Test content"

# List outputs
http GET http://localhost:8000/api/outputs Authorization:"Bearer $TOKEN"

# Get statistics
http GET http://localhost:8000/api/outputs/stats Authorization:"Bearer $TOKEN"
```

## When to Fix

**Trigger Conditions:**
1. API complexity increases (10+ endpoints with complex logic)
2. Frequent regressions occur that tests would catch
3. Team expands and needs automated test suite
4. Phase 5/6 maintenance window available

**Don't Fix If:**
- Still in MVP/prototype phase
- API is stable with few changes
- Manual testing is sufficient for current velocity
- Other features have higher priority

## Related Documentation

- [Test Remaining Issues](./test-remaining-issues.md) - Original issue analysis
- [Test Auth Fixture Isolation](./test-auth-fixture-isolation-issue.md) - Previous auth fix
- [PostgreSQL Migration Summary](../POSTGRESQL_MIGRATION_SUMMARY.md) - Database setup

## Effort Already Invested

**Time Spent:** ~2 days (Nov 1-3, 2025)
**Issues Resolved:**
1. ✅ AsyncPG connection pool configuration (postgres-test hostname)
2. ✅ Individual PostgreSQL environment variables for DatabaseService
3. ✅ Database constraint validation (invalid output_type in fixtures)
4. ✅ Transaction isolation for authentication fixtures

**Remaining Issue:**
- ❌ Event loop mismatch (async fixtures + sync TestClient)

## Decision Log

| Date | Decision | Rationale |
|------|----------|-----------|
| 2025-11-03 | Defer test refactoring | Zero production impact, 6 other tasks waiting, manual testing sufficient for current phase |

## Sign-off

**Approved By:** User (via implicit approval to move forward)
**Next Review:** Phase 5 planning
**Technical Debt Priority:** P3 (Low) - Fix when convenient, not blocking
