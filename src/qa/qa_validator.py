"""
Validador de Respostas do Q&A.

Verifica a qualidade das respostas geradas para evitar
alucinações e garantir que as respostas são baseadas
no contexto fornecido.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any, Tuple
from difflib import SequenceMatcher

logger = logging.getLogger(__name__)


@dataclass
class ValidationResult:
    """Resultado da validação de uma resposta."""
    
    is_valid: bool
    confidence: float
    issues: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    grounded_facts: List[str] = field(default_factory=list)
    potentially_hallucinated: List[str] = field(default_factory=list)
    
    def to_dict(self) -> dict:
        return {
            "is_valid": self.is_valid,
            "confidence": self.confidence,
            "issues": self.issues,
            "warnings": self.warnings,
            "grounded_facts": self.grounded_facts,
            "potentially_hallucinated": self.potentially_hallucinated,
        }
    
    def format_report(self) -> str:
        """Formata relatório de validação."""
        lines = [
            f"Validação: {'✓ VÁLIDA' if self.is_valid else '✗ INVÁLIDA'}",
            f"Confiança: {self.confidence:.0%}",
        ]
        
        if self.issues:
            lines.append("\nProblemas encontrados:")
            for issue in self.issues:
                lines.append(f"  ✗ {issue}")
        
        if self.warnings:
            lines.append("\nAvisos:")
            for warning in self.warnings:
                lines.append(f"  ⚠ {warning}")
        
        return "\n".join(lines)


class QAValidator:
    """
    Valida respostas do sistema de Q&A.
    
    Verifica:
    - Se a resposta está fundamentada no contexto
    - Se não há alucinações (informações inventadas)
    - Se a resposta é relevante para a pergunta
    - Se a resposta não está vazia ou genérica
    """
    
    # Frases que indicam resposta não encontrada (aceitáveis)
    NOT_FOUND_PHRASES = [
        "não foi encontrad",
        "não encontr",
        "não há informação",
        "não está no documento",
        "não está no contexto",
        "não menciona",
        "não consta",
        "não há menção",
        "informação não disponível",
        "não foi possível encontrar",
        "não foi possível identificar",
    ]
    
    # Frases genéricas que indicam resposta de baixa qualidade
    GENERIC_PHRASES = [
        "de acordo com o documento",
        "conforme mencionado",
        "como podemos ver",
        "é importante notar",
        "vale ressaltar",
        "em resumo",
        "basicamente",
        "de modo geral",
    ]
    
    def __init__(
        self,
        min_confidence: float = 0.5,
        strict_mode: bool = False
    ):
        """
        Inicializa o validador.
        
        Args:
            min_confidence: Confiança mínima para considerar válida
            strict_mode: Se True, aplica validações mais rigorosas
        """
        self.min_confidence = min_confidence
        self.strict_mode = strict_mode
    
    def validate(
        self,
        question: str,
        answer: str,
        context: str,
        pages: Optional[List[int]] = None
    ) -> ValidationResult:
        """
        Valida uma resposta do Q&A.
        
        Args:
            question: Pergunta original
            answer: Resposta gerada
            context: Contexto usado para gerar a resposta
            pages: Páginas referenciadas
        
        Returns:
            ValidationResult com detalhes da validação
        """
        issues = []
        warnings = []
        grounded = []
        hallucinated = []
        
        # 1. Verifica resposta vazia
        if not answer or len(answer.strip()) < 10:
            issues.append("Resposta vazia ou muito curta")
            return ValidationResult(
                is_valid=False,
                confidence=0.0,
                issues=issues,
            )
        
        # 2. Verifica se é resposta de "não encontrado" (aceita)
        if self._is_not_found_response(answer):
            return ValidationResult(
                is_valid=True,
                confidence=0.7,
                warnings=["Resposta indica que informação não foi encontrada"],
            )
        
        # 3. Verifica fundamentação no contexto
        grounding_score, grounded, hallucinated = self._check_grounding(
            answer, context
        )
        
        if grounding_score < 0.3:
            issues.append(
                "Resposta pode conter informações não presentes no contexto"
            )
        elif grounding_score < 0.5:
            warnings.append(
                "Algumas informações podem não estar completamente fundamentadas"
            )
        
        # 4. Verifica relevância para a pergunta
        relevance_score = self._check_relevance(question, answer)
        
        if relevance_score < 0.2:
            issues.append("Resposta não parece relevante para a pergunta")
        elif relevance_score < 0.4:
            warnings.append("Relevância da resposta pode ser baixa")
        
        # 5. Verifica frases genéricas
        generic_count = self._count_generic_phrases(answer)
        
        if generic_count > 3:
            warnings.append("Resposta contém muitas frases genéricas")
        
        # 6. Verifica citação de páginas
        if pages and len(pages) > 0:
            if not self._has_page_reference(answer, pages):
                warnings.append(
                    "Resposta não menciona as páginas de referência"
                )
        
        # 7. Calcula confiança final
        confidence = self._calculate_confidence(
            grounding_score,
            relevance_score,
            generic_count,
            len(issues),
            len(warnings)
        )
        
        # 8. Determina se é válida
        is_valid = len(issues) == 0 and confidence >= self.min_confidence
        
        # Em modo estrito, warnings também invalidam
        if self.strict_mode and len(warnings) > 2:
            is_valid = False
        
        return ValidationResult(
            is_valid=is_valid,
            confidence=confidence,
            issues=issues,
            warnings=warnings,
            grounded_facts=grounded,
            potentially_hallucinated=hallucinated,
        )
    
    def _is_not_found_response(self, answer: str) -> bool:
        """Verifica se a resposta indica que a informação não foi encontrada."""
        answer_lower = answer.lower()
        
        for phrase in self.NOT_FOUND_PHRASES:
            if phrase in answer_lower:
                return True
        
        return False
    
    def _check_grounding(
        self,
        answer: str,
        context: str
    ) -> Tuple[float, List[str], List[str]]:
        """
        Verifica se a resposta está fundamentada no contexto.
        
        Returns:
            Tuple de (score, fatos_fundamentados, possíveis_alucinações)
        """
        grounded = []
        hallucinated = []
        
        # Extrai frases/afirmações da resposta
        sentences = self._extract_sentences(answer)
        
        if not sentences:
            return 0.5, [], []
        
        context_lower = context.lower()
        grounding_scores = []
        
        for sentence in sentences:
            # Ignora frases muito curtas
            if len(sentence.split()) < 4:
                continue
            
            # Calcula similaridade com o contexto
            similarity = self._calculate_text_similarity(
                sentence.lower(),
                context_lower
            )
            
            grounding_scores.append(similarity)
            
            if similarity > 0.4:
                grounded.append(sentence)
            elif similarity < 0.2 and len(sentence.split()) > 6:
                # Verifica se contém dados específicos
                if self._contains_specific_data(sentence):
                    hallucinated.append(sentence)
        
        if not grounding_scores:
            return 0.5, grounded, hallucinated
        
        avg_score = sum(grounding_scores) / len(grounding_scores)
        
        return avg_score, grounded, hallucinated
    
    def _check_relevance(self, question: str, answer: str) -> float:
        """Verifica relevância da resposta para a pergunta."""
        # Extrai palavras-chave da pergunta
        question_keywords = self._extract_keywords(question)
        answer_lower = answer.lower()
        
        if not question_keywords:
            return 0.5
        
        # Conta quantas palavras-chave aparecem na resposta
        found = sum(1 for kw in question_keywords if kw in answer_lower)
        
        return found / len(question_keywords)
    
    def _extract_keywords(self, text: str) -> List[str]:
        """Extrai palavras-chave de um texto."""
        # Stopwords simples em português
        stopwords = {
            "o", "a", "os", "as", "um", "uma", "uns", "umas",
            "de", "da", "do", "das", "dos", "em", "no", "na",
            "nos", "nas", "por", "para", "com", "sem", "que",
            "qual", "quais", "onde", "como", "quando", "quem",
            "é", "são", "foi", "foram", "ser", "estar", "ter",
            "há", "havia", "houve", "isso", "isto", "esse",
            "essa", "este", "esta", "aquele", "aquela",
        }
        
        words = re.findall(r'\b\w+\b', text.lower())
        keywords = [
            w for w in words
            if w not in stopwords and len(w) > 2
        ]
        
        return keywords
    
    def _extract_sentences(self, text: str) -> List[str]:
        """Extrai sentenças de um texto."""
        # Divide por pontuação final
        sentences = re.split(r'[.!?]\s+', text)
        
        # Limpa e filtra
        return [
            s.strip()
            for s in sentences
            if s.strip() and len(s.strip()) > 10
        ]
    
    def _calculate_text_similarity(self, text1: str, text2: str) -> float:
        """Calcula similaridade entre dois textos."""
        # Usa SequenceMatcher para similaridade básica
        # Em produção, poderia usar embeddings
        
        # Para textos muito longos, amostra
        if len(text2) > 5000:
            # Procura a substring mais similar
            best_ratio = 0.0
            window_size = len(text1) * 2
            
            for i in range(0, len(text2) - window_size, window_size // 2):
                window = text2[i:i + window_size]
                ratio = SequenceMatcher(None, text1, window).ratio()
                best_ratio = max(best_ratio, ratio)
            
            return best_ratio
        
        return SequenceMatcher(None, text1, text2).ratio()
    
    def _contains_specific_data(self, text: str) -> bool:
        """Verifica se o texto contém dados específicos."""
        # Padrões que indicam dados específicos
        patterns = [
            r'\d+[,.]?\d*\s*%',  # Percentuais
            r'R\$\s*[\d.,]+',     # Valores monetários
            r'\d{1,2}/\d{1,2}/\d{2,4}',  # Datas
            r'\d{2}\.\d{3}\.\d{3}',  # CPF/CNPJ
            r'artigo\s+\d+',  # Artigos legais
            r'cláusula\s+\d+',  # Cláusulas
        ]
        
        for pattern in patterns:
            if re.search(pattern, text, re.IGNORECASE):
                return True
        
        return False
    
    def _count_generic_phrases(self, text: str) -> int:
        """Conta frases genéricas no texto."""
        text_lower = text.lower()
        count = 0
        
        for phrase in self.GENERIC_PHRASES:
            if phrase in text_lower:
                count += 1
        
        return count
    
    def _has_page_reference(self, answer: str, pages: List[int]) -> bool:
        """Verifica se a resposta menciona as páginas."""
        answer_lower = answer.lower()
        
        # Procura menção a "página" ou números das páginas
        if "página" in answer_lower or "pág" in answer_lower:
            return True
        
        # Procura números das páginas
        for page in pages:
            if str(page) in answer:
                return True
        
        return False
    
    def _calculate_confidence(
        self,
        grounding_score: float,
        relevance_score: float,
        generic_count: int,
        issue_count: int,
        warning_count: int
    ) -> float:
        """Calcula a confiança final da resposta."""
        # Pesos para cada fator
        confidence = (
            grounding_score * 0.4 +
            relevance_score * 0.3 +
            max(0, 1 - generic_count * 0.1) * 0.1 +
            max(0, 1 - issue_count * 0.3) * 0.15 +
            max(0, 1 - warning_count * 0.1) * 0.05
        )
        
        return min(1.0, max(0.0, confidence))
    
    def quick_validate(self, answer: str, context: str) -> bool:
        """
        Validação rápida (menos rigorosa).
        
        Args:
            answer: Resposta a validar
            context: Contexto usado
        
        Returns:
            True se passa validação básica
        """
        # Resposta não vazia
        if not answer or len(answer.strip()) < 10:
            return False
        
        # Resposta de "não encontrado" é válida
        if self._is_not_found_response(answer):
            return True
        
        # Verifica alguma similaridade com contexto
        grounding_score, _, _ = self._check_grounding(answer, context)
        
        return grounding_score >= 0.2

