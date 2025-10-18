# Architecture Documentation

## System Overview

The Foundation Historian is a Retrieval-Augmented Generation (RAG) application designed to assist grant writers in creating high-quality proposal content by intelligently retrieving and synthesizing information from the organization's document library.

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     User Interface Layer                    │
│                        (Streamlit)                          │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐       │
│  │   Document   │  │    Query     │  │    Chat      │       │
│  │  Management  │  │  Assistant   │  │  Interface   │       │ 
│  └──────────────┘  └──────────────┘  └──────────────┘       │
└────────────────────────────┬────────────────────────────────┘
                             │ HTTP/WebSocket
                             ▼
┌─────────────────────────────────────────────────────────────┐
│                    Application Layer                        │
│                        (FastAPI)                            │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐       │
│  │   Document   │  │   Retrieval  │  │  Generation  │       │
│  │  Processing  │  │    Engine    │  │   Service    │       │
│  └──────────────┘  └──────────────┘  └──────────────┘       │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐       │
│  │   Prompt     │  │   Quality    │  │   Citation   │       │
│  │  Management  │  │  Validation  │  │   Manager    │       │
│  └──────────────┘  └──────────────┘  └──────────────┘       │
└────────────────────────────┬────────────────────────────────┘
                             │
                    ┌────────┴────────┐
                    ▼                 ▼
        ┌──────────────────┐  ┌──────────────────┐
        │  Vector Database │  │  Anthropic API   │
        │    (Qdrant)      │  │  (Claude)        │
        │                  │  │                  │
        │  - Embeddings    │  │  - Text Gen      │
        │  - Metadata      │  │  - Streaming     │
        │  - Search        │  │                  │
        └──────────────────┘  └──────────────────┘
```

---

## Component Architecture

### 1. Frontend Layer (Streamlit)

**Purpose:** Provide user interface for all interactions with the system.

**Components:**

#### 1.1 Document Management Interface
**File:** `frontend/pages/document_library.py`

**Responsibilities:**
- File upload UI with drag-and-drop
- Metadata collection forms
- Document library table with filtering/sorting
- Bulk operations (delete, export)
- Statistics dashboard

**Key Functions:**
```python
def render_upload_section()
def render_metadata_form()
def render_library_table(filters)
def handle_bulk_delete(selected_docs)
def show_library_stats()
```

**State Management:**
```python
st.session_state.uploaded_files = []
st.session_state.library_filters = {}
st.session_state.selected_docs = []
```

#### 1.2 Query Assistant Interface
**File:** `frontend/pages/query_assistant.py`

**Responsibilities:**
- Project parameter configuration form
- Template selection
- Advanced options (retrieval params, filters)
- Response display with formatting
- Quality indicators display
- Source/citation viewer

**Key Functions:**
```python
def render_project_form()
def render_template_selector()
def render_advanced_options()
def display_response(response)
def show_quality_metrics(metrics)
def render_sources_panel(sources)
```

#### 1.3 Chat Interface
**File:** `frontend/pages/chat.py`

**Responsibilities:**
- Conversational message flow
- Message input with keyboard shortcuts
- Streaming response display
- Artifact rendering
- Conversation history sidebar
- Context preservation across turns

**Key Functions:**
```python
def render_chat_history()
def handle_user_input()
def stream_response(response_generator)
def render_artifact(artifact)
def save_conversation()
def load_conversation(conversation_id)
```

#### 1.4 Settings Interface
**File:** `frontend/pages/settings.py`

**Responsibilities:**
- Prompt template management
- Model configuration
- RAG parameter tuning
- User preferences
- System status display

**Key Functions:**
```python
def render_prompt_editor()
def render_model_config()
def render_rag_settings()
def save_settings()
```

---

### 2. Backend Layer (FastAPI)

**Purpose:** Handle business logic, orchestrate RAG pipeline, manage data flow.

#### 2.1 API Endpoints

**File:** `backend/app/main.py`

**Core Endpoints:**

```python
# Document Management
POST   /api/documents/upload          # Upload and process documents
GET    /api/documents                 # List all documents with filters
GET    /api/documents/{doc_id}        # Get document details
DELETE /api/documents/{doc_id}        # Delete document
GET    /api/documents/stats           # Get library statistics

# Query & Generation
POST   /api/query                     # Generate content (non-streaming)
POST   /api/query/stream              # Generate content (streaming)
POST   /api/chat                      # Chat endpoint with context

# Prompt Management
GET    /api/prompts                   # List all prompt templates
POST   /api/prompts                   # Create prompt template
PUT    /api/prompts/{prompt_id}       # Update prompt template
DELETE /api/prompts/{prompt_id}       # Delete prompt template

# System
GET    /api/health                    # Health check
GET    /api/config                    # Get system configuration
PUT    /api/config                    # Update system configuration
```

**Request/Response Models:**

```python
# Document Upload
class DocumentUploadRequest(BaseModel):
    file: UploadFile
    metadata: DocumentMetadata

class DocumentMetadata(BaseModel):
    doc_type: str
    year: int
    programs: List[str]
    tags: List[str]
    outcome: str
    notes: Optional[str]

class DocumentUploadResponse(BaseModel):
    success: bool
    doc_id: str
    chunks_created: int
    message: str

# Query Request
class QueryRequest(BaseModel):
    query: str
    audience: str
    section: str
    tone: str
    max_sources: int = 5
    recency_weight: float = 0.7
    include_citations: bool = True
    filters: Optional[DocumentFilters]
    custom_instructions: Optional[str]

class QueryResponse(BaseModel):
    text: str
    sources: List[Source]
    confidence: float
    quality_issues: List[str]
    metadata: ResponseMetadata
