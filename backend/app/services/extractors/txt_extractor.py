"""
TXT Text Extractor

Extracts text from plain text files with automatic encoding detection.
Handles various text encodings (UTF-8, Latin-1, ASCII, etc.) gracefully.
"""

import logging
from typing import Tuple, Optional
import chardet

from ..document_processor import TextExtractor

logger = logging.getLogger(__name__)


class TXTExtractor(TextExtractor):
    """
    Extracts text content from plain text files

    Features:
    - Automatic encoding detection
    - Support for UTF-8, Latin-1, ASCII, and other common encodings
    - Graceful fallback handling
    - Line ending normalization
    """

    def __init__(self, preferred_encoding: str = 'utf-8'):
        """
        Initialize TXT extractor

        Args:
            preferred_encoding: Encoding to try first (default: utf-8)
        """
        self.preferred_encoding = preferred_encoding

    def extract(self, content: bytes, filename: str) -> str:
        """
        Extract text from plain text file

        Args:
            content: Raw text file bytes
            filename: Original filename (for error messages)

        Returns:
            Extracted text as string

        Raises:
            ValueError: If file cannot be decoded or is empty
        """
        try:
            logger.debug(f"Processing text file: {filename}")

            if not content:
                raise ValueError(f"Text file '{filename}' is empty")

            # Try preferred encoding first (usually UTF-8)
            text = None
            encoding_used = None

            try:
                text = content.decode(self.preferred_encoding)
                encoding_used = self.preferred_encoding
                logger.debug(f"Decoded {filename} using {self.preferred_encoding}")
            except (UnicodeDecodeError, LookupError):
                # Preferred encoding failed, try auto-detection
                logger.debug(
                    f"{self.preferred_encoding} failed for {filename}, "
                    "attempting encoding detection"
                )
                text, encoding_used = self._detect_and_decode(content, filename)

            if not text:
                raise ValueError(
                    f"Could not decode text file '{filename}' with any supported encoding"
                )

            # Normalize line endings (convert CRLF to LF)
            text = text.replace('\r\n', '\n').replace('\r', '\n')

            # Strip leading/trailing whitespace but preserve internal structure
            text = text.strip()

            if not text:
                raise ValueError(
                    f"Text file '{filename}' contains no readable content after decoding"
                )

            logger.info(
                f"Successfully extracted {len(text)} characters from {filename} "
                f"using {encoding_used} encoding"
            )

            return text

        except Exception as e:
            if isinstance(e, ValueError):
                raise  # Re-raise our custom errors
            logger.error(f"Unexpected error extracting text from {filename}: {str(e)}")
            raise ValueError(
                f"Failed to extract text from '{filename}': {str(e)}"
            )

    def _detect_and_decode(self, content: bytes, filename: str) -> Tuple[str, str]:
        """
        Detect encoding and decode content

        Args:
            content: Raw file bytes
            filename: Filename for logging

        Returns:
            Tuple of (decoded_text, encoding_used)

        Raises:
            ValueError: If no encoding works
        """
        # Use chardet for automatic encoding detection
        detection = chardet.detect(content)
        detected_encoding = detection.get('encoding')
        confidence = detection.get('confidence', 0)

        logger.debug(
            f"Detected encoding for {filename}: {detected_encoding} "
            f"(confidence: {confidence:.2%})"
        )

        # Try detected encoding if confidence is reasonable
        if detected_encoding and confidence > 0.5:
            try:
                text = content.decode(detected_encoding)
                return text, detected_encoding
            except (UnicodeDecodeError, LookupError) as e:
                logger.warning(
                    f"Failed to decode {filename} with detected encoding "
                    f"{detected_encoding}: {str(e)}"
                )

        # Fallback: try common encodings
        fallback_encodings = [
            'utf-8',
            'latin-1',  # ISO-8859-1
            'windows-1252',  # CP1252
            'ascii',
            'utf-16',
            'utf-16le',
            'utf-16be',
        ]

        for encoding in fallback_encodings:
            if encoding == self.preferred_encoding:
                continue  # Already tried this

            try:
                text = content.decode(encoding)
                logger.info(
                    f"Successfully decoded {filename} using fallback encoding: {encoding}"
                )
                return text, encoding
            except (UnicodeDecodeError, LookupError):
                continue

        # Last resort: decode with errors='replace' to get something
        text = content.decode('utf-8', errors='replace')
        logger.warning(
            f"Used UTF-8 with error replacement for {filename}. "
            "Some characters may be lost or corrupted."
        )
        return text, 'utf-8 (with errors)'

    def validate(self, content: bytes) -> Tuple[bool, Optional[str]]:
        """
        Validate that content is readable text

        Args:
            content: Raw file bytes

        Returns:
            Tuple of (is_valid, error_message)
        """
        try:
            if not content:
                return False, "File is empty"

            # Try to decode with preferred encoding
            try:
                _ = content.decode(self.preferred_encoding)
                return True, None
            except (UnicodeDecodeError, LookupError):
                pass

            # Try encoding detection
            detection = chardet.detect(content)
            detected_encoding = detection.get('encoding')
            confidence = detection.get('confidence', 0)

            if not detected_encoding:
                return False, "Could not detect text encoding"

            if confidence < 0.5:
                return False, f"Low confidence in detected encoding ({confidence:.2%})"

            # Try to decode with detected encoding
            try:
                _ = content.decode(detected_encoding)
                return True, None
            except (UnicodeDecodeError, LookupError) as e:
                return False, f"Failed to decode with detected encoding: {str(e)}"

        except Exception as e:
            return False, f"Text validation failed: {str(e)}"

    def get_encoding_info(self, content: bytes) -> dict:
        """
        Get encoding information about the text file (optional helper method)

        Args:
            content: Raw text file bytes

        Returns:
            Dictionary with encoding information
        """
        try:
            detection = chardet.detect(content)

            info = {
                'detected_encoding': detection.get('encoding', 'unknown'),
                'confidence': detection.get('confidence', 0),
                'language': detection.get('language', 'unknown'),
                'byte_size': len(content),
            }

            # Try to get character count with detected encoding
            try:
                if detection.get('encoding'):
                    text = content.decode(detection['encoding'])
                    info['char_count'] = len(text)
                    info['line_count'] = len(text.splitlines())
            except Exception:
                pass

            return info

        except Exception as e:
            logger.warning(f"Failed to get encoding info: {str(e)}")
            return {'error': str(e)}
