# Authentication Development Strategy

**Document Version:** 1.0
**Last Updated:** 2025-11-11
**Status:** Active

## Overview

This document outlines the authentication strategy for the Org Archivist project during frontend development and the path to production deployment.

## Current Configuration

### Development Phase
- **ENABLE_AUTH**: `false`
- **SECRET_KEY**: Generated and configured in `.env` (not committed to version control)
- **Rationale**: Rapid frontend prototyping without authentication overhead

## Decision: Start with Authentication Disabled

### Why This Approach?

**Option A: ENABLE_AUTH=false (SELECTED)**
- ✅ Faster initial development
- ✅ Focus on UI/UX implementation first
- ✅ Test API responses and data flows without token management
- ✅ Iterate quickly on frontend features
- ✅ Lower barrier for frontend developers
- ⚠️ Authentication flow tested separately later

**Option B: ENABLE_AUTH=true (Alternative)**
- ✅ More realistic production-like environment
- ✅ Tests authentication early in development
- ✅ Catches auth-related issues sooner
- ⚠️ Slower initial setup
- ⚠️ Adds complexity to every API call during prototyping

### When Selected Option A

We chose **Option A** because:
1. **Nuxt 4 frontend is new** - Team needs to focus on learning the framework and building UI components
2. **Backend authentication is already implemented** - The JWT-based auth system is complete and tested
3. **Phased approach reduces complexity** - Separate frontend implementation from auth integration
4. **Faster feedback loops** - UI changes can be tested immediately without login flow

## Development Phases

### Phase 1: Initial Frontend Development (Current Phase)
**Configuration:**
```bash
ENABLE_AUTH=false
```

**Activities:**
- Build Nuxt 4 components and pages
- Implement API client without auth headers
- Test data flows and UI interactions
- Develop layouts, navigation, and forms
- Focus on user experience and visual design

**API Access:**
- All endpoints accessible without Bearer token
- No login/logout flow required
- Direct API calls to test functionality

### Phase 2: Authentication Integration
**Configuration:**
```bash
ENABLE_AUTH=true
SECRET_KEY=<generated-secure-key>
```

**Activities:**
- Implement login/logout UI components
- Add JWT token storage (cookies or localStorage)
- Create auth middleware for protected routes
- Add Authorization header to API client
- Implement session refresh logic
- Test role-based access control (RBAC)

**Testing Checklist:**
- [ ] User registration flow
- [ ] Login with valid credentials
- [ ] Login with invalid credentials
- [ ] Logout and session cleanup
- [ ] Token expiration handling
- [ ] Protected route access control
- [ ] Role-based permission checks (admin, editor, writer)
- [ ] Session timeout and refresh

### Phase 3: Production Deployment
**Configuration:**
```bash
ENABLE_AUTH=true
SECRET_KEY=<strong-production-secret>
SESSION_TIMEOUT_MINUTES=60
CORS_ORIGINS=https://app.orgarchivist.com
```

**Security Requirements:**
- Strong SECRET_KEY (32+ character random string)
- HTTPS only (no HTTP in production)
- Secure cookie configuration
- Rate limiting on auth endpoints
- Proper CORS configuration
- Regular security audits

## Configuration Changes

### Transitioning to Auth-Enabled Mode

1. **Update Environment Variable**
   ```bash
   # In .env file
   ENABLE_AUTH=true
   ```

2. **Verify SECRET_KEY**
   ```bash
   # Ensure SECRET_KEY is set to a strong random value
   # Generate new key if needed:
   python -c "import secrets; print(secrets.token_urlsafe(32))"
   ```

3. **Restart Backend**
   ```bash
   docker-compose restart backend
   # or
   docker-compose up -d backend
   ```

4. **Update Frontend API Client**
   ```typescript
   // Add auth interceptor to add Authorization header
   // Store and manage JWT tokens
   // Handle 401 Unauthorized responses
   ```

## Backend Authentication System

### Already Implemented Features
- JWT token generation and validation
- Bcrypt password hashing
- Session management with PostgreSQL
- Role-based access control (RBAC)
- Token refresh capability
- Session expiration and cleanup

### Endpoints (Available when ENABLE_AUTH=true)
- `POST /api/auth/register` - Create new user account
- `POST /api/auth/login` - Authenticate and receive tokens
- `POST /api/auth/logout` - Invalidate session
- `GET /api/auth/session` - Validate current session
- `GET /api/auth/me` - Get current user details

### Role Hierarchy
1. **Admin** (Level 3) - Full system access
2. **Editor** (Level 2) - Content management
3. **Writer** (Level 1) - Content creation only

See `backend-api-guide.md` section 2.4 for complete RBAC details.

## Security Considerations

### Development (ENABLE_AUTH=false)
- Only use in local development environment
- Never expose publicly without authentication
- Development database should use test/dummy data
- No production API keys in development

### Production (ENABLE_AUTH=true)
- HTTPS required
- Strong SECRET_KEY (never commit to git)
- Rate limiting on authentication endpoints
- Monitor failed login attempts
- Regular security audits
- Session timeout enforcement
- Secure cookie configuration (httpOnly, secure, sameSite)

## Testing Strategy

### Without Authentication (Current Phase)
```bash
# Direct API calls without Bearer token
curl http://localhost:8000/api/documents

# Frontend can directly call API
fetch('http://localhost:8000/api/documents')
```

### With Authentication (Phase 2)
```bash
# Login first
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "user@example.com", "password": "password"}'

# Use returned token
curl http://localhost:8000/api/documents \
  -H "Authorization: Bearer eyJhbGci..."
```

## Common Issues & Solutions

### Issue: Backend returns 401 when ENABLE_AUTH=true
**Solution:** Ensure frontend sends Authorization header with valid JWT token

### Issue: Token expired error
**Solution:** Implement token refresh logic in frontend or prompt user to login again

### Issue: CORS errors after enabling auth
**Solution:** Verify CORS_ORIGINS includes frontend URL in .env

### Issue: Can't test auth endpoints with ENABLE_AUTH=false
**Solution:** Temporarily set ENABLE_AUTH=true and restart backend

## References

- **Backend API Guide**: `/docs/backend-api-guide.md` (Section 2: Authentication & Authorization)
- **Environment Configuration**: `/.env.example`
- **Auth Middleware**: `/backend/app/middleware/auth.py`
- **Auth Service**: `/backend/app/services/auth_service.py`

## Timeline

| Phase | Duration | Status |
|-------|----------|--------|
| Phase 1: Frontend Development (Auth Disabled) | 2-3 weeks | ✅ Current |
| Phase 2: Authentication Integration | 3-5 days | ⏳ Upcoming |
| Phase 3: Production Deployment | Ongoing | ⏳ Future |

## Decision Log

| Date | Decision | Rationale |
|------|----------|-----------|
| 2025-11-11 | Start with ENABLE_AUTH=false | Enable rapid frontend prototyping without auth complexity |
| 2025-11-11 | Generate and set secure SECRET_KEY | Prepare for future auth enablement, good security practice |

## Next Steps

1. ✅ Configure ENABLE_AUTH=false for development
2. ✅ Generate and set SECRET_KEY
3. ✅ Document authentication strategy
4. ⏳ Build frontend UI components without auth
5. ⏳ Implement authentication UI (Phase 2)
6. ⏳ Integrate auth with API client (Phase 2)
7. ⏳ Test complete auth flow (Phase 2)

## Contact

For questions about authentication strategy or implementation:
- Review `/docs/backend-api-guide.md` Section 2
- Check this document for configuration guidance
- Test endpoints at `http://localhost:8000/docs` (Swagger UI)
