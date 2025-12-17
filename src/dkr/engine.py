"""
DKR Engine - Motor de processamento de regras de domínio.

Responsável por:
- Detectar intenção de perguntas
- Expandir queries para melhor retrieval
- Validar e corrigir respostas
- Tudo 100% OFFLINE
"""

from __future__ import annotations

import logging
import re
import time
from pathlib import Path
from typing import Optional, Dict, Any, List

from .models import (
    CompiledRules,
    DKRResult,
    IntentPattern,
    ValidationRule,
    RuleAction,
    DomainFact,
)
from .parser import DKRParser

logger = logging.getLogger(__name__)


class DKREngine:
    """
    Motor de processamento de regras de domínio.
    
    Uso básico:
        engine = DKREngine("domain_rules/licencas_software.rules")
        result = engine.process(question, raw_answer, context)
        
        if result.was_corrected:
            final_answer = result.final_answer
    """
    
    def __init__(
        self,
        rules_path: Optional[Path | str] = None,
        rules: Optional[CompiledRules] = None,
    ):
        """
        Inicializa o engine.
        
        Args:
            rules_path: Caminho do arquivo .rules
            rules: Regras já compiladas (alternativa ao path)
        """
        self._rules: Optional[CompiledRules] = None
        self._parser = DKRParser()
        
        if rules:
            self._rules = rules
        elif rules_path:
            self.load_rules(rules_path)
    
    def load_rules(self, rules_path: Path | str) -> None:
        """
        Carrega regras de um arquivo.
        
        Args:
            rules_path: Caminho do arquivo .rules
        """
        self._rules = self._parser.parse_file(Path(rules_path))
        logger.info(f"DKR Engine carregado: {self._rules.domain}")
    
    @property
    def rules(self) -> Optional[CompiledRules]:
        """Retorna as regras carregadas."""
        return self._rules
    
    @property
    def is_loaded(self) -> bool:
        """Verifica se há regras carregadas."""
        return self._rules is not None
    
    def process(
        self,
        question: str,
        answer: str,
        context: str = "",
        apply_corrections: bool = True,
    ) -> DKRResult:
        """
        Processa uma pergunta/resposta aplicando regras de domínio.
        
        Args:
            question: Pergunta do usuário
            answer: Resposta gerada pelo LLM
            context: Contexto usado (para referência)
            apply_corrections: Se deve aplicar correções
        
        Returns:
            DKRResult com resultado do processamento
        """
        start_time = time.time()
        
        result = DKRResult(
            original_question=question,
            original_answer=answer,
            final_answer=answer,
            domain=self._rules.domain if self._rules else "",
        )
        
        if not self._rules:
            logger.warning("DKR Engine sem regras carregadas")
            return result
        
        # 1. Detecta intenção
        intent, confidence = self._detect_intent(question)
        result.detected_intent = intent
        result.intent_confidence = confidence
        
        # 2. Expande query (para uso externo)
        if intent and intent in self._rules.expansions:
            expansion = self._rules.expansions[intent]
            result.query_expanded = True
            result.expanded_query = expansion.expand(question)
            result.expansion_terms = expansion.add_terms
        
        # 3. Normaliza termos na resposta (NOVO)
        current_answer = answer
        if self._rules.normalizations:
            current_answer, normalizations = self._normalize_terms(answer)
            if normalizations:
                result.was_normalized = True
                result.normalizations_applied = normalizations
                result.answer_after_normalization = current_answer
                result.final_answer = current_answer
                logger.debug(f"DKR normalizou {len(normalizations)} termo(s)")
        
        # 4. Valida e corrige resposta (usando resposta normalizada)
        if apply_corrections:
            result = self._validate_and_correct(result, current_answer)
        
        result.processing_time_ms = (time.time() - start_time) * 1000
        
        logger.debug(
            f"DKR processado: intent={intent}, "
            f"normalized={result.was_normalized}, "
            f"corrected={result.was_corrected}, "
            f"time={result.processing_time_ms:.1f}ms"
        )
        
        return result
    
    def _detect_intent(self, question: str) -> tuple[Optional[str], float]:
        """
        Detecta a intenção da pergunta.
        
        Returns:
            Tuple de (nome_intent, confiança)
        """
        if not self._rules:
            return None, 0.0
        
        best_intent = None
        best_confidence = 0.0
        
        for name, intent in self._rules.intents.items():
            if intent.matches(question):
                confidence = intent.get_confidence(question)
                if confidence > best_confidence:
                    best_intent = name
                    best_confidence = confidence
        
        return best_intent, best_confidence
    
    def _validate_and_correct(
        self, 
        result: DKRResult, 
        answer: str
    ) -> DKRResult:
        """
        Valida a resposta e aplica correções se necessário.
        
        Args:
            result: Resultado parcial
            answer: Resposta a validar
        
        Returns:
            DKRResult atualizado
        """
        if not self._rules:
            return result
        
        result.rules_evaluated = len(self._rules.validation_rules)
        
        for rule in self._rules.validation_rules:
            if rule.should_trigger(result.detected_intent, answer):
                result.rules_triggered.append(rule.name)
                
                if rule.action == RuleAction.REPLACE:
                    # Aplica correção
                    corrected = self._apply_replacement(rule, result)
                    if corrected:
                        result.final_answer = corrected
                        result.was_corrected = True
                        result.correction_reason = (
                            f"Regra '{rule.name}': {rule.description or 'Resposta corrigida'}"
                        )
                        logger.info(f"DKR correção aplicada: {rule.name}")
                        # Aplica apenas a primeira correção
                        break
                
                elif rule.action == RuleAction.KEEP:
                    # Mantém resposta original
                    logger.debug(f"DKR mantendo resposta: {rule.name}")
        
        return result
    
    def _apply_replacement(
        self, 
        rule: ValidationRule, 
        result: DKRResult
    ) -> Optional[str]:
        """
        Aplica template de substituição.
        
        Args:
            rule: Regra de validação
            result: Resultado atual (para contexto)
        
        Returns:
            Texto corrigido ou None se falhar
        """
        template = rule.replacement_template
        
        if not template:
            # Sem template, tenta gerar resposta baseada nos fatos
            return self._generate_fact_based_response(result)
        
        # Substitui variáveis no template
        corrected = self._substitute_variables(template, result)
        
        return corrected
    
    def _substitute_variables(self, template: str, result: DKRResult) -> str:
        """
        Substitui variáveis no template.
        
        Variáveis suportadas:
            {facts.criticidade.ALTO[0].name}
            {facts.criticidade.ALTO[0].reason}
            {question}
            {intent}
        """
        text = template
        
        # Substitui referências a fatos
        fact_pattern = r'\{facts\.criticidade\.(\w+)\[(\d+)\]\.(\w+)\}'
        
        for match in re.finditer(fact_pattern, template):
            level = match.group(1).upper()
            index = int(match.group(2))
            prop = match.group(3)
            
            facts = self._rules.facts.get(level, [])
            if index < len(facts):
                fact = facts[index]
                value = getattr(fact, prop, "")
                text = text.replace(match.group(0), str(value))
        
        # Substitui variáveis simples
        text = text.replace("{question}", result.original_question)
        text = text.replace("{intent}", result.detected_intent or "")
        
        return text.strip()
    
    def _generate_fact_based_response(self, result: DKRResult) -> Optional[str]:
        """
        Gera resposta baseada nos fatos conhecidos.
        
        Usado quando regra não tem template definido.
        """
        if not self._rules:
            return None
        
        intent = result.detected_intent
        
        if intent == "criticidade_alta":
            critical_facts = self._rules.get_critical_facts()
            if critical_facts:
                fact = critical_facts[0]
                return (
                    f"De acordo com as regras do domínio, a mais crítica é "
                    f"**{fact.name}** com grau de criticidade **ALTO**.\n\n"
                    f"Justificativa: {fact.reason or 'Requer atenção especial.'}\n\n"
                    f"Recomendação: {fact.action or 'Evitar uso.'}\n\n"
                    f"(Resposta validada pelo sistema de regras de domínio)"
                )
        
        elif intent == "criticidade_baixa":
            safe_facts = self._rules.get_safe_facts()
            if safe_facts:
                names = ", ".join(f"**{f.name}**" for f in safe_facts[:3])
                return (
                    f"De acordo com as regras do domínio, as mais seguras são: "
                    f"{names} com grau de criticidade **BAIXO**.\n\n"
                    f"São opções permissivas com poucas obrigações.\n\n"
                    f"(Resposta validada pelo sistema de regras de domínio)"
                )
        
        return None
    
    def _normalize_terms(self, text: str) -> tuple[str, List[str]]:
        """
        Aplica todas as normalizações de termos ao texto.
        
        Args:
            text: Texto a normalizar
        
        Returns:
            Tuple de (texto_normalizado, lista_de_normalizações_aplicadas)
        """
        if not self._rules or not self._rules.normalizations:
            return text, []
        
        result = text
        applied = []
        
        for norm in self._rules.normalizations:
            new_text, was_applied = norm.apply(result)
            if was_applied:
                applied.append(str(norm))
                result = new_text
        
        return result, applied
    
    def expand_query(self, question: str) -> str:
        """
        Expande a query para melhor retrieval.
        
        Args:
            question: Pergunta original
        
        Returns:
            Query expandida (ou original se não houver expansão)
        """
        if not self._rules:
            return question
        
        intent, _ = self._detect_intent(question)
        
        if intent and intent in self._rules.expansions:
            expansion = self._rules.expansions[intent]
            return expansion.expand(question)
        
        return question
    
    def get_facts_summary(self) -> Dict[str, Any]:
        """Retorna resumo dos fatos conhecidos."""
        if not self._rules:
            return {}
        
        return {
            "domain": self._rules.domain,
            "total_facts": sum(len(f) for f in self._rules.facts.values()),
            "by_criticality": {
                level: len(facts) 
                for level, facts in self._rules.facts.items()
            },
            "intents": list(self._rules.intents.keys()),
            "rules": len(self._rules.validation_rules),
            "normalizations": len(self._rules.normalizations),
        }
    
    def explain_intent(self, question: str) -> str:
        """
        Explica qual intent foi detectado e por quê.
        
        Args:
            question: Pergunta a analisar
        
        Returns:
            Explicação formatada
        """
        intent, confidence = self._detect_intent(question)
        
        if not intent:
            return "Nenhuma intenção detectada para esta pergunta."
        
        lines = [
            f"Intenção detectada: {intent}",
            f"Confiança: {confidence:.0%}",
        ]
        
        if self._rules and intent in self._rules.intents:
            intent_def = self._rules.intents[intent]
            lines.append(f"Padrões correspondentes:")
            for p in intent_def.patterns:
                if p.lower() in question.lower():
                    lines.append(f"  ✓ '{p}'")
        
        if intent in self._rules.expansions:
            exp = self._rules.expansions[intent]
            lines.append(f"Query será expandida com: {exp.add_terms}")
        
        return "\n".join(lines)


def get_dkr_engine(
    domain: str,
    rules_dir: Path | str = Path("domain_rules")
) -> Optional[DKREngine]:
    """
    Factory para obter engine DKR para um domínio.
    
    Args:
        domain: Nome do domínio (ex: "licencas_software")
        rules_dir: Diretório dos arquivos .rules
    
    Returns:
        DKREngine configurado ou None se não existir
    """
    rules_dir = Path(rules_dir)
    rules_file = rules_dir / f"{domain}.rules"
    
    if not rules_file.exists():
        logger.debug(f"Arquivo .rules não encontrado: {rules_file}")
        return None
    
    try:
        return DKREngine(rules_file)
    except Exception as e:
        logger.error(f"Erro ao carregar DKR para '{domain}': {e}")
        return None

