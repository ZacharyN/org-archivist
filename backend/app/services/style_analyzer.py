"""
Writing Style Analysis Service

This module provides the StyleAnalyzerService class for analyzing writing samples
and generating comprehensive style prompts using Claude API. Supports:
- Analysis of 3-7 writing samples
- Extraction of 8 key style elements (vocabulary, sentence structure, etc.)
- Generation of 1500-2000 word style prompts
- Refinement operations (make concise, add examples, emphasize aspects)
"""

import logging
import time
from typing import List, Optional, Dict, Any
from dataclasses import dataclass
from enum import Enum

from anthropic import Anthropic, AsyncAnthropic

from ..config import settings

logger = logging.getLogger(__name__)


class StyleRefinementOperation(str, Enum):
    """Available refinement operations for style prompts"""
    MAKE_CONCISE = "make_concise"
    MAKE_SPECIFIC = "make_specific"
    ADD_EXAMPLES = "add_examples"
    EMPHASIZE_ASPECT = "emphasize_aspect"


@dataclass
class StyleAnalysisConfig:
    """Configuration for style analysis"""
    model: str = settings.claude_model
    temperature: float = 0.5  # Slightly higher for creative analysis
    max_tokens: int = 6000  # Need more for comprehensive 1500-2000 word prompts
    timeout: int = 90  # Longer timeout for analysis
    min_samples: int = 3
    max_samples: int = 7
    min_words_per_sample: int = 200
    target_prompt_words_min: int = 1500
    target_prompt_words_max: int = 2000


