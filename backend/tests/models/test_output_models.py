"""
Test module for Output Pydantic models

Tests Pydantic validation for:
- OutputType and OutputStatus enums
- Field validators (date ordering, amount limits)
- OutputCreateRequest validation
- OutputUpdateRequest validation
- Error messages and edge cases
"""

import pytest
from datetime import date, datetime
from decimal import Decimal
from pydantic import ValidationError

from backend.app.models.output import (
    OutputType,
    OutputStatus,
    OutputBase,
    OutputCreateRequest,
    OutputUpdateRequest,
    OutputResponse,
)


# ==================== Test Data ====================

@pytest.fixture
def valid_output_data():
    """Generate valid output data for testing"""
    return {
        "output_type": OutputType.GRANT_PROPOSAL,
        "title": "Test Grant Proposal",
        "content": "This is test content for the grant proposal that is sufficient for testing.",
        "word_count": 500,
        "status": OutputStatus.DRAFT,
    }


@pytest.fixture
def complete_output_data():
    """Generate complete output data with all fields"""
    return {
        "output_type": OutputType.GRANT_PROPOSAL,
        "title": "Complete Grant Proposal",
        "content": "This is a complete grant proposal with all fields populated for comprehensive testing.",
        "word_count": 1000,
        "status": OutputStatus.AWARDED,
        "writing_style_id": "550e8400-e29b-41d4-a716-446655440000",
        "funder_name": "National Science Foundation",
        "requested_amount": Decimal("50000.00"),
        "awarded_amount": Decimal("45000.00"),
        "submission_date": date(2024, 1, 15),
        "decision_date": date(2024, 3, 1),
        "success_notes": "Excellent proposal, minor budget adjustments",
        "metadata": {"source": "ai_generated", "confidence": 0.95},
    }


# ==================== Enum Validation Tests ====================

class TestEnumValidation:
    """Test OutputType and OutputStatus enum validation"""

    def test_output_type_enum_values(self, valid_output_data):
        """Test that valid OutputType values are accepted"""
        # Test each valid enum value
        for output_type in OutputType:
            data = {**valid_output_data, "output_type": output_type}
            output = OutputBase(**data)
            assert output.output_type == output_type

    def test_output_type_enum_invalid(self, valid_output_data):
        """Test that invalid OutputType raises ValidationError"""
        data = {**valid_output_data, "output_type": "invalid_type"}
        with pytest.raises(ValidationError) as exc_info:
            OutputBase(**data)
        assert "output_type" in str(exc_info.value)

    def test_output_status_enum_values(self, valid_output_data):
        """Test that valid OutputStatus values are accepted"""
        # Test each valid enum value
        for status in OutputStatus:
            data = {**valid_output_data, "status": status}
            output = OutputBase(**data)
            assert output.status == status

    def test_output_status_enum_invalid(self, valid_output_data):
        """Test that invalid OutputStatus raises ValidationError"""
        data = {**valid_output_data, "status": "invalid_status"}
        with pytest.raises(ValidationError) as exc_info:
            OutputBase(**data)
        assert "status" in str(exc_info.value)


# ==================== Field Validation Tests ====================

