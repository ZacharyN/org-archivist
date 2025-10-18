# Org Archivist

AI-powered institutional memory system to make it easier to respond to RFPs and complete grant applications. Org Archivist uses Retrieval-Augmented Generation (RAG) to search your document library and generate audience-specific content with proper citations.

## The Problem I'm Trying to Solve

Nonprofits, foundations, and mission-driven organizations repeatedly write similar content for different audiences: grant proposals, RFP responses, annual reports, donor communications. Each document requires pulling together organizational history, program descriptions, impact data, and strategic vision—but tailored to specific contexts.

**The current process is:**
- Time-intensive: Hours spent searching past documents for relevant examples
- Inconsistent: Different staff find different source materials
- Knowledge-dependent: Newer staff don't know where the best examples are
- Repetitive: Same information rewritten slightly differently each time

**Org Archivist solves this by:**
- Acting as comprehensive institutional memory across all documents
- Automatically finding the most relevant past examples and data
- Generating appropriately-styled content for different audiences
- Maintaining consistency in brand voice and factual accuracy
- Reducing draft creation time from hours to minutes

See [/context/project-context.md](/context/project-context.md) for detailed background and use cases.

## How It Works

1. **Upload Documents**: Add past proposals, annual reports, program descriptions, impact evaluations, strategic plans
2. **Smart Processing**: Documents are semantically chunked and embedded for intelligent retrieval
3. **Query**: Describe what you need ("Write organizational capacity section for federal DoED grant, $500K early childhood literacy")
4. **Generate**: System retrieves relevant content, composes context-aware prompts, and generates drafts using Claude
5. **Refine**: Review citations, check quality indicators, download or iterate

## Architecture

Org Archivist uses a modern RAG (Retrieval-Augmented Generation) architecture:

```
User Interface (Streamlit)
         ↓
    Backend API (FastAPI)
         ↓
    ┌────┴────┐
    ↓         ↓
Vector DB   Claude API
(Qdrant)    (Anthropic)
```

**Core Components:**
- **Document Processor**: Extracts text, chunks semantically, generates embeddings
- **Retrieval Engine**: Hybrid search (vector + keyword), metadata filtering, recency weighting
- **Generation Service**: Audience-aware prompts, streaming responses, citation tracking
- **Quality Validator**: Confidence scoring, hallucination detection, completeness checks

**Technology Stack:**
- **Backend**: Python, FastAPI, LlamaIndex
- **Vector Database**: Qdrant
- **Embeddings**: Configurable - OpenAI (text-embedding-3-small/large), Anthropic/Voyage, or BAAI/bge-large-en-v1.5 (local)
- **LLM**: Anthropic Claude (Sonnet 4.5)
- **Frontend**: Streamlit
- **Metadata Storage**: PostgreSQL (with Alembic migrations)
- **Deployment**: Docker, Docker Compose

See [/context/architecture.md](/context/architecture.md) for detailed system design.

## Features

**Document Management:**
- Upload PDF, DOCX, TXT files with metadata (type, year, programs, tags)
- Semantic chunking for optimal retrieval
- Filter and search document library
- Track document usage and relevance

**Content Generation:**
- Audience-specific prompts (Federal RFP, Foundation Grant, Individual Donor)
- Section-specific templates (Organizational Capacity, Program Description, Impact)
- Configurable tone and formality
- Streaming responses with real-time feedback

**Quality Assurance:**
- Confidence scoring for generated content
- Source citation and attribution
- Hallucination detection
- Completeness validation per section type
- Manual review flagging for low-confidence outputs

**Customization:**
- Manage prompt templates for brand voice
- Configure retrieval parameters (top-k sources, recency weight)
- Adjust model settings (temperature, max tokens)

See [/context/requirements.md](/context/requirements.md) for complete feature specifications.

## Use Cases

**Primary:** Grant writing and RFP responses
- Organizational capacity sections
- Program descriptions
- Impact narratives
- Budget justifications

**Secondary:**
- Annual reports
- Donor communications
- Board reports
- Strategic planning documents
- Marketing materials

**Who Benefits:**
- Nonprofits and foundations
- Social enterprises and B-Corps
- Cooperatives and collectives
- Mission-driven organizations
- Any organization that writes repeatedly about itself

## Project Status

**Current Phase:** Active Development (MVP)

This is a 2-week sprint to demonstrate core value:
- Week 1: Core RAG pipeline (document processing, retrieval, generation)
- Week 2: User interface and polish

**MVP Goals:**
- Upload and process documents
- Generate high-quality draft content
- Provide source citations
- Demonstrate 70-80% time savings vs manual drafting

## Getting Started

### Prerequisites
- Docker and Docker Compose
- Anthropic API key
- PostgreSQL database
- 8GB RAM, 20GB disk space

