# Docker Deployment Guide

**Last Updated:** 2025-11-16
**Status:** Active - Nuxt 4 Migration Complete

## Overview

This document provides comprehensive guidance for deploying Org Archivist using Docker and docker-compose. The application uses a multi-container architecture with production-optimized Dockerfiles for both frontend and backend services.

## Architecture

### Container Services

```
┌─────────────────────────────────────────────────────────────┐
│                    Docker Network                           │
│                 org-archivist-network                        │
│                                                              │
│  ┌──────────┐    ┌──────────┐    ┌─────────┐              │
│  │          │    │          │    │         │              │
│  │  Nuxt 4  │───▶│  FastAPI │───▶│ Postgres│              │
│  │ Frontend │    │  Backend │    │   DB    │              │
│  │  :3000   │    │  :8000   │    │  :5432  │              │
│  │          │    │          │    │         │              │
│  └──────────┘    └────┬─────┘    └─────────┘              │
│                       │                                     │
│                       │          ┌─────────┐              │
│                       └─────────▶│ Qdrant  │              │
│                                  │ Vector  │              │
│                                  │   DB    │              │
│                                  │ :6333   │              │
│                                  └─────────┘              │
└─────────────────────────────────────────────────────────────┘
```

### Service Ports

- **Frontend (Nuxt 4):** 3000
- **Backend (FastAPI):** 8000
- **PostgreSQL:** 5432
- **PostgreSQL Test:** 5433
- **Qdrant HTTP:** 6333
- **Qdrant gRPC:** 6334

## Frontend Migration: Streamlit → Nuxt 4

### Migration Summary

**Date:** 2025-11-16
**Reason:** Modern, performant, and scalable frontend framework with better TypeScript support and developer experience

### Changes Made

#### 1. Frontend Dockerfile (`frontend/Dockerfile`)

**Multi-stage Build Architecture:**

```dockerfile
# Stage 1: Build stage
FROM node:20-alpine as builder
WORKDIR /build
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build

# Stage 2: Production runtime
FROM node:20-alpine
WORKDIR /app
# ... install runtime dependencies
COPY --from=builder /build/.output ./.output
CMD ["node", ".output/server/index.mjs"]
```

**Key Features:**
- **Node 20 Alpine:** Minimal base image (~5x smaller than full Node image)
- **Multi-stage build:** Separates build tools from runtime (reduces final image size by ~60%)
- **Production dependencies only:** `npm ci --only=production` in runtime stage
- **Non-root user:** Security best practice with `appuser` (uid 1000)
- **Health check:** HTTP endpoint monitoring on port 3000
- **Optimized caching:** Proper layer ordering for faster rebuilds

#### 2. Docker Compose Configuration (`docker-compose.yml`)

**Before (Streamlit):**
```yaml
frontend:
  ports:
    - "8501:8501"
  environment:
    STREAMLIT_SERVER_PORT: 8501
    STREAMLIT_SERVER_ADDRESS: 0.0.0.0
  healthcheck:
    test: ["CMD-SHELL", "curl -f http://localhost:8501/_stcore/health || exit 1"]
```

**After (Nuxt 4):**
```yaml
frontend:
  ports:
    - "3000:3000"
  environment:
    NUXT_PUBLIC_API_BASE: http://backend:8000
    NUXT_PUBLIC_ENVIRONMENT: production
    NODE_ENV: production
    HOST: 0.0.0.0
    PORT: 3000
  healthcheck:
    test: ["CMD-SHELL", "curl -f http://localhost:3000/ || exit 1"]
  volumes:
    # Development hot reload (comment out for production)
    - ./frontend:/app
    - /app/node_modules
    - /app/.nuxt
    - /app/.output
```

#### 3. Environment Configuration (`.env.example`)

**Updated Variables:**
- `FRONTEND_PORT`: 8501 → **3000**
- `CORS_ORIGINS`: `http://localhost:8501` → **`http://localhost:3000`**

#### 4. Build Optimization (`.dockerignore`)

Created `frontend/.dockerignore` to exclude:
- `node_modules/` - Rebuilt in container
- `.nuxt/`, `.output/` - Build artifacts
- `.env`, `.env.*` - Secrets
- Development files (README, docs, IDE configs)

**Impact:** ~50-70% reduction in build context size

## Deployment Workflows

### Development Deployment