```

#### 2.2 Document Processing Service

**File:** `backend/app/services/document_processor.py`

**Class:** `DocumentProcessor`

**Responsibilities:**
- Extract text from various file formats
- Classify documents by type
- Split documents into semantic chunks
- Generate embeddings for chunks
- Enrich metadata from content
- Store in vector database

**Architecture:**

```python
class DocumentProcessor:
    def __init__(
        self,
        vector_store: VectorStore,
        embedding_model: EmbeddingModel,
        node_parser: NodeParser
    ):
        self.vector_store = vector_store
        self.embedding_model = embedding_model
        self.node_parser = node_parser
        self.text_extractors = {
            'pdf': PDFExtractor(),
            'docx': DOCXExtractor(),
            'txt': TextExtractor()
        }
    
    async def process_document(
        self,
        file_content: bytes,
        filename: str,
        metadata: Dict
    ) -> ProcessingResult:
        """Main processing pipeline"""
        # 1. Extract text
        text = await self._extract_text(file_content, filename)
        
        # 2. Classify document
        doc_type = self._classify_document(text, metadata)
        
        # 3. Enrich metadata
        enriched_metadata = self._enrich_metadata(text, metadata)
        
        # 4. Create document object
        document = Document(text=text, metadata=enriched_metadata)
        
        # 5. Parse into nodes (chunks)
        nodes = self.node_parser.get_nodes_from_documents([document])
        
        # 6. Generate embeddings
        for node in nodes:
            node.embedding = self.embedding_model.get_embedding(node.text)
        
        # 7. Store in vector database
        await self.vector_store.add_nodes(nodes)
        
        return ProcessingResult(
            success=True,
            doc_id=enriched_metadata['doc_id'],
            chunks=len(nodes)
        )
    
    def _extract_text(self, content: bytes, filename: str) -> str:
        """Extract text based on file extension"""
        
    def _classify_document(self, text: str, metadata: Dict) -> str:
        """Auto-classify document type"""
        
    def _enrich_metadata(self, text: str, metadata: Dict) -> Dict:
        """Extract additional metadata from content"""
```

**Text Extractors:**

```python
class PDFExtractor:
    """Extract text from PDF files"""
    def extract(self, content: bytes) -> str:
        reader = PyPDF2.PdfReader(io.BytesIO(content))
        text = ""
        for page in reader.pages:
            text += page.extract_text() + "\n\n"
        return text

class DOCXExtractor:
    """Extract text from DOCX files"""
    def extract(self, content: bytes) -> str:
        doc = docx.Document(io.BytesIO(content))
        paragraphs = [para.text for para in doc.paragraphs]
        return "\n\n".join(paragraphs)

class TextExtractor:
    """Extract text from plain text files"""
    def extract(self, content: bytes) -> str:
        return content.decode('utf-8', errors='ignore')
```

**Node Parser (Chunking Strategy):**

```python
from llama_index.core.node_parser import SemanticSplitterNodeParser

# Semantic chunking - splits at topic boundaries
node_parser = SemanticSplitterNodeParser(
    buffer_size=1,  # Number of sentences to compare
    breakpoint_percentile_threshold=95,  # Threshold for topic change
    embed_model=embedding_model
)

# Alternative: Sentence-based chunking with overlap
from llama_index.core.node_parser import SentenceSplitter

sentence_splitter = SentenceSplitter(
    chunk_size=500,  # Target chunk size in tokens
    chunk_overlap=50,  # Overlap between chunks
    paragraph_separator="\n\n"
)
```

#### 2.3 Retrieval Engine

**File:** `backend/app/services/retrieval_engine.py`

**Class:** `RetrievalEngine`

**Responsibilities:**
- Process and expand user queries
- Perform hybrid search (vector + keyword)
- Apply metadata filters
- Re-rank results
- Apply recency weighting
- Return top-k relevant chunks

**Architecture:**

```python
class RetrievalEngine:
    def __init__(
        self,
        vector_store: VectorStore,
        embedding_model: EmbeddingModel,
        reranker: Optional[Reranker] = None
    ):
        self.vector_store = vector_store
        self.embedding_model = embedding_model
        self.reranker = reranker
    
    async def retrieve(
        self,
        query: str,
        top_k: int = 5,
        filters: Optional[Dict] = None,
        recency_weight: float = 0.7
    ) -> List[RetrievalResult]:
        """Main retrieval pipeline"""
        
        # 1. Process query
        processed_query = self._process_query(query)
        
        # 2. Generate query embedding
        query_embedding = self.embedding_model.get_embedding(processed_query)
        
        # 3. Vector similarity search
        vector_results = await self.vector_store.search(
            query_embedding=query_embedding,
            top_k=top_k * 4,  # Retrieve more for reranking
            filters=filters
        )
        
        # 4. Keyword search (BM25)
        keyword_results = await self._keyword_search(
            processed_query,
            top_k=top_k * 2,
            filters=filters
        )
        
        # 5. Hybrid scoring
        combined_results = self._combine_results(
            vector_results,
            keyword_results,
            vector_weight=0.7,
            keyword_weight=0.3
        )
        
        # 6. Apply recency weighting
        weighted_results = self._apply_recency_weight(
            combined_results,
            recency_weight
        )
        
        # 7. Re-rank if reranker available
        if self.reranker:
            weighted_results = self.reranker.rerank(
                query,
                weighted_results,
                top_k=top_k * 2
            )
        
        # 8. Diversify results (avoid too many from same doc)
        diversified_results = self._diversify_results(weighted_results)
        
        # 9. Return top-k
        return diversified_results[:top_k]
    
    def _process_query(self, query: str) -> str:
        """Expand query with synonyms, clean text"""
        # Remove stop words, expand abbreviations, etc.
        return processed_query
    
    def _keyword_search(self, query: str, top_k: int, filters: Dict) -> List:
        """BM25 keyword search"""
        # Implementation using search library or custom BM25
        return results
    
    def _combine_results(
        self,
        vector_results: List,
        keyword_results: List,
        vector_weight: float,
        keyword_weight: float
    ) -> List:
        """Combine and score results from both searches"""
        combined = {}
        
        # Add vector results
        for result in vector_results:
            combined[result.node_id] = {
                'node': result.node,
                'score': result.score * vector_weight,
                'metadata': result.metadata
            }
        
        # Add/update with keyword results
        for result in keyword_results:
            if result.node_id in combined:
                combined[result.node_id]['score'] += result.score * keyword_weight
            else:
                combined[result.node_id] = {
                    'node': result.node,
                    'score': result.score * keyword_weight,
                    'metadata': result.metadata
                }
        
        # Sort by combined score
        sorted_results = sorted(
            combined.values(),
            key=lambda x: x['score'],
            reverse=True
        )
        
        return sorted_results
    
    def _apply_recency_weight(
        self,
        results: List,
        recency_weight: float
    ) -> List:
        """Boost scores for more recent documents"""
        current_year = datetime.now().year
        
        for result in results:
            doc_year = result['metadata'].get('year', current_year)
            years_old = current_year - doc_year
            
            # Calculate recency multiplier
            if years_old == 0:
                multiplier = 1.0
            elif years_old == 1:
                multiplier = 0.95
            elif years_old == 2:
                multiplier = 0.90
            else:
                multiplier = 0.85
            
            # Apply weight
            multiplier = 1.0 + (multiplier - 1.0) * recency_weight
            result['score'] *= multiplier
        
        # Re-sort
        results.sort(key=lambda x: x['score'], reverse=True)
        return results
    
    def _diversify_results(self, results: List, max_per_doc: int = 3) -> List:
        """Ensure diversity - limit chunks per document"""
        doc_counts = {}
        diversified = []
        
        for result in results:
            doc_id = result['metadata'].get('doc_id')
            count = doc_counts.get(doc_id, 0)
            
            if count < max_per_doc:
                diversified.append(result)
                doc_counts[doc_id] = count + 1
        
        return diversified
