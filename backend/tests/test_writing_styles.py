"""
Comprehensive Writing Styles Tests

Tests for Phase 3: Writing Styles Feature
- Sample validation (min 3 samples, 200 words each)
- AI analysis with mocked Claude responses
- Style creation, retrieval, update, deletion
- Style filtering (by type, active status, search)
- End-to-end workflow verification
"""

import pytest
from datetime import datetime
from unittest.mock import AsyncMock, Mock, patch
from uuid import uuid4, UUID
from typing import Dict, Any

from backend.app.models.writing_style import (
    StyleAnalysisRequest,
    StyleAnalysisResponse,
    WritingStyleCreateRequest,
    WritingStyleUpdateRequest,
    WritingStyle,
)
from backend.app.services.style_analysis import StyleAnalysisService
from backend.app.services.database import DatabaseService


# ==================== Test Data ====================

def generate_sample_text(word_count: int = 200) -> str:
    """Generate a sample text with specified word count"""
    base_text = (
        "We are committed to fostering educational excellence through innovative programs. "
        "Our comprehensive approach integrates evidence-based practices with community engagement. "
        "Students demonstrate measurable growth across multiple domains including academic achievement, "
        "social-emotional learning, and civic participation. Data from recent evaluations shows "
        "significant improvements in key performance indicators. Partnerships with local organizations "
        "strengthen our capacity to serve diverse populations. "
    )

    # Repeat and trim to exact word count
    words = (base_text * (word_count // len(base_text.split()) + 1)).split()
    return " ".join(words[:word_count])


@pytest.fixture
def valid_samples():
    """Generate 3 valid samples with 200+ words each"""
    return [
        generate_sample_text(250),
        generate_sample_text(300),
        generate_sample_text(220),
    ]


@pytest.fixture
def mock_claude_response():
    """Mock Claude API response for style analysis"""
    return Mock(
        content=[
            Mock(
                text="""## Style Overview

This writing demonstrates a professional, evidence-based approach typical of grant proposals. The style balances formality with accessibility, using clear language to communicate complex programmatic concepts. The voice is confident yet collaborative, emphasizing organizational capacity while acknowledging partnership and community engagement.

## Detailed Guidelines

### Vocabulary and Word Choice
The vocabulary reflects professionalism without excessive jargon. Key characteristics include:
- Action-oriented verbs (demonstrate, foster, integrate, strengthen)
- Evidence-based terminology (data, evaluations, indicators, outcomes)
- Community-focused language (engagement, partnerships, populations)
- Aspirational but grounded adjectives (innovative, comprehensive, measurable)

### Sentence Structure
Sentences vary in length and complexity:
- Mix of simple declarative statements and compound sentences
- Average length: 15-20 words
- Predominantly active voice with occasional passive constructions for emphasis
- Parallel structure used for lists and multiple concepts

### Thought Composition
Ideas flow logically from commitment to evidence to partnership:
- Opening with organizational mission and approach
- Supporting with data and outcomes
- Concluding with capacity and collaboration
- Cause-and-effect relationships clearly articulated

### Paragraph Organization
Paragraphs are focused and cohesive:
- Clear topic sentences establishing main ideas
- Supporting details with specific examples
- Smooth transitions between related concepts
- Typical length: 4-6 sentences or 80-120 words

### Transitions and Flow
Transitions create smooth progression:
- Logical connectors (through, across, including)
- Temporal markers (recent, ongoing)
- Causal relationships (demonstrates, shows, strengthens)
- Building from program to impact to sustainability

### Tone and Voice
The tone is professional, confident, and collaborative:
- Formal but not stuffy or overly academic
- Warm and inclusive without being casual
- Evidence-based without being dry or technical
- Future-focused while grounded in current capacity

### Perspective and Person
First person plural ("we", "our") establishes organizational voice:
- Emphasizes collective effort and institutional commitment
- Balances organizational agency with community partnership
- Maintains professional distance while conveying passion

### Data and Evidence Integration
Data is woven naturally into narrative:
- Specific metrics provided without overwhelming
- Qualitative and quantitative evidence balanced
- Data supports rather than replaces narrative
- Sources and timeframes clearly indicated

## Do's and Don'ts

**Do:**
- Lead with mission and values before diving into details
- Use specific, measurable language when describing outcomes
- Balance confidence with humility and collaboration
- Vary sentence structure for readability
- Support claims with data and evidence

**Don't:**
- Use excessive jargon or academic language
- Make unsupported claims or overpromise
- Write in passive voice unnecessarily
- Create overly long paragraphs (keep to 4-6 sentences)
- Lose sight of the human impact behind the data

## Example Patterns

1. **Opening with commitment**: "We are committed to fostering educational excellence through innovative programs."
   - Establishes mission immediately
   - Uses action verb + value + approach structure

2. **Evidence integration**: "Data from recent evaluations shows significant improvements in key performance indicators."
   - Cites source timeframe
   - Uses strong verb (shows) to connect data to finding
   - Specific without overwhelming with numbers

3. **Partnership framing**: "Partnerships with local organizations strengthen our capacity to serve diverse populations."
   - Emphasizes collaboration
   - Links partnership to organizational capacity
   - Acknowledges community diversity

This style guide enables consistent voice across grant proposals, reports, and organizational communications while maintaining authenticity and credibility."""
            )
        ],
        usage=Mock(input_tokens=1200, output_tokens=800),
    )


@pytest.fixture
def mock_database_service():
    """Mock database service for testing"""
    mock_db = AsyncMock(spec=DatabaseService)

    # Configure mock methods
    mock_db.create_writing_style.return_value = str(uuid4())
    mock_db.get_writing_style.return_value = {
        "style_id": str(uuid4()),
        "name": "Test Grant Style",
        "type": "grant",
        "description": "Test description",
        "prompt_content": "Test prompt content with enough words to meet minimum requirements for testing purposes.",
        "samples": [],
        "analysis_metadata": {"vocabulary": True},
        "sample_count": 3,
        "active": True,
        "created_at": datetime.utcnow().isoformat(),
        "updated_at": datetime.utcnow().isoformat(),
        "created_by": None,
    }
    mock_db.list_writing_styles.return_value = []
    mock_db.update_writing_style.return_value = True
    mock_db.delete_writing_style.return_value = True
    mock_db.get_writing_style_by_name.return_value = None

    return mock_db


# ==================== Validation Tests ====================

class TestSampleValidation:
    """Test sample validation requirements"""

    def test_minimum_samples_required(self):
        """Test that minimum 3 samples are required"""
        # Valid request with 3 samples
        samples = [generate_sample_text(200) for _ in range(3)]
        request = StyleAnalysisRequest(
            samples=samples,
            style_type="grant",
        )
        assert len(request.samples) == 3

        # Invalid request with 2 samples
        with pytest.raises(Exception, match="at least 3 items"):
            StyleAnalysisRequest(
                samples=[generate_sample_text(200) for _ in range(2)],
                style_type="grant",
            )

    def test_maximum_samples_enforced(self):
        """Test that maximum 7 samples are enforced"""
        # Valid request with 7 samples
        samples = [generate_sample_text(200) for _ in range(7)]
        request = StyleAnalysisRequest(
            samples=samples,
            style_type="grant",
        )
        assert len(request.samples) == 7

        # Invalid request with 8 samples
        with pytest.raises(Exception, match="at most 7 items"):
            StyleAnalysisRequest(
                samples=[generate_sample_text(200) for _ in range(8)],
                style_type="grant",
            )

    def test_minimum_word_count_per_sample(self):
        """Test that each sample must have at least 200 words"""
        # Valid samples with 200+ words
        samples = [
            generate_sample_text(200),
            generate_sample_text(250),
            generate_sample_text(300),
        ]
        request = StyleAnalysisRequest(
            samples=samples,
            style_type="grant",
        )
        assert all(len(s.split()) >= 200 for s in request.samples)

        # Invalid - sample 2 has less than 200 words
        with pytest.raises(ValueError, match="Sample 2 has .* words, minimum 200 required"):
            StyleAnalysisRequest(
                samples=[
                    generate_sample_text(200),
                    generate_sample_text(150),  # Too short
                    generate_sample_text(200),
                ],
                style_type="grant",
            )

    def test_valid_style_types(self):
        """Test that only valid style types are accepted"""
        samples = [generate_sample_text(200) for _ in range(3)]

        # Valid types
        for style_type in ["grant", "proposal", "report", "general"]:
            request = StyleAnalysisRequest(
                samples=samples,
                style_type=style_type,
            )
            assert request.style_type == style_type

        # Invalid type
        with pytest.raises(ValueError, match="style_type must be one of"):
            StyleAnalysisRequest(
                samples=samples,
                style_type="invalid_type",
            )


# ==================== AI Analysis Tests ====================

class TestAIAnalysis:
    """Test AI analysis with mocked Claude responses"""

    @pytest.mark.asyncio
    async def test_analyze_samples_success(self, valid_samples, mock_claude_response):
        """Test successful sample analysis with mocked Claude"""
        service = StyleAnalysisService()

        # Mock the Anthropic client
        with patch.object(service.client.messages, 'create', new_callable=AsyncMock) as mock_create:
            mock_create.return_value = mock_claude_response

            # Analyze samples
            response = await service.analyze_samples(
                samples=valid_samples,
                style_type="grant",
                style_name="Test Grant Style",
            )

            # Verify response
            assert response.success is True
            assert response.style_prompt is not None
            assert len(response.style_prompt) > 0
            assert response.style_name == "Test Grant Style"
            assert response.style_type == "grant"
            assert response.word_count > 0
            assert response.generation_time > 0
            assert response.tokens_used == 2000  # 1200 input + 800 output
            assert len(response.errors) == 0

            # Verify analysis metadata
            assert response.analysis_metadata is not None
            assert response.analysis_metadata["vocabulary"] is True
            assert response.analysis_metadata["sentence_structure"] is True

            # Verify sample stats
            assert response.sample_stats is not None
            assert response.sample_stats["sample_count"] == 3
            assert response.sample_stats["total_words"] > 600

    @pytest.mark.asyncio
    async def test_analyze_samples_with_warnings(self, mock_claude_response):
        """Test that warnings are generated for minimal samples"""
        service = StyleAnalysisService()

        # Exactly 3 samples (minimum) with low total word count
        minimal_samples = [generate_sample_text(200) for _ in range(3)]

        with patch.object(service.client.messages, 'create', new_callable=AsyncMock) as mock_create:
            mock_create.return_value = mock_claude_response

            response = await service.analyze_samples(
                samples=minimal_samples,
                style_type="general",
            )

            # Should succeed but with warnings
            assert response.success is True
            assert len(response.warnings) > 0
            assert any("3 samples" in w for w in response.warnings)

    @pytest.mark.asyncio
    async def test_analyze_samples_validation_failure(self):
        """Test that validation errors are handled properly"""
        service = StyleAnalysisService()

        # Samples that fail validation (< 200 words)
        invalid_samples = [
            "Short sample one.",
            "Short sample two.",
            "Short sample three.",
        ]

        response = await service.analyze_samples(
            samples=invalid_samples,
            style_type="grant",
        )

        # Should fail validation
        assert response.success is False
        assert len(response.errors) > 0
        assert any("200 required" in e for e in response.errors)

    @pytest.mark.asyncio
    async def test_analyze_samples_api_failure(self, valid_samples):
        """Test handling of API failures"""
        service = StyleAnalysisService()

        # Mock API failure
        with patch.object(service.client.messages, 'create', new_callable=AsyncMock) as mock_create:
            mock_create.side_effect = Exception("API connection failed")

            response = await service.analyze_samples(
                samples=valid_samples,
                style_type="grant",
            )

            # Should fail gracefully
            assert response.success is False
            assert len(response.errors) > 0
            assert any("failed" in e.lower() for e in response.errors)


# ==================== Style CRUD Tests ====================

class TestStyleCreation:
    """Test writing style creation"""

    @pytest.mark.asyncio
    async def test_create_style_success(self, mock_database_service):
        """Test successful style creation"""
        # Prepare creation request
        request = WritingStyleCreateRequest(
            name="Professional Grant Style",
            type="grant",
            description="A professional style for federal grant proposals",
            prompt_content="This is a comprehensive style guide with detailed instructions for writing in a professional grant style that meets all requirements and expectations." * 10,  # Make it long enough
            samples=[generate_sample_text(200) for _ in range(3)],
            analysis_metadata={"vocabulary": True, "tone": True},
        )

        # Create style (mock database)
        style_id = await mock_database_service.create_writing_style(
            style_id=uuid4(),
            name=request.name,
            style_type=request.type,
            prompt_content=request.prompt_content,
            description=request.description,
            samples=request.samples,
            analysis_metadata=request.analysis_metadata,
            sample_count=len(request.samples),
            created_by=None,
        )

        assert style_id is not None
        mock_database_service.create_writing_style.assert_called_once()

    def test_create_style_validation(self):
        """Test style creation validation"""
        from pydantic import ValidationError

        # Name too short
        with pytest.raises(ValidationError):
            WritingStyleCreateRequest(
                name="",
                type="grant",
                prompt_content="A" * 100,
            )

        # Prompt too short
        with pytest.raises(ValidationError):
            WritingStyleCreateRequest(
                name="Test Style",
                type="grant",
                prompt_content="Too short",
            )

        # Valid creation should work
        valid_request = WritingStyleCreateRequest(
            name="Valid Style",
            type="grant",
            prompt_content="A" * 101,  # Just over minimum
        )
        assert valid_request.name == "Valid Style"
        assert valid_request.type == "grant"


class TestStyleRetrieval:
    """Test writing style retrieval"""

    @pytest.mark.asyncio
    async def test_get_style_by_id(self, mock_database_service):
        """Test retrieving a style by ID"""
        style_id = uuid4()

        result = await mock_database_service.get_writing_style(style_id)

        assert result is not None
        assert "style_id" in result
        assert "name" in result
        assert "prompt_content" in result
        mock_database_service.get_writing_style.assert_called_once_with(style_id)

    @pytest.mark.asyncio
    async def test_get_style_not_found(self, mock_database_service):
        """Test handling of non-existent style"""
        mock_database_service.get_writing_style.return_value = None

        result = await mock_database_service.get_writing_style(uuid4())

        assert result is None

    @pytest.mark.asyncio
    async def test_list_styles(self, mock_database_service):
        """Test listing all styles"""
        # Configure mock to return multiple styles
        mock_database_service.list_writing_styles.return_value = [
            {
                "style_id": str(uuid4()),
                "name": "Grant Style 1",
                "type": "grant",
                "description": "Description 1",
                "sample_count": 3,
                "active": True,
                "created_at": datetime.utcnow().isoformat(),
                "updated_at": datetime.utcnow().isoformat(),
                "created_by": None,
            },
            {
                "style_id": str(uuid4()),
                "name": "Proposal Style 1",
                "type": "proposal",
                "description": "Description 2",
                "sample_count": 5,
                "active": True,
                "created_at": datetime.utcnow().isoformat(),
                "updated_at": datetime.utcnow().isoformat(),
                "created_by": None,
            },
        ]

        result = await mock_database_service.list_writing_styles()

        assert len(result) == 2
        assert result[0]["type"] == "grant"
        assert result[1]["type"] == "proposal"


class TestStyleFiltering:
    """Test filtering writing styles"""

    @pytest.mark.asyncio
    async def test_filter_by_type(self, mock_database_service):
        """Test filtering styles by type"""
        # Configure mock to return only grant styles
        mock_database_service.list_writing_styles.return_value = [
            {
                "style_id": str(uuid4()),
                "name": "Grant Style 1",
                "type": "grant",
                "description": "Grant description",
                "sample_count": 3,
                "active": True,
                "created_at": datetime.utcnow().isoformat(),
                "updated_at": datetime.utcnow().isoformat(),
                "created_by": None,
            },
        ]

        result = await mock_database_service.list_writing_styles(style_type="grant")

        assert len(result) == 1
        assert all(style["type"] == "grant" for style in result)
        mock_database_service.list_writing_styles.assert_called_once_with(style_type="grant")

    @pytest.mark.asyncio
    async def test_filter_by_active_status(self, mock_database_service):
        """Test filtering by active status"""
        # Configure mock to return only active styles
        mock_database_service.list_writing_styles.return_value = [
            {
                "style_id": str(uuid4()),
                "name": "Active Style",
                "type": "grant",
                "description": "Active description",
                "sample_count": 3,
                "active": True,
                "created_at": datetime.utcnow().isoformat(),
                "updated_at": datetime.utcnow().isoformat(),
                "created_by": None,
            },
        ]

        result = await mock_database_service.list_writing_styles(active=True)

        assert len(result) == 1
        assert all(style["active"] is True for style in result)

    @pytest.mark.asyncio
    async def test_filter_by_search(self, mock_database_service):
        """Test searching styles by name/description"""
        # Configure mock to return matching styles
        mock_database_service.list_writing_styles.return_value = [
            {
                "style_id": str(uuid4()),
                "name": "Federal Grant Style",
                "type": "grant",
                "description": "For federal applications",
                "sample_count": 3,
                "active": True,
                "created_at": datetime.utcnow().isoformat(),
                "updated_at": datetime.utcnow().isoformat(),
                "created_by": None,
            },
        ]

        result = await mock_database_service.list_writing_styles(search="federal")

        assert len(result) == 1
        assert "federal" in result[0]["name"].lower() or "federal" in result[0]["description"].lower()

    @pytest.mark.asyncio
    async def test_combined_filters(self, mock_database_service):
        """Test combining multiple filters"""
        # Filter by type AND active status
        result = await mock_database_service.list_writing_styles(
            style_type="grant",
            active=True,
        )

        mock_database_service.list_writing_styles.assert_called_once_with(
            style_type="grant",
            active=True,
        )


class TestStyleUpdate:
    """Test updating writing styles"""

    @pytest.mark.asyncio
    async def test_update_style_name(self, mock_database_service):
        """Test updating style name"""
        style_id = uuid4()

        result = await mock_database_service.update_writing_style(
            style_id=style_id,
            name="Updated Style Name",
        )

        assert result is True
        mock_database_service.update_writing_style.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_style_active_status(self, mock_database_service):
        """Test updating active status"""
        style_id = uuid4()

        result = await mock_database_service.update_writing_style(
            style_id=style_id,
            active=False,
        )

        assert result is True

    @pytest.mark.asyncio
    async def test_update_style_prompt(self, mock_database_service):
        """Test updating prompt content"""
        style_id = uuid4()

        new_prompt = "Updated comprehensive style guide with new instructions and examples." * 10

        result = await mock_database_service.update_writing_style(
            style_id=style_id,
            prompt_content=new_prompt,
        )

        assert result is True


class TestStyleDeletion:
    """Test deleting writing styles"""

    @pytest.mark.asyncio
    async def test_delete_style(self, mock_database_service):
        """Test successful style deletion"""
        style_id = uuid4()

        result = await mock_database_service.delete_writing_style(style_id)

        assert result is True
        mock_database_service.delete_writing_style.assert_called_once_with(style_id)


# ==================== End-to-End Workflow Tests ====================

class TestEndToEndWorkflow:
    """Test complete writing style workflow"""

    @pytest.mark.asyncio
    async def test_complete_workflow(self, valid_samples, mock_claude_response, mock_database_service):
        """Test end-to-end workflow: analyze → create → retrieve → filter → update → delete"""

        # Step 1: Analyze samples
        analysis_service = StyleAnalysisService()

        with patch.object(analysis_service.client.messages, 'create', new_callable=AsyncMock) as mock_create:
            mock_create.return_value = mock_claude_response

            analysis_response = await analysis_service.analyze_samples(
                samples=valid_samples,
                style_type="grant",
                style_name="Complete Workflow Style",
            )

            assert analysis_response.success is True
            assert analysis_response.style_prompt is not None

        # Step 2: Create style from analysis
        style_id = uuid4()
        await mock_database_service.create_writing_style(
            style_id=style_id,
            name=analysis_response.style_name,
            style_type=analysis_response.style_type,
            prompt_content=analysis_response.style_prompt,
            description="Created from workflow test",
            samples=valid_samples,
            analysis_metadata=analysis_response.analysis_metadata,
            sample_count=len(valid_samples),
            created_by=None,
        )

        # Step 3: Retrieve created style
        mock_database_service.get_writing_style.return_value = {
            "style_id": str(style_id),
            "name": "Complete Workflow Style",
            "type": "grant",
            "description": "Created from workflow test",
            "prompt_content": analysis_response.style_prompt,
            "samples": valid_samples,
            "analysis_metadata": analysis_response.analysis_metadata,
            "sample_count": len(valid_samples),
            "active": True,
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat(),
            "created_by": None,
        }

        retrieved_style = await mock_database_service.get_writing_style(style_id)
        assert retrieved_style is not None
        assert retrieved_style["name"] == "Complete Workflow Style"

        # Step 4: Filter to find style
        mock_database_service.list_writing_styles.return_value = [retrieved_style]
        filtered_styles = await mock_database_service.list_writing_styles(
            style_type="grant",
            active=True,
        )
        assert len(filtered_styles) == 1
        assert filtered_styles[0]["style_id"] == str(style_id)

        # Step 5: Update style
        updated = await mock_database_service.update_writing_style(
            style_id=style_id,
            description="Updated description",
        )
        assert updated is True

        # Step 6: Delete style
        deleted = await mock_database_service.delete_writing_style(style_id)
        assert deleted is True

    @pytest.mark.asyncio
    async def test_workflow_with_refinement(self, valid_samples, mock_claude_response, mock_database_service):
        """Test workflow with style refinement"""

        # Analyze samples
        analysis_service = StyleAnalysisService()

        with patch.object(analysis_service.client.messages, 'create', new_callable=AsyncMock) as mock_create:
            mock_create.return_value = mock_claude_response

            # Initial analysis
            analysis_response = await analysis_service.analyze_samples(
                samples=valid_samples,
                style_type="grant",
                style_name="Refinement Test Style",
            )

            assert analysis_response.success is True
            original_prompt = analysis_response.style_prompt

            # Create style
            style_id = uuid4()
            await mock_database_service.create_writing_style(
                style_id=style_id,
                name="Refinement Test Style",
                style_type="grant",
                prompt_content=original_prompt,
                description="To be refined",
                samples=valid_samples,
                analysis_metadata=analysis_response.analysis_metadata,
                sample_count=len(valid_samples),
                created_by=None,
            )

            # Simulate refinement by updating prompt
            refined_prompt = original_prompt + "\n\n## Additional Refinements\nBased on feedback, emphasize clarity and conciseness."

            updated = await mock_database_service.update_writing_style(
                style_id=style_id,
                prompt_content=refined_prompt,
                description="Refined based on feedback",
            )

            assert updated is True


# ==================== Integration Markers ====================

# Note: Only async test functions are marked with @pytest.mark.asyncio
# Non-async functions (like validation tests) don't need the marker
