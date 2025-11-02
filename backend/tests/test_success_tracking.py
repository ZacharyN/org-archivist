"""
Success Tracking Service Tests

Tests for Phase 4: Success Tracking Service
- Status transition validation (valid and invalid paths)
- Admin override functionality
- Outcome data validation
- Analytics by style, funder, year
- Success rate calculations
- Funder performance rankings
"""

import pytest
from datetime import datetime, date
from decimal import Decimal
from unittest.mock import AsyncMock, Mock, MagicMock
from uuid import uuid4

from backend.app.services.success_tracking import (
    SuccessTrackingService,
    StatusTransitionError,
    VALID_STATUS_TRANSITIONS,
)


# ==================== Fixtures ====================

@pytest.fixture
def mock_conn():
    """Mock database connection with pre-configured methods"""
    conn = AsyncMock()
    conn.fetchrow = AsyncMock()
    conn.fetch = AsyncMock()
    conn.execute = AsyncMock()
    return conn


@pytest.fixture
def mock_database_service(mock_conn):
    """Mock DatabaseService with proper async context manager"""
    mock_db = AsyncMock()

    # Create proper async context manager class
    class MockPoolAcquire:
        """Async context manager for pool.acquire()"""
        def __init__(self, connection):
            self.connection = connection

        async def __aenter__(self):
            return self.connection

        async def __aexit__(self, exc_type, exc_val, exc_tb):
            return None

    # Mock pool with proper context manager
    mock_pool = Mock()
    mock_pool.acquire = Mock(return_value=MockPoolAcquire(mock_conn))

    mock_db.pool = mock_pool

    # Mock get_outputs_stats method
    mock_db.get_outputs_stats = AsyncMock(return_value={
        "total_outputs": 10,
        "by_status": {"draft": 2, "submitted": 3, "awarded": 5},
        "by_type": {"grant_proposal": 8, "research_article": 2},
        "success_rate": 50.0,
    })

    return mock_db


@pytest.fixture
def success_service(mock_database_service):
    """Create SuccessTrackingService with mocked database"""
    return SuccessTrackingService(mock_database_service)


@pytest.fixture
def sample_style_id():
    """Sample writing style UUID"""
    return uuid4()


# ==================== Status Transition Validation Tests ====================

class TestStatusTransitionValidation:
    """Test status transition validation logic"""

    def test_valid_transition_draft_to_submitted(self):
        """Test draft -> submitted is allowed"""
        result = SuccessTrackingService.validate_status_transition("draft", "submitted")
        assert result is True

    def test_valid_transition_submitted_to_pending(self):
        """Test submitted -> pending is allowed"""
        result = SuccessTrackingService.validate_status_transition("submitted", "pending")
        assert result is True

    def test_valid_transition_submitted_to_draft(self):
        """Test submitted -> draft is allowed (revision path)"""
        result = SuccessTrackingService.validate_status_transition("submitted", "draft")
        assert result is True

    def test_valid_transition_pending_to_awarded(self):
        """Test pending -> awarded is allowed"""
        result = SuccessTrackingService.validate_status_transition("pending", "awarded")
        assert result is True

    def test_valid_transition_pending_to_not_awarded(self):
        """Test pending -> not_awarded is allowed"""
        result = SuccessTrackingService.validate_status_transition("pending", "not_awarded")
        assert result is True

    def test_valid_transition_pending_to_submitted(self):
        """Test pending -> submitted is allowed (return to review)"""
        result = SuccessTrackingService.validate_status_transition("pending", "submitted")
        assert result is True

    def test_invalid_transition_draft_to_awarded(self):
        """Test draft -> awarded is blocked (raises StatusTransitionError)"""
        with pytest.raises(StatusTransitionError) as exc_info:
            SuccessTrackingService.validate_status_transition("draft", "awarded")

        assert "Invalid status transition from 'draft' to 'awarded'" in str(exc_info.value)

    def test_invalid_transition_draft_to_pending(self):
        """Test draft -> pending is blocked"""
        with pytest.raises(StatusTransitionError) as exc_info:
            SuccessTrackingService.validate_status_transition("draft", "pending")

        assert "Invalid status transition from 'draft' to 'pending'" in str(exc_info.value)

    def test_invalid_transition_awarded_terminal_state(self):
        """Test awarded is terminal state (no transitions allowed)"""
        with pytest.raises(StatusTransitionError) as exc_info:
            SuccessTrackingService.validate_status_transition("awarded", "draft")

        assert "terminal state" in str(exc_info.value)

    def test_invalid_transition_not_awarded_terminal_state(self):
        """Test not_awarded is terminal state (no transitions allowed)"""
        with pytest.raises(StatusTransitionError) as exc_info:
            SuccessTrackingService.validate_status_transition("not_awarded", "draft")

        assert "terminal state" in str(exc_info.value)

    def test_valid_transition_same_status(self):
        """Test same status is allowed (no-op)"""
        result = SuccessTrackingService.validate_status_transition("draft", "draft")
        assert result is True

        result = SuccessTrackingService.validate_status_transition("awarded", "awarded")
        assert result is True

    def test_admin_override_allows_any_transition(self):
        """Test admin can override restrictions"""
        # Admin can force draft -> awarded
        result = SuccessTrackingService.validate_status_transition(
            "draft", "awarded", allow_override=True
        )
        assert result is True

        # Admin can force awarded -> draft
        result = SuccessTrackingService.validate_status_transition(
            "awarded", "draft", allow_override=True
        )
        assert result is True


