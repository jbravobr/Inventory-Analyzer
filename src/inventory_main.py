#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
CLI principal do Document Analyzer.

Suporta multiplos perfis de analise:
- inventory: Escritura Publica de Inventario
- meeting_minutes: Ata de Reuniao de Quotistas

Suporta multiplos modos de operacao:
- offline: 100% local, sem conexao a internet (PADRAO)
- online: Permite downloads e APIs cloud
- hybrid: Tenta online, usa cache local se falhar
"""

import json
import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional
from rich.console import Console
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn

import click
import yaml

# Configura encoding UTF-8 para Windows ANTES de qualquer output
from utils.console_utils import setup_encoding, get_console, get_printer, ASCII_CHARS
setup_encoding()

# Configura logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Console seguro para Windows/Unix
console = get_console()
printer = get_printer()

# Contexto global para passar flags entre comandos
class Context:
    """Contexto para armazenar configurações globais da CLI."""
    def __init__(self):
        self.mode_override: Optional[str] = None
        self.allow_download: Optional[bool] = None
        self.use_cloud_generation: Optional[bool] = None
        self.use_cloud_embeddings: Optional[bool] = None

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


def _init_mode_manager(
    mode_override: Optional[str],
    allow_download: Optional[bool],
    use_cloud_generation: Optional[bool] = None,
    use_cloud_embeddings: Optional[bool] = None
):
    """Inicializa o ModeManager com as opções da CLI."""
    from config.settings import get_settings
    from config.mode_manager import init_mode_manager
    
    settings = get_settings()
    
    # Inicializa o ModeManager com todas as opções
    mode_mgr = init_mode_manager(
        config=settings.system,
        cli_override=mode_override,
        allow_download_override=allow_download,
        use_cloud_generation_override=use_cloud_generation,
        use_cloud_embeddings_override=use_cloud_embeddings
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
@click.option('--use-cloud-generation/--no-cloud-generation', 'use_cloud_gen', default=None,
              help='Usa LLM cloud para extração complementar (requer --online)')
@click.option('--use-cloud-embeddings/--no-cloud-embeddings', 'use_cloud_emb', default=None,
              help='Usa embeddings cloud para busca semântica (requer --online)')
@pass_context
def cli(
    ctx: Context,
    mode: str,
    allow_download: Optional[bool],
    use_cloud_gen: Optional[bool],
    use_cloud_emb: Optional[bool]
):
    """
    Document Analyzer - Análise de Documentos Jurídicos/Financeiros.
    
    MODOS DE OPERAÇÃO:
    
    \b
      --offline   (padrão) 100% local, sem conexão à internet
      --online    Permite downloads do HuggingFace e APIs cloud
      --hybrid    Tenta online, usa cache local se falhar
    
    EXTRAÇÃO LLM (modo online):
    
    \b
      --use-cloud-generation    Usa LLM cloud para complementar regex
      --use-cloud-embeddings    Usa embeddings cloud para busca semântica
    
    EXEMPLOS:
    
    \b
      python run.py analyze documento.pdf
      python run.py --online analyze documento.pdf --profile meeting_minutes
      python run.py --online --use-cloud-generation analyze documento.pdf
      python run.py --hybrid --allow-download analyze documento.pdf
    """
    # Armazena opções no contexto
    ctx.mode_override = mode
    ctx.allow_download = allow_download
    ctx.use_cloud_generation = use_cloud_gen
    ctx.use_cloud_embeddings = use_cloud_emb
    
    # Inicializa ModeManager com as opções
    _init_mode_manager(mode, allow_download, use_cloud_gen, use_cloud_emb)


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
            console.print(f"[OK] Relatorio TXT: [green]{txt_path}[/green]")
        
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
            
            console.print(f"[OK] PDF com highlights: [green]{pdf_output}[/green]")
        
        if output_json:
            json_path = output_dir / f"{base_name}_resultado_{timestamp}.json"
            with open(json_path, 'w', encoding='utf-8') as f:
                json.dump(result.to_dict(), f, ensure_ascii=False, indent=2)
            console.print(f"[OK] Resultado JSON: [green]{json_path}[/green]")
    
    else:  # inventory (padrão)
        result = _analyze_inventory(pdf_path)
        _print_summary(result)
        
        # Gera saídas
        if txt:
            from inventory.report_generator import ReportGenerator
            txt_path = output_dir / f"{base_name}_relatorio_{timestamp}.txt"
            report_gen = ReportGenerator()
            report_gen.generate(result, txt_path, pdf_path.name)
            console.print(f"[OK] Relatorio TXT: [green]{txt_path}[/green]")
        
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
            
            console.print(f"[OK] PDF com highlights: [green]{pdf_output}[/green]")
        
        if output_json:
            json_path = output_dir / f"{base_name}_resultado_{timestamp}.json"
            with open(json_path, 'w', encoding='utf-8') as f:
                json.dump(result.to_dict(), f, ensure_ascii=False, indent=2)
            console.print(f"[OK] Resultado JSON: [green]{json_path}[/green]")
    
    console.print(f"\n[bold green]Análise concluída em {result.processing_time:.2f}s[/bold green]")
    console.print(f"Arquivos salvos em: [cyan]{output_dir}[/cyan]\n")


def _create_rag_config():
    """Cria RAGConfig baseado nas configurações do arquivo YAML."""
    from config.settings import get_settings
    from rag.rag_pipeline import RAGConfig
    from rag.chunker import ChunkingStrategy
    
    settings = get_settings()
    config_path = Path(__file__).parent.parent / "config.yaml"
    
    # Valores padrão
    chunk_size = 800
    chunk_overlap = 100
    chunking_strategy = ChunkingStrategy.SEMANTIC_SECTIONS
    top_k = 10
    min_score = 0.2
    use_hybrid_search = True
    use_reranking = True
    use_mmr = True
    mmr_diversity = 0.3
    bm25_weight = 0.4
    semantic_weight = 0.6
    generate_answers = False
    
    # Carrega configurações do YAML se existir
    if config_path.exists():
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                yaml_config = yaml.safe_load(f)
            
            # Chunking
            chunking = yaml_config.get("rag", {}).get("chunking", {})
            chunk_size = chunking.get("chunk_size", chunk_size)
            chunk_overlap = chunking.get("chunk_overlap", chunk_overlap)
            
            strategy_str = chunking.get("strategy", "semantic_sections")
            strategy_map = {
                "fixed_size": ChunkingStrategy.FIXED_SIZE,
                "sentence": ChunkingStrategy.SENTENCE,
                "paragraph": ChunkingStrategy.PARAGRAPH,
                "recursive": ChunkingStrategy.RECURSIVE,
                "semantic_sections": ChunkingStrategy.SEMANTIC_SECTIONS,
            }
            chunking_strategy = strategy_map.get(strategy_str, chunking_strategy)
            
            # Retrieval
            retrieval = yaml_config.get("rag", {}).get("retrieval", {})
            top_k = retrieval.get("top_k", top_k)
            min_score = retrieval.get("min_score", min_score)
            use_hybrid_search = retrieval.get("use_hybrid_search", use_hybrid_search)
            use_reranking = retrieval.get("use_reranking", use_reranking)
            use_mmr = retrieval.get("use_mmr", use_mmr)
            mmr_diversity = retrieval.get("mmr_diversity", mmr_diversity)
            bm25_weight = retrieval.get("bm25_weight", bm25_weight)
            semantic_weight = retrieval.get("semantic_weight", semantic_weight)
            
            # Generation
            generation = yaml_config.get("rag", {}).get("generation", {})
            generate_answers = generation.get("generate_answers", generate_answers)
            
        except Exception as e:
            logger.warning(f"Erro ao carregar config.yaml: {e}. Usando valores padrão.")
    
    # Também verifica settings para generate_answers (pode ser sobrescrito)
    if hasattr(settings, 'rag') and hasattr(settings.rag, 'generation'):
        generate_answers = settings.rag.generation.generate_answers
    
    logger.info(
        f"RAGConfig: chunking={chunking_strategy.value}, "
        f"chunk_size={chunk_size}, overlap={chunk_overlap}, "
        f"hybrid_search={use_hybrid_search}, bm25_weight={bm25_weight}"
    )
    
    return RAGConfig(
        mode="local",
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        chunking_strategy=chunking_strategy,
        top_k=top_k,
        min_score=min_score,
        use_hybrid_search=use_hybrid_search,
        use_reranking=use_reranking,
        use_mmr=use_mmr,
        mmr_diversity=mmr_diversity,
        bm25_weight=bm25_weight,
        semantic_weight=semantic_weight,
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
@click.option('--no-cache', is_flag=True, help='Desabilita cache de OCR')
def extract(pdf_path: str, output: str, no_cache: bool):
    """
    Apenas extrai texto do PDF (sem análise RAG).
    
    Útil para verificar a qualidade do OCR.
    """
    print_banner()
    
    from core.pdf_reader import PDFReader
    from core.ocr_extractor import OCRExtractor
    from core.ocr_cache import get_ocr_cache
    import time
    
    pdf_path = Path(pdf_path)
    output_dir = Path(output)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    console.print(f"\nExtraindo texto de: [bold]{pdf_path.name}[/bold]\n")
    
    reader = PDFReader()
    document = reader.read(pdf_path)
    
    # Verifica cache de OCR
    ocr_cache = get_ocr_cache()
    cached_doc = ocr_cache.get(pdf_path) if not no_cache else None
    
    if cached_doc:
        console.print("[green][CACHE] Usando texto em cache[/green]")
        # Preenche documento com texto do cache
        for i, page in enumerate(document.pages):
            if i < len(cached_doc.pages):
                page.text = cached_doc.pages[i].get("text", "")
    else:
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            task = progress.add_task("Executando OCR...", total=None)
            
            ocr_start = time.time()
            ocr = OCRExtractor()
            ocr.extract(document)
            ocr_time = time.time() - ocr_start
        
        # Salva no cache
        if not no_cache:
            pages_data = [
                {"number": p.number, "text": p.text}
                for p in document.pages
            ]
            ocr_cache.save(pdf_path, pages_data, ocr_time)
            console.print(f"[green][CACHE] Texto salvo no cache ({ocr_time:.1f}s)[/green]")
    
    # Salva texto
    output_file = output_dir / f"{pdf_path.stem}_texto.txt"
    
    with open(output_file, 'w', encoding='utf-8') as f:
        for page in document.pages:
            f.write(f"{'='*60}\n")
            f.write(f"PAGINA {page.number}\n")
            f.write(f"{'='*60}\n\n")
            f.write(page.text or "(sem texto)")
            f.write("\n\n")
    
    console.print(f"[OK] Texto extraido: [green]{output_file}[/green]")
    console.print(f"Total de paginas: {len(document.pages)}")


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
        console.print(f"  [OK] Tesseract: {', '.join(langs)}", style="green")
    except Exception as e:
        console.print(f"  [ERRO] Tesseract: {e}", style="red")
    
    # FAISS
    try:
        import faiss
        console.print("  [OK] FAISS disponivel", style="green")
    except ImportError:
        console.print("  [ERRO] FAISS nao instalado", style="red")
    
    # Sentence Transformers
    try:
        from sentence_transformers import SentenceTransformer
        console.print("  [OK] Sentence Transformers disponivel", style="green")
    except ImportError:
        console.print("  [ERRO] Sentence Transformers nao instalado", style="red")


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
    
    console.print(f"[OK] Arquivo criado: [green]{sample_path}[/green]")


# ============================================
# COMANDOS DO MÓDULO Q&A
# ============================================

@cli.command()
@click.argument('pdf_path', type=click.Path(exists=True), required=False)
@click.option('-q', '--question', default=None, help='Pergunta unica (modo nao-interativo)')
@click.option('-i', '--interactive', is_flag=True, help='Modo interativo de perguntas')
@click.option('-t', '--template', default=None, help='Nome do template a usar')
@click.option('-o', '--output', default=None, help='Arquivo para exportar conversa')
@click.option('--save-txt', 'save_txt', default=None, help='Salva resposta em arquivo TXT')
@click.option('--model', default=None, help='Modelo de linguagem (tinyllama, phi3-mini, gpt2-portuguese)')
@click.option('--no-cache', is_flag=True, help='Desabilita cache de respostas')
@click.option('--no-ocr-cache', is_flag=True, help='Desabilita cache de OCR')
@click.option('--list-templates', is_flag=True, help='Lista templates disponiveis e sai')
@click.option('--explain', is_flag=True, help='Mostra trace do DKR (Domain Knowledge Rules)')
@click.option('--no-dkr', is_flag=True, help='Desabilita DKR (regras de dominio)')
def qa(
    pdf_path: Optional[str],
    question: Optional[str],
    interactive: bool,
    template: Optional[str],
    output: Optional[str],
    save_txt: Optional[str],
    model: Optional[str],
    no_cache: bool,
    no_ocr_cache: bool,
    list_templates: bool,
    explain: bool,
    no_dkr: bool
):
    """
    Sistema de Perguntas e Respostas sobre documentos.
    
    Permite fazer perguntas em linguagem natural sobre o conteudo
    de um documento PDF e receber respostas baseadas no contexto.
    
    \b
    MODOS DE USO:
    
    \b
      Pergunta unica:
        python run.py qa documento.pdf -q "Qual e a licenca mais critica?"
    
    \b
      Modo interativo:
        python run.py qa documento.pdf -i
    
    \b
      Com template especifico:
        python run.py qa documento.pdf -q "pergunta" --template licencas_software
    
    \b
      Salvar resposta em TXT:
        python run.py qa documento.pdf -q "pergunta" --save-txt resposta.txt
    
    \b
      Usar modelo especifico:
        python run.py qa documento.pdf -q "pergunta" --model tinyllama
    
    \b
    TEMPLATES DISPONIVEIS:
    
    \b
      sistema_padrao      - Template generico (padrao)
      licencas_software   - Para documentos de licencas open source
      contratos           - Para contratos e documentos juridicos
      atas_reuniao        - Para atas de reuniao
      inventario          - Para escrituras de inventario
      geral               - Template minimo
    
    \b
    MODELOS DISPONIVEIS:
    
    \b
      tinyllama           - TinyLlama 1.1B (padrao, recomendado)
      phi3-mini           - Phi-3 Mini (melhor qualidade)
      gpt2-portuguese     - GPT-2 Portuguese (fallback)
    
    \b
    EXEMPLOS:
    
    \b
      python run.py qa analise.pdf -i --template licencas_software
      python run.py qa contrato.pdf -q "Qual o valor?" --save-txt resposta.txt
      python run.py qa documento.pdf -q "pergunta" --model tinyllama
      python run.py qa --list-templates
    """
    from qa import QAEngine, QAConfig
    
    # Lista templates se solicitado
    if list_templates:
        _list_qa_templates()
        return
    
    # Valida se PDF foi fornecido
    if not pdf_path:
        printer.print_error("E necessario fornecer um arquivo PDF.")
        console.print("Exemplo: python run.py qa documento.pdf -q \"sua pergunta\"")
        console.print("\nPara listar templates disponiveis:")
        console.print("  python run.py qa --list-templates")
        return
    
    # Valida argumentos
    if not question and not interactive:
        printer.print_warning("Use -q para pergunta unica ou -i para modo interativo.")
        console.print("Exemplo: python run.py qa documento.pdf -q \"Sua pergunta aqui\"")
        console.print("         python run.py qa documento.pdf -i")
        return
    
    # Banner
    printer.print_banner("DOCUMENT ANALYZER", "Sistema Q&A")
    
    pdf_path = Path(pdf_path)
    
    # Configura Q&A
    config = QAConfig()
    config.use_cache = not no_cache
    config.use_dkr = not no_dkr  # DKR habilitado por padrão
    
    if template:
        config.default_template = template
    
    # Configura modelo se especificado
    if model:
        config.generation_model = model
        console.print(f"[info]Modelo selecionado: {model}[/info]")
    
    # Info sobre DKR
    if no_dkr:
        console.print("[dim]DKR desabilitado[/dim]")
    
    # Inicializa engine
    qa_engine = QAEngine(config=config)
    
    # Callback de progresso
    def progress_callback(msg: str, pct: float):
        pass  # Silencioso
    
    qa_engine.progress_callback = progress_callback
    
    # Verifica cache de OCR
    from core.ocr_cache import get_ocr_cache
    ocr_cache = get_ocr_cache()
    
    if not no_ocr_cache and ocr_cache.has_cache(pdf_path):
        console.print("[green][CACHE] Usando texto em cache (OCR)[/green]")
    else:
        console.print("[yellow]Carregando documento...[/yellow]")
    
    # Carrega documento
    try:
        num_chunks = qa_engine.load_document(pdf_path, template=template)
        printer.print_success(f"Documento indexado: {num_chunks} chunks")
    except Exception as e:
        printer.print_error(f"Erro ao carregar documento: {e}")
        return
    
    doc_info = qa_engine.get_document_info()
    console.print(f"\n[Documento] [bold]{pdf_path.name}[/bold]")
    console.print(f"[Info] Paginas: {doc_info.get('pages', '?')} | Chunks: {num_chunks}")
    console.print(f"[Template] {qa_engine._current_template.name if qa_engine._current_template else 'padrao'}")
    if model:
        console.print(f"[Modelo] {model}")
    console.print()
    
    if interactive:
        _run_interactive_qa(qa_engine, output, save_txt, explain_dkr=explain)
    elif question:
        _run_single_question(qa_engine, question, save_txt, explain_dkr=explain)


def _list_qa_templates():
    """Lista templates de Q&A disponíveis."""
    from qa import TemplateLoader
    
    # Banner simples sem caracteres especiais
    console.print("\n" + "=" * 60)
    console.print("  DOCUMENT ANALYZER - Q&A TEMPLATES")
    console.print("=" * 60)
    
    loader = TemplateLoader()
    templates = loader.list_templates()
    
    console.print("\n[bold]Templates de Q&A Disponiveis:[/bold]\n")
    
    table = Table(show_header=True, header_style="bold cyan")
    table.add_column("Nome", style="cyan")
    table.add_column("Descrição", style="white")
    table.add_column("Padrão", style="green")
    
    for t in templates:
        is_default = "[X]" if t.get("is_default") else ""
        table.add_row(
            t["name"],
            t.get("description", "")[:60] + "..." if len(t.get("description", "")) > 60 else t.get("description", ""),
            is_default
        )
    
    console.print(table)
    console.print()
    console.print("[bold]Como usar um template:[/bold]")
    console.print("  python run.py qa documento.pdf -q \"pergunta\" --template nome_do_template")
    console.print()
    console.print("[bold]Como criar templates:[/bold]")
    console.print("  Veja o arquivo: instructions/qa_templates/_COMO_CRIAR_TEMPLATES.txt")
    console.print()


def _run_single_question(qa_engine, question: str, save_txt: Optional[str] = None, explain_dkr: bool = False):
    """Executa uma unica pergunta."""
    console.print(f"[bold]Pergunta:[/bold] {question}\n")
    console.print("Processando...", style="yellow")
    
    try:
        response = qa_engine.ask(question)
    except Exception as e:
        printer.print_error(f"Erro ao processar pergunta: {e}")
        return
    
    # Exibe trace do DKR se solicitado
    if explain_dkr and response.dkr_result:
        _print_dkr_trace(response.dkr_result)
    
    # Exibe resposta
    _print_qa_response(response)
    
    # Salva em TXT se solicitado
    if save_txt:
        _save_response_to_txt(question, response, save_txt)


def _save_response_to_txt(question: str, response, output_path: str):
    """Salva resposta em arquivo TXT."""
    try:
        doc_info = {}
        timestamp = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
        
        content = f"""{'=' * 60}
