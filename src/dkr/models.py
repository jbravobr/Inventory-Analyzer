"""
Modelos de dados para o módulo DKR.

Define as estruturas de dados usadas para representar
regras de domínio parseadas.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from enum import Enum


class CriticalityLevel(Enum):
    """Níveis de criticidade."""
    ALTO = "ALTO"
    MEDIO = "MÉDIO"
    BAIXO = "BAIXO"


class RuleAction(Enum):
    """Ações possíveis para regras de validação."""
    REPLACE = "replace"       # Substitui resposta completamente
    PREPEND = "prepend"       # Adiciona texto no início
    APPEND = "append"         # Adiciona texto no final
    FLAG = "flag"             # Marca para revisão
    KEEP = "keep"             # Mantém resposta original


@dataclass
class DomainFact:
    """
    Fato do domínio (conhecimento estruturado).
    
    Exemplo:
        A licença AGPL-3.0-only tem criticidade ALTO.
        Motivo: Possui obrigações mesmo sem distribuição.
        Ação: Evitar uso.
    """
    name: str
    criticality: Optional[str] = None
    reason: str = ""
    action: str = ""
    aliases: List[str] = field(default_factory=list)
    properties: Dict[str, Any] = field(default_factory=dict)
    
    def matches(self, text: str) -> bool:
        """Verifica se o fato é mencionado no texto."""
        text_lower = text.lower()
        if self.name.lower() in text_lower:
            return True
        for alias in self.aliases:
            if alias.lower() in text_lower:
                return True
        return False


@dataclass
class IntentPattern:
    """
    Padrão de intenção para detectar tipo de pergunta.
    
    Exemplo:
        Nome: criticidade_alta
        Padrões: ["mais crítica", "mais perigosa", "maior risco"]
        Resposta esperada deve conter: ["ALTO", "AGPL"]
    """
    name: str
    patterns: List[str]
    expected_contains: List[str] = field(default_factory=list)
    expected_not_contains: List[str] = field(default_factory=list)
    
    def matches(self, text: str) -> bool:
        """Verifica se algum padrão corresponde ao texto."""
        text_lower = text.lower()
        for pattern in self.patterns:
            if pattern.lower() in text_lower:
                return True
        return False
    
    def get_confidence(self, text: str) -> float:
        """Retorna confiança da detecção (0.0 a 1.0)."""
        text_lower = text.lower()
        matches = sum(1 for p in self.patterns if p.lower() in text_lower)
        if matches == 0:
            return 0.0
        return min(1.0, matches / len(self.patterns) + 0.5)


@dataclass
class QueryExpansion:
    """
    Expansão de query para melhorar retrieval.
    
    Exemplo:
        Para intenção: criticidade_alta
        Adicionar termos: ["GRAU DE CRITICIDADE", "ALTO"]
    """
    intent_name: str
    add_terms: List[str]
    
    def expand(self, query: str) -> str:
        """Expande a query com os termos adicionais."""
        return f"{query} {' '.join(self.add_terms)}"


@dataclass
class ValidationRule:
    """
    Regra de validação/correção de resposta.
    
    Exemplo:
        Nome: criticidade_invertida
        Trigger: intent == "criticidade_alta" AND 
                 resposta contém "Apache" AND
                 resposta NÃO contém "AGPL"
        Ação: REPLACE
        Template: "A licença mais crítica é AGPL-3.0-only (ALTO)..."
    """
    name: str
    description: str = ""
    trigger_intent: Optional[str] = None
    trigger_answer_contains: List[str] = field(default_factory=list)
    trigger_answer_not_contains: List[str] = field(default_factory=list)
    action: RuleAction = RuleAction.REPLACE
    replacement_template: str = ""
    
    def should_trigger(
        self, 
        detected_intent: Optional[str],
        answer: str
    ) -> bool:
        """Verifica se a regra deve ser ativada."""
        # Verifica intent
        if self.trigger_intent and detected_intent != self.trigger_intent:
            return False
        
        answer_lower = answer.lower()
        
        # Verifica se contém algum termo esperado
        if self.trigger_answer_contains:
            has_any = any(
                term.lower() in answer_lower 
                for term in self.trigger_answer_contains
            )
            if not has_any:
                return False
        
        # Verifica se NÃO contém termos esperados
        if self.trigger_answer_not_contains:
            missing_all = all(
                term.lower() not in answer_lower
                for term in self.trigger_answer_not_contains
            )
            if not missing_all:
                return False
        
        return True


@dataclass
class Synonym:
    """
    Grupo de sinônimos.
    
    Exemplo:
        "crítica" também pode ser: "perigosa", "arriscada", "restritiva"
    """
    term: str
    alternatives: List[str]
    
    def expand(self, text: str) -> str:
        """Expande o texto com sinônimos."""
        # Não modifica, apenas para referência
        return text
    
    def matches_any(self, text: str) -> bool:
        """Verifica se o termo ou algum sinônimo está no texto."""
        text_lower = text.lower()
        if self.term.lower() in text_lower:
            return True
        return any(alt.lower() in text_lower for alt in self.alternatives)


@dataclass
class TermNormalization:
    """
    Normalização de termo (correção de siglas/termos errados).
    
    Exemplo:
        "GPLA" corrigir para: "GPL"
        "GPLv2" corrigir para: "GPL-2.0"
    """
    original: str           # Termo incorreto/variante (ex: "GPLA")
    normalized: str         # Termo canônico (ex: "GPL")
    case_sensitive: bool = False  # Se deve respeitar maiúsculas/minúsculas
    
    def apply(self, text: str) -> tuple[str, bool]:
        """
        Aplica a normalização no texto.
        
        Returns:
            Tuple de (texto_normalizado, foi_aplicado)
        """
        import re
        
        if self.case_sensitive:
            if self.original in text:
                return text.replace(self.original, self.normalized), True
            return text, False
        else:
            # Substituição case-insensitive
            pattern = re.compile(re.escape(self.original), re.IGNORECASE)
            new_text, count = pattern.subn(self.normalized, text)
            return new_text, count > 0
    
    def __str__(self) -> str:
        cs = " [case-sensitive]" if self.case_sensitive else ""
        return f'"{self.original}" → "{self.normalized}"{cs}'


@dataclass
class CompiledRules:
    """
    Conjunto completo de regras compiladas de um arquivo .rules.
    """
    domain: str
    version: str = "1.0"
    source_file: str = ""
    source_hash: str = ""
    
    # Conhecimento
    facts: Dict[str, List[DomainFact]] = field(default_factory=dict)
    # Agrupados por criticidade: {"ALTO": [...], "MÉDIO": [...], "BAIXO": [...]}
    
    # Detecção de intenção
    intents: Dict[str, IntentPattern] = field(default_factory=dict)
    
    # Expansão de query
    expansions: Dict[str, QueryExpansion] = field(default_factory=dict)
    
    # Validação
    validation_rules: List[ValidationRule] = field(default_factory=list)
    
    # Sinônimos
    synonyms: Dict[str, Synonym] = field(default_factory=dict)
    
    # Normalizações de termos
    normalizations: List[TermNormalization] = field(default_factory=list)
    
    def get_facts_by_criticality(self, level: str) -> List[DomainFact]:
        """Retorna fatos de uma criticidade específica."""
        return self.facts.get(level.upper(), [])
    
    def get_critical_facts(self) -> List[DomainFact]:
        """Retorna fatos com criticidade ALTO."""
        return self.get_facts_by_criticality("ALTO")
    
    def get_safe_facts(self) -> List[DomainFact]:
        """Retorna fatos com criticidade BAIXO."""
        return self.get_facts_by_criticality("BAIXO")
    
    def to_dict(self) -> Dict[str, Any]:
        """Serializa para dicionário."""
        return {
            "domain": self.domain,
            "version": self.version,
            "source_file": self.source_file,
            "source_hash": self.source_hash,
            "facts_count": sum(len(f) for f in self.facts.values()),
            "intents_count": len(self.intents),
            "rules_count": len(self.validation_rules),
            "synonyms_count": len(self.synonyms),
            "normalizations_count": len(self.normalizations),
        }


@dataclass
class DKRResult:
    """
    Resultado do processamento DKR.
    """
    original_question: str
    original_answer: str
    final_answer: str
    
    # Detecção
    detected_intent: Optional[str] = None
    intent_confidence: float = 0.0
    
    # Expansão
    query_expanded: bool = False
    expanded_query: str = ""
    expansion_terms: List[str] = field(default_factory=list)
    
    # Normalização
    was_normalized: bool = False
    normalizations_applied: List[str] = field(default_factory=list)
    answer_after_normalization: str = ""
    
    # Validação
    rules_evaluated: int = 0
    rules_triggered: List[str] = field(default_factory=list)
    was_corrected: bool = False
    correction_reason: str = ""
    
    # Metadata
    processing_time_ms: float = 0.0
    domain: str = ""
    
    @property
    def answer_changed(self) -> bool:
        """Verifica se a resposta foi alterada."""
        return self.original_answer != self.final_answer
    
    def to_dict(self) -> Dict[str, Any]:
        """Serializa para dicionário (para logs/debug)."""
        return {
            "detected_intent": self.detected_intent,
            "intent_confidence": self.intent_confidence,
            "query_expanded": self.query_expanded,
            "was_normalized": self.was_normalized,
            "normalizations_applied": self.normalizations_applied,
            "rules_evaluated": self.rules_evaluated,
            "rules_triggered": self.rules_triggered,
            "was_corrected": self.was_corrected,
            "correction_reason": self.correction_reason,
            "processing_time_ms": self.processing_time_ms,
        }
    
    def format_trace(self) -> str:
        """Formata trace para exibição."""
        lines = [
            "═" * 60,
            "  DKR TRACE",
            "═" * 60,
            f"Domínio: {self.domain}",
            f"Intenção detectada: {self.detected_intent or 'Nenhuma'} ({self.intent_confidence:.0%})",
            f"Query expandida: {'Sim' if self.query_expanded else 'Não'}",
        ]
        
        if self.query_expanded:
            lines.append(f"  Termos adicionados: {self.expansion_terms}")
        
        # Normalização
        lines.append(f"Termos normalizados: {'Sim' if self.was_normalized else 'Não'}")
        if self.was_normalized:
            for norm in self.normalizations_applied:
                lines.append(f"  • {norm}")
        
        lines.extend([
            f"Regras avaliadas: {self.rules_evaluated}",
            f"Regras ativadas: {len(self.rules_triggered)}",
        ])
        
        if self.rules_triggered:
            for rule in self.rules_triggered:
                lines.append(f"  • {rule}")
        
        lines.extend([
            f"Resposta corrigida: {'SIM' if self.was_corrected else 'NÃO'}",
        ])
        
        if self.was_corrected:
            lines.append(f"  Motivo: {self.correction_reason}")
        
        lines.append(f"Tempo: {self.processing_time_ms:.1f}ms")
        lines.append("═" * 60)
        
        return "\n".join(lines)

