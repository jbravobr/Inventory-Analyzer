"""
Validador de arquivos .rules.

Verifica sintaxe e semântica dos arquivos de regras,
fornecendo mensagens de erro amigáveis.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional, Dict, Any

from .models import CompiledRules
from .parser import DKRParser

logger = logging.getLogger(__name__)


@dataclass
class ValidationIssue:
    """Representa um problema encontrado na validação."""
    
    level: str  # "error", "warning", "info"
    message: str
    line: Optional[int] = None
    suggestion: str = ""
    
    def format(self) -> str:
        """Formata o issue para exibição."""
        icon = {"error": "❌", "warning": "⚠️", "info": "ℹ️"}.get(self.level, "•")
        
        parts = [f"{icon} {self.message}"]
        
        if self.line:
            parts[0] = f"{icon} Linha {self.line}: {self.message}"
        
        if self.suggestion:
            parts.append(f"   💡 Sugestão: {self.suggestion}")
        
        return "\n".join(parts)


@dataclass
class ValidationReport:
    """Relatório completo de validação."""
    
    file_path: str
    is_valid: bool
    errors: List[ValidationIssue] = field(default_factory=list)
    warnings: List[ValidationIssue] = field(default_factory=list)
    info: List[ValidationIssue] = field(default_factory=list)
    rules: Optional[CompiledRules] = None
    
    @property
    def has_errors(self) -> bool:
        return len(self.errors) > 0
    
    @property
    def has_warnings(self) -> bool:
        return len(self.warnings) > 0
    
    def format(self) -> str:
        """Formata o relatório para exibição."""
        lines = [
            "╔" + "═" * 60 + "╗",
            f"║  📋 VALIDAÇÃO: {Path(self.file_path).name:<43} ║",
            "╠" + "═" * 60 + "╣",
        ]
        
        # Status geral
        if self.is_valid:
            lines.append("║  ✅ Arquivo válido e pronto para uso" + " " * 22 + "║")
        else:
            lines.append("║  ❌ Arquivo contém erros que precisam ser corrigidos" + " " * 6 + "║")
        
        lines.append("╠" + "═" * 60 + "╣")
        
        # Estatísticas
        if self.rules:
            facts_count = sum(len(f) for f in self.rules.facts.values())
            lines.extend([
                f"║  📊 Estatísticas:" + " " * 41 + "║",
                f"║     • Domínio: {self.rules.domain:<40}  ║",
                f"║     • Fatos: {facts_count:<42}  ║",
                f"║     • Intents: {len(self.rules.intents):<40}  ║",
                f"║     • Regras: {len(self.rules.validation_rules):<41}  ║",
                f"║     • Sinônimos: {len(self.rules.synonyms):<38}  ║",
            ])
            lines.append("╠" + "═" * 60 + "╣")
        
        # Erros
        if self.errors:
            lines.append("║  ❌ ERROS (impedem uso do arquivo):" + " " * 22 + "║")
            lines.append("╟" + "─" * 60 + "╢")
            for error in self.errors:
                for line in error.format().split("\n"):
                    lines.append(f"║  {line:<57} ║")
            lines.append("╠" + "═" * 60 + "╣")
        
        # Warnings
        if self.warnings:
            lines.append("║  ⚠️  AVISOS (recomenda-se corrigir):" + " " * 20 + "║")
            lines.append("╟" + "─" * 60 + "╢")
            for warning in self.warnings:
                for line in warning.format().split("\n"):
                    lines.append(f"║  {line:<57} ║")
            lines.append("╠" + "═" * 60 + "╣")
        
        # Info
        if self.info:
            lines.append("║  ℹ️  INFORMAÇÕES:" + " " * 40 + "║")
            lines.append("╟" + "─" * 60 + "╢")
            for info in self.info:
                for line in info.format().split("\n"):
                    lines.append(f"║  {line:<57} ║")
            lines.append("╠" + "═" * 60 + "╣")
        
        # Resumo
        lines.extend([
            f"║  📊 RESUMO:" + " " * 47 + "║",
            f"║     • {len(self.errors)} erro(s)" + " " * 46 + "║",
            f"║     • {len(self.warnings)} aviso(s)" + " " * 44 + "║",
            "╚" + "═" * 60 + "╝",
        ])
        
        return "\n".join(lines)
    
    def to_dict(self) -> Dict[str, Any]:
        """Serializa para dicionário."""
        return {
            "file_path": self.file_path,
            "is_valid": self.is_valid,
            "errors_count": len(self.errors),
            "warnings_count": len(self.warnings),
            "errors": [{"message": e.message, "line": e.line} for e in self.errors],
            "warnings": [{"message": w.message, "line": w.line} for w in self.warnings],
        }


class DKRValidator:
    """
    Validador de arquivos .rules.
    
    Uso:
        validator = DKRValidator()
        report = validator.validate_file("domain_rules/licencas.rules")
        
        if report.is_valid:
            print("Arquivo OK!")
        else:
            print(report.format())
    """
    
    # Valores válidos
    VALID_CRITICALITY = ["ALTO", "MÉDIO", "MEDIO", "BAIXO"]
    VALID_ACTIONS = ["evitar", "cuidado", "segura", "verificar", "usar"]
    
    def __init__(self):
        """Inicializa o validador."""
        self._parser = DKRParser()
    
    def validate_file(self, file_path: Path | str) -> ValidationReport:
        """
        Valida um arquivo .rules.
        
        Args:
            file_path: Caminho do arquivo
        
        Returns:
            ValidationReport com resultado
        """
        file_path = Path(file_path)
        
        report = ValidationReport(
            file_path=str(file_path),
            is_valid=True,
        )
        
        # Verifica se arquivo existe
        if not file_path.exists():
            report.is_valid = False
            report.errors.append(ValidationIssue(
                level="error",
                message=f"Arquivo não encontrado: {file_path}",
                suggestion="Verifique o caminho do arquivo.",
            ))
            return report
        
        # Verifica extensão
        if file_path.suffix != ".rules":
            report.warnings.append(ValidationIssue(
                level="warning",
                message=f"Extensão inesperada: {file_path.suffix}",
                suggestion="Use a extensão .rules para arquivos de regras.",
            ))
        
        # Tenta parsear
        try:
            rules = self._parser.parse_file(file_path)
            report.rules = rules
        except Exception as e:
            report.is_valid = False
            report.errors.append(ValidationIssue(
                level="error",
                message=f"Erro ao parsear arquivo: {str(e)}",
                suggestion="Verifique a sintaxe do arquivo.",
            ))
            return report
        
        # Validações semânticas
        self._validate_domain(rules, report)
        self._validate_facts(rules, report)
        self._validate_rules(rules, report)
        self._validate_coverage(rules, report)
        
        # Determina validade final
        report.is_valid = len(report.errors) == 0
        
        return report
    
    def _validate_domain(
        self, 
        rules: CompiledRules, 
        report: ValidationReport
    ) -> None:
        """Valida o domínio."""
        if rules.domain == "unknown":
            report.warnings.append(ValidationIssue(
                level="warning",
                message="Domínio não especificado",
                suggestion="Adicione 'DOMÍNIO: Nome do Domínio' no início do arquivo.",
            ))
    
    def _validate_facts(
        self, 
        rules: CompiledRules, 
        report: ValidationReport
    ) -> None:
        """Valida os fatos."""
        total_facts = sum(len(f) for f in rules.facts.values())
        
        if total_facts == 0:
            report.warnings.append(ValidationIssue(
                level="warning",
                message="Nenhum fato definido",
                suggestion="Adicione fatos na seção FATOS CONHECIDOS.",
            ))
            return
        
        # Verifica criticidades
        for level, facts in rules.facts.items():
            if level not in self.VALID_CRITICALITY and level != "OUTRO":
                report.warnings.append(ValidationIssue(
                    level="warning",
                    message=f"Criticidade não reconhecida: '{level}'",
                    suggestion=f"Use: {', '.join(self.VALID_CRITICALITY)}",
                ))
            
            # Verifica fatos duplicados
            names = [f.name.lower() for f in facts]
            seen = set()
            for name in names:
                if name in seen:
                    report.warnings.append(ValidationIssue(
                        level="warning",
                        message=f"Fato duplicado: '{name}'",
                        suggestion="Remova a duplicata ou unifique as informações.",
                    ))
                seen.add(name)
    
    def _validate_rules(
        self, 
        rules: CompiledRules, 
        report: ValidationReport
    ) -> None:
        """Valida as regras de validação."""
        for rule in rules.validation_rules:
            # Regra sem condições
            if not rule.trigger_answer_contains and not rule.trigger_answer_not_contains:
                if not rule.trigger_intent:
                    report.warnings.append(ValidationIssue(
                        level="warning",
                        message=f"Regra '{rule.name}' sem condições de trigger",
                        suggestion="Adicione condições 'E resposta menciona...'",
                    ))
            
            # Regra REPLACE sem template
            if rule.action.value == "replace" and not rule.replacement_template:
                # Verifica se tem fatos para gerar resposta automática
                if not rules.get_critical_facts() and not rules.get_safe_facts():
                    report.warnings.append(ValidationIssue(
                        level="warning",
                        message=f"Regra '{rule.name}' sem template de correção",
                        suggestion="Adicione 'ENTÃO corrigir para:' seguido do texto.",
                    ))
    
    def _validate_coverage(
        self, 
        rules: CompiledRules, 
        report: ValidationReport
    ) -> None:
        """Valida cobertura das regras."""
        has_alto = len(rules.get_critical_facts()) > 0
        has_baixo = len(rules.get_safe_facts()) > 0
        
        if has_alto and not has_baixo:
            report.info.append(ValidationIssue(
                level="info",
                message="Apenas fatos de criticidade ALTO definidos",
                suggestion="Considere adicionar fatos BAIXO para perguntas sobre segurança.",
            ))
        
        if has_baixo and not has_alto:
            report.info.append(ValidationIssue(
                level="info",
                message="Apenas fatos de criticidade BAIXO definidos",
                suggestion="Considere adicionar fatos ALTO para perguntas sobre riscos.",
            ))
        
        # Verifica se há intents sem expansão
        for intent_name in rules.intents:
            if intent_name not in rules.expansions:
                report.info.append(ValidationIssue(
                    level="info",
                    message=f"Intent '{intent_name}' sem expansão de query",
                    suggestion="Adicione termos de expansão para melhorar retrieval.",
                ))
    
    def validate_content(self, content: str) -> ValidationReport:
        """
        Valida conteúdo de regras (sem arquivo).
        
        Args:
            content: Conteúdo do arquivo .rules
        
        Returns:
            ValidationReport
        """
        report = ValidationReport(
            file_path="<inline>",
            is_valid=True,
        )
        
        try:
            rules = self._parser.parse_content(content)
            report.rules = rules
            
            self._validate_domain(rules, report)
            self._validate_facts(rules, report)
            self._validate_rules(rules, report)
            self._validate_coverage(rules, report)
            
        except Exception as e:
            report.is_valid = False
            report.errors.append(ValidationIssue(
                level="error",
                message=f"Erro de parsing: {str(e)}",
            ))
        
        report.is_valid = len(report.errors) == 0
        return report

