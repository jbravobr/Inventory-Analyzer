"""
Módulo de análise de documentos.

Especializado em extrair informações de:
- Escrituras Públicas de Inventário
- Atas de Reunião de Quotistas
"""

from .analyzer import InventoryAnalyzer
from .meeting_minutes_analyzer import MeetingMinutesAnalyzer
from .report_generator import ReportGenerator
from .meeting_minutes_report import MeetingMinutesReportGenerator
from .pdf_highlighter import PDFHighlighter
from .meeting_minutes_highlighter import MeetingMinutesPDFHighlighter

__all__ = [
    "InventoryAnalyzer",
    "MeetingMinutesAnalyzer",
    "ReportGenerator",
    "MeetingMinutesReportGenerator",
    "PDFHighlighter",
    "MeetingMinutesPDFHighlighter"
]