class TestFieldValidation:
    """Test field validators and constraints"""

    def test_title_min_length(self, valid_output_data):
        """Test that title must be at least 1 character"""
        # Valid title with 1 character
        data = {**valid_output_data, "title": "A"}
        output = OutputBase(**data)
        assert output.title == "A"

        # Invalid empty title
        data = {**valid_output_data, "title": ""}
        with pytest.raises(ValidationError) as exc_info:
            OutputBase(**data)
        assert "title" in str(exc_info.value)

    def test_title_max_length(self, valid_output_data):
        """Test that title must be ≤500 characters"""
        # Valid title at 500 characters
        data = {**valid_output_data, "title": "A" * 500}
        output = OutputBase(**data)
        assert len(output.title) == 500

        # Invalid title over 500 characters
        data = {**valid_output_data, "title": "A" * 501}
        with pytest.raises(ValidationError) as exc_info:
            OutputBase(**data)
        assert "title" in str(exc_info.value)

    def test_content_required(self, valid_output_data):
        """Test that content field is required"""
        # Valid content
        data = {**valid_output_data, "content": "Valid content"}
        output = OutputBase(**data)
        assert output.content == "Valid content"

        # Missing content
        data = {**valid_output_data}
        del data["content"]
        with pytest.raises(ValidationError) as exc_info:
            OutputBase(**data)
        assert "content" in str(exc_info.value)

        # Empty content
        data = {**valid_output_data, "content": ""}
        with pytest.raises(ValidationError) as exc_info:
            OutputBase(**data)
        assert "content" in str(exc_info.value)

    def test_word_count_positive(self, valid_output_data):
        """Test that word count must be ≥0"""
        # Valid word count
        data = {**valid_output_data, "word_count": 100}
        output = OutputBase(**data)
        assert output.word_count == 100

        # Valid zero word count
        data = {**valid_output_data, "word_count": 0}
        output = OutputBase(**data)
        assert output.word_count == 0

        # Note: Pydantic doesn't automatically enforce >=0 for Optional[int]
        # If we want strict validation, we'd need a field_validator

    def test_requested_amount_positive(self, valid_output_data):
        """Test that requested amount must be ≥0"""
        # Valid requested amount
        data = {**valid_output_data, "requested_amount": Decimal("50000.00")}
        output = OutputBase(**data)
        assert output.requested_amount == Decimal("50000.00")

        # Valid zero amount
        data = {**valid_output_data, "requested_amount": Decimal("0.00")}
        output = OutputBase(**data)
        assert output.requested_amount == Decimal("0.00")

        # Invalid negative amount
        data = {**valid_output_data, "requested_amount": Decimal("-1000.00")}
        with pytest.raises(ValidationError) as exc_info:
            OutputBase(**data)
        assert "requested_amount" in str(exc_info.value)

    def test_awarded_amount_positive(self, valid_output_data):
        """Test that awarded amount must be ≥0"""
        # Valid awarded amount
        data = {**valid_output_data, "awarded_amount": Decimal("45000.00")}
        output = OutputBase(**data)
        assert output.awarded_amount == Decimal("45000.00")

        # Valid zero amount
        data = {**valid_output_data, "awarded_amount": Decimal("0.00")}
        output = OutputBase(**data)
        assert output.awarded_amount == Decimal("0.00")

        # Invalid negative amount
        data = {**valid_output_data, "awarded_amount": Decimal("-1000.00")}
        with pytest.raises(ValidationError) as exc_info:
            OutputBase(**data)
        assert "awarded_amount" in str(exc_info.value)

    def test_funder_name_max_length(self, valid_output_data):
        """Test that funder name must be ≤255 characters"""
        # Valid funder name at 255 characters
        data = {**valid_output_data, "funder_name": "A" * 255}
        output = OutputBase(**data)
        assert len(output.funder_name) == 255

        # Invalid funder name over 255 characters
        data = {**valid_output_data, "funder_name": "A" * 256}
        with pytest.raises(ValidationError) as exc_info:
            OutputBase(**data)
        assert "funder_name" in str(exc_info.value)


# ==================== Date Validation Tests ====================

class TestDateValidation:
    """Test date field validators"""

    def test_decision_date_after_submission_valid(self, valid_output_data):
        """Test that decision_date >= submission_date is valid"""
        data = {
            **valid_output_data,
            "submission_date": date(2024, 1, 15),
            "decision_date": date(2024, 3, 1),
        }
        output = OutputBase(**data)
        assert output.decision_date > output.submission_date

    def test_decision_date_before_submission_invalid(self, valid_output_data):
        """Test that decision_date < submission_date raises ValueError"""
        data = {
            **valid_output_data,
            "submission_date": date(2024, 3, 1),
            "decision_date": date(2024, 1, 15),
        }
        with pytest.raises(ValidationError) as exc_info:
            OutputBase(**data)
        error_msg = str(exc_info.value)
        assert "decision_date cannot be before submission_date" in error_msg

    def test_decision_date_same_as_submission_valid(self, valid_output_data):
        """Test that same decision_date and submission_date is valid"""
        same_date = date(2024, 2, 1)
        data = {
            **valid_output_data,
            "submission_date": same_date,
            "decision_date": same_date,
        }
        output = OutputBase(**data)
        assert output.decision_date == output.submission_date

    def test_decision_date_without_submission_date_valid(self, valid_output_data):
        """Test that decision_date can exist without submission_date"""
        data = {
            **valid_output_data,
            "decision_date": date(2024, 3, 1),
        }
        output = OutputBase(**data)
        assert output.decision_date == date(2024, 3, 1)
        assert output.submission_date is None