```

**Metadata Filtering:**

```python
class DocumentFilters(BaseModel):
    doc_types: Optional[List[str]] = None
    years: Optional[List[int]] = None
    programs: Optional[List[str]] = None
    outcomes: Optional[List[str]] = None
    exclude_docs: Optional[List[str]] = None
    date_range: Optional[Tuple[int, int]] = None

# In Qdrant, filters translate to:
from qdrant_client.models import Filter, FieldCondition, MatchAny

def build_qdrant_filter(filters: DocumentFilters) -> Filter:
    conditions = []
    
    if filters.doc_types:
        conditions.append(
            FieldCondition(
                key="doc_type",
                match=MatchAny(any=filters.doc_types)
            )
        )
    
    if filters.years:
        conditions.append(
            FieldCondition(
                key="year",
                match=MatchAny(any=filters.years)
            )
        )
    
    # ... other conditions
    
    return Filter(must=conditions) if conditions else None
```

#### 2.4 Generation Service

**File:** `backend/app/services/generation_service.py`

**Class:** `GenerationService`

**Responsibilities:**
- Construct prompts from templates and context
- Call Claude API
- Handle streaming responses
- Parse and post-process outputs
- Extract citations
- Validate responses

**Architecture:**

```python
class GenerationService:
    def __init__(
        self,
        anthropic_client: anthropic.Anthropic,
        prompt_manager: PromptManager
    ):
        self.client = anthropic_client
        self.prompt_manager = prompt_manager
    
    async def generate(
        self,
        query: str,
        context: List[RetrievalResult],
        parameters: GenerationParameters,
        stream: bool = False
    ) -> Union[GenerationResponse, AsyncGenerator]:
        """Generate response from query and context"""
        
        # 1. Build system prompt
        system_prompt = self.prompt_manager.build_system_prompt(
            audience=parameters.audience,
            section=parameters.section,
            tone=parameters.tone
        )
        
        # 2. Format context
        formatted_context = self._format_context(context)
        
        # 3. Build user message
        user_message = self._build_user_message(
            query=query,
            context=formatted_context,
            parameters=parameters
        )
        
        # 4. Call Claude API
        if stream:
            return self._generate_streaming(system_prompt, user_message, parameters)
        else:
            return await self._generate_complete(system_prompt, user_message, parameters)
    
    def _format_context(self, context: List[RetrievalResult]) -> str:
        """Format retrieved chunks for prompt"""
        formatted = []
        
        for i, result in enumerate(context, 1):
            source_info = (
                f"Source [{i}]: {result.metadata['filename']} "
                f"({result.metadata['year']}) - "
                f"Relevance: {result.score:.2f}\n"
            )
            formatted.append(source_info + result.text + "\n---\n")
        
        return "\n".join(formatted)
    
    def _build_user_message(
        self,
        query: str,
        context: str,
        parameters: GenerationParameters
    ) -> str:
        """Construct user message with instructions"""
        
        message = f"""Context from organizational documents:

{context}

Writing Parameters:
- Audience: {parameters.audience}
- Section: {parameters.section}
- Tone: {parameters.tone}

"""
        
        if parameters.custom_instructions:
            message += f"Additional Instructions:\n{parameters.custom_instructions}\n\n"
        
        if parameters.include_citations:
            message += "Please include inline citations using [N] notation for all factual claims.\n\n"
        
        message += f"Request: {query}"
        
        return message
    
    async def _generate_complete(
        self,
        system_prompt: str,
        user_message: str,
        parameters: GenerationParameters
    ) -> GenerationResponse:
        """Non-streaming generation"""
        
        response = self.client.messages.create(
            model=parameters.model,
            max_tokens=parameters.max_tokens,
            temperature=parameters.temperature,
            system=system_prompt,
            messages=[{"role": "user", "content": user_message}]
        )
        
        text = response.content[0].text
        
        # Post-process
        text = self._post_process(text)
        
        # Extract citations
        citations = self._extract_citations(text)
        
        return GenerationResponse(
            text=text,
            citations=citations,
            model=parameters.model,
            usage=response.usage
        )
    
    async def _generate_streaming(
        self,
        system_prompt: str,
        user_message: str,
        parameters: GenerationParameters
    ) -> AsyncGenerator[str, None]:
        """Streaming generation"""
        
        with self.client.messages.stream(
            model=parameters.model,
            max_tokens=parameters.max_tokens,
            temperature=parameters.temperature,
            system=system_prompt,
            messages=[{"role": "user", "content": user_message}]
        ) as stream:
            for chunk in stream.text_stream:
                yield chunk
    
    def _post_process(self, text: str) -> str:
        """Clean up generated text"""
        # Remove extra whitespace
        text = re.sub(r'\n{3,}', '\n\n', text)
        text = re.sub(r' {2,}', ' ', text)
        
        # Fix punctuation
        text = re.sub(r' \.', '.', text)
        text = re.sub(r' ,', ',', text)
        
        return text.strip()
    
    def _extract_citations(self, text: str) -> List[int]:
        """Extract citation numbers from text"""
        pattern = r'\[(\d+)\]'
        citations = re.findall(pattern, text)
        return [int(c) for c in citations]
