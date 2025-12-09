#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
CLI principal do Document Analyzer.

Suporta múltiplos perfis de análise:
- inventory: Escritura Pública de Inventário
- meeting_minutes: Ata de Reunião de Quotistas

Suporta múltiplos modos de operação:
- offline: 100% local, sem conexão à internet (PADRÃO)
- online: Permite downloads e APIs cloud
- hybrid: Tenta online, usa cache local se falhar
"""

import json
import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

import click
import yaml
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table

# Configura logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

console = Console()

# Contexto global para passar flags entre comandos
class Context:
    """Contexto para armazenar configurações globais da CLI."""
    def __init__(self):
        self.mode_override: Optional[str] = None
        self.allow_download: Optional[bool] = None

pass_context = click.make_pass_decorator(Context, ensure=True)

# Perfis disponíveis
AVAILABLE_PROFILES = {
    "inventory": {
        "name": "Análise de Inventário",
        "description": "Extrai herdeiros, inventariante, bens BTG e divisão patrimonial"
    },
    "meeting_minutes": {
        "name": "Ata de Reunião de Quotistas",
        "description": "Extrai ativos envolvidos e suas quantidades"
    }
}


def get_active_profile() -> str:
    """Obtém o perfil ativo da configuração."""
    config_path = Path(__file__).parent.parent / "config.yaml"
    if config_path.exists():
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                config = yaml.safe_load(f)
                return config.get("analysis", {}).get("active_profile", "inventory")
        except Exception:
            pass
    return "inventory"


def _init_mode_manager(mode_override: Optional[str], allow_download: Optional[bool]):
    """Inicializa o ModeManager com as opções da CLI."""
    from config.settings import get_settings
    from config.mode_manager import init_mode_manager
    
    settings = get_settings()
    
    # Inicializa o ModeManager
    mode_mgr = init_mode_manager(
        config=settings.system,
        cli_override=mode_override,
        allow_download_override=allow_download
    )
    
    # Log do modo ativo
    logger.info(f"Modo de operação: {mode_mgr.get_status_message()}")


def print_banner(profile: str = "inventory", mode: Optional[str] = None):
    """Exibe banner do aplicativo."""
    from config.mode_manager import get_mode_manager
    
    profile_info = AVAILABLE_PROFILES.get(profile, AVAILABLE_PROFILES["inventory"])
    
    # Obtém modo de operação
    try:
        mode_mgr = get_mode_manager()
        mode_str = mode_mgr.mode.value.upper()
    except:
        mode_str = (mode or "OFFLINE").upper()
    
    banner = f"""