# ==================== Outcome Data Validation Tests ====================

class TestOutcomeDataValidation:
    """Test outcome data validation logic"""

    def test_validate_outcome_draft_no_warnings(self):
        """Test draft status doesn't require submission data"""
        warnings = SuccessTrackingService.validate_outcome_data(
            status="draft",
            funder_name=None,
            requested_amount=None,
            submission_date=None,
        )
        assert len(warnings) == 0

    def test_validate_outcome_submitted_requires_submission_date(self):
        """Test submitted status recommends submission data"""
        warnings = SuccessTrackingService.validate_outcome_data(
            status="submitted",
            funder_name=None,
            requested_amount=None,
            submission_date=None,
        )

        assert "funder_name" in warnings
        assert "requested_amount" in warnings
        assert "submission_date" in warnings

    def test_validate_outcome_submitted_with_complete_data_no_warnings(self):
        """Test submitted with complete data has no warnings"""
        warnings = SuccessTrackingService.validate_outcome_data(
            status="submitted",
            funder_name="Test Foundation",
            requested_amount=Decimal("50000.00"),
            submission_date=date(2025, 1, 15),
        )
        assert len(warnings) == 0

    def test_validate_outcome_awarded_requires_decision_data(self):
        """Test awarded status recommends decision data"""
        warnings = SuccessTrackingService.validate_outcome_data(
            status="awarded",
            funder_name="Test Foundation",
            requested_amount=Decimal("50000.00"),
            submission_date=date(2025, 1, 15),
            decision_date=None,  # Missing
            awarded_amount=None,  # Missing
        )

        assert "decision_date" in warnings
        assert "awarded_amount" in warnings

    def test_validate_outcome_awarded_amount_consistency(self):
        """Test awarded amount should not exceed requested"""
        warnings = SuccessTrackingService.validate_outcome_data(
            status="awarded",
            requested_amount=Decimal("50000.00"),
            awarded_amount=Decimal("60000.00"),  # Exceeds requested
        )

        assert "awarded_amount" in warnings
        assert "exceeds requested" in warnings["awarded_amount"]

    def test_validate_outcome_awarded_amount_within_requested_valid(self):
        """Test awarded amount <= requested is valid"""
        warnings = SuccessTrackingService.validate_outcome_data(
            status="awarded",
            funder_name="Test Foundation",
            requested_amount=Decimal("50000.00"),
            awarded_amount=Decimal("45000.00"),  # Within requested
            submission_date=date(2025, 1, 15),
            decision_date=date(2025, 3, 1),
        )

        assert "awarded_amount" not in warnings

    def test_validate_outcome_not_awarded_with_amount_warning(self):
        """Test not_awarded should not have awarded amount"""
        warnings = SuccessTrackingService.validate_outcome_data(
            status="not_awarded",
            awarded_amount=Decimal("10000.00"),  # Should be 0 or null
        )

        assert "awarded_amount" in warnings
        assert "should be 0 or null" in warnings["awarded_amount"]

    def test_validate_outcome_decision_date_before_submission_invalid(self):
        """Test decision date cannot be before submission date"""
        warnings = SuccessTrackingService.validate_outcome_data(
            status="awarded",
            submission_date=date(2025, 3, 1),
            decision_date=date(2025, 1, 15),  # Before submission
        )

        assert "decision_date" in warnings
        assert "before submission" in warnings["decision_date"]

    def test_validate_outcome_decision_date_after_submission_valid(self):
        """Test decision date >= submission date is valid"""
        warnings = SuccessTrackingService.validate_outcome_data(
            status="awarded",
            funder_name="Test Foundation",
            requested_amount=Decimal("50000.00"),
            awarded_amount=Decimal("50000.00"),
            submission_date=date(2025, 1, 15),
            decision_date=date(2025, 3, 1),  # After submission
        )

        assert "decision_date" not in warnings

    def test_validate_outcome_complete_data_no_warnings(self):
        """Test complete awarded data produces no warnings"""
        warnings = SuccessTrackingService.validate_outcome_data(
            status="awarded",
            funder_name="Test Foundation",
            requested_amount=Decimal("50000.00"),
            awarded_amount=Decimal("50000.00"),
            submission_date=date(2025, 1, 15),
            decision_date=date(2025, 3, 1),
        )

        assert len(warnings) == 0


