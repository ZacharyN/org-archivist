"""
Metadata Extractor Service

Extracts and enriches document metadata from multiple sources:
1. File properties (creation date, modification date, author)
2. Document structure (page count, word count, character count)
3. Filename patterns (parses structured filenames)
4. User-provided metadata (doc_type, year, programs, outcomes, tags)
5. File system metadata (file size, timestamps)

Provides validation and graceful handling of missing metadata.
"""

import re
import logging
from datetime import datetime
from typing import Dict, Optional, Tuple, List, Any
from pathlib import Path
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class ExtractedMetadata:
    """
    Comprehensive metadata extracted from a document
    """
    # User-provided metadata
    doc_type: str
    year: int
    programs: List[str] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)
    outcome: str = "N/A"
    notes: Optional[str] = None

    # File properties
    filename: str = ""
    file_size: Optional[int] = None
    created_date: Optional[datetime] = None
    modified_date: Optional[datetime] = None
    author: Optional[str] = None

    # Document structure
    page_count: Optional[int] = None
    word_count: Optional[int] = None
    char_count: Optional[int] = None
    paragraph_count: Optional[int] = None
    table_count: Optional[int] = None
    section_count: Optional[int] = None

    # Content metadata (PDF-specific)
    title: Optional[str] = None
    subject: Optional[str] = None
    creator: Optional[str] = None
    producer: Optional[str] = None
    creation_date: Optional[str] = None
    modification_date: Optional[str] = None

    # Processing metadata
    upload_date: datetime = field(default_factory=datetime.now)
    processed_date: Optional[datetime] = None
    doc_id: Optional[str] = None

    # Extracted from filename patterns
    parsed_from_filename: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict:
        """Convert to dictionary for storage"""
        return {
            # User-provided
            'doc_type': self.doc_type,
            'year': self.year,
            'programs': self.programs,
            'tags': self.tags,
            'outcome': self.outcome,
            'notes': self.notes,

            # File properties
            'filename': self.filename,
            'file_size': self.file_size,
            'created_date': self.created_date.isoformat() if self.created_date else None,
            'modified_date': self.modified_date.isoformat() if self.modified_date else None,
            'author': self.author,

            # Document structure
            'page_count': self.page_count,
            'word_count': self.word_count,
            'char_count': self.char_count,
            'paragraph_count': self.paragraph_count,
            'table_count': self.table_count,
            'section_count': self.section_count,

            # Content metadata
            'title': self.title,
            'subject': self.subject,
            'creator': self.creator,
            'producer': self.producer,
            'creation_date': self.creation_date,
            'modification_date': self.modification_date,

            # Processing metadata
            'upload_date': self.upload_date.isoformat() if self.upload_date else None,
            'processed_date': self.processed_date.isoformat() if self.processed_date else None,
            'doc_id': self.doc_id,

            # Parsed
            'parsed_from_filename': self.parsed_from_filename,
        }