The project provides two approaches for development:

#### Option 1: Dedicated Development Containers (Recommended)

Uses `Dockerfile.dev` files optimized for development with hot reload:

**Quick Start:**
```bash
# 1. Copy environment template
cp .env.example .env

# 2. Configure environment variables
# Edit .env with your API keys and settings

# 3. Start all services using development configuration
docker-compose -f docker-compose.dev.yml up

# 4. View logs
docker-compose -f docker-compose.dev.yml logs -f frontend
docker-compose -f docker-compose.dev.yml logs -f backend

# 5. Access application
# Frontend: http://localhost:3000
# Backend API: http://localhost:8000
# API Docs: http://localhost:8000/docs
```

**Key Features:**
- **Frontend** (`frontend/Dockerfile.dev`):
  - Uses `npm install` instead of `npm ci` for easier dependency updates
  - Runs `npm run dev` for hot module replacement
  - Source code mounted via volume for instant reload
  - Debug mode enabled with verbose logging

- **Backend** (`backend/Dockerfile.dev`):
  - Uvicorn runs with `--reload` flag for auto-restart
  - Source code mounted via volume for instant reload
  - Debug logging enabled
  - Development environment variables set

**Rebuilding After Dependency Changes:**
```bash
# Rebuild specific service
docker-compose -f docker-compose.dev.yml build frontend
docker-compose -f docker-compose.dev.yml build backend

# Rebuild and restart
docker-compose -f docker-compose.dev.yml up --build
```

#### Option 2: Production Containers with Volume Mounts

Uses production Dockerfiles with volume mounts (legacy approach):

```bash
# Frontend changes auto-reload (volumes mounted)
# Backend changes auto-reload (volumes mounted)
docker-compose up

# To rebuild after dependency changes:
docker-compose up --build
```

**Note:** This approach uses the production multi-stage builds but mounts volumes for development. Option 1 is preferred for a more optimized development experience.

### Production Deployment

**Production Build:**
```bash
# 1. Set production environment variables
export ENVIRONMENT=production
export DEBUG=false
export ENABLE_AUTH=true

# 2. Build optimized images
docker-compose build --no-cache

# 3. Start services in detached mode
docker-compose up -d

# 4. Verify health
docker-compose ps
```

**Production Checklist:**
- [ ] Set `ENVIRONMENT=production`
- [ ] Set `DEBUG=false`
- [ ] Set `ENABLE_AUTH=true`
- [ ] Configure strong `SECRET_KEY`
- [ ] Set production `CORS_ORIGINS`
- [ ] Configure API keys
- [ ] Enable log rotation
- [ ] Set up monitoring
- [ ] Configure SSL/TLS termination (reverse proxy)

### Individual Service Management

**Frontend Only:**
```bash
# Build
docker-compose build frontend

# Start
docker-compose up frontend

# Restart
docker-compose restart frontend

# View logs
docker-compose logs -f frontend

# Shell access
docker-compose exec frontend sh
```

**Backend Only:**
```bash
# Build
docker-compose build backend

# Start (with dependencies)
docker-compose up backend

# Run migrations
docker-compose exec backend alembic upgrade head

# Shell access
docker-compose exec backend bash
```

## Service Dependencies

### Dependency Graph

```
frontend ──depends_on──> backend (healthy)
                           │
                           ├──depends_on──> postgres (healthy)
                           │
                           └──depends_on──> qdrant (started)
```

### Health Checks

**Backend Health Check:**
- Endpoint: `http://localhost:8000/api/health`
- Interval: 30s
- Timeout: 10s
- Start period: 40s
- Retries: 3

**Frontend Health Check:**
- Endpoint: `http://localhost:3000/`
- Interval: 30s
- Timeout: 10s
- Start period: 40s
- Retries: 3

**PostgreSQL Health Check:**
- Command: `pg_isready -U user -d org_archivist`
- Interval: 10s
- Start period: 10s

## Volume Management

### Named Volumes

```yaml
volumes:
  postgres_data:           # PostgreSQL production data
  postgres_test_data:      # PostgreSQL test data
  qdrant_storage:          # Qdrant vector storage
```

**Backup Volumes:**
```bash
# Export PostgreSQL data
docker-compose exec postgres pg_dump -U user org_archivist > backup.sql

# Export Qdrant data
docker-compose exec qdrant tar -czf - /qdrant/storage > qdrant-backup.tar.gz
```