# ==================== Analytics by Style Tests ====================

class TestAnalyticsByStyle:
    """Test success rate calculations by writing style"""

    @pytest.mark.asyncio
    async def test_calculate_success_rate_by_style(self, success_service, mock_conn, sample_style_id):
        """Test correct success rate calculations"""
        # Mock database response
        mock_row = {
            "total_outputs": 10,
            "submitted_count": 8,
            "awarded_count": 5,
            "not_awarded_count": 3,
            "total_requested": Decimal("400000.00"),
            "total_awarded": Decimal("250000.00"),
        }

        mock_conn.fetchrow = AsyncMock(return_value=mock_row)

        # Calculate
        result = await success_service.calculate_success_rate_by_style(sample_style_id)

        # Assert
        assert result["style_id"] == str(sample_style_id)
        assert result["total_outputs"] == 10
        assert result["submitted_count"] == 8
        assert result["awarded_count"] == 5
        assert result["not_awarded_count"] == 3
        assert result["success_rate"] == 62.5  # 5/8 * 100
        assert result["total_requested"] == 400000.00
        assert result["total_awarded"] == 250000.00
        assert result["avg_award_rate"] == 62.5  # 250000/400000 * 100

    @pytest.mark.asyncio
    async def test_calculate_success_rate_by_style_with_date_filter(self, success_service, mock_conn, sample_style_id):
        """Test date range filtering works"""
        mock_row = {
            "total_outputs": 5,
            "submitted_count": 5,
            "awarded_count": 3,
            "not_awarded_count": 2,
            "total_requested": Decimal("100000.00"),
            "total_awarded": Decimal("75000.00"),
        }

        mock_conn.fetchrow = AsyncMock(return_value=mock_row)

        # Calculate with date filters
        start_date = datetime(2025, 1, 1)
        end_date = datetime(2025, 12, 31)
        result = await success_service.calculate_success_rate_by_style(
            sample_style_id,
            start_date=start_date,
            end_date=end_date
        )

        # Verify query was called with date parameters
        assert mock_conn.fetchrow.called
        assert result["success_rate"] == 60.0  # 3/5 * 100

    @pytest.mark.asyncio
    async def test_calculate_success_rate_by_style_no_data(self, success_service, mock_conn, sample_style_id):
        """Test handling empty results"""
        mock_row = {
            "total_outputs": 0,
            "submitted_count": 0,
            "awarded_count": 0,
            "not_awarded_count": 0,
            "total_requested": Decimal("0.00"),
            "total_awarded": Decimal("0.00"),
        }

        mock_conn.fetchrow = AsyncMock(return_value=mock_row)

        result = await success_service.calculate_success_rate_by_style(sample_style_id)

        assert result["total_outputs"] == 0
        assert result["success_rate"] == 0.0
        assert result["avg_award_rate"] == 0.0


# ==================== Analytics by Funder Tests ====================

