"""
PDF Text Extractor

Extracts text from PDF files using PyPDF2 library.
Handles multi-page PDFs, preserves basic structure, and provides error handling
for corrupted or password-protected files.
"""

import io
import logging
from typing import Tuple, Optional

try:
    import PyPDF2
except ImportError:
    import pypdf as PyPDF2  # pypdf2 3.x renamed to pypdf

from ..document_processor import TextExtractor

logger = logging.getLogger(__name__)


class PDFExtractor(TextExtractor):
    """
    Extracts text content from PDF files

    Features:
    - Multi-page PDF support
    - Page separation with markers
    - Error handling for corrupted/encrypted PDFs
    - Structure preservation (paragraphs)
    """

    def __init__(self, page_separator: str = "\n\n--- Page Break ---\n\n"):
        """
        Initialize PDF extractor

        Args:
            page_separator: String to insert between pages (default: page break marker)
        """
        self.page_separator = page_separator

    def extract(self, content: bytes, filename: str) -> str:
        """
        Extract text from PDF file

        Args:
            content: Raw PDF file bytes
            filename: Original filename (for error messages)

        Returns:
            Extracted text with page separators

        Raises:
            ValueError: If PDF is encrypted, corrupted, or cannot be read
        """
        try:
            # Create PDF reader from bytes
            pdf_file = io.BytesIO(content)
            pdf_reader = PyPDF2.PdfReader(pdf_file)

            # Check if PDF is encrypted
            if pdf_reader.is_encrypted:
                # Try to decrypt with empty password
                try:
                    pdf_reader.decrypt('')
                except Exception:
                    raise ValueError(
                        f"PDF file '{filename}' is password-protected and cannot be read"
                    )

            # Get number of pages
            num_pages = len(pdf_reader.pages)
            logger.debug(f"Processing PDF with {num_pages} pages: {filename}")

            if num_pages == 0:
                raise ValueError(f"PDF file '{filename}' contains no pages")

            # Extract text from each page
            text_parts = []

            for page_num in range(num_pages):
                try:
                    page = pdf_reader.pages[page_num]
                    page_text = page.extract_text()

                    # Skip empty pages
                    if page_text and page_text.strip():
                        text_parts.append(page_text.strip())
                        logger.debug(
                            f"Extracted {len(page_text)} characters from page {page_num + 1}"
                        )
                except Exception as e:
                    logger.warning(
                        f"Failed to extract text from page {page_num + 1} of {filename}: {str(e)}"
                    )
                    # Continue with other pages even if one fails
                    continue

            if not text_parts:
                raise ValueError(
                    f"No text could be extracted from PDF '{filename}'. "
                    "File may be image-based or corrupted."
                )

            # Combine pages with separator
            full_text = self.page_separator.join(text_parts)

            logger.info(
                f"Successfully extracted {len(full_text)} characters "
                f"from {len(text_parts)} pages of {filename}"
            )

            return full_text

        except PyPDF2.errors.PdfReadError as e:
            raise ValueError(
                f"Failed to read PDF '{filename}': {str(e)}. File may be corrupted."
            )
        except Exception as e:
            if isinstance(e, ValueError):
                raise  # Re-raise our custom errors
            logger.error(f"Unexpected error extracting text from {filename}: {str(e)}")
            raise ValueError(
                f"Failed to extract text from PDF '{filename}': {str(e)}"
            )

    def validate(self, content: bytes) -> Tuple[bool, Optional[str]]:
        """
        Validate that content is a valid PDF file

        Args:
            content: Raw file bytes

        Returns:
            Tuple of (is_valid, error_message)
        """
        try:
            # Check file signature (PDF magic bytes)
            if not content.startswith(b'%PDF'):
                return False, "File does not appear to be a valid PDF (missing PDF header)"

            # Try to open with PyPDF2
            pdf_file = io.BytesIO(content)
            pdf_reader = PyPDF2.PdfReader(pdf_file)

            # Check if encrypted
            if pdf_reader.is_encrypted:
                # Try empty password
                try:
                    pdf_reader.decrypt('')
                except Exception:
                    return False, "PDF is password-protected"

            # Check if has pages
            num_pages = len(pdf_reader.pages)
            if num_pages == 0:
                return False, "PDF contains no pages"

            # Try to read first page (basic validation)
            try:
                first_page = pdf_reader.pages[0]
                _ = first_page.extract_text()
            except Exception as e:
                return False, f"Cannot read PDF content: {str(e)}"

            return True, None

        except PyPDF2.errors.PdfReadError as e:
            return False, f"Invalid or corrupted PDF: {str(e)}"
        except Exception as e:
            return False, f"PDF validation failed: {str(e)}"

    def get_metadata(self, content: bytes) -> dict:
        """
        Extract PDF metadata (optional helper method)

        Args:
            content: Raw PDF file bytes

        Returns:
            Dictionary with metadata (title, author, creation date, etc.)
        """
        try:
            pdf_file = io.BytesIO(content)
            pdf_reader = PyPDF2.PdfReader(pdf_file)

            metadata = {}

            # Get document info
            doc_info = pdf_reader.metadata
            if doc_info:
                metadata['title'] = doc_info.get('/Title', '')
                metadata['author'] = doc_info.get('/Author', '')
                metadata['subject'] = doc_info.get('/Subject', '')
                metadata['creator'] = doc_info.get('/Creator', '')
                metadata['producer'] = doc_info.get('/Producer', '')
                metadata['creation_date'] = doc_info.get('/CreationDate', '')
                metadata['modification_date'] = doc_info.get('/ModDate', '')

            # Add page count
            metadata['page_count'] = len(pdf_reader.pages)

            return metadata

        except Exception as e:
            logger.warning(f"Failed to extract PDF metadata: {str(e)}")
            return {}
