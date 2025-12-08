"""Pipeline de processamento completo."""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, List, Optional

from ..config.settings import Settings, get_settings
from ..core.pdf_reader import PDFReader
from ..core.ocr_extractor import OCRExtractor
from ..core.text_validator import TextValidator
from ..core.instruction_parser import InstructionParser, ParsedInstructions
from ..core.text_searcher import TextSearcher
from ..core.output_generator import OutputGenerator
from ..models.document import Document
from ..models.extraction_result import ExtractionResult, ValidationResult
from ..models.search_result import SearchResult

logger = logging.getLogger(__name__)


@dataclass
class PipelineResult:
    """Resultado completo do pipeline."""
    
    success: bool = False
    document: Optional[Document] = None
    extraction_result: Optional[ExtractionResult] = None
    validation_result: Optional[ValidationResult] = None
    search_result: Optional[SearchResult] = None
    output_files: dict = field(default_factory=dict)
    total_time: float = 0.0
    errors: List[str] = field(default_factory=list)
    
    def add_error(self, error: str) -> None:
        """Adiciona erro ao resultado."""
        self.errors.append(error)
        self.success = False


class Pipeline:
    """
    Pipeline de processamento de documentos.
    
    Orquestra todo o fluxo de processamento:
    1. Leitura do PDF
    2. Extração OCR
    3. Validação do texto
    4. Parsing de instruções
    5. Busca de texto
    6. Geração de saída
    """
    
    def __init__(
        self,
        settings: Optional[Settings] = None,
        progress_callback: Optional[Callable[[str, float], None]] = None
    ):
        """
        Inicializa o pipeline.
        
        Args:
            settings: Configurações do aplicativo.
            progress_callback: Callback para progresso (mensagem, percentual).
        """
        self.settings = settings or get_settings()
        self.progress_callback = progress_callback
        
        # Componentes do pipeline
        self._pdf_reader: Optional[PDFReader] = None
        self._ocr_extractor: Optional[OCRExtractor] = None
        self._text_validator: Optional[TextValidator] = None
        self._instruction_parser: Optional[InstructionParser] = None
        self._text_searcher: Optional[TextSearcher] = None
        self._output_generator: Optional[OutputGenerator] = None
    
    def _report_progress(self, message: str, percent: float) -> None:
        """Reporta progresso se callback configurado."""
        logger.info(f"[{percent:.0%}] {message}")
        if self.progress_callback:
            self.progress_callback(message, percent)
    
    @property
    def pdf_reader(self) -> PDFReader:
        """Obtém leitor de PDF lazy-loaded."""
        if self._pdf_reader is None:
            self._pdf_reader = PDFReader(self.settings)
        return self._pdf_reader
    
    @property
    def ocr_extractor(self) -> OCRExtractor:
        """Obtém extrator OCR lazy-loaded."""
        if self._ocr_extractor is None:
            self._ocr_extractor = OCRExtractor(self.settings)
        return self._ocr_extractor
    
    @property
    def text_validator(self) -> TextValidator:
        """Obtém validador de texto lazy-loaded."""
        if self._text_validator is None:
            self._text_validator = TextValidator(self.settings)
        return self._text_validator
    
    @property
    def instruction_parser(self) -> InstructionParser:
        """Obtém parser de instruções lazy-loaded."""
        if self._instruction_parser is None:
            self._instruction_parser = InstructionParser(self.settings)
        return self._instruction_parser
    
    @property
    def text_searcher(self) -> TextSearcher:
        """Obtém buscador de texto lazy-loaded."""
        if self._text_searcher is None:
            self._text_searcher = TextSearcher(self.settings)
        return self._text_searcher
    
    @property
    def output_generator(self) -> OutputGenerator:
        """Obtém gerador de saída lazy-loaded."""
        if self._output_generator is None:
            self._output_generator = OutputGenerator(self.settings)
        return self._output_generator
    
    def run(
        self,
        pdf_path: Path,
        instructions_path: Path,
        output_dir: Path
    ) -> PipelineResult:
        """
        Executa o pipeline completo.
        
        Args:
            pdf_path: Caminho do arquivo PDF.
            instructions_path: Caminho do arquivo de instruções.
            output_dir: Diretório de saída.
        
        Returns:
            PipelineResult: Resultado completo do processamento.
        """
        result = PipelineResult()
        start_time = time.time()
        
        logger.info(f"Iniciando pipeline para: {pdf_path}")
        
        try:
            # Etapa 1: Leitura do PDF
            self._report_progress("Lendo PDF...", 0.1)
            document = self.pdf_reader.read(pdf_path)
            result.document = document
            
            # Etapa 2: Extração OCR
            self._report_progress("Extraindo texto com OCR...", 0.3)
            extraction_result = self.ocr_extractor.extract(document)
            result.extraction_result = extraction_result
            
            if not extraction_result.success:
                result.add_error("Falha na extração OCR")
                return result
            
            # Etapa 3: Validação do texto
            self._report_progress("Validando texto extraído...", 0.4)
            validation_result = self.text_validator.validate(document)
            result.validation_result = validation_result
            
            if not validation_result.is_valid and not validation_result.is_partial:
                result.add_error(
                    f"Validação falhou: {', '.join(validation_result.issues)}"
                )
                # Continua mesmo com validação parcial
            
            # Etapa 4: Parsing de instruções
            self._report_progress("Processando instruções...", 0.5)
            instructions = self.instruction_parser.parse_file(instructions_path)
            
            if instructions.count == 0:
                result.add_error("Nenhuma instrução encontrada no arquivo")
                return result
            
            # Etapa 5: Busca de texto
            self._report_progress("Buscando informações...", 0.6)
            search_result = self.text_searcher.search(document, instructions)
            result.search_result = search_result
            
            # Etapa 6: Geração de saída
            self._report_progress("Gerando arquivos de saída...", 0.8)
            output_files = self.output_generator.generate_all(
                document, search_result, output_dir
            )
            result.output_files = output_files
            
            # Finalização
            result.success = True
            self._report_progress("Pipeline concluído!", 1.0)
            
        except FileNotFoundError as e:
            result.add_error(f"Arquivo não encontrado: {e}")
        except Exception as e:
            logger.exception("Erro no pipeline")
            result.add_error(f"Erro durante processamento: {e}")
        
        result.total_time = time.time() - start_time
        logger.info(f"Pipeline finalizado em {result.total_time:.2f}s")
        
        return result
    
    def run_extraction_only(self, pdf_path: Path) -> PipelineResult:
        """
        Executa apenas extração de texto (sem busca).
        
        Args:
            pdf_path: Caminho do arquivo PDF.
        
        Returns:
            PipelineResult: Resultado da extração.
        """
        result = PipelineResult()
        start_time = time.time()
        
        try:
            self._report_progress("Lendo PDF...", 0.2)
            document = self.pdf_reader.read(pdf_path)
            result.document = document
            
            self._report_progress("Extraindo texto com OCR...", 0.5)
            extraction_result = self.ocr_extractor.extract(document)
            result.extraction_result = extraction_result
            
            self._report_progress("Validando texto...", 0.8)
            validation_result = self.text_validator.validate(document)
            result.validation_result = validation_result
            
            result.success = extraction_result.success
            self._report_progress("Extração concluída!", 1.0)
            
        except Exception as e:
            result.add_error(str(e))
        
        result.total_time = time.time() - start_time
        return result
    
    def run_search_only(
        self,
        text: str,
        instructions_path: Path
    ) -> SearchResult:
        """
        Executa apenas busca em texto já extraído.
        
        Args:
            text: Texto para buscar.
            instructions_path: Caminho do arquivo de instruções.
        
        Returns:
            SearchResult: Resultado da busca.
        """
        # Cria documento fake com o texto
        from ..models.document import Document, Page
        
        document = Document(source_path=Path("memory"))
        document.add_page(Page(number=1, text=text))
        
        instructions = self.instruction_parser.parse_file(instructions_path)
        
        return self.text_searcher.search(document, instructions)


class PipelineBuilder:
    """Builder para configurar pipeline customizado."""
    
    def __init__(self):
        """Inicializa o builder."""
        self._settings: Optional[Settings] = None
        self._progress_callback: Optional[Callable] = None
        self._skip_validation: bool = False
        self._skip_search: bool = False
    
    def with_settings(self, settings: Settings) -> "PipelineBuilder":
        """Configura settings customizadas."""
        self._settings = settings
        return self
    
    def with_progress_callback(
        self,
        callback: Callable[[str, float], None]
    ) -> "PipelineBuilder":
        """Configura callback de progresso."""
        self._progress_callback = callback
        return self
    
    def skip_validation(self) -> "PipelineBuilder":
        """Pula etapa de validação."""
        self._skip_validation = True
        return self
    
    def skip_search(self) -> "PipelineBuilder":
        """Pula etapa de busca."""
        self._skip_search = True
        return self
    
    def build(self) -> Pipeline:
        """Constrói o pipeline configurado."""
        return Pipeline(
            settings=self._settings,
            progress_callback=self._progress_callback
        )
