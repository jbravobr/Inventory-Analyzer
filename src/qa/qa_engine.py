"""
Motor Principal de Q&A (Perguntas e Respostas).

Orquestra todos os componentes para responder perguntas
sobre documentos PDF.

Funciona em modo offline e online, seguindo a mesma
lógica do restante do sistema.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional, Dict, Any, Callable

from config.settings import Settings, get_settings
from config.mode_manager import get_mode_manager, ModeManager
from models.document import Document
from core.pdf_reader import PDFReader
from core.ocr_extractor import OCRExtractor
from rag.rag_pipeline import RAGPipeline, RAGConfig
from rag.generator import get_response_generator, ResponseGenerator

from .template_loader import TemplateLoader, PromptTemplate
from .conversation import Conversation, ConversationTurn, MemoryType
from .knowledge_base import KnowledgeBase
from .qa_validator import QAValidator, ValidationResult
from .cache import ResponseCache

logger = logging.getLogger(__name__)


@dataclass
class QAConfig:
    """Configuração do sistema de Q&A."""
    
    # Template
    default_template: str = "sistema_padrao"
    templates_dir: str = "./instructions/qa_templates"
    auto_detect_template: bool = True
    
    # RAG
    top_k: int = 10
    min_score: float = 0.2
    use_hybrid_search: bool = True
    use_mmr: bool = True
    mmr_diversity: float = 0.3
    
    # Conversa
    max_conversation_turns: int = 10
    memory_type: str = "sliding_window"  # full, summary, sliding_window
    
    # Validação
    validate_responses: bool = True
    min_confidence: float = 0.5
    strict_validation: bool = False
    
    # Cache
    use_cache: bool = True
    cache_ttl_hours: int = 24
    
    # Geracao
    generate_answers: bool = True
    include_page_references: bool = True
    generation_model: Optional[str] = None  # tinyllama, phi3-mini, gpt2-portuguese
    
    @classmethod
    def from_settings(cls, settings: Settings) -> "QAConfig":
        """Cria configuração a partir de Settings."""
        config = cls()
        
        # Carrega configurações de qa se existirem
        if hasattr(settings, 'qa'):
            qa_settings = settings.qa
            
            if hasattr(qa_settings, 'default_template'):
                config.default_template = qa_settings.default_template
            if hasattr(qa_settings, 'templates_dir'):
                config.templates_dir = qa_settings.templates_dir
            if hasattr(qa_settings, 'auto_detect_template'):
                config.auto_detect_template = qa_settings.auto_detect_template
        
        # Configurações do RAG
        if hasattr(settings, 'rag'):
            rag = settings.rag
            if hasattr(rag, 'retrieval'):
                config.top_k = rag.retrieval.top_k
                config.min_score = rag.retrieval.min_score
                config.use_hybrid_search = rag.retrieval.use_hybrid_search
                config.use_mmr = rag.retrieval.use_mmr
                config.mmr_diversity = rag.retrieval.mmr_diversity
        
        return config


@dataclass
class QAResponse:
    """Resposta de uma pergunta do Q&A."""
    
    question: str
    answer: str
    pages: List[int]
    confidence: float
    context_used: str
    template_used: str
    processing_time: float
    from_cache: bool = False
    validation: Optional[ValidationResult] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> dict:
        return {
            "question": self.question,
            "answer": self.answer,
            "pages": self.pages,
            "confidence": self.confidence,
            "processing_time": self.processing_time,
            "from_cache": self.from_cache,
            "template": self.template_used,
            "validation": self.validation.to_dict() if self.validation else None,
        }
    
    def format_response(self, include_metadata: bool = False) -> str:
        """Formata a resposta para exibição."""
        lines = [self.answer]
        
        if self.pages:
            lines.append(f"\n📚 Páginas de referência: {', '.join(map(str, self.pages))}")
        
        if include_metadata:
            lines.append(f"🎯 Confiança: {self.confidence:.0%}")
            lines.append(f"⏱️ Tempo: {self.processing_time:.2f}s")
            if self.from_cache:
                lines.append("💾 Resposta do cache")
        
        return "\n".join(lines)


class QAEngine:
    """
    Motor principal de Q&A sobre documentos.
    
    Integra RAG, templates, validação e cache para responder
    perguntas sobre documentos PDF.
    
    Suporta modo offline e online, seguindo a configuração
    do sistema.
    """
    
    def __init__(
        self,
        config: Optional[QAConfig] = None,
        settings: Optional[Settings] = None,
        mode_manager: Optional[ModeManager] = None,
        progress_callback: Optional[Callable[[str, float], None]] = None
    ):
        """
        Inicializa o motor de Q&A.
        
        Args:
            config: Configuração do Q&A
            settings: Configurações gerais
            mode_manager: Gerenciador de modo offline/online
            progress_callback: Callback para progresso
        """
        self.settings = settings or get_settings()
        self.mode_manager = mode_manager or get_mode_manager()
        self.config = config or QAConfig.from_settings(self.settings)
        self.progress_callback = progress_callback
        
        # Componentes
        self._template_loader: Optional[TemplateLoader] = None
        self._rag_pipeline: Optional[RAGPipeline] = None
        self._generator: Optional[ResponseGenerator] = None
        self._validator: Optional[QAValidator] = None
        self._cache: Optional[ResponseCache] = None
        self._knowledge_base: Optional[KnowledgeBase] = None
        
        # Estado
        self._document: Optional[Document] = None
        self._document_name: str = ""
        self._conversation: Optional[Conversation] = None
        self._current_template: Optional[PromptTemplate] = None
        self._initialized = False
    
    def _report_progress(self, message: str, percent: float) -> None:
        """Reporta progresso."""
        logger.info(f"[{percent:.0%}] {message}")
        if self.progress_callback:
            self.progress_callback(message, percent)
    
    @property
    def template_loader(self) -> TemplateLoader:
        """Obtém o carregador de templates."""
        if self._template_loader is None:
            self._template_loader = TemplateLoader(
                templates_dir=Path(self.config.templates_dir),
                default_template=self.config.default_template
            )
            self._template_loader.load_all()
        return self._template_loader
    
    @property
    def validator(self) -> QAValidator:
        """Obtém o validador."""
        if self._validator is None:
            self._validator = QAValidator(
                min_confidence=self.config.min_confidence,
                strict_mode=self.config.strict_validation
            )
        return self._validator
    
    @property
    def cache(self) -> ResponseCache:
        """Obtém o cache."""
        if self._cache is None:
            self._cache = ResponseCache(
                ttl_hours=self.config.cache_ttl_hours,
                persist=True
            )
        return self._cache
    
    @property
    def knowledge_base(self) -> KnowledgeBase:
        """Obtém a base de conhecimento."""
        if self._knowledge_base is None:
            self._knowledge_base = KnowledgeBase()
        return self._knowledge_base
    
    @property
    def conversation(self) -> Conversation:
        """Obtém a conversa atual."""
        if self._conversation is None:
            memory_type = MemoryType(self.config.memory_type)
            self._conversation = Conversation(
                max_turns=self.config.max_conversation_turns,
                memory_type=memory_type,
                document_name=self._document_name
            )
        return self._conversation
    
    def load_document(
        self,
        pdf_path: Path,
        template: Optional[str] = None
    ) -> int:
        """
        Carrega e indexa um documento PDF.
        
        Args:
            pdf_path: Caminho do PDF
            template: Nome do template a usar (opcional)
        
        Returns:
            int: Número de chunks indexados
        """
        self._report_progress("Carregando documento...", 0.1)
        
        pdf_path = Path(pdf_path)
        self._document_name = pdf_path.name
        
        # Lê o PDF
        reader = PDFReader(self.settings)
        self._document = reader.read(pdf_path)
        
        self._report_progress("Extraindo texto com OCR...", 0.2)
        
        # Extrai texto
        ocr = OCRExtractor(self.settings)
        ocr.extract(self._document)
        
        self._report_progress("Indexando documento...", 0.4)
        
        # Configura e indexa no RAG
        rag_config = RAGConfig(
            mode="local" if self.mode_manager.is_offline else "cloud",
            top_k=self.config.top_k,
            min_score=self.config.min_score,
            use_hybrid_search=self.config.use_hybrid_search,
            use_mmr=self.config.use_mmr,
            mmr_diversity=self.config.mmr_diversity,
            generate_answers=self.config.generate_answers,
        )
        
        self._rag_pipeline = RAGPipeline(rag_config, self.settings)
        num_chunks = self._rag_pipeline.index_document(self._document)
        
        self._report_progress("Extraindo conhecimento estruturado...", 0.7)
        
        # Indexa na base de conhecimento
        full_text = self._document.full_text
        pages_text = [p.text for p in self._document.pages]
        self.knowledge_base.index_document(
            full_text,
            self._document_name,
            pages_text
        )
        
        self._report_progress("Selecionando template...", 0.9)
        
        # Seleciona template
        self._select_template(template, full_text[:5000])
        
        # Reinicia conversa
        self._conversation = None
        
        self._initialized = True
        self._report_progress(f"Documento carregado: {num_chunks} chunks", 1.0)
        
        return num_chunks
    
    def _select_template(
        self,
        template_name: Optional[str],
        sample_text: str
    ) -> None:
        """Seleciona o template a usar."""
        if template_name:
            self._current_template = self.template_loader.get_template(template_name)
            logger.info(f"Template selecionado: {template_name}")
            return
        
        # Auto-detecção
        if self.config.auto_detect_template:
            # Regras de detecção (podem vir do config.yaml)
            rules = [
                {"pattern": r"licen[cç]a|GPL|MIT|Apache|open.?source|AGPL|LGPL", "template": "licencas_software"},
                {"pattern": r"contrato|claus|locação|prestação|parte|contratante", "template": "contratos"},
                {"pattern": r"ata|reunião|assembleia|quotista|delibera", "template": "atas_reuniao"},
                {"pattern": r"inventário|herdeiro|espólio|partilha|falecido", "template": "inventario"},
            ]
            
            detected = self.template_loader.detect_template(sample_text, rules)
            if detected:
                self._current_template = self.template_loader.get_template(detected)
                logger.info(f"Template detectado automaticamente: {detected}")
                return
        
        # Usa template padrão
        self._current_template = self.template_loader.get_template()
        logger.info(f"Usando template padrão: {self.config.default_template}")
    
    def ask(
        self,
        question: str,
        template: Optional[str] = None,
        use_cache: Optional[bool] = None
    ) -> QAResponse:
        """
        Faz uma pergunta sobre o documento.
        
        Args:
            question: Pergunta do usuário
            template: Template específico (opcional)
            use_cache: Usar cache (None = usa config)
        
        Returns:
            QAResponse com a resposta
        """
        if not self._initialized:
            raise RuntimeError(
                "Nenhum documento carregado. "
                "Use load_document() primeiro."
            )
        
        start_time = time.time()
        
        # Verifica se é pergunta de acompanhamento
        if self.conversation.is_follow_up_question(question):
            enriched_question = self.conversation.enrich_follow_up_question(question)
            logger.debug(f"Pergunta enriquecida: {enriched_question}")
        else:
            enriched_question = question
        
        # Seleciona template se especificado
        if template:
            prompt_template = self.template_loader.get_template(template)
        else:
            prompt_template = self._current_template
        
        template_name = prompt_template.name if prompt_template else "fallback"
        
        # Verifica cache
        should_use_cache = use_cache if use_cache is not None else self.config.use_cache
        
        if should_use_cache:
            # Obtém contexto primeiro para verificar cache
            retrieval = self._rag_pipeline.query(
                enriched_question,
                generate_response=False
            )
            context = retrieval.retrieval_result.context
            pages = retrieval.retrieval_result.pages
            
            cached = self.cache.get(
                question=question,
                document_name=self._document_name,
                context=context,
                template=template_name
            )
            
            if cached:
                logger.info("Resposta obtida do cache")
                
                # Adiciona ao histórico
                self.conversation.add_turn(
                    question=question,
                    answer=cached.answer,
                    pages=cached.pages,
                    confidence=cached.confidence
                )
                
                return QAResponse(
                    question=question,
                    answer=cached.answer,
                    pages=cached.pages,
                    confidence=cached.confidence,
                    context_used=context,
                    template_used=template_name,
                    processing_time=time.time() - start_time,
                    from_cache=True,
                )
        
        # Busca contexto se não buscou ainda
        if not should_use_cache:
            retrieval = self._rag_pipeline.query(
                enriched_question,
                generate_response=False
            )
            context = retrieval.retrieval_result.context
            pages = retrieval.retrieval_result.pages
        
        # Gera resposta
        answer = self._generate_answer(
            question=enriched_question,
            context=context,
            pages=pages,
            template=prompt_template
        )
        
        # Valida resposta
        validation = None
        if self.config.validate_responses:
            validation = self.validator.validate(
                question=question,
                answer=answer,
                context=context,
                pages=pages
            )
            
            if not validation.is_valid:
                logger.warning(f"Resposta inválida: {validation.issues}")
        
        # Calcula confiança
        confidence = self._calculate_confidence(retrieval, validation)
        
        # Adiciona referências de página se configurado
        if self.config.include_page_references and pages:
            if not any(str(p) in answer for p in pages):
                answer += f"\n\n(Fonte: página(s) {', '.join(map(str, pages))})"
        
        # Salva no cache
        if should_use_cache:
            self.cache.set(
                question=question,
                answer=answer,
                document_name=self._document_name,
                context=context,
                pages=pages,
                confidence=confidence,
                template=template_name
            )
        
        # Adiciona ao histórico
        self.conversation.add_turn(
            question=question,
            answer=answer,
            context_used=context,
            pages=pages,
            confidence=confidence
        )
        
        processing_time = time.time() - start_time
        
        return QAResponse(
            question=question,
            answer=answer,
            pages=pages,
            confidence=confidence,
            context_used=context,
            template_used=template_name,
            processing_time=processing_time,
            validation=validation,
            metadata={
                "chunks_retrieved": len(retrieval.retrieval_result.chunks),
                "mode": "offline" if self.mode_manager.is_offline else "online",
            }
        )
    
    def _generate_answer(
        self,
        question: str,
        context: str,
        pages: List[int],
        template: Optional[PromptTemplate]
    ) -> str:
        """Gera resposta usando o template e generator."""
        
        if not context:
            return (
                "Não foi possível encontrar informações relevantes "
                "no documento para responder esta pergunta."
            )
        
        # Prepara prompts
        if template:
            prompts = template.get_full_prompt(
                contexto=context,
                pergunta=question,
                documento=self._document_name,
                paginas=", ".join(map(str, pages)) if pages else "N/A"
            )
            system_prompt = prompts["system"]
            user_prompt = prompts["user"]
        else:
            system_prompt = None
            user_prompt = f"Contexto:\n{context}\n\nPergunta: {question}"
        
        # Obtém generator
        if self._generator is None:
            self._generator = get_response_generator(
                settings=self.settings,
                mode_manager=self.mode_manager
            )
        
        # Gera resposta
        try:
            self._generator.ensure_initialized()
            response = self._generator.generate(
                query=user_prompt,
                context=context,
                system_prompt=system_prompt
            )
            return response.answer
            
        except Exception as e:
            logger.error(f"Erro na geração de resposta: {e}")
            
            # Fallback: retorna contexto
            return (
                f"Contexto encontrado no documento:\n\n{context[:1500]}"
                f"\n\n(Erro na geração de resposta elaborada: {str(e)[:100]})"
            )
    
    def _calculate_confidence(
        self,
        retrieval_response,
        validation: Optional[ValidationResult]
    ) -> float:
        """Calcula confiança da resposta."""
        # Base: média dos scores de retrieval
        if retrieval_response.retrieval_result.scores:
            retrieval_confidence = sum(retrieval_response.retrieval_result.scores) / len(
                retrieval_response.retrieval_result.scores
            )
        else:
            retrieval_confidence = 0.0
        
        # Ajusta com validação
        if validation:
            validation_factor = validation.confidence
        else:
            validation_factor = 0.7
        
        # Combina
        confidence = (retrieval_confidence * 0.6 + validation_factor * 0.4)
        
        return min(1.0, max(0.0, confidence))
    
    def ask_batch(
        self,
        questions: List[str],
        template: Optional[str] = None
    ) -> List[QAResponse]:
        """
        Faz múltiplas perguntas em lote.
        
        Args:
            questions: Lista de perguntas
            template: Template a usar
        
        Returns:
            Lista de respostas
        """
        responses = []
        total = len(questions)
        
        for i, question in enumerate(questions):
            self._report_progress(
                f"Processando pergunta {i+1}/{total}...",
                i / total
            )
            
            response = self.ask(question, template=template)
            responses.append(response)
        
        self._report_progress("Processamento concluído", 1.0)
        
        return responses
    
    def get_conversation_history(self) -> List[Dict[str, Any]]:
        """Retorna histórico da conversa."""
        return [turn.to_dict() for turn in self.conversation.get_all_turns()]
    
    def export_conversation(self, output_path: Path) -> None:
        """Exporta conversa para arquivo."""
        transcript = self.conversation.export_transcript()
        
        output_path = Path(output_path)
        output_path.write_text(transcript, encoding="utf-8")
        
        logger.info(f"Conversa exportada: {output_path}")
    
    def clear_conversation(self) -> None:
        """Limpa histórico da conversa."""
        self.conversation.clear()
    
    def list_templates(self) -> List[Dict[str, Any]]:
        """Lista templates disponíveis."""
        return self.template_loader.list_templates()
    
    def set_template(self, template_name: str) -> None:
        """Define o template atual."""
        self._current_template = self.template_loader.get_template(template_name)
        logger.info(f"Template alterado para: {template_name}")
    
    def get_document_info(self) -> Dict[str, Any]:
        """Retorna informações do documento carregado."""
        if not self._document:
            return {"loaded": False}
        
        return {
            "loaded": True,
            "name": self._document_name,
            "pages": self._document.total_pages,
            "words": self._document.total_words,
            "knowledge_base": self.knowledge_base.get_summary(),
        }
    
    def search_knowledge_base(self, query: str) -> Dict[str, Any]:
        """Busca na base de conhecimento."""
        return self.knowledge_base.search(query)
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Retorna estatísticas do cache."""
        return self.cache.get_stats()
    
    def clear_cache(self) -> int:
        """Limpa o cache."""
        return self.cache.clear()