```

#### 2.5 Prompt Management

**File:** `backend/app/services/prompt_manager.py`

**Class:** `PromptManager`

**Responsibilities:**
- Store and manage prompt templates
- Compose layered prompts
- Variable substitution
- Template validation

**Architecture:**

```python
class PromptManager:
    def __init__(self, storage: PromptStorage):
        self.storage = storage
        self.base_prompts = self._load_base_prompts()
    
    def build_system_prompt(
        self,
        audience: str,
        section: str,
        tone: str
    ) -> str:
        """Compose full system prompt from layers"""
        
        layers = []
        
        # 1. Base role definition
        layers.append(self.base_prompts['role_definition'])
        
        # 2. Brand voice
        layers.append(self.base_prompts['brand_voice'])
        
        # 3. Audience-specific
        audience_prompt = self.storage.get_prompt(
            category='audience',
            name=audience
        )
        if audience_prompt:
            layers.append(audience_prompt.content)
        
        # 4. Section-specific
        section_prompt = self.storage.get_prompt(
            category='section',
            name=section
        )
        if section_prompt:
            layers.append(section_prompt.content)
        
        # 5. Tone adjustments
        tone_instructions = self._get_tone_instructions(tone)
        layers.append(tone_instructions)
        
        return "\n\n---\n\n".join(layers)
    
    def _load_base_prompts(self) -> Dict[str, str]:
        """Load core prompts that are always included"""
        return {
            'role_definition': """You are the Foundation Historian for Nebraska Children and Families Foundation.
Your role is to help staff write grant proposals, RFP responses, and donor communications by drawing on the organization's extensive document library.

You have access to past proposals, annual reports, program descriptions, impact evaluations, and strategic plans. Use these materials to inform your responses while adapting the content appropriately for each specific request.""",
            
            'brand_voice': """Brand Voice Guidelines:
- Professional yet warm and accessible
- Data-driven but story-focused
- Emphasize impact and outcomes for children and families
- Use active voice and clear, direct language
- Avoid jargon unless appropriate for technical audiences
- Balance optimism about potential with realism about challenges
- Center the communities and families served, not the organization"""
        }
    
    def _get_tone_instructions(self, tone: str) -> str:
        """Get tone-specific instructions"""
        tone_map = {
            'Very Formal': "Use highly formal, technical language appropriate for federal agencies. Third-person perspective only.",
            'Formal': "Use formal professional language. Prefer third-person but first-person organizational voice is acceptable.",
            'Professional': "Use clear professional language. Balance formality with accessibility.",
            'Warm': "Use warm, engaging language while maintaining professionalism. First-person organizational voice encouraged.",
            'Conversational': "Use accessible, conversational language appropriate for individual donors."
        }
        return tone_map.get(tone, tone_map['Professional'])

class PromptTemplate(BaseModel):
    """Prompt template model"""
    id: str
    name: str
    category: str  # 'audience', 'section', 'custom'
    content: str
    variables: List[str]  # Variables that can be substituted
    created_at: datetime
    updated_at: datetime
    active: bool

class PromptStorage:
    """Storage interface for prompts"""
    def get_prompt(self, category: str, name: str) -> Optional[PromptTemplate]:
        pass
    
    def create_prompt(self, prompt: PromptTemplate) -> PromptTemplate:
        pass
    
    def update_prompt(self, prompt_id: str, updates: Dict) -> PromptTemplate:
        pass
    
    def delete_prompt(self, prompt_id: str) -> bool:
        pass
    
    def list_prompts(self, category: Optional[str] = None) -> List[PromptTemplate]:
        pass