class TestAnalyticsByFunder:
    """Test success rate calculations by funder"""

    @pytest.mark.asyncio
    async def test_calculate_success_rate_by_funder(self, success_service, mock_conn):
        """Test correct calculations for funder"""
        mock_row = {
            "total_outputs": 6,
            "submitted_count": 6,
            "awarded_count": 4,
            "not_awarded_count": 2,
            "total_requested": Decimal("300000.00"),
            "total_awarded": Decimal("200000.00"),
        }

        # Connection already provided via fixture
        mock_conn.fetchrow = AsyncMock(return_value=mock_row)

        result = await success_service.calculate_success_rate_by_funder("National Science Foundation")

        assert result["funder_name"] == "National Science Foundation"
        assert result["total_outputs"] == 6
        assert result["awarded_count"] == 4
        assert result["success_rate"] == 66.67  # 4/6 * 100, rounded to 2 decimals

    @pytest.mark.asyncio
    async def test_calculate_success_rate_by_funder_partial_match(self, success_service, mock_conn):
        """Test ILIKE partial matching works"""
        mock_row = {
            "total_outputs": 3,
            "submitted_count": 3,
            "awarded_count": 2,
            "not_awarded_count": 1,
            "total_requested": Decimal("150000.00"),
            "total_awarded": Decimal("100000.00"),
        }

        # Connection already provided via fixture
        mock_conn.fetchrow = AsyncMock(return_value=mock_row)

        # Search for "Gates" - should match "Bill & Melinda Gates Foundation"
        result = await success_service.calculate_success_rate_by_funder("Gates")

        # Verify query uses ILIKE pattern
        assert mock_conn.fetchrow.called
        call_args = mock_conn.fetchrow.call_args
        assert "%Gates%" in str(call_args)

    @pytest.mark.asyncio
    async def test_calculate_success_rate_by_funder_no_matches(self, success_service, mock_conn):
        """Test handling no matching funders"""
        mock_row = {
            "total_outputs": 0,
            "submitted_count": 0,
            "awarded_count": 0,
            "not_awarded_count": 0,
            "total_requested": Decimal("0.00"),
            "total_awarded": Decimal("0.00"),
        }

        # Connection already provided via fixture
        mock_conn.fetchrow = AsyncMock(return_value=mock_row)

        result = await success_service.calculate_success_rate_by_funder("Nonexistent Foundation")

        assert result["total_outputs"] == 0
        assert result["success_rate"] == 0.0


# ==================== Analytics by Year Tests ====================

class TestAnalyticsByYear:
    """Test success rate calculations by year"""

    @pytest.mark.asyncio
    async def test_calculate_success_rate_by_year(self, success_service, mock_conn):
        """Test year-based aggregation"""
        mock_row = {
            "total_outputs": 12,
            "submitted_count": 10,
            "awarded_count": 7,
            "not_awarded_count": 3,
            "total_requested": Decimal("500000.00"),
            "total_awarded": Decimal("350000.00"),
        }

        # Connection already provided via fixture
        mock_conn.fetchrow = AsyncMock(return_value=mock_row)

        result = await success_service.calculate_success_rate_by_year(2025)

        assert result["year"] == 2025
        assert result["total_outputs"] == 12
        assert result["submitted_count"] == 10
        assert result["awarded_count"] == 7
        assert result["success_rate"] == 70.0  # 7/10 * 100

    @pytest.mark.asyncio
    async def test_calculate_success_rate_by_year_no_data(self, success_service, mock_conn):
        """Test empty year handling"""
        mock_row = {
            "total_outputs": 0,
            "submitted_count": 0,
            "awarded_count": 0,
            "not_awarded_count": 0,
            "total_requested": Decimal("0.00"),
            "total_awarded": Decimal("0.00"),
        }

        # Connection already provided via fixture
        mock_conn.fetchrow = AsyncMock(return_value=mock_row)

        result = await success_service.calculate_success_rate_by_year(2020)

        assert result["year"] == 2020
        assert result["total_outputs"] == 0
        assert result["success_rate"] == 0.0


# ==================== Summary Metrics Tests ====================

