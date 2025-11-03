# PostgreSQL ENUM Types Issue and Resolution

**Date Created**: 2025-11-03
**Status**: Temporary workaround applied, permanent fix needed
**Related Task**: Archon Project "Phase 4 Testing Fixes" - Task TBD

---

## Issue Summary

When migrating test infrastructure from SQLite to PostgreSQL, tests failed with:
```
asyncpg.exceptions.UndefinedObjectError: type "userrole" does not exist
```

This occurred because **PostgreSQL ENUM types were not being created** by Alembic migrations, causing SQLAlchemy to fail when trying to insert data using these custom types.

---

## Root Cause Analysis

### The Problem

The application models use Python `Enum` classes that SQLAlchemy maps to PostgreSQL ENUM types:

```python
# backend/app/db/models.py
from enum import Enum as PyEnum

class UserRole(str, PyEnum):
    WRITER = "writer"
    EDITOR = "editor"
    ADMIN = "admin"

class User(Base):
    __tablename__ = "users"
    role = Column(Enum(UserRole, name="userrole"), nullable=False)
```

SQLAlchemy expects the PostgreSQL ENUM type `userrole` to exist in the database, but:

1. **Alembic migrations didn't create these ENUM types** - The migrations created tables but not the prerequisite ENUM types
2. **Both production and test databases were missing ENUMs** - Neither database had the proper type definitions
3. **SQLite doesn't use ENUMs** - Previously, tests used SQLite which stores enums as strings, masking this issue

### Expected ENUM Types

The following PostgreSQL ENUM types should exist:

| Type Name | Values | Used By |
|-----------|--------|---------|
| `userrole` | `writer`, `editor`, `admin` | `users.role` |
| `outputtype` | `grant_proposal`, `letter_of_inquiry`, `grant_report`, `other` | `outputs.output_type` |
| `outputstatus` | `draft`, `submitted`, `pending`, `awarded`, `not_awarded` | `outputs.status` |
| `styletype` | `narrative`, `technical`, `persuasive`, `academic`, `other` | `writing_styles.style_type` |

---

## Temporary Workaround (Current State)

### What Was Done

Manually created ENUM types in the **test database only**:

```sql
CREATE TYPE userrole AS ENUM ('writer', 'editor', 'admin');
CREATE TYPE outputtype AS ENUM ('grant_proposal', 'letter_of_inquiry', 'grant_report', 'other');
CREATE TYPE outputstatus AS ENUM ('draft', 'submitted', 'pending', 'awarded', 'not_awarded');
CREATE TYPE styletype AS ENUM ('narrative', 'technical', 'persuasive', 'academic', 'other');
```

**Command Used**:
```bash
docker exec org-archivist-postgres-test psql -U test_user -d org_archivist_test -c "
CREATE TYPE userrole AS ENUM ('writer', 'editor', 'admin');
CREATE TYPE outputtype AS ENUM ('grant_proposal', 'letter_of_inquiry', 'grant_report', 'other');
CREATE TYPE outputstatus AS ENUM ('draft', 'submitted', 'pending', 'awarded', 'not_awarded');
CREATE TYPE styletype AS ENUM ('narrative', 'technical', 'persuasive', 'academic', 'other');
"
```

### Verification

```bash
# Verify ENUM types exist
docker exec org-archivist-postgres-test psql -U test_user -d org_archivist_test -c "\dT+"
```

Expected output shows all 4 ENUM types plus the `gtrgm` type from pg_trgm extension.

### Limitations of Workaround

- ❌ **Not automated** - Won't work on fresh test database instances
- ❌ **Production database still missing ENUMs** - Needs manual intervention or migration
- ❌ **Not version controlled** - Manual SQL not tracked in migrations
- ❌ **Fragile** - Any new ENUM values require manual updates

---

## Permanent Solution (To Be Implemented)

### Option A: Update Baseline Migration (Recommended)

**What**: Modify the baseline Alembic migration to create ENUM types before creating tables.

**Location**: `backend/alembic/versions/2e0140e533a8_baseline_schema.py`

**Implementation**:

```python
def upgrade():
    # Create ENUM types FIRST (before any tables that use them)
    op.execute("CREATE TYPE userrole AS ENUM ('writer', 'editor', 'admin')")
    op.execute("CREATE TYPE outputtype AS ENUM ('grant_proposal', 'letter_of_inquiry', 'grant_report', 'other')")
    op.execute("CREATE TYPE outputstatus AS ENUM ('draft', 'submitted', 'pending', 'awarded', 'not_awarded')")
    op.execute("CREATE TYPE styletype AS ENUM ('narrative', 'technical', 'persuasive', 'academic', 'other')")

    # Then create tables...
    # (existing table creation code)

def downgrade():
    # Drop tables first (in reverse order)
    # (existing table drop code)

    # Then drop ENUM types
    op.execute("DROP TYPE IF EXISTS styletype")
    op.execute("DROP TYPE IF EXISTS outputstatus")
    op.execute("DROP TYPE IF EXISTS outputtype")
    op.execute("DROP TYPE IF EXISTS userrole")
```

**Pros**:
- ✅ Ensures ENUMs exist before tables referencing them
- ✅ Works for fresh database installs
- ✅ Maintains migration history
- ✅ Bidirectional (upgrade/downgrade)

**Cons**:
- ⚠️ Requires existing databases to run the baseline migration again OR apply ENUMs manually

### Option B: Create New Migration for ENUM Types

**What**: Create a new Alembic migration specifically for adding ENUM types.

**Command**:
```bash
cd backend
alembic revision -m "add_postgresql_enum_types"
```

**Implementation**: Similar to Option A, but in a new migration file.

**Pros**:
- ✅ Cleaner separation of concerns
- ✅ Can be applied to existing databases without re-running baseline

**Cons**:
- ⚠️ Doesn't help with fresh installations (baseline still needs ENUMs)
- ⚠️ Requires manually tracking which ENUMs are already created

### Option C: Use SQLAlchemy's Native ENUM Creation

**What**: Rely on SQLAlchemy's automatic ENUM type creation.

**Implementation**:
```python
# In models, use create_type=True
role = Column(Enum(UserRole, name="userrole", create_type=True), nullable=False)
```

**Pros**:
- ✅ Automatic ENUM creation by SQLAlchemy

**Cons**:
- ❌ Doesn't work well with Alembic migrations
- ❌ Can cause issues with migration ordering
- ❌ Not recommended for production use

---

## Recommended Action Plan

### Step 1: Create Alembic Migration (High Priority)

Create a new migration that explicitly creates ENUM types:

```bash
cd backend
alembic revision -m "add_postgresql_enum_types"
```

Edit the generated file:
```python
"""add_postgresql_enum_types

Revision ID: <generated_id>
Revises: 6f2e9b3a4d5c  # Latest migration
Create Date: <timestamp>

"""
from alembic import op

def upgrade():
    # Create all ENUM types used by the application
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE userrole AS ENUM ('writer', 'editor', 'admin');
        EXCEPTION
            WHEN duplicate_object THEN null;
        END $$;
    """)

    op.execute("""
        DO $$ BEGIN
            CREATE TYPE outputtype AS ENUM ('grant_proposal', 'letter_of_inquiry', 'grant_report', 'other');
        EXCEPTION
            WHEN duplicate_object THEN null;
        END $$;
    """)

    op.execute("""
        DO $$ BEGIN
            CREATE TYPE outputstatus AS ENUM ('draft', 'submitted', 'pending', 'awarded', 'not_awarded');
        EXCEPTION
            WHEN duplicate_object THEN null;
        END $$;
    """)

    op.execute("""
        DO $$ BEGIN
            CREATE TYPE styletype AS ENUM ('narrative', 'technical', 'persuasive', 'academic', 'other');
        EXCEPTION
            WHEN duplicate_object THEN null;
        END $$;
    """)

def downgrade():
    # Note: Only drop if no tables are using them
    op.execute("DROP TYPE IF EXISTS styletype")
    op.execute("DROP TYPE IF EXISTS outputstatus")
    op.execute("DROP TYPE IF EXISTS outputtype")
    op.execute("DROP TYPE IF EXISTS userrole")
```

**Note**: The `DO $$ BEGIN ... EXCEPTION WHEN duplicate_object` pattern allows the migration to be idempotent (safe to run multiple times).

### Step 2: Apply to All Databases