```

**Default Audience Prompts:**

```python
AUDIENCE_PROMPTS = {
    'Federal RFP': """Federal RFP Style Requirements:
- Highly structured with clear sections matching RFP requirements
- Technical, formal language
- Third-person perspective
- Heavy emphasis on data, metrics, and evidence-based practices
- Explicit connections to federal priorities and regulations
- Comprehensive detail on evaluation and sustainability
- Budget justification with clear cost-benefit analysis""",
    
    'Foundation Grant': """Foundation Grant Style Requirements:
- Clear theory of change and logic model
- Balance of quantitative data and qualitative stories
- Emphasis on community partnerships and engagement
- Professional but accessible tone
- First-person organizational voice acceptable
- Focus on innovation and lessons learned
- Realistic about challenges and mitigation strategies""",
    
    'Individual Donor': """Individual Donor Style Requirements:
- Warm, engaging, personal tone
- Lead with compelling stories, support with data
- Make donor feel like a partner in the work
- Use "you" and "your support" language
- Emphasize tangible, concrete outcomes
- Show impact of donations at multiple levels
- Create emotional connection while remaining professional"""
}
```

**Default Section Prompts:**

```python
SECTION_PROMPTS = {
    'Organizational Capacity': """Required Elements:
- Organizational history and mission alignment
- Governance structure and board composition
- Staff qualifications and expertise
- Organizational track record and past successes
- Financial stability and management
- Administrative systems and infrastructure
- Quality assurance and continuous improvement processes

Structure: Start with brief organizational overview, then address each capacity area with specific evidence.""",
    
    'Program Description': """Required Elements:
- Clear program goals and objectives (SMART)
- Target population and eligibility criteria
- Program activities and service delivery model
- Timeline and milestones
- Staffing and organizational structure
- Logic model or theory of change
- Evidence base or best practices foundation

Structure: Begin with program overview and goals, describe activities in logical sequence, conclude with expected outcomes."""
}
```

#### 2.6 Quality Validation Service

**File:** `backend/app/services/quality_validator.py`

**Class:** `QualityValidator`

**Responsibilities:**
- Calculate confidence scores
- Detect hallucinations
- Check completeness
- Identify contradictions
- Validate tone appropriateness

**Architecture:**

```python
class QualityValidator:
    def __init__(self, embedding_model: EmbeddingModel):
        self.embedding_model = embedding_model
    
    def validate(
        self,
        query: str,
        response: str,
        sources: List[RetrievalResult],
        parameters: GenerationParameters
    ) -> ValidationResult:
        """Comprehensive quality validation"""
        
        issues = []
        
        # 1. Calculate confidence
        confidence = self._calculate_confidence(response, sources)
        if confidence < 0.6:
            issues.append(QualityIssue(
                severity='warning',
                message=f'Low confidence score ({confidence:.2f}). Response may need review.'
            ))
        
        # 2. Check groundedness
        groundedness = self._check_groundedness(response, sources)
        if groundedness < 0.8:
            issues.append(QualityIssue(
                severity='warning',
                message=f'Some claims may lack source support ({groundedness:.0%} grounded).'
            ))
        
        # 3. Check completeness
        completeness_issues = self._check_completeness(
            response,
            parameters.section
        )
        issues.extend(completeness_issues)
        
        # 4. Check for contradictions
        contradictions = self._find_contradictions(response, sources)
        if contradictions:
            issues.append(QualityIssue(
                severity='error',
                message=f'Potential contradictions detected: {contradictions}'
            ))
        
        # 5. Validate tone
        tone_match = self._validate_tone(response, parameters.tone)
        if not tone_match:
            issues.append(QualityIssue(
                severity='info',
                message=f'Response tone may not match requested "{parameters.tone}" tone.'
            ))
        
        # 6. Check relevance to query
        relevance = self._check_relevance(query, response)
        if relevance < 0.7:
            issues.append(QualityIssue(
                severity='warning',
                message='Response may be off-topic or not fully address the query.'
            ))
        
        return ValidationResult(
            confidence=confidence,
            groundedness=groundedness,
            relevance=relevance,
            issues=issues,
            needs_review=any(i.severity in ['warning', 'error'] for i in issues)
        )
    
    def _calculate_confidence(
        self,
        response: str,
        sources: List[RetrievalResult]
    ) -> float:
        """Calculate overall confidence score"""
        
        # Average source relevance (40%)
        avg_relevance = sum(s.score for s in sources) / len(sources) if sources else 0
        relevance_score = avg_relevance * 0.4
        
        # Number of sources (20%)
        # More sources = higher confidence, up to a point
        num_sources = len(sources)
        sources_score = min(num_sources / 5.0, 1.0) * 0.2
        
        # Source agreement (20%)
        # Check if sources tell consistent story
        agreement_score = self._calculate_source_agreement(sources) * 0.2
        
        # Response length appropriateness (20%)
        # Neither too short nor too long for the query
        length_score = self._calculate_length_score(response) * 0.2
        
        confidence = relevance_score + sources_score + agreement_score + length_score
        
        return confidence
    
    def _check_groundedness(
        self,
        response: str,
        sources: List[RetrievalResult]
    ) -> float:
        """Check what % of response is supported by sources"""
        
        # Split response into claims (sentences)
        sentences = self._split_into_sentences(response)
        
        # Combine source text
        source_text = " ".join([s.text for s in sources])
        source_embedding = self.embedding_model.get_embedding(source_text)
        
        # Check each claim
        grounded_count = 0
        for sentence in sentences:
            # Skip transitional/structural sentences
            if self._is_structural_sentence(sentence):
                continue
            
            sentence_embedding = self.embedding_model.get_embedding(sentence)
            similarity = self._cosine_similarity(sentence_embedding, source_embedding)
            
            if similarity > 0.5:  # Threshold for "supported"
                grounded_count += 1
        
        return grounded_count / len(sentences) if sentences else 0
    
    def _check_completeness(
        self,
        response: str,
        section_type: str
    ) -> List[QualityIssue]:
        """Check if response contains required elements for section"""
        
        issues = []
        
        # Define required elements per section
        required_elements = {
            'Organizational Capacity': [
                'staff', 'governance', 'board', 'track record',
                'financial', 'history', 'experience'
            ],
            'Program Description': [
                'goal', 'objective', 'activity', 'participant',
                'timeline', 'outcome'
            ],
            'Impact & Outcomes': [
                'metric', 'data', 'result', 'outcome',
                'evidence', 'evaluation'
            ],
            'Budget Narrative': [
                'cost', 'budget', 'expense', 'justification',
                'personnel', 'sustainability'
            ]
        }
        
        if section_type in required_elements:
            response_lower = response.lower()
            missing = []
            
            for element in required_elements[section_type]:
                if element not in response_lower:
                    missing.append(element)
            
            if missing:
                issues.append(QualityIssue(
                    severity='info',
                    message=f'Consider including: {", ".join(missing)}'
                ))
        
        return issues
    
    def _find_contradictions(
        self,
        response: str,
        sources: List[RetrievalResult]
    ) -> List[str]:
        """Identify potential contradictions"""
        
        contradictions = []
        
        # Extract numerical claims from response
        response_numbers = self._extract_numerical_claims(response)
        
        # Extract numerical claims from sources
        source_numbers = {}
        for source in sources:
            source_numbers.update(self._extract_numerical_claims(source.text))
        
        # Compare
        for metric, value in response_numbers.items():
            if metric in source_numbers:
                if abs(value - source_numbers[metric]) / source_numbers[metric] > 0.1:
                    contradictions.append(
                        f'{metric}: response says {value}, source says {source_numbers[metric]}'
                    )
        
        return contradictions
    
    def _validate_tone(self, response: str, requested_tone: str) -> bool:
        """Check if response matches requested tone"""
        
        # Simple heuristic-based tone detection
        # In production, could use a fine-tuned classifier
        
        tone_indicators = {
            'Very Formal': ['furthermore', 'pursuant', 'hereby', 'whereas'],
            'Formal': ['therefore', 'additionally', 'demonstrated', 'implementation'],
            'Professional': ['however', 'support', 'develop', 'ensure'],
            'Warm': ['proud', 'passionate', 'together', 'community'],
            'Conversational': ['you', 'your', 'help', 'make a difference']
        }
        
        response_lower = response.lower()
        indicators_present = sum(
            1 for word in tone_indicators.get(requested_tone, [])
            if word in response_lower
        )
        
        # If at least 2 tone indicators present, consider it a match
        return indicators_present >= 2
    
    def _check_relevance(self, query: str, response: str) -> float:
        """Check semantic similarity between query and response"""
        query_embedding = self.embedding_model.get_embedding(query)
        response_embedding = self.embedding_model.get_embedding(response)
        return self._cosine_similarity(query_embedding, response_embedding)
    
    def _cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """Calculate cosine similarity between vectors"""
        import numpy as np
        return np.dot(vec1, vec2) / (np.linalg.norm(vec1) * np.linalg.norm(vec2))

