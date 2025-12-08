"""Módulo para validação da qualidade do texto extraído."""

from __future__ import annotations

import logging
import re
import unicodedata
from collections import Counter
from typing import List, Optional, Tuple

from ..config.settings import Settings, get_settings
from ..models.document import Document
from ..models.extraction_result import (
    ValidationResult,
    ValidationMetrics,
    ValidationStatus,
)

logger = logging.getLogger(__name__)


class TextValidator:
    """Validador de qualidade do texto extraído por OCR."""
    
    # Palavras comuns em português para validação
    COMMON_PORTUGUESE_WORDS = {
        "de", "da", "do", "e", "que", "o", "a", "os", "as", "em", "um", "uma",
        "para", "com", "não", "se", "na", "no", "por", "mais", "foi", "são",
        "como", "mas", "ao", "ser", "seu", "sua", "ou", "quando", "muito",
        "nos", "já", "também", "só", "pelo", "pela", "até", "isso", "ela",
        "entre", "depois", "sem", "mesmo", "aos", "seus", "ter", "suas",
        "contrato", "locação", "imóvel", "locador", "locatário", "aluguel",
        "prazo", "valor", "cláusula", "parágrafo", "artigo", "lei"
    }
    
    # Padrões que indicam problemas de OCR
    OCR_ERROR_PATTERNS = [
        r"[^\w\s.,;:!?()[\]{}\-\"\'@#$%&*+=/<>\\|~`^]{3,}",  # Sequência de caracteres estranhos
        r"\b[bcdfghjklmnpqrstvwxz]{5,}\b",  # Consoantes consecutivas
        r"\b[aeiou]{5,}\b",  # Vogais consecutivas
        r"(.)\1{4,}",  # Caractere repetido 5+ vezes
    ]
    
    def __init__(self, settings: Optional[Settings] = None):
        """
        Inicializa o validador.
        
        Args:
            settings: Configurações do aplicativo.
        """
        self.settings = settings or get_settings()
        self._compiled_patterns = [
            re.compile(p, re.IGNORECASE) for p in self.OCR_ERROR_PATTERNS
        ]
    
    def validate(self, document: Document) -> ValidationResult:
        """
        Valida o texto extraído do documento.
        
        Args:
            document: Documento com texto extraído.
        
        Returns:
            ValidationResult: Resultado da validação.
        """
        result = ValidationResult()
        text = document.full_text
        
        if not text or not text.strip():
            result.status = ValidationStatus.INVALID
            result.add_issue("Nenhum texto extraído do documento")
            return result
        
        logger.info("Iniciando validação do texto extraído")
        
        # Calcula métricas
        metrics = self._calculate_metrics(text)
        result.metrics = metrics
        
        # Verifica encoding
        encoding_valid, encoding_issues = self._check_encoding(text)
        if not encoding_valid:
            result.add_issue(f"Problemas de encoding: {', '.join(encoding_issues)}")
            metrics.encoding_valid = False
        
        # Verifica coerência
        coherence_score = self._calculate_coherence(text)
        metrics.coherence_score = coherence_score
        
        # Detecta idioma
        language, confidence = self._detect_language(text)
        metrics.detected_language = language
        metrics.language_confidence = confidence
        
        # Verifica padrões de erro OCR
        ocr_errors = self._detect_ocr_errors(text)
        for error in ocr_errors:
            result.add_issue(f"Possível erro de OCR: {error}")
        
        # Determina status final
        result.status = self._determine_status(metrics, len(ocr_errors))
        
        # Adiciona sugestões
        self._add_suggestions(result)
        
        logger.info(f"Validação concluída: {result.status.value}")
        
        return result
    
    def _calculate_metrics(self, text: str) -> ValidationMetrics:
        """
        Calcula métricas do texto.
        
        Args:
            text: Texto para análise.
        
        Returns:
            ValidationMetrics: Métricas calculadas.
        """
        metrics = ValidationMetrics()
        
        # Contagem de palavras
        words = text.split()
        metrics.word_count = len(words)
        
        # Contagem de sentenças
        sentences = re.split(r'[.!?]+', text)
        sentences = [s.strip() for s in sentences if s.strip()]
        metrics.sentence_count = len(sentences)
        
        # Tamanho médio das palavras
        if words:
            word_lengths = [len(w) for w in words if w.isalpha()]
            metrics.avg_word_length = (
                sum(word_lengths) / len(word_lengths) if word_lengths else 0
            )
        
        return metrics
    
    def _check_encoding(self, text: str) -> Tuple[bool, List[str]]:
        """
        Verifica problemas de encoding no texto.
        
        Args:
            text: Texto para verificação.
        
        Returns:
            Tuple[bool, List[str]]: (é válido, lista de problemas)
        """
        issues = []
        
        # Verifica caracteres de substituição Unicode
        if "\ufffd" in text:
            issues.append("Caracteres de substituição Unicode encontrados")
        
        # Verifica caracteres de controle inválidos
        control_chars = sum(1 for c in text if unicodedata.category(c) == 'Cc' and c not in '\n\r\t')
        if control_chars > 0:
            issues.append(f"{control_chars} caracteres de controle encontrados")
        
        # Verifica proporção de caracteres não-ASCII suspeitos
        non_ascii = sum(1 for c in text if ord(c) > 127)
        if len(text) > 0 and non_ascii / len(text) > 0.3:
            issues.append("Alta proporção de caracteres não-ASCII")
        
        return len(issues) == 0, issues
    
    def _calculate_coherence(self, text: str) -> float:
        """
        Calcula score de coerência do texto.
        
        Usa análise de frequência de palavras comuns em português
        para determinar se o texto faz sentido.
        
        Args:
            text: Texto para análise.
        
        Returns:
            float: Score de coerência (0-1).
        """
        words = text.lower().split()
        
        if len(words) < 10:
            return 0.0
        
        # Conta palavras comuns
        word_set = set(words)
        common_count = len(word_set.intersection(self.COMMON_PORTUGUESE_WORDS))
        
        # Calcula proporção de palavras válidas (alfabéticas)
        alpha_words = [w for w in words if w.isalpha()]
        alpha_ratio = len(alpha_words) / len(words) if words else 0
        
        # Calcula score baseado em palavras comuns e alfabéticas
        common_ratio = common_count / len(self.COMMON_PORTUGUESE_WORDS)
        
        # Combina scores
        coherence = (common_ratio * 0.4 + alpha_ratio * 0.6)
        
        return min(coherence, 1.0)
    
    def _detect_language(self, text: str) -> Tuple[str, float]:
        """
        Detecta o idioma do texto.
        
        Usa análise de frequência de palavras para detecção simples.
        
        Args:
            text: Texto para análise.
        
        Returns:
            Tuple[str, float]: (código do idioma, confiança)
        """
        words = set(text.lower().split())
        
        # Palavras exclusivas do português
        portuguese_markers = {
            "não", "são", "você", "está", "também", "já", "há",
            "então", "porém", "através", "após", "além", "até"
        }
        
        # Conta marcadores encontrados
        found_markers = len(words.intersection(portuguese_markers))
        found_common = len(words.intersection(self.COMMON_PORTUGUESE_WORDS))
        
        # Calcula confiança
        total_indicators = found_markers * 2 + found_common
        confidence = min(total_indicators / 30, 1.0)
        
        if confidence > 0.3:
            return "pt", confidence
        
        return "unknown", 0.0
    
    def _detect_ocr_errors(self, text: str) -> List[str]:
        """
        Detecta possíveis erros de OCR no texto.
        
        Args:
            text: Texto para análise.
        
        Returns:
            List[str]: Lista de erros encontrados.
        """
        errors = []
        
        for pattern in self._compiled_patterns:
            matches = pattern.findall(text)
            for match in matches[:3]:  # Limita a 3 por padrão
                if isinstance(match, tuple):
                    match = match[0]
                if len(match) > 1:
                    errors.append(f"Padrão suspeito: '{match[:20]}...'")
        
        return errors[:10]  # Limita total de erros
    
    def _determine_status(
        self,
        metrics: ValidationMetrics,
        error_count: int
    ) -> ValidationStatus:
        """
        Determina o status final da validação.
        
        Args:
            metrics: Métricas calculadas.
            error_count: Número de erros de OCR.
        
        Returns:
            ValidationStatus: Status final.
        """
        min_words = self.settings.validation.min_word_count
        min_coherence = self.settings.validation.min_sentence_coherence
        
        # Critérios de validação
        has_enough_words = metrics.word_count >= min_words
        has_coherence = metrics.coherence_score >= min_coherence
        has_valid_encoding = metrics.encoding_valid
        has_few_errors = error_count < 5
        
        if has_enough_words and has_coherence and has_valid_encoding and has_few_errors:
            return ValidationStatus.VALID
        elif has_enough_words and (has_coherence or has_valid_encoding):
            return ValidationStatus.PARTIAL
        else:
            return ValidationStatus.INVALID
    
    def _add_suggestions(self, result: ValidationResult) -> None:
        """
        Adiciona sugestões baseadas nos problemas encontrados.
        
        Args:
            result: Resultado da validação.
        """
        metrics = result.metrics
        
        if metrics.word_count < self.settings.validation.min_word_count:
            result.add_suggestion(
                "Considere aumentar a resolução do PDF ou verificar se é um PDF digitalizado"
            )
        
        if metrics.coherence_score < 0.5:
            result.add_suggestion(
                "O texto pode estar corrompido. Tente processar com outro idioma no Tesseract"
            )
        
        if not metrics.encoding_valid:
            result.add_suggestion(
                "Verifique se o PDF foi criado corretamente ou tente reconverter"
            )
        
        if result.status == ValidationStatus.PARTIAL:
            result.add_suggestion(
                "A extração foi parcial. Revise manualmente os trechos importantes"
            )