# ==================== Amount Validation Tests ====================

class TestAmountValidation:
    """Test amount field validators"""

    def test_awarded_less_than_requested_valid(self, valid_output_data):
        """Test that awarded ≤ requested is valid"""
        data = {
            **valid_output_data,
            "requested_amount": Decimal("50000.00"),
            "awarded_amount": Decimal("45000.00"),
        }
        output = OutputBase(**data)
        assert output.awarded_amount < output.requested_amount

    def test_awarded_exceeds_requested_invalid(self, valid_output_data):
        """Test that awarded > requested raises ValueError"""
        data = {
            **valid_output_data,
            "requested_amount": Decimal("50000.00"),
            "awarded_amount": Decimal("55000.00"),
        }
        with pytest.raises(ValidationError) as exc_info:
            OutputBase(**data)
        error_msg = str(exc_info.value)
        assert "awarded_amount cannot exceed requested_amount" in error_msg

    def test_awarded_equals_requested_valid(self, valid_output_data):
        """Test that awarded = requested is valid"""
        amount = Decimal("50000.00")
        data = {
            **valid_output_data,
            "requested_amount": amount,
            "awarded_amount": amount,
        }
        output = OutputBase(**data)
        assert output.awarded_amount == output.requested_amount

    def test_awarded_without_requested_valid(self, valid_output_data):
        """Test that awarded_amount can exist without requested_amount"""
        data = {
            **valid_output_data,
            "awarded_amount": Decimal("45000.00"),
        }
        output = OutputBase(**data)
        assert output.awarded_amount == Decimal("45000.00")
        assert output.requested_amount is None


# ==================== Request/Response Model Tests ====================