╔═══════════════════════════════════════════════════════════╗
║       DOCUMENT ANALYZER v1.1.0 - {mode_str:^8}                ║
║   {profile_info['name']:^51} ║
╚═══════════════════════════════════════════════════════════╝
"""
    console.print(banner, style="cyan")


@click.group()
@click.version_option(version="1.1.0")
@click.option('--offline', 'mode', flag_value='offline', default=True,
              help='Modo offline: usa apenas modelos locais (PADRÃO)')
@click.option('--online', 'mode', flag_value='online',
              help='Modo online: permite downloads e APIs cloud')
@click.option('--hybrid', 'mode', flag_value='hybrid',
              help='Modo híbrido: tenta online, fallback para offline')
@click.option('--allow-download/--no-download', 'allow_download', default=None,
              help='Permite/bloqueia download de modelos (override)')
@pass_context
def cli(ctx: Context, mode: str, allow_download: Optional[bool]):
    """
    Document Analyzer - Análise de Documentos Jurídicos/Financeiros.
    
    MODOS DE OPERAÇÃO:
    
    \b
      --offline   (padrão) 100% local, sem conexão à internet
      --online    Permite downloads do HuggingFace e APIs cloud
      --hybrid    Tenta online, usa cache local se falhar
    
    EXEMPLOS:
    
    \b
      python run.py analyze documento.pdf
      python run.py --online analyze documento.pdf --profile meeting_minutes
      python run.py --hybrid --allow-download analyze documento.pdf
    """
    # Armazena opções no contexto
    ctx.mode_override = mode
    ctx.allow_download = allow_download
    
    # Inicializa ModeManager com as opções
    _init_mode_manager(mode, allow_download)


@cli.command()
@click.argument('pdf_path', type=click.Path(exists=True))
@click.option('-o', '--output', default='./output', help='Diretório de saída')
@click.option('-p', '--profile', default=None, 
              type=click.Choice(['inventory', 'meeting_minutes']),
              help='Perfil de análise (inventory ou meeting_minutes)')
@click.option('-i', '--instructions', default=None, type=click.Path(exists=True),
              help='Caminho para arquivo de instruções customizado')
@click.option('--txt/--no-txt', default=True, help='Gerar relatório TXT')
@click.option('--pdf/--no-pdf', default=True, help='Gerar PDF com highlights')
@click.option('--json/--no-json', 'output_json', default=False, help='Gerar saída JSON')
def analyze(
    pdf_path: str,
    output: str,
    profile: Optional[str],
    instructions: Optional[str],
    txt: bool,
    pdf: bool,
    output_json: bool
):
    """
    Analisa um documento PDF.
    
    Perfis disponíveis:
    
    - inventory: Escritura de Inventário (herdeiros, inventariante, bens BTG)
    
    - meeting_minutes: Ata de Reunião de Quotistas (ativos e quantidades)
    
    Exemplos:
    
        python run.py analyze documento.pdf --profile inventory
    
        python run.py analyze ata.pdf --profile meeting_minutes
    
        python run.py analyze doc.pdf -i ./minhas_instrucoes.txt
    """
    # Determina o perfil a usar
    active_profile = profile or get_active_profile()
    
    print_banner(active_profile)
    
    pdf_path = Path(pdf_path)
    output_dir = Path(output)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Nome base para arquivos de saída
    base_name = pdf_path.stem
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    console.print(f"\nAnalisando: [bold]{pdf_path.name}[/bold]")
    console.print(f"Perfil: [cyan]{AVAILABLE_PROFILES[active_profile]['name']}[/cyan]\n")
    
    if instructions:
        console.print(f"Instruções customizadas: [yellow]{instructions}[/yellow]\n")
    
    # Executa análise baseada no perfil
    if active_profile == "meeting_minutes":
        result = _analyze_meeting_minutes(pdf_path)
        _print_meeting_minutes_summary(result)
        
        # Gera saídas
        if txt:
            from inventory.meeting_minutes_report import MeetingMinutesReportGenerator
            txt_path = output_dir / f"{base_name}_relatorio_{timestamp}.txt"
            report_gen = MeetingMinutesReportGenerator()
            report_gen.generate(result, txt_path, pdf_path.name)
            console.print(f"✓ Relatório TXT: [green]{txt_path}[/green]")
        
        if pdf:
            from inventory.meeting_minutes_highlighter import MeetingMinutesPDFHighlighter
            pdf_output = output_dir / f"{base_name}_destacado_{timestamp}.pdf"
            highlighter = MeetingMinutesPDFHighlighter()
            
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=console
            ) as progress:
                task = progress.add_task("Gerando PDF com highlights...", total=None)
                highlighter.generate_highlighted_pdf(pdf_path, result, pdf_output)
            
            console.print(f"✓ PDF com highlights: [green]{pdf_output}[/green]")
        
        if output_json:
            json_path = output_dir / f"{base_name}_resultado_{timestamp}.json"
            with open(json_path, 'w', encoding='utf-8') as f:
                json.dump(result.to_dict(), f, ensure_ascii=False, indent=2)
            console.print(f"✓ Resultado JSON: [green]{json_path}[/green]")
    
    else:  # inventory (padrão)
        result = _analyze_inventory(pdf_path)
        _print_summary(result)
        
        # Gera saídas
        if txt:
            from inventory.report_generator import ReportGenerator
            txt_path = output_dir / f"{base_name}_relatorio_{timestamp}.txt"
            report_gen = ReportGenerator()
            report_gen.generate(result, txt_path, pdf_path.name)
            console.print(f"✓ Relatório TXT: [green]{txt_path}[/green]")
        
        if pdf:
            from inventory.pdf_highlighter import PDFHighlighter
            pdf_output = output_dir / f"{base_name}_destacado_{timestamp}.pdf"
            highlighter = PDFHighlighter()
            
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=console
            ) as progress:
                task = progress.add_task("Gerando PDF com highlights...", total=None)
                highlighter.generate_highlighted_pdf(pdf_path, result, pdf_output)
            
            console.print(f"✓ PDF com highlights: [green]{pdf_output}[/green]")
        
        if output_json:
            json_path = output_dir / f"{base_name}_resultado_{timestamp}.json"
            with open(json_path, 'w', encoding='utf-8') as f:
                json.dump(result.to_dict(), f, ensure_ascii=False, indent=2)
            console.print(f"✓ Resultado JSON: [green]{json_path}[/green]")
    
    console.print(f"\n[bold green]Análise concluída em {result.processing_time:.2f}s[/bold green]")
    console.print(f"Arquivos salvos em: [cyan]{output_dir}[/cyan]\n")


def _create_rag_config():
    """Cria RAGConfig baseado nas configurações do arquivo YAML."""
    from config.settings import get_settings
    from rag.rag_pipeline import RAGConfig
    
    settings = get_settings()
    
    # Obtém configuração de geração do arquivo YAML
    generate_answers = False
    if hasattr(settings, 'rag') and hasattr(settings.rag, 'generation'):
        generate_answers = settings.rag.generation.generate_answers
    
    return RAGConfig(
        mode="local",
        chunk_size=400,
        chunk_overlap=100,
        top_k=10,
        use_hybrid_search=True,
        generate_answers=generate_answers
    )


def _analyze_inventory(pdf_path: Path):
    """Executa análise de inventário."""
    from inventory.analyzer import InventoryAnalyzer
    
    config = _create_rag_config()
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console
    ) as progress:
        task = progress.add_task("Processando documento...", total=None)
        
        analyzer = InventoryAnalyzer(config=config)
        result = analyzer.analyze(pdf_path)
        
        progress.update(task, description="Análise concluída!")
    
    return result


def _analyze_meeting_minutes(pdf_path: Path):
    """Executa análise de ata de reunião."""
    from inventory.meeting_minutes_analyzer import MeetingMinutesAnalyzer
    
    config = _create_rag_config()
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console
    ) as progress:
        task = progress.add_task("Processando documento...", total=None)
        
        analyzer = MeetingMinutesAnalyzer(config=config)
        result = analyzer.analyze(pdf_path)
        
        progress.update(task, description="Análise concluída!")
    
    return result


def _print_meeting_minutes_summary(result):
    """Exibe resumo da análise de ata de reunião."""
    from typing import Dict, List
    
    # Tabela de resumo
    table = Table(title="Resumo da Análise - Ata de Reunião", show_header=True)
    table.add_column("Seção", style="cyan")
    table.add_column("Resultado", style="green")
    table.add_column("Confiança", style="yellow")
    
    # Info do Fundo
    fund_info = result.fund_name or "Não identificado"
    if result.meeting_date:
        fund_info += f"\nData: {result.meeting_date}"
    
    table.add_row(
        "Fundo",
        fund_info,
        "-"
    )
    
    # Cláusula A - Ativos
    assets_result = f"{len(result.assets)} ativo(s)"
    if result.assets:
        # Agrupa por tipo
        by_type: Dict[str, int] = {}
        for asset in result.assets:
            t = asset.asset_type or "Outros"
            by_type[t] = by_type.get(t, 0) + 1
        
        assets_result += "\n" + "\n".join([f"  • {t}: {c}" for t, c in list(by_type.items())[:4]])
    
    table.add_row(
        "A) Ativos",
        assets_result,
        f"{result.confidence_scores.get('assets', 0)*100:.0f}%"
    )
    
    # Cláusula B - Quantidades
    qty_result = f"{len(result.asset_quantities)} quantidade(s)"
    if result.asset_quantities:
        total_value = sum(q.total_value for q in result.asset_quantities if q.total_value)
        if total_value > 0:
            qty_result += f"\nValor total: R$ {total_value:,.2f}"
    
    table.add_row(
        "B) Quantidades",
        qty_result,
        f"{result.confidence_scores.get('quantities', 0)*100:.0f}%"
    )
    
    console.print()
    console.print(table)
    console.print()


def _print_summary(result):
    """Exibe resumo da análise."""
    
    # Tabela de resumo
    table = Table(title="Resumo da Análise", show_header=True)
    table.add_column("Cláusula", style="cyan")
    table.add_column("Resultado", style="green")
    table.add_column("Confiança", style="yellow")
    
    # Cláusula A - Herdeiros
    heirs_result = f"{len(result.heirs)} encontrado(s)"
    if result.heirs:
        heirs_result += f"\n" + "\n".join([f"  • {h.name}" for h in result.heirs[:5]])
        if len(result.heirs) > 5:
            heirs_result += f"\n  ... e mais {len(result.heirs) - 5}"
    
    table.add_row(
        "A) Herdeiros",
        heirs_result,
        f"{result.confidence_scores.get('heirs', 0)*100:.0f}%"
    )
    
    # Cláusula B - Inventariante
    admin_result = result.administrator_name or "Não identificado"
    if result.administrator_is_heir:
        admin_result += " (também herdeiro)"
    
    table.add_row(
        "B) Inventariante",
        admin_result,
        f"{result.confidence_scores.get('administrator', 0)*100:.0f}%"
    )
    
    # Cláusula C - Bens BTG
    btg_result = f"{len(result.btg_assets)} encontrado(s)"
    if result.btg_assets:
        total = sum(a.value for a in result.btg_assets if a.value)
        if total > 0:
            btg_result += f"\nTotal: R$ {total:,.2f}"
    
    table.add_row(
        "C) Bens BTG",
        btg_result,
        f"{result.confidence_scores.get('btg_assets', 0)*100:.0f}%"
    )
    
    # Cláusula D - Divisão
    div_result = f"{len(result.asset_divisions)} divisão(ões)"
    
    table.add_row(
        "D) Divisão",
        div_result,
        f"{result.confidence_scores.get('divisions', 0)*100:.0f}%"
    )
    
    console.print()
    console.print(table)
    console.print()


@cli.command()
@click.argument('pdf_path', type=click.Path(exists=True))
@click.option('-o', '--output', default='./output', help='Diretório de saída')
def extract(pdf_path: str, output: str):
    """
    Apenas extrai texto do PDF (sem análise RAG).
    
    Útil para verificar a qualidade do OCR.
    """
    print_banner()
    
    from core.pdf_reader import PDFReader
    from core.ocr_extractor import OCRExtractor
    
    pdf_path = Path(pdf_path)
    output_dir = Path(output)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    console.print(f"\nExtraindo texto de: [bold]{pdf_path.name}[/bold]\n")
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console
    ) as progress:
        task = progress.add_task("Lendo PDF...", total=None)
        
        reader = PDFReader()
        document = reader.read(pdf_path)
        
        progress.update(task, description="Executando OCR...")
        
        ocr = OCRExtractor()
        ocr.extract(document)
    
    # Salva texto
    output_file = output_dir / f"{pdf_path.stem}_texto.txt"
    
    with open(output_file, 'w', encoding='utf-8') as f:
        for page in document.pages:
            f.write(f"{'='*60}\n")
            f.write(f"PÁGINA {page.number}\n")
            f.write(f"{'='*60}\n\n")
            f.write(page.text or "(sem texto)")
            f.write("\n\n")
    
    console.print(f"✓ Texto extraído: [green]{output_file}[/green]")
    console.print(f"Total de páginas: {len(document.pages)}")


@cli.command()
def profiles():
    """Lista os perfis de análise disponíveis."""
    print_banner()
    
    active = get_active_profile()
    
    console.print("\n[bold]Perfis de Análise Disponíveis:[/bold]\n")
    
    table = Table(show_header=True, header_style="bold cyan")
    table.add_column("Perfil", style="cyan")
    table.add_column("Nome", style="green")
    table.add_column("Descrição")
    table.add_column("Status")
    
    for profile_id, profile_info in AVAILABLE_PROFILES.items():
        status = "[bold green]ATIVO[/bold green]" if profile_id == active else ""
        table.add_row(
            profile_id,
            profile_info["name"],
            profile_info["description"],
            status
        )
    
    console.print(table)
    console.print()
    
    console.print("[bold]Como usar:[/bold]")
    console.print("  python run.py analyze documento.pdf --profile inventory")
    console.print("  python run.py analyze documento.pdf --profile meeting_minutes")
    console.print()
    console.print("[bold]Para mudar o perfil padrão:[/bold]")
    console.print("  Edite o arquivo [cyan]config.yaml[/cyan] e altere [yellow]analysis.active_profile[/yellow]")
    console.print()


@cli.command()
@pass_context
def info(ctx: Context):
    """Exibe informações sobre a configuração atual."""
    print_banner(mode=ctx.mode_override)
    
    from config.settings import get_settings
    from config.mode_manager import get_mode_manager
    
    settings = get_settings()
    mode_mgr = get_mode_manager()
    active_profile = get_active_profile()
    
    table = Table(title="Configuração Atual", show_header=True)
    table.add_column("Parâmetro", style="cyan")
    table.add_column("Valor", style="green")
    
    # Modo de operação
    table.add_row("Modo de Operação", mode_mgr.get_status_message())
    table.add_row("Downloads Permitidos", "Sim" if mode_mgr.allow_downloads else "Não")
    table.add_row("APIs Cloud", "Habilitadas" if mode_mgr.allow_cloud_apis else "Desabilitadas")
    table.add_row("Caminho dos Modelos", mode_mgr.models_path)
    table.add_row("", "")  # Separador
    table.add_row("Perfil Ativo", active_profile)
    table.add_row("Modo NLP", settings.nlp.mode)
    table.add_row("Tesseract", settings.ocr.tesseract_path)
    table.add_row("Idioma OCR", settings.ocr.language)
    table.add_row("DPI", str(settings.ocr.dpi))
    
    console.print(table)
    console.print()
    
    # Status das dependências
    console.print("Status das Dependências:", style="bold")
    
    # Tesseract
    try:
        import pytesseract
        langs = pytesseract.get_languages()
        console.print(f"  ✓ Tesseract: {', '.join(langs)}", style="green")
    except Exception as e:
        console.print(f"  ✗ Tesseract: {e}", style="red")
    
    # FAISS
    try:
        import faiss
        console.print("  ✓ FAISS disponível", style="green")
    except ImportError:
        console.print("  ✗ FAISS não instalado", style="red")
    
    # Sentence Transformers
    try:
        from sentence_transformers import SentenceTransformer
        console.print("  ✓ Sentence Transformers disponível", style="green")
    except ImportError:
        console.print("  ✗ Sentence Transformers não instalado", style="red")


@cli.command()
def create_sample():
    """Cria arquivo de instruções de exemplo."""
    
    sample_path = Path("instructions/inventory_analysis.txt")
    
    if sample_path.exists():
        console.print(f"Arquivo já existe: {sample_path}", style="yellow")
        return
    
    sample_path.parent.mkdir(parents=True, exist_ok=True)
    
    content = """# Instruções para Análise de Inventário
# =====================================

# Cláusula A - Herdeiros
- Localizar todos os herdeiros
- Identificar nome completo e CPF
- Verificar grau de parentesco

# Cláusula B - Inventariante
- Identificar o inventariante nomeado
- Verificar se é também herdeiro

# Cláusula C - Bens BTG
- Localizar bens com menção a BTG
- Identificar tipo e valor

# Cláusula D - Divisão
- Verificar como os bens foram divididos
- Identificar percentuais por herdeiro
"""
    
    with open(sample_path, 'w', encoding='utf-8') as f:
        f.write(content)
    
    console.print(f"✓ Arquivo criado: [green]{sample_path}[/green]")


def main():
    """Ponto de entrada principal."""
    try:
        cli()
    except Exception as e:
        console.print(f"\n[red]Erro: {e}[/red]")
        logger.exception("Erro na execução")
        sys.exit(1)


if __name__ == "__main__":
    main()

