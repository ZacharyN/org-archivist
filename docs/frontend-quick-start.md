# Frontend Development Quick Start

This guide helps frontend developers get started with the Org Archivist Nuxt 4 frontend development.

## Quick Links

### Essential Documentation
1. **[nuxt4-setup.md](nuxt4-setup.md)** - Nuxt 4 installation and configuration
2. **[backend-api-guide.md](backend-api-guide.md)** - Complete backend API reference
3. **[nuxt4-implementation-risks.md](nuxt4-implementation-risks.md)** - Important risks and mitigation strategies
4. **[/context/frontend-requirements.md](../context/frontend-requirements.md)** - Detailed frontend specifications

### Supporting Documentation
- **[docker-deployment.md](docker-deployment.md)** - Docker setup for local development
- **[user-management.md](user-management.md)** - User account creation for testing
- **[database-schema.md](database-schema.md)** - Database structure reference

## Development Environment Setup

### Prerequisites
- Docker and Docker Compose
- Node.js 18+ (for local development outside Docker)
- Basic familiarity with Vue 3 and TypeScript

### Quick Start (Docker Development)

```bash
# 1. Clone repository
git clone https://github.com/zacharyr0th/org-archivist.git
cd org-archivist

# 2. Configure environment
cp .env.example .env
# Edit .env with your settings (see backend-api-guide.md for required variables)

# 3. Start development environment with hot reload
docker-compose -f docker-compose.dev.yml up

# Frontend will be available at: http://localhost:3000
# Backend API at: http://localhost:8000
# API Documentation: http://localhost:8000/docs
```

### Project Structure

```
frontend/
├── pages/              # Vue pages (file-based routing)
├── components/         # Reusable Vue components
├── composables/        # Composable functions
├── layouts/            # Page layouts
├── types/              # TypeScript type definitions
├── app.vue             # Root application component
└── nuxt.config.ts      # Nuxt configuration
```

## Backend API Integration

### API Base URL
- **Development:** `http://localhost:8000`
- **Production:** Configure via environment variable

### Authentication
The backend uses JWT-based authentication. See **[backend-api-guide.md](backend-api-guide.md)** for:
- Login/registration endpoints
- Token management
- Protected route patterns

### Key API Endpoints

#### Authentication
- `POST /api/v1/auth/register` - User registration
- `POST /api/v1/auth/login` - User login
- `POST /api/v1/auth/logout` - User logout

#### Documents
- `GET /api/v1/documents/` - List user's documents
- `POST /api/v1/documents/upload` - Upload new document
- `GET /api/v1/documents/{id}` - Get document details
- `DELETE /api/v1/documents/{id}` - Delete document

#### Outputs (Generated Content)
- `POST /api/v1/outputs/generate` - Generate content
- `GET /api/v1/outputs/` - List user's outputs
- `GET /api/v1/outputs/{id}` - Get output details

#### Prompt Templates & Writing Styles
- `GET /api/v1/prompt-templates/` - List templates
- `GET /api/v1/writing-styles/` - List writing styles

**Full API documentation:** http://localhost:8000/docs (when backend is running)

## Development Workflow

### 1. Create a Feature Branch
```bash
git checkout -b feature/your-feature-name
```

### 2. Develop with Hot Reload
The development Docker setup automatically reloads on code changes.

### 3. API Testing
Use the interactive API docs at http://localhost:8000/docs to:
- Test endpoints
- View request/response schemas
- Generate test data

### 4. Commit Frequently
Follow the commit guidelines in `/CLAUDE.md`:
```bash
git add components/MyComponent.vue
git commit -m "feat(components): add MyComponent for feature X"
```

## Common Tasks

### Creating a New Page
```bash
# Pages use file-based routing
# Create: frontend/pages/my-page.vue
# Access at: http://localhost:3000/my-page
```

### Fetching Data from Backend
```typescript
// Use Nuxt's composables for data fetching
const { data, error } = await useFetch('/api/v1/documents/')
```

### Handling Authentication
See `composables/useAuth.ts` for authentication helpers (to be implemented).

## Important Considerations

### Nuxt 4 Risks
Review **[nuxt4-implementation-risks.md](nuxt4-implementation-risks.md)** for:
- Nuxt UI stability concerns
- TypeScript configuration
- SSR vs. client-side rendering decisions

### API Versioning
The backend uses versioned APIs (`/api/v1/`). Always use the versioned endpoints to ensure compatibility.

### CORS Configuration
The backend is configured to accept requests from `http://localhost:3000` in development. See `backend/app/config.py` for CORS settings.

## Testing

### Local Testing
```bash
# Test API connectivity
curl http://localhost:8000/api/v1/health

# Test authenticated endpoint (requires token)
curl -H "Authorization: Bearer YOUR_TOKEN" http://localhost:8000/api/v1/documents/
```

### Creating Test Users
See **[user-management.md](user-management.md)** for creating test accounts.

## Getting Help

1. **API Questions:** Check **[backend-api-guide.md](backend-api-guide.md)**
2. **Setup Issues:** Review **[docker-deployment.md](docker-deployment.md)**
3. **Requirements:** See **[/context/frontend-requirements.md](../context/frontend-requirements.md)**
4. **Architecture:** Review **[/context/architecture.md](../context/architecture.md)**

## Next Steps

1. Read **[nuxt4-setup.md](nuxt4-setup.md)** for detailed Nuxt configuration
2. Review **[backend-api-guide.md](backend-api-guide.md)** for API details
3. Check **[/context/frontend-requirements.md](../context/frontend-requirements.md)** for feature specifications
4. Start building! Begin with authentication and document listing pages

---

**Last Updated:** 2025-11-16
**Status:** Active Development - MVP Phase
