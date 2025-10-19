# Development Setup Guide

This guide will help you set up the Org Archivist development environment on your local machine.

## Table of Contents

- [Prerequisites](#prerequisites)
- [Quick Start](#quick-start)
- [Detailed Setup](#detailed-setup)
- [Running the Application](#running-the-application)
- [Verification & Testing](#verification--testing)
- [Development Workflow](#development-workflow)
- [Troubleshooting](#troubleshooting)
- [Advanced Configuration](#advanced-configuration)

---

## Prerequisites

Before you begin, ensure you have the following installed:

### Required Software

| Software | Minimum Version | Purpose | Installation |
|----------|----------------|---------|--------------|
| **Docker** | 20.10+ | Container runtime | [Get Docker](https://docs.docker.com/get-docker/) |
| **Docker Compose** | 2.0+ | Multi-container orchestration | Included with Docker Desktop |
| **Python** | 3.10+ | Backend development | [Python.org](https://www.python.org/downloads/) |
| **Git** | 2.30+ | Version control | [Git-SCM.com](https://git-scm.com/) |

### Recommended Software

- **Visual Studio Code** or **PyCharm** - IDE with Python support
- **Postman** or **Insomnia** - API testing
- **Docker Desktop** - GUI for Docker management

### API Keys

You'll need API keys for the following services:

- **Anthropic API Key** (required) - [Get API Key](https://console.anthropic.com/)
- **OpenAI API Key** (optional) - Only if using OpenAI embeddings
- **Voyage AI API Key** (optional) - Only if using Voyage embeddings

---

## Quick Start

For experienced developers who want to get started quickly:

```bash
# 1. Clone the repository
git clone https://github.com/yourusername/org-archivist.git
cd org-archivist

# 2. Copy environment file
cp env.example .env

# 3. Edit .env and add your API keys
# Required: ANTHROPIC_API_KEY
# Optional: OPENAI_API_KEY, VOYAGE_API_KEY

# 4. Start services
docker-compose up -d

# 5. Initialize Qdrant collection (once backend is ready)
python docker/qdrant/scripts/init_collection.py

# 6. Access the application
# - Backend API: http://localhost:8000
# - Frontend UI: http://localhost:8501
# - Qdrant Dashboard: http://localhost:6333/dashboard
```

---

## Detailed Setup

### Step 1: Clone the Repository

```bash
git clone https://github.com/yourusername/org-archivist.git
cd org-archivist
```

### Step 2: Create Environment File

Copy the example environment file and customize it:

```bash
cp env.example .env
```

**Windows (PowerShell):**
```powershell
Copy-Item env.example .env
```

### Step 3: Configure Environment Variables

Open `.env` in your favorite text editor and configure the following:

#### Required Variables

```bash
# Anthropic API Key (required)
ANTHROPIC_API_KEY=sk-ant-your-actual-api-key-here
```

#### Embedding Configuration

Choose your embedding provider:

**Option A: Local Embeddings (Free, No API Key Required)**
```bash
EMBEDDING_PROVIDER=local
EMBEDDING_MODEL=bge-large-en-v1.5
EMBEDDING_DIMENSIONS=1024
```

**Option B: OpenAI Embeddings**
```bash
EMBEDDING_PROVIDER=openai
EMBEDDING_MODEL=text-embedding-3-small
EMBEDDING_DIMENSIONS=1536
OPENAI_API_KEY=sk-your-openai-key-here
```

**Option C: Voyage AI Embeddings**
```bash
EMBEDDING_PROVIDER=voyage
EMBEDDING_MODEL=voyage-large-2
EMBEDDING_DIMENSIONS=1536
VOYAGE_API_KEY=pa-your-voyage-key-here
```

#### Database Configuration

The default values work for local development:

```bash
POSTGRES_USER=user
POSTGRES_PASSWORD=password
POSTGRES_DB=org_archivist
```

**For production, use strong passwords!**

### Step 4: Verify Docker Installation

Check that Docker is running:

```bash
docker --version
docker-compose --version
```

Expected output:
```
Docker version 24.0.0 or higher
Docker Compose version 2.20.0 or higher
```

---

## Running the Application

### Start All Services

```bash
# Start all services in detached mode (background)
docker-compose up -d

# Or start with logs visible
docker-compose up
```

### Start Individual Services

```bash
# Start only database services
docker-compose up -d postgres qdrant

# Start backend only (requires databases)
docker-compose up -d backend

# Start frontend only (requires backend)
docker-compose up -d frontend
```

### Stop Services

```bash
# Stop all services
docker-compose down

# Stop and remove volumes (deletes all data!)
docker-compose down -v
```

### View Logs

```bash
# View all logs
docker-compose logs

# View specific service logs
docker-compose logs backend
docker-compose logs frontend
docker-compose logs postgres
docker-compose logs qdrant

# Follow logs in real-time
docker-compose logs -f backend
```

### Service Initialization

After starting services for the first time:

1. **PostgreSQL** initializes automatically using `docker/postgres/init/01-init-database.sql`
2. **Qdrant** requires manual collection initialization (see below)

#### Initialize Qdrant Collection

**Method 1: Run script directly (if qdrant-client installed)**

```bash
pip install qdrant-client
python docker/qdrant/scripts/init_collection.py
```

**Method 2: Run from backend container**

```bash
docker exec -it org-archivist-backend python /app/scripts/init_collection.py
```

**Method 3: Automatic (backend handles it)**

The backend application should automatically initialize the collection on first startup.

---

## Verification & Testing

### Check Service Health

#### 1. Check Docker Containers

```bash
docker ps
```

All services should show status "Up" and be healthy:
```
NAME                      STATUS
org-archivist-postgres    Up (healthy)
org-archivist-qdrant      Up (healthy)
org-archivist-backend     Up (healthy)
org-archivist-frontend    Up (healthy)
```

#### 2. Test PostgreSQL

```bash
# Connect to PostgreSQL
docker exec -it org-archivist-postgres psql -U user -d org_archivist

# Run a test query
SELECT COUNT(*) FROM documents;

# Exit PostgreSQL
\q
```

#### 3. Test Qdrant

```bash
# Health check
curl http://localhost:6333/health

# List collections
curl http://localhost:6333/collections

# Or visit dashboard
open http://localhost:6333/dashboard  # macOS
start http://localhost:6333/dashboard  # Windows
```

#### 4. Test Backend API

```bash
# Health check
curl http://localhost:8000/api/health

# API documentation
open http://localhost:8000/docs  # macOS
start http://localhost:8000/docs  # Windows
```

#### 5. Test Frontend

Visit http://localhost:8501 in your browser.

### Run Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=backend

# Run specific test file
pytest tests/test_document_processor.py

# Run with verbose output
pytest -v
```

---

## Development Workflow

### Making Code Changes

1. **Backend Changes** (Python/FastAPI)
   - Edit files in `backend/`
   - Backend auto-reloads when files change (if `ENABLE_HOT_RELOAD=true`)
   - Check logs: `docker-compose logs -f backend`

2. **Frontend Changes** (Streamlit)
   - Edit files in `frontend/`
   - Streamlit auto-reloads on file changes
   - Check logs: `docker-compose logs -f frontend`

3. **Database Schema Changes**
   - Edit `docker/postgres/init/01-init-database.sql`
   - Recreate database: `docker-compose down -v && docker-compose up -d`
   - **OR** use migrations (Alembic) - see Advanced section

### Adding Dependencies

**Backend (Python):**

```bash
# Add to requirements.txt
echo "new-package==1.0.0" >> backend/requirements.txt

# Rebuild backend container
docker-compose build backend
docker-compose up -d backend
```

**Frontend (Python):**

```bash
# Add to requirements.txt
echo "new-package==1.0.0" >> frontend/requirements.txt

# Rebuild frontend container
docker-compose build frontend
docker-compose up -d frontend
```

### Database Management

**Backup Database:**

```bash
docker exec org-archivist-postgres pg_dump -U user org_archivist > backup.sql
```

**Restore Database:**

```bash
docker exec -i org-archivist-postgres psql -U user org_archivist < backup.sql
```

**Reset Database:**

```bash
docker-compose down -v
docker-compose up -d postgres
# Database will be recreated from init script
```

### Working with Qdrant

**View Collections:**

Visit http://localhost:6333/dashboard

**Reset Collection:**

```bash
python docker/qdrant/scripts/init_collection.py
# Select 'y' when prompted to recreate
```

**Backup Qdrant Data:**

```bash
docker run --rm \
  -v org-archivist-qdrant-storage:/data \
  -v $(pwd):/backup \
  alpine tar czf /backup/qdrant-backup.tar.gz -C /data .
```

---

## Troubleshooting

### Common Issues

#### Port Already in Use

**Symptoms:** Error starting container, "port is already allocated"

**Solutions:**
1. Check what's using the port:
   ```bash
   # Linux/macOS
   lsof -i :8000  # or :5432, :6333, etc.

   # Windows
   netstat -ano | findstr :8000
   ```

2. Stop the conflicting service or change the port in `.env`:
   ```bash
   BACKEND_PORT=8001  # Use different port
   ```

3. Restart services:
   ```bash
   docker-compose down
   docker-compose up -d
   ```

#### Container Won't Start

**Symptoms:** Container exits immediately or shows "Unhealthy"

**Solutions:**
1. Check container logs:
   ```bash
   docker-compose logs backend  # or postgres, qdrant, frontend
   ```

2. Check environment variables are set correctly in `.env`

3. Verify Docker has enough resources (Memory: 4GB+, CPUs: 2+)

4. Try rebuilding:
   ```bash
   docker-compose build --no-cache backend
   docker-compose up -d
   ```

#### Database Connection Errors

**Symptoms:** Backend can't connect to PostgreSQL

**Solutions:**
1. Check PostgreSQL is running and healthy:
   ```bash
   docker ps | grep postgres
   ```

2. Verify connection string in `.env`:
   ```bash
   DATABASE_URL=postgresql://user:password@postgres:5432/org_archivist
   ```

3. Check PostgreSQL logs:
   ```bash
   docker-compose logs postgres
   ```

4. Try connecting manually:
   ```bash
   docker exec -it org-archivist-postgres psql -U user -d org_archivist
   ```

#### Qdrant Collection Errors

**Symptoms:** "Collection not found" or "Vector dimension mismatch"

**Solutions:**
1. Initialize the collection:
   ```bash
   python docker/qdrant/scripts/init_collection.py
   ```

2. Verify embedding dimensions match in `.env`:
   ```bash
   EMBEDDING_DIMENSIONS=1024  # Must match your model
   ```

3. Recreate collection with correct dimensions:
   ```bash
   python docker/qdrant/scripts/init_collection.py
   # Choose 'y' to recreate
   ```

#### API Key Errors

**Symptoms:** "Invalid API key" or authentication errors

**Solutions:**
1. Verify API key is set in `.env`:
   ```bash
   grep ANTHROPIC_API_KEY .env
   ```

2. Ensure no extra spaces or quotes:
   ```bash
   # Correct
   ANTHROPIC_API_KEY=sk-ant-xxxxx

   # Wrong
   ANTHROPIC_API_KEY="sk-ant-xxxxx"  # Remove quotes
   ANTHROPIC_API_KEY= sk-ant-xxxxx   # Remove space
   ```

3. Restart services after changing `.env`:
   ```bash
   docker-compose restart backend
   ```

#### Slow Performance

**Symptoms:** Slow searches or generation

**Solutions:**
1. Increase Docker resources (Settings > Resources)
   - Memory: 8GB recommended
   - CPUs: 4+ recommended

2. Check system resource usage:
   ```bash
   docker stats
   ```

3. Optimize Qdrant settings in `docker/qdrant/config/config.yaml`:
   ```yaml
   hnsw_config:
     m: 32  # Increase for better search quality
     ef_construct: 200
   ```

4. Use smaller embedding model:
   ```bash
   EMBEDDING_MODEL=bge-small-en-v1.5
   EMBEDDING_DIMENSIONS=384
   ```

---

## Advanced Configuration

### Using Local Python Environment

For faster development, you can run backend/frontend locally instead of in Docker:

```bash
# Create virtual environment
python -m venv .venv

# Activate (Linux/macOS)
source .venv/bin/activate

# Activate (Windows)
.venv\Scripts\activate

# Install dependencies
pip install -r backend/requirements.txt

# Run backend
cd backend
uvicorn app.main:app --reload --port 8000

# Run frontend (in another terminal)
cd frontend
streamlit run app.py --server.port 8501
```

**Note:** Still need Docker for PostgreSQL and Qdrant!

### Environment-Specific Configurations

Create multiple environment files:

```bash
.env.development   # Local development
.env.staging       # Staging environment
.env.production    # Production
```

Load specific environment:

```bash
docker-compose --env-file .env.staging up -d
```

### Debug Mode

Enable detailed logging:

```bash
# In .env
DEBUG=true
LOG_LEVEL=DEBUG
```

View detailed logs:

```bash
docker-compose logs -f backend | grep DEBUG
```

### Using Database Migrations (Alembic)

Instead of recreating the database, use Alembic for schema changes:

```bash
# Initialize Alembic (first time)
cd backend
alembic init alembic

# Create migration
alembic revision --autogenerate -m "Add new column"

# Apply migration
alembic upgrade head

# Rollback migration
alembic downgrade -1
```

---

## Getting Help

- **Documentation**: See `/docs` folder for detailed documentation
- **Architecture**: See `context/architecture.md`
- **Requirements**: See `context/requirements.md`
- **Issues**: Submit on GitHub Issues
- **Slack/Discord**: [Your team communication channel]

---

## Next Steps

Once your development environment is set up:

1. **Read the Architecture Documentation** - `context/architecture.md`
2. **Review the Requirements** - `context/requirements.md`
3. **Explore the Codebase** - Start with `backend/app/main.py`
4. **Run the Tests** - `pytest`
5. **Make Your First Contribution** - See `CONTRIBUTING.md`

Happy coding! 🚀