class StyleAnalyzerService:
    """
    Service for analyzing writing samples and generating style prompts

    Analyzes writing samples to extract style characteristics and generates
    comprehensive prompts that can be used to instruct AI to write in that style.
    """

    def __init__(self, config: Optional[StyleAnalysisConfig] = None):
        """
        Initialize style analyzer service

        Args:
            config: Optional configuration (defaults to StyleAnalysisConfig)
        """
        self.config = config or StyleAnalysisConfig()

        # Initialize Anthropic clients
        self.client = Anthropic(api_key=settings.anthropic_api_key)
        self.async_client = AsyncAnthropic(api_key=settings.anthropic_api_key)

        logger.info(f"Initialized StyleAnalyzerService with model: {self.config.model}")

    def _validate_samples(self, samples: List[str]) -> Dict[str, Any]:
        """
        Validate writing samples meet requirements

        Args:
            samples: List of writing sample texts

        Returns:
            Dictionary with validation results:
                - valid: Boolean indicating if samples are valid
                - errors: List of validation errors
                - warnings: List of validation warnings
                - stats: Dictionary with sample statistics
        """
        errors = []
        warnings = []

        # Check sample count
        if len(samples) < self.config.min_samples:
            errors.append(
                f"Minimum {self.config.min_samples} samples required, got {len(samples)}"
            )
        elif len(samples) > self.config.max_samples:
            errors.append(
                f"Maximum {self.config.max_samples} samples allowed, got {len(samples)}"
            )

        # Check word counts
        word_counts = []
        for i, sample in enumerate(samples, 1):
            word_count = len(sample.split())
            word_counts.append(word_count)

            if word_count < self.config.min_words_per_sample:
                errors.append(
                    f"Sample {i} has {word_count} words, minimum {self.config.min_words_per_sample} required"
                )

        # Calculate total words
        total_words = sum(word_counts)

        # Warn if samples are very short or very long
        if total_words < 1000:
            warnings.append(
                f"Total word count ({total_words}) is low. Recommended: 1000-10000 words"
            )
        elif total_words > 10000:
            warnings.append(
                f"Total word count ({total_words}) is high. May take longer to process"
            )

        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings,
            "stats": {
                "sample_count": len(samples),
                "word_counts": word_counts,
                "total_words": total_words,
                "avg_words_per_sample": total_words / len(samples) if samples else 0
            }
        }

    def _build_analysis_prompt(self, samples: List[str], style_type: str = "general") -> str:
        """
        Build prompt for analyzing writing samples

        Args:
            samples: List of writing sample texts
            style_type: Type of writing (grant, proposal, report, general)

        Returns:
            System and user prompts for Claude API
        """
        # Combine samples with delimiters
        combined_samples = "\n\n---SAMPLE SEPARATOR---\n\n".join(
            f"SAMPLE {i+1}:\n{sample}"
            for i, sample in enumerate(samples)
        )

        system_prompt = """You are an expert writing style analyst with deep expertise in rhetoric, composition, and stylistic analysis. Your task is to analyze writing samples and create comprehensive style guides that capture the unique voice and approach of the writer."""

        user_prompt = f"""Analyze the following writing samples and create a detailed style guide that captures how to write in this style.

WRITING SAMPLES ({len(samples)} samples):
{combined_samples}

Please analyze these samples across the following 8 dimensions:

1. **Vocabulary Selection**: Word choices, complexity level, technical terminology, jargon usage, formality of language, preferred synonyms and phrases

2. **Sentence Structure**: Average sentence length, sentence variety (simple/compound/complex), rhythm and flow, use of active vs passive voice, punctuation patterns

3. **Thought Composition**: How ideas are introduced and developed, logical flow and argumentation style, use of examples and evidence, paragraph-level organization

4. **Paragraph Structure**: Typical paragraph length, use of topic sentences, internal paragraph organization, transitions between paragraphs

5. **Transitions**: Specific transitional phrases used, how ideas are connected, flow between sections, use of signposting

6. **Tone**: Formality level, warmth and accessibility, confidence and assertiveness, objectivity vs subjectivity, emotional resonance

7. **Perspective**: Use of first person (we/our) vs third person, organizational voice characteristics, relationship with reader (inclusive/authoritative/collaborative)

8. **Data Integration**: How statistics and facts are presented, balance of quantitative vs qualitative information, how evidence supports claims, citation and attribution patterns

Generate a comprehensive style prompt (1500-2000 words) that instructs an AI to write in this style. Structure your response as follows:

## Style Overview
[2-3 paragraph summary of the overall writing style and key characteristics]

## Detailed Style Guidelines

### Vocabulary & Language
[Detailed analysis with specific examples from the samples]

### Sentence Structure & Syntax
[Detailed analysis with specific examples from the samples]

### Thought Development & Organization
[Detailed analysis with specific examples from the samples]

### Paragraph Composition
[Detailed analysis with specific examples from the samples]

### Transitions & Flow
[Detailed analysis with specific examples from the samples]

### Tone & Voice
[Detailed analysis with specific examples from the samples]

### Perspective & Point of View
[Detailed analysis with specific examples from the samples]

### Evidence & Data Integration
[Detailed analysis with specific examples from the samples]

## Key Examples
[5-7 representative sentences/passages extracted from the samples that exemplify the style]

## Do's and Don'ts
### Do:
- [5-7 specific guidelines based on the analysis]

### Don't:
- [5-7 specific anti-patterns to avoid]

## Application Guidelines
[Brief section on how to apply this style in practice]

Ensure your style prompt is:
- Comprehensive (1500-2000 words)
- Specific and actionable
- Grounded in the actual samples provided
- Rich with concrete examples
- Clear enough to guide consistent AI writing output"""

        return system_prompt, user_prompt

    async def analyze_style(
        self,
        samples: List[str],
        style_type: str = "general",
        style_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Analyze writing samples and generate comprehensive style prompt

        Args:
            samples: List of writing sample texts (3-7 samples)
            style_type: Type of writing (grant, proposal, report, general)
            style_name: Optional name for the style

        Returns:
            Dictionary with:
                - success: Boolean indicating success
                - style_prompt: Generated style prompt (1500-2000 words)
                - analysis_metadata: Detailed analysis of style elements
                - sample_stats: Statistics about the samples
                - generation_time: Time taken in seconds
                - errors: List of errors if any
        """
        logger.info(
            f"Analyzing {len(samples)} writing samples "
            f"for style type: {style_type}"
        )

        # Validate samples
        validation = self._validate_samples(samples)
        if not validation["valid"]:
            logger.error(f"Sample validation failed: {validation['errors']}")
            return {
                "success": False,
                "errors": validation["errors"],
                "warnings": validation["warnings"]
            }

        if validation["warnings"]:
            logger.warning(f"Validation warnings: {validation['warnings']}")

        start_time = time.time()

        try:
            # Build prompts
            system_prompt, user_prompt = self._build_analysis_prompt(
                samples,
                style_type
            )

            # Call Claude API for analysis
            logger.info("Calling Claude API for style analysis...")
            response = await self.async_client.messages.create(
                model=self.config.model,
                max_tokens=self.config.max_tokens,
                temperature=self.config.temperature,
                system=system_prompt,
                messages=[
                    {"role": "user", "content": user_prompt}
                ],
                timeout=self.config.timeout
            )

            generation_time = time.time() - start_time

            # Extract generated style prompt
            style_prompt = response.content[0].text if response.content else ""

            # Calculate word count
            word_count = len(style_prompt.split())

            logger.info(
                f"Style analysis complete in {generation_time:.2f}s, "
                f"generated {word_count} words"
            )

            # Check if word count is in target range
            warnings = validation["warnings"].copy()
            if word_count < self.config.target_prompt_words_min:
                warnings.append(
                    f"Generated prompt ({word_count} words) is shorter than target "
                    f"({self.config.target_prompt_words_min}-{self.config.target_prompt_words_max} words)"
                )
            elif word_count > self.config.target_prompt_words_max:
                warnings.append(
                    f"Generated prompt ({word_count} words) is longer than target "
                    f"({self.config.target_prompt_words_min}-{self.config.target_prompt_words_max} words)"
                )

            # Extract metadata about style elements (simple keyword-based extraction)
            analysis_metadata = self._extract_analysis_metadata(style_prompt)

            return {
                "success": True,
                "style_prompt": style_prompt,
                "style_name": style_name,
                "style_type": style_type,
                "analysis_metadata": analysis_metadata,
                "sample_stats": validation["stats"],
                "word_count": word_count,
                "generation_time": generation_time,
                "tokens_used": response.usage.input_tokens + response.usage.output_tokens,
                "model": response.model,
                "warnings": warnings
            }

        except Exception as e:
            logger.error(f"Style analysis failed: {e}", exc_info=True)
            return {
                "success": False,
                "errors": [str(e)]
            }

    def _extract_analysis_metadata(self, style_prompt: str) -> Dict[str, Any]:
        """
        Extract metadata about style elements from generated prompt

        Args:
            style_prompt: Generated style prompt text

        Returns:
            Dictionary with presence/analysis of each style element
        """
        # Simple keyword-based detection for each style element
        elements = {
            "vocabulary": ["vocabulary", "word choice", "terminology", "jargon"],
            "sentence_structure": ["sentence", "structure", "syntax", "punctuation"],
            "thought_composition": ["thought", "idea", "argument", "logic"],
            "paragraph_structure": ["paragraph", "topic sentence", "organization"],
            "transitions": ["transition", "flow", "connection", "signpost"],
            "tone": ["tone", "formality", "warmth", "confidence"],
            "perspective": ["perspective", "person", "voice", "point of view"],
            "data_integration": ["data", "evidence", "statistic", "fact"]
        }

        prompt_lower = style_prompt.lower()
        metadata = {}

        for element, keywords in elements.items():
            # Check if element is addressed (any keyword appears)
            addressed = any(keyword in prompt_lower for keyword in keywords)
            # Count keyword occurrences as rough measure of emphasis
            emphasis = sum(prompt_lower.count(keyword) for keyword in keywords)

            metadata[element] = {
                "addressed": addressed,
                "emphasis_score": emphasis
            }

        return metadata

    async def refine_style_prompt(
        self,
        original_prompt: str,
        operation: StyleRefinementOperation,
        aspect: Optional[str] = None,
        custom_instructions: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Refine an existing style prompt with specific operations

        Args:
            original_prompt: The original style prompt to refine
            operation: Refinement operation to perform
            aspect: Specific aspect to emphasize (for EMPHASIZE_ASPECT operation)
            custom_instructions: Additional custom refinement instructions

        Returns:
            Dictionary with:
                - success: Boolean indicating success
                - refined_prompt: Refined style prompt
                - operation: Operation that was performed
                - generation_time: Time taken in seconds
        """
        logger.info(f"Refining style prompt with operation: {operation}")

        # Build refinement prompt based on operation
        if operation == StyleRefinementOperation.MAKE_CONCISE:
            refinement_instructions = """Make this style prompt more concise while retaining all essential style guidance.
Remove redundancy and wordiness, but keep specific examples and actionable guidelines.
Target: 1000-1200 words."""

        elif operation == StyleRefinementOperation.MAKE_SPECIFIC:
            refinement_instructions = """Make this style prompt more specific and detailed.
Add more concrete examples, precise guidelines, and specific techniques.
Expand on vague descriptions with actionable details.
Target: 1800-2200 words."""

        elif operation == StyleRefinementOperation.ADD_EXAMPLES:
            refinement_instructions = """Enhance this style prompt by adding more specific examples throughout.
For each guideline or characteristic, provide concrete examples that illustrate the point.
Ensure examples are diverse and representative of the style being described."""

        elif operation == StyleRefinementOperation.EMPHASIZE_ASPECT:
            if not aspect:
                return {
                    "success": False,
                    "errors": ["aspect parameter required for EMPHASIZE_ASPECT operation"]
                }
            refinement_instructions = f"""Emphasize the '{aspect}' aspect of this style prompt.
Expand the section on {aspect} with more detail, examples, and specific guidance.
Ensure this aspect receives prominent treatment while maintaining balance with other elements."""

        else:
            return {
                "success": False,
                "errors": [f"Unknown refinement operation: {operation}"]
            }

        # Add custom instructions if provided
        if custom_instructions:
            refinement_instructions += f"\n\nAdditional instructions: {custom_instructions}"

        system_prompt = """You are an expert writing style analyst. Your task is to refine and improve style prompts while maintaining their core characteristics and utility."""

        user_prompt = f"""Please refine the following style prompt according to these instructions:

{refinement_instructions}

ORIGINAL STYLE PROMPT:
{original_prompt}

Generate the refined style prompt below:"""

        start_time = time.time()

        try:
            response = await self.async_client.messages.create(
                model=self.config.model,
                max_tokens=self.config.max_tokens,
                temperature=self.config.temperature,
                system=system_prompt,
                messages=[
                    {"role": "user", "content": user_prompt}
                ],
                timeout=self.config.timeout
            )

            generation_time = time.time() - start_time

            refined_prompt = response.content[0].text if response.content else ""
            word_count = len(refined_prompt.split())

            logger.info(
                f"Style prompt refinement complete in {generation_time:.2f}s, "
                f"generated {word_count} words"
            )

            return {
                "success": True,
                "refined_prompt": refined_prompt,
                "original_word_count": len(original_prompt.split()),
                "refined_word_count": word_count,
                "operation": operation.value,
                "aspect": aspect,
                "generation_time": generation_time,
                "tokens_used": response.usage.input_tokens + response.usage.output_tokens,
                "model": response.model
            }

        except Exception as e:
            logger.error(f"Style prompt refinement failed: {e}", exc_info=True)
            return {
                "success": False,
                "errors": [str(e)]
            }

    def calculate_style_metrics(self, text: str) -> Dict[str, Any]:
        """
        Calculate basic metrics about a text sample

        Args:
            text: Text to analyze

        Returns:
            Dictionary with metrics:
                - word_count: Total words
                - sentence_count: Estimated sentences
                - avg_sentence_length: Average words per sentence
                - paragraph_count: Number of paragraphs
        """
        # Basic text metrics
        words = text.split()
        word_count = len(words)

        # Rough sentence count (periods, exclamation marks, question marks)
        import re
        sentences = re.split(r'[.!?]+', text)
        sentence_count = len([s for s in sentences if s.strip()])

        # Paragraph count (double newlines)
        paragraphs = [p for p in text.split('\n\n') if p.strip()]
        paragraph_count = len(paragraphs)

        # Average sentence length
        avg_sentence_length = word_count / sentence_count if sentence_count > 0 else 0

        return {
            "word_count": word_count,
            "sentence_count": sentence_count,
            "avg_sentence_length": round(avg_sentence_length, 1),
            "paragraph_count": paragraph_count
        }


class StyleAnalyzerServiceFactory:
    """Factory for creating StyleAnalyzerService instances"""

    @staticmethod
    def create_service(config: Optional[StyleAnalysisConfig] = None) -> StyleAnalyzerService:
        """
        Create a StyleAnalyzerService with specified configuration

        Args:
            config: Optional StyleAnalysisConfig (defaults to default config)

        Returns:
            Configured StyleAnalyzerService instance
        """
        return StyleAnalyzerService(config=config)