RESPOSTA Q&A - DOCUMENT ANALYZER
{'=' * 60}

Data: {timestamp}

{'-' * 60}
PERGUNTA:
{'-' * 60}
{question}

{'-' * 60}
RESPOSTA:
{'-' * 60}
{response.answer}

{'-' * 60}
METADADOS:
{'-' * 60}
Paginas de referencia: {', '.join(map(str, response.pages)) if response.pages else 'N/A'}
Confianca: {response.confidence:.0%}
Tempo de processamento: {response.processing_time:.2f}s
Template usado: {response.template_used}
Resposta do cache: {'Sim' if response.from_cache else 'Nao'}

{'=' * 60}
"""
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        printer.print_success(f"Resposta salva em: {output_path}")
        
    except Exception as e:
        printer.print_error(f"Erro ao salvar resposta: {e}")


def _print_dkr_trace(dkr_result):
    """Exibe trace do processamento DKR."""
    console.print("\n[bold cyan]--- DKR Trace ---[/bold cyan]")
    
    # Intent
    if dkr_result.detected_intent:
        conf = dkr_result.intent_confidence
        bar = "[green]" + "█" * int(conf * 10) + "[/green]" + "░" * (10 - int(conf * 10))
        console.print(f"  Intent: [bold]{dkr_result.detected_intent}[/bold] {bar} {conf:.0%}")
    else:
        console.print("  Intent: [dim]Nenhum detectado[/dim]")
    
    # Query expansion
    if dkr_result.query_expanded:
        console.print(f"  Query expandida: [green]Sim[/green]")
        console.print(f"    Termos: {dkr_result.expansion_terms}")
    
    # Regras
    console.print(f"  Regras avaliadas: {dkr_result.rules_evaluated}")
    
    if dkr_result.rules_triggered:
        console.print(f"  Regras ativadas: [yellow]{len(dkr_result.rules_triggered)}[/yellow]")
        for rule in dkr_result.rules_triggered:
            console.print(f"    [yellow]>[/yellow] {rule}")
    
    # Correção
    if dkr_result.was_corrected:
        console.print(f"  [bold green]Resposta CORRIGIDA[/bold green]")
        console.print(f"    Motivo: {dkr_result.correction_reason}")
    else:
        console.print(f"  Resposta: [dim]Mantida (sem correção)[/dim]")
    
    console.print(f"  Tempo DKR: {dkr_result.processing_time_ms:.1f}ms")
    console.print("[dim]--- Fim DKR Trace ---[/dim]\n")


def _run_interactive_qa(qa_engine, output_path: Optional[str], save_txt: Optional[str] = None, explain_dkr: bool = False):
    """Executa modo interativo de Q&A."""
    all_responses = []  # Para salvar todas as respostas
    
    console.print("[bold cyan]Modo Interativo de Q&A[/bold cyan]")
    console.print("Digite suas perguntas. Comandos especiais:")
    console.print("  [yellow]/sair[/yellow]      - Encerra a sessao")
    console.print("  [yellow]/limpar[/yellow]    - Limpa historico da conversa")
    console.print("  [yellow]/exportar[/yellow]  - Exporta conversa para arquivo")
    console.print("  [yellow]/template[/yellow]  - Muda o template")
    console.print("  [yellow]/modelo[/yellow]    - Muda o modelo de linguagem")
    console.print("  [yellow]/info[/yellow]      - Mostra informacoes do documento")
    if explain_dkr:
        console.print("  [cyan]/dkr[/cyan]       - Toggle trace DKR")
    console.print()
    
    while True:
        try:
            # Prompt
            user_input = console.input("[bold green]> [/bold green]").strip()
            
            if not user_input:
                continue
            
            # Comandos especiais
            if user_input.lower() == "/sair":
                console.print("\n[cyan]Encerrando sessao...[/cyan]")
                
                if output_path:
                    qa_engine.export_conversation(Path(output_path))
                    printer.print_success(f"Conversa exportada: {output_path}")
                
                # Salva em TXT se solicitado
                if save_txt and all_responses:
                    _save_session_to_txt(all_responses, save_txt)
                
                break
            
            elif user_input.lower() == "/limpar":
                qa_engine.clear_conversation()
                all_responses.clear()
                console.print("[yellow]Historico limpo.[/yellow]\n")
                continue
            
            elif user_input.lower() == "/exportar":
                export_file = f"conversa_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
                qa_engine.export_conversation(Path(export_file))
                printer.print_success(f"Conversa exportada: {export_file}")
                continue
            
            elif user_input.lower().startswith("/template"):
                parts = user_input.split(maxsplit=1)
                if len(parts) > 1:
                    try:
                        qa_engine.set_template(parts[1])
                        printer.print_success(f"Template alterado para: {parts[1]}")
                    except Exception as e:
                        printer.print_error(str(e))
                else:
                    templates = qa_engine.list_templates()
                    console.print("Templates disponiveis:")
                    for t in templates:
                        marker = " (atual)" if t.get("is_default") else ""
                        console.print(f"  * {t['name']}{marker}")
                    console.print()
                continue
            
            elif user_input.lower() == "/info":
                info = qa_engine.get_document_info()
                console.print(f"Documento: {info.get('name', 'N/A')}")
                console.print(f"Paginas: {info.get('pages', 'N/A')}")
                console.print(f"Modelo atual: {qa_engine.get_current_model()}")
                console.print(f"Perguntas nesta sessao: {qa_engine.conversation.turn_count}")
                console.print()
                continue
            
            elif user_input.lower().startswith("/modelo"):
                parts = user_input.split(maxsplit=1)
                if len(parts) > 1:
                    model_name = parts[1].strip().lower()
                    try:
                        console.print(f"Carregando modelo [cyan]{model_name}[/cyan]...", style="dim")
                        actual = qa_engine.set_model(model_name)
                        printer.print_success(f"Modelo alterado para: {actual}")
                    except Exception as e:
                        printer.print_error(f"Erro ao mudar modelo: {e}")
                        console.print("Modelos disponiveis: tinyllama, phi3-mini, gpt2-portuguese")
                else:
                    current = qa_engine.get_current_model()
                    console.print(f"Modelo atual: [cyan]{current}[/cyan]")
                    console.print("Modelos disponiveis:")
                    console.print("  * tinyllama      - TinyLlama 1.1B (recomendado)")
                    console.print("  * phi3-mini      - Phi-3 Mini (melhor qualidade)")
                    console.print("  * gpt2-portuguese - GPT-2 Portuguese (fallback)")
                    console.print()
                    console.print("Use: /modelo <nome>")
                    console.print()
                continue
            
            elif user_input.startswith("/"):
                console.print("[yellow]Comando nao reconhecido. Use /sair para encerrar.[/yellow]\n")
                continue
            
            # Processa pergunta
            console.print("Pensando...", style="dim")
            
            try:
                response = qa_engine.ask(user_input)
                # Guarda para salvar depois
                all_responses.append({"question": user_input, "response": response})
            except Exception as e:
                printer.print_error(str(e))
                continue
            
            # Exibe trace DKR se habilitado
            if explain_dkr and response.dkr_result:
                _print_dkr_trace(response.dkr_result)
            
            # Exibe resposta
            _print_qa_response(response, compact=True)
            console.print()
            
        except KeyboardInterrupt:
            console.print("\n[cyan]Sessao interrompida.[/cyan]")
            # Salva em TXT se solicitado
            if save_txt and all_responses:
                _save_session_to_txt(all_responses, save_txt)
            break
        except EOFError:
            break


def _save_session_to_txt(responses: list, output_path: str):
    """Salva sessao interativa completa em arquivo TXT."""
    try:
        timestamp = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
        
        content = f"""{'=' * 60}
