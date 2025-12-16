"""
REPL Interativo para DKR.

Permite testar regras de forma interativa,
simular perguntas e respostas, e debugar
o comportamento do sistema.
"""

from __future__ import annotations

import cmd
import logging
from pathlib import Path
from typing import Optional, List

from .engine import DKREngine
from .parser import DKRParser
from .validator import DKRValidator

logger = logging.getLogger(__name__)


class DKREPL(cmd.Cmd):
    """
    REPL interativo para testar regras DKR.
    
    Uso:
        repl = DKREPL("domain_rules/licencas_software.rules")
        repl.cmdloop()
    """
    
    intro = """
╔═══════════════════════════════════════════════════════════╗
║           DKR REPL - Domain Knowledge Rules               ║
║                 Modo Interativo de Teste                  ║
╠═══════════════════════════════════════════════════════════╣
║  Comandos:                                                ║
║    ask <pergunta>        - Analisa uma pergunta           ║
║    test <pergunta>       - Testa com resposta simulada    ║
║    intent <texto>        - Detecta intent do texto        ║
║    expand <query>        - Mostra expansão de query       ║
║    facts [nivel]         - Lista fatos conhecidos         ║
║    rules                 - Lista regras de validação      ║
║    reload                - Recarrega arquivo .rules       ║
║    help                  - Mostra ajuda                   ║
║    exit / quit           - Sai do REPL                    ║
╚═══════════════════════════════════════════════════════════╝
"""
    
    prompt = "\n[DKR] > "
    
    def __init__(
        self,
        rules_path: Optional[Path | str] = None,
        stdin=None,
        stdout=None
    ):
        """
        Inicializa o REPL.
        
        Args:
            rules_path: Caminho do arquivo .rules
        """
        super().__init__(stdin=stdin, stdout=stdout)
        
        self.rules_path: Optional[Path] = None
        self.engine: Optional[DKREngine] = None
        self.last_answer: str = ""
        
        if rules_path:
            self.load_rules(rules_path)
    
    def load_rules(self, rules_path: Path | str) -> bool:
        """Carrega arquivo de regras."""
        self.rules_path = Path(rules_path)
        
        if not self.rules_path.exists():
            self._print(f"❌ Arquivo não encontrado: {self.rules_path}")
            return False
        
        try:
            self.engine = DKREngine(self.rules_path)
            domain = self.engine.rules.domain if self.engine.rules else "?"
            self._print(f"✅ Carregado: {self.rules_path.name}")
            self._print(f"   Domínio: {domain}")
            
            if self.engine.rules:
                facts_count = sum(len(f) for f in self.engine.rules.facts.values())
                rules_count = len(self.engine.rules.validation_rules)
                self._print(f"   Fatos: {facts_count} | Regras: {rules_count}")
            
            return True
        except Exception as e:
            self._print(f"❌ Erro ao carregar: {e}")
            return False
    
    def _print(self, text: str) -> None:
        """Imprime texto no stdout."""
        self.stdout.write(text + "\n")
    
    def _ensure_loaded(self) -> bool:
        """Verifica se há regras carregadas."""
        if not self.engine or not self.engine.rules:
            self._print("⚠️  Nenhum arquivo .rules carregado")
            self._print("   Use: load <caminho>")
            return False
        return True
    
    # ========================================
    # Comandos
    # ========================================
    
    def do_load(self, arg: str) -> None:
        """Carrega um arquivo .rules: load <caminho>"""
        if not arg:
            self._print("Uso: load <caminho_do_arquivo.rules>")
            return
        
        self.load_rules(arg)
    
    def do_reload(self, arg: str) -> None:
        """Recarrega o arquivo .rules atual"""
        if not self.rules_path:
            self._print("⚠️  Nenhum arquivo carregado para recarregar")
            return
        
        self.load_rules(self.rules_path)
    
    def do_ask(self, arg: str) -> None:
        """Analisa uma pergunta: ask <pergunta>"""
        if not arg:
            self._print("Uso: ask <pergunta>")
            return
        
        if not self._ensure_loaded():
            return
        
        self._print(f"\n📝 Pergunta: {arg}")
        self._print("─" * 50)
        
        # Detecta intent
        explanation = self.engine.explain_intent(arg)
        self._print(explanation)
        
        # Mostra expansão
        expanded = self.engine.expand_query(arg)
        if expanded != arg:
            self._print(f"\n🔍 Query expandida:")
            self._print(f"   {expanded}")
    
    def do_test(self, arg: str) -> None:
        """Testa pergunta com resposta simulada: test <pergunta>"""
        if not arg:
            self._print("Uso: test <pergunta>")
            self._print("     (será solicitada a resposta simulada)")
            return
        
        if not self._ensure_loaded():
            return
        
        question = arg
        
        # Solicita resposta
        self._print(f"\n📝 Pergunta: {question}")
        self.stdout.write("💬 Resposta simulada: ")
        self.stdout.flush()
        
        try:
            answer = self.stdin.readline().strip()
        except (EOFError, KeyboardInterrupt):
            self._print("\n[Cancelado]")
            return
        
        if not answer:
            self._print("⚠️  Resposta vazia")
            return
        
        self.last_answer = answer
        
        # Processa
        result = self.engine.process(question, answer)
        
        self._print("\n" + "─" * 50)
        self._print("  RESULTADO DO PROCESSAMENTO")
        self._print("─" * 50)
        
        # Intent
        if result.detected_intent:
            bar = "█" * int(result.intent_confidence * 10)
            bar += "░" * (10 - len(bar))
            self._print(f"🎯 Intent: {result.detected_intent} [{bar}] {result.intent_confidence:.0%}")
        else:
            self._print("🎯 Intent: Nenhum detectado")
        
        # Regras
        self._print(f"📋 Regras avaliadas: {result.rules_evaluated}")
        
        if result.rules_triggered:
            self._print(f"⚡ Regras ativadas:")
            for rule in result.rules_triggered:
                self._print(f"   • {rule}")
        
        # Correção
        if result.was_corrected:
            self._print(f"\n✅ RESPOSTA CORRIGIDA")
            self._print(f"   Motivo: {result.correction_reason}")
            self._print(f"\n   Nova resposta:")
            for line in result.final_answer.split("\n")[:5]:
                self._print(f"   {line}")
            if len(result.final_answer.split("\n")) > 5:
                self._print("   ...")
        else:
            self._print(f"\n⏸️  Resposta mantida (sem correção)")
        
        self._print(f"\n⏱️  Tempo: {result.processing_time_ms:.2f}ms")
        self._print("─" * 50)
    
    def do_intent(self, arg: str) -> None:
        """Detecta intent de um texto: intent <texto>"""
        if not arg:
            self._print("Uso: intent <texto>")
            return
        
        if not self._ensure_loaded():
            return
        
        explanation = self.engine.explain_intent(arg)
        self._print(explanation)
    
    def do_expand(self, arg: str) -> None:
        """Mostra expansão de query: expand <query>"""
        if not arg:
            self._print("Uso: expand <query>")
            return
        
        if not self._ensure_loaded():
            return
        
        expanded = self.engine.expand_query(arg)
        
        self._print(f"\n📝 Original: {arg}")
        
        if expanded != arg:
            self._print(f"🔍 Expandida: {expanded}")
            
            # Mostra termos adicionados
            added = expanded.replace(arg, "").strip()
            self._print(f"   Termos adicionados: {added}")
        else:
            self._print("   (sem expansão)")
    
    def do_facts(self, arg: str) -> None:
        """Lista fatos conhecidos: facts [ALTO|MEDIO|BAIXO]"""
        if not self._ensure_loaded():
            return
        
        level = arg.upper() if arg else None
        
        self._print("\n📚 FATOS CONHECIDOS")
        self._print("─" * 50)
        
        for crit, facts in self.engine.rules.facts.items():
            if level and crit != level:
                continue
            
            self._print(f"\n[{crit}]")
            for fact in facts:
                self._print(f"  • {fact.name}")
                if fact.reason:
                    self._print(f"    Motivo: {fact.reason}")
    
    def do_rules(self, arg: str) -> None:
        """Lista regras de validação"""
        if not self._ensure_loaded():
            return
        
        self._print("\n⚖️  REGRAS DE VALIDAÇÃO")
        self._print("─" * 50)
        
        for rule in self.engine.rules.validation_rules:
            self._print(f"\n  {rule.name}:")
            self._print(f"    Intent: {rule.trigger_intent or 'qualquer'}")
            
            if rule.trigger_answer_contains:
                self._print(f"    SE contém: {rule.trigger_answer_contains}")
            if rule.trigger_answer_not_contains:
                self._print(f"    SE NÃO contém: {rule.trigger_answer_not_contains}")
            
            self._print(f"    Ação: {rule.action.value}")
    
    def do_info(self, arg: str) -> None:
        """Mostra informações do arquivo carregado"""
        if not self._ensure_loaded():
            return
        
        rules = self.engine.rules
        
        self._print(f"\n📄 Arquivo: {self.rules_path}")
        self._print(f"   Domínio: {rules.domain}")
        self._print(f"   Hash: {rules.source_hash}")
        self._print(f"\n   Estatísticas:")
        self._print(f"   • Fatos: {sum(len(f) for f in rules.facts.values())}")
        self._print(f"   • Intents: {len(rules.intents)}")
        self._print(f"   • Regras: {len(rules.validation_rules)}")
        self._print(f"   • Sinônimos: {len(rules.synonyms)}")
    
    def do_validate(self, arg: str) -> None:
        """Valida o arquivo carregado"""
        if not self.rules_path:
            self._print("⚠️  Nenhum arquivo carregado")
            return
        
        validator = DKRValidator()
        report = validator.validate_file(self.rules_path)
        self._print(report.format())
    
    def do_exit(self, arg: str) -> bool:
        """Sai do REPL"""
        self._print("\n👋 Até logo!")
        return True
    
    def do_quit(self, arg: str) -> bool:
        """Sai do REPL"""
        return self.do_exit(arg)
    
    def do_EOF(self, arg: str) -> bool:
        """Sai do REPL (Ctrl+D)"""
        self._print("")
        return self.do_exit(arg)
    
    def default(self, line: str) -> None:
        """Comando desconhecido."""
        self._print(f"❓ Comando desconhecido: {line}")
        self._print("   Digite 'help' para ver os comandos disponíveis")
    
    def emptyline(self) -> None:
        """Linha vazia."""
        pass


def run_repl(rules_path: Optional[Path | str] = None) -> None:
    """
    Inicia o REPL interativo.
    
    Args:
        rules_path: Caminho do arquivo .rules (opcional)
    """
    repl = DKREPL(rules_path)
    try:
        repl.cmdloop()
    except KeyboardInterrupt:
        print("\n\n👋 Até logo!")

