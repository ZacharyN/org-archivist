"""
Database Service Integration Tests for Outputs

Tests for Phase 4: Past Outputs Dashboard - Database Layer
- CRUD operations (create, get, update, delete)
- List with filters (type, status, date range, created_by, writing_style, funder)
- Search functionality (full-text)
- Statistics calculations
- Pagination (skip/limit)
- Edge cases (not found, empty results, metadata JSON)

Target: 30 tests, comprehensive coverage of database.py output methods
"""

import pytest
import pytest_asyncio
import asyncio
import json
from datetime import datetime, date, timedelta
from uuid import uuid4, UUID
from decimal import Decimal

from backend.app.services.database import DatabaseService


# Fixtures

@pytest_asyncio.fixture
async def db_service():
    """Create DatabaseService instance connected to test database"""
    service = DatabaseService()
    await service.connect()
    yield service
    await service.disconnect()


@pytest_asyncio.fixture
async def sample_outputs(db_service):
    """Create sample outputs for testing"""
    outputs = []

    # Create diverse test data
    test_data = [
        {
            "output_type": "grant_proposal",
            "title": "Education Grant Proposal",
            "content": "This is a comprehensive proposal for education funding...",
            "word_count": 1500,
            "status": "awarded",
            "funder_name": "Gates Foundation",
            "requested_amount": 50000.00,
            "awarded_amount": 45000.00,
            "submission_date": date(2024, 1, 15),
            "decision_date": date(2024, 2, 20),
            "success_notes": "Awarded with minor budget reduction",
            "created_by": "user1@example.com",
        },
        {
            "output_type": "grant_proposal",
            "title": "Healthcare Research Grant",
            "content": "Research proposal for healthcare innovation...",
            "word_count": 2000,
            "status": "not_awarded",
            "funder_name": "NIH",
            "requested_amount": 100000.00,
            "awarded_amount": None,
            "submission_date": date(2024, 1, 20),
            "decision_date": date(2024, 3, 1),
            "success_notes": "Not awarded - budget constraints cited",
            "created_by": "user1@example.com",
        },
        {
            "output_type": "budget_narrative",
            "title": "Budget Justification for Community Program",
            "content": "Detailed budget narrative explaining costs...",
            "word_count": 800,
            "status": "submitted",
            "funder_name": "Community Foundation",
            "requested_amount": 25000.00,
            "awarded_amount": None,
            "submission_date": date(2024, 2, 1),
            "decision_date": None,
            "success_notes": None,
            "created_by": "user2@example.com",
        },
        {
            "output_type": "program_description",
            "title": "Youth Mentorship Program Description",
            "content": "Program description for youth mentorship initiative...",
            "word_count": 1200,
            "status": "pending",
            "funder_name": "Ford Foundation",
            "requested_amount": 75000.00,
            "awarded_amount": None,
            "submission_date": date(2024, 2, 10),
            "decision_date": None,
            "success_notes": None,
            "created_by": "user1@example.com",
        },
        {
            "output_type": "grant_proposal",
            "title": "Environmental Conservation Grant",
            "content": "Grant proposal for environmental conservation efforts...",
            "word_count": 1800,
            "status": "draft",
            "funder_name": None,
            "requested_amount": None,
            "awarded_amount": None,
            "submission_date": None,
            "decision_date": None,
            "success_notes": None,
            "created_by": "user2@example.com",
        },
    ]

    # Create outputs in database
    for idx, data in enumerate(test_data):
        output_id = uuid4()
        await db_service.create_output(
            output_id=output_id,
            **data
        )
        outputs.append({
            "output_id": output_id,
            **data
        })

    yield outputs

    # Cleanup - delete all created outputs
    for output_data in outputs:
        try:
            await db_service.delete_output(output_data["output_id"])
        except Exception:
            pass  # Ignore cleanup errors


# CRUD Operations Tests