class MetadataExtractor:
    """
    Extracts comprehensive metadata from documents

    Combines metadata from multiple sources:
    - User input (doc_type, year, programs, etc.)
    - File properties (size, dates)
    - Document content (via file-specific extractors)
    - Filename patterns (structured parsing)
    - Text analysis (word count, char count)

    Provides validation and graceful handling of missing metadata.
    """

    # Common filename patterns for grant writing documents
    FILENAME_PATTERNS = [
        # Pattern: "NCFF_GrantProposal_2024_DoED.pdf"
        r'(?P<org>[A-Z]+)_(?P<type>[A-Za-z]+)_(?P<year>\d{4})_(?P<funder>[A-Za-z]+)',

        # Pattern: "Annual Report 2024.pdf"
        r'(?P<type>[A-Za-z\s]+)\s+(?P<year>\d{4})',

        # Pattern: "2024_Program_Description_Early_Childhood.docx"
        r'(?P<year>\d{4})_(?P<type>[A-Za-z_]+)_(?P<program>[A-Za-z_]+)',

        # Pattern: "Grant_DoED_2024_Funded.pdf"
        r'(?P<type>[A-Za-z]+)_(?P<funder>[A-Za-z]+)_(?P<year>\d{4})_(?P<outcome>[A-Za-z]+)',
    ]

    def __init__(self):
        """Initialize metadata extractor"""
        logger.info("MetadataExtractor initialized")

    def extract(
        self,
        user_metadata: Dict,
        file_content: bytes,
        filename: str,
        text: str,
        file_extractor: Optional[Any] = None
    ) -> ExtractedMetadata:
        """
        Extract comprehensive metadata from all available sources

        Args:
            user_metadata: User-provided metadata (doc_type, year, programs, etc.)
            file_content: Raw file bytes (for file-specific extraction)
            filename: Original filename
            text: Extracted document text
            file_extractor: Optional file-specific extractor (PDFExtractor, DOCXExtractor, etc.)

        Returns:
            ExtractedMetadata object with all extracted metadata
        """
        logger.info(f"Extracting metadata for: {filename}")

        # Start with user-provided metadata
        metadata = ExtractedMetadata(
            doc_type=user_metadata.get('doc_type', 'Unknown'),
            year=user_metadata.get('year', datetime.now().year),
            programs=user_metadata.get('programs', []),
            tags=user_metadata.get('tags', []),
            outcome=user_metadata.get('outcome', 'N/A'),
            notes=user_metadata.get('notes'),
        )

        # Extract file properties
        metadata.filename = filename
        metadata.file_size = len(file_content)

        # Extract document structure from text
        metadata.char_count = len(text)
        metadata.word_count = len(text.split())

        # Extract from filename patterns
        parsed_filename = self._parse_filename(filename)
        if parsed_filename:
            metadata.parsed_from_filename = parsed_filename
            # Enhance metadata with parsed values if not already provided
            if 'year' in parsed_filename and not user_metadata.get('year'):
                try:
                    metadata.year = int(parsed_filename['year'])
                except (ValueError, TypeError):
                    pass

            if 'outcome' in parsed_filename and metadata.outcome == 'N/A':
                metadata.outcome = self._normalize_outcome(parsed_filename['outcome'])

        # Extract file-specific metadata (PDF, DOCX properties)
        if file_extractor and hasattr(file_extractor, 'get_metadata'):
            try:
                file_metadata = file_extractor.get_metadata(file_content)
                self._merge_file_metadata(metadata, file_metadata)
                logger.debug(f"Extracted file-specific metadata: {list(file_metadata.keys())}")
            except Exception as e:
                logger.warning(f"Failed to extract file-specific metadata: {str(e)}")

        # Add processing timestamps
        metadata.processed_date = datetime.now()

        # Generate doc_id if not provided
        if not metadata.doc_id:
            metadata.doc_id = self._generate_doc_id(filename)

        logger.info(
            f"Metadata extraction complete for {filename}: "
            f"{metadata.word_count} words, {metadata.char_count} chars, "
            f"year={metadata.year}, type={metadata.doc_type}"
        )

        return metadata

    def _parse_filename(self, filename: str) -> Dict[str, str]:
        """
        Parse filename for structured metadata

        Attempts to extract metadata from common filename patterns:
        - Organization name
        - Document type
        - Year
        - Funder/Program
        - Outcome status

        Args:
            filename: Original filename

        Returns:
            Dictionary of parsed values, empty if no pattern matched
        """
        # Remove extension
        name_without_ext = Path(filename).stem

        # Try each pattern
        for pattern in self.FILENAME_PATTERNS:
            match = re.search(pattern, name_without_ext, re.IGNORECASE)
            if match:
                parsed = match.groupdict()
                logger.debug(f"Parsed filename '{filename}' with pattern: {parsed}")
                return parsed

        logger.debug(f"No filename pattern matched for: {filename}")
        return {}

    def _normalize_outcome(self, outcome_str: str) -> str:
        """
        Normalize outcome string to standard values

        Args:
            outcome_str: Raw outcome string from filename

        Returns:
            Normalized outcome value
        """
        outcome_lower = outcome_str.lower()

        if outcome_lower in ['funded', 'approved', 'awarded']:
            return 'Funded'
        elif outcome_lower in ['denied', 'rejected', 'notfunded']:
            return 'Not Funded'
        elif outcome_lower in ['pending', 'submitted', 'inreview']:
            return 'Pending'
        elif outcome_lower in ['final', 'report', 'finalreport']:
            return 'Final Report'
        else:
            return 'N/A'

    def _merge_file_metadata(
        self,
        metadata: ExtractedMetadata,
        file_metadata: Dict
    ) -> None:
        """
        Merge file-specific metadata into ExtractedMetadata

        Handles both PDF and DOCX metadata formats

        Args:
            metadata: ExtractedMetadata object to update
            file_metadata: Dictionary of file-specific metadata
        """
        # PDF metadata
        if 'page_count' in file_metadata:
            metadata.page_count = file_metadata['page_count']

        if 'title' in file_metadata:
            metadata.title = file_metadata['title']

        if 'author' in file_metadata:
            metadata.author = file_metadata['author']

        if 'subject' in file_metadata:
            metadata.subject = file_metadata['subject']

        if 'creator' in file_metadata:
            metadata.creator = file_metadata['creator']

        if 'producer' in file_metadata:
            metadata.producer = file_metadata['producer']

        if 'creation_date' in file_metadata:
            metadata.creation_date = file_metadata['creation_date']

        if 'modification_date' in file_metadata:
            metadata.modification_date = file_metadata['modification_date']

        # DOCX metadata
        if 'paragraph_count' in file_metadata:
            metadata.paragraph_count = file_metadata['paragraph_count']

        if 'table_count' in file_metadata:
            metadata.table_count = file_metadata['table_count']

        if 'section_count' in file_metadata:
            metadata.section_count = file_metadata['section_count']

        if 'created' in file_metadata:
            metadata.created_date = self._parse_datetime(file_metadata['created'])

        if 'modified' in file_metadata:
            metadata.modified_date = self._parse_datetime(file_metadata['modified'])

    def _parse_datetime(self, date_str: str) -> Optional[datetime]:
        """
        Parse datetime string with error handling

        Args:
            date_str: Datetime string

        Returns:
            datetime object or None if parsing fails
        """
        if not date_str:
            return None

        try:
            return datetime.fromisoformat(date_str)
        except (ValueError, TypeError):
            logger.debug(f"Failed to parse datetime: {date_str}")
            return None

    def _generate_doc_id(self, filename: str) -> str:
        """
        Generate a unique document ID

        Uses timestamp + filename hash for uniqueness

        Args:
            filename: Original filename

        Returns:
            Unique document ID
        """
        import hashlib

        timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
        filename_hash = hashlib.md5(filename.encode()).hexdigest()[:8]
        doc_id = f"doc_{timestamp}_{filename_hash}"

        return doc_id

    def validate_metadata(
        self,
        metadata: ExtractedMetadata
    ) -> Tuple[bool, List[str]]:
        """
        Validate extracted metadata for completeness and correctness

        Args:
            metadata: ExtractedMetadata object to validate

        Returns:
            Tuple of (is_valid, list_of_warnings)
        """
        warnings = []

        # Check required fields
        if not metadata.doc_type or metadata.doc_type == 'Unknown':
            warnings.append("Document type is missing or unknown")

        if not metadata.year or metadata.year < 2000:
            warnings.append(f"Invalid year: {metadata.year}")

        if not metadata.filename:
            warnings.append("Filename is missing")

        # Check data quality
        if metadata.word_count and metadata.word_count < 10:
            warnings.append(f"Very low word count: {metadata.word_count}")

        if metadata.file_size and metadata.file_size < 100:
            warnings.append(f"Very small file size: {metadata.file_size} bytes")

        # Check consistency
        if metadata.page_count is not None and metadata.page_count == 0:
            warnings.append("Document has zero pages")

        is_valid = len(warnings) == 0

        if warnings:
            logger.warning(f"Metadata validation warnings for {metadata.filename}: {warnings}")

        return is_valid, warnings


class MetadataExtractorFactory:
    """
    Factory for creating MetadataExtractor instances
    """

    @staticmethod
    def create_extractor() -> MetadataExtractor:
        """
        Create a MetadataExtractor instance

        Returns:
            Configured MetadataExtractor
        """
        return MetadataExtractor()
