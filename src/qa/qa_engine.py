"""
Motor Principal de Q&A (Perguntas e Respostas).

Orquestra todos os componentes para responder perguntas
sobre documentos PDF.

Funciona em modo offline e online, seguindo a mesma
lógica do restante do sistema.
"""

from __future__ import annotations

import logging
import re
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional, Dict, Any, Callable

from config.settings import Settings, get_settings
from config.mode_manager import get_mode_manager, ModeManager
from models.document import Document
from core.pdf_reader import PDFReader
from core.ocr_extractor import OCRExtractor
from core.ocr_cache import get_ocr_cache, OCRCache
from rag.rag_pipeline import RAGPipeline, RAGConfig
from rag.generator import ResponseGenerator
from rag.smart_generator import SmartGenerator, get_smart_generator

from .template_loader import TemplateLoader, PromptTemplate
from .conversation import Conversation, ConversationTurn, MemoryType
from .knowledge_base import KnowledgeBase
from .qa_validator import QAValidator, ValidationResult
from .cache import ResponseCache

# Importa DKR (Domain Knowledge Rules) se disponível
try:
    from dkr import DKREngine, get_dkr_engine, DKRResult
    DKR_AVAILABLE = True
except ImportError:
    DKREngine = None
    DKRResult = None
    DKR_AVAILABLE = False

logger = logging.getLogger(__name__)


