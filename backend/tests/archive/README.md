# Archived Tests

This directory contains experimental, development, and issue-specific tests that were created during feature development but are not needed for long-term maintenance of the project.

## Purpose

These tests were valuable during development to validate specific implementations and debugging, but are archived rather than deleted to preserve historical context and potentially reuse test patterns in the future.

## Status

Tests in this directory are **NOT** run as part of the standard CI/CD pipeline or test suite. They are preserved for reference only.

## Archived Test Categories

### Integration Tests (Early Development)
- `test_integration.py` - Early integration test for document processor with extractors
- `test_upload_integration.py` - Upload integration validation
- `test_vector_search_integration.py` - Vector search integration testing
- `test_hybrid_integration.py` - Hybrid search integration tests

### Experimental Feature Tests
- `test_hybrid_scoring.py` - Hybrid scoring and result combination experiments
- `test_bm25_keyword_search.py` - BM25 keyword search implementation tests
- `test_reranking.py` - Reranking functionality tests
- `test_recency_weighting.py` - Recency weighting experiments

### Component Validation Tests
- `test_embedding_generation.py` - Embedding generation validation
- `test_semantic_chunking_validation.py` - Semantic chunking validation (task-specific)
- `test_generation_service.py` - Generation service testing
- `test_retrieval_structure.py` - Retrieval structure validation

### Extractor Tests
- `test_all_extractors.py` - All extractors integration test
- `test_pdf_extractor.py` - PDF extractor specific tests
- `test_metadata_extractor.py` - Metadata extractor tests

### Storage Tests
- `test_vector_store.py` - Vector store functionality tests

## When to Use These Tests

These tests may be useful as reference when:
1. Debugging similar issues or features
2. Understanding historical implementation decisions
3. Reusing test patterns or mock objects
4. Validating experimental features before production

## Migration to Production Tests

If an archived test becomes relevant for production maintenance:
1. Review and update the test to match current codebase
2. Move to appropriate directory in `backend/tests/`
3. Update test fixtures to use `conftest.py` patterns
4. Ensure test follows current testing standards
5. Add to CI/CD pipeline configuration

## Maintenance

This archive is reviewed periodically. Tests that are:
- No longer relevant or comprehensible may be deleted
- Found to be critical for production may be migrated back
- Superseded by better tests in production suite should be noted

Last organized: 2025-11-16
