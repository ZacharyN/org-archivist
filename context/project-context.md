# CLAUDE.md

## Project Context

### Why This Project Exists

Nebraska Children and Families Foundation regularly writes grant proposals, responds to RFPs, creates donor communications, and produces various institutional documents. This work requires pulling together the organization's history, mission, programs, impact data, and strategic vision in ways that are tailored to specific audiences and funding opportunities.

**The Current Challenge:**

While the Foundation has extensive documentation—past successful proposals, annual reports, program descriptions, impact evaluations, strategic plans—each new writing project is different enough that source materials must be manually reviewed, relevant sections identified, and content rewritten to match the specific context. This process is:

- **Time-intensive:** Writers spend hours searching through past documents for relevant language, data, and examples
- **Inconsistent:** Different staff members may find different source materials or emphasize different aspects of the organization
- **Knowledge-dependent:** Newer staff may not know which past proposals contain the best examples for specific situations
- **Repetitive:** Much of the same information gets rewritten slightly differently for each new application
- **Quality-variable:** The quality of output depends heavily on which source documents a writer happens to find and reference

**The Opportunity:**

An AI-powered "Foundation Historian" can dramatically improve this workflow by:

1. **Institutional Memory:** Acting as a comprehensive knowledge base of everything the Foundation has written, across all programs and time periods
2. **Intelligent Retrieval:** Automatically finding the most relevant past examples, data points, and language for any new writing task
3. **Audience Adaptation:** Generating appropriately-styled content for different audiences (federal agencies, private foundations, corporate sponsors, individual donors)
4. **Consistency:** Ensuring brand voice, key messages, and factual accuracy remain consistent across all communications
5. **Efficiency:** Reducing draft creation time from hours to minutes, allowing writers to focus on refinement and customization
6. **Knowledge Transfer:** Making institutional knowledge accessible to all staff regardless of tenure

**Success Criteria:**

This project will be considered successful if it:

- Reduces time spent on initial draft creation by 70-80%
- Produces drafts that require only light editing rather than substantial rewriting
- Maintains factual accuracy with proper citations to source documents
- Generates content that matches the Foundation's brand voice consistently
- Provides confidence indicators so writers know when outputs need more review
- Demonstrates clear value-add that justifies continued development and maintenance

**User Workflow Vision:**

A grant writer needs to complete the "Organizational Capacity" section for a federal Department of Education RFP requesting $500,000 for early childhood literacy programs. Instead of:

1. Opening 10+ past proposals to find good organizational capacity language
2. Searching annual reports for staff qualifications and organizational history
3. Looking for previous DoED grants to match the tone and structure
4. Manually copying, pasting, and rewriting relevant sections
5. Fact-checking details against current organizational information
6. Spending 2-3 hours on a first draft

The writer:

1. Opens Foundation Historian
2. Describes the task: "Write organizational capacity section for DoED RFP, $500K early childhood literacy"
3. Selects audience (Federal RFP) and section type (Organizational Capacity)
4. Reviews generated draft in 30 seconds
5. Sees citations showing which documents informed the response
6. Makes minor edits for specific RFP requirements
7. Has a polished draft ready in 15 minutes

**Why Build Custom vs. Using Existing Tools:**

- **Control:** Full control over retrieval logic, prompt engineering, and quality validation for grant-specific use cases
- **Privacy:** Keep sensitive organizational and financial data within controlled infrastructure
- **Customization:** Tailor chunking, retrieval, and generation specifically for grant writing workflows
- **Learning:** Build organizational capability in AI/ML implementation
- **Integration:** Potential to integrate with other internal systems (document management, CRM)
- **Cost:** More cost-effective than enterprise solutions for a single-organization use case

---

## Technology Stack

### Overview

The Foundation Historian is built as a containerized application using modern, open-source technologies focused on production-quality Retrieval-Augmented Generation (RAG).

### Core Architecture

**Pattern:** RAG (Retrieval-Augmented Generation)
- Combines document retrieval with large language model generation
- Documents are chunked, embedded, and stored in vector database
- User queries trigger semantic search to find relevant content
- Retrieved content is used as context for LLM to generate responses

**Deployment:** Docker Compose
- Multi-container application (frontend, backend, vector database)
- Easy local development and production deployment
- Portable across hosting environments

### Backend Stack

**Language:** Python 3.11+
- Primary language for AI/ML ecosystem
- Excellent library support for RAG pipelines
- Strong typing support for maintainability

**Web Framework:** FastAPI
- Modern, fast Python web framework
- Automatic API documentation (Swagger/OpenAPI)
- Native async/await support for concurrent operations
- Type hints and validation via Pydantic
- WebSocket support for streaming responses

**RAG Framework:** LlamaIndex
- Purpose-built for RAG applications
- Best-in-class document processing and retrieval
- Built-in query optimization and caching
- Excellent citation/source tracking
- Supports hybrid search (vector + keyword)
- Active development and strong community

**Vector Database:** Qdrant
- Open-source vector similarity search engine
- High performance with filtered search
- Excellent Python client
- Payload storage for metadata
- Easy to deploy via Docker
- REST API for management

**Embedding Model:** BAAI/bge-large-en-v1.5
- State-of-the-art open-source embedding model
- Optimized for retrieval tasks
- 1024-dimensional embeddings
- Runs locally (no API costs)
- Via HuggingFace Transformers