**Restore Volumes:**
```bash
# Restore PostgreSQL
cat backup.sql | docker-compose exec -T postgres psql -U user -d org_archivist

# Restore Qdrant
docker-compose exec -T qdrant tar -xzf - -C / < qdrant-backup.tar.gz
```

### Development Volumes

```yaml
# Frontend (mounted for hot reload)
- ./frontend:/app
- /app/node_modules    # Exclude from host mount
- /app/.nuxt           # Exclude from host mount
- /app/.output         # Exclude from host mount

# Backend (mounted for hot reload)
- ./backend/app:/app/app
- ./data/documents:/app/documents
- ./logs:/app/logs
```

**Production Note:** Remove development volume mounts for production deployment to use only the built image contents.

## Log Management

### Docker-Level Log Rotation

**Configuration:**
```yaml
logging:
  driver: "json-file"
  options:
    max-size: "10m"      # Max 10MB per log file
    max-file: "5"        # Keep 5 files (50MB total)
    compress: "true"     # Compress rotated logs
```

**View Logs:**
```bash
# All services
docker-compose logs

# Specific service with follow
docker-compose logs -f frontend

# Last 100 lines
docker-compose logs --tail=100 backend

# Since timestamp
docker-compose logs --since="2025-11-16T10:00:00"
```

## Troubleshooting

### Frontend Won't Start

**Symptom:** Frontend container exits immediately

**Check:**
```bash
# View build output
docker-compose build frontend --no-cache

# Check logs
docker-compose logs frontend

# Inspect filesystem
docker-compose run --rm frontend ls -la .output
```

**Common Issues:**
- Missing `.output` directory → Build failed, check `npm run build` output
- Port already in use → Check `lsof -i :3000`
- Missing dependencies → Run `npm ci` in build stage

### Backend Connection Issues

**Symptom:** Frontend can't connect to backend

**Check:**
```bash
# Verify backend health
curl http://localhost:8000/api/health

# Check backend logs
docker-compose logs backend

# Test from frontend container
docker-compose exec frontend curl http://backend:8000/api/health
```

**Common Issues:**
- Wrong `NUXT_PUBLIC_API_BASE` → Should be `http://backend:8000` for container-to-container
- CORS not configured → Check `CORS_ORIGINS` includes frontend URL
- Backend not healthy → Check postgres connection

### Database Migration Issues

**Symptom:** Backend fails with database errors

**Solution:**
```bash
# Check migration status
docker-compose exec backend alembic current

# View migration history
docker-compose exec backend alembic history

# Run migrations manually
docker-compose exec backend alembic upgrade head

# Rollback if needed
docker-compose exec backend alembic downgrade -1
```

See [auto-migrations.md](auto-migrations.md) for detailed migration troubleshooting.

### Container Resource Issues

**Symptom:** Containers running slowly or OOM killed

**Check Resource Usage:**
```bash
# View container stats
docker stats

# Check container resource limits
docker-compose config
```

**Increase Resources:**
```yaml
# In docker-compose.yml
services:
  backend:
    deploy:
      resources:
        limits:
          cpus: '2'
          memory: 2G
        reservations:
          cpus: '1'
          memory: 1G
```

## Performance Optimization

### Image Size Optimization

**Current Sizes (approximate):**
- Backend: ~180MB (Python 3.11-slim + dependencies)
- Frontend: ~150MB (Node 20-alpine + production build)
- PostgreSQL: ~230MB (postgres:15-alpine)
- Qdrant: ~200MB (qdrant/qdrant:latest)

**Optimization Techniques Used:**
1. **Alpine base images** - Minimal OS layer
2. **Multi-stage builds** - Separate build and runtime
3. **Production dependencies only** - No dev dependencies in final image
4. **Layer caching** - Order Dockerfile commands for optimal caching
5. **.dockerignore** - Reduce build context size

### Build Cache Optimization

**Best Practices:**
```dockerfile
# 1. Copy dependency files first (changes less frequently)
COPY package*.json ./
RUN npm ci

# 2. Copy source code last (changes most frequently)
COPY . .
RUN npm run build
```

**Result:** Dependency layers cached, only rebuild when package.json changes

### Runtime Optimization

