# Database Schema Archive

## Purpose

This directory contains archived database initialization scripts and schema exports from the org-archivist project's migration to pure Alembic-based database migrations.

## Files

### `01-init-database-backup-20251030.sql`
**Date:** October 30, 2025
**Source:** `docker/postgres/init/01-init-database.sql`
**Purpose:** Backup of the original PostgreSQL initialization script used before migrating to Alembic

This file contains the complete database schema including:
- 8 tables (documents, document_programs, document_tags, prompt_templates, conversations, messages, system_config, audit_log)
- PostgreSQL extensions (uuid-ossp, pg_trgm)
- Indexes for performance optimization
- Check constraints for data validation
- Triggers for auto-updating timestamps
- Seed data for system configuration and prompt templates

### `schema-export-20251030.sql`
**Date:** October 30, 2025
**Source:** Exported from running PostgreSQL database using `pg_dump`
**Purpose:** Live schema export for comparison and verification

This export captures the actual state of the database at the time of migration, ensuring we have a reference point for:
- Verifying that the Alembic migration creates an identical schema
- Troubleshooting any discrepancies
- Rolling back if needed

## Migration Context

### Why This Migration Happened

The org-archivist project originally used a hybrid database management approach:
1. **SQL Init Script:** `docker/postgres/init/01-init-database.sql` created the baseline schema
2. **Alembic Migrations:** Handled subsequent schema changes

This approach had several drawbacks:
- Dual maintenance burden (SQL script + Alembic)
- Alembic couldn't fully track schema history
- No way to rollback the baseline schema
- Inconsistent migration testing

### The New Approach

**Pure Alembic Migrations:**
- All schema changes managed through Alembic
- Complete version control of database schema
- Reliable rollback capabilities
- Single source of truth

### Migration Tasks Completed

See Archon Project: **Migrate to Pure Alembic Database Migrations** (ID: 8b9052de-9d8b-408c-9c7b-3084112b896c)

1. ✓ Backup current database schema and document existing structure
2. Convert baseline migration to create actual schema
3. Create data migration for seed data
4. Implement automatic migration runner on app startup
5. Update Docker configuration to remove SQL init script
6. Test migration on clean database
7. Update documentation for new migration workflow
8. Clean up old SQL init script and archive

## Restoration Instructions

If you need to restore the old SQL-based initialization:

```bash
# 1. Stop containers
docker-compose down -v

# 2. Copy the backup back
cp docs/archive/01-init-database-backup-20251030.sql docker/postgres/init/01-init-database.sql

# 3. Uncomment volume mount in docker-compose.yml
# volumes:
#   - ./docker/postgres/init:/docker-entrypoint-initdb.d:ro

# 4. Restart containers
docker-compose up -d

# 5. Revert Alembic baseline migration to no-op state
# Edit: backend/alembic/versions/2e0140e533a8_baseline_schema.py
# Change upgrade() and downgrade() back to pass
```

## References

- **Project ID:** 8b9052de-9d8b-408c-9c7b-3084112b896c
- **Branch:** feature/alembic-pure-migrations
- **Architecture Doc:** `context/architecture.md` (Section 3.2 - Metadata Storage)
- **Original SQL Script:** Lines 1-310 of this backup file
