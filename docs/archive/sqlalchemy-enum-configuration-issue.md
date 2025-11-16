# SQLAlchemy Enum Configuration Issue - PostgreSQL Integration

**Date Created**: 2025-11-03
**Status**: ⏸️ Blocked - Awaiting Fix
**Severity**: 🔴 HIGH - Blocks all PostgreSQL-based testing
**Related Files**:
- `backend/app/db/models.py` (all Enum column definitions)
- `/docs/postgresql-enum-types-issue.md` (prerequisite context)

---

## Issue Summary

After successfully setting up PostgreSQL test database and creating ENUM types, tests now fail with:

```
sqlalchemy.exc.DBAPIError: (sqlalchemy.dialects.postgresql.asyncpg.Error)
<class 'asyncpg.exceptions.InvalidTextRepresentationError'>:
invalid input value for enum userrole: "ADMIN"
```

**Root Cause**: SQLAlchemy's `Enum()` column type is sending Python Enum **names** (uppercase, e.g., `ADMIN`) to PostgreSQL instead of Enum **values** (lowercase, e.g., `admin`).

---

## Technical Background

### Python Enum Definition (Correct)

```python
# backend/app/db/models.py lines 33-37
class UserRole(str, enum.Enum):
    """User role enumeration"""
    ADMIN = "admin"      # NAME = "ADMIN", VALUE = "admin"
    EDITOR = "editor"    # NAME = "EDITOR", VALUE = "editor"
    WRITER = "writer"    # NAME = "WRITER", VALUE = "writer"
```

### PostgreSQL ENUM Type (Correct)

```sql
-- Created manually, values match Python Enum values
CREATE TYPE userrole AS ENUM ('admin', 'editor', 'writer');
```

### SQLAlchemy Column Definition (INCORRECT)

```python
# backend/app/db/models.py line 233
role = Column(SQLEnum(UserRole), nullable=False, default=UserRole.WRITER)
```

**Problem**: `SQLEnum(UserRole)` uses the default behavior which sends enum **name** instead of **value**.

### What SQLAlchemy Sends

```python
# When creating a user with role=UserRole.ADMIN
user = User(role=UserRole.ADMIN)
db.add(user)
db.commit()

# SQLAlchemy generates:
# INSERT INTO users (..., role, ...) VALUES (..., 'ADMIN', ...)
#                                                  ^^^^^^^^
#                                                  Should be 'admin'!
```

### What PostgreSQL Expects

```sql
-- PostgreSQL ENUM definition
CREATE TYPE userrole AS ENUM ('admin', 'editor', 'writer');
                              ^^^^^^^ ^^^^^^^^  ^^^^^^^^
                              lowercase values only

-- Valid INSERT:
INSERT INTO users (role) VALUES ('admin');   -- ✅ Works

-- Invalid INSERT (what SQLAlchemy is doing):
INSERT INTO users (role) VALUES ('ADMIN');   -- ❌ Fails!
-- Error: invalid input value for enum userrole: "ADMIN"
```

---

## Error Example

**Test Code**:
```python
# backend/tests/test_outputs_api.py lines 91-100
admin = User(
    user_id=uuid4(),
    email="admin@test.com",
    hashed_password=AuthService.hash_password("AdminPass123!"),
    full_name="Admin User",
    role=UserRole.ADMIN,    # This is correct Python usage
    is_active=True,
    is_superuser=False,
)
db_session.add(admin)
await db_session.commit()   # ❌ Fails here!
```

**Full Error Trace**:
```
ERROR backend/tests/test_outputs_api.py::TestCreateOutput::test_create_output_authenticated_user
sqlalchemy.exc.DBAPIError: (sqlalchemy.dialects.postgresql.asyncpg.Error)
<class 'asyncpg.exceptions.InvalidTextRepresentationError'>:
invalid input value for enum userrole: "ADMIN"

[SQL: INSERT INTO users (user_id, email, hashed_password, full_name, role,
is_active, is_superuser, created_at, updated_at)
VALUES ($1::UUID, $2::VARCHAR, $3::VARCHAR, $4::VARCHAR, $5::userrole,
$6::BOOLEAN, $7::BOOLEAN, $8::TIMESTAMP WITHOUT TIME ZONE,
$9::TIMESTAMP WITHOUT TIME ZONE)]

[parameters: [(UUID('d3959b1e-0684-42af-b1fd-9d9c98a8618c'),
'admin@test.com', '$2b$12$...', 'Admin User',
'ADMIN',    # ❌ This should be 'admin'
True, False, datetime(...), datetime(...))]]
```

---

## Solution: Fix SQLAlchemy Enum Column Definitions

