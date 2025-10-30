"""
Style Analysis Service

AI-powered writing style analysis using Claude to extract
style patterns from writing samples and generate style prompts.
"""

import logging
import time
from typing import List, Dict, Any

from anthropic import AsyncAnthropic

from ..config import settings
from ..models.writing_style import StyleAnalysisResponse

logger = logging.getLogger(__name__)


class StyleAnalysisService:
    """
    Service for analyzing writing samples to generate style prompts

    Uses Claude AI to analyze:
    - Vocabulary and word choice
    - Sentence structure and complexity
    - Thought composition and logic
    - Paragraph organization
    - Transitions and flow
    - Tone and formality
    - Perspective (1st/3rd person)
    - Data integration approach
    """

    def __init__(self):
        """Initialize style analysis service"""
        self.client = AsyncAnthropic(api_key=settings.anthropic_api_key)
        self.model = settings.claude_model
        logger.info(f"Initialized StyleAnalysisService with model: {self.model}")

    async def analyze_samples(
        self,
        samples: List[str],
        style_type: str,
        style_name: str | None = None,
    ) -> StyleAnalysisResponse:
        """
        Analyze writing samples to generate a style prompt

        Args:
            samples: List of writing samples (3-7 samples)
            style_type: Type of writing style (grant, proposal, report, general)
            style_name: Optional name for the style

        Returns:
            StyleAnalysisResponse with generated style prompt and metadata

        Raises:
            ValueError: If samples validation fails
            Exception: If AI analysis fails
        """
        start_time = time.time()

        try:
            # Calculate sample statistics
            sample_stats = self._calculate_sample_stats(samples)

            # Validate samples meet requirements
            self._validate_samples(samples, sample_stats)

            # Build analysis prompt
            system_prompt = self._build_system_prompt(style_type)
            user_prompt = self._build_user_prompt(samples, style_type, style_name)

            logger.info(
                f"Analyzing {len(samples)} samples ({sample_stats['total_words']} total words) "
                f"for {style_type} style"
            )

            # Call Claude API
            response = await self.client.messages.create(
                model=self.model,
                max_tokens=4096,  # Style prompts are typically 1500-2000 words
                temperature=0.3,  # Lower temperature for more consistent analysis
                system=system_prompt,
                messages=[
                    {
                        "role": "user",
                        "content": user_prompt,
                    }
                ],
            )

            # Extract generated style prompt
            style_prompt = response.content[0].text

            # Calculate generation time and metrics
            generation_time = time.time() - start_time
            word_count = len(style_prompt.split())
            tokens_used = response.usage.input_tokens + response.usage.output_tokens

            # Extract analysis metadata from the generated prompt
            analysis_metadata = self._extract_analysis_metadata(style_prompt)

            # Generate warnings if needed
            warnings = self._generate_warnings(sample_stats, word_count)

            logger.info(
                f"Analysis complete. Generated {word_count} word style prompt in {generation_time:.2f}s"
            )

            return StyleAnalysisResponse(
                success=True,
                style_prompt=style_prompt,
                style_name=style_name,
                style_type=style_type,
                analysis_metadata=analysis_metadata,
                sample_stats=sample_stats,
                word_count=word_count,
                generation_time=generation_time,
                tokens_used=tokens_used,
                model=self.model,
                warnings=warnings,
                errors=[],
            )

        except ValueError as e:
            logger.error(f"Validation error in analyze_samples: {e}")
            return StyleAnalysisResponse(
                success=False,
                style_name=style_name,
                style_type=style_type,
                warnings=[],
                errors=[str(e)],
            )

        except Exception as e:
            logger.error(f"Failed to analyze samples: {e}")
            return StyleAnalysisResponse(
                success=False,
                style_name=style_name,
                style_type=style_type,
                warnings=[],
                errors=[f"Analysis failed: {str(e)}"],
            )

    def _calculate_sample_stats(self, samples: List[str]) -> Dict[str, Any]:
        """
        Calculate statistics about the writing samples

        Args:
            samples: List of sample texts

        Returns:
            Dictionary with sample statistics
        """
        word_counts = [len(sample.split()) for sample in samples]
        total_words = sum(word_counts)
        avg_words = total_words / len(samples) if samples else 0

        return {
            "sample_count": len(samples),
            "total_words": total_words,
            "avg_words_per_sample": round(avg_words, 1),
            "min_words": min(word_counts) if word_counts else 0,
            "max_words": max(word_counts) if word_counts else 0,
            "word_counts": word_counts,
        }

    def _validate_samples(
        self,
        samples: List[str],
        stats: Dict[str, Any]
    ) -> None:
        """
        Validate samples meet requirements

        Args:
            samples: List of sample texts
            stats: Sample statistics

        Raises:
            ValueError: If validation fails
        """
        # Check sample count
        if len(samples) < 3:
            raise ValueError("Minimum 3 samples required")
        if len(samples) > 7:
            raise ValueError("Maximum 7 samples allowed")

        # Check minimum words per sample
        for i, count in enumerate(stats["word_counts"], 1):
            if count < 200:
                raise ValueError(
                    f"Sample {i} has {count} words, minimum 200 required"
                )

        # Check total word count recommendations
        if stats["total_words"] < 1000:
            logger.warning(
                f"Total word count {stats['total_words']} is below recommended 1000"
            )
        if stats["total_words"] > 10000:
            logger.warning(
                f"Total word count {stats['total_words']} exceeds recommended 10000"
            )

    def _build_system_prompt(self, style_type: str) -> str:
        """
        Build system prompt for style analysis

        Args:
            style_type: Type of writing style

        Returns:
            System prompt string
        """
        style_type_guidance = {
            "grant": "grant proposals and funding applications",
            "proposal": "business proposals and partnership documents",
            "report": "reports, updates, and documentation",
            "general": "general organizational communications",
        }

        guidance = style_type_guidance.get(
            style_type,
            "organizational writing"
        )

        return f"""You are an expert writing style analyst and technical writing consultant. Your task is to analyze writing samples and create a comprehensive style guide that captures the unique voice and patterns of the writing.

The samples provided are from {guidance}. Your analysis should help writers replicate this style consistently.

Analyze the following elements:
1. **Vocabulary**: Word choice, complexity level, technical terms, jargon usage, preferred terminology
2. **Sentence Structure**: Average length, variety, complexity, active vs. passive voice, sentence patterns
3. **Thought Composition**: How ideas are presented, logical flow, argument structure, use of evidence
4. **Paragraph Structure**: Length, organization, topic sentences, coherence, supporting details
5. **Transitions**: Connective phrases, logical connectors, flow between ideas and sections
6. **Tone**: Formality level, warmth, directness, confidence, professionalism
7. **Perspective**: Person (1st, 3rd), organizational voice, author presence
8. **Data Integration**: How statistics, facts, and evidence are woven into narrative

Generate a comprehensive style prompt (1500-2000 words) organized as:

## Style Overview
[2-3 paragraph summary of the writing style]

## Detailed Guidelines

### Vocabulary and Word Choice
[Specific patterns, preferred terms, complexity level]

### Sentence Structure
[Patterns, typical constructions, variety approaches]

### Thought Composition
[How ideas are developed, logic flow, argument building]

### Paragraph Organization
[Structure patterns, length, coherence approaches]

### Transitions and Flow
[Connective techniques, flow patterns]

### Tone and Voice
[Formality, warmth, confidence patterns]

### Perspective and Person
[POV patterns, organizational voice]

### Data and Evidence Integration
[How facts, stats, examples are incorporated]

## Do's and Don'ts
[Specific guidance on what to do and avoid]

## Example Patterns
[Extract 3-5 specific examples from the samples that exemplify the style]

Make the style guide actionable and specific. Include concrete examples from the samples to illustrate key patterns."""

    def _build_user_prompt(
        self,
        samples: List[str],
        style_type: str,
        style_name: str | None
    ) -> str:
        """
        Build user prompt with samples

        Args:
            samples: List of writing samples
            style_type: Type of style
            style_name: Optional style name

        Returns:
            User prompt string
        """
        # Format samples
        formatted_samples = []
        for i, sample in enumerate(samples, 1):
            formatted_samples.append(f"=== Sample {i} ===\n{sample}\n")

        samples_text = "\n".join(formatted_samples)

        name_text = f" named '{style_name}'" if style_name else ""

        return f"""Analyze the following writing samples and create a comprehensive style guide for a {style_type} writing style{name_text}.

{samples_text}

Generate a detailed style prompt that captures the unique voice, patterns, and characteristics of this writing. The style guide should enable other writers to replicate this style consistently."""

    def _extract_analysis_metadata(self, style_prompt: str) -> Dict[str, Any]:
        """
        Extract structured metadata from the generated style prompt

        Args:
            style_prompt: Generated style prompt text

        Returns:
            Dictionary with analysis metadata
        """
        # Extract key sections that were analyzed
        metadata = {
            "vocabulary": "vocabulary" in style_prompt.lower(),
            "sentence_structure": "sentence" in style_prompt.lower(),
            "thought_composition": "thought" in style_prompt.lower() or "logic" in style_prompt.lower(),
            "paragraph_structure": "paragraph" in style_prompt.lower(),
            "transitions": "transition" in style_prompt.lower(),
            "tone": "tone" in style_prompt.lower(),
            "perspective": "perspective" in style_prompt.lower() or "person" in style_prompt.lower(),
            "data_integration": "data" in style_prompt.lower() or "evidence" in style_prompt.lower(),
        }

        # Count sections
        metadata["sections_analyzed"] = sum(1 for v in metadata.values() if v)

        return metadata

    def _generate_warnings(
        self,
        sample_stats: Dict[str, Any],
        style_prompt_word_count: int
    ) -> List[str]:
        """
        Generate warnings about the analysis

        Args:
            sample_stats: Statistics about samples
            style_prompt_word_count: Word count of generated prompt

        Returns:
            List of warning messages
        """
        warnings = []

        # Check sample count
        if sample_stats["sample_count"] == 3:
            warnings.append(
                "Only 3 samples provided. Consider adding more samples for better analysis."
            )

        # Check total word count
        if sample_stats["total_words"] < 1000:
            warnings.append(
                f"Total word count ({sample_stats['total_words']}) is below recommended 1000. "
                "More content will improve analysis accuracy."
            )
        elif sample_stats["total_words"] > 10000:
            warnings.append(
                f"Total word count ({sample_stats['total_words']}) exceeds recommended 10000. "
                "Analysis may have difficulty identifying consistent patterns."
            )

        # Check style prompt length
        if style_prompt_word_count < 1000:
            warnings.append(
                "Generated style prompt is shorter than typical. Consider refining or adding more samples."
            )
        elif style_prompt_word_count > 2500:
            warnings.append(
                "Generated style prompt is longer than typical. Consider making it more concise."
            )

        return warnings
