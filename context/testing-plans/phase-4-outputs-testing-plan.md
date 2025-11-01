# Phase 4: Outputs and Success Tracking - Testing Plan

**Date**: 2025-11-01
**Phase**: Phase 4 - Past Outputs Dashboard
**Status**: 📋 PLANNING COMPLETE
**Coverage Target**: >80%
**Estimated Effort**: 10 hours

---

## Executive Summary

This document outlines the comprehensive testing strategy for Phase 4 outputs and success tracking functionality. The plan covers 5 test categories with 105-130 individual tests targeting >80% code coverage across Pydantic models, service layers, database integration, API endpoints, and end-to-end workflows.

---

## Testing Architecture

### Test Pyramid Structure

```
        ┌──────────────────┐
        │  E2E Tests (10)  │  ← Full workflows
        └──────────────────┘
       ┌────────────────────┐
       │ API Tests (35-40)  │  ← Endpoint integration
       └────────────────────┘
      ┌──────────────────────┐
      │ DB Tests (25-30)     │  ← Database operations
      └──────────────────────┘
     ┌────────────────────────┐
     │ Service Tests (20-25)  │  ← Business logic
     └────────────────────────┘
    ┌──────────────────────────┐
    │ Model Tests (15-20)      │  ← Data validation
    └──────────────────────────┘
```

**Total**: 105-130 tests across 5 test files

---

## Test Categories

### 1. Pydantic Model Unit Tests
**File**: `backend/tests/test_output_models.py`
**Archon Task ID**: c9a9bd0d-8a6a-4f6a-bbbb-d87852c71877
**Estimated Lines**: ~200
**Estimated Tests**: 15-20
**Dependencies**: None (pure unit tests)

#### Test Coverage

**Enum Validation** (4 tests):
1. `test_output_type_enum_values` - Valid OutputType values
2. `test_output_type_enum_invalid` - Invalid OutputType raises error
3. `test_output_status_enum_values` - Valid OutputStatus values
4. `test_output_status_enum_invalid` - Invalid OutputStatus raises error

**Field Validation** (8 tests):
5. `test_title_min_length` - Title must be at least 1 character
6. `test_title_max_length` - Title must be ≤500 characters
7. `test_content_required` - Content field is required
8. `test_word_count_positive` - Word count must be ≥0
9. `test_requested_amount_positive` - Requested amount must be ≥0
10. `test_awarded_amount_positive` - Awarded amount must be ≥0
11. `test_writing_style_id_uuid_format` - Writing style ID must be valid UUID string
12. `test_funder_name_max_length` - Funder name ≤255 characters

**Date Validation** (3 tests):
13. `test_decision_date_after_submission_valid` - Decision date >= submission date is valid
14. `test_decision_date_before_submission_invalid` - Decision date < submission date raises error
15. `test_decision_date_same_as_submission_valid` - Same date is valid

**Amount Validation** (3 tests):
16. `test_awarded_less_than_requested_valid` - Awarded ≤ requested is valid
17. `test_awarded_exceeds_requested_invalid` - Awarded > requested raises error
18. `test_awarded_equals_requested_valid` - Awarded = requested is valid

**Request/Response Models** (2-3 tests):
19. `test_output_create_request_valid` - Valid creation request
20. `test_output_update_request_partial` - Partial updates allowed
21. `test_output_response_from_attributes` - Response model from ORM

**Pattern**: Follow `test_writing_styles.py` TestSampleValidation class
**Fixtures**: Sample output data, valid/invalid inputs

---

### 2. Success Tracking Service Tests
**File**: `backend/tests/test_success_tracking.py`
**Archon Task ID**: 3e0cce53-524c-4c2f-8092-5c441167a187
**Estimated Lines**: ~400
**Estimated Tests**: 20-25
**Dependencies**: Mock DatabaseService

#### Test Coverage

