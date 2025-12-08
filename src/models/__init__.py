"""Modelos de dados do aplicativo."""

from .document import Document, Page, PageImage
from .extraction_result import ExtractionResult, ValidationResult
from .search_result import SearchResult, SearchMatch, InstructionMatch

__all__ = [
    "Document",
    "Page",
    "PageImage",
    "ExtractionResult",
    "ValidationResult",
    "SearchResult",
    "SearchMatch",
    "InstructionMatch",
]
