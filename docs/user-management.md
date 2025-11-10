# User Management Guide

**Last Updated:** November 9, 2025
**Status:** Active
**Applies to:** Org Archivist v0.1.0+

## Overview

This guide covers user account creation, management, and troubleshooting for the Org Archivist application. The authentication system uses PostgreSQL for user storage with bcrypt password hashing and session-based authentication.

## Table of Contents

1. [Creating Your First User](#creating-your-first-user)
2. [User Roles](#user-roles)
3. [Environment Setup](#environment-setup)
4. [Troubleshooting](#troubleshooting)
5. [Security Best Practices](#security-best-practices)

---

## Creating Your First User

### Prerequisites

- Docker containers running (`docker-compose up -d` or `docker compose up -d`)
- Backend container healthy and database migrations completed
- PostgreSQL database accessible

### Method 1: Interactive Creation (Recommended)

The safest method that prompts for credentials without storing them:

```bash
# From project root
docker exec -it org-archivist-backend python scripts/create_user.py
```

You'll be prompted for:
- **Email:** Your login email address
- **Password:** Secure password (hidden input)
- **Full Name:** Your display name
- **Role:** admin, editor, or writer (defaults to admin)

**Example Output:**
```
Creating user account for Org Archivist...
============================================================
Enter email: user@example.com
Enter password: [hidden]
Enter full name: John Doe

✓ User account created successfully!

  Email: user@example.com
  Name: John Doe
  Role: UserRole.ADMIN
  User ID: 550e8400-e29b-41d4-a716-446655440000
  Created: 2025-11-09 12:00:00

  Use the email and password you provided to log in.

============================================================
You can now login to the Streamlit frontend with these credentials.
```

### Method 2: Environment Variables (Automation)

For scripting or CI/CD pipelines where interactive input isn't possible:

```bash
docker exec \
  -e USER_EMAIL=admin@example.com \
  -e USER_PASSWORD=SecurePassword123! \
  -e USER_FULL_NAME="Admin User" \
  -e USER_ROLE=admin \
  org-archivist-backend python scripts/create_user.py
```

**⚠️ Security Warning:** Never commit scripts or configuration files containing these environment variables to version control.

### Method 3: Direct Database Access (Advanced)

Only use this for troubleshooting or password resets:

```bash
# Connect to PostgreSQL
docker exec -it org-archivist-postgres psql -U user -d org_archivist

# Check existing users
SELECT user_id, email, full_name, role, is_active, created_at FROM users;

# Update user password (requires hashed password from Python)
# DO NOT use this method for password creation - use scripts instead
```

---

## User Roles

The system supports three user roles with different permission levels:

### Admin (`UserRole.ADMIN`)
- **Permissions:** Full system access
- **Can:**
  - Create, read, update, delete all resources
  - Manage other users (future feature)
  - Access system configuration
  - View audit logs
  - Manage writing styles and templates
- **Use case:** System administrators, project owners

### Editor (`UserRole.EDITOR`)
- **Permissions:** Content creation and management
- **Can:**
  - Create and edit documents
  - Generate outputs
  - Manage writing styles
  - View analytics
- **Cannot:**
  - Access system configuration
  - View full audit logs (only own actions)
- **Use case:** Content managers, editors

### Writer (`UserRole.WRITER`)
- **Permissions:** Basic content creation
- **Can:**
  - Create outputs using existing templates
  - View own documents and outputs
  - Use existing writing styles
- **Cannot:**
  - Create or modify writing styles
  - Access analytics dashboard
  - Manage system settings
- **Use case:** Content creators, contributors

---

## Environment Setup

### Database Connection

The user creation script uses the following database connection by default:

```
postgresql+asyncpg://user:password@postgres:5432/org_archivist
```

This works inside Docker containers. If running locally, override with:

```bash
export DATABASE_URL="postgresql+asyncpg://user:password@localhost:5432/org_archivist"
```

### Configuration Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_URL` | `postgresql+asyncpg://user:password@postgres:5432/org_archivist` | Database connection string (must use asyncpg driver) |
| `USER_EMAIL` | Interactive prompt | User email address |
| `USER_PASSWORD` | Interactive prompt | User password (plain text, will be hashed) |
| `USER_FULL_NAME` | Interactive prompt | User's full name |
| `USER_ROLE` | `admin` | User role: admin, editor, or writer |

---

## Troubleshooting

### Issue: "User already exists"

If a user with the email already exists:

```
✗ User with email user@example.com already exists!
  User ID: 550e8400-e29b-41d4-a716-446655440000
  Role: UserRole.ADMIN
  Created: 2025-11-09 12:00:00
```

**Solutions:**

1. **Use the existing account:** If you know the password, just log in
2. **Reset password:** Delete and recreate the user (see below)
3. **Use a different email:** Create a new user with a different email

**To delete a user:**
```bash
docker exec -it org-archivist-postgres psql -U user -d org_archivist

-- Check user details
SELECT user_id, email FROM users WHERE email = 'user@example.com';

-- Delete user sessions first
DELETE FROM user_sessions WHERE user_id = '<user-id-from-above>';

-- Delete user
DELETE FROM users WHERE email = 'user@example.com';

-- Verify deletion
SELECT * FROM users;
```

### Issue: "Connection refused" or "Database not found"

**Symptoms:**
```
Error: could not connect to server: Connection refused
```

**Solutions:**

1. **Verify containers are running:**
   ```bash
   docker ps --filter name=org-archivist
   ```

2. **Check backend logs:**
   ```bash
   docker logs org-archivist-backend --tail 50
   ```

3. **Verify database is healthy:**
   ```bash
   docker exec org-archivist-postgres psql -U user -d org_archivist -c "SELECT 1;"
   ```

4. **Check if migrations completed:**
   ```bash
   docker exec org-archivist-postgres psql -U user -d org_archivist -c "\dt"
   ```

### Issue: "Invalid credentials" (401 Error)

**Symptoms:**
```
Authentication failed: 401 Client Error: Unauthorized
```

**Common causes:**

1. **Wrong password:** Double-check the password (remember it's case-sensitive)
2. **User doesn't exist:** Verify user exists in database
3. **Account inactive:** Check `is_active` flag in database

**Verify user credentials:**
```bash
docker exec -it org-archivist-postgres psql -U user -d org_archivist

SELECT email, is_active, role FROM users WHERE email = 'your@email.com';
```

### Issue: Frontend shows "Connection refused"

**Symptoms:**
```
HTTPConnectionPool(host='backend', port=8000): Max retries exceeded
```

**Solutions:**

1. **Check API_BASE_URL environment variable:**
   ```bash
   docker exec org-archivist-frontend env | grep API_BASE_URL
   # Should show: API_BASE_URL=http://backend:8000
   ```

2. **Verify backend is running:**
   ```bash
   docker ps --filter name=org-archivist-backend
   curl http://localhost:8001/api/health
   ```

3. **Check docker-compose.yml has API_BASE_URL:**
   ```yaml
   frontend:
     environment:
       API_BASE_URL: ${BACKEND_URL:-http://backend:8000}
   ```

4. **Recreate frontend container:**
   ```bash
   docker compose up -d frontend
   ```

### Issue: "The asyncio extension requires an async driver"

**Symptoms:**
```
sqlalchemy.exc.InvalidRequestError: The asyncio extension requires an async driver
```

**Solution:**

The database URL must use `postgresql+asyncpg://` instead of `postgresql://`:

```python
# ✗ Wrong
DATABASE_URL = "postgresql://user:password@postgres:5432/org_archivist"

# ✓ Correct
DATABASE_URL = "postgresql+asyncpg://user:password@postgres:5432/org_archivist"
```

This is already fixed in the current version of `scripts/create_user.py`.

---

## Security Best Practices

### Password Requirements

While the system doesn't enforce these, we recommend:

- **Minimum length:** 12 characters
- **Complexity:** Mix of uppercase, lowercase, numbers, and symbols
- **Uniqueness:** Don't reuse passwords from other services
- **Avoid:** Common words, personal information, keyboard patterns

**Examples:**
- ✗ Weak: `password123`, `admin`, `qwerty`
- ✓ Strong: `Tr0pic@l-Sunr!se-2025`, `Quantum$Leap#42`

### Never Commit Credentials

The `.gitignore` file is configured to prevent credential leaks:

```gitignore
.env
.env.local
.env.*.local
*.env
.streamlit/secrets.toml
secrets/
```

**Always:**
- Use environment variables for automation
- Use interactive prompts for manual creation
- Store production credentials in secure vaults (e.g., AWS Secrets Manager, HashiCorp Vault)

**Never:**
- Hardcode credentials in Python scripts
- Commit `.env` files with real credentials
- Share credentials via chat or email
- Store credentials in version control

### Session Security

The application uses session-based authentication with:

- **Secure token generation:** Cryptographically secure random tokens
- **Token expiration:** Configurable timeout (default: 60 minutes)
- **Session invalidation:** Logout clears sessions from database
- **Password hashing:** bcrypt with automatic salt generation

### Production Recommendations

For production deployments:

1. **Use strong passwords:** Minimum 16 characters
2. **Enable HTTPS:** Set `CORS_ORIGINS` to HTTPS URLs only
3. **Rotate secrets:** Change `SECRET_KEY` regularly
4. **Limit admin accounts:** Create only necessary admin users
5. **Enable audit logging:** Review user actions regularly
6. **Database backups:** Regular automated backups
7. **Network isolation:** Use VPN or private networks for database access

---

## Quick Reference

### Common Commands

```bash
# Create user interactively
docker exec -it org-archivist-backend python scripts/create_user.py

# List all users
docker exec org-archivist-postgres psql -U user -d org_archivist \
  -c "SELECT email, full_name, role, is_active FROM users;"

# Check backend health
curl http://localhost:8001/api/health

# View backend logs
docker logs org-archivist-backend --tail 50 --follow

# Restart backend (after code changes)
docker restart org-archivist-backend

# Restart frontend (after config changes)
docker restart org-archivist-frontend
```

### File Locations

- **User creation script:** `/scripts/create_user.py`
- **Auth models:** `/backend/app/models/auth.py`
- **Auth service:** `/backend/app/services/auth_service.py`
- **Auth API endpoints:** `/backend/app/api/auth.py`
- **Database models:** `/backend/app/db/models.py`

---

## Related Documentation

- [Database Schema](database-schema.md) - User table schema and relationships
- [Auto Migrations](auto-migrations.md) - Database migration process
- [API Endpoint Verification](api-endpoint-verification.md) - Testing auth endpoints

---

## Support

If you encounter issues not covered in this guide:

1. Check backend logs: `docker logs org-archivist-backend --tail 100`
2. Verify database state: `docker exec -it org-archivist-postgres psql -U user -d org_archivist`
3. Review [Troubleshooting](#troubleshooting) section above
4. Open an issue on GitHub with logs and error messages