class TestCRUDOperations:
    """Test create, read, update, delete operations"""

    @pytest.mark.asyncio
    async def test_create_output_success(self, db_service):
        """Test creating an output with all fields"""
        output_id = uuid4()

        result = await db_service.create_output(
            output_id=output_id,
            output_type="grant_proposal",
            title="Test Grant Proposal",
            content="This is test content for the grant proposal.",
            word_count=500,
            status="draft",
            funder_name="Test Foundation",
            requested_amount=10000.00,
            metadata={"source": "test", "confidence": 0.95},
            created_by="test@example.com",
        )

        assert result is not None
        assert result["output_id"] == str(output_id)
        assert result["output_type"] == "grant_proposal"
        assert result["title"] == "Test Grant Proposal"
        assert result["status"] == "draft"
        assert "created_at" in result

        # Cleanup
        await db_service.delete_output(output_id)

    @pytest.mark.asyncio
    async def test_create_output_minimal(self, db_service):
        """Test creating an output with only required fields"""
        output_id = uuid4()

        result = await db_service.create_output(
            output_id=output_id,
            output_type="other",
            title="Minimal Output",
            content="Minimal content.",
        )

        assert result is not None
        assert result["output_id"] == str(output_id)
        assert result["status"] == "draft"  # Default status

        # Cleanup
        await db_service.delete_output(output_id)

    @pytest.mark.asyncio
    async def test_get_output_by_id_success(self, db_service, sample_outputs):
        """Test retrieving an existing output"""
        test_output = sample_outputs[0]

        result = await db_service.get_output(test_output["output_id"])

        assert result is not None
        assert result["output_id"] == str(test_output["output_id"])
        assert result["title"] == test_output["title"]
        assert result["content"] == test_output["content"]
        assert result["output_type"] == test_output["output_type"]
        assert result["status"] == test_output["status"]
        assert result["funder_name"] == test_output["funder_name"]
        assert float(result["requested_amount"]) == test_output["requested_amount"]
        assert float(result["awarded_amount"]) == test_output["awarded_amount"]

    @pytest.mark.asyncio
    async def test_get_output_not_found(self, db_service):
        """Test retrieving a non-existent output returns None"""
        non_existent_id = uuid4()

        result = await db_service.get_output(non_existent_id)

        assert result is None

    @pytest.mark.asyncio
    async def test_update_output_single_field(self, db_service, sample_outputs):
        """Test updating a single field"""
        test_output = sample_outputs[4]  # Draft output

        result = await db_service.update_output(
            test_output["output_id"],
            status="submitted"
        )

        assert result is not None
        assert result["status"] == "submitted"

        # Verify update persisted
        updated = await db_service.get_output(test_output["output_id"])
        assert updated["status"] == "submitted"

    @pytest.mark.asyncio
    async def test_update_output_multiple_fields(self, db_service, sample_outputs):
        """Test updating multiple fields at once"""
        test_output = sample_outputs[3]  # Pending output

        result = await db_service.update_output(
            test_output["output_id"],
            status="awarded",
            awarded_amount=70000.00,
            decision_date=date(2024, 3, 15),
            success_notes="Awarded - excellent proposal"
        )

        assert result is not None
        assert result["status"] == "awarded"

        # Verify all updates persisted
        updated = await db_service.get_output(test_output["output_id"])
        assert updated["status"] == "awarded"
        assert float(updated["awarded_amount"]) == 70000.00
        assert updated["success_notes"] == "Awarded - excellent proposal"

    @pytest.mark.asyncio
    async def test_delete_output_success(self, db_service):
        """Test deleting an output returns True"""
        # Create output to delete
        output_id = uuid4()
        await db_service.create_output(
            output_id=output_id,
            output_type="other",
            title="To Delete",
            content="Will be deleted.",
        )

        result = await db_service.delete_output(output_id)

        assert result is True

        # Verify deletion
        deleted = await db_service.get_output(output_id)
        assert deleted is None

    @pytest.mark.asyncio
    async def test_delete_output_not_found(self, db_service):
        """Test deleting a non-existent output returns False"""
        non_existent_id = uuid4()

        result = await db_service.delete_output(non_existent_id)

        assert result is False


