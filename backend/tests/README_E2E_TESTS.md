# End-to-End Document Processing Tests

## Overview

This document describes the comprehensive end-to-end integration tests for the Org Archivist document processing pipeline in `test_e2e_document_processing.py`.

## Purpose

These tests validate the **complete document processing pipeline** from file upload through storage and retrieval:

1. **Document Upload** - Accept PDF, DOCX, and TXT files
2. **Text Extraction** - Extract text from various formats
3. **Metadata Enrichment** - Parse filenames and extract document properties
4. **Semantic Chunking** - Split documents into meaningful chunks
5. **Embedding Generation** - Create vector embeddings for each chunk
6. **Vector Storage** - Store chunks with embeddings in Qdrant
7. **Database Storage** - Store metadata in PostgreSQL
8. **Retrieval** - Search and retrieve relevant content
9. **Cleanup** - Delete documents from all systems

## Test Coverage

### Document Format Tests

#### 1. `test_pdf_document_upload_and_processing`
- **Purpose**: Validate complete PDF processing pipeline
- **Validates**:
  - PDF text extraction (multi-page)
  - Page separator handling
  - Semantic chunking of PDF content
  - Vector storage with proper metadata
  - Database record creation
  - Chunk searchability
- **Sample Document**: 2-page grant proposal about youth STEM education

#### 2. `test_docx_document_upload_and_processing`
- **Purpose**: Validate complete DOCX processing pipeline
- **Validates**:
  - DOCX text extraction (paragraphs + tables)
  - Table content extraction
  - Metadata from DOCX properties
  - Storage and retrieval
- **Sample Document**: Annual report with tables and structured content

#### 3. `test_txt_document_upload_and_processing`
- **Purpose**: Validate complete TXT processing pipeline
- **Validates**:
  - TXT text extraction
  - Encoding detection (UTF-8)
  - Line ending normalization
  - Processing of plain text documents
- **Sample Document**: Budget narrative with line-based structure

### Error Handling Tests

#### 4. `test_invalid_file_handling`
- **Purpose**: Validate error handling for invalid inputs
- **Tests**:
  - Empty file rejection (0 bytes)
  - Invalid file type rejection (.exe files)
  - Corrupted file handling (invalid PDF structure)
- **Validates**: Graceful failure with appropriate error messages

### Metadata Tests

#### 5. `test_metadata_extraction_and_enrichment`
- **Purpose**: Validate metadata extraction and enrichment
- **Tests**:
  - Filename pattern parsing (`Org_Type_Year_Funder.pdf`)
  - Year extraction from filename
  - Document type inference
  - File size and structure metadata
- **Validates**: System can enrich minimal metadata from context

### Retrieval Tests

#### 6. `test_document_retrieval_after_upload`
- **Purpose**: Validate documents are searchable after upload
- **Tests**:
  - Basic similarity search works
  - Metadata filtering (by doc_id)
  - Relevance scoring (>0.5 threshold)
  - Search results contain expected content
- **Validates**: Complete upload → search workflow

### Concurrency Tests

#### 7. `test_concurrent_document_processing`
- **Purpose**: Validate concurrent document processing
- **Tests**:
  - Process multiple documents simultaneously
  - No data corruption during concurrent uploads
  - All documents stored correctly
  - Database integrity maintained
- **Validates**: System handles concurrent loads

### Deletion Tests

#### 8. `test_document_deletion_cascade`
- **Purpose**: Validate complete deletion across all systems
- **Tests**:
  - Chunks removed from Qdrant
  - Metadata removed from PostgreSQL
  - No orphaned data remains
  - Search returns no results after deletion
- **Validates**: Clean deletion cascade across systems

### Performance Tests

#### 9. `test_processing_performance`
- **Purpose**: Validate processing completes in reasonable time
- **Tests**:
  - Total processing time (<30s threshold)
  - Time per chunk calculation
  - Performance metrics capture
- **Validates**: System meets performance requirements

## Prerequisites

### Required Services

These tests require **real running services** (not mocks):

1. **Qdrant Vector Database**
   ```bash
   docker-compose up qdrant -d
   ```
   - Must be accessible at `localhost:6333`
   - HTTP API enabled

2. **PostgreSQL Database**
   ```bash
   docker-compose up postgres -d
   ```
   - Must be accessible at configured host/port
   - Database schema initialized (see `docker/postgres/init/`)

3. **Environment Variables**
   ```bash
   # Required for embeddings
   OPENAI_API_KEY=your_key_here
   # or
   VOYAGE_API_KEY=your_key_here

   # Database configuration
   POSTGRES_HOST=localhost
   POSTGRES_PORT=5432
   POSTGRES_USER=user
   POSTGRES_PASSWORD=password
   POSTGRES_DB=org_archivist

   # Qdrant configuration
   QDRANT_HOST=localhost
   QDRANT_PORT=6333
   ```

### Python Dependencies

Install all test dependencies:
```bash
cd backend
pip install -r requirements.txt
pip install reportlab  # For PDF generation in tests
```

## Running the Tests

### Run All E2E Tests
```bash
cd backend
python -m pytest tests/test_e2e_document_processing.py -v
```

### Run Specific Test
```bash
python -m pytest tests/test_e2e_document_processing.py::test_pdf_document_upload_and_processing -v
```

### Run with Output
```bash
python -m pytest tests/test_e2e_document_processing.py -v -s
```
The `-s` flag shows print statements, which provide detailed progress information.

### Run with Coverage
```bash
python -m pytest tests/test_e2e_document_processing.py --cov=app.services --cov=app.api --cov-report=html
```

## Test Output

Each test provides detailed console output:

```
=== Testing PDF Document Processing ===
Processing: Youth_STEM_Grant_2023_Foundation.pdf
File size: 4567 bytes
✓ Document processed: abc123-def456-...
✓ Chunks created: 3
✓ Found 3 chunks in Qdrant
✓ Chunk metadata validated
✓ Document metadata verified in PostgreSQL
  - Filename: Youth_STEM_Grant_2023_Foundation.pdf
  - Type: Grant Proposal
  - Chunks: 3
✓ Test data cleaned up
=== PDF Test PASSED ===
```

## Test Data Management

### Test Isolation
- Each test uses a **separate test collection** in Qdrant (`test_e2e_processing`)
- Test data is **automatically cleaned up** after each test
- Database records are deleted after verification
- No test data persists between runs

### Test Fixtures
- **sample_pdf_file**: Generates 2-page PDF with grant proposal content
- **sample_docx_file**: Generates DOCX with paragraphs and tables
- **sample_txt_file**: Generates plain text budget narrative
- **test_vector_store**: Qdrant store with test collection
- **test_database**: PostgreSQL connection with cleanup

### Cleanup Strategy
Each test follows this pattern:
```python
# 1. Upload and process document
result = await processor.process_document(...)
doc_id = result.doc_id

# 2. Perform validations
assert result.success
# ... more assertions

# 3. Always cleanup (even if assertions fail)
await test_vector_store.delete_document(doc_id)
await test_database.delete_document(UUID(doc_id))
```

## Expected Results

All 9 tests should **PASS** if:
- Qdrant is running and accessible
- PostgreSQL is running with schema initialized
- Valid API key configured for embeddings (OpenAI/Voyage)
- All dependencies installed

### Typical Execution Time
- **Individual test**: 5-15 seconds
- **Full suite**: 60-120 seconds (depending on API latency)

## Troubleshooting

### Common Issues

#### 1. Connection Errors
```
Error: Connection refused to localhost:6333
```
**Solution**: Start Qdrant container
```bash
docker-compose up qdrant -d
```

#### 2. Database Errors
```
Error: Database connection failed
```
**Solution**:
- Check PostgreSQL is running: `docker-compose ps postgres`
- Verify credentials in `.env` file
- Run schema initialization: `docker exec -i postgres psql ...`

#### 3. Embedding API Errors
```
Error: Invalid API key
```
**Solution**: Set valid API key in `.env`:
```bash
OPENAI_API_KEY=sk-...
```

#### 4. Import Errors
```
ModuleNotFoundError: No module named 'reportlab'
```
**Solution**: Install missing dependencies
```bash
pip install reportlab python-docx
```

#### 5. Test Collection Already Exists
```
Error: Collection test_e2e_processing already exists
```
**Solution**: Delete manually if cleanup failed
```bash
curl -X DELETE http://localhost:6333/collections/test_e2e_processing
```

## Integration with CI/CD

### GitHub Actions Example
```yaml
name: E2E Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    services:
      postgres:
        image: postgres:15
        env:
          POSTGRES_PASSWORD: testpass
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
      qdrant:
        image: qdrant/qdrant:latest
        ports:
          - 6333:6333

    steps:
      - uses: actions/checkout@v3
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: |
          cd backend
          pip install -r requirements.txt
          pip install reportlab

      - name: Run E2E tests
        env:
          OPENAI_API_KEY: ${{ secrets.OPENAI_API_KEY }}
          POSTGRES_HOST: localhost
          QDRANT_HOST: localhost
        run: |
          cd backend
          python -m pytest tests/test_e2e_document_processing.py -v
```

## Metrics and Validation

### Coverage Targets
- **Document Processor**: >85% coverage
- **Vector Store**: >80% coverage
- **Database Service**: >80% coverage
- **Extractors (PDF/DOCX/TXT)**: >75% coverage

### Performance Targets
- **PDF Processing**: <10s per document
- **DOCX Processing**: <8s per document
- **TXT Processing**: <5s per document
- **Concurrent Processing**: <15s for 2 documents
- **Retrieval Latency**: <2s per query

### Quality Metrics
- **Chunk Quality**: Text is clean and readable
- **Relevance Scores**: >0.5 for related queries
- **Metadata Accuracy**: 100% of required fields populated
- **Error Handling**: 100% of invalid inputs rejected gracefully

## Related Documentation

- **Document Processor**: `backend/app/services/document_processor.py`
- **Vector Store**: `backend/app/services/vector_store.py`
- **Database Service**: `backend/app/services/database.py`
- **Upload API**: `backend/app/api/documents.py`
- **Unit Tests**: `backend/tests/test_document_processor.py`

## Maintenance

### Updating Tests

When updating the document processing pipeline:

1. **Add new tests** for new features
2. **Update fixtures** if document structure changes
3. **Adjust performance thresholds** if infrastructure changes
4. **Update validation logic** if metadata schema changes

### Test Data Generation

Test documents are generated in-memory using:
- **reportlab**: For PDF generation
- **python-docx**: For DOCX generation
- **bytes/strings**: For TXT generation

To modify test documents, edit the fixture functions:
- `sample_pdf_file()`
- `sample_docx_file()`
- `sample_txt_file()`

## Summary

These E2E tests provide **comprehensive validation** of the complete document processing pipeline, ensuring:

✅ All file formats are supported (PDF, DOCX, TXT)
✅ Text extraction works correctly
✅ Metadata is enriched properly
✅ Chunks are created and stored
✅ Embeddings are generated
✅ Documents are searchable
✅ Deletion cascades properly
✅ Concurrent processing works
✅ Error handling is robust
✅ Performance is acceptable

This test suite validates the core functionality of the Org Archivist document processing system from end to end.