**Status Transition Validation** (8 tests):
1. `test_valid_transition_draft_to_submitted` - draft → submitted allowed
2. `test_valid_transition_submitted_to_pending` - submitted → pending allowed
3. `test_valid_transition_pending_to_awarded` - pending → awarded allowed
4. `test_valid_transition_pending_to_not_awarded` - pending → not_awarded allowed
5. `test_invalid_transition_draft_to_awarded` - draft → awarded blocked (raises StatusTransitionError)
6. `test_invalid_transition_draft_to_pending` - draft → pending blocked
7. `test_valid_transition_same_status` - Same status allowed (no-op)
8. `test_admin_override_allows_any_transition` - Admin can override restrictions

**Outcome Data Validation** (4 tests):
9. `test_validate_outcome_submitted_requires_submission_date` - Warning if missing
10. `test_validate_outcome_awarded_requires_decision_data` - Warning for incomplete data
11. `test_validate_outcome_awarded_amount_consistency` - Check awarded ≤ requested
12. `test_validate_outcome_complete_data_no_warnings` - No warnings with complete data

**Analytics by Style** (3 tests):
13. `test_calculate_success_rate_by_style` - Correct calculations
14. `test_calculate_success_rate_by_style_with_date_filter` - Date range filtering
15. `test_calculate_success_rate_by_style_no_data` - Handle empty results

**Analytics by Funder** (3 tests):
16. `test_calculate_success_rate_by_funder` - Correct calculations
17. `test_calculate_success_rate_by_funder_partial_match` - ILIKE matching
18. `test_calculate_success_rate_by_funder_no_matches` - Handle no results

**Analytics by Year** (2 tests):
19. `test_calculate_success_rate_by_year` - Year-based aggregation
20. `test_calculate_success_rate_by_year_no_data` - Empty year handling

**Summary Metrics** (2 tests):
21. `test_get_success_metrics_summary` - Complete summary with top styles/funders
22. `test_get_success_metrics_summary_role_filtering` - Writers see only their data

**Funder Performance** (2 tests):
23. `test_get_funder_performance_rankings` - Ordered by success rate
24. `test_get_funder_performance_limit` - Limit parameter works

**Pattern**: Mock database service with AsyncMock, async test functions
**Fixtures**: Mock database returns, sample output data

---

### 3. Database Service Integration Tests
**File**: `backend/tests/test_output_database.py`
**Archon Task ID**: f9d45af1-eafc-49e2-882d-4b3d34490289
**Estimated Lines**: ~600
**Estimated Tests**: 25-30
**Dependencies**: Test database (SQLite in-memory)

#### Test Coverage

**CRUD Operations** (8 tests):
1. `test_create_output_success` - Create output with all fields
2. `test_create_output_minimal` - Create with required fields only
3. `test_get_output_by_id_success` - Retrieve existing output
4. `test_get_output_not_found` - Returns None for non-existent ID
5. `test_update_output_single_field` - Partial update works
6. `test_update_output_multiple_fields` - Update multiple fields
7. `test_delete_output_success` - Delete returns True
8. `test_delete_output_not_found` - Delete non-existent returns False

**List and Filtering** (10 tests):
9. `test_list_outputs_all` - List all outputs
10. `test_list_outputs_filter_by_type_single` - Filter by one output_type
11. `test_list_outputs_filter_by_type_multiple` - Filter by multiple types
12. `test_list_outputs_filter_by_status_single` - Filter by one status
13. `test_list_outputs_filter_by_status_multiple` - Filter by multiple statuses
14. `test_list_outputs_filter_by_created_by` - Filter by user
15. `test_list_outputs_filter_by_writing_style` - Filter by style ID
16. `test_list_outputs_filter_by_funder_name` - Partial funder match
17. `test_list_outputs_filter_by_date_range` - Date range filtering
18. `test_list_outputs_combined_filters` - Multiple filters together

**Pagination** (3 tests):
19. `test_list_outputs_pagination_first_page` - skip=0, limit=10
20. `test_list_outputs_pagination_second_page` - skip=10, limit=10
21. `test_list_outputs_pagination_custom_limit` - Custom page size

**Search** (3 tests):
22. `test_search_outputs_by_title` - Title search with ILIKE
23. `test_search_outputs_by_content` - Content search
24. `test_search_outputs_by_funder` - Funder name search
25. `test_search_outputs_no_results` - Empty search results