SESSAO Q&A - DOCUMENT ANALYZER
{'=' * 60}

Data: {timestamp}
Total de perguntas: {len(responses)}

"""
        
        for i, item in enumerate(responses, 1):
            question = item["question"]
            response = item["response"]
            
            content += f"""{'-' * 60}
PERGUNTA {i}:
{'-' * 60}
{question}

RESPOSTA:
{response.answer}

Paginas: {', '.join(map(str, response.pages)) if response.pages else 'N/A'}
Confianca: {response.confidence:.0%}

"""
        
        content += f"{'=' * 60}\n"
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        printer.print_success(f"Sessao salva em: {output_path}")
        
    except Exception as e:
        printer.print_error(f"Erro ao salvar sessao: {e}")


def _print_qa_response(response, compact: bool = False):
    """Exibe resposta do Q&A formatada."""
    from rich.panel import Panel
    
    # Determina estilo baseado na confianca
    if response.confidence >= 0.7:
        style = "green"
        confidence_label = "Alta"
    elif response.confidence >= 0.4:
        style = "yellow"
        confidence_label = "Media"
    else:
        style = "red"
        confidence_label = "Baixa"
    
    # Formata resposta
    answer_text = response.answer
    
    # Adiciona metadados
    model_info = ""
    if response.metadata and "smart_generator" in response.metadata:
        sg_info = response.metadata["smart_generator"]
        model_info = sg_info.get("model_name", "")
    
    if not compact:
        footer = []
        if response.pages:
            footer.append(f"Paginas: {', '.join(map(str, response.pages))}")
        footer.append(f"Confianca: {response.confidence:.0%} ({confidence_label})")
        footer.append(f"Tempo: {response.processing_time:.2f}s")
        if model_info:
            footer.append(f"Modelo: {model_info}")
        if response.from_cache:
            footer.append("(Cache)")
        
        answer_text += "\n\n" + " | ".join(footer)
    else:
        footer_parts = []
        if response.pages:
            footer_parts.append(f"Paginas: {', '.join(map(str, response.pages))}")
        footer_parts.append(f"Confianca: {response.confidence:.0%}")
        if model_info:
            footer_parts.append(f"Modelo: {model_info}")
        if footer_parts:
            answer_text += f"\n\n[dim]{' | '.join(footer_parts)}[/dim]"
    
    console.print(Panel(
        answer_text,
        title="[bold]Resposta[/bold]" if not compact else None,
        border_style=style,
        padding=(1, 2)
    ))


@cli.command(name="qa-cache")
@click.option('--stats', is_flag=True, help='Mostra estatísticas do cache')
@click.option('--clear', is_flag=True, help='Limpa o cache')
@click.option('--frequent', is_flag=True, help='Mostra perguntas frequentes')
def qa_cache(stats: bool, clear: bool, frequent: bool):
    """
    Gerencia o cache do sistema Q&A.
    
    \b
    Exemplos:
      python run.py qa-cache --stats
      python run.py qa-cache --clear
      python run.py qa-cache --frequent
    """
    from qa import ResponseCache
    
    cache = ResponseCache()
    
    if clear:
        count = cache.clear()
        console.print(f"[green]Cache limpo: {count} entradas removidas[/green]")
        return
    
    if frequent:
        questions = cache.get_frequent_questions(10)
        if not questions:
            console.print("[yellow]Nenhuma pergunta no cache.[/yellow]")
            return
        
        console.print("\n[bold]Perguntas Mais Frequentes:[/bold]\n")
        table = Table(show_header=True)
        table.add_column("#", style="cyan")
        table.add_column("Pergunta")
        table.add_column("Acessos", style="green")
        
        for i, q in enumerate(questions, 1):
            table.add_row(
                str(i),
                q["question"][:60] + "..." if len(q["question"]) > 60 else q["question"],
                str(q["access_count"])
            )
        
        console.print(table)
        return
    
    # Stats (padrão)
    cache_stats = cache.get_stats()
    
    console.print("\n[bold]Estatísticas do Cache Q&A:[/bold]\n")
    table = Table(show_header=True)
    table.add_column("Métrica", style="cyan")
    table.add_column("Valor", style="green")
    
    table.add_row("Entradas", str(cache_stats.get("entries", 0)))
    table.add_row("Máximo", str(cache_stats.get("max_size", 0)))
    table.add_row("TTL (horas)", str(cache_stats.get("ttl_hours", 0)))
    table.add_row("Total de Acessos", str(cache_stats.get("total_accesses", 0)))
    table.add_row("Confiança Média", f"{cache_stats.get('avg_confidence', 0):.0%}")
    table.add_row("Persistência", "Sim" if cache_stats.get("persist_enabled") else "Não")
    
    console.print(table)
    console.print()


# ============================================
# COMANDOS DE CACHE OCR
# ============================================

@cli.command(name="ocr-cache")
@click.option('--list', 'list_cache', is_flag=True, help='Lista documentos em cache')
@click.option('--stats', is_flag=True, help='Mostra estatisticas do cache')
@click.option('--clear', is_flag=True, help='Limpa todo o cache')
@click.option('--remove', 'remove_file', default=None, help='Remove documento especifico do cache')
@click.option('--info', 'info_file', default=None, help='Mostra info de documento especifico')
@click.option('--cleanup', is_flag=True, help='Remove entradas expiradas')
def ocr_cache(
    list_cache: bool,
    stats: bool,
    clear: bool,
    remove_file: Optional[str],
    info_file: Optional[str],
    cleanup: bool
):
    """
    Gerencia o cache de extracoes OCR.
    
    O cache armazena o texto extraido de PDFs para evitar
    reprocessamento custoso do OCR.
    
    \b
    Exemplos:
      python run.py ocr-cache --list
      python run.py ocr-cache --stats
      python run.py ocr-cache --clear
      python run.py ocr-cache --remove documento.pdf
      python run.py ocr-cache --info documento.pdf
      python run.py ocr-cache --cleanup
    """
    from core.ocr_cache import get_ocr_cache
    from rich.table import Table
    
    cache = get_ocr_cache()
    
    printer.print_banner("DOCUMENT ANALYZER", "Cache OCR")
    
    if clear:
        count = cache.clear()
        printer.print_success(f"Cache limpo: {count} entradas removidas")
        return
    
    if cleanup:
        count = cache.cleanup_expired()
        printer.print_success(f"Limpeza: {count} entradas expiradas removidas")
        return
    
    if remove_file:
        count = cache.remove_by_name(remove_file)
        if count > 0:
            printer.print_success(f"Removido: {count} entrada(s) para '{remove_file}'")
        else:
            printer.print_warning(f"Nenhuma entrada encontrada para '{remove_file}'")
        return
    
    if info_file:
        entry = cache.get_entry_info(info_file)
        if entry:
            console.print(f"\n[bold]Informacoes do Cache:[/bold]\n")
            table = Table(show_header=False, safe_box=True)
            table.add_column("Campo", style="cyan")
            table.add_column("Valor", style="green")
            
            table.add_row("Arquivo", entry.file_name)
            table.add_row("Hash", entry.file_hash[:16] + "...")
            table.add_row("Paginas", str(entry.num_pages))
            table.add_row("Palavras", f"{entry.total_words:,}")
            table.add_row("Tamanho Original", f"{entry.file_size / 1024 / 1024:.2f} MB")
            table.add_row("Extraido em", entry.extracted_at[:19])
            table.add_row("Tempo de Extracao", f"{entry.extraction_time_seconds:.1f}s")
            table.add_row("Idade", f"{entry.age_hours:.1f} horas")
            
            console.print(table)
        else:
            printer.print_warning(f"Documento '{info_file}' nao encontrado no cache")
        return
    
    if list_cache:
        entries = cache.list_entries()
        
        if not entries:
            printer.print_warning("Nenhum documento no cache OCR.")
            return
        
        console.print(f"\n[bold]Documentos em Cache: {len(entries)}[/bold]\n")
        
        table = Table(show_header=True, safe_box=True)
        table.add_column("#", style="cyan", width=4)
        table.add_column("Arquivo", style="green")
        table.add_column("Pags", style="yellow", width=6)
        table.add_column("Palavras", style="white", width=10)
        table.add_column("Tempo OCR", style="magenta", width=10)
        table.add_column("Idade", style="dim", width=10)
        
        for i, entry in enumerate(entries, 1):
            age_str = f"{entry.age_hours:.0f}h" if entry.age_hours < 48 else f"{entry.age_hours/24:.0f}d"
            table.add_row(
                str(i),
                entry.file_name[:40] + "..." if len(entry.file_name) > 40 else entry.file_name,
                str(entry.num_pages),
                f"{entry.total_words:,}",
                f"{entry.extraction_time_seconds:.1f}s",
                age_str
            )
        
        console.print(table)
        console.print()
        return
    
    # Stats (padrao)
    cache_stats = cache.get_stats()
    
    console.print("\n[bold]Estatisticas do Cache OCR:[/bold]\n")
    
    table = Table(show_header=False, safe_box=True)
    table.add_column("Metrica", style="cyan")
    table.add_column("Valor", style="green")
    
    table.add_row("Status", "Habilitado" if cache_stats.get("enabled") else "Desabilitado")
    table.add_row("Documentos em Cache", str(cache_stats.get("total_entries", 0)))
    table.add_row("Total de Paginas", str(cache_stats.get("total_pages", 0)))
    table.add_row("Total de Palavras", f"{cache_stats.get('total_words', 0):,}")
    table.add_row("Tamanho Original", f"{cache_stats.get('total_original_size_mb', 0):.2f} MB")
    table.add_row("Tamanho do Cache", f"{cache_stats.get('total_cache_size_mb', 0):.2f} MB")
    table.add_row("Tempo Total Salvo", f"{cache_stats.get('total_time_saved_seconds', 0):.1f}s")
    table.add_row("Validade Maxima", f"{cache_stats.get('max_age_hours', 0)} horas")
    table.add_row("Diretorio", cache_stats.get("cache_dir", "N/A"))
    
    console.print(table)
    console.print()


# ============================================
# COMANDOS DE MODELOS
# ============================================

@cli.command(name="models")
@click.option('--list', 'list_models', is_flag=True, help='Lista modelos disponiveis')
@click.option('--info', 'model_name', default=None, help='Mostra info de modelo especifico')
@click.option('--check', is_flag=True, help='Verifica quais modelos estao instalados')
def models_cmd(list_models: bool, model_name: Optional[str], check: bool):
    """
    Gerencia modelos de linguagem para geracao de respostas.
    
    O sistema suporta:
    - Modelos HuggingFace (GPT-2 Portuguese)
    - Modelos GGUF quantizados (TinyLlama, Phi-3, Mistral)
    
    \b
    Exemplos:
      python run.py models --list
      python run.py models --info tinyllama
      python run.py models --check
    """
    from rich.table import Table
    
    printer.print_banner("DOCUMENT ANALYZER", "Gerenciador de Modelos")
    
    # Modelos disponiveis
    all_models = [
        {
            "id": "gpt2-portuguese",
            "name": "GPT-2 Small Portuguese",
            "type": "huggingface",
            "size": "~500 MB",
            "ram": "~2 GB",
            "quality": "Basico",
            "path": "./models/generator/models--pierreguillou--gpt2-small-portuguese",
            "description": "Modelo leve, qualidade limitada para Q&A"
        },
        {
            "id": "tinyllama",
            "name": "TinyLlama-1.1B-Chat",
            "type": "gguf",
            "size": "~670 MB",
            "ram": "~2 GB",
            "quality": "Bom",
            "path": "./models/generator/tinyllama-1.1b-chat-v1.0.Q4_K_M.gguf",
            "description": "Equilibrio entre tamanho e qualidade (RECOMENDADO)",
            "default": True
        },
        {
            "id": "phi3-mini",
            "name": "Phi-3-Mini-4K-Instruct",
            "type": "gguf",
            "size": "~2.3 GB",
            "ram": "~6 GB",
            "quality": "Excelente",
            "path": "./models/generator/Phi-3-mini-4k-instruct-q4.gguf",
            "description": "Alta qualidade, requer mais recursos"
        },
        {
            "id": "mistral-7b",
            "name": "Mistral-7B-Instruct",
            "type": "gguf",
            "size": "~4 GB",
            "ram": "~8 GB",
            "quality": "Excelente",
            "path": "./models/generator/mistral-7b-instruct-v0.2.Q4_K_M.gguf",
            "description": "Melhor qualidade, requer hardware potente"
        },
    ]
    
    if model_name:
        # Info de modelo especifico
        model = next((m for m in all_models if m["id"] == model_name), None)
        
        if not model:
            printer.print_error(f"Modelo '{model_name}' nao encontrado")
            console.print("\nModelos disponiveis:")
            for m in all_models:
                console.print(f"  - {m['id']}")
            return
        
        model_path = Path(model["path"])
        exists = model_path.exists()
        
        console.print(f"\n[bold]Modelo: {model['name']}[/bold]\n")
        
        table = Table(show_header=False, safe_box=True)
        table.add_column("Campo", style="cyan")
        table.add_column("Valor", style="green")
        
        table.add_row("ID", model["id"])
        table.add_row("Tipo", model["type"].upper())
        table.add_row("Tamanho", model["size"])
        table.add_row("RAM Necessaria", model["ram"])
        table.add_row("Qualidade", model["quality"])
        table.add_row("Descricao", model["description"])
        table.add_row("Caminho", model["path"])
        table.add_row("Instalado", "[green]SIM[/green]" if exists else "[red]NAO[/red]")
        if model.get("default"):
            table.add_row("Padrao", "[yellow]SIM[/yellow]")
        
        console.print(table)
        
        if not exists:
            console.print("\n[yellow]Para instalar este modelo:[/yellow]")
            console.print(f"  Veja: docs/MODELOS_OFFLINE.md")
        
        return
    
    if check:
        from rag.smart_generator import (
            check_llama_cpp_available,
            list_available_models as list_smart_models,
            get_best_available_model
        )
        
        # Verifica modelos instalados
        console.print("\n[bold]Verificando dependencias...[/bold]\n")
        
        # Verifica llama-cpp-python (necessario para GGUF)
        llama_cpp_installed = check_llama_cpp_available()
        if llama_cpp_installed:
            console.print("  [green][OK][/green] llama-cpp-python")
        else:
            console.print("  [red][X][/red] llama-cpp-python (necessario para TinyLlama)")
            console.print("        [dim]Execute: .\\scripts\\install_llama_cpp.ps1[/dim]")
        
        console.print("\n[bold]Verificando modelos...[/bold]\n")
        
        models = list_smart_models()
        available_count = 0
        
        for model in models:
            if model["available"]:
                console.print(f"  [green][OK][/green] {model['name']}")
                available_count += 1
            else:
                reason = f" ({model['reason']})" if model['reason'] else ""
                console.print(f"  [red][X][/red] {model['name']}{reason}")
        
        console.print(f"\n[bold]Modelos disponiveis: {available_count}/{len(models)}[/bold]")
        
        # Mostra qual modelo sera usado
        best_id, best_config = get_best_available_model()
        console.print(f"\n[bold cyan]Modelo que sera usado: {best_config['name']}[/bold cyan]")
        
        if best_id == "gpt2-portuguese" and not llama_cpp_installed:
            console.print("\n[yellow]Para usar TinyLlama (melhor qualidade):[/yellow]")
            console.print("  1. Execute: .\\scripts\\install_llama_cpp.ps1")
            console.print("  2. Ou: pip install llama-cpp-python")
            console.print("\n  O modelo TinyLlama ja esta baixado!")
        
        return
    
    # Lista modelos (padrao)
    console.print("\n[bold]Modelos de Linguagem Disponiveis:[/bold]\n")
    
    table = Table(show_header=True, safe_box=True)
    table.add_column("ID", style="cyan")
    table.add_column("Nome", style="green")
    table.add_column("Tipo", style="yellow")
    table.add_column("Tamanho", style="white")
    table.add_column("Qualidade", style="magenta")
    table.add_column("Status", style="white")
    
    for model in all_models:
        model_path = Path(model["path"])
        exists = model_path.exists()
        
        status = "[OK]" if exists else "[X]"
        if model.get("default"):
            status += " (Padrao)"
        
        table.add_row(
            model["id"],
            model["name"],
            model["type"].upper(),
            model["size"],
            model["quality"],
            status
        )
    
    console.print(table)
    console.print()
    console.print("[bold]Como usar um modelo especifico:[/bold]")
    console.print("  Configure no config.yaml ou use --model no comando qa")
    console.print()
    console.print("[bold]Para instalar modelos:[/bold]")
    console.print("  Veja: docs/MODELOS_OFFLINE.md")
    console.print()


def main():
    """Ponto de entrada principal."""
    try:
        cli()
    except Exception as e:
        try:
            printer.print_error(str(e))
        except Exception:
            print(f"ERRO: {e}")
        logger.exception("Erro na execucao")
        sys.exit(1)


# ============================================
# COMANDOS DO MÓDULO DKR
# ============================================

@cli.command()
@click.argument('action', type=click.Choice(['validate', 'test', 'info', 'list', 'wizard', 'repl']))
@click.argument('file_path', type=click.Path(), required=False)
@click.option('-q', '--question', default=None, help='Pergunta para testar (com action=test)')
@click.option('-a', '--answer', default=None, help='Resposta simulada para testar')
@click.option('-d', '--dir', 'rules_dir', default='domain_rules', help='Diretório dos arquivos .rules')
def dkr(action: str, file_path: Optional[str], question: Optional[str], answer: Optional[str], rules_dir: str):
    """
    Gerencia Domain Knowledge Rules (DKR).
    
    Sistema de regras de domínio para melhorar acurácia das respostas.
    
    \b
    AÇÕES DISPONÍVEIS:
    
    \b
      validate  - Valida sintaxe e semântica de um arquivo .rules
      test      - Testa regras com pergunta/resposta simulada
      info      - Exibe informações de um arquivo .rules
      list      - Lista arquivos .rules disponíveis
      wizard    - Assistente guiado para criar novo arquivo .rules
      repl      - REPL interativo para testar regras
    
    \b
    EXEMPLOS:
    
    \b
      python run.py dkr validate domain_rules/licencas_software.rules
      python run.py dkr test domain_rules/licencas_software.rules -q "pergunta" -a "resposta"
      python run.py dkr info domain_rules/licencas_software.rules
      python run.py dkr list
      python run.py dkr wizard
      python run.py dkr repl domain_rules/licencas_software.rules
    """
    from pathlib import Path
    
    if action == 'wizard':
        # Wizard para criar novo arquivo
        from dkr.wizard import run_wizard
        result = run_wizard(Path(rules_dir))
        if result:
            printer.print_success(f"Arquivo criado: {result}")
        return
    
    if action == 'repl':
        # REPL interativo
        from dkr.repl import run_repl
        run_repl(file_path)
        return
    
    # Outros comandos via CLI
    from dkr.cli import DKRCli
    
    cli_dkr = DKRCli(rules_dir=Path(rules_dir))
    
    if action == 'list':
        args = ['list', '-d', rules_dir]
    elif action == 'validate':
        if not file_path:
            printer.print_error("Forneça o caminho do arquivo .rules")
            return
        args = ['validate', file_path]
    elif action == 'info':
        if not file_path:
            printer.print_error("Forneça o caminho do arquivo .rules")
            return
        args = ['info', file_path]
    elif action == 'test':
        if not file_path:
            printer.print_error("Forneça o caminho do arquivo .rules")
            return
        args = ['test', file_path]
        if question:
            args.extend(['-q', question])
        if answer:
            args.extend(['-a', answer])
    else:
        printer.print_error(f"Ação desconhecida: {action}")
        return
    
    exit_code = cli_dkr.run(args)
    sys.exit(exit_code)


if __name__ == "__main__":
    main()