@dataclass
class QAConfig:
    """Configuração do sistema de Q&A."""
    
    # Template
    default_template: str = "sistema_padrao"
    templates_dir: str = "./instructions/qa_templates"
    auto_detect_template: bool = True
    
    # RAG - Chunking
    chunk_size: int = 800
    chunk_overlap: int = 100
    chunking_strategy: str = "semantic_sections"  # semantic_sections, recursive, paragraph
    
    # RAG - Retrieval
    top_k: int = 10
    min_score: float = 0.2
    use_hybrid_search: bool = True
    use_reranking: bool = True
    use_mmr: bool = True
    mmr_diversity: float = 0.3
    bm25_weight: float = 0.4      # Peso do BM25 na busca híbrida
    semantic_weight: float = 0.6  # Peso dos embeddings na busca híbrida
    
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
    
    # DKR (Domain Knowledge Rules)
    use_dkr: bool = True  # Usa DKR se disponível
    dkr_rules_dir: str = "./domain_rules"  # Diretório dos arquivos .rules
    dkr_auto_detect: bool = True  # Auto-detecta arquivo .rules pelo template
    
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
            
            # Chunking (carrega do YAML via config.yaml diretamente)
            # Estas configurações serão passadas para RAGConfig
            
            if hasattr(rag, 'retrieval'):
                config.top_k = getattr(rag.retrieval, 'top_k', config.top_k)
                config.min_score = getattr(rag.retrieval, 'min_score', config.min_score)
                config.use_hybrid_search = getattr(rag.retrieval, 'use_hybrid_search', config.use_hybrid_search)
                config.use_reranking = getattr(rag.retrieval, 'use_reranking', config.use_reranking)
                config.use_mmr = getattr(rag.retrieval, 'use_mmr', config.use_mmr)
                config.mmr_diversity = getattr(rag.retrieval, 'mmr_diversity', config.mmr_diversity)
                config.bm25_weight = getattr(rag.retrieval, 'bm25_weight', config.bm25_weight)
                config.semantic_weight = getattr(rag.retrieval, 'semantic_weight', config.semantic_weight)
        
        return config
    
    @classmethod
    def from_yaml(cls, yaml_path: str = "./config.yaml") -> "QAConfig":
        """Cria configuração diretamente do arquivo YAML."""
        import yaml
        from pathlib import Path
        
        config = cls()
        yaml_path = Path(yaml_path)
        
        if not yaml_path.exists():
            return config
        
        try:
            with open(yaml_path, "r", encoding="utf-8") as f:
                yaml_config = yaml.safe_load(f)
            
            # Chunking
            chunking = yaml_config.get("rag", {}).get("chunking", {})
            config.chunk_size = chunking.get("chunk_size", config.chunk_size)
            config.chunk_overlap = chunking.get("chunk_overlap", config.chunk_overlap)
            config.chunking_strategy = chunking.get("strategy", config.chunking_strategy)
            
            # Retrieval
            retrieval = yaml_config.get("rag", {}).get("retrieval", {})
            config.top_k = retrieval.get("top_k", config.top_k)
            config.min_score = retrieval.get("min_score", config.min_score)
            config.use_hybrid_search = retrieval.get("use_hybrid_search", config.use_hybrid_search)
            config.use_reranking = retrieval.get("use_reranking", config.use_reranking)
            config.use_mmr = retrieval.get("use_mmr", config.use_mmr)
            config.mmr_diversity = retrieval.get("mmr_diversity", config.mmr_diversity)
            config.bm25_weight = retrieval.get("bm25_weight", config.bm25_weight)
            config.semantic_weight = retrieval.get("semantic_weight", config.semantic_weight)
            
            # Generation
            generation = yaml_config.get("rag", {}).get("generation", {})
            config.generate_answers = generation.get("generate_answers", config.generate_answers)
            
            # QA específico
            qa_config = yaml_config.get("qa", {})
            templates = qa_config.get("templates", {})
            config.default_template = templates.get("default", config.default_template)
            config.templates_dir = templates.get("dir", config.templates_dir)
            config.auto_detect_template = templates.get("auto_detect", {}).get("enabled", config.auto_detect_template)
            
        except Exception as e:
            logger.warning(f"Erro ao carregar config.yaml: {e}")
        
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
    dkr_result: Optional[Any] = None  # DKRResult se DKR foi usado
    
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
        self._dkr_engine: Optional["DKREngine"] = None  # Domain Knowledge Rules
        
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
    def dkr_engine(self) -> Optional["DKREngine"]:
        """Obtém o engine DKR se disponível e configurado."""
        return self._dkr_engine
    
    def _load_dkr_for_template(self, template_name: str) -> None:
        """
        Carrega arquivo .rules correspondente ao template.
        
        Args:
            template_name: Nome do template (ex: "licencas_software")
        """
        if not DKR_AVAILABLE:
            logger.debug("DKR não disponível (módulo não instalado)")
            return
        
        if not self.config.use_dkr:
            logger.debug("DKR desabilitado na configuração")
            return
        
        rules_dir = Path(self.config.dkr_rules_dir)
        rules_file = rules_dir / f"{template_name}.rules"
        
        if not rules_file.exists():
            logger.debug(f"Arquivo .rules não encontrado: {rules_file}")
            self._dkr_engine = None
            return
        
        try:
            self._dkr_engine = DKREngine(rules_file)
            logger.info(f"DKR Engine carregado: {rules_file.name}")
        except Exception as e:
            logger.warning(f"Erro ao carregar DKR: {e}")
            self._dkr_engine = None
    
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
        
        # Verifica cache de OCR
        ocr_cache = get_ocr_cache()
        cached_doc = ocr_cache.get(pdf_path)
        
        if cached_doc:
            self._report_progress("Usando texto do cache OCR...", 0.2)
            logger.info(f"Cache OCR hit: {pdf_path.name}")
            
            # Preenche documento com texto do cache
            for i, page in enumerate(self._document.pages):
                if i < len(cached_doc.pages):
                    page.text = cached_doc.pages[i].get("text", "")
            
        else:
            self._report_progress("Extraindo texto com OCR...", 0.2)
            
            # Extrai texto
            import time
            start_time = time.time()
            
            ocr = OCRExtractor(self.settings)
            ocr.extract(self._document)
            
            extraction_time = time.time() - start_time
            
            # Salva no cache
            pages_data = [
                {"number": p.number, "text": p.text}
                for p in self._document.pages
            ]
            ocr_cache.save(pdf_path, pages_data, extraction_time)
        
        self._report_progress("Indexando documento...", 0.4)
        
        # Mapeia estratégia de chunking do string para enum
        from rag.chunker import ChunkingStrategy
        strategy_map = {
            "fixed_size": ChunkingStrategy.FIXED_SIZE,
            "sentence": ChunkingStrategy.SENTENCE,
            "paragraph": ChunkingStrategy.PARAGRAPH,
            "recursive": ChunkingStrategy.RECURSIVE,
            "semantic_sections": ChunkingStrategy.SEMANTIC_SECTIONS,
        }
        chunking_strategy = strategy_map.get(
            self.config.chunking_strategy, 
            ChunkingStrategy.SEMANTIC_SECTIONS
        )
        
        # Configura e indexa no RAG com todas as configurações
        rag_config = RAGConfig(
            mode="local" if self.mode_manager.is_offline else "cloud",
            # Chunking
            chunk_size=self.config.chunk_size,
            chunk_overlap=self.config.chunk_overlap,
            chunking_strategy=chunking_strategy,
            # Retrieval
            top_k=self.config.top_k,
            min_score=self.config.min_score,
            use_hybrid_search=self.config.use_hybrid_search,
            use_reranking=self.config.use_reranking,
            use_mmr=self.config.use_mmr,
            mmr_diversity=self.config.mmr_diversity,
            bm25_weight=self.config.bm25_weight,
            semantic_weight=self.config.semantic_weight,
            # Generation
            generate_answers=self.config.generate_answers,
        )
        
        logger.info(
            f"Q&A RAGConfig: chunking={chunking_strategy.value}, "
            f"hybrid_search={self.config.use_hybrid_search}, "
            f"bm25_weight={self.config.bm25_weight}"
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
        selected_name = None
        
        if template_name:
            self._current_template = self.template_loader.get_template(template_name)
            selected_name = template_name
            logger.info(f"Template selecionado: {template_name}")
        
        elif self.config.auto_detect_template:
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
                selected_name = detected
                logger.info(f"Template detectado automaticamente: {detected}")
        
        # Fallback para template padrão
        if not selected_name:
            self._current_template = self.template_loader.get_template()
            selected_name = self.config.default_template
            logger.info(f"Usando template padrão: {self.config.default_template}")
        
        # Carrega DKR correspondente ao template
        if self.config.use_dkr and self.config.dkr_auto_detect:
            self._load_dkr_for_template(selected_name)
    
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
        
        # Query expansion - usa DKR se disponível, senão usa lógica legada
        is_criticality_q = self._is_criticality_question(question)
        
        if self._dkr_engine:
            # DKR pode expandir query baseado em intents detectados
            search_query = self._dkr_engine.expand_query(enriched_question)
            if search_query != enriched_question:
                logger.info("Query expandida via DKR")
        elif is_criticality_q:
            # Fallback: usa lógica legada para criticidade
            search_query = self._expand_query_for_criticality(enriched_question)
            logger.info("Detectada pergunta sobre criticidade - usando query expandida (legado)")
        else:
            search_query = enriched_question
        
        # Seleciona template se especificado
        if template:
            prompt_template = self.template_loader.get_template(template)
        else:
            prompt_template = self._current_template
        
        template_name = prompt_template.name if prompt_template else "fallback"
        
        # Verifica cache
        should_use_cache = use_cache if use_cache is not None else self.config.use_cache
        
        # Obtém hash das regras DKR para invalidação de cache
        current_rules_hash = ""
        if self._dkr_engine and self._dkr_engine.rules:
            current_rules_hash = self._dkr_engine.rules.source_hash
        
        if should_use_cache:
            # Obtém contexto primeiro para verificar cache
            # Usa search_query (expandida para criticidade) em vez de enriched_question
            retrieval = self._rag_pipeline.query(
                search_query,
                generate_response=False
            )
            context = retrieval.retrieval_result.context
            pages = retrieval.retrieval_result.pages
            
            cached = self.cache.get(
                question=question,
                document_name=self._document_name,
                context=context,
                template=template_name,
                rules_hash=current_rules_hash
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
                search_query,  # Usa query expandida para criticidade
                generate_response=False
            )
            context = retrieval.retrieval_result.context
            pages = retrieval.retrieval_result.pages
        
        # Gera resposta
        answer, generator_metadata = self._generate_answer(
            question=enriched_question,
            context=context,
            pages=pages,
            template=prompt_template
        )
        
        # ======== Augment com DKR ou KnowledgeBase ========
        dkr_result = None
        
        if self._dkr_engine:
            # Usa DKR para validar e potencialmente corrigir resposta
            dkr_result = self._dkr_engine.process(
                question=question,
                answer=answer,
                context=context,
                apply_corrections=True
            )
            
            if dkr_result.was_corrected:
                logger.info(f"DKR corrigiu resposta: {dkr_result.correction_reason}")
                answer = dkr_result.final_answer
            
        elif is_criticality_q:
            # Fallback: usa KnowledgeBase para perguntas de criticidade
            answer = self._augment_answer_with_knowledge(
                question=question,
                answer=answer,
                context=context
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
                template=template_name,
                rules_hash=current_rules_hash
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
        
        # Combina metadata do retrieval com metadata do generator
        response_metadata = {
            "chunks_retrieved": len(retrieval.retrieval_result.chunks),
            "mode": "offline" if self.mode_manager.is_offline else "online",
        }
        response_metadata.update(generator_metadata)
        
        return QAResponse(
            question=question,
            answer=answer,
            pages=pages,
            confidence=confidence,
            context_used=context,
            template_used=template_name,
            processing_time=processing_time,
            validation=validation,
            metadata=response_metadata,
            dkr_result=dkr_result
        )
    
    def _is_criticality_question(self, question: str) -> bool:
        """Detecta se a pergunta é sobre criticidade de licenças."""
        patterns = [
            r'cr[íi]tic[ao]',
            r'mais\s+(cr[íi]tic[ao]|perigosa?|restritiva?)',
            r'grau\s+de\s+criticidade',
            r'licen[çc]as?\s+(cr[íi]tic|alto|alto\s+risco)',
            r'evitar|priorizar',
            r'risco\s+(alto|maior)',
        ]
        question_lower = question.lower()
        return any(re.search(p, question_lower) for p in patterns)
    
    def _expand_query_for_criticality(self, question: str) -> str:
        """Expande query para buscar melhor informações de criticidade."""
        # Adiciona termos que ajudam a recuperar chunks da tabela de criticidade
        # Mantém expansão focada para não trazer muito ruído
        expansion_terms = [
            "GRAU DE CRITICIDADE DAS LICENÇAS",
            "ALTO",
        ]
        
        # Junta pergunta original com termos de expansão
        expanded = f"{question} {' '.join(expansion_terms)}"
        logger.debug(f"Query expandida para criticidade: {expanded[:100]}...")
        return expanded
    
    def _augment_answer_with_knowledge(
        self,
        question: str,
        answer: str,
        context: str
    ) -> str:
        """
        Usa a KnowledgeBase para verificar e enriquecer a resposta.
        
        Se a pergunta é sobre licença mais crítica e a resposta menciona
        uma licença de baixo risco, corrige usando a KB.
        """
        if not self._is_criticality_question(question):
            return answer
        
        # Obtém licenças críticas da KB
        critical_licenses = self.knowledge_base.get_critical_licenses()
        safe_licenses = self.knowledge_base.get_safe_licenses()
        
        if not critical_licenses:
            logger.warning("KB não tem licenças críticas - verificar extração")
            return answer
        
        answer_lower = answer.lower()
        
        # Verifica se a resposta menciona incorretamente uma licença segura como crítica
        is_asking_most_critical = re.search(
            r'mais\s+cr[íi]tic|maior\s+cr[íi]tic|mais\s+perigosa|mais\s+restritiva',
            question.lower()
        )
        
        if is_asking_most_critical:
            # Verifica se resposta menciona licença de baixo risco
            mentions_safe = any(
                lic.name.lower() in answer_lower 
                for lic in safe_licenses
            )
            mentions_critical = any(
                lic.name.lower() in answer_lower 
                for lic in critical_licenses
            )
            
            # Se menciona licença segura mas não menciona crítica, corrige
            if mentions_safe and not mentions_critical:
                logger.warning("Resposta possivelmente invertida - corrigindo com KB")
                
                # Constrói resposta correta baseada na KB
                critical_info = critical_licenses[0]  # Pega a primeira (geralmente AGPL)
                
                corrected = (
                    f"De acordo com o documento, a licença mais crítica é a "
                    f"**{critical_info.name}** com grau de criticidade **ALTO**.\n\n"
                    f"Justificativa: {critical_info.criticality_reason or 'Possui obrigações mesmo sem distribuição, introduzindo a modalidade SAS (Software as a Service).'}\n\n"
                    f"Recomendação: Evitar o uso desta licença por ser mais restritiva.\n\n"
                    f"(Resposta validada pela base de conhecimento)"
                )
                return corrected
        
        return answer
    
    def _generate_answer(
        self,
        question: str,
        context: str,
        pages: List[int],
        template: Optional[PromptTemplate]
    ) -> tuple[str, Dict[str, Any]]:
        """
        Gera resposta usando o template e generator.
        
        Returns:
            Tuple com (answer, metadata)
        """
        
        if not context:
            return (
                "Não foi possível encontrar informações relevantes "
                "no documento para responder esta pergunta.",
                {}
            )
        
        # Prepara prompts
        # NOTA: O GGUFGenerator tem seu próprio formato de prompt,
        # então passamos apenas o system_prompt simplificado e 
        # deixamos ele formatar context + question no seu formato
        if template:
            system_prompt = template.format_system_prompt()
            # Não usamos user_prompt formatado - o generator fará isso
        else:
            system_prompt = None
        
        # Obtém generator (usa SmartGenerator para selecionar melhor modelo)
        if self._generator is None:
            # Usa modelo especificado na config ou deixa SmartGenerator escolher
            preferred_model = self.config.generation_model
            logger.info(f"Criando gerador com modelo preferido: {preferred_model or 'auto'}")
            self._generator = get_smart_generator(
                preferred_model=preferred_model,
                fallback_enabled=True
            )
        
        # Gera resposta
        # Passa apenas a pergunta como query, o contexto separadamente
        # O generator é responsável por formatar e truncar adequadamente
        try:
            self._generator.ensure_initialized()
            response = self._generator.generate(
                query=question,  # Apenas a pergunta, não o prompt formatado
                context=context,  # Contexto original
                system_prompt=system_prompt
            )
            
            # Retorna answer e metadata do generator
            metadata = response.metadata or {}
            return response.answer, metadata
            
        except Exception as e:
            logger.error(f"Erro na geração de resposta: {e}")
            
            # Fallback: retorna contexto
            return (
                f"Contexto encontrado no documento:\n\n{context[:1500]}"
                f"\n\n(Erro na geração de resposta elaborada: {str(e)[:100]})",
                {"error": str(e)}
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
    
    def set_model(self, model_name: str) -> str:
        """
        Define o modelo de geração a usar.
        
        Args:
            model_name: Nome do modelo (tinyllama, phi3-mini, gpt2-portuguese)
        
        Returns:
            str: Nome do modelo configurado
        """
        # Recria o gerador com o novo modelo
        self.config.generation_model = model_name
        self._generator = None  # Força recriação
        
        # Cria novo gerador para verificar se funciona
        self._generator = get_smart_generator(
            preferred_model=model_name,
            fallback_enabled=True
        )
        self._generator.ensure_initialized()
        
        actual_model = self._generator.model_name
        logger.info(f"Modelo alterado para: {actual_model}")
        
        return actual_model
    
    def get_current_model(self) -> str:
        """Retorna o nome do modelo em uso."""
        if self._generator and hasattr(self._generator, 'model_name'):
            return self._generator.model_name
        return self.config.generation_model or "auto"
    
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