class ValidationResult(BaseModel):
    confidence: float
    groundedness: float
    relevance: float
    issues: List[QualityIssue]
    needs_review: bool

class QualityIssue(BaseModel):
    severity: str  # 'info', 'warning', 'error'
    message: str
```

#### 2.7 Citation Manager

**File:** `backend/app/services/citation_manager.py`

**Class:** `CitationManager`

**Responsibilities:**
- Extract citations from response
- Map citations to sources
- Format citations in various styles
- Generate bibliographies

**Architecture:**

```python
class CitationManager:
    def __init__(self):
        self.citation_styles = {
            'numbered': self._format_numbered,
            'footnote': self._format_footnote,
            'apa': self._format_apa
        }
    
    def process_citations(
        self,
        response: str,
        sources: List[RetrievalResult],
        style: str = 'numbered'
    ) -> CitationResult:
        """Process and format citations"""
        
        # 1. Extract citation markers
        citations = self._extract_citations(response)
        
        # 2. Validate citations reference real sources
        valid_citations, invalid_citations = self._validate_citations(
            citations,
            sources
        )
        
        # 3. Map citations to sources
        citation_map = self._map_citations_to_sources(valid_citations, sources)
        
        # 4. Format citations
        formatter = self.citation_styles.get(style, self._format_numbered)
        formatted_response = formatter(response, citation_map)
        
        # 5. Generate bibliography
        bibliography = self._generate_bibliography(citation_map, style)
        
        return CitationResult(
            formatted_response=formatted_response,
            bibliography=bibliography,
            citation_map=citation_map,
            invalid_citations=invalid_citations
        )
    
    def _extract_citations(self, text: str) -> List[int]:
        """Extract citation numbers [N] from text"""
        pattern = r'\[(\d+)\]'
        return [int(m) for m in re.findall(pattern, text)]
    
    def _validate_citations(
        self,
        citations: List[int],
        sources: List[RetrievalResult]
    ) -> Tuple[List[int], List[int]]:
        """Check citations reference valid sources"""
        valid = [c for c in citations if 0 < c <= len(sources)]
        invalid = [c for c in citations if c not in valid]
        return valid, invalid
    
    def _map_citations_to_sources(
        self,
        citations: List[int],
        sources: List[RetrievalResult]
    ) -> Dict[int, Source]:
        """Map citation numbers to source objects"""
        return {
            i: Source(
                id=i,
                filename=sources[i-1].metadata['filename'],
                doc_type=sources[i-1].metadata['doc_type'],
                year=sources[i-1].metadata.get('year'),
                excerpt=sources[i-1].text[:200] + "...",
                relevance=sources[i-1].score
            )
            for i in citations
            if 0 < i <= len(sources)
        }
    
    def _format_numbered(
        self,
        text: str,
        citation_map: Dict[int, Source]
    ) -> str:
        """Keep numbered citations [N] as-is"""
        return text
    
    def _format_footnote(
        self,
        text: str,
        citation_map: Dict[int, Source]
    ) -> str:
        """Convert to footnote format"""
        # Replace [N] with superscript
        for num in sorted(citation_map.keys(), reverse=True):
            text = text.replace(f'[{num}]', f'<sup>{num}</sup>')
        return text
    
    def _format_apa(
        self,
        text: str,
        citation_map: Dict[int, Source]
    ) -> str:
        """Convert to APA style (Author, Year)"""
        for num, source in citation_map.items():
            org_name = "Nebraska Children and Families Foundation"
            year = source.year or "n.d."
            apa_citation = f'({org_name}, {year})'
            text = text.replace(f'[{num}]', apa_citation)
        return text
    
    def _generate_bibliography(
        self,
        citation_map: Dict[int, Source],
        style: str
    ) -> List[str]:
        """Generate formatted bibliography"""
        bibliography = []
        
        for num in sorted(citation_map.keys()):
            source = citation_map[num]
            
            if style == 'apa':
                entry = f"Nebraska Children and Families Foundation. ({source.year or 'n.d.'}). {source.filename}."
            else:
                entry = f"[{num}] {source.filename} ({source.year or 'n.d.'}) - {source.doc_type}"
            
            bibliography.append(entry)
        
        return bibliography

class Source(BaseModel):
    id: int
    filename: str
    doc_type: str
    year: Optional[int]
    excerpt: str
    relevance: float

class CitationResult(BaseModel):
    formatted_response: str
    bibliography: List[str]
    citation_map: Dict[int, Source]
    invalid_citations: List[int]
```

---

### 3. Data Layer

#### 3.1 Vector Database (Qdrant)

**Purpose:** Store and search document embeddings with metadata.

**Schema:**

```python
# Collection configuration
collection_config = {
    "vectors": {
        "size": 1024,  # bge-large-en-v1.5 embedding size
        "distance": "Cosine"  # Cosine similarity
    },
    "optimizers_config": {
        "indexing_threshold": 10000
    }
}

# Point structure
{
    "id": "doc_id_chunk_index",  # Unique identifier
    "vector": [0.1, 0.2, ...],   # 1024-dimensional embedding
    "payload": {
        # Document metadata
        "doc_id": "uuid",
        "filename": "proposal_2024.pdf",
        "doc_type": "Grant Proposal",
        "year": 2024,
        "programs": ["Early Childhood", "Education"],
        "tags": ["federal", "DoED", "funded"],
        "outcome": "Funded",
        "upload_date": "2024-10-15T10:30:00Z",
        
        # Chunk metadata
        "chunk_index": 0,
        "chunk_text": "Nebraska Children and Families Foundation...",
        "section_type": "organizational_capacity",
        
        # Processing metadata
        "processed_date": "2024-10-15T10:31:00Z"
    }
}
```

**Key Operations:**

```python
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct, Filter, FieldCondition