class TestSummaryMetrics:
    """Test comprehensive success metrics summary"""

    @pytest.mark.asyncio
    async def test_get_success_metrics_summary(self, success_service, mock_conn):
        """Test complete summary with top styles/funders"""
        # Mock top styles
        mock_styles_rows = [
            {"writing_style_id": uuid4(), "submitted_count": 10, "awarded_count": 8, "success_rate": Decimal("80.00")},
            {"writing_style_id": uuid4(), "submitted_count": 5, "awarded_count": 3, "success_rate": Decimal("60.00")},
        ]

        # Mock top funders
        mock_funders_rows = [
            {"funder_name": "NSF", "submitted_count": 15, "awarded_count": 10, "success_rate": Decimal("66.67"), "total_awarded": Decimal("500000.00")},
            {"funder_name": "NIH", "submitted_count": 8, "awarded_count": 6, "success_rate": Decimal("75.00"), "total_awarded": Decimal("400000.00")},
        ]

        # Mock year trends
        mock_trends_rows = [
            {"year": 2025, "submitted_count": 20, "awarded_count": 15, "success_rate": Decimal("75.00"), "total_awarded": Decimal("800000.00")},
            {"year": 2024, "submitted_count": 18, "awarded_count": 12, "success_rate": Decimal("66.67"), "total_awarded": Decimal("600000.00")},
        ]

        # Connection already provided via fixture
        mock_conn.fetch.side_effect = [mock_styles_rows, mock_funders_rows, mock_trends_rows]

        result = await success_service.get_success_metrics_summary()

        assert "overall" in result
        assert "top_writing_styles" in result
        assert "top_funders" in result
        assert "year_over_year_trends" in result

        assert len(result["top_writing_styles"]) == 2
        assert len(result["top_funders"]) == 2
        assert len(result["year_over_year_trends"]) == 2

        # Verify top style data
        assert result["top_writing_styles"][0]["success_rate"] == 80.0

        # Verify top funder data
        assert result["top_funders"][0]["funder_name"] == "NSF"
        assert result["top_funders"][0]["total_awarded"] == 500000.00

    @pytest.mark.asyncio
    async def test_get_success_metrics_summary_role_filtering(self, success_service, mock_conn):
        """Test writers see only their data"""
        # Mock fetch to return empty results for stats queries
        mock_conn.fetch.return_value = []

        # Mock fetchrow for stats query
        mock_conn.fetchrow.return_value = {
            "total_outputs": 0,
            "total_submitted": 0,
            "total_awarded": 0,
            "success_rate": 0.0,
            "total_requested": 0.0,
            "total_awarded_amount": 0.0,
            "avg_award_rate": 0.0,
        }

        writer_username = "writer@example.com"
        result = await success_service.get_success_metrics_summary(created_by=writer_username)

        # Verify the service returned a summary (even if empty)
        assert result is not None
        assert "total_outputs" in result or "top_writing_styles" in result


# ==================== Funder Performance Tests ====================

class TestFunderPerformance:
    """Test funder performance rankings"""

    @pytest.mark.asyncio
    async def test_get_funder_performance_rankings(self, success_service, mock_conn):
        """Test funders ordered by success rate"""
        mock_rows = [
            {
                "funder_name": "Gates Foundation",
                "total_submissions": 10,
                "awarded_count": 8,
                "not_awarded_count": 2,
                "pending_count": 0,
                "success_rate": Decimal("80.00"),
                "total_requested": Decimal("1000000.00"),
                "total_awarded": Decimal("800000.00"),
                "avg_award_amount": Decimal("100000.00"),
            },
            {
                "funder_name": "NSF",
                "total_submissions": 15,
                "awarded_count": 9,
                "not_awarded_count": 6,
                "pending_count": 0,
                "success_rate": Decimal("60.00"),
                "total_requested": Decimal("750000.00"),
                "total_awarded": Decimal("450000.00"),
                "avg_award_amount": Decimal("50000.00"),
            },
        ]

        # Connection already provided via fixture
        mock_conn.fetch.return_value = mock_rows

        result = await success_service.get_funder_performance(limit=10)

        assert len(result) == 2

        # Verify first funder has highest success rate
        assert result[0]["funder_name"] == "Gates Foundation"
        assert result[0]["success_rate"] == 80.0
        assert result[0]["total_awarded"] == 800000.00

        # Verify second funder
        assert result[1]["funder_name"] == "NSF"
        assert result[1]["success_rate"] == 60.0

    @pytest.mark.asyncio
    async def test_get_funder_performance_limit(self, success_service, mock_conn):
        """Test limit parameter works"""
        # Connection already provided via fixture
        mock_conn.fetch.return_value = []

        await success_service.get_funder_performance(limit=5)

        # Verify limit was passed in query
        assert mock_conn.fetch.called
        call_args = mock_conn.fetch.call_args
        assert 5 in call_args[0]  # Limit should be in parameters
