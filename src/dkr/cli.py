"""
CLI para o módulo DKR.

Comandos disponíveis:
- dkr validate <arquivo.rules>  - Valida sintaxe e semântica
- dkr test <arquivo.rules>      - Testa regras interativamente
- dkr info <arquivo.rules>      - Exibe informações do arquivo
- dkr list                      - Lista arquivos .rules disponíveis
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path
from typing import List, Optional

from .parser import DKRParser
from .engine import DKREngine
from .validator import DKRValidator
from .cache import get_dkr_cache

logger = logging.getLogger(__name__)


class DKRCli:
    """Interface de linha de comando para DKR."""
    
    def __init__(self, rules_dir: Path = Path("domain_rules")):
        """
        Inicializa a CLI.
        
        Args:
            rules_dir: Diretório padrão dos arquivos .rules
        """
        self.rules_dir = rules_dir
        self.parser = DKRParser()
        self.validator = DKRValidator()
    
    def run(self, args: Optional[List[str]] = None) -> int:
        """
        Executa a CLI.
        
        Args:
            args: Argumentos (usa sys.argv se None)
        
        Returns:
            Código de saída (0 = sucesso)
        """
        parser = self._create_parser()
        parsed = parser.parse_args(args)
        
        if not hasattr(parsed, 'func'):
            parser.print_help()
            return 1
        
        try:
            return parsed.func(parsed)
        except Exception as e:
            print(f"\n❌ Erro: {e}")
            if parsed.verbose:
                import traceback
                traceback.print_exc()
            return 1
    
    def _create_parser(self) -> argparse.ArgumentParser:
        """Cria o parser de argumentos."""
        parser = argparse.ArgumentParser(
            prog="dkr",
            description="Gerenciador de Domain Knowledge Rules",
            formatter_class=argparse.RawDescriptionHelpFormatter,
            epilog="""
