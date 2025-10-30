# Automatic Database Migrations

## Overview

The Org Archivist backend now includes an automatic database migration system that runs Alembic migrations on application startup. This ensures your database schema is always up-to-date when the application starts.

## Features

- **Automatic Execution**: Migrations run automatically when FastAPI starts
- **Database Health Check**: Verifies database connectivity before attempting migrations
- **Retry Logic**: Automatically retries failed migrations with configurable attempts and delays
- **Error Handling**: Comprehensive error handling with detailed logging
- **Graceful Degradation**: Application continues starting even if migrations fail (allows debugging)
- **Configurable**: Can be disabled via environment variable for manual control

## Configuration

### Environment Variables

Add these to your `.env` file:

```bash
# Disable automatic database migrations on startup (true | false)
# Set to true if you want to run migrations manually
DISABLE_AUTO_MIGRATIONS=false

# Migration timeout in seconds
MIGRATION_TIMEOUT_SECONDS=60

# Number of retry attempts for migrations
MIGRATION_RETRY_ATTEMPTS=3

# Delay between migration retry attempts in seconds
MIGRATION_RETRY_DELAY_SECONDS=5
```

### Default Values

- `DISABLE_AUTO_MIGRATIONS`: `false` (migrations run automatically)
- `MIGRATION_TIMEOUT_SECONDS`: `60`
- `MIGRATION_RETRY_ATTEMPTS`: `3`
- `MIGRATION_RETRY_DELAY_SECONDS`: `5`

## How It Works

### Startup Sequence

1. **Application Starts**: FastAPI lifespan manager begins
2. **Database Check**: Verifies database is available (with retries)
3. **Run Migrations**: Executes `alembic upgrade head`
4. **Retry on Failure**: Retries up to `MIGRATION_RETRY_ATTEMPTS` times if needed
5. **Log Results**: Logs success or failure details
6. **Continue Startup**: Initializes database connection pool and other services

### Migration Process

```python
# Automatic execution in backend/app/main.py lifespan()
await run_startup_migrations(
    database_url=settings.database_url,
    disable_auto_migrations=settings.disable_auto_migrations,
    max_attempts=settings.migration_retry_attempts,
    retry_delay_seconds=settings.migration_retry_delay_seconds,
    timeout_seconds=settings.migration_timeout_seconds
)
```

### What Gets Logged

**Success:**
```
INFO - Checking database connectivity...
INFO - ✓ Database connection successful
INFO - Running migrations from: /app/backend/alembic.ini
INFO - Alembic output:
INFO - ✓ Migrations completed successfully
INFO - Database migrations completed successfully
```

**Disabled:**
```
INFO - Automatic migrations are disabled (DISABLE_AUTO_MIGRATIONS=true)
INFO - Run migrations manually with: alembic upgrade head
```

**Failure:**
```
WARNING - Database connection attempt 1/3 failed: connection refused
INFO - Retrying in 5 seconds...
ERROR - Migration attempt 1 failed: Migration failed with exit code 1
ERROR - Failed to run migrations after 3 attempts
WARNING - Application will continue starting, but database may be out of date
```

## Usage Scenarios

### Development (Default)

Automatic migrations are enabled by default. Just start the application:

```bash
docker-compose up
```

Migrations will run automatically on startup.

### Production Deployment

**Option 1: Automatic (Recommended)**

Keep `DISABLE_AUTO_MIGRATIONS=false` and let the application handle migrations on startup.

**Option 2: Manual Control**

```bash
# In .env
DISABLE_AUTO_MIGRATIONS=true
```

Then run migrations manually before starting the app:

```bash
docker-compose run --rm backend alembic upgrade head
docker-compose up
```

### CI/CD Pipelines

**Option A: Pre-deployment Migration**

```bash
# Run migrations as a separate step
docker-compose run --rm backend alembic upgrade head

# Then deploy with auto-migrations disabled
DISABLE_AUTO_MIGRATIONS=true docker-compose up -d
```

**Option B: Let Application Handle It**

```bash
# Deploy with auto-migrations enabled
docker-compose up -d
```

The application will run migrations on startup.

### Zero-Downtime Deployments

For zero-downtime deployments with multiple instances:

1. Create backward-compatible migrations
2. Run migrations manually before deployment:
   ```bash
   alembic upgrade head
   ```
3. Deploy new application version with `DISABLE_AUTO_MIGRATIONS=true`
4. Rolling restart of application instances

## Troubleshooting

### Migrations Fail on Startup

**Symptom:**
```
ERROR - Failed to run migrations after 3 attempts
```

**Solutions:**

1. **Check Database Connectivity:**
   ```bash
   docker-compose ps postgres
   docker-compose logs postgres
   ```

2. **Verify Database URL:**
   ```bash
   # In .env, ensure DATABASE_URL is correct
   DATABASE_URL=postgresql://user:password@postgres:5432/org_archivist
   ```

3. **Run Migrations Manually:**
   ```bash
   docker-compose exec backend alembic upgrade head
   ```

4. **Check Alembic Configuration:**
   ```bash
   docker-compose exec backend alembic current
   docker-compose exec backend alembic history
   ```

### Database Not Ready

**Symptom:**
```
WARNING - Database connection attempt 1/3 failed
```

**Solution:**

The migration runner includes retry logic. If database takes longer to start, increase retry settings:

```bash
MIGRATION_RETRY_ATTEMPTS=5
MIGRATION_RETRY_DELAY_SECONDS=10
```

### Migration Timeout

**Symptom:**
```
ERROR - Migration timed out after 60 seconds
```

**Solution:**

Increase timeout for complex migrations:

```bash
MIGRATION_TIMEOUT_SECONDS=120
```

### Want to Skip Migrations

**Solution:**

Disable automatic migrations:

```bash
DISABLE_AUTO_MIGRATIONS=true
```

Then run manually when needed:

```bash
docker-compose exec backend alembic upgrade head
```

## Implementation Details

### Files Created

- `backend/app/utils/migrations.py` - Migration runner with retry logic
- `backend/app/utils/__init__.py` - Utils module initialization
- Updated `backend/app/config.py` - Added migration configuration
- Updated `backend/app/main.py` - Integrated migration runner in lifespan
- Updated `.env.example` - Added migration configuration examples

### Key Functions

- `wait_for_database()` - Checks database connectivity with retries
- `run_alembic_upgrade()` - Executes Alembic migrations
- `run_migrations_with_retry()` - Runs migrations with retry logic
- `run_startup_migrations()` - Main entry point called at startup

### Dependencies

Required packages (already in `requirements.txt`):
- `alembic` - Database migrations
- `sqlalchemy` - Database ORM
- `psycopg2-binary` - PostgreSQL driver

## Best Practices

1. **Always Test Migrations Locally First**
   ```bash
   alembic upgrade head
   alembic downgrade -1
   ```

2. **Create Backward-Compatible Migrations**
   - Add new columns as nullable
   - Don't drop columns immediately
   - Use multi-step migrations for breaking changes

3. **Monitor Migration Logs**
   ```bash
   docker-compose logs -f backend | grep -i migration
   ```

4. **Keep Migration History Clean**
   - One logical change per migration
   - Clear, descriptive migration messages
   - Test rollback functionality

5. **Use Manual Migrations for Critical Deployments**
   - Run migrations in maintenance window
   - Verify success before deployment
   - Keep auto-migrations disabled during deployment

## Related Documentation

- [Alembic Documentation](https://alembic.sqlalchemy.org/)
- [Project Architecture](./architecture.md)
- [Database Schema](../backend/alembic/README.md)
- [Deployment Guide](./deployment.md)