**Statistics** (3 tests):
26. `test_get_outputs_stats_all` - Stats for all outputs
27. `test_get_outputs_stats_filtered_by_type` - Stats with type filter
28. `test_get_outputs_stats_filtered_by_user` - Stats for specific user
29. `test_get_outputs_stats_success_rate_calculation` - Verify success rate math

**Edge Cases** (1-2 tests):
30. `test_create_output_with_metadata_json` - JSON metadata serialization

**Pattern**: Follow `test_auth.py` database fixture patterns
**Fixtures**: `db_engine`, `db_session`, sample outputs

---

### 4. API Endpoints Integration Tests
**File**: `backend/tests/test_outputs_api.py`
**Archon Task ID**: a3085da5-0e55-4a52-9ba9-b4b3e0594661
**Estimated Lines**: ~800
**Estimated Tests**: 35-40
**Dependencies**: Test database, FastAPI TestClient, mock auth

#### Test Coverage

**POST /api/outputs - Create Output** (5 tests):
1. `test_create_output_authenticated_user` - Successful creation
2. `test_create_output_with_conversation` - Link to conversation
3. `test_create_output_minimal_data` - Required fields only
4. `test_create_output_unauthenticated` - 401 without token
5. `test_create_output_validation_error` - 422 for invalid data

**GET /api/outputs - List Outputs** (8 tests):
6. `test_list_outputs_as_writer` - Writers see only own outputs
7. `test_list_outputs_as_editor` - Editors see all outputs
8. `test_list_outputs_as_admin` - Admins see all outputs
9. `test_list_outputs_with_type_filter` - Filter by output_type
10. `test_list_outputs_with_status_filter` - Filter by status
11. `test_list_outputs_with_search_query` - Search functionality
12. `test_list_outputs_pagination` - Skip and limit work
13. `test_list_outputs_unauthenticated` - 401 without token

**GET /api/outputs/stats - Statistics** (4 tests):
14. `test_get_stats_as_writer` - Stats for own outputs only
15. `test_get_stats_as_editor` - Stats for all outputs
16. `test_get_stats_with_type_filter` - Filtered statistics
17. `test_get_stats_success_rate_calculation` - Verify calculations

**GET /api/outputs/{id} - Get Single Output** (5 tests):
18. `test_get_output_as_owner` - Owner can view
19. `test_get_output_as_editor` - Editor can view any
20. `test_get_output_as_admin` - Admin can view any
21. `test_get_output_as_other_writer` - 403 for other writer's output
22. `test_get_output_not_found` - 404 for non-existent ID

**PUT /api/outputs/{id} - Update Output** (7 tests):
23. `test_update_output_as_owner` - Owner can update
24. `test_update_output_as_editor` - Editor can update any
25. `test_update_output_as_admin` - Admin can update any
26. `test_update_output_as_other_writer` - 403 for other writer's output
27. `test_update_output_status_transition_valid` - Valid transition allowed
28. `test_update_output_status_transition_invalid` - 422 for invalid transition
29. `test_update_output_admin_override` - Admin can override status rules

**DELETE /api/outputs/{id} - Delete Output** (5 tests):
30. `test_delete_output_as_owner` - Owner can delete own
31. `test_delete_output_as_admin` - Admin can delete any
32. `test_delete_output_as_editor` - 403 editor cannot delete others'
33. `test_delete_output_as_other_writer` - 403 for other writer's output
34. `test_delete_output_not_found` - 404 for non-existent ID

**Analytics Endpoints** (5 tests):
35. `test_get_analytics_by_style` - GET /api/outputs/analytics/style/{id}
36. `test_get_analytics_by_funder` - GET /api/outputs/analytics/funder/{name}
37. `test_get_analytics_by_year` - GET /api/outputs/analytics/year/{year}
38. `test_get_analytics_summary` - GET /api/outputs/analytics/summary
39. `test_get_analytics_funders` - GET /api/outputs/analytics/funders

**Error Handling** (1-2 tests):
40. `test_invalid_uuid_format` - 422 for malformed UUID

**Pattern**: Follow `test_auth.py` TestClient and auth patterns
**Fixtures**: `test_client`, `test_users`, `auth_headers`, test database

---

