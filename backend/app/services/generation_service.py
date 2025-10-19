"""
Generation service for Claude API integration

This module provides the GenerationService class for generating
grant writing content using Anthropic's Claude API with:
- Audience-aware prompt templates
- Streaming and non-streaming responses
- Citation tracking and inline citations
- Quality validation
- Error handling and retries
"""

import logging
import time
from typing import List, Optional, Dict, Any, AsyncIterator
from dataclasses import dataclass

from anthropic import Anthropic, AsyncAnthropic
from anthropic.types import MessageStreamEvent

from ..config import settings
from ..models.query import Source

logger = logging.getLogger(__name__)


@dataclass
class GenerationConfig:
    """Configuration for content generation"""
    model: str = settings.claude_model
    temperature: float = settings.claude_temperature
    max_tokens: int = settings.claude_max_tokens
    timeout: int = settings.claude_timeout_seconds
    max_retries: int = settings.claude_max_retries
    retry_delay: int = settings.claude_retry_delay_seconds


class GenerationService:
    """
    Service for generating content using Claude API

    Handles both streaming and non-streaming generation with
    audience-aware prompts, citation tracking, and quality validation.
    """

    def __init__(self, config: Optional[GenerationConfig] = None):
        """
        Initialize generation service

        Args:
            config: Optional configuration (defaults to settings)
        """
        self.config = config or GenerationConfig()

        # Initialize Anthropic clients
        self.client = Anthropic(api_key=settings.anthropic_api_key)
        self.async_client = AsyncAnthropic(api_key=settings.anthropic_api_key)

        logger.info(f"Initialized GenerationService with model: {self.config.model}")

    def _build_system_prompt(
        self,
        audience: str,
        section: str,
        tone: str
    ) -> str:
        """
        Build system prompt for audience-specific generation

        Args:
            audience: Target audience (Federal RFP, Foundation Grant, etc.)
            section: Document section (Organizational Capacity, etc.)
            tone: Desired tone (Professional, Conversational, etc.)

        Returns:
            System prompt string
        """
        prompt = f"""You are an expert grant writer and nonprofit communications specialist. Your task is to help nonprofits create compelling, accurate content for grant applications and fundraising materials.

Target Audience: {audience}
Document Section: {section}
Writing Tone: {tone}

Key Guidelines:
1. Write in a {tone.lower()} tone appropriate for {audience} audience
2. Use clear, concise language focused on impact and outcomes
3. Support claims with specific data and examples from the provided sources
4. Include inline citations [1], [2], etc. when referencing source material
5. Follow grant writing best practices for {section} sections
6. Avoid jargon unless appropriate for the {audience} audience
7. Focus on demonstrating organizational capacity, program impact, and sustainability
8. Be specific and concrete rather than vague or generic
9. Highlight measurable outcomes and evidence-based approaches
10. Maintain consistency with the organization's documented history and capabilities

Remember: The content must be grounded in the provided source documents. Do not make up information or claim capabilities not supported by the sources."""

        return prompt

    def _build_user_prompt(
        self,
        query: str,
        sources: List[Source],
        include_citations: bool = True,
        custom_instructions: Optional[str] = None
    ) -> str:
        """
        Build user prompt with context from retrieved sources

        Args:
            query: User's content generation request
            sources: Retrieved source documents
            include_citations: Whether to include inline citations
            custom_instructions: Additional custom instructions

        Returns:
            User prompt string with context
        """
        # Build context from sources
        context_parts = []
        for source in sources:
            context_parts.append(
                f"[{source.id}] {source.filename} ({source.doc_type}, {source.year}):\n{source.excerpt}\n"
            )

        context = "\n\n".join(context_parts)

        # Build the full prompt
        prompt = f"""Based on the following source documents from our organization's history, please generate content for:

REQUEST: {query}

SOURCE DOCUMENTS:
{context}

"""

        if include_citations:
            prompt += "Please include inline citations [1], [2], etc. when referencing specific information from the sources.\n\n"

        if custom_instructions:
            prompt += f"ADDITIONAL INSTRUCTIONS:\n{custom_instructions}\n\n"

        prompt += "Generated content:"

        return prompt

    async def generate(
        self,
        query: str,
        sources: List[Source],
        audience: str,
        section: str,
        tone: str = "Professional",
        include_citations: bool = True,
        custom_instructions: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Generate content using Claude API (non-streaming)

        Args:
            query: User's content generation request
            sources: Retrieved source documents
            audience: Target audience
            section: Document section
            tone: Writing tone
            include_citations: Include inline citations
            custom_instructions: Additional instructions
            temperature: Override default temperature
            max_tokens: Override default max tokens

        Returns:
            Dictionary with:
                - text: Generated content
                - model: Model name
                - tokens_used: Token count
                - generation_time: Time in seconds
                - stop_reason: Why generation stopped
        """
        logger.info(f"Generating content for query: {query[:100]}...")

        start_time = time.time()

        try:
            # Build prompts
            system_prompt = self._build_system_prompt(audience, section, tone)
            user_prompt = self._build_user_prompt(
                query, sources, include_citations, custom_instructions
            )

            # Generate using Claude API
            response = await self.async_client.messages.create(
                model=temperature or self.config.model,
                max_tokens=max_tokens or self.config.max_tokens,
                temperature=temperature if temperature is not None else self.config.temperature,
                system=system_prompt,
                messages=[
                    {"role": "user", "content": user_prompt}
                ],
                timeout=self.config.timeout
            )

            generation_time = time.time() - start_time

            # Extract text from response
            text = response.content[0].text if response.content else ""

            logger.info(
                f"Generation complete in {generation_time:.2f}s, "
                f"{response.usage.input_tokens + response.usage.output_tokens} tokens used"
            )

            return {
                "text": text,
                "model": response.model,
                "tokens_used": response.usage.input_tokens + response.usage.output_tokens,
                "input_tokens": response.usage.input_tokens,
                "output_tokens": response.usage.output_tokens,
                "generation_time": generation_time,
                "stop_reason": response.stop_reason
            }

        except Exception as e:
            logger.error(f"Generation failed: {e}", exc_info=True)
            raise

    async def generate_stream(
        self,
        query: str,
        sources: List[Source],
        audience: str,
        section: str,
        tone: str = "Professional",
        include_citations: bool = True,
        custom_instructions: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None
    ) -> AsyncIterator[MessageStreamEvent]:
        """
        Generate content using Claude API with streaming

        Args:
            query: User's content generation request
            sources: Retrieved source documents
            audience: Target audience
            section: Document section
            tone: Writing tone
            include_citations: Include inline citations
            custom_instructions: Additional instructions
            temperature: Override default temperature
            max_tokens: Override default max tokens

        Yields:
            MessageStreamEvent objects from Claude API
        """
        logger.info(f"Starting streaming generation for query: {query[:100]}...")

        try:
            # Build prompts
            system_prompt = self._build_system_prompt(audience, section, tone)
            user_prompt = self._build_user_prompt(
                query, sources, include_citations, custom_instructions
            )

            # Stream using Claude API
            async with self.async_client.messages.stream(
                model=self.config.model,
                max_tokens=max_tokens or self.config.max_tokens,
                temperature=temperature if temperature is not None else self.config.temperature,
                system=system_prompt,
                messages=[
                    {"role": "user", "content": user_prompt}
                ],
                timeout=self.config.timeout
            ) as stream:
                async for event in stream:
                    yield event

            logger.info("Streaming generation complete")

        except Exception as e:
            logger.error(f"Streaming generation failed: {e}", exc_info=True)
            raise

    def extract_citations(self, text: str) -> List[int]:
        """
        Extract citation numbers from generated text

        Args:
            text: Generated text with inline citations [1], [2], etc.

        Returns:
            List of unique citation numbers found in text
        """
        import re

        # Find all citation patterns [1], [2], etc.
        citations = re.findall(r'\[(\d+)\]', text)

        # Convert to integers and get unique values
        citation_numbers = sorted(set(int(c) for c in citations))

        return citation_numbers

    def validate_citations(
        self,
        text: str,
        sources: List[Source]
    ) -> Dict[str, Any]:
        """
        Validate that citations in text match available sources

        Args:
            text: Generated text with citations
            sources: Available source documents

        Returns:
            Dictionary with:
                - valid: Whether all citations are valid
                - cited_sources: List of source IDs that were cited
                - uncited_sources: List of source IDs that were not cited
                - invalid_citations: List of citation numbers with no matching source
        """
        citation_numbers = self.extract_citations(text)
        source_ids = {s.id for s in sources}

        valid_citations = [c for c in citation_numbers if c in source_ids]
        invalid_citations = [c for c in citation_numbers if c not in source_ids]

        cited_sources = valid_citations
        uncited_sources = list(source_ids - set(cited_sources))

        return {
            "valid": len(invalid_citations) == 0,
            "cited_sources": cited_sources,
            "uncited_sources": uncited_sources,
            "invalid_citations": invalid_citations,
            "total_citations": len(citation_numbers)
        }


class GenerationServiceFactory:
    """Factory for creating GenerationService instances"""

    @staticmethod
    def create_service(config: Optional[GenerationConfig] = None) -> GenerationService:
        """
        Create a GenerationService with specified configuration

        Args:
            config: Optional GenerationConfig (defaults to settings)

        Returns:
            Configured GenerationService instance
        """
        return GenerationService(config=config)