class QdrantVectorStore:
    def __init__(self, host: str = "localhost", port: int = 6333):
        self.client = QdrantClient(host=host, port=port)
        self.collection_name = "foundation_docs"
    
    def create_collection(self):
        """Initialize collection"""
        self.client.create_collection(
            collection_name=self.collection_name,
            vectors_config=VectorParams(size=1024, distance=Distance.COSINE)
        )
    
    async def add_nodes(self, nodes: List[Node]):
        """Add document chunks"""
        points = [
            PointStruct(
                id=node.id_,
                vector=node.embedding,
                payload={
                    **node.metadata,
                    "chunk_text": node.text
                }
            )
            for node in nodes
        ]
        
        self.client.upsert(
            collection_name=self.collection_name,
            points=points
        )
    
    async def search(
        self,
        query_embedding: List[float],
        top_k: int = 5,
        filters: Optional[Filter] = None
    ) -> List[ScoredPoint]:
        """Semantic search"""
        return self.client.search(
            collection_name=self.collection_name,
            query_vector=query_embedding,
            limit=top_k,
            query_filter=filters
        )
    
    async def delete_by_doc_id(self, doc_id: str):
        """Delete all chunks for a document"""
        self.client.delete(
            collection_name=self.collection_name,
            points_selector=Filter(
                must=[
                    FieldCondition(
                        key="doc_id",
                        match={"value": doc_id}
                    )
                ]
            )
        )
```

#### 3.2 Metadata Storage

**Initial:** In-memory dictionary
**Production:** PostgreSQL

**Schema (PostgreSQL):**

```sql
-- Documents table
CREATE TABLE documents (
    doc_id UUID PRIMARY KEY,
    filename VARCHAR(255) NOT NULL,
    doc_type VARCHAR(50) NOT NULL,
    year INTEGER,
    outcome VARCHAR(50),
    notes TEXT,
    upload_date TIMESTAMP NOT NULL,
    file_size INTEGER,
    chunks_count INTEGER,
    created_by VARCHAR(100),
    CONSTRAINT valid_year CHECK (year >= 2000 AND year <= EXTRACT(YEAR FROM CURRENT_DATE) + 1)
);

-- Programs junction table (many-to-many)
CREATE TABLE document_programs (
    doc_id UUID REFERENCES documents(doc_id) ON DELETE CASCADE,
    program VARCHAR(100),
    PRIMARY KEY (doc_id, program)
);

-- Tags junction table
CREATE TABLE document_tags (
    doc_id UUID REFERENCES documents(doc_id) ON DELETE CASCADE,
    tag VARCHAR(100),
    PRIMARY KEY (doc_id, tag)
);

-- Prompt templates
CREATE TABLE prompt_templates (
    prompt_id UUID PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    category VARCHAR(50) NOT NULL,
    content TEXT NOT NULL,
    variables JSONB,
    active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP NOT NULL,
    updated_at TIMESTAMP NOT NULL,
    version INTEGER DEFAULT 1
);

-- Conversations
CREATE TABLE conversations (
    conversation_id UUID PRIMARY KEY,
    name VARCHAR(255),
    created_at TIMESTAMP NOT NULL,
    updated_at TIMESTAMP NOT NULL,
    user_id VARCHAR(100)
);

-- Messages
CREATE TABLE messages (
    message_id UUID PRIMARY KEY,
    conversation_id UUID REFERENCES conversations(conversation_id) ON DELETE CASCADE,
    role VARCHAR(20) NOT NULL,  -- 'user' or 'assistant'
    content TEXT NOT NULL,
    sources JSONB,
    metadata JSONB,
    created_at TIMESTAMP NOT NULL,
    CONSTRAINT valid_role CHECK (role IN ('user', 'assistant'))
);

-- System configuration
CREATE TABLE system_config (
    key VARCHAR(100) PRIMARY KEY,
    value JSONB NOT NULL,
    updated_at TIMESTAMP NOT NULL
);
```

---

## Data Flow Diagrams

### Document Upload Flow

```
User uploads document
        ↓
Streamlit file_uploader captures file + metadata
        ↓
POST /api/documents/upload
        ↓
DocumentProcessor.process_document()
        ├─→ Extract text (PDF/DOCX/TXT)
        ├─→ Classify document type
        ├─→ Enrich metadata from content
        ├─→ Create Document object
        ├─→ Semantic chunking (NodeParser)
        ├─→ Generate embeddings per chunk
        └─→ Store in Qdrant + metadata DB
        ↓
Return success + doc_id + chunk_count
        ↓
Update Streamlit UI (document library)
```

### Query Generation Flow

```
User enters query + selects parameters
        ↓
POST /api/query/stream
        ↓
RetrievalEngine.retrieve()
        ├─→ Process query (expand, clean)
        ├─→ Generate query embedding
        ├─→ Vector search (Qdrant)
        ├─→ Keyword search (BM25)
        ├─→ Hybrid scoring
        ├─→ Apply recency weighting
        ├─→ Re-rank results
        ├─→ Diversify sources
        └─→ Return top-k chunks
        ↓
PromptManager.build_system_prompt()
        ├─→ Layer prompts (role + brand + audience + section)
        └─→ Return composed prompt
        ↓
GenerationService.generate_streaming()
        ├─→ Format context from retrieved chunks
        ├─→ Build user message with instructions
        ├─→ Call Claude API (streaming)
        └─→ Stream tokens back
        ↓
QualityValidator.validate()
        ├─→ Calculate confidence
        ├─→ Check groundedness
        ├─→ Validate completeness
        ├─→ Detect contradictions
        └─→ Return validation result
        ↓
CitationManager.process_citations()
        ├─→ Extract citation markers
        ├─→ Map to sources
        ├─→ Format per style
        └─→ Generate bibliography
        ↓
Stream response + sources + quality metrics to frontend
        ↓
Streamlit displays in chat + artifact
```

### Chat Conversation Flow

```
User sends message in chat
        ↓
Append to conversation history (session_state)
        ↓