### 5. End-to-End Workflow Tests
**File**: `backend/tests/test_outputs_e2e.py`
**Archon Task ID**: b79a8a3c-1a5b-4e7a-9908-71cc4272efa3
**Estimated Lines**: ~400
**Estimated Tests**: 10-15
**Dependencies**: Full test database, TestClient

#### Test Coverage

**Complete Grant Lifecycle** (5 tests):
1. `test_complete_workflow_draft_to_awarded` - Full success path
   - Create output (draft)
   - Update to submitted (with submission_date)
   - Update to pending
   - Update to awarded (with decision_date, awarded_amount, success_notes)
   - Verify all data captured correctly

2. `test_complete_workflow_draft_to_not_awarded` - Rejection path
   - Create → submit → pending → not_awarded
   - Verify success_notes captured

3. `test_workflow_with_revisions` - Back-and-forth editing
   - submitted → draft (revisions needed)
   - draft → submitted (resubmit)
   - submitted → pending → awarded

4. `test_workflow_status_validation_enforcement` - Invalid transitions blocked
   - Attempt draft → awarded (should fail)
   - Attempt draft → pending (should fail)

5. `test_workflow_admin_override` - Admin can skip steps
   - Admin updates draft → awarded directly

**Success Tracking Integration** (3 tests):
6. `test_success_tracking_with_funder_info` - Capture complete funder data
   - Create output with funder_name, requested_amount
   - Update with decision_date, awarded_amount
   - Verify data consistency

7. `test_success_tracking_multiple_grants_statistics` - Stats calculation
   - Create 5 outputs (3 awarded, 2 not_awarded)
   - Verify success_rate = 60%
   - Verify total_awarded, avg_awarded calculations

8. `test_success_tracking_by_writing_style` - Style analytics
   - Create outputs with different writing_styles
   - Some awarded, some not
   - Verify style-based success rates

**Multi-User Scenarios** (3 tests):
9. `test_multi_user_data_isolation` - Writers see only own data
   - Writer A creates outputs
   - Writer B creates outputs
   - Verify each sees only their own in list

10. `test_multi_user_editor_visibility` - Editors see all
    - Create outputs as different writers
    - Editor can list and view all

11. `test_multi_user_permissions_enforcement` - Permission checks work
    - Writer A cannot edit Writer B's output
    - Editor can edit any
    - Admin can edit and delete any

**Data Consistency** (2 tests):
12. `test_output_conversation_linking` - Link to conversation works
    - Create conversation
    - Create output linked to conversation
    - Verify relationship

13. `test_output_writing_style_linking` - Link to writing style works
    - Create writing style
    - Create output with style
    - Verify relationship and analytics

**Analytics Aggregation** (2 tests):
14. `test_e2e_analytics_summary` - Dashboard summary endpoint
    - Create diverse output data
    - Verify summary includes top styles, funders, trends

15. `test_e2e_funder_performance` - Funder rankings
    - Create outputs for multiple funders
    - Verify rankings ordered by success rate

**Pattern**: Follow `test_writing_styles.py` TestEndToEndWorkflow class
**Fixtures**: Full database, multiple users with different roles

---

## Test Infrastructure

### Fixtures and Utilities

**Database Fixtures** (from test_auth.py):
```python
@pytest.fixture(scope="function")
async def db_engine():
    """SQLite in-memory test database"""
    # Create engine, create tables, yield, drop tables

@pytest.fixture(scope="function")
async def db_session(db_engine):
    """Test database session"""
    # Create session, yield, cleanup
```

**User Fixtures**:
```python
@pytest.fixture(scope="function")
async def test_users(db_session):
    """Create test users with different roles"""
    # Create admin, editor, writer users
    # Return dict with users and passwords
```

**Auth Fixtures**:
```python
@pytest.fixture
def auth_headers(test_users):
    """Generate auth headers for test users"""
    # Return dict of headers by role
```

**Output Fixtures**:
```python
@pytest.fixture
def sample_output_data():
    """Generate sample output data for tests"""
    return {
        "output_type": "grant_proposal",
        "title": "Test Grant Proposal",
        "content": "This is test content for the grant proposal...",
        "word_count": 500,
        "status": "draft",
    }

@pytest.fixture
async def test_outputs(db_session, test_users):
    """Create sample outputs for testing"""
    # Create 5-10 outputs with varying data
    # Different types, statuses, users, dates
```