**LLM:** Anthropic Claude (via API)
- Claude Sonnet 4.5 (claude-sonnet-4-5-20250929) as primary model
- Claude Opus 4 option for complex tasks
- Excellent at following detailed instructions
- Strong at maintaining consistent tone/style
- 200K token context window
- Good citation behavior

**Document Processing:**
- PyPDF2: PDF text extraction
- python-docx: Word document processing
- python-multipart: File upload handling

**Additional Libraries:**
- sentence-transformers: Local embedding generation
- anthropic: Claude API client
- pydantic: Data validation and settings management
- uvicorn: ASGI server for FastAPI

### Frontend Stack

**Framework:** Streamlit
- Rapid development framework for data applications
- Pure Python (no JavaScript required)
- Built-in widgets for forms, file uploads, data display
- Real-time updates with minimal code
- Session state management
- Easy deployment

**Key Features Used:**
- `st.file_uploader`: Document upload interface
- `st.form`: Complex forms with validation
- `st.data_editor`: Interactive document library table
- `st.chat_message`: Chat interface
- `st.expander`: Collapsible sections (sources, settings)
- `st.session_state`: Conversation and application state

**UI Components:**
- Markdown rendering for formatted text
- Metric displays for confidence/statistics
- Progress indicators for long operations
- Download buttons for artifacts
- Tabs for navigation between sections

### Database & Storage

**Vector Storage:** Qdrant
- Stores document embeddings
- Metadata filtering for advanced retrieval
- Similarity search with configurable distance metrics

**Document Metadata:** In-memory (MVP) → PostgreSQL (Production)
- Document registry and metadata
- User preferences and settings
- Conversation history
- Prompt templates

**File Storage:** Local filesystem (Docker volume)
- Uploaded source documents
- Generated artifacts
- Logs and audit trails

### External Services

**Anthropic API:**
- Claude model access
- Streaming response support
- Rate limiting and retry logic
- API key via environment variable

### Development & Deployment

**Containerization:**
- Docker for consistent environments
- Docker Compose for orchestration
- Multi-stage builds for optimization
- Volume mounts for data persistence

**Environment Management:**
- `.env` files for configuration
- Environment variables for secrets
- Config validation on startup

**Logging:**
- Structured logging via Python logging
- Log levels: DEBUG, INFO, WARNING, ERROR
- Request/response logging
- Error tracking and debugging

### Infrastructure Requirements

**Minimum Specifications:**
- 4 CPU cores
- 8GB RAM (16GB recommended)
- 50GB storage (for documents + embeddings)
- Docker and Docker Compose installed

**Hosting Options:**
- Local development: Docker Desktop
- Production: Any Docker-compatible host (DigitalOcean, AWS, Azure, on-premise)
- Supabase: Alternative for managed PostgreSQL + vector extensions

### Security Considerations

**API Key Management:**
- Environment variables (not hardcoded)
- `.env` file excluded from version control
- Secret rotation capability

**Data Privacy:**
- All data stored within controlled infrastructure
- No data sent to third parties except Anthropic API (only query text + retrieved context)
- Source documents never leave the system

**Access Control:**
- Basic authentication (MVP)
- Option for SSO/SAML integration (future)
- Role-based access control (future)

### Performance Characteristics

**Expected Performance:**
- Document processing: 5-10 seconds per document
- Retrieval: < 2 seconds for 5-10 sources
- Response generation: 3-10 seconds (streaming, first token < 1s)
- Concurrent users: 5-10 (single server)

**Scaling Considerations:**
- Horizontal scaling: Multiple backend containers behind load balancer
- Vector DB: Qdrant supports clustering for larger datasets
- Caching: LlamaIndex built-in caching for repeated queries
- Rate limiting: Respect Anthropic API limits (50 requests/min default)

### Monitoring & Observability

**Logging:**
- Application logs: All operations, errors, warnings
- API logs: All Claude API calls with latency
- User actions: Document uploads, queries, generations

**Metrics (future):**
- Query volume and patterns
- Response quality ratings
- Source document usage
- Error rates and types
- API costs tracking

---

## Development Philosophy

**Priorities:**
1. **Quality First:** RAG quality is paramount—better to have slower, accurate responses than fast, incorrect ones
2. **Iterative Improvement:** Start with core functionality, measure quality, iterate based on real usage
3. **User Feedback:** Build feedback mechanisms from day one to continuously improve
4. **Simplicity:** Choose simpler solutions that work over complex solutions that might work better
5. **Documentation:** Document decisions, configurations, and lessons learned

**Why These Technology Choices:**

- **LlamaIndex over LangChain:** More focused on RAG specifically, better defaults, less boilerplate
- **Qdrant over Chroma:** More production-ready, better filtering, cleaner API
- **Streamlit over React:** Faster development, good enough UI for internal tools, pure Python
- **FastAPI over Flask:** Modern, async support, automatic docs, type safety
- **Claude over GPT:** Better instruction following, stronger ethics, better citations
- **Local embeddings over API:** Cost savings, no data sent to embedding services, faster for large batches

---

## Next Steps

This document provides the foundation for development. See individual requirement documents for detailed specifications:

- `requirements/application-requirements.md` - User-facing feature requirements
- `requirements/business-logic-requirements.md` - Internal logic and algorithms
- `docs/architecture.md` - Detailed system architecture
- `docs/setup.md` - Development environment setup
- `docs/deployment.md` - Production deployment guide