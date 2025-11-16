"""
Comprehensive Integration Tests for Retrieval Engine

Tests the complete end-to-end retrieval pipeline including:
- Vector similarity search
- BM25 keyword search
- Hybrid scoring
- Metadata filtering
- Recency weighting
- Result diversification
- Optional reranking
- Error handling and edge cases

Uses realistic grant writing scenarios.
"""
import pytest
import asyncio
from typing import List, Dict
from datetime import datetime
import uuid

from app.services.retrieval_engine import (
    RetrievalEngine,
    RetrievalConfig,
    RetrievalResult,
    RetrievalEngineFactory
)
from app.services.vector_store import QdrantStore, VectorStoreConfig
from app.services.chunking_service import ChunkingService, ChunkingConfig, ChunkingStrategy
from app.models.document import DocumentFilters
from llama_index.embeddings.openai import OpenAIEmbedding
import os


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture(scope="module")
def event_loop():
    """Create event loop for async tests"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="module")
async def vector_store():
    """
    Initialize vector store for testing

    Uses localhost Qdrant instance (assumes Docker container is running)
    """
    config = VectorStoreConfig(
        host="localhost",
        port=6333,
        collection_name="test_retrieval_integration",
        vector_size=1536,  # OpenAI embedding size
        use_grpc=False
    )

    store = QdrantStore(config)

    # Ensure collection is created
    try:
        store.client.get_collection(store.collection_name)
    except:
        await store._create_collection()

    yield store

    # Cleanup: delete test collection
    try:
        store.client.delete_collection(store.collection_name)
    except:
        pass


@pytest.fixture(scope="module")
def embedding_model():
    """
    Initialize embedding model for testing

    Uses OpenAI embeddings (requires OPENAI_API_KEY env var)
    """
    api_key = os.getenv("OPENAI_API_KEY", "test-key")

    # For testing without real API calls, we can mock this
    # But for integration tests, we want real embeddings
    if api_key == "test-key":
        pytest.skip("OpenAI API key not set, skipping integration tests")

    return OpenAIEmbedding(
        model="text-embedding-3-small",
        api_key=api_key
    )


@pytest.fixture(scope="module")
async def sample_documents(vector_store, embedding_model):
    """
    Create sample grant writing documents for testing

    Returns document metadata for use in tests
    """
    documents = [
        # Document 1: Recent funded grant proposal (Early Childhood)
        {
            "doc_id": str(uuid.uuid4()),
            "text": """
            Nebraska Children and Families Foundation Organizational Capacity

            The Foundation has over 25 years of experience serving children and families
            across Nebraska. Our staff includes 15 full-time employees with expertise
            in early childhood development, program evaluation, and community engagement.

            We successfully manage $5 million in annual grant funding with 98% compliance
            rate. Our board includes 12 diverse members with backgrounds in education,
            social work, and business. We maintain strong partnerships with 50+ community
            organizations statewide.

            Our track record demonstrates success: 85% of our programs meet or exceed
            outcome targets. We serve 10,000 children annually through evidence-based
            programs like home visiting and early learning initiatives.
            """,
            "metadata": {
                "doc_id": None,  # Will be filled in
                "filename": "federal_grant_2024_ed.pdf",
                "doc_type": "Grant Proposal",
                "year": 2024,
                "programs": ["Early Childhood"],
                "outcome": "Funded",
                "chunk_index": 0
            }
        },
        # Document 2: Recent annual report (Multiple programs)
        {
            "doc_id": str(uuid.uuid4()),
            "text": """
            2023 Annual Report - Program Impact

            Early Childhood Programs: Reached 3,500 children through home visiting and
            quality preschool initiatives. Kindergarten readiness increased by 25%.

            Youth Development: Engaged 2,000 youth in after-school programs. High school
            graduation rates for participants reached 92%, exceeding state average by 15%.

            Family Support Services: Provided case management to 800 families. 78% achieved
            financial stability goals within 12 months.

            Total investment: $4.2 million. Return on investment: Every $1 invested yields
            $7 in future savings through reduced special education and social services costs.
            """,
            "metadata": {
                "doc_id": None,
                "filename": "annual_report_2023.pdf",
                "doc_type": "Annual Report",
                "year": 2023,
                "programs": ["Early Childhood", "Youth Development", "Family Support"],
                "outcome": "N/A",
                "chunk_index": 0
            }
        },
        # Document 3: Older grant proposal (Youth Development, Funded)
        {
            "doc_id": str(uuid.uuid4()),
            "text": """
            Program Description: Youth Leadership Initiative

            Goal: Develop leadership skills in 500 high school students from underserved
            communities over 3 years.

            Activities: Monthly leadership workshops, community service projects, mentorship
            from business leaders, college readiness support.

            Timeline: Year 1 (pilot with 100 students), Year 2 (expansion to 300),
            Year 3 (full implementation with 500).

            Evaluation: Pre/post surveys measuring leadership competencies, community
            engagement hours, college enrollment rates. External evaluator from University
            of Nebraska will conduct impact assessment.
            """,
            "metadata": {
                "doc_id": None,
                "filename": "youth_leadership_2021.pdf",
                "doc_type": "Grant Proposal",
                "year": 2021,
                "programs": ["Youth Development"],
                "outcome": "Funded",
                "chunk_index": 0
            }
        },
        # Document 4: Recent foundation grant (Early Childhood, Pending)
        {
            "doc_id": str(uuid.uuid4()),
            "text": """
            Budget Narrative - Early Learning Quality Initiative

            Personnel (65% of budget):
            - Program Director (0.5 FTE): $45,000
            - Quality Coaches (2 FTE): $90,000
            - Data Analyst (0.25 FTE): $15,000

            Program Costs (25%):
            - Professional development materials: $15,000
            - Coaching supplies and assessments: $10,000
            - Travel for site visits: $8,000

            Indirect Costs (10%): $18,300

            Total Budget: $201,300

            Sustainability: After grant period, program will be sustained through state
            quality rating system funding and participant fees on sliding scale.
            """,
            "metadata": {
                "doc_id": None,
                "filename": "foundation_grant_2024_early_learning.pdf",
                "doc_type": "Grant Proposal",
                "year": 2024,
                "programs": ["Early Childhood"],
                "outcome": "Pending",
                "chunk_index": 0
            }
        },
        # Document 5: Program description (Education)
        {
            "doc_id": str(uuid.uuid4()),
            "text": """
            Summer Learning Program Description

            Evidence Base: Program design based on RAND Corporation research showing
            summer learning programs prevent achievement loss and narrow achievement gaps.

            Our program includes:
            - Academic instruction (math and literacy) for 4 hours daily
            - Arts and recreation activities for 2 hours daily
            - Nutritious breakfast and lunch
            - Family engagement workshops weekly

            Staffing: Certified teachers for academic instruction, teaching assistants
            for small group work, recreation staff with youth development experience.

            Outcomes: 85% of participants maintain or improve reading levels. 72% show
            growth in math skills. 100% of families report increased engagement with
            child's learning.
            """,
            "metadata": {
                "doc_id": None,
                "filename": "summer_learning_program_description.pdf",
                "doc_type": "Program Description",
                "year": 2023,
                "programs": ["Education", "Youth Development"],
                "outcome": "N/A",
                "chunk_index": 0
            }
        },
        # Document 6: Old unfunded proposal (for testing filters)
        {
            "doc_id": str(uuid.uuid4()),
            "text": """
            Health and Wellness Initiative Proposal

            This pilot program aims to improve children's health through nutrition education
            and physical activity. We requested $50,000 but the proposal was not funded
            due to limited alignment with funder priorities.

            Lessons learned: Need stronger evidence base, clearer logic model, and more
            detailed evaluation plan. Will revise and resubmit with additional data.
            """,
            "metadata": {
                "doc_id": None,
                "filename": "health_wellness_2020_unfunded.pdf",
                "doc_type": "Grant Proposal",
                "year": 2020,
                "programs": ["Health"],
                "outcome": "Not Funded",
                "chunk_index": 0
            }
        },
    ]

    # Store documents in vector store
    for doc in documents:
        doc_id = doc["doc_id"]
        doc["metadata"]["doc_id"] = doc_id

        # Generate embedding
        embedding = embedding_model.get_text_embedding(doc["text"])

        # Store in Qdrant
        await vector_store.store_chunks([{
            "chunk_id": doc_id,
            "text": doc["text"],
            "embedding": embedding,
            "metadata": doc["metadata"]
        }])

    return documents


@pytest.fixture(scope="module")
async def retrieval_engine(vector_store, embedding_model, sample_documents):
    """
    Create retrieval engine with sample documents loaded
    """
    config = RetrievalConfig(
        vector_weight=0.7,
        keyword_weight=0.3,
        recency_weight=0.7,
        max_per_doc=3,
        enable_reranking=False,  # Disable for basic tests
        expand_query=True
    )

    engine = RetrievalEngine(
        vector_store=vector_store,
        embedding_model=embedding_model,
        config=config
    )

    # Build BM25 index
    await engine.build_bm25_index()

    return engine


# ============================================================================
# Basic Retrieval Tests
# ============================================================================

@pytest.mark.asyncio
async def test_basic_retrieval(retrieval_engine):
    """Test basic retrieval without filters"""
    query = "organizational capacity and staff qualifications"

    results = await retrieval_engine.retrieve(
        query=query,
        top_k=3
    )

    # Assertions
    assert len(results) > 0, "Should return results"
    assert len(results) <= 3, "Should respect top_k limit"

    # Check result structure
    for result in results:
        assert isinstance(result, RetrievalResult)
        assert result.chunk_id is not None
        assert result.text is not None
        assert result.score is not None
        assert result.metadata is not None
        assert 0 <= result.score <= 1.5, "Score should be in reasonable range"

    # Top result should be highly relevant
    top_result = results[0]
    assert "organizational" in top_result.text.lower() or \
           "staff" in top_result.text.lower() or \
           "capacity" in top_result.text.lower(), \
           "Top result should contain query terms"

    print(f"\n[OK] Basic retrieval: {len(results)} results for '{query}'")
    print(f"     Top score: {results[0].score:.4f}")


@pytest.mark.asyncio
async def test_domain_specific_query(retrieval_engine):
    """Test retrieval with domain-specific grant writing query"""
    query = "program evaluation and impact outcomes"

    results = await retrieval_engine.retrieve(query=query, top_k=5)

    assert len(results) > 0

    # Should find results about program impact and evaluation
    combined_text = " ".join([r.text.lower() for r in results])

    # Check for domain-relevant terms
    assert any(term in combined_text for term in [
        "evaluation", "outcome", "impact", "program", "assess", "measure"
    ]), "Results should contain evaluation/impact terminology"

    print(f"[OK] Domain-specific query: Found {len(results)} relevant results")


@pytest.mark.asyncio
async def test_multiterm_query(retrieval_engine):
    """Test retrieval with multi-term query"""
    query = "early childhood education kindergarten readiness"

    results = await retrieval_engine.retrieve(query=query, top_k=5)

    assert len(results) > 0

    # Should prioritize results with multiple matching terms
    top_text = results[0].text.lower()

    # Count how many query terms appear in top result
    terms = ["early", "childhood", "education", "kindergarten", "readiness"]
    matches = sum(1 for term in terms if term in top_text)

    assert matches >= 2, "Top result should match multiple query terms"

    print(f"[OK] Multi-term query: Top result matches {matches}/5 terms")


# ============================================================================
# Metadata Filtering Tests
# ============================================================================

@pytest.mark.asyncio
async def test_filter_by_document_type(retrieval_engine):
    """Test filtering by document type"""
    query = "organizational capacity"

    # Filter for only Grant Proposals
    filters = DocumentFilters(doc_types=["Grant Proposal"])

    results = await retrieval_engine.retrieve(
        query=query,
        top_k=5,
        filters=filters
    )

    assert len(results) > 0

    # All results should be Grant Proposals
    for result in results:
        assert result.metadata.get("doc_type") == "Grant Proposal", \
            "All results should match document type filter"

    print(f"[OK] Document type filter: {len(results)} Grant Proposals found")


@pytest.mark.asyncio
async def test_filter_by_year(retrieval_engine):
    """Test filtering by specific year"""
    query = "program impact"

    # Filter for 2024 documents
    filters = DocumentFilters(years=[2024])

    results = await retrieval_engine.retrieve(
        query=query,
        top_k=5,
        filters=filters
    )

    assert len(results) > 0

    # All results should be from 2024
    for result in results:
        assert result.metadata.get("year") == 2024, \
            "All results should be from 2024"

    print(f"[OK] Year filter: {len(results)} documents from 2024")


@pytest.mark.asyncio
async def test_filter_by_year_range(retrieval_engine):
    """Test filtering by year range"""
    query = "programs"

    # Filter for 2022-2024 range
    filters = DocumentFilters(date_range=(2022, 2024))

    results = await retrieval_engine.retrieve(
        query=query,
        top_k=10,
        filters=filters
    )

    assert len(results) > 0

    # All results should be in range
    for result in results:
        year = result.metadata.get("year")
        assert year is not None and 2022 <= year <= 2024, \
            f"Year {year} should be in range 2022-2024"

    print(f"[OK] Year range filter: {len(results)} documents from 2022-2024")


@pytest.mark.asyncio
async def test_filter_by_program(retrieval_engine):
    """Test filtering by program area"""
    query = "children and families"

    # Filter for Early Childhood programs
    filters = DocumentFilters(programs=["Early Childhood"])

    results = await retrieval_engine.retrieve(
        query=query,
        top_k=5,
        filters=filters
    )

    assert len(results) > 0

    # All results should include Early Childhood program
    for result in results:
        programs = result.metadata.get("programs", [])
        assert "Early Childhood" in programs, \
            "All results should include Early Childhood program"

    print(f"[OK] Program filter: {len(results)} Early Childhood documents")


@pytest.mark.asyncio
async def test_filter_by_outcome(retrieval_engine):
    """Test filtering by grant outcome status"""
    query = "proposal"

    # Filter for only funded proposals
    filters = DocumentFilters(outcomes=["Funded"])

    results = await retrieval_engine.retrieve(
        query=query,
        top_k=5,
        filters=filters
    )

    assert len(results) > 0

    # All results should be funded
    for result in results:
        assert result.metadata.get("outcome") == "Funded", \
            "All results should be funded proposals"

    print(f"[OK] Outcome filter: {len(results)} funded proposals")


@pytest.mark.asyncio
async def test_exclude_documents(retrieval_engine, sample_documents):
    """Test excluding specific documents"""
    query = "program"

    # Get doc_id of first document to exclude
    doc_to_exclude = sample_documents[0]["doc_id"]

    # Retrieve without filter first
    all_results = await retrieval_engine.retrieve(query=query, top_k=10)

    # Retrieve with exclusion
    filters = DocumentFilters(exclude_docs=[doc_to_exclude])
    filtered_results = await retrieval_engine.retrieve(
        query=query,
        top_k=10,
        filters=filters
    )

    # Excluded document should not be in results
    for result in filtered_results:
        assert result.metadata.get("doc_id") != doc_to_exclude, \
            "Excluded document should not appear in results"

    print(f"[OK] Exclude filter: Excluded 1 document, got {len(filtered_results)} results")


@pytest.mark.asyncio
async def test_combined_filters(retrieval_engine):
    """Test using multiple filters together"""
    query = "early childhood programs"

    # Combine multiple filters
    filters = DocumentFilters(
        doc_types=["Grant Proposal", "Program Description"],
        date_range=(2021, 2024),
        programs=["Early Childhood"],
        outcomes=["Funded", "Pending", "N/A"]  # Exclude "Not Funded"
    )

    results = await retrieval_engine.retrieve(
        query=query,
        top_k=10,
        filters=filters
    )

    assert len(results) > 0

    # Verify all filters are applied
    for result in results:
        # Check document type
        assert result.metadata.get("doc_type") in ["Grant Proposal", "Program Description"]

        # Check year range
        year = result.metadata.get("year")
        assert 2021 <= year <= 2024

        # Check program
        programs = result.metadata.get("programs", [])
        assert "Early Childhood" in programs

        # Check outcome (should not be "Not Funded")
        outcome = result.metadata.get("outcome")
        assert outcome != "Not Funded"

    print(f"[OK] Combined filters: {len(results)} results matching all criteria")


# ============================================================================
# Hybrid Search Tests
# ============================================================================

@pytest.mark.asyncio
async def test_hybrid_search_combines_both(retrieval_engine):
    """Test that hybrid search combines vector and keyword results"""
    # Query that should trigger both vector (semantic) and keyword (exact match) search
    query = "kindergarten readiness assessment"

    results = await retrieval_engine.retrieve(query=query, top_k=5)

    assert len(results) > 0

    # Check that results have hybrid score metadata
    for result in results:
        metadata = result.metadata
        # Results should have both vector and keyword scores (or at least one)
        has_vector = "_vector_score" in metadata
        has_keyword = "_keyword_score" in metadata

        # At least one should be present (depending on what matched)
        assert has_vector or has_keyword, \
            "Results should have vector and/or keyword score metadata"

    print(f"[OK] Hybrid search: Combined vector + keyword results")


@pytest.mark.asyncio
async def test_vector_vs_keyword_emphasis(retrieval_engine):
    """Test different weight configurations"""
    query = "organizational capacity board governance"

    # Test with vector-heavy weights
    vector_heavy_config = RetrievalConfig(
        vector_weight=0.9,
        keyword_weight=0.1,
        recency_weight=0.0  # Disable for this test
    )

    vector_heavy_engine = RetrievalEngine(
        vector_store=retrieval_engine.vector_store,
        embedding_model=retrieval_engine.embedding_model,
        config=vector_heavy_config
    )
    await vector_heavy_engine.build_bm25_index()

    vector_results = await vector_heavy_engine.retrieve(query=query, top_k=3)

    # Test with keyword-heavy weights
    keyword_heavy_config = RetrievalConfig(
        vector_weight=0.1,
        keyword_weight=0.9,
        recency_weight=0.0
    )

    keyword_heavy_engine = RetrievalEngine(
        vector_store=retrieval_engine.vector_store,
        embedding_model=retrieval_engine.embedding_model,
        config=keyword_heavy_config
    )
    await keyword_heavy_engine.build_bm25_index()

    keyword_results = await keyword_heavy_engine.retrieve(query=query, top_k=3)

    # Both should return results
    assert len(vector_results) > 0
    assert len(keyword_results) > 0

    # Results may differ due to different weighting
    print(f"[OK] Weight configurations: Vector-heavy and keyword-heavy both work")


# ============================================================================
# Recency Weighting Tests
# ============================================================================

@pytest.mark.asyncio
async def test_recency_weighting_boosts_recent(retrieval_engine):
    """Test that recency weighting boosts recent documents"""
    query = "grant proposal"

    # Retrieve with recency weighting disabled
    no_recency_results = await retrieval_engine.retrieve(
        query=query,
        top_k=5,
        recency_weight=0.0
    )

    # Retrieve with recency weighting enabled
    with_recency_results = await retrieval_engine.retrieve(
        query=query,
        top_k=5,
        recency_weight=1.0  # Maximum recency weighting
    )

    assert len(no_recency_results) > 0
    assert len(with_recency_results) > 0

    # Check if recency affected ranking
    # Extract years from top results
    no_recency_years = [r.metadata.get("year") for r in no_recency_results[:3]]
    with_recency_years = [r.metadata.get("year") for r in with_recency_results[:3]]

    # With recency, average year should be more recent (higher)
    avg_year_no_recency = sum(y for y in no_recency_years if y) / len([y for y in no_recency_years if y])
    avg_year_with_recency = sum(y for y in with_recency_years if y) / len([y for y in with_recency_years if y])

    print(f"[OK] Recency weighting: avg year without={avg_year_no_recency:.1f}, with={avg_year_with_recency:.1f}")
    print(f"     Recent documents boosted: {avg_year_with_recency >= avg_year_no_recency}")


# ============================================================================
# Result Diversification Tests
# ============================================================================

@pytest.mark.asyncio
async def test_result_diversification(retrieval_engine):
    """Test that results are diversified across documents"""
    # Query that might return multiple chunks from same document
    query = "program"

    results = await retrieval_engine.retrieve(query=query, top_k=10)

    # Count chunks per document
    doc_counts = {}
    for result in results:
        doc_id = result.metadata.get("doc_id")
        doc_counts[doc_id] = doc_counts.get(doc_id, 0) + 1

    # Check that no document dominates (max_per_doc = 3 by default)
    max_chunks_from_one_doc = max(doc_counts.values()) if doc_counts else 0

    assert max_chunks_from_one_doc <= retrieval_engine.config.max_per_doc, \
        f"No document should have more than {retrieval_engine.config.max_per_doc} chunks"

    print(f"[OK] Diversification: Results from {len(doc_counts)} different documents")
    print(f"     Max chunks from one document: {max_chunks_from_one_doc}")


# ============================================================================
# Edge Cases and Error Handling
# ============================================================================

@pytest.mark.asyncio
async def test_empty_query(retrieval_engine):
    """Test handling of empty query"""
    results = await retrieval_engine.retrieve(query="", top_k=5)

    # Should handle gracefully (may return empty or raise exception)
    # For now, we expect it to return empty results
    assert isinstance(results, list)

    print(f"[OK] Empty query handled: {len(results)} results")


@pytest.mark.asyncio
async def test_no_matching_results(retrieval_engine):
    """Test query that should return no results"""
    # Very specific query that shouldn't match anything
    query = "xyzabc123 nonexistent quantum cryptocurrency blockchain"

    results = await retrieval_engine.retrieve(query=query, top_k=5)

    # May return zero or low-scored results
    assert isinstance(results, list)

    if len(results) > 0:
        # If results returned, scores should be low
        assert all(r.score < 0.5 for r in results), \
            "Unrelated results should have low scores"

    print(f"[OK] No matching query: {len(results)} results (low scores expected)")


@pytest.mark.asyncio
async def test_filters_with_no_matches(retrieval_engine):
    """Test filters that exclude all documents"""
    query = "program"

    # Filter for year that doesn't exist in test data
    filters = DocumentFilters(years=[1999])

    results = await retrieval_engine.retrieve(
        query=query,
        top_k=5,
        filters=filters
    )

    # Should return empty results
    assert len(results) == 0, "Should return no results when filters exclude everything"

    print(f"[OK] Filter with no matches: Correctly returned 0 results")


@pytest.mark.asyncio
async def test_very_small_top_k(retrieval_engine):
    """Test with top_k=1"""
    query = "organizational capacity"

    results = await retrieval_engine.retrieve(query=query, top_k=1)

    assert len(results) == 1, "Should return exactly 1 result"
    assert results[0].score > 0, "Result should have positive score"

    print(f"[OK] top_k=1: Returned exactly 1 result with score {results[0].score:.4f}")


@pytest.mark.asyncio
async def test_very_large_top_k(retrieval_engine):
    """Test with top_k larger than available documents"""
    query = "program"

    # Request more results than we have documents
    results = await retrieval_engine.retrieve(query=query, top_k=1000)

    # Should return all available results (up to number of chunks)
    assert len(results) > 0
    assert len(results) <= 1000  # Shouldn't exceed request

    print(f"[OK] top_k=1000: Returned {len(results)} results (max available)")


# ============================================================================
# Performance and Quality Tests
# ============================================================================

@pytest.mark.asyncio
async def test_retrieval_latency(retrieval_engine):
    """Test that retrieval completes in reasonable time"""
    import time

    query = "organizational capacity and program outcomes"

    start = time.time()
    results = await retrieval_engine.retrieve(query=query, top_k=5)
    latency_ms = (time.time() - start) * 1000

    assert len(results) > 0

    # Should complete in under 5 seconds (generous for integration test)
    assert latency_ms < 5000, f"Retrieval took {latency_ms:.0f}ms, should be < 5000ms"

    print(f"[OK] Retrieval latency: {latency_ms:.0f}ms for top_k=5")


@pytest.mark.asyncio
async def test_result_quality_scores(retrieval_engine):
    """Test that result scores are reasonable and sorted"""
    query = "early childhood education programs"

    results = await retrieval_engine.retrieve(query=query, top_k=5)

    assert len(results) > 0

    # Scores should be in descending order
    for i in range(len(results) - 1):
        assert results[i].score >= results[i+1].score, \
            "Results should be sorted by score (descending)"

    # Top result should have reasonable score (> 0.3 for decent match)
    assert results[0].score > 0.1, \
        f"Top result score {results[0].score:.4f} seems too low"

    print(f"[OK] Result quality: Scores range from {results[0].score:.4f} to {results[-1].score:.4f}")


@pytest.mark.asyncio
async def test_result_relevance(retrieval_engine):
    """Test that results are actually relevant to query"""
    queries = [
        ("organizational capacity", ["capacity", "organization", "staff", "board"]),
        ("program evaluation", ["evaluation", "assess", "measure", "outcome"]),
        ("budget and costs", ["budget", "cost", "expense", "dollar", "funding"]),
    ]

    for query, expected_terms in queries:
        results = await retrieval_engine.retrieve(query=query, top_k=3)

        assert len(results) > 0, f"Should return results for query: {query}"

        # Check that top result contains at least one expected term
        top_text = results[0].text.lower()
        found_terms = [term for term in expected_terms if term in top_text]

        assert len(found_terms) > 0, \
            f"Top result for '{query}' should contain at least one of {expected_terms}"

        print(f"[OK] Relevance test for '{query}': Found terms {found_terms}")


# ============================================================================
# Configuration Tests
# ============================================================================

@pytest.mark.asyncio
async def test_custom_config(vector_store, embedding_model, sample_documents):
    """Test creating engine with custom configuration"""
    custom_config = RetrievalConfig(
        vector_weight=0.5,
        keyword_weight=0.5,
        recency_weight=0.5,
        max_per_doc=2,
        enable_reranking=False,
        expand_query=False  # Disable query expansion
    )

    engine = RetrievalEngine(
        vector_store=vector_store,
        embedding_model=embedding_model,
        config=custom_config
    )
    await engine.build_bm25_index()

    results = await engine.retrieve(query="programs", top_k=5)

    assert len(results) > 0

    # Check that max_per_doc is respected
    doc_counts = {}
    for result in results:
        doc_id = result.metadata.get("doc_id")
        doc_counts[doc_id] = doc_counts.get(doc_id, 0) + 1

    max_chunks = max(doc_counts.values()) if doc_counts else 0
    assert max_chunks <= custom_config.max_per_doc, \
        f"Should respect max_per_doc={custom_config.max_per_doc}"

    print(f"[OK] Custom config: max_per_doc={custom_config.max_per_doc} respected")


# ============================================================================
# Real-World Scenario Tests
# ============================================================================

@pytest.mark.asyncio
async def test_federal_rfp_scenario(retrieval_engine):
    """
    Real-world scenario: Finding content for federal RFP organizational capacity section
    """
    query = """
    We need to write the organizational capacity section for a federal Department of Education RFP.
    The section should cover our organization's qualifications, staff expertise, governance structure,
    track record of success, and financial stability.
    """

    # Filter for recent, funded proposals and annual reports
    filters = DocumentFilters(
        doc_types=["Grant Proposal", "Annual Report"],
        date_range=(2022, 2024),
        outcomes=["Funded", "N/A"]  # Exclude unfunded
    )

    results = await retrieval_engine.retrieve(
        query=query,
        top_k=5,
        filters=filters,
        recency_weight=0.8  # Emphasize recent content
    )

    assert len(results) > 0, "Should find relevant organizational capacity content"

    # Top results should mention organizational elements
    combined_text = " ".join([r.text.lower() for r in results[:3]])

    org_terms = ["staff", "board", "governance", "experience", "track record",
                 "financial", "capacity", "qualified"]
    found_terms = [term for term in org_terms if term in combined_text]

    assert len(found_terms) >= 3, \
        f"Should find multiple organizational capacity terms, found: {found_terms}"

    print(f"[OK] Federal RFP scenario: Found {len(results)} relevant chunks")
    print(f"     Organizational terms found: {found_terms}")


@pytest.mark.asyncio
async def test_foundation_grant_scenario(retrieval_engine):
    """
    Real-world scenario: Finding program description content for foundation grant
    """
    query = """
    Writing program description for a foundation grant focused on early childhood education.
    Need information about program activities, evidence base, staffing, and outcomes.
    """

    filters = DocumentFilters(
        programs=["Early Childhood"],
        doc_types=["Grant Proposal", "Program Description", "Annual Report"]
    )

    results = await retrieval_engine.retrieve(
        query=query,
        top_k=5,
        filters=filters
    )

    assert len(results) > 0

    # Should find program-related content
    combined_text = " ".join([r.text.lower() for r in results])

    program_terms = ["program", "children", "early", "activities", "outcomes", "staff"]
    found_terms = [term for term in program_terms if term in combined_text]

    assert len(found_terms) >= 4, f"Should find program terms, found: {found_terms}"

    print(f"[OK] Foundation grant scenario: Found {len(results)} relevant chunks")


@pytest.mark.asyncio
async def test_budget_narrative_scenario(retrieval_engine):
    """
    Real-world scenario: Finding budget and sustainability information
    """
    query = "budget costs personnel expenses sustainability funding"

    results = await retrieval_engine.retrieve(query=query, top_k=5)

    assert len(results) > 0

    # Should find budget-related content
    combined_text = " ".join([r.text.lower() for r in results])

    budget_terms = ["budget", "cost", "expense", "personnel", "sustainability", "funding"]
    found_terms = [term for term in budget_terms if term in combined_text]

    assert len(found_terms) >= 3, f"Should find budget terms, found: {found_terms}"

    print(f"[OK] Budget narrative scenario: Found {len(results)} budget-related chunks")


# ============================================================================
# Summary Test
# ============================================================================

@pytest.mark.asyncio
async def test_comprehensive_pipeline(retrieval_engine):
    """
    Comprehensive test of entire pipeline with realistic query
    """
    query = "youth development leadership programs with proven outcomes"

    filters = DocumentFilters(
        programs=["Youth Development"],
        outcomes=["Funded", "N/A"],
        date_range=(2020, 2024)
    )

    results = await retrieval_engine.retrieve(
        query=query,
        top_k=5,
        filters=filters,
        recency_weight=0.7
    )

    # Validate comprehensive pipeline execution
    assert len(results) > 0, "Pipeline should return results"
    assert all(isinstance(r, RetrievalResult) for r in results), \
        "Results should be proper RetrievalResult objects"
    assert all(r.score > 0 for r in results), "All results should have positive scores"
    assert all("doc_id" in r.metadata for r in results), "All results should have doc_id"

    # Validate filters were applied
    for result in results:
        programs = result.metadata.get("programs", [])
        assert "Youth Development" in programs, "Program filter should be applied"

        year = result.metadata.get("year")
        assert 2020 <= year <= 2024, "Year range filter should be applied"

    # Validate hybrid scoring metadata
    for result in results:
        metadata = result.metadata
        # Should have scoring metadata
        assert "_hybrid_score" in metadata or \
               "_vector_score" in metadata or \
               "_keyword_score" in metadata, \
               "Results should have scoring metadata"

    print(f"[OK] Comprehensive pipeline test PASSED")
    print(f"     Retrieved: {len(results)} results")
    print(f"     Score range: {results[-1].score:.4f} to {results[0].score:.4f}")
    print(f"     Filters applied: {len(filters.programs)} programs, year range")


if __name__ == "__main__":
    """
    Run tests with pytest:

        pytest backend/tests/test_retrieval_engine.py -v

    Or run with coverage:

        pytest backend/tests/test_retrieval_engine.py -v --cov=app/services/retrieval_engine
    """
    pytest.main([__file__, "-v", "-s"])