**Mock Fixtures**:
```python
@pytest.fixture
def mock_database_service():
    """Mock DatabaseService for service layer tests"""
    mock = AsyncMock(spec=DatabaseService)
    # Configure return values
    return mock
```

### Test Utilities

**Helper Functions**:
```python
def generate_output_dict(**overrides):
    """Generate valid output data with overrides"""

def assert_output_response(response_data, expected_data):
    """Assert output response matches expected data"""

def create_output_via_api(client, data, auth_header):
    """Helper to create output through API"""
```

---

## Coverage Targets

### Overall Coverage Goal
**Target**: >80% coverage for Phase 4 modules

### Module-Specific Targets

| Module | Target Coverage | Priority |
|--------|----------------|----------|
| `backend/app/models/output.py` | 95%+ | High |
| `backend/app/services/success_tracking.py` | 85%+ | High |
| `backend/app/services/database.py` (outputs methods) | 85%+ | High |
| `backend/app/api/outputs.py` | 90%+ | Critical |

### Coverage Measurement
```bash
# Run with coverage
pytest backend/tests/test_output*.py -v --cov=backend/app/api/outputs --cov=backend/app/services/success_tracking --cov=backend/app/models/output --cov-report=html --cov-report=term

# View HTML report
open htmlcov/index.html
```

---

## Test Execution Plan

### Phase 1: Model Tests (Day 1)
**Duration**: 1 hour
**Task**: c9a9bd0d-8a6a-4f6a-bbbb-d87852c71877
**Steps**:
1. Create test_output_models.py
2. Implement 15-20 unit tests
3. Run tests, verify all pass
4. Commit: "test(models): add Pydantic output model unit tests"

### Phase 2: Service Tests (Day 1)
**Duration**: 2 hours
**Task**: 3e0cce53-524c-4c2f-8092-5c441167a187
**Steps**:
1. Create test_success_tracking.py
2. Set up mock database fixture
3. Implement 20-25 service tests
4. Run tests, verify all pass
5. Commit: "test(services): add success tracking service tests"

### Phase 3: Database Tests (Day 2)
**Duration**: 2 hours
**Task**: f9d45af1-eafc-49e2-882d-4b3d34490289
**Steps**:
1. Create test_output_database.py
2. Set up test database fixtures
3. Implement 25-30 integration tests
4. Run tests, verify all pass
5. Commit: "test(database): add outputs database service tests"

### Phase 4: API Tests (Day 2-3)
**Duration**: 3 hours
**Task**: a3085da5-0e55-4a52-9ba9-b4b3e0594661
**Steps**:
1. Create test_outputs_api.py
2. Set up TestClient and auth fixtures
3. Implement 35-40 API tests
4. Run tests, verify all pass
5. Commit: "test(api): add outputs API endpoint tests"

### Phase 5: E2E Tests (Day 3)
**Duration**: 2 hours
**Task**: b79a8a3c-1a5b-4e7a-9908-71cc4272efa3
**Steps**:
1. Create test_outputs_e2e.py
2. Implement 10-15 workflow tests
3. Run tests, verify all pass
4. Commit: "test(e2e): add outputs end-to-end workflow tests"

### Phase 6: Coverage & Documentation (Day 3)
**Duration**: 1 hour
**Task**: 2595a8d0-c540-4684-9bcd-fbfa4b52870f
**Steps**:
1. Run full test suite with coverage
2. Identify gaps, add tests if needed
3. Generate coverage report
4. Document results
5. Commit: "test(outputs): achieve >80% coverage for Phase 4"

---

## Quality Checkpoints

### Before Each Commit
- [ ] All tests pass locally
- [ ] No syntax errors
- [ ] Tests follow established patterns
- [ ] Proper async/await usage
- [ ] Descriptive test names
- [ ] Clear assertions

### Before Marking Task Complete
- [ ] Target number of tests implemented
- [ ] All tests passing
- [ ] Coverage target met for module
- [ ] Code follows project patterns
- [ ] Committed and pushed to GitHub
- [ ] Archon task updated to "review"

