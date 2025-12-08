"""Modelos de dados para documentos PDF."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional

import numpy as np


@dataclass
class PageImage:
    """Representa a imagem de uma página do PDF."""
    
    page_number: int
    image: np.ndarray
    width: int
    height: int
    dpi: int = 300
    
    @property
    def shape(self) -> tuple:
        """Retorna as dimensões da imagem."""
        return self.image.shape


@dataclass
class Page:
    """Representa uma página do documento."""
    
    number: int
    text: str = ""
    image: Optional[PageImage] = None
    word_count: int = 0
    confidence: float = 0.0
    
    def __post_init__(self):
        """Calcula contagem de palavras após inicialização."""
        if self.text and self.word_count == 0:
            self.word_count = len(self.text.split())


@dataclass
class Document:
    """Representa um documento PDF processado."""
    
    source_path: Path
    pages: List[Page] = field(default_factory=list)
    total_pages: int = 0
    metadata: dict = field(default_factory=dict)
    
    def __post_init__(self):
        """Inicializa o documento."""
        if isinstance(self.source_path, str):
            self.source_path = Path(self.source_path)
    
    @property
    def full_text(self) -> str:
        """Retorna o texto completo do documento."""
        return "\n\n".join(page.text for page in self.pages if page.text)
    
    @property
    def total_words(self) -> int:
        """Retorna o total de palavras no documento."""
        return sum(page.word_count for page in self.pages)
    
    @property
    def average_confidence(self) -> float:
        """Retorna a confiança média do OCR."""
        if not self.pages:
            return 0.0
        confidences = [p.confidence for p in self.pages if p.confidence > 0]
        return sum(confidences) / len(confidences) if confidences else 0.0
    
    def get_page(self, number: int) -> Optional[Page]:
        """Obtém uma página pelo número."""
        for page in self.pages:
            if page.number == number:
                return page
        return None
    
    def get_text_by_pages(self, page_numbers: List[int]) -> str:
        """Obtém texto de páginas específicas."""
        texts = []
        for num in page_numbers:
            page = self.get_page(num)
            if page and page.text:
                texts.append(page.text)
        return "\n\n".join(texts)
    
    def add_page(self, page: Page) -> None:
        """Adiciona uma página ao documento."""
        self.pages.append(page)
        self.total_pages = len(self.pages)
    
    def to_dict(self) -> dict:
        """Converte o documento para dicionário."""
        return {
            "source_path": str(self.source_path),
            "total_pages": self.total_pages,
            "total_words": self.total_words,
            "average_confidence": self.average_confidence,
            "metadata": self.metadata,
            "pages": [
                {
                    "number": p.number,
                    "word_count": p.word_count,
                    "confidence": p.confidence,
                    "text_preview": p.text[:200] + "..." if len(p.text) > 200 else p.text
                }
                for p in self.pages
            ]
        }