### Option 1: Use `values_callable` (Explicit)

**Recommended for clarity**

```python
# backend/app/db/models.py
from sqlalchemy import Enum as SQLEnum

role = Column(
    SQLEnum(
        UserRole,
        values_callable=lambda x: [e.value for e in x],  # Use .value not .name
        native_enum=True,  # Use PostgreSQL native ENUM type
        name="userrole"     # Explicit ENUM type name
    ),
    nullable=False,
    default=UserRole.WRITER
)
```

**How it works**:
- `values_callable=lambda x: [e.value for e in x]` extracts `["admin", "editor", "writer"]` instead of `["ADMIN", "EDITOR", "WRITER"]`
- SQLAlchemy will send `"admin"` when `role=UserRole.ADMIN`

### Option 2: Let SQLAlchemy Auto-Detect (Simpler)

**May work if SQLAlchemy detects `str` enum**

```python
role = Column(
    SQLEnum(UserRole, native_enum=True),
    nullable=False,
    default=UserRole.WRITER
)
```

**Caveat**: This relies on SQLAlchemy detecting that `UserRole` inherits from `str` and using `.value` automatically. May not work reliably across all SQLAlchemy versions.

### Option 3: Use String Column with Check Constraint (Alternative)

**If Enum type causes too many issues**

```python
from sqlalchemy import String, CheckConstraint

role = Column(
    String(20),
    CheckConstraint("role IN ('admin', 'editor', 'writer')", name='check_user_role'),
    nullable=False,
    default='writer'
)
```

**Note**: Loses type safety at Python level, but simpler database interaction.

---

## All Affected Columns

Search for all `SQLEnum` usage in models:

### 1. User Model - `role` column

**Location**: `backend/app/db/models.py` line 233

**Current**:
```python
role = Column(SQLEnum(UserRole), nullable=False, default=UserRole.WRITER)
```

**Fixed**:
```python
role = Column(
    SQLEnum(UserRole, values_callable=lambda x: [e.value for e in x], native_enum=True),
    nullable=False,
    default=UserRole.WRITER
)
```

### 2. Output Model - `output_type` column

**Location**: `backend/app/db/models.py` (search for OutputType enum)

**Expected Current**:
```python
output_type = Column(SQLEnum(OutputType), nullable=False)
```

**Fixed**:
```python
output_type = Column(
    SQLEnum(OutputType, values_callable=lambda x: [e.value for e in x], native_enum=True),
    nullable=False
)
```

### 3. Output Model - `status` column

**Location**: `backend/app/db/models.py` (search for OutputStatus enum)

**Expected Current**:
```python
status = Column(SQLEnum(OutputStatus), nullable=False, default=OutputStatus.DRAFT)
```

**Fixed**:
```python
status = Column(
    SQLEnum(OutputStatus, values_callable=lambda x: [e.value for e in x], native_enum=True),
    nullable=False,
    default=OutputStatus.DRAFT
)
```

### 4. WritingStyle Model - `style_type` column

**Location**: `backend/app/db/models.py` (search for StyleType enum)

**Expected Current**:
```python
style_type = Column(SQLEnum(StyleType), nullable=False)
```

**Fixed**:
```python
style_type = Column(
    SQLEnum(StyleType, values_callable=lambda x: [e.value for e in x], native_enum=True),
    nullable=False
)
```

---

## Step-by-Step Fix Instructions

### Step 1: Locate All Enum Columns

```bash
cd /home/zacharyn/PyCharm-Projects/org-archivist
grep -n "SQLEnum" backend/app/db/models.py
```

Expected output will show all lines with `SQLEnum(...)` usage.

### Step 2: Update Each Enum Column Definition

For each line found, replace:

```python
Column(SQLEnum(EnumClass), ...)
```

With:

```python
Column(
    SQLEnum(EnumClass, values_callable=lambda x: [e.value for e in x], native_enum=True),
    ...
)
```

### Step 3: Verify Enum Class Definitions

Ensure all Python Enum classes inherit from both `str` and `enum.Enum`:

```python
class UserRole(str, enum.Enum):  # ✅ Good - inherits str
    ADMIN = "admin"
    EDITOR = "editor"
    WRITER = "writer"

class BadExample(enum.Enum):  # ❌ Bad - missing str inheritance
    ADMIN = "admin"
```

### Step 4: Test the Fix

Run a simple test to verify:

```bash
docker run --rm --network org-archivist-network \
  -v /home/zacharyn/PyCharm-Projects/org-archivist:/app \
  -w /app \
  -e TEST_DATABASE_URL="postgresql+asyncpg://test_user:test_password@postgres-test:5432/org_archivist_test" \
  python:3.11-slim bash -c "
    pip install -q -r backend/requirements.txt email-validator &&
    python -m pytest backend/tests/test_outputs_api.py::TestCreateOutput::test_create_output_authenticated_user -v
  "
```

