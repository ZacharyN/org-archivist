"""
DOCX Text Extractor (Stub)

Will be implemented in the next task.
"""

from typing import Tuple, Optional
from ..document_processor import TextExtractor


class DOCXExtractor(TextExtractor):
    """Stub for DOCX extractor - to be implemented"""

    def extract(self, content: bytes, filename: str) -> str:
        raise NotImplementedError("DOCX extraction not yet implemented")

    def validate(self, content: bytes) -> Tuple[bool, Optional[str]]:
        return False, "DOCX extraction not yet implemented"
