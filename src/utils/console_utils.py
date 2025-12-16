"""
Utilitarios de Console com suporte a encoding Windows.

Este modulo resolve definitivamente os problemas de encoding
entre Prompt de Comando, PowerShell e terminais Unix.
"""

import io
import os
import sys
import platform
from typing import Optional

from rich.console import Console
from rich.theme import Theme
from rich.table import Table
from rich.panel import Panel
from rich.progress import Progress, TextColumn, BarColumn, TaskProgressColumn


# Detecta ambiente
IS_WINDOWS = platform.system() == "Windows"


def setup_encoding() -> None:
    """
    Configura encoding UTF-8 para stdout/stderr no Windows.
    
    Deve ser chamado no inicio do programa.
    """
    if IS_WINDOWS:
        # Tenta configurar UTF-8 no console Windows
        try:
            # Python 3.7+
            if hasattr(sys.stdout, 'reconfigure'):
                sys.stdout.reconfigure(encoding='utf-8', errors='replace')
                sys.stderr.reconfigure(encoding='utf-8', errors='replace')
            else:
                # Fallback para versoes anteriores
                sys.stdout = io.TextIOWrapper(
                    sys.stdout.buffer, encoding='utf-8', errors='replace'
                )
                sys.stderr = io.TextIOWrapper(
                    sys.stderr.buffer, encoding='utf-8', errors='replace'
                )
        except Exception:
            pass
        
        # Define variavel de ambiente para subprocessos
        os.environ['PYTHONIOENCODING'] = 'utf-8'


# Tema personalizado com cores que funcionam bem em terminais escuros e claros
CUSTOM_THEME = Theme({
    "info": "cyan",
    "warning": "yellow",
    "error": "red bold",
    "success": "green",
    "highlight": "magenta",
    "muted": "dim",
})


# Caracteres ASCII para compatibilidade
ASCII_CHARS = {
    "check": "[OK]",
    "cross": "[X]",
    "arrow": "->",
    "bullet": "*",
    "box_top": "+" + "-" * 58 + "+",
    "box_mid": "|",
    "box_bot": "+" + "-" * 58 + "+",
    "line": "-" * 60,
    "double_line": "=" * 60,
}


def create_console() -> Console:
    """
    Cria uma instancia de Console configurada para o ambiente.
    
    Returns:
        Console configurada para Windows ou Unix
    """
    # Configura encoding primeiro
    setup_encoding()
    
    if IS_WINDOWS:
        # No Windows, usa configuracoes seguras
        return Console(
            theme=CUSTOM_THEME,
            force_terminal=True,
            no_color=False,
            highlight=True,
            # Desabilita caracteres Unicode problematicos
            legacy_windows=True,
            # Usa ASCII para bordas de tabelas e paineis
            safe_box=True,
        )
    else:
        # Unix/Mac - suporte completo a Unicode
        return Console(
            theme=CUSTOM_THEME,
            force_terminal=True,
        )


class SafePrinter:
    """
    Wrapper para impressao segura que trata erros de encoding.
    """
    
    def __init__(self, console: Optional[Console] = None):
        self.console = console or create_console()
    
    def print(self, *args, **kwargs) -> None:
        """Imprime com tratamento de erros de encoding."""
        try:
            self.console.print(*args, **kwargs)
        except UnicodeEncodeError:
            # Fallback: converte para ASCII
            text = " ".join(str(arg) for arg in args)
            safe_text = text.encode('ascii', errors='replace').decode('ascii')
            try:
                self.console.print(safe_text, **kwargs)
            except Exception:
                # Ultimo recurso: print basico
                print(safe_text)
    
    def print_error(self, message: str) -> None:
        """Imprime mensagem de erro."""
        self.print(f"[error]{ASCII_CHARS['cross']} ERRO: {message}[/error]")
    
    def print_success(self, message: str) -> None:
        """Imprime mensagem de sucesso."""
        self.print(f"[success]{ASCII_CHARS['check']} {message}[/success]")
    
    def print_warning(self, message: str) -> None:
        """Imprime aviso."""
        self.print(f"[warning]AVISO: {message}[/warning]")
    
    def print_info(self, message: str) -> None:
        """Imprime informacao."""
        self.print(f"[info]{message}[/info]")
    
    def print_banner(self, title: str, subtitle: str = "") -> None:
        """Imprime banner ASCII."""
        self.print("")
        self.print(ASCII_CHARS["double_line"])
        self.print(f"  {title}")
        if subtitle:
            self.print(f"  {subtitle}")
        self.print(ASCII_CHARS["double_line"])
        self.print("")
    
    def create_table(self, title: str = "", **kwargs) -> Table:
        """Cria tabela com estilo seguro."""
        return Table(
            title=title,
            safe_box=True,
            **kwargs
        )
    
    def create_panel(self, content: str, title: str = "", **kwargs) -> Panel:
        """Cria painel com estilo seguro."""
        return Panel(
            content,
            title=title,
            safe_box=True,
            **kwargs
        )
    
    def create_progress(self) -> Progress:
        """Cria barra de progresso simples (sem spinner Unicode)."""
        return Progress(
            TextColumn("[progress.description]{task.description}"),
            BarColumn(bar_width=30),
            TaskProgressColumn(),
            console=self.console,
        )
    
    def input(self, prompt: str = "") -> str:
        """Input seguro."""
        try:
            return self.console.input(prompt)
        except UnicodeEncodeError:
            safe_prompt = prompt.encode('ascii', errors='replace').decode('ascii')
            return input(safe_prompt)


# Instancia global
_printer: Optional[SafePrinter] = None


def get_printer() -> SafePrinter:
    """Obtem instancia global do SafePrinter."""
    global _printer
    if _printer is None:
        _printer = SafePrinter()
    return _printer


def get_console() -> Console:
    """Obtem instancia global do Console."""
    return get_printer().console


# Funcoes de conveniencia
def safe_print(*args, **kwargs) -> None:
    """Print seguro."""
    get_printer().print(*args, **kwargs)


def print_error(message: str) -> None:
    """Imprime erro."""
    get_printer().print_error(message)


def print_success(message: str) -> None:
    """Imprime sucesso."""
    get_printer().print_success(message)


def print_warning(message: str) -> None:
    """Imprime aviso."""
    get_printer().print_warning(message)


def print_info(message: str) -> None:
    """Imprime info."""
    get_printer().print_info(message)


def print_banner(title: str, subtitle: str = "") -> None:
    """Imprime banner."""
    get_printer().print_banner(title, subtitle)