**Expected**: Test should pass without "invalid input value for enum" errors.

### Step 5: Run Full Test Suite

```bash
docker run --rm --network org-archivist-network \
  -v /home/zacharyn/PyCharm-Projects/org-archivist:/app \
  -w /app \
  -e TEST_DATABASE_URL="postgresql+asyncpg://test_user:test_password@postgres-test:5432/org_archivist_test" \
  python:3.11-slim bash -c "
    pip install -q -r backend/requirements.txt email-validator &&
    python -m pytest backend/tests/test_outputs_api.py -v
  "
```

---

## Verification Checklist

After applying the fix:

- [ ] All Enum column definitions use `values_callable`
- [ ] All Python Enum classes inherit from `str` and `enum.Enum`
- [ ] PostgreSQL ENUM types match Python Enum values (lowercase)
- [ ] Test user creation succeeds without errors
- [ ] Output creation succeeds without errors
- [ ] WritingStyle creation succeeds without errors
- [ ] Full test suite passes

---

## Alternative: Quick Workaround (Not Recommended)

If you need immediate unblocking without modifying models, you can temporarily change PostgreSQL ENUMs to uppercase:

```sql
-- Drop existing ENUMs
DROP TYPE IF EXISTS userrole CASCADE;
DROP TYPE IF EXISTS outputtype CASCADE;
DROP TYPE IF EXISTS outputstatus CASCADE;
DROP TYPE IF EXISTS styletype CASCADE;

-- Recreate with uppercase values (matches Python Enum names)
CREATE TYPE userrole AS ENUM ('ADMIN', 'EDITOR', 'WRITER');
CREATE TYPE outputtype AS ENUM ('GRANT_PROPOSAL', 'LETTER_OF_INQUIRY', 'GRANT_REPORT', 'OTHER');
CREATE TYPE outputstatus AS ENUM ('DRAFT', 'SUBMITTED', 'PENDING', 'AWARDED', 'NOT_AWARDED');
CREATE TYPE styletype AS ENUM ('NARRATIVE', 'TECHNICAL', 'PERSUASIVE', 'ACADEMIC', 'OTHER');
```

**Why this is not recommended**:
- ❌ Violates PostgreSQL conventions (lowercase enum values)
- ❌ Doesn't match the actual Python Enum **values**
- ❌ Creates confusion between name and value
- ❌ Will cause issues if Python code ever uses `.value` property

**Only use this if**: You need immediate test execution and will fix properly later.

---

## Related Issues

1. **PostgreSQL ENUM Types Missing**: See `/docs/postgresql-enum-types-issue.md` - This was the prerequisite issue that we already resolved.

2. **Alembic Migration for ENUMs**: Archon task created to properly add ENUM creation to Alembic migrations.

---

## Testing After Fix

### Quick Verification Test

```python
# Create a simple test script: test_enum_fix.py
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from backend.app.db.models import User, UserRole
from uuid import uuid4

async def test_enum():
    engine = create_async_engine(
        "postgresql+asyncpg://test_user:test_password@localhost:5433/org_archivist_test",
        echo=True
    )

    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as session:
        # Test creating user with ADMIN role
        user = User(
            user_id=uuid4(),
            email="test@example.com",
            hashed_password="hashed",
            full_name="Test User",
            role=UserRole.ADMIN,  # Should send "admin" not "ADMIN"
            is_active=True,
            is_superuser=False
        )
        session.add(user)
        await session.commit()
        print("✅ User created successfully with role:", user.role)
        print("✅ Role value in DB:", user.role.value)

asyncio.run(test_enum())
```

Run:
```bash
python test_enum_fix.py
```

Expected output:
```
✅ User created successfully with role: UserRole.ADMIN
✅ Role value in DB: admin
```

---

## Summary

**Problem**: SQLAlchemy sends Enum names (uppercase) instead of values (lowercase) to PostgreSQL

**Root Cause**: Default `SQLEnum()` behavior doesn't specify how to extract values from Python Enums

**Solution**: Use `values_callable=lambda x: [e.value for e in x]` in all `SQLEnum()` column definitions

**Affected Models**: User, Output, WritingStyle (4 columns total)

**Estimated Fix Time**: 30 minutes

**Testing Time**: 15 minutes

**Total Impact**: ~45 minutes to resolve

---

**Last Updated**: 2025-11-03
**Status**: Documented, awaiting implementation
**Next Action**: Update Enum column definitions in `backend/app/db/models.py`