**Frontend:**
- Server-side rendering with Nuxt
- Static asset optimization
- Compression enabled
- Production mode (`NODE_ENV=production`)

**Backend:**
- Uvicorn with production settings
- Connection pooling for PostgreSQL
- Query result caching
- Gzip compression

## Security Considerations

### Non-Root Users

Both containers run as non-root users (uid 1000):

```dockerfile
RUN adduser -D -u 1000 appuser
USER appuser
```

**Benefit:** Limits potential damage from container breakout vulnerabilities

### Secret Management

**DO NOT:**
- Commit `.env` to version control
- Include secrets in Dockerfile
- Hardcode API keys in docker-compose.yml

**DO:**
- Use `.env` file (excluded by `.gitignore`)
- Use Docker secrets for production
- Rotate secrets regularly

### Network Isolation

**Configuration:**
```yaml
networks:
  org-archivist-network:
    driver: bridge
```

**Benefit:** Services isolated from host network and other Docker networks

### Image Scanning

**Recommended:**
```bash
# Scan for vulnerabilities
docker scan org-archivist-backend
docker scan org-archivist-frontend

# Or use trivy
trivy image org-archivist-backend
```

## Migration Notes

### Migrating from Streamlit to Nuxt 4

If upgrading an existing deployment:

1. **Backup data volumes:**
   ```bash
   docker-compose down
   docker-compose exec postgres pg_dump -U user org_archivist > backup.sql
   ```

2. **Update configuration:**
   ```bash
   # Update .env file
   sed -i 's/FRONTEND_PORT=8501/FRONTEND_PORT=3000/' .env
   sed -i 's/localhost:8501/localhost:3000/g' .env
   ```

3. **Remove old frontend container and image:**
   ```bash
   docker-compose rm -f frontend
   docker rmi org-archivist-frontend
   ```

4. **Build and start new frontend:**
   ```bash
   docker-compose build frontend
   docker-compose up -d frontend
   ```

5. **Verify:**
   ```bash
   docker-compose ps
   curl http://localhost:3000/
   ```

## Related Documentation

- **[nuxt4-setup.md](nuxt4-setup.md)** - Nuxt 4 development setup and configuration
- **[nuxt4-implementation-risks.md](nuxt4-implementation-risks.md)** - Migration risks and mitigation strategies
- **[auto-migrations.md](auto-migrations.md)** - Database migration management
- **[backend-api-guide.md](backend-api-guide.md)** - Backend API documentation

## Future Enhancements

### Planned Improvements

1. **Kubernetes Deployment** - Helm charts for k8s orchestration
2. **Multi-stage Testing** - Test stage in Dockerfile
3. **Image Registry** - Push to private registry
4. **Auto-scaling** - Horizontal pod autoscaling
5. **Blue-Green Deployment** - Zero-downtime updates
6. **Monitoring** - Prometheus + Grafana integration
7. **Distributed Tracing** - OpenTelemetry integration

### Considerations

- **ARM Support:** Add multi-platform builds for ARM64 (Apple Silicon, AWS Graviton)
- **Development Containers:** VS Code devcontainer configuration
- **CI/CD Integration:** Automated builds and deployments

## Support

For issues or questions:

1. Check logs: `docker-compose logs [service]`
2. Review health status: `docker-compose ps`
3. Consult related documentation
4. Check GitHub issues

## Changelog

### 2025-11-16 - Development Dockerfiles
- Created dedicated development Dockerfiles for optimized dev workflow
  - `frontend/Dockerfile.dev` - Nuxt 4 with hot reload and npm install
  - `backend/Dockerfile.dev` - FastAPI with uvicorn --reload
- Created `docker-compose.dev.yml` for complete development environment
- Updated documentation with development deployment workflows
- Development containers use separate volumes from production
- Enhanced CORS configuration for development (includes localhost:5173)

### 2025-11-16 - Nuxt 4 Migration
- Migrated frontend from Streamlit to Nuxt 4
- Created multi-stage production Dockerfile for frontend
- Updated docker-compose.yml configuration
- Changed default port from 8501 → 3000
- Added frontend/.dockerignore for build optimization
- Updated environment configuration and CORS settings

### Earlier
- Initial Docker setup with Streamlit frontend
- Backend FastAPI multi-stage Dockerfile
- PostgreSQL and Qdrant integration
- Health check implementation
- Log rotation configuration
