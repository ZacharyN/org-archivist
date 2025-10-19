"""
Quick test script for GenerationService

Tests:
- Service initialization
- System prompt building
- User prompt building
- Citation extraction
- Citation validation
"""

import asyncio
import sys
import os

# Add backend to path
sys.path.insert(0, os.path.dirname(__file__))

from app.services.generation_service import GenerationService, GenerationConfig
from app.models.query import Source


def test_initialization():
    """Test service initialization"""
    print("Test 1: Service initialization...")

    config = GenerationConfig()
    service = GenerationService(config)

    assert service.config.model == config.model
    assert service.client is not None
    assert service.async_client is not None

    print(f"  [OK] Service initialized with model: {service.config.model}")


def test_system_prompt():
    """Test system prompt building"""
    print("\nTest 2: System prompt building...")

    service = GenerationService()

    prompt = service._build_system_prompt(
        audience="Federal RFP",
        section="Organizational Capacity",
        tone="Professional"
    )

    prompt_lower = prompt.lower()

    assert "Federal RFP" in prompt
    assert "Organizational Capacity" in prompt
    assert "professional" in prompt_lower
    assert "grant writer" in prompt_lower
    assert "citation" in prompt_lower  # Allow "citation" or "citations"

    print(f"  [OK] System prompt created ({len(prompt)} chars)")
    print(f"  Sample: {prompt[:150]}...")


def test_user_prompt():
    """Test user prompt building"""
    print("\nTest 3: User prompt building...")

    service = GenerationService()

    # Create sample sources
    sources = [
        Source(
            id=1,
            filename="grant_2023.pdf",
            doc_type="Grant Proposal",
            year=2023,
            excerpt="Our organization has served 5,000 youth through after-school programs.",
            relevance=0.95,
            chunk_index=0
        ),
        Source(
            id=2,
            filename="annual_report_2022.pdf",
            doc_type="Annual Report",
            year=2022,
            excerpt="We achieved a 95% college acceptance rate among program participants.",
            relevance=0.89,
            chunk_index=5
        )
    ]

    prompt = service._build_user_prompt(
        query="Describe our program outcomes",
        sources=sources,
        include_citations=True,
        custom_instructions="Focus on quantitative metrics"
    )

    assert "Describe our program outcomes" in prompt
    assert "[1]" in prompt
    assert "[2]" in prompt
    assert "grant_2023.pdf" in prompt
    assert "annual_report_2022.pdf" in prompt
    assert "citations" in prompt.lower()
    assert "quantitative metrics" in prompt

    print(f"  [OK] User prompt created ({len(prompt)} chars)")
    print(f"  Sources included: 2")


def test_citation_extraction():
    """Test citation extraction"""
    print("\nTest 4: Citation extraction...")

    service = GenerationService()

    text = """Our organization has demonstrated strong impact [1].
    We served 5,000 youth [2] and achieved a 95% college acceptance rate [2][3].
    Multiple sources [1][4] confirm our effectiveness."""

    citations = service.extract_citations(text)

    assert citations == [1, 2, 3, 4]

    print(f"  [OK] Extracted citations: {citations}")


def test_citation_validation():
    """Test citation validation"""
    print("\nTest 5: Citation validation...")

    service = GenerationService()

    # Create sample sources
    sources = [
        Source(id=1, filename="doc1.pdf", doc_type="Grant", year=2023,
               excerpt="excerpt1", relevance=0.9, chunk_index=0),
        Source(id=2, filename="doc2.pdf", doc_type="Report", year=2022,
               excerpt="excerpt2", relevance=0.8, chunk_index=0),
        Source(id=3, filename="doc3.pdf", doc_type="Letter", year=2021,
               excerpt="excerpt3", relevance=0.7, chunk_index=0)
    ]

    # Text with valid and invalid citations
    text = "Valid citation [1] and [2]. Invalid citation [5]. Uncited source 3."

    validation = service.validate_citations(text, sources)

    assert validation["valid"] == False  # Has invalid citations
    assert 5 in validation["invalid_citations"]
    assert 1 in validation["cited_sources"]
    assert 2 in validation["cited_sources"]
    assert 3 in validation["uncited_sources"]
    assert validation["total_citations"] == 3  # [1], [2], [5]

    print(f"  [OK] Citation validation:")
    print(f"    Valid: {validation['valid']}")
    print(f"    Cited sources: {validation['cited_sources']}")
    print(f"    Uncited sources: {validation['uncited_sources']}")
    print(f"    Invalid citations: {validation['invalid_citations']}")


async def test_generation_mock():
    """Test generation (mock mode, no API call)"""
    print("\nTest 6: Generation service structure...")

    # Just verify the method exists and has correct signature
    service = GenerationService()

    # Check that methods exist
    assert hasattr(service, 'generate')
    assert hasattr(service, 'generate_stream')

    print("  [OK] Generation methods available")
    print("    - generate (non-streaming)")
    print("    - generate_stream (streaming)")
    print("\nNote: Actual API calls require valid ANTHROPIC_API_KEY")


def main():
    """Run all tests"""
    print("=" * 60)
    print("GenerationService Test Suite")
    print("=" * 60)

    try:
        test_initialization()
        test_system_prompt()
        test_user_prompt()
        test_citation_extraction()
        test_citation_validation()

        # Run async test
        asyncio.run(test_generation_mock())

        print("\n" + "=" * 60)
        print("[SUCCESS] All tests passed!")
        print("=" * 60)

    except AssertionError as e:
        print(f"\n[FAIL] Test failed: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n[ERROR] Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