Exemplos:
  dkr validate domain_rules/licencas_software.rules
  dkr test domain_rules/licencas_software.rules
  dkr info domain_rules/licencas_software.rules
  dkr list
            """
        )
        
        parser.add_argument(
            "-v", "--verbose",
            action="store_true",
            help="Modo verboso"
        )
        
        subparsers = parser.add_subparsers(title="Comandos")
        
        # Comando: validate
        validate_parser = subparsers.add_parser(
            "validate",
            help="Valida um arquivo .rules"
        )
        validate_parser.add_argument(
            "file",
            type=Path,
            help="Arquivo .rules para validar"
        )
        validate_parser.set_defaults(func=self._cmd_validate)
        
        # Comando: test
        test_parser = subparsers.add_parser(
            "test",
            help="Testa regras interativamente"
        )
        test_parser.add_argument(
            "file",
            type=Path,
            help="Arquivo .rules para testar"
        )
        test_parser.add_argument(
            "-q", "--question",
            type=str,
            help="Pergunta para testar (modo não-interativo)"
        )
        test_parser.add_argument(
            "-a", "--answer",
            type=str,
            help="Resposta simulada para testar"
        )
        test_parser.set_defaults(func=self._cmd_test)
        
        # Comando: info
        info_parser = subparsers.add_parser(
            "info",
            help="Exibe informações de um arquivo .rules"
        )
        info_parser.add_argument(
            "file",
            type=Path,
            help="Arquivo .rules"
        )
        info_parser.set_defaults(func=self._cmd_info)
        
        # Comando: list
        list_parser = subparsers.add_parser(
            "list",
            help="Lista arquivos .rules disponíveis"
        )
        list_parser.add_argument(
            "-d", "--dir",
            type=Path,
            default=self.rules_dir,
            help=f"Diretório para buscar (padrão: {self.rules_dir})"
        )
        list_parser.set_defaults(func=self._cmd_list)
        
        # Comando: explain
        explain_parser = subparsers.add_parser(
            "explain",
            help="Explica como uma pergunta seria processada"
        )
        explain_parser.add_argument(
            "file",
            type=Path,
            help="Arquivo .rules"
        )
        explain_parser.add_argument(
            "-q", "--question",
            type=str,
            required=True,
            help="Pergunta para analisar"
        )
        explain_parser.set_defaults(func=self._cmd_explain)
        
        return parser
    
    def _cmd_validate(self, args) -> int:
        """Comando: validate."""
        print(f"\n🔍 Validando: {args.file}\n")
        
        report = self.validator.validate_file(args.file)
        print(report.format())
        
        return 0 if report.is_valid else 1
    
    def _cmd_test(self, args) -> int:
        """Comando: test."""
        print(f"\n🧪 Testando regras: {args.file}\n")
        
        engine = DKREngine(args.file)
        
        if args.question and args.answer:
            # Modo não-interativo
            return self._test_single(engine, args.question, args.answer)
        else:
            # Modo interativo
            return self._test_interactive(engine)
    
    def _test_single(
        self, 
        engine: DKREngine, 
        question: str, 
        answer: str
    ) -> int:
        """Testa uma única pergunta/resposta."""
        result = engine.process(question, answer)
        
        self._print_result(result)
        
        return 0
    
    def _test_interactive(self, engine: DKREngine) -> int:
        """Modo de teste interativo."""
        print("Modo interativo de teste de regras")
        print("Digite 'sair' para encerrar\n")
        
        while True:
            try:
                question = input("📝 Pergunta: ").strip()
                if question.lower() in ["sair", "exit", "quit"]:
                    break
                
                if not question:
                    continue
                
                answer = input("💬 Resposta (simulada): ").strip()
                if not answer:
                    continue
                
                result = engine.process(question, answer)
                self._print_result(result)
                print()
                
            except KeyboardInterrupt:
                print("\n")
                break
            except EOFError:
                break
        
        print("👋 Encerrando...")
        return 0
    
    def _print_result(self, result) -> None:
        """Imprime resultado do processamento DKR."""
        print("\n" + "─" * 60)
        print("  RESULTADO DO PROCESSAMENTO DKR")
        print("─" * 60)
        
        # Intent
        if result.detected_intent:
            conf_bar = "█" * int(result.intent_confidence * 10)
            conf_bar += "░" * (10 - len(conf_bar))
            print(f"🎯 Intent: {result.detected_intent} [{conf_bar}] {result.intent_confidence:.0%}")
        else:
            print("🎯 Intent: Nenhum detectado")
        
        # Query expansion
        if result.query_expanded:
            print(f"🔍 Query expandida: Sim")
            print(f"   Termos: {result.expansion_terms}")
        
        # Normalização
        if result.was_normalized:
            print(f"🔧 Termos normalizados: Sim")
            for norm in result.normalizations_applied:
                print(f"   • {norm}")
        
        # Regras
        print(f"📋 Regras avaliadas: {result.rules_evaluated}")
        
        if result.rules_triggered:
            print(f"⚡ Regras ativadas: {len(result.rules_triggered)}")
            for rule in result.rules_triggered:
                print(f"   • {rule}")
        
        # Correção
        if result.was_corrected:
            print(f"\n✅ RESPOSTA CORRIGIDA")
            print(f"   Motivo: {result.correction_reason}")
            print(f"\n📄 Nova resposta:")
            print("   " + result.final_answer.replace("\n", "\n   "))
        else:
            print(f"\n⏸️  Resposta mantida (sem correção necessária)")
        
        print("─" * 60)
    
    def _cmd_info(self, args) -> int:
        """Comando: info."""
        print(f"\n📄 Informações: {args.file}\n")
        
        rules = self.parser.parse_file(args.file)
        
        print(f"╔{'═' * 58}╗")
        print(f"║  Domínio: {rules.domain:<46} ║")
        print(f"╠{'═' * 58}╣")
        
        # Fatos por criticidade
        print(f"║  📊 FATOS CONHECIDOS{' ' * 37}║")
        for level, facts in rules.facts.items():
            print(f"║     {level}: {len(facts)} fato(s){' ' * (47 - len(level) - len(str(len(facts))))}║")
            for fact in facts[:3]:  # Mostra primeiros 3
                name = fact.name[:40]
                print(f"║       • {name:<46}  ║")
            if len(facts) > 3:
                print(f"║       ... e mais {len(facts) - 3}{' ' * (38 - len(str(len(facts) - 3)))}║")
        
        print(f"╠{'═' * 58}╣")
        
        # Intents
        print(f"║  🎯 INTENTS: {len(rules.intents)}{' ' * (43 - len(str(len(rules.intents))))}║")
        for name, intent in rules.intents.items():
            patterns_count = len(intent.patterns)
            print(f"║     • {name}: {patterns_count} padrão(ões){' ' * (40 - len(name) - len(str(patterns_count)))}║")
        
        print(f"╠{'═' * 58}╣")
        
        # Regras de validação
        print(f"║  ⚖️  REGRAS DE VALIDAÇÃO: {len(rules.validation_rules)}{' ' * (30 - len(str(len(rules.validation_rules))))}║")
        for rule in rules.validation_rules[:5]:
            action = rule.action.value
            print(f"║     • {rule.name}: {action}{' ' * (42 - len(rule.name) - len(action))}║")
        if len(rules.validation_rules) > 5:
            print(f"║     ... e mais {len(rules.validation_rules) - 5}{' ' * (39 - len(str(len(rules.validation_rules) - 5)))}║")
        
        print(f"╠{'═' * 58}╣")
        
        # Normalizações
        print(f"║  🔧 NORMALIZAÇÕES: {len(rules.normalizations)}{' ' * (37 - len(str(len(rules.normalizations))))}║")
        for norm in rules.normalizations[:3]:
            desc = f'"{norm.original}" → "{norm.normalized}"'
            if len(desc) > 46:
                desc = desc[:43] + "..."
            print(f"║     • {desc}{' ' * (49 - len(desc))}║")
        if len(rules.normalizations) > 3:
            print(f"║     ... e mais {len(rules.normalizations) - 3}{' ' * (39 - len(str(len(rules.normalizations) - 3)))}║")
        
        print(f"╠{'═' * 58}╣")
        
        # Sinônimos
        print(f"║  🔄 SINÔNIMOS: {len(rules.synonyms)}{' ' * (41 - len(str(len(rules.synonyms))))}║")
        
        print(f"╚{'═' * 58}╝")
        
        return 0
    
    def _cmd_list(self, args) -> int:
        """Comando: list."""
        rules_dir = args.dir
        
        print(f"\n📁 Arquivos .rules em: {rules_dir}\n")
        
        if not rules_dir.exists():
            print(f"   ⚠️  Diretório não existe")
            return 1
        
        files = list(rules_dir.glob("*.rules"))
        
        if not files:
            print(f"   📭 Nenhum arquivo .rules encontrado")
            return 0
        
        print(f"{'─' * 70}")
        print(f"{'Arquivo':<30} {'Domínio':<25} {'Fatos':<6} {'Regras':<6}")
        print(f"{'─' * 70}")
        
        for file in sorted(files):
            try:
                rules = self.parser.parse_file(file)
                facts_count = sum(len(f) for f in rules.facts.values())
                rules_count = len(rules.validation_rules)
                domain = rules.domain[:23] + ".." if len(rules.domain) > 25 else rules.domain
                
                print(f"{file.name:<30} {domain:<25} {facts_count:<6} {rules_count:<6}")
            except Exception as e:
                print(f"{file.name:<30} {'<erro ao carregar>':<25}")
        
        print(f"{'─' * 70}")
        print(f"\nTotal: {len(files)} arquivo(s)")
        
        return 0
    
    def _cmd_explain(self, args) -> int:
        """Comando: explain."""
        print(f"\n🔎 Explicando processamento para: \"{args.question}\"\n")
        
        engine = DKREngine(args.file)
        
        # Exibe explicação detalhada
        explanation = engine.explain_intent(args.question)
        print(explanation)
        
        # Mostra expansão de query
        expanded = engine.expand_query(args.question)
        if expanded != args.question:
            print(f"\n📝 Query expandida:")
            print(f"   Original: {args.question}")
            print(f"   Expandida: {expanded}")
        else:
            print(f"\n📝 Query não será expandida")
        
        # Mostra regras que podem ser ativadas
        print(f"\n⚖️  Regras potencialmente aplicáveis:")
        
        if engine.rules:
            intent, _ = engine._detect_intent(args.question)
            
            matching_rules = [
                r for r in engine.rules.validation_rules
                if r.trigger_intent == intent or r.trigger_intent is None
            ]
            
            if matching_rules:
                for rule in matching_rules:
                    print(f"   • {rule.name}")
                    if rule.trigger_answer_contains:
                        print(f"     Se resposta contém: {rule.trigger_answer_contains}")
                    if rule.trigger_answer_not_contains:
                        print(f"     Se resposta NÃO contém: {rule.trigger_answer_not_contains}")
            else:
                print("   Nenhuma regra específica para este intent")
        
        return 0


def main(args: Optional[List[str]] = None) -> int:
    """Ponto de entrada principal."""
    cli = DKRCli()
    return cli.run(args)


if __name__ == "__main__":
    sys.exit(main())