### Before Phase 4 Completion
- [ ] All 5 test files created
- [ ] 105+ tests implemented
- [ ] >80% overall coverage
- [ ] All tests passing in CI/CD
- [ ] Documentation updated
- [ ] Code reviewed

---

## Dependencies and Prerequisites

### Required Packages
```python
pytest==7.4.0
pytest-asyncio==0.21.1
pytest-cov==4.1.0
httpx==0.24.1  # For TestClient
aiosqlite==0.19.0  # For test database
```

### Required Modules
- ✅ `backend/app/models/output.py` - Pydantic models (Phase 4 complete)
- ✅ `backend/app/services/database.py` - Database service (Phase 4 complete)
- ✅ `backend/app/services/success_tracking.py` - Success tracking (Phase 4 complete)
- ✅ `backend/app/api/outputs.py` - API endpoints (Phase 4 complete)
- ✅ `backend/app/db/models.py` - SQLAlchemy Output model (Phase 4 complete)

### Database Setup
- Outputs table created (migration 6f2e9b3a4d5c)
- Foreign keys to conversations, writing_styles
- All indexes created

---

## Risk Mitigation

### Potential Issues

**Issue 1**: Test database setup complexity
- **Mitigation**: Use proven fixtures from test_auth.py
- **Fallback**: Mock database service for problematic tests

**Issue 2**: Async test timing issues
- **Mitigation**: Use proper pytest-asyncio markers
- **Fallback**: Add explicit await statements, increase timeouts

**Issue 3**: Permission logic complexity
- **Mitigation**: Create reusable auth fixtures
- **Fallback**: Test each role combination explicitly

**Issue 4**: Coverage gaps in edge cases
- **Mitigation**: Identify gaps with coverage report
- **Fallback**: Add targeted tests for uncovered lines

---

## Success Metrics

### Quantitative Metrics
- **Test Count**: 105-130 tests
- **Code Coverage**: >80% overall
  - Models: >95%
  - Services: >85%
  - API: >90%
- **Test Execution Time**: <30 seconds for full suite
- **Pass Rate**: 100% (all tests passing)

### Qualitative Metrics
- Tests follow established patterns
- Clear, descriptive test names
- Comprehensive error scenarios covered
- Realistic test data
- Easy to maintain and extend

---

## Maintenance Plan

### Test Updates Required When...

**Pydantic Models Change**:
- Update test_output_models.py validators
- Update fixtures with new fields

**New API Endpoints Added**:
- Add endpoint tests to test_outputs_api.py
- Update permission tests

**Database Schema Changes**:
- Update database fixtures
- Add migration-related tests

**Business Logic Changes**:
- Update service tests
- Update E2E workflow tests

---

## References

### Existing Test Files
- `backend/tests/test_auth.py` - Authentication test patterns
- `backend/tests/test_writing_styles.py` - Validation and service test patterns

### Documentation
- `/context/phase-4-plan.md` - Phase 4 requirements
- `/context/work-reports/2025-11-01-phase-4-core-implementation.md` - Implementation details
- `/context/architecture.md` - Testing architecture guidelines

### Archon Tasks
- Parent: bbccb7a9-420d-4148-88b6-2c316a75c3c3 (Test outputs and success tracking workflow)
- Sub-tasks: c9a9bd0d, 3e0cce53, f9d45af1, a3085da5, b79a8a3c, 2595a8d0

---

## Appendix: Test Template

### Basic Test Structure
```python
"""
Test module for [component]
"""
import pytest
from uuid import uuid4

# Test Class
class TestComponentName:
    """Test [component] functionality"""

    @pytest.mark.asyncio
    async def test_specific_scenario(self, fixture):
        """Test [specific scenario description]"""
        # Arrange
        test_data = {...}

        # Act
        result = await function_under_test(test_data)

        # Assert
        assert result.success is True
        assert result.field == expected_value
```

---

**Plan Created**: 2025-11-01
**Author**: Claude (Coding Agent)
**Status**: Ready for Implementation
**Next Step**: Begin Phase 1 - Model Tests
