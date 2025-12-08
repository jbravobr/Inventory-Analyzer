"""Modelos para resultados de extração e validação."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional


class ValidationStatus(Enum):
    """Status da validação do texto extraído."""
    
    VALID = "valid"
    PARTIAL = "partial"
    INVALID = "invalid"
    ERROR = "error"


@dataclass
class ValidationMetrics:
    """Métricas de validação do texto."""
    
    word_count: int = 0
    sentence_count: int = 0
    avg_word_length: float = 0.0
    coherence_score: float = 0.0
    language_confidence: float = 0.0
    encoding_valid: bool = True
    detected_language: str = ""
    
    @property
    def is_acceptable(self) -> bool:
        """Verifica se as métricas são aceitáveis."""
        return (
            self.word_count >= 10 and
            self.coherence_score >= 0.5 and
            self.encoding_valid
        )


@dataclass
class ValidationResult:
    """Resultado da validação do texto extraído."""
    
    status: ValidationStatus = ValidationStatus.VALID
    metrics: ValidationMetrics = field(default_factory=ValidationMetrics)
    issues: List[str] = field(default_factory=list)
    suggestions: List[str] = field(default_factory=list)
    
    @property
    def is_valid(self) -> bool:
        """Verifica se a validação passou."""
        return self.status == ValidationStatus.VALID
    
    @property
    def is_partial(self) -> bool:
        """Verifica se a validação é parcial."""
        return self.status == ValidationStatus.PARTIAL
    
    def add_issue(self, issue: str) -> None:
        """Adiciona um problema encontrado."""
        self.issues.append(issue)
    
    def add_suggestion(self, suggestion: str) -> None:
        """Adiciona uma sugestão."""
        self.suggestions.append(suggestion)
    
    def to_dict(self) -> dict:
        """Converte para dicionário."""
        return {
            "status": self.status.value,
            "is_valid": self.is_valid,
            "metrics": {
                "word_count": self.metrics.word_count,
                "sentence_count": self.metrics.sentence_count,
                "avg_word_length": self.metrics.avg_word_length,
                "coherence_score": self.metrics.coherence_score,
                "language_confidence": self.metrics.language_confidence,
                "encoding_valid": self.metrics.encoding_valid,
                "detected_language": self.metrics.detected_language,
            },
            "issues": self.issues,
            "suggestions": self.suggestions,
        }


@dataclass
class ExtractionResult:
    """Resultado completo da extração de texto."""
    
    success: bool = False
    text: str = ""
    page_count: int = 0
    validation: Optional[ValidationResult] = None
    processing_time: float = 0.0
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    
    def add_error(self, error: str) -> None:
        """Adiciona um erro."""
        self.errors.append(error)
        self.success = False
    
    def add_warning(self, warning: str) -> None:
        """Adiciona um aviso."""
        self.warnings.append(warning)
    
    def to_dict(self) -> dict:
        """Converte para dicionário."""
        return {
            "success": self.success,
            "page_count": self.page_count,
            "text_length": len(self.text),
            "processing_time": self.processing_time,
            "validation": self.validation.to_dict() if self.validation else None,
            "errors": self.errors,
            "warnings": self.warnings,
        }
