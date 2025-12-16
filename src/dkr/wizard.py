"""
Assistente Guiado para Criação de Regras DKR.

Wizard interativo que guia o usuário na criação de 
arquivos .rules sem necessidade de conhecer a sintaxe.

Funciona 100% OFFLINE usando templates e prompts guiados.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional, Dict, Any
from datetime import datetime


@dataclass
class WizardFact:
    """Fato coletado pelo wizard."""
    name: str
    criticality: str
    reason: str = ""
    action: str = ""


@dataclass
class WizardIntent:
    """Intent coletado pelo wizard."""
    name: str
    patterns: List[str] = field(default_factory=list)
    expected: List[str] = field(default_factory=list)


@dataclass
class WizardRule:
    """Regra coletada pelo wizard."""
    trigger_pattern: str
    answer_contains: List[str] = field(default_factory=list)
    answer_not_contains: List[str] = field(default_factory=list)
    correction: str = ""


@dataclass
class WizardData:
    """Dados coletados pelo wizard."""
    domain: str = ""
    facts: List[WizardFact] = field(default_factory=list)
    intents: List[WizardIntent] = field(default_factory=list)
    rules: List[WizardRule] = field(default_factory=list)
    synonyms: Dict[str, List[str]] = field(default_factory=dict)


class DKRWizard:
    """
    Assistente guiado para criação de regras DKR.
    
    Uso:
        wizard = DKRWizard()
        wizard.run()  # Modo interativo
        # ou
        wizard.generate_from_template("licencas")  # Template pré-definido
    """
    
    # Templates pré-definidos
    TEMPLATES = {
        "licencas": {
            "domain": "Licenças de Software",
            "description": "Template para documentos de licenças open source",
            "facts_prompt": "Quais licenças existem e qual a criticidade de cada uma?",
            "sample_facts": [
                ("AGPL-3.0", "ALTO", "Copyleft forte com obrigações SaaS"),
                ("MIT", "BAIXO", "Licença permissiva"),
            ],
            "intents": ["criticidade_alta", "criticidade_baixa", "compatibilidade"],
        },
        "contratos": {
            "domain": "Análise de Contratos",
            "description": "Template para contratos e documentos jurídicos",
            "facts_prompt": "Quais cláusulas são importantes e qual o risco de cada uma?",
            "sample_facts": [
                ("Cláusula de Rescisão", "ALTO", "Pode ter multas pesadas"),
                ("Prazo de Vigência", "MÉDIO", "Importante verificar renovação"),
            ],
            "intents": ["risco_alto", "obrigacoes", "prazos"],
        },
        "inventario": {
            "domain": "Escritura de Inventário",
            "description": "Template para documentos de inventário/herança",
            "facts_prompt": "Quais elementos são importantes no inventário?",
            "sample_facts": [
                ("Inventariante", "ALTO", "Responsável legal pelo processo"),
                ("Quinhão", "MÉDIO", "Percentual de cada herdeiro"),
            ],
            "intents": ["herdeiros", "bens", "divisao"],
        },
        "geral": {
            "domain": "Domínio Personalizado",
            "description": "Template em branco para qualquer domínio",
            "facts_prompt": "Quais são os conceitos importantes do seu domínio?",
            "sample_facts": [],
            "intents": [],
        },
    }
    
    def __init__(self, output_dir: Path = Path("domain_rules")):
        """
        Inicializa o wizard.
        
        Args:
            output_dir: Diretório onde salvar os arquivos .rules
        """
        self.output_dir = output_dir
        self.data = WizardData()
    
    def run(self) -> Optional[Path]:
        """
        Executa o wizard interativo.
        
        Returns:
            Path do arquivo criado ou None se cancelado
        """
        print("\n" + "═" * 60)
        print("  🧙 ASSISTENTE DE CRIAÇÃO DE REGRAS DKR")
        print("═" * 60)
        print("\nEste assistente vai guiar você na criação de um arquivo")
        print("de regras (.rules) para melhorar a acurácia do Q&A.\n")
        print("Digite 'cancelar' a qualquer momento para sair.\n")
        
        try:
            # 1. Escolher template
            template = self._choose_template()
            if not template:
                return None
            
            # 2. Definir domínio
            domain = self._get_domain(template)
            if not domain:
                return None
            self.data.domain = domain
            
            # 3. Coletar fatos
            print("\n" + "─" * 60)
            print("  📚 FATOS CONHECIDOS")
            print("─" * 60)
            self._collect_facts(template)
            
            # 4. Definir intents (opcional)
            print("\n" + "─" * 60)
            print("  🎯 PADRÕES DE INTENÇÃO")
            print("─" * 60)
            self._collect_intents(template)
            
            # 5. Criar regras de validação
            print("\n" + "─" * 60)
            print("  ⚖️  REGRAS DE VALIDAÇÃO")
            print("─" * 60)
            self._collect_rules()
            
            # 6. Gerar arquivo
            output_path = self._generate_file()
            
            print("\n" + "═" * 60)
            print(f"  ✅ Arquivo criado: {output_path}")
            print("═" * 60)
            
            return output_path
            
        except KeyboardInterrupt:
            print("\n\n[Cancelado pelo usuário]")
            return None
    
    def _input(self, prompt: str, default: str = "") -> Optional[str]:
        """Input com suporte a cancelamento."""
        try:
            if default:
                value = input(f"{prompt} [{default}]: ").strip()
                value = value or default
            else:
                value = input(f"{prompt}: ").strip()
            
            if value.lower() == "cancelar":
                raise KeyboardInterrupt()
            
            return value
        except EOFError:
            raise KeyboardInterrupt()
    
    def _choose_template(self) -> Optional[str]:
        """Escolhe um template base."""
        print("Templates disponíveis:\n")
        
        for i, (key, info) in enumerate(self.TEMPLATES.items(), 1):
            print(f"  {i}. {info['domain']}")
            print(f"     {info['description']}")
            print()
        
        choice = self._input("Escolha um template (número)")
        
        try:
            idx = int(choice) - 1
            if 0 <= idx < len(self.TEMPLATES):
                return list(self.TEMPLATES.keys())[idx]
        except ValueError:
            pass
        
        # Tenta por nome
        if choice in self.TEMPLATES:
            return choice
        
        print("\n⚠️  Opção inválida, usando template 'geral'")
        return "geral"
    
    def _get_domain(self, template_key: str) -> Optional[str]:
        """Define o nome do domínio."""
        template = self.TEMPLATES[template_key]
        default = template["domain"]
        
        print(f"\nNome do domínio (ex: {default})")
        domain = self._input("Domínio", default)
        
        return domain
    
    def _collect_facts(self, template_key: str) -> None:
        """Coleta fatos do domínio."""
        template = self.TEMPLATES[template_key]
        
        print(f"\n{template['facts_prompt']}\n")
        
        if template["sample_facts"]:
            print("Exemplos:")
            for name, crit, reason in template["sample_facts"]:
                print(f"  • {name} (criticidade {crit}): {reason}")
            print()
        
        print("Para cada fato, informe: nome, criticidade (ALTO/MÉDIO/BAIXO), motivo")
        print("Digite 'pronto' quando terminar.\n")
        
        while True:
            name = self._input("Nome do fato (ou 'pronto')")
            if not name or name.lower() == "pronto":
                break
            
            print("  Criticidade:")
            print("    1. ALTO - Requer atenção especial")
            print("    2. MÉDIO - Verificar caso a caso")
            print("    3. BAIXO - Geralmente seguro")
            
            crit_choice = self._input("  Escolha (1/2/3)", "1")
            criticality = {"1": "ALTO", "2": "MÉDIO", "3": "BAIXO"}.get(crit_choice, "ALTO")
            
            reason = self._input("  Motivo (opcional)", "")
            action = self._input("  Ação recomendada (opcional)", "")
            
            self.data.facts.append(WizardFact(
                name=name,
                criticality=criticality,
                reason=reason,
                action=action
            ))
            
            print(f"  ✓ Fato adicionado: {name} ({criticality})\n")
    
    def _collect_intents(self, template_key: str) -> None:
        """Coleta intents (opcional)."""
        template = self.TEMPLATES[template_key]
        
        print("\nIntents são padrões de pergunta que o sistema reconhece.")
        print("O sistema já gera intents automáticos baseados nos fatos.\n")
        
        if template["intents"]:
            print(f"Intents sugeridos: {', '.join(template['intents'])}")
        
        add_custom = self._input("\nAdicionar intents personalizados? (s/n)", "n")
        
        if add_custom.lower() != "s":
            return
        
        print("\nPara cada intent, informe: nome e padrões de texto")
        print("Digite 'pronto' quando terminar.\n")
        
        while True:
            name = self._input("Nome do intent (ou 'pronto')")
            if not name or name.lower() == "pronto":
                break
            
            # Normaliza nome
            name = re.sub(r'[^\w]', '_', name.lower())
            
            print("  Quais frases indicam esta intenção?")
            print("  (separe por vírgula)")
            
            patterns_str = self._input("  Padrões")
            patterns = [p.strip() for p in patterns_str.split(",") if p.strip()]
            
            if patterns:
                self.data.intents.append(WizardIntent(name=name, patterns=patterns))
                print(f"  ✓ Intent adicionado: {name}\n")
    
    def _collect_rules(self) -> None:
        """Coleta regras de validação."""
        print("\nRegras de validação corrigem respostas incorretas.")
        print("Exemplo: Se pergunta 'mais crítico' e resposta menciona 'MIT',")
        print("         corrigir para mencionar 'AGPL'.\n")
        
        add_rules = self._input("Adicionar regras de validação? (s/n)", "s")
        
        if add_rules.lower() != "s":
            # Gera regras automáticas baseadas nos fatos
            self._generate_auto_rules()
            return
        
        print("\nPara cada regra, defina: quando e como corrigir")
        print("Digite 'pronto' quando terminar.\n")
        
        while True:
            print("Quando o usuário pergunta sobre:")
            trigger = self._input("  Padrão de pergunta (ou 'pronto')")
            if not trigger or trigger.lower() == "pronto":
                break
            
            print("  E a resposta menciona incorretamente:")
            contains_str = self._input("  Termos incorretos (separados por vírgula)")
            contains = [t.strip() for t in contains_str.split(",") if t.strip()]
            
            print("  Mas NÃO menciona o correto:")
            not_contains_str = self._input("  Termos esperados (separados por vírgula)", "")
            not_contains = [t.strip() for t in not_contains_str.split(",") if t.strip()]
            
            print("  Texto de correção:")
            correction = self._input("  Resposta corrigida")
            
            self.data.rules.append(WizardRule(
                trigger_pattern=trigger,
                answer_contains=contains,
                answer_not_contains=not_contains,
                correction=correction
            ))
            
            print("  ✓ Regra adicionada\n")
    
    def _generate_auto_rules(self) -> None:
        """Gera regras automáticas baseadas nos fatos."""
        # Encontra fatos de alto e baixo risco
        high_risk = [f for f in self.data.facts if f.criticality == "ALTO"]
        low_risk = [f for f in self.data.facts if f.criticality == "BAIXO"]
        
        if high_risk and low_risk:
            # Regra: corrige se pergunta "mais crítico" e menciona low_risk
            for low in low_risk[:2]:  # Máximo 2 regras automáticas
                high = high_risk[0]
                self.data.rules.append(WizardRule(
                    trigger_pattern="mais crítica",
                    answer_contains=[low.name],
                    answer_not_contains=[high.name],
                    correction=f"O mais crítico é **{high.name}** (criticidade ALTO). {high.reason}"
                ))
            
            print(f"  ✓ {len(self.data.rules)} regra(s) automática(s) gerada(s)")
    
    def _generate_file(self) -> Path:
        """Gera o arquivo .rules."""
        # Cria diretório se necessário
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Nome do arquivo
        safe_name = re.sub(r'[^\w]', '_', self.data.domain.lower())
        output_path = self.output_dir / f"{safe_name}.rules"
        
        # Gera conteúdo
        content = self._format_rules_file()
        
        # Salva
        output_path.write_text(content, encoding="utf-8")
        
        return output_path
    
    def _format_rules_file(self) -> str:
        """Formata o conteúdo do arquivo .rules."""
        timestamp = datetime.now().strftime("%d/%m/%Y %H:%M")
        
        lines = [
            "# " + "═" * 58,
            f"#  REGRAS DE DOMÍNIO: {self.data.domain}",
            "#",
            f"#  Criado por: DKR Wizard",
            f"#  Data: {timestamp}",
            "# " + "═" * 58,
            "",
            f"DOMÍNIO: {self.data.domain}",
            "",
        ]
        
        # Fatos
        if self.data.facts:
            lines.extend([
                "─" * 60,
                "FATOS CONHECIDOS:",
                "─" * 60,
                "",
            ])
            
            for fact in self.data.facts:
                lines.append(f"A/O {fact.name} tem criticidade {fact.criticality}.")
                if fact.reason:
                    lines.append(f"  Motivo: {fact.reason}")
                if fact.action:
                    lines.append(f"  Ação: {fact.action}")
                lines.append("")
        
        # Intents
        if self.data.intents:
            lines.extend([
                "─" * 60,
                "PADRÕES DE INTENÇÃO:",
                "─" * 60,
                "",
            ])
            
            for intent in self.data.intents:
                lines.append(f"{intent.name}:")
                for pattern in intent.patterns:
                    lines.append(f'  - "{pattern}"')
                if intent.expected:
                    expected_str = ', '.join(f'"{e}"' for e in intent.expected)
                    lines.append(f"  Resposta deve conter: {expected_str}")
                lines.append("")
        
        # Regras
        if self.data.rules:
            lines.extend([
                "─" * 60,
                "REGRAS DE VALIDAÇÃO:",
                "─" * 60,
                "",
            ])
            
            for rule in self.data.rules:
                lines.append(f'QUANDO usuário pergunta "{rule.trigger_pattern}"')
                
                for term in rule.answer_contains:
                    lines.append(f'  E resposta menciona "{term}"')
                
                for term in rule.answer_not_contains:
                    lines.append(f'  E resposta NÃO menciona "{term}"')
                
                lines.append("ENTÃO corrigir para:")
                for line in rule.correction.split("\n"):
                    lines.append(f"  {line}")
                lines.append("")
        
        # Sinônimos
        if self.data.synonyms:
            lines.extend([
                "─" * 60,
                "SINÔNIMOS:",
                "─" * 60,
                "",
            ])
            
            for term, alternatives in self.data.synonyms.items():
                alts_str = ", ".join(f'"{a}"' for a in alternatives)
                lines.append(f'"{term}" também pode ser: {alts_str}')
            lines.append("")
        
        return "\n".join(lines)
    
    def generate_from_template(self, template_key: str, domain: str = "") -> Path:
        """
        Gera arquivo a partir de um template.
        
        Args:
            template_key: Nome do template
            domain: Nome do domínio (opcional)
        
        Returns:
            Path do arquivo gerado
        """
        if template_key not in self.TEMPLATES:
            raise ValueError(f"Template não encontrado: {template_key}")
        
        template = self.TEMPLATES[template_key]
        
        self.data = WizardData()
        self.data.domain = domain or template["domain"]
        
        # Adiciona fatos de exemplo
        for name, crit, reason in template.get("sample_facts", []):
            self.data.facts.append(WizardFact(
                name=name,
                criticality=crit,
                reason=reason
            ))
        
        # Gera regras automáticas
        self._generate_auto_rules()
        
        return self._generate_file()


def run_wizard(output_dir: Path = Path("domain_rules")) -> Optional[Path]:
    """Função de conveniência para executar o wizard."""
    wizard = DKRWizard(output_dir)
    return wizard.run()

