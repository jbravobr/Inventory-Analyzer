#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
CLI principal do Inventory Analyzer.
"""

import json
import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

import click
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


def print_banner():
    """Exibe banner do aplicativo."""
    banner = """
╔═══════════════════════════════════════════════════════════╗
║       INVENTORY ANALYZER v1.0.0 - OFFLINE                 ║
║   Análise de Escrituras de Inventário e Adjudicação       ║
╚═══════════════════════════════════════════════════════════╝
"""
    console.print(banner, style="cyan")


@click.group()
@click.version_option(version="1.0.0")
def cli():
    """Inventory Analyzer - Análise de Escrituras de Inventário."""
    pass


@cli.command()
@click.argument('pdf_path', type=click.Path(exists=True))
@click.option('-o', '--output', default='./output', help='Diretório de saída')
@click.option('--txt/--no-txt', default=True, help='Gerar relatório TXT')
@click.option('--pdf/--no-pdf', default=True, help='Gerar PDF com highlights')
@click.option('--json/--no-json', 'output_json', default=False, help='Gerar saída JSON')
def analyze(
    pdf_path: str,
    output: str,
    txt: bool,
    pdf: bool,
    output_json: bool
):
    """
    Analisa uma escritura de inventário.
    
    Extrai informações sobre herdeiros, inventariante, bens BTG e divisão.
    """
    print_banner()
    
    from inventory.analyzer import InventoryAnalyzer
    from inventory.report_generator import ReportGenerator
    from inventory.pdf_highlighter import PDFHighlighter
    
    pdf_path = Path(pdf_path)
    output_dir = Path(output)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Nome base para arquivos de saída
    base_name = pdf_path.stem
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    console.print(f"\nAnalisando: [bold]{pdf_path.name}[/bold]\n")
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console
    ) as progress:
        
        # Análise
        task = progress.add_task("Processando documento...", total=None)
        
        analyzer = InventoryAnalyzer()
        result = analyzer.analyze(pdf_path)
        
        progress.update(task, description="Análise concluída!")
    
    # Exibe resumo
    _print_summary(result)
    
    # Gera saídas
    outputs = []
    
    if txt:
        txt_path = output_dir / f"{base_name}_relatorio_{timestamp}.txt"
        report_gen = ReportGenerator()
        report_gen.generate(result, txt_path, pdf_path.name)
        outputs.append(("Relatório TXT", txt_path))
        console.print(f"✓ Relatório TXT: [green]{txt_path}[/green]")
    
    if pdf:
        pdf_output = output_dir / f"{base_name}_destacado_{timestamp}.pdf"
        highlighter = PDFHighlighter()
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            task = progress.add_task("Gerando PDF com highlights...", total=None)
            highlighter.generate_highlighted_pdf(pdf_path, result, pdf_output)
        
        outputs.append(("PDF Destacado", pdf_output))
        console.print(f"✓ PDF com highlights: [green]{pdf_output}[/green]")
    
    if output_json:
        json_path = output_dir / f"{base_name}_resultado_{timestamp}.json"
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(result.to_dict(), f, ensure_ascii=False, indent=2)
        outputs.append(("JSON", json_path))
        console.print(f"✓ Resultado JSON: [green]{json_path}[/green]")
    
    console.print(f"\n[bold green]Análise concluída em {result.processing_time:.2f}s[/bold green]")
    console.print(f"Arquivos salvos em: [cyan]{output_dir}[/cyan]\n")


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
            f.write(f"PÁGINA {page.page_number}\n")
            f.write(f"{'='*60}\n\n")
            f.write(page.text or "(sem texto)")
            f.write("\n\n")
    
    console.print(f"✓ Texto extraído: [green]{output_file}[/green]")
    console.print(f"Total de páginas: {len(document.pages)}")


@cli.command()
def info():
    """Exibe informações sobre a configuração atual."""
    print_banner()
    
    from config.settings import get_settings
    
    settings = get_settings()
    
    table = Table(title="Configuração Atual", show_header=True)
    table.add_column("Parâmetro", style="cyan")
    table.add_column("Valor", style="green")
    
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

