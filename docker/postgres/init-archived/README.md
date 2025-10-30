# Archived PostgreSQL Init Scripts

This directory contains archived SQL initialization scripts that are **no longer used** in the Org Archivist application.

## Why These Files Are Archived

As of October 2025, Org Archivist migrated to a **pure Alembic approach** for database schema management. All database schema changes are now managed through version-controlled Alembic migrations instead of SQL init scripts.

## What Replaced These Files

The functionality previously provided by `01-init-database.sql` is now handled by:

1. **Alembic Baseline Migration** (`backend/alembic/versions/2e0140e533a8_baseline_schema.py`)
   - Creates the complete initial database schema
   - Includes all tables, indexes, and constraints
   - Version-controlled and reviewable

2. **Subsequent Migrations**
   - All schema changes after baseline are managed through individual Alembic migrations
   - Each change is tracked, reviewable, and reversible

3. **Auto-Migration System** (`backend/app/utils/migrations.py`)
   - Automatically applies migrations on application startup (development)
   - Manual migration control for production deployments

## Benefits of the New Approach

- ✅ **Version Control**: All schema changes tracked in Git
- ✅ **Rollback Capability**: Can downgrade to any previous version
- ✅ **Review Process**: Migrations reviewed before applying
- ✅ **Consistency**: Same schema applied across all environments
- ✅ **Automation**: Automatic in dev, controlled in production
- ✅ **Developer Experience**: Clear workflow with proper tooling

## Historical Reference

These files are preserved for historical reference and to understand the evolution of the database schema. They should **not** be used in any deployment.

## Migration Guide

For information on using the new migration system, see:

- `backend/alembic/README.md` - Alembic migration documentation
- `DEVELOPMENT.md` - Developer workflow guide
- `docs/auto-migrations.md` - Auto-migration implementation details
- `context/architecture.md` - Architecture documentation (section 3.3)

## File Inventory

- `01-init-database.sql.backup` - Original PostgreSQL initialization script (deprecated)

---

**Last Updated:** October 30, 2025
**Migration Completed:** Feature branch `feature/alembic-pure-migrations`
