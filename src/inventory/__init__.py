"""
Módulo de análise de inventário.

Especializado em extrair informações de Escrituras Públicas de Inventário.
"""

from .analyzer import InventoryAnalyzer
from .report_generator import ReportGenerator
from .pdf_highlighter import PDFHighlighter

__all__ = [
    "InventoryAnalyzer",
    "ReportGenerator", 
    "PDFHighlighter"
]

