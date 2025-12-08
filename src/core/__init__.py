"""Módulos core do aplicativo."""

from .pdf_reader import PDFReader
from .ocr_extractor import OCRExtractor
from .text_validator import TextValidator
from .instruction_parser import InstructionParser
from .text_searcher import TextSearcher
from .output_generator import OutputGenerator

__all__ = [
    "PDFReader",
    "OCRExtractor",
    "TextValidator",
    "InstructionParser",
    "TextSearcher",
    "OutputGenerator",
]