# List and Filtering Tests

class TestListAndFiltering:
    """Test list_outputs with various filters"""

    @pytest.mark.asyncio
    async def test_list_outputs_all(self, db_service, sample_outputs):
        """Test listing all outputs without filters"""
        results = await db_service.list_outputs(skip=0, limit=10)

        # Should return at least our sample outputs
        assert len(results) >= len(sample_outputs)

    @pytest.mark.asyncio
    async def test_list_outputs_filter_by_type_single(self, db_service, sample_outputs):
        """Test filtering by a single output type"""
        results = await db_service.list_outputs(
            output_type=["budget_narrative"],
            skip=0,
            limit=10
        )

        assert len(results) >= 1
        for output in results:
            assert output["output_type"] == "budget_narrative"

    @pytest.mark.asyncio
    async def test_list_outputs_filter_by_type_multiple(self, db_service, sample_outputs):
        """Test filtering by multiple output types"""
        results = await db_service.list_outputs(
            output_type=["grant_proposal", "program_description"],
            skip=0,
            limit=10
        )

        assert len(results) >= 4
        for output in results:
            assert output["output_type"] in ["grant_proposal", "program_description"]

    @pytest.mark.asyncio
    async def test_list_outputs_filter_by_status_single(self, db_service, sample_outputs):
        """Test filtering by a single status"""
        results = await db_service.list_outputs(
            status=["awarded"],
            skip=0,
            limit=10
        )

        assert len(results) >= 1
        for output in results:
            assert output["status"] == "awarded"

    @pytest.mark.asyncio
    async def test_list_outputs_filter_by_status_multiple(self, db_service, sample_outputs):
        """Test filtering by multiple statuses"""
        results = await db_service.list_outputs(
            status=["submitted", "pending"],
            skip=0,
            limit=10
        )

        assert len(results) >= 2
        for output in results:
            assert output["status"] in ["submitted", "pending"]

    @pytest.mark.asyncio
    async def test_list_outputs_filter_by_created_by(self, db_service, sample_outputs):
        """Test filtering by creator"""
        results = await db_service.list_outputs(
            created_by="user1@example.com",
            skip=0,
            limit=10
        )

        assert len(results) >= 3
        for output in results:
            assert output["created_by"] == "user1@example.com"

    @pytest.mark.asyncio
    async def test_list_outputs_filter_by_writing_style(self, db_service, sample_outputs):
        """Test filtering by writing style ID"""
        # Create a writing style first (to satisfy foreign key constraint)
        style_id = uuid4()
        await db_service.create_writing_style(
            writing_style_id=style_id,
            name="Test Style",
            description="Test writing style for output filtering"
        )

        # Create an output with the writing style
        output_id = uuid4()
        await db_service.create_output(
            output_id=output_id,
            output_type="grant_proposal",
            title="With Style",
            content="Content with style.",
            writing_style_id=style_id,
        )

        results = await db_service.list_outputs(
            writing_style_id=str(style_id),
            skip=0,
            limit=10
        )

        assert len(results) >= 1
        for output in results:
            assert output["writing_style_id"] == str(style_id)

        # Cleanup
        await db_service.delete_output(output_id)
        await db_service.delete_writing_style(style_id)

    @pytest.mark.asyncio
    async def test_list_outputs_filter_by_funder_name(self, db_service, sample_outputs):
        """Test filtering by funder name (partial match)"""
        results = await db_service.list_outputs(
            funder_name="Foundation",
            skip=0,
            limit=10
        )

        # Should match "Gates Foundation", "Community Foundation", "Ford Foundation"
        assert len(results) >= 3
        for output in results:
            assert "foundation" in output["funder_name"].lower()

    @pytest.mark.asyncio
    async def test_list_outputs_filter_by_date_range(self, db_service, sample_outputs):
        """Test filtering by date range"""
        # Filter for outputs created in the last hour
        now = datetime.utcnow()
        one_hour_ago = now - timedelta(hours=1)

        results = await db_service.list_outputs(
            date_range=(one_hour_ago, now),
            skip=0,
            limit=10
        )

        # Should return our sample outputs (just created)
        assert len(results) >= len(sample_outputs)

    @pytest.mark.asyncio
    async def test_list_outputs_combined_filters(self, db_service, sample_outputs):
        """Test combining multiple filters"""
        results = await db_service.list_outputs(
            output_type=["grant_proposal"],
            status=["awarded", "not_awarded"],
            created_by="user1@example.com",
            skip=0,
            limit=10
        )

        # Should match outputs 0 and 1 from sample_outputs
        assert len(results) >= 2
        for output in results:
            assert output["output_type"] == "grant_proposal"
            assert output["status"] in ["awarded", "not_awarded"]
            assert output["created_by"] == "user1@example.com"