**Test Database**:
```bash
# Already has ENUMs from manual creation, but run migration for consistency
docker run --rm --network org-archivist-network \
  -v /home/zacharyn/PyCharm-Projects/org-archivist:/app \
  -w /app/backend \
  -e DATABASE_URL="postgresql://test_user:test_password@postgres-test:5432/org_archivist_test" \
  python:3.11-slim bash -c "
    pip install -q -r requirements.txt &&
    alembic upgrade head
  "
```

**Production Database**:
```bash
# IMPORTANT: Review current state first!
docker exec org-archivist-postgres psql -U user -d org_archivist -c "\dT+"

# Then apply migration
docker run --rm --network org-archivist-network \
  -v /home/zacharyn/PyCharm-Projects/org-archivist:/app \
  -w /app/backend \
  -e DATABASE_URL="postgresql://user:password@postgres:5432/org_archivist" \
  python:3.11-slim bash -c "
    pip install -q -r requirements.txt &&
    alembic upgrade head
  "
```

### Step 3: Update Baseline Migration (Nice-to-have)

For clean installations, also update the baseline migration (`2e0140e533a8_baseline_schema.py`) to create ENUMs first. This ensures fresh database installs work correctly.

### Step 4: Document in README

Add note to project README about PostgreSQL ENUM requirements for anyone setting up the project fresh.

---

## Testing the Fix

### Verify ENUM Types Exist

```bash
# Test database
docker exec org-archivist-postgres-test psql -U test_user -d org_archivist_test -c "\dT+"

# Production database
docker exec org-archivist-postgres psql -U user -d org_archivist -c "\dT+"
```

Expected output should show all 4 application ENUM types:
- `userrole`
- `outputtype`
- `outputstatus`
- `styletype`

### Run Tests

```bash
# Run API tests
docker run --rm --network org-archivist-network \
  -v /home/zacharyn/PyCharm-Projects/org-archivist:/app \
  -w /app \
  -e TEST_DATABASE_URL="postgresql+asyncpg://test_user:test_password@postgres-test:5432/org_archivist_test" \
  python:3.11-slim bash -c "
    pip install -q -r backend/requirements.txt email-validator &&
    python -m pytest backend/tests/test_outputs_api.py -v
  "
```

Tests should pass without "type does not exist" errors.

---

## Related Files

- **Models**: `backend/app/db/models.py` - Defines Python Enum classes
- **Baseline Migration**: `backend/alembic/versions/2e0140e533a8_baseline_schema.py`
- **Latest Migration**: `backend/alembic/versions/6f2e9b3a4d5c_add_outputs_table.py`
- **Test Configuration**: `pytest.ini`, `backend/tests/conftest.py`

---

## Future Considerations

### Adding New ENUM Values

When adding new values to an existing ENUM:

```sql
-- PostgreSQL doesn't support ALTER TYPE ... ADD VALUE in a transaction
-- Must run outside transaction or use a migration with special handling

ALTER TYPE userrole ADD VALUE 'guest' AFTER 'writer';
```

**In Alembic**:
```python
def upgrade():
    # Must use connection.execute() with autocommit
    op.execute("ALTER TYPE userrole ADD VALUE IF NOT EXISTS 'guest'")
```

**Note**: PostgreSQL ENUM value additions are non-transactional and cannot be rolled back!

### Creating New ENUM Types

Always create the ENUM type in a migration **before** any table that uses it:

```python
def upgrade():
    # 1. Create ENUM type first
    op.execute("CREATE TYPE documenttype AS ENUM ('pdf', 'docx', 'txt')")

    # 2. Then create table using it
    op.create_table(
        'documents',
        sa.Column('doc_type', sa.Enum('pdf', 'docx', 'txt', name='documenttype'))
    )
```

---

## Summary Checklist

### Current State (Temporary Fix)
- [x] Test database has ENUM types (manually created)
- [ ] Production database has ENUM types
- [ ] ENUM types defined in Alembic migrations
- [ ] Fresh database installations work correctly

### To Complete Permanent Fix
- [ ] Create Alembic migration for ENUM types
- [ ] Apply migration to test database
- [ ] Apply migration to production database
- [ ] Update baseline migration for fresh installs
- [ ] Verify all tests pass
- [ ] Document in project README

---

**Last Updated**: 2025-11-03
**Maintained By**: Development Team
**Next Review**: After permanent fix is implemented
