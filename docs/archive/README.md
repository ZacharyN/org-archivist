# Documentation Archive

## Purpose

This directory contains:
1. **Development Documentation** - Historical docs from completed development phases
2. **Database Schema Archives** - Archived database initialization scripts and schema exports from the migration to pure Alembic-based database migrations

---

## Development Documentation Archive

These documents were valuable during specific development phases but are no longer needed for day-to-day maintenance, frontend development, or production operations. They are preserved for historical reference.

### Development-Specific Guides
- **authentication-development-strategy.md** - Authentication implementation strategy (now complete)
- **frontend-preparation-roadmap.md** - Pre-Nuxt 4 frontend preparation planning
- **streamlit-development-plan.md** - Original Streamlit frontend plan (replaced by Nuxt 4)
- **streamlit-fixes-summary.md** - Streamlit fixes (no longer relevant)
- **writing-styles-wizard-handoff.md** - Writing styles implementation handoff

### Testing & Validation Reports
- **api-endpoint-verification.md** - API endpoint verification procedures
- **api-test-results.md** - Historical API test results
- **test-auth-fixture-isolation-issue.md** - Auth fixture isolation debugging
- **test-infrastructure-auth-driver-issues.md** - Test infrastructure challenges
- **test-infrastructure-technical-debt.md** - Test infrastructure technical debt analysis
- **test-remaining-issues.md** - Test issues snapshot

### Technical Issues & Solutions
- **async-testing-testclient-architecture-mismatch.md** - TestClient async issues analysis
- **bm25-okapi-zero-idf-issue.md** - BM25Okapi IDF calculation bug and solution
- **outputs-api-database-service-di-issue.md** - Database service dependency injection issue
- **postgresql-enum-types-issue.md** - PostgreSQL enum type handling
- **sqlalchemy-enum-configuration-issue.md** - SQLAlchemy enum configuration

### Architecture & Planning
- **MVP_STATUS_AND_REMAINING_TASKS.md** - MVP status checkpoint
- **reranking-decision-and-roadmap.md** - Reranking implementation decision and roadmap
- **retrieval-engine-usage.md** - Early retrieval engine documentation

**Active Documentation:** For current docs, see [/docs/README.md](../README.md)

---

## Database Schema Archive

### Files

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