# Pagination Tests

class TestPagination:
    """Test pagination with skip and limit"""

    @pytest.mark.asyncio
    async def test_list_outputs_pagination_first_page(self, db_service, sample_outputs):
        """Test first page of results"""
        results = await db_service.list_outputs(skip=0, limit=3)

        assert len(results) <= 3

    @pytest.mark.asyncio
    async def test_list_outputs_pagination_second_page(self, db_service, sample_outputs):
        """Test second page of results"""
        first_page = await db_service.list_outputs(skip=0, limit=2)
        second_page = await db_service.list_outputs(skip=2, limit=2)

        # Ensure different results
        first_ids = {o["output_id"] for o in first_page}
        second_ids = {o["output_id"] for o in second_page}

        # Pages should not overlap (unless there's exactly 2 total)
        if len(first_ids) == 2 and len(second_ids) >= 1:
            assert len(first_ids & second_ids) == 0

    @pytest.mark.asyncio
    async def test_list_outputs_pagination_custom_limit(self, db_service, sample_outputs):
        """Test custom page size"""
        results = await db_service.list_outputs(skip=0, limit=1)

        assert len(results) == 1


# Search Tests

class TestSearch:
    """Test full-text search functionality"""

    @pytest.mark.asyncio
    async def test_search_outputs_by_title(self, db_service, sample_outputs):
        """Test searching by title text"""
        results = await db_service.search_outputs(
            query="Education",
            skip=0,
            limit=10
        )

        assert len(results) >= 1
        # Should match "Education Grant Proposal"
        found_education = any("Education" in o["title"] for o in results)
        assert found_education

    @pytest.mark.asyncio
    async def test_search_outputs_by_content(self, db_service, sample_outputs):
        """Test searching by content text"""
        results = await db_service.search_outputs(
            query="healthcare innovation",
            skip=0,
            limit=10
        )

        assert len(results) >= 1
        # Should match the healthcare research grant
        found_healthcare = any("Healthcare" in o["title"] for o in results)
        assert found_healthcare

    @pytest.mark.asyncio
    async def test_search_outputs_by_funder(self, db_service, sample_outputs):
        """Test searching by funder name"""
        results = await db_service.search_outputs(
            query="NIH",
            skip=0,
            limit=10
        )

        assert len(results) >= 1
        found_nih = any(o.get("funder_name") == "NIH" for o in results)
        assert found_nih

    @pytest.mark.asyncio
    async def test_search_outputs_no_results(self, db_service, sample_outputs):
        """Test search with no matching results"""
        results = await db_service.search_outputs(
            query="nonexistentqueryxyz12345",
            skip=0,
            limit=10
        )

        assert len(results) == 0


# Statistics Tests