### Quick Start

```bash
# Clone repository
git clone https://github.com/yourusername/org-archivist.git
cd org-archivist

# Configure environment
cp .env.example .env
# Edit .env with your API keys and database connection

# Start services
docker-compose up -d

# Access application
# Frontend: http://localhost:8501
# Backend API: http://localhost:8000
# API Docs: http://localhost:8000/docs
```

### Development Setup

See detailed setup instructions in `/docs/setup.md` (coming soon).

## Project Structure

```
org-archivist/
├── backend/              # FastAPI application
│   ├── app/
│   │   ├── services/     # Core business logic
│   │   └── models/       # Data models
│   └── tests/
├── frontend/             # Streamlit UI
│   ├── pages/            # UI pages
│   └── components/       # Reusable components
├── context/              # Documentation
│   ├── project-context.md
│   ├── requirements.md
│   └── architecture.md
├── data/                 # Document storage
└── docker-compose.yml
```

## Key Design Decisions

**Why RAG over Fine-tuning:**
- Organization-specific content changes frequently
- No need to retrain on document updates
- Transparent source attribution
- Lower cost and complexity

**Why Semantic Chunking:**
- Respects document structure and topic boundaries
- Better retrieval relevance than fixed-size chunks
- Preserves context within chunks

**Why Hybrid Search:**
- Vector search for semantic similarity
- Keyword search for exact term matches
- Combined approach yields better results than either alone

**Why Local Embeddings:**
- No API costs for embeddings
- Faster for batch processing
- Data privacy (embeddings generated locally)

**Why Claude:**
- Excellent instruction following
- Strong citation behavior
- Consistent tone and style adherence
- Large context window (200K tokens)

## Roadmap

### Phase 1 (Current): MVP - Core Functionality
- Document upload and processing
- Basic retrieval and generation
- Simple UI
- Database migrations with Alembic
- API versioning strategy

### Phase 2: Enhanced RAG Features
- **Advanced RAG Techniques**
  - Query decomposition for complex multi-part questions
  - Self-RAG/CRAG patterns for improved accuracy
  - Hypothetical Document Embeddings (HyDE) for better retrieval
  - Cross-encoder reranking with dedicated models
- **Adaptive Chunking Strategy**
  - Document-type specific chunking parameters
  - Configurable chunk sizes and overlaps per document type
  - Smart boundary detection based on document structure
- Chat interface with multi-turn conversations
- Advanced prompt management UI
- Response versioning and comparison

### Phase 3: Production Hardening
- **Scalability Enhancements**
  - Connection pooling for PostgreSQL
  - Redis caching layer for frequently accessed data
  - Queue system (Celery/RabbitMQ) for async document processing
  - CDN integration for static assets
- **Rate Limiting**
  - API endpoint rate limiting with slowapi
  - Per-user and per-IP limits
  - Configurable rate limit tiers
- **Async Processing**
  - Background job queue for document processing
  - Webhook notifications for long-running tasks
  - Batch document upload processing
- Usage analytics and monitoring

### Phase 4: Observability & DevOps
- **Comprehensive Monitoring**
  - OpenTelemetry integration for distributed tracing
  - Prometheus metrics for system monitoring
  - Structured logging with correlation IDs
  - LangSmith/Langfuse integration for LLM observability
- **CI/CD Pipeline**
  - Automated testing workflows
  - Database migration validation
  - Deployment automation
  - Rollback strategies
- **API Management**
  - Version deprecation policy
  - API documentation versioning
  - Client SDK generation
  - Breaking change notifications

### Phase 5: Enterprise Features
- **Authentication & Security**
  - Multi-user support with SSO
  - Role-based access control (RBAC)
  - Document-level permissions
  - Audit logging with retention policies
- **Advanced Integrations**
  - Webhook system for external integrations
  - REST API for third-party access
  - GraphQL endpoint option
  - Export to common grant management platforms

### Phase 6: Advanced Intelligence
- **ML Enhancements**
  - Custom embedding fine-tuning on organizational content
  - Active learning from user feedback
  - Automatic document classification
  - Smart metadata extraction with NER
- **Content Intelligence**
  - Automatic grant opportunity matching
  - Success prediction based on historical data
  - Writing style analysis and recommendations
  - Plagiarism and self-plagiarism detection

### Future Considerations
- **Multi-modal Support**
  - Image and chart analysis from documents
  - Table extraction and understanding
  - Support for presentation files (PPTX)
- **Collaboration Features**
  - Real-time collaborative editing
  - Comment and review workflows
  - Version control integration
- **Compliance & Governance**
  - GDPR/CCPA compliance tools
  - Data retention automation
  - PII detection and redaction
  - Compliance reporting
