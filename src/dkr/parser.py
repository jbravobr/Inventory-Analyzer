"""
Parser de arquivos .rules (DSL humanizada).

Converte arquivos de texto em linguagem humanizada para
estruturas de dados utilizáveis pelo DKR Engine.

Formato suportado:
    DOMÍNIO: Nome do Domínio
    
    FATOS CONHECIDOS:
    A licença X tem criticidade ALTO.
      Motivo: ...
      Ação: ...
    
    REGRAS DE VALIDAÇÃO:
    QUANDO usuário pergunta "..."
      E resposta menciona "..."
    ENTÃO corrigir para: ...
    
    SINÔNIMOS:
    "termo" também pode ser: "alt1", "alt2"
"""

from __future__ import annotations

import hashlib
import logging
import re
from pathlib import Path
from typing import List, Dict, Optional, Tuple, Any

from .models import (
    DomainFact,
    IntentPattern,
    ValidationRule,
    QueryExpansion,
    Synonym,
    CompiledRules,
    RuleAction,
)

logger = logging.getLogger(__name__)


class DKRParser:
    """
    Parser para arquivos .rules em DSL humanizada.
    
    Uso:
        parser = DKRParser()
        rules = parser.parse_file("domain_rules/licencas_software.rules")
    """
    
    # Seções reconhecidas
    SECTION_MARKERS = {
        "domain": r"^DOMÍNIO:\s*(.+)$",
        "facts": r"^FATOS\s+CONHECIDOS:?\s*$",
        "intents": r"^PADRÕES\s+DE\s+INTENÇÃO:?\s*$",
        "rules": r"^REGRAS\s+DE\s+VALIDAÇÃO:?\s*$",
        "expansions": r"^EXPANSÃO\s+DE\s+BUSCA:?\s*$",
        "synonyms": r"^SINÔNIMOS:?\s*$",
    }
    
    # Padrões para parsing de fatos
    FACT_PATTERNS = {
        "main": r"^[AO]\s+(?:licença\s+)?(.+?)\s+tem\s+criticidade\s+(ALTO|MÉDIO|BAIXO)\.?$",
        "reason": r"^\s*Motivo:\s*(.+)$",
        "action": r"^\s*Ação:\s*(.+)$",
    }
    
    # Padrões para parsing de regras
    RULE_PATTERNS = {
        "when": r"^QUANDO\s+(?:usuário\s+)?pergunta[r]?\s+[\"'](.+?)[\"']",
        "and_contains": r"^\s*E\s+resposta\s+(?:menciona|contém)\s+[\"'](.+?)[\"']",
        "and_not_contains": r"^\s*E\s+resposta\s+NÃO\s+(?:menciona|contém)\s+[\"'](.+?)[\"']",
        "or_contains": r"^\s*OU\s+[\"'](.+?)[\"']",
        "then_replace": r"^\s*ENTÃO\s+corrigir\s+para:\s*$",
        "then_keep": r"^\s*ENTÃO\s+manter\s+resposta",
    }
    
    # Padrões para sinônimos
    SYNONYM_PATTERN = r"^[\"'](.+?)[\"']\s+também\s+pode\s+ser:\s*(.+)$"
    
    # Padrões para intent
    INTENT_PATTERNS = {
        "name": r"^(\w+):?\s*$",
        "pattern": r"^\s*[-•]\s*[\"'](.+?)[\"']",
        "expected": r"^\s*Resposta\s+deve\s+conter:\s*(.+)$",
    }
    
    # Padrões para expansão
    EXPANSION_PATTERN = r"^Para\s+[\"']?(\w+)[\"']?,?\s+(?:adicionar|buscar):\s*(.+)$"
    
    def __init__(self):
        """Inicializa o parser."""
        self._current_section: Optional[str] = None
        self._errors: List[str] = []
        self._warnings: List[str] = []
    
    def parse_file(self, file_path: Path | str) -> CompiledRules:
        """
        Parseia um arquivo .rules.
        
        Args:
            file_path: Caminho do arquivo
        
        Returns:
            CompiledRules com regras compiladas
        
        Raises:
            FileNotFoundError: Se arquivo não existe
            ValueError: Se arquivo tem erros de sintaxe
        """
        file_path = Path(file_path)
        
        if not file_path.exists():
            raise FileNotFoundError(f"Arquivo não encontrado: {file_path}")
        
        content = file_path.read_text(encoding="utf-8")
        file_hash = hashlib.md5(content.encode()).hexdigest()[:8]
        
        rules = self.parse_content(content)
        rules.source_file = str(file_path)
        rules.source_hash = file_hash
        
        logger.info(
            f"Arquivo .rules parseado: {file_path.name} "
            f"({len(rules.validation_rules)} regras, "
            f"{sum(len(f) for f in rules.facts.values())} fatos)"
        )
        
        return rules
    
    def parse_content(self, content: str) -> CompiledRules:
        """
        Parseia conteúdo de um arquivo .rules.
        
        Args:
            content: Conteúdo do arquivo
        
        Returns:
            CompiledRules com regras compiladas
        """
        self._errors = []
        self._warnings = []
        self._current_section = None
        
        rules = CompiledRules(domain="unknown")
        
        lines = content.split("\n")
        i = 0
        
        while i < len(lines):
            line = lines[i]
            stripped = line.strip()
            
            # Ignora linhas vazias e comentários
            if not stripped or stripped.startswith("#"):
                i += 1
                continue
            
            # Ignora separadores visuais
            if stripped.startswith("─") or stripped.startswith("━") or stripped.startswith("═"):
                i += 1
                continue
            
            # Detecta seção
            section = self._detect_section(stripped)
            if section:
                self._current_section = section
                if section == "domain":
                    rules.domain = self._extract_domain(stripped)
                i += 1
                continue
            
            # Parseia conteúdo da seção atual
            if self._current_section == "facts":
                fact, consumed = self._parse_fact(lines, i)
                if fact:
                    crit = fact.criticality or "OUTRO"
                    if crit not in rules.facts:
                        rules.facts[crit] = []
                    rules.facts[crit].append(fact)
                i += consumed
                
            elif self._current_section == "rules":
                rule, consumed = self._parse_validation_rule(lines, i)
                if rule:
                    rules.validation_rules.append(rule)
                i += consumed
                
            elif self._current_section == "synonyms":
                synonym = self._parse_synonym(stripped)
                if synonym:
                    rules.synonyms[synonym.term.lower()] = synonym
                i += 1
                
            elif self._current_section == "intents":
                intent, consumed = self._parse_intent(lines, i)
                if intent:
                    rules.intents[intent.name] = intent
                i += consumed
                
            elif self._current_section == "expansions":
                expansion = self._parse_expansion(stripped)
                if expansion:
                    rules.expansions[expansion.intent_name] = expansion
                i += 1
                
            else:
                i += 1
        
        # Gera intents automáticos baseados em fatos (se não definidos)
        self._generate_auto_intents(rules)
        
        return rules
    
    def _detect_section(self, line: str) -> Optional[str]:
        """Detecta se a linha marca início de uma seção."""
        for section_name, pattern in self.SECTION_MARKERS.items():
            if re.match(pattern, line, re.IGNORECASE):
                return section_name
        return None
    
    def _extract_domain(self, line: str) -> str:
        """Extrai nome do domínio da linha."""
        match = re.match(self.SECTION_MARKERS["domain"], line, re.IGNORECASE)
        if match:
            return match.group(1).strip()
        return "unknown"
    
    def _parse_fact(self, lines: List[str], start: int) -> Tuple[Optional[DomainFact], int]:
        """
        Parseia um fato do domínio.
        
        Returns:
            Tuple de (DomainFact ou None, linhas consumidas)
        """
        line = lines[start].strip()
        
        # Tenta padrão principal
        match = re.match(self.FACT_PATTERNS["main"], line, re.IGNORECASE)
        if not match:
            return None, 1
        
        fact = DomainFact(
            name=match.group(1).strip(),
            criticality=match.group(2).upper(),
        )
        
        consumed = 1
        
        # Busca linhas adicionais (Motivo, Ação)
        while start + consumed < len(lines):
            next_line = lines[start + consumed].strip()
            
            if not next_line:
                consumed += 1
                continue
            
            # Verifica se é nova seção ou novo fato
            if self._detect_section(next_line):
                break
            if re.match(self.FACT_PATTERNS["main"], next_line, re.IGNORECASE):
                break
            
            # Parseia Motivo
            reason_match = re.match(self.FACT_PATTERNS["reason"], next_line, re.IGNORECASE)
            if reason_match:
                fact.reason = reason_match.group(1).strip()
                consumed += 1
                continue
            
            # Parseia Ação
            action_match = re.match(self.FACT_PATTERNS["action"], next_line, re.IGNORECASE)
            if action_match:
                fact.action = action_match.group(1).strip()
                consumed += 1
                continue
            
            # Linha não reconhecida, para
            break
        
        return fact, consumed
    
    def _parse_validation_rule(
        self, 
        lines: List[str], 
        start: int
    ) -> Tuple[Optional[ValidationRule], int]:
        """
        Parseia uma regra de validação.
        
        Returns:
            Tuple de (ValidationRule ou None, linhas consumidas)
        """
        line = lines[start].strip()
        
        # Deve começar com QUANDO
        when_match = re.match(self.RULE_PATTERNS["when"], line, re.IGNORECASE)
        if not when_match:
            return None, 1
        
        # Extrai padrão de pergunta para criar intent automático
        question_pattern = when_match.group(1)
        
        rule = ValidationRule(
            name=f"rule_{start}",
            trigger_intent=self._pattern_to_intent_name(question_pattern),
        )
        
        consumed = 1
        in_replacement = False
        replacement_lines = []
        
        while start + consumed < len(lines):
            next_line = lines[start + consumed]
            stripped = next_line.strip()
            
            if not stripped:
                if in_replacement:
                    # Linha vazia em replacement pode ser parte do template
                    # Mas se já temos conteúdo, provavelmente acabou
                    if replacement_lines:
                        break
                consumed += 1
                continue
            
            # Verifica se é nova seção
            if self._detect_section(stripped):
                break
            
            # Verifica se é nova regra
            if re.match(self.RULE_PATTERNS["when"], stripped, re.IGNORECASE):
                break
            
            if in_replacement:
                # Coleta linhas do template de correção
                replacement_lines.append(next_line)
                consumed += 1
                continue
            
            # E resposta menciona
            and_match = re.match(self.RULE_PATTERNS["and_contains"], stripped, re.IGNORECASE)
            if and_match:
                rule.trigger_answer_contains.append(and_match.group(1))
                consumed += 1
                continue
            
            # OU "termo"
            or_match = re.match(self.RULE_PATTERNS["or_contains"], stripped, re.IGNORECASE)
            if or_match:
                rule.trigger_answer_contains.append(or_match.group(1))
                consumed += 1
                continue
            
            # E resposta NÃO menciona
            not_match = re.match(self.RULE_PATTERNS["and_not_contains"], stripped, re.IGNORECASE)
            if not_match:
                rule.trigger_answer_not_contains.append(not_match.group(1))
                consumed += 1
                continue
            
            # ENTÃO corrigir para:
            then_replace = re.match(self.RULE_PATTERNS["then_replace"], stripped, re.IGNORECASE)
            if then_replace:
                rule.action = RuleAction.REPLACE
                in_replacement = True
                consumed += 1
                continue
            
            # ENTÃO manter resposta
            then_keep = re.match(self.RULE_PATTERNS["then_keep"], stripped, re.IGNORECASE)
            if then_keep:
                rule.action = RuleAction.KEEP
                consumed += 1
                break
            
            # Linha não reconhecida
            consumed += 1
        
        # Monta template de replacement
        if replacement_lines:
            rule.replacement_template = "\n".join(replacement_lines)
        
        return rule, consumed
    
    def _parse_synonym(self, line: str) -> Optional[Synonym]:
        """Parseia uma linha de sinônimo."""
        match = re.match(self.SYNONYM_PATTERN, line, re.IGNORECASE)
        if not match:
            return None
        
        term = match.group(1).strip()
        alternatives_str = match.group(2).strip()
        
        # Extrai alternativas (separadas por vírgula)
        alternatives = []
        for alt in re.findall(r'["\']([^"\']+)["\']', alternatives_str):
            alternatives.append(alt.strip())
        
        if not alternatives:
            # Tenta sem aspas
            alternatives = [a.strip() for a in alternatives_str.split(",")]
        
        return Synonym(term=term, alternatives=alternatives)
    
    def _parse_intent(
        self, 
        lines: List[str], 
        start: int
    ) -> Tuple[Optional[IntentPattern], int]:
        """Parseia definição de intent."""
        line = lines[start].strip()
        
        # Nome do intent
        name_match = re.match(self.INTENT_PATTERNS["name"], line)
        if not name_match:
            return None, 1
        
        intent = IntentPattern(
            name=name_match.group(1),
            patterns=[],
        )
        
        consumed = 1
        
        while start + consumed < len(lines):
            next_line = lines[start + consumed].strip()
            
            if not next_line:
                consumed += 1
                continue
            
            # Verifica se é nova seção ou novo intent
            if self._detect_section(next_line):
                break
            if re.match(self.INTENT_PATTERNS["name"], next_line):
                break
            
            # Padrão de matching
            pattern_match = re.match(self.INTENT_PATTERNS["pattern"], next_line)
            if pattern_match:
                intent.patterns.append(pattern_match.group(1))
                consumed += 1
                continue
            
            # Expected contains
            expected_match = re.match(self.INTENT_PATTERNS["expected"], next_line, re.IGNORECASE)
            if expected_match:
                terms = re.findall(r'["\']([^"\']+)["\']', expected_match.group(1))
                intent.expected_contains.extend(terms)
                consumed += 1
                continue
            
            consumed += 1
        
        if not intent.patterns:
            return None, consumed
        
        return intent, consumed
    
    def _parse_expansion(self, line: str) -> Optional[QueryExpansion]:
        """Parseia definição de expansão de query."""
        match = re.match(self.EXPANSION_PATTERN, line, re.IGNORECASE)
        if not match:
            return None
        
        intent_name = match.group(1).strip()
        terms_str = match.group(2).strip()
        
        # Extrai termos
        terms = re.findall(r'["\']([^"\']+)["\']', terms_str)
        if not terms:
            terms = [t.strip() for t in terms_str.split(",")]
        
        return QueryExpansion(intent_name=intent_name, add_terms=terms)
    
    def _pattern_to_intent_name(self, pattern: str) -> str:
        """Converte padrão de pergunta em nome de intent."""
        pattern_lower = pattern.lower()
        
        if "mais crítica" in pattern_lower or "maior risco" in pattern_lower:
            return "criticidade_alta"
        if "mais segura" in pattern_lower or "recomendada" in pattern_lower:
            return "criticidade_baixa"
        if "compatib" in pattern_lower:
            return "compatibilidade"
        if "evitar" in pattern_lower:
            return "evitar"
        if "defini" in pattern_lower or "o que é" in pattern_lower:
            return "definicao"
        
        # Gera nome baseado no padrão
        clean = re.sub(r'[^\w\s]', '', pattern_lower)
        words = clean.split()[:3]
        return "_".join(words) if words else "unknown"
    
    def _generate_auto_intents(self, rules: CompiledRules) -> None:
        """Gera intents automáticos baseados nos fatos conhecidos."""
        # Intent para criticidade alta
        if "criticidade_alta" not in rules.intents and rules.get_critical_facts():
            rules.intents["criticidade_alta"] = IntentPattern(
                name="criticidade_alta",
                patterns=[
                    "mais crítica",
                    "mais perigosa", 
                    "mais restritiva",
                    "maior risco",
                    "devo evitar",
                    "crítico",
                ],
                expected_contains=["ALTO", "AGPL"] if rules.get_critical_facts() else [],
            )
            
            # Expansão automática
            if "criticidade_alta" not in rules.expansions:
                rules.expansions["criticidade_alta"] = QueryExpansion(
                    intent_name="criticidade_alta",
                    add_terms=["GRAU DE CRITICIDADE", "ALTO"],
                )
        
        # Intent para criticidade baixa
        if "criticidade_baixa" not in rules.intents and rules.get_safe_facts():
            rules.intents["criticidade_baixa"] = IntentPattern(
                name="criticidade_baixa",
                patterns=[
                    "mais segura",
                    "mais permissiva",
                    "recomendada",
                    "posso usar",
                    "baixo risco",
                ],
                expected_contains=["BAIXO"],
            )
            
            if "criticidade_baixa" not in rules.expansions:
                rules.expansions["criticidade_baixa"] = QueryExpansion(
                    intent_name="criticidade_baixa",
                    add_terms=["GRAU DE CRITICIDADE", "BAIXO", "permissiva"],
                )
    
    @property
    def errors(self) -> List[str]:
        """Retorna erros encontrados no parsing."""
        return self._errors.copy()
    
    @property
    def warnings(self) -> List[str]:
        """Retorna avisos encontrados no parsing."""
        return self._warnings.copy()