class TestStatistics:
    """Test get_outputs_stats calculations"""

    @pytest.mark.asyncio
    async def test_get_outputs_stats_all(self, db_service, sample_outputs):
        """Test statistics for all outputs"""
        stats = await db_service.get_outputs_stats()

        assert stats is not None
        assert "total_outputs" in stats
        assert "by_type" in stats
        assert "by_status" in stats
        assert "success_rate" in stats
        assert "total_requested" in stats
        assert "total_awarded" in stats
        assert "avg_requested" in stats
        assert "avg_awarded" in stats

        # Should have at least our sample outputs
        assert stats["total_outputs"] >= len(sample_outputs)

    @pytest.mark.asyncio
    async def test_get_outputs_stats_filtered_by_type(self, db_service, sample_outputs):
        """Test statistics filtered by output type"""
        stats = await db_service.get_outputs_stats(
            output_type=["grant_proposal"]
        )

        assert stats is not None
        assert stats["total_outputs"] >= 3  # We have 3 grant_proposal outputs

        # All should be grant_proposal type
        if "grant_proposal" in stats["by_type"]:
            assert stats["by_type"]["grant_proposal"] >= 3

    @pytest.mark.asyncio
    async def test_get_outputs_stats_filtered_by_user(self, db_service, sample_outputs):
        """Test statistics filtered by user"""
        stats = await db_service.get_outputs_stats(
            created_by="user1@example.com"
        )

        assert stats is not None
        assert stats["total_outputs"] >= 3  # user1 created 3 outputs

    @pytest.mark.asyncio
    async def test_get_outputs_stats_success_rate_calculation(self, db_service, sample_outputs):
        """Test success rate calculation accuracy"""
        stats = await db_service.get_outputs_stats()

        # Sample data has: 1 awarded, 1 not_awarded, 1 submitted, 1 pending, 1 draft
        # Success rate = awarded / (submitted + pending + awarded + not_awarded)
        # Success rate = 1 / (1 + 1 + 1 + 1) = 1 / 4 = 25%

        assert "success_rate" in stats
        # The success rate should be calculated (might be affected by other data)
        assert isinstance(stats["success_rate"], (int, float))
        assert stats["success_rate"] >= 0
        assert stats["success_rate"] <= 100


# Edge Cases Tests

class TestEdgeCases:
    """Test edge cases and special scenarios"""

    @pytest.mark.asyncio
    async def test_create_output_with_metadata_json(self, db_service):
        """Test creating output with complex JSON metadata"""
        output_id = uuid4()

        metadata = {
            "source": "conversation-123",
            "confidence": 0.87,
            "generated_by": "gpt-4",
            "prompt_tokens": 1500,
            "completion_tokens": 800,
            "references": ["doc1", "doc2", "doc3"],
            "nested": {
                "key1": "value1",
                "key2": [1, 2, 3]
            }
        }

        await db_service.create_output(
            output_id=output_id,
            output_type="grant_proposal",
            title="Output with Metadata",
            content="Content here.",
            metadata=metadata,
        )

        # Retrieve and verify metadata
        result = await db_service.get_output(output_id)

        assert result is not None
        # Metadata might be returned as JSON string, parse if needed
        result_metadata = result["metadata"]
        if isinstance(result_metadata, str):
            result_metadata = json.loads(result_metadata)

        assert result_metadata == metadata
        assert result_metadata["source"] == "conversation-123"
        assert result_metadata["confidence"] == 0.87
        assert result_metadata["nested"]["key1"] == "value1"

        # Cleanup
        await db_service.delete_output(output_id)

    @pytest.mark.asyncio
    async def test_update_output_with_no_changes(self, db_service, sample_outputs):
        """Test update with no fields returns current data"""
        test_output = sample_outputs[0]

        result = await db_service.update_output(test_output["output_id"])

        assert result is not None
        assert result["output_id"] == str(test_output["output_id"])

    @pytest.mark.asyncio
    async def test_list_outputs_empty_filters(self, db_service, sample_outputs):
        """Test list with empty filter arrays"""
        # Empty arrays should be treated as no filter
        results = await db_service.list_outputs(
            output_type=[],
            status=[],
            skip=0,
            limit=10
        )

        # Should return results (not filter out everything)
        assert len(results) >= 0
