"""Modulos core do aplicativo."""

from .pdf_reader import PDFReader
from .ocr_extractor import OCRExtractor
from .text_validator import TextValidator
from .instruction_parser import InstructionParser
from .text_searcher import TextSearcher
from .output_generator import OutputGenerator
from .ocr_cache import (
    OCRCache,
    OCRCacheEntry,
    CachedDocument,
    get_ocr_cache,
    init_ocr_cache,
)

__all__ = [
    "PDFReader",
    "OCRExtractor",
    "TextValidator",
    "InstructionParser",
    "TextSearcher",
    "OutputGenerator",
    "OCRCache",
    "OCRCacheEntry",
    "CachedDocument",
    "get_ocr_cache",
    "init_ocr_cache",
]
