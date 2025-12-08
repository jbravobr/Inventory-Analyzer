"""Ponto de entrada principal do aplicativo."""

from __future__ import annotations

import json
import logging
import sys
from pathlib import Path
from typing import Optional

import click
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table
from rich.panel import Panel
from rich.markdown import Markdown

from .config.settings import get_settings, Settings
from .pipeline.pipeline import Pipeline, PipelineResult
from .rag.rag_pipeline import RAGPipeline, RAGPipelineBuilder, RAGConfig

# Configuração de logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

console = Console()


def setup_logging(verbose: bool = False) -> None:
    """Configura nível de logging."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.getLogger().setLevel(level)


def print_banner() -> None:
    """Exibe banner do aplicativo."""
    banner = """
╔═══════════════════════════════════════════════════════════╗
║        PDF CONTRACT ANALYZER v2.0.0 + RAG                 ║
║   Análise de Contratos com OCR, NLP e RAG Pipeline        ║
╚═══════════════════════════════════════════════════════════╝
"""
    console.print(banner, style="bold blue")


def print_result_summary(result: PipelineResult) -> None:
    """Exibe resumo dos resultados."""
    
    table = Table(title="Resumo do Processamento")
    table.add_column("Métrica", style="cyan")
    table.add_column("Valor", style="green")
    
    if result.document:
        table.add_row("Total de Páginas", str(result.document.total_pages))
        table.add_row("Total de Palavras", str(result.document.total_words))
        table.add_row(
            "Confiança OCR",
            f"{result.document.average_confidence:.1%}"
        )
    
    if result.search_result:
        table.add_row(
            "Instruções Satisfeitas",
            f"{result.search_result.found_count}/{len(result.search_result.instruction_matches)}"
        )
        table.add_row("Total de Matches", str(result.search_result.total_matches))
        table.add_row(
            "Páginas com Resultados",
            ", ".join(map(str, result.search_result.all_pages)) or "Nenhuma"
        )
    
    table.add_row("Tempo Total", f"{result.total_time:.2f}s")
    
    console.print(table)
    
    if result.output_files:
        console.print("\n[bold green]Arquivos Gerados:[/bold green]")
        for key, path in result.output_files.items():
            if isinstance(path, list):
                console.print(f"  • {key}: {len(path)} arquivos")
            else:
                console.print(f"  • {key}: {path}")
    
    if result.errors:
        console.print("\n[bold red]Erros:[/bold red]")
        for error in result.errors:
            console.print(f"  ✗ {error}", style="red")


@click.group()
@click.version_option(version="2.0.0")
def cli():
    """PDF Contract Analyzer - Análise de contratos com OCR, NLP e RAG."""
    pass


@cli.command()
@click.argument("pdf_path", type=click.Path(exists=True))
@click.argument("instructions_path", type=click.Path(exists=True))
@click.option(
    "-o", "--output",
    type=click.Path(),
    default="./output",
    help="Diretório de saída"
)
@click.option(
    "-c", "--config",
    type=click.Path(exists=True),
    help="Arquivo de configuração YAML"
)
@click.option(
    "--mode",
    type=click.Choice(["local", "cloud"]),
    default="local",
    help="Modo de processamento NLP"
)
@click.option("-v", "--verbose", is_flag=True, help="Modo verboso")
def analyze(
    pdf_path: str,
    instructions_path: str,
    output: str,
    config: Optional[str],
    mode: str,
    verbose: bool
):
    """
    Analisa um contrato PDF baseado em instruções (modo tradicional).
    
    PDF_PATH: Caminho do arquivo PDF a analisar
    INSTRUCTIONS_PATH: Arquivo com instruções de busca
    """
    print_banner()
    setup_logging(verbose)
    
    if config:
        settings = Settings.from_yaml(Path(config))
    else:
        settings = get_settings()
    
    settings.nlp.mode = mode
    
    pipeline = Pipeline(settings)
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console
    ) as progress:
        task = progress.add_task("Processando...", total=None)
        
        def update_progress(msg: str, pct: float):
            progress.update(task, description=f"[cyan]{msg}[/cyan]")
        
        pipeline.progress_callback = update_progress
        
        result = pipeline.run(
            pdf_path=Path(pdf_path),
            instructions_path=Path(instructions_path),
            output_dir=Path(output)
        )
    
    if result.success:
        console.print("\n[bold green]✓ Análise concluída com sucesso![/bold green]\n")
    else:
        console.print("\n[bold red]✗ Análise concluída com erros[/bold red]\n")
    
    print_result_summary(result)
    
    sys.exit(0 if result.success else 1)


@cli.command()
@click.argument("pdf_path", type=click.Path(exists=True))
@click.option(
    "-q", "--query",
    multiple=True,
    help="Pergunta para o RAG (pode usar múltiplas vezes)"
)
@click.option(
    "-i", "--instructions",
    type=click.Path(exists=True),
    help="Arquivo com instruções (uma por linha)"
)
@click.option(
    "-o", "--output",
    type=click.Path(),
    help="Arquivo de saída JSON"
)
@click.option(
    "--mode",
    type=click.Choice(["local", "cloud"]),
    default="local",
    help="Modo de processamento"
)
@click.option(
    "--top-k",
    type=int,
    default=5,
    help="Número de chunks a recuperar"
)
@click.option(
    "--no-generate",
    is_flag=True,
    help="Apenas recupera contexto, sem gerar resposta"
)
@click.option("-v", "--verbose", is_flag=True, help="Modo verboso")
def rag(
    pdf_path: str,
    query: tuple,
    instructions: Optional[str],
    output: Optional[str],
    mode: str,
    top_k: int,
    no_generate: bool,
    verbose: bool
):
    """
    Analisa contrato usando RAG (Retrieval-Augmented Generation).
    
    PDF_PATH: Caminho do arquivo PDF
    
    Exemplos:
        python run.py rag contrato.pdf -q "Qual o valor do aluguel?"
        python run.py rag contrato.pdf -i instrucoes.txt --mode cloud
    """
    print_banner()
    setup_logging(verbose)
    
    # Coleta queries
    queries = list(query)
    
    if instructions:
        with open(instructions, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#"):
                    # Remove bullet markers
                    line = line.lstrip("-*•").strip()
                    if line:
                        queries.append(line)
    
    if not queries:
        console.print("[red]Erro: Forneça pelo menos uma query (-q) ou arquivo de instruções (-i)[/red]")
        sys.exit(1)
    
    console.print(f"\n[cyan]Processando {len(queries)} pergunta(s)...[/cyan]\n")
    
    # Configura RAG
    rag_config = RAGConfig(
        mode=mode,
        top_k=top_k,
        use_hybrid_search=True,
    )
    
    settings = get_settings()
    rag_pipeline = RAGPipeline(rag_config, settings)
    
    # Pipeline
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console
    ) as progress:
        task = progress.add_task("Inicializando...", total=None)
        
        def update_progress(msg: str, pct: float):
            progress.update(task, description=f"[cyan]{msg}[/cyan]")
        
        rag_pipeline.progress_callback = update_progress
        
        # Lê e indexa PDF
        progress.update(task, description="[cyan]Lendo PDF...[/cyan]")
        
        from .core.pdf_reader import PDFReader
        from .core.ocr_extractor import OCRExtractor
        
        reader = PDFReader(settings)
        document = reader.read(Path(pdf_path))
        
        progress.update(task, description="[cyan]Extraindo texto com OCR...[/cyan]")
        ocr = OCRExtractor(settings)
        ocr.extract(document)
        
        progress.update(task, description="[cyan]Indexando documento...[/cyan]")
        rag_pipeline.index_document(document)
        
        # Processa queries
        results = []
        for i, q in enumerate(queries):
            progress.update(
                task,
                description=f"[cyan]Query {i+1}/{len(queries)}: {q[:40]}...[/cyan]"
            )
            
            response = rag_pipeline.query(
                q,
                top_k=top_k,
                generate_response=not no_generate
            )
            results.append(response)
    
    # Exibe resultados
    console.print("\n")
    
    for i, (q, response) in enumerate(zip(queries, results)):
        console.print(Panel(
            f"[bold]Pergunta:[/bold] {q}\n\n"
            f"[bold]Resposta:[/bold]\n{response.answer}\n\n"
            f"[dim]Páginas: {response.pages_cited} | "
            f"Confiança: {response.confidence:.0%} | "
            f"Tempo: {response.processing_time:.2f}s[/dim]",
            title=f"Resultado {i+1}/{len(queries)}",
            border_style="green" if response.confidence > 0.5 else "yellow"
        ))
        console.print()
    
    # Salva resultados
    if output:
        output_data = {
            "pdf": pdf_path,
            "mode": mode,
            "results": [
                {
                    "query": q,
                    "answer": r.answer,
                    "confidence": r.confidence,
                    "pages": r.pages_cited,
                    "processing_time": r.processing_time,
                }
                for q, r in zip(queries, results)
            ]
        }
        
        with open(output, "w", encoding="utf-8") as f:
            json.dump(output_data, f, ensure_ascii=False, indent=2)
        
        console.print(f"[green]Resultados salvos em: {output}[/green]")


@cli.command()
@click.argument("pdf_path", type=click.Path(exists=True))
@click.option(
    "-o", "--output",
    type=click.Path(),
    help="Arquivo de saída para o texto"
)
@click.option("-v", "--verbose", is_flag=True, help="Modo verboso")
def extract(pdf_path: str, output: Optional[str], verbose: bool):
    """
    Extrai texto de um PDF usando OCR.
    
    PDF_PATH: Caminho do arquivo PDF
    """
    print_banner()
    setup_logging(verbose)
    
    settings = get_settings()
    pipeline = Pipeline(settings)
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console
    ) as progress:
        task = progress.add_task("Extraindo texto...", total=None)
        
        def update_progress(msg: str, pct: float):
            progress.update(task, description=f"[cyan]{msg}[/cyan]")
        
        pipeline.progress_callback = update_progress
        result = pipeline.run_extraction_only(Path(pdf_path))
    
    if result.success and result.document:
        text = result.document.full_text
        
        if output:
            with open(output, "w", encoding="utf-8") as f:
                f.write(text)
            console.print(f"\n[green]Texto salvo em: {output}[/green]")
        else:
            console.print(Panel(text[:2000] + "..." if len(text) > 2000 else text))
        
        console.print(f"\n[cyan]Total: {result.document.total_words} palavras[/cyan]")
    else:
        console.print("[red]Erro na extração[/red]")
        for error in result.errors:
            console.print(f"  ✗ {error}", style="red")


@cli.command()
@click.argument("output_path", type=click.Path())
def create_instructions(output_path: str):
    """
    Cria arquivo de exemplo de instruções.
    
    OUTPUT_PATH: Caminho do arquivo a criar
    """
    from .core.instruction_parser import InstructionParser
    
    parser = InstructionParser()
    parser.create_example_file(Path(output_path))
    
    console.print(f"[green]Arquivo de instruções criado: {output_path}[/green]")
    console.print("\nEdite o arquivo para adicionar suas instruções de busca.")


@cli.command()
@click.option("--rag", is_flag=True, help="Mostra configurações RAG")
def info(rag: bool):
    """Exibe informações sobre a configuração atual."""
    print_banner()
    
    settings = get_settings()
    
    # Configurações gerais
    table = Table(title="Configuração Atual")
    table.add_column("Parâmetro", style="cyan")
    table.add_column("Valor", style="green")
    
    table.add_row("Modo NLP", settings.nlp.mode)
    table.add_row("Modelo spaCy", settings.nlp.local.spacy_model)
    table.add_row("Tesseract", settings.ocr.tesseract_path)
    table.add_row("Idioma OCR", settings.ocr.language)
    table.add_row("DPI", str(settings.ocr.dpi))
    
    console.print(table)
    
    # Configurações RAG
    if rag:
        console.print()
        rag_table = Table(title="Configurações RAG")
        rag_table.add_column("Parâmetro", style="cyan")
        rag_table.add_column("Valor", style="green")
        
        rag_table.add_row("Embedding Model", settings.nlp.local.sentence_transformer)
        rag_table.add_row("Similarity Threshold", str(settings.nlp.local.similarity_threshold))
        rag_table.add_row("Cloud Provider", settings.nlp.cloud.provider)
        rag_table.add_row("Cloud Model", settings.nlp.cloud.model)
        
        console.print(rag_table)
    
    # Verifica dependências
    console.print("\n[bold]Status das Dependências:[/bold]")
    
    # Tesseract
    try:
        import pytesseract
        langs = pytesseract.get_languages()
        console.print(f"  [green]✓[/green] Tesseract: {', '.join(langs[:5])}")
    except Exception as e:
        console.print(f"  [red]✗[/red] Tesseract: {e}")
    
    # FAISS
    try:
        import faiss
        console.print(f"  [green]✓[/green] FAISS disponível")
    except ImportError:
        console.print(f"  [yellow]![/yellow] FAISS não instalado (usando SimpleVectorStore)")
    
    # Sentence Transformers
    try:
        from sentence_transformers import SentenceTransformer
        console.print(f"  [green]✓[/green] Sentence Transformers disponível")
    except ImportError:
        console.print(f"  [red]✗[/red] Sentence Transformers não instalado")
    
    # Transformers (para geração local)
    try:
        import transformers
        console.print(f"  [green]✓[/green] Transformers disponível")
    except ImportError:
        console.print(f"  [yellow]![/yellow] Transformers não instalado (geração local limitada)")


@cli.command()
@click.argument("pdf_path", type=click.Path(exists=True))
@click.option(
    "-o", "--output",
    type=click.Path(),
    default="./index",
    help="Diretório para salvar índice"
)
@click.option("-v", "--verbose", is_flag=True, help="Modo verboso")
def index(pdf_path: str, output: str, verbose: bool):
    """
    Indexa um PDF para uso posterior com RAG.
    
    PDF_PATH: Caminho do arquivo PDF
    """
    print_banner()
    setup_logging(verbose)
    
    settings = get_settings()
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console
    ) as progress:
        task = progress.add_task("Processando...", total=None)
        
        def update_progress(msg: str, pct: float):
            progress.update(task, description=f"[cyan]{msg}[/cyan]")
        
        # Lê PDF
        progress.update(task, description="[cyan]Lendo PDF...[/cyan]")
        from .core.pdf_reader import PDFReader
        from .core.ocr_extractor import OCRExtractor
        
        reader = PDFReader(settings)
        document = reader.read(Path(pdf_path))
        
        progress.update(task, description="[cyan]Extraindo texto...[/cyan]")
        ocr = OCRExtractor(settings)
        ocr.extract(document)
        
        # Indexa
        progress.update(task, description="[cyan]Criando índice RAG...[/cyan]")
        
        rag_pipeline = RAGPipeline(settings=settings)
        rag_pipeline.progress_callback = update_progress
        
        num_chunks = rag_pipeline.index_document(document)
        
        progress.update(task, description="[cyan]Salvando índice...[/cyan]")
        rag_pipeline.save_index(Path(output))
    
    console.print(f"\n[green]✓ Índice criado com {num_chunks} chunks[/green]")
    console.print(f"[green]  Salvo em: {output}[/green]")
    console.print("\nUse 'python run.py query' para fazer perguntas sobre este documento.")


@cli.command()
@click.argument("index_path", type=click.Path(exists=True))
@click.argument("question")
@click.option(
    "--mode",
    type=click.Choice(["local", "cloud"]),
    default="local",
    help="Modo de geração"
)
@click.option(
    "--top-k",
    type=int,
    default=5,
    help="Número de chunks"
)
def query(index_path: str, question: str, mode: str, top_k: int):
    """
    Faz uma pergunta sobre um índice existente.
    
    INDEX_PATH: Caminho do índice criado com 'index'
    QUESTION: Pergunta a fazer
    """
    print_banner()
    
    settings = get_settings()
    
    config = RAGConfig(mode=mode, top_k=top_k)
    rag_pipeline = RAGPipeline(config, settings)
    
    console.print("[cyan]Carregando índice...[/cyan]")
    rag_pipeline.load_index(Path(index_path))
    
    console.print(f"[cyan]Processando pergunta...[/cyan]\n")
    
    response = rag_pipeline.query(question)
    
    console.print(Panel(
        f"[bold]Pergunta:[/bold] {question}\n\n"
        f"[bold]Resposta:[/bold]\n{response.answer}\n\n"
        f"[dim]Páginas: {response.pages_cited} | "
        f"Confiança: {response.confidence:.0%}[/dim]",
        title="Resultado RAG",
        border_style="green"
    ))


def main():
    """Ponto de entrada principal."""
    cli()


if __name__ == "__main__":
    main()