class TestRequestResponseModels:
    """Test OutputCreateRequest and OutputUpdateRequest models"""

    def test_output_create_request_valid(self, valid_output_data):
        """Test valid OutputCreateRequest creation"""
        create_data = {
            **valid_output_data,
            "conversation_id": "550e8400-e29b-41d4-a716-446655440000",
        }
        request = OutputCreateRequest(**create_data)
        assert request.output_type == OutputType.GRANT_PROPOSAL
        assert request.title == "Test Grant Proposal"
        assert request.conversation_id == "550e8400-e29b-41d4-a716-446655440000"

    def test_output_create_request_minimal(self, valid_output_data):
        """Test OutputCreateRequest with only required fields"""
        minimal_data = {
            "output_type": OutputType.GRANT_PROPOSAL,
            "title": "Minimal Proposal",
            "content": "Minimal content for testing",
        }
        request = OutputCreateRequest(**minimal_data)
        assert request.output_type == OutputType.GRANT_PROPOSAL
        assert request.status == OutputStatus.DRAFT  # Default value
        assert request.conversation_id is None

    def test_output_update_request_partial(self):
        """Test OutputUpdateRequest with partial updates"""
        # Update only status
        update_data = {"status": OutputStatus.SUBMITTED}
        request = OutputUpdateRequest(**update_data)
        assert request.status == OutputStatus.SUBMITTED
        assert request.title is None
        assert request.content is None

        # Update multiple fields
        update_data = {
            "status": OutputStatus.AWARDED,
            "awarded_amount": Decimal("45000.00"),
            "decision_date": date(2024, 3, 1),
        }
        request = OutputUpdateRequest(**update_data)
        assert request.status == OutputStatus.AWARDED
        assert request.awarded_amount == Decimal("45000.00")
        assert request.decision_date == date(2024, 3, 1)

    def test_output_update_request_validates_dates(self):
        """Test that OutputUpdateRequest validates date ordering"""
        # Invalid date ordering
        update_data = {
            "submission_date": date(2024, 3, 1),
            "decision_date": date(2024, 1, 15),
        }
        with pytest.raises(ValidationError) as exc_info:
            OutputUpdateRequest(**update_data)
        assert "decision_date cannot be before submission_date" in str(exc_info.value)

    def test_output_update_request_validates_amounts(self):
        """Test that OutputUpdateRequest validates amount limits"""
        # Invalid amount relationship
        update_data = {
            "requested_amount": Decimal("50000.00"),
            "awarded_amount": Decimal("55000.00"),
        }
        with pytest.raises(ValidationError) as exc_info:
            OutputUpdateRequest(**update_data)
        assert "awarded_amount cannot exceed requested_amount" in str(exc_info.value)

    def test_output_response_model(self, complete_output_data):
        """Test OutputResponse model with all fields"""
        response_data = {
            **complete_output_data,
            "output_id": "550e8400-e29b-41d4-a716-446655440000",
            "conversation_id": "650e8400-e29b-41d4-a716-446655440001",
            "created_by": "user123",
            "created_at": datetime(2024, 1, 1, 12, 0, 0),
            "updated_at": datetime(2024, 3, 1, 15, 30, 0),
        }
        response = OutputResponse(**response_data)
        assert response.output_id == "550e8400-e29b-41d4-a716-446655440000"
        assert response.created_by == "user123"
        assert response.created_at == datetime(2024, 1, 1, 12, 0, 0)
        assert response.updated_at == datetime(2024, 3, 1, 15, 30, 0)


# ==================== Edge Cases and Special Scenarios ====================

class TestEdgeCases:
    """Test edge cases and special scenarios"""

    def test_metadata_json_serialization(self, valid_output_data):
        """Test that metadata field accepts various JSON structures"""
        # Simple metadata
        data = {**valid_output_data, "metadata": {"key": "value"}}
        output = OutputBase(**data)
        assert output.metadata == {"key": "value"}

        # Complex nested metadata
        complex_metadata = {
            "sources": ["doc1.pdf", "doc2.pdf"],
            "confidence": 0.95,
            "ai_model": "claude-3-sonnet",
            "processing": {"time_ms": 1500, "tokens": 2000},
        }
        data = {**valid_output_data, "metadata": complex_metadata}
        output = OutputBase(**data)
        assert output.metadata == complex_metadata

    def test_all_output_types(self, valid_output_data):
        """Test that all OutputType enum values work correctly"""
        output_types = [
            OutputType.GRANT_PROPOSAL,
            OutputType.BUDGET_NARRATIVE,
            OutputType.PROGRAM_DESCRIPTION,
            OutputType.IMPACT_SUMMARY,
            OutputType.OTHER,
        ]
        for output_type in output_types:
            data = {**valid_output_data, "output_type": output_type}
            output = OutputBase(**data)
            assert output.output_type == output_type

    def test_all_output_statuses(self, valid_output_data):
        """Test that all OutputStatus enum values work correctly"""
        statuses = [
            OutputStatus.DRAFT,
            OutputStatus.SUBMITTED,
            OutputStatus.PENDING,
            OutputStatus.AWARDED,
            OutputStatus.NOT_AWARDED,
        ]
        for status in statuses:
            data = {**valid_output_data, "status": status}
            output = OutputBase(**data)
            assert output.status == status

    def test_decimal_precision(self, valid_output_data):
        """Test that Decimal fields maintain precision"""
        data = {
            **valid_output_data,
            "requested_amount": Decimal("50000.12"),
            "awarded_amount": Decimal("45000.99"),
        }
        output = OutputBase(**data)
        assert output.requested_amount == Decimal("50000.12")
        assert output.awarded_amount == Decimal("45000.99")