POST /api/chat
        ├─→ Include conversation context (last N messages)
        ├─→ Determine if RAG needed (query intent)
        └─→ If RAG: follow Query Generation Flow
        ↓
Assistant response generated
        ↓
Append to conversation history
        ↓
Display in chat interface
        ↓
Auto-save conversation periodically
```

---

## Deployment Architecture

### Docker Compose Configuration

```yaml
version: '3.8'

services:
  # Frontend - Streamlit
  frontend:
    build: ./frontend
    ports:
      - "8501:8501"
    environment:
      - BACKEND_URL=http://backend:8000
    depends_on:
      - backend
    volumes:
      - ./frontend:/app
    restart: unless-stopped

  # Backend - FastAPI
  backend:
    build: ./backend
    ports:
      - "8000:8000"
    environment:
      - ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY}
      - QDRANT_HOST=qdrant
      - QDRANT_PORT=6333
      - DATABASE_URL=postgresql://user:pass@postgres:5432/foundation_historian
    depends_on:
      - qdrant
      - postgres
    volumes:
      - ./backend:/app
      - ./data/documents:/app/documents
    restart: unless-stopped

  # Vector Database - Qdrant
  qdrant:
    image: qdrant/qdrant:latest
    ports:
      - "6333:6333"
      - "6334:6334"
    volumes:
      - qdrant_storage:/qdrant/storage
    restart: unless-stopped

  # Metadata Database - PostgreSQL (production)
  postgres:
    image: postgres:15
    environment:
      - POSTGRES_USER=user
      - POSTGRES_PASSWORD=pass
      - POSTGRES_DB=foundation_historian
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data
    restart: unless-stopped

volumes:
  qdrant_storage:
  postgres_data:
```

### Network Architecture

```
                    ┌──────────────┐
                    │   Internet   │
                    └──────┬───────┘
                           │
                    ┌──────▼───────┐
                    │   Firewall   │
                    │   (443/80)   │
                    └──────┬───────┘
                           │
                  ┌────────▼─────────┐
                  │  Reverse Proxy   │
                  │     (Nginx)      │
                  └────────┬─────────┘
                           │
              ┌────────────┴────────────┐
              │                         │
        ┌─────▼──────┐          ┌──────▼─────┐
        │  Frontend  │          │   Backend  │
        │ (Streamlit)│◄────────►│  (FastAPI) │
        │   :8501    │          │   :8000    │
        └────────────┘          └──────┬─────┘
                                       │
                          ┌────────────┴────────────┐
                          │                         │
                    ┌─────▼──────┐          ┌──────▼──────┐
                    │   Qdrant   │          │  PostgreSQL │
                    │   :6333    │          │    :5432    │
                    └────────────┘          └─────────────┘
```

---

## Security Architecture

### Authentication & Authorization (Future)

```
┌─────────────┐
│    User     │
└──────┬──────┘
       │ Login credentials
       ▼
┌─────────────────┐
│  Auth Service   │
│  (JWT tokens)   │
└──────┬──────────┘
       │ JWT token
       ▼
┌─────────────────┐
│   API Gateway   │
│ (Token verify)  │
└──────┬──────────┘
       │ Authorized request
       ▼
┌─────────────────┐
│   Backend API   │
└─────────────────┘
```

### Data Security

**At Rest:**
- Document files encrypted on disk
- Database encryption (Transparent Data Encryption)
- Environment variables for secrets

**In Transit:**
- HTTPS/TLS for all external communication
- Internal service communication over private network
- API keys in headers, not URLs

**Access Control:**
- Role-based access (admin, writer, viewer)
- Document-level permissions (future)
- Audit logging of all operations

---

## Monitoring & Logging

### Logging Architecture

```
Application Logs
       ├─→ Stdout (Docker logs)
       ├─→ File (rotating logs)
       └─→ Log aggregation (future: ELK stack)

Log Levels:
- DEBUG: Detailed diagnostic info
- INFO: General operational events
- WARNING: Unusual but handled events
- ERROR: Operation failures
- CRITICAL: System failures
```

### Metrics to Track

**System Metrics:**
- CPU/Memory usage per container
- Disk usage (documents + embeddings)
- Network I/O

**Application Metrics:**
- Request latency (p50, p95, p99)
- Error rates by endpoint
- Active users/sessions

**Business Metrics:**
- Documents uploaded per day
- Queries per day
- Average confidence scores
- User satisfaction ratings
- Most used documents
- API costs (Claude)

### Health Checks

```python
@app.get("/api/health")
async def health_check():
    checks = {
        "status": "healthy",
        "checks": {
            "qdrant": await check_qdrant(),
            "postgres": await check_postgres(),
            "anthropic_api": await check_anthropic(),
            "disk_space": check_disk_space()
        }
    }
    
    if any(not c for c in checks["checks"].values()):
        checks["status"] = "unhealthy"
        raise HTTPException(status_code=503, detail=checks)
    
    return checks
```

---

## Performance Considerations

### Caching Strategy

```
Query Cache (LRU):
├─→ Cache retrieved results for identical queries
├─→ TTL: 1 hour
└─→ Max size: 1000 entries

Embedding Cache:
├─→ Cache embeddings for duplicate chunks
├─→ Persistent across restarts
└─→ Reduces re-computation

Response Cache:
├─→ Cache complete responses for repeated queries
├─→ TTL: 30 minutes
└─→ Invalidate on document updates
```

### Optimization Techniques

**Document Processing:**
- Batch embedding generation (20-50 chunks at once)
- Async file I/O
- Parallel processing for multiple uploads

**Retrieval:**
- Index optimization in Qdrant (HNSW)
- Query result caching
- Pre-compute common filters

**Generation:**
- Streaming responses for immediate feedback
- Connection pooling for API calls
- Retry with exponential backoff

### Scalability

**Vertical Scaling:**
- Increase RAM for embedding model
- More CPU cores for parallel processing
- SSD for faster vector search

**Horizontal Scaling:**
- Load balancer for multiple backend instances
- Qdrant clustering for larger datasets
- Read replicas for PostgreSQL

**Expected Capacity:**
- Single server: 500 documents, 50K chunks
- With scaling: 10K+ documents, 1M+ chunks