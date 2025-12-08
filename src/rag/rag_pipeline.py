"""
Pipeline RAG (Retrieval-Augmented Generation) completo.

Orquestra todos os componentes RAG:
1. Indexação de documentos
2. Recuperação de contexto
3. Geração de respostas
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional, Dict, Any, Callable

from ..config.settings import Settings, get_settings
from ..models.document import Document
from .embeddings import EmbeddingProvider, LocalEmbeddings, CloudEmbeddings
from .chunker import TextChunker, ChunkingConfig, ChunkingStrategy, Chunk
from .vector_store import VectorStore, FAISSVectorStore, SimpleVectorStore
from .retriever import Retriever, HybridRetriever, RetrievalResult
from .generator import (
    ResponseGenerator,
    LocalGenerator,
    CloudGenerator,
    GeneratedResponse
)

logger = logging.getLogger(__name__)


@dataclass
class RAGConfig:
    """Configuração do pipeline RAG."""
    
    # Modo de processamento
    mode: str = "local"  # "local" ou "cloud"
    
    # Chunking
    chunk_size: int = 512
    chunk_overlap: int = 50
    chunking_strategy: ChunkingStrategy = ChunkingStrategy.RECURSIVE
    
    # Retrieval
    top_k: int = 5
    min_score: float = 0.3
    use_reranking: bool = False
    use_hybrid_search: bool = False
    use_mmr: bool = False
    mmr_diversity: float = 0.3
    
    # Generation
    temperature: float = 0.1
    max_tokens: int = 1000
    
    # Vector Store
    use_faiss: bool = True
    
    # Caching
    cache_embeddings: bool = True
    index_path: Optional[Path] = None


@dataclass
class RAGResponse:
    """Resposta completa do pipeline RAG."""
    
    query: str
    answer: str
    sources: List[Dict[str, Any]]
    retrieval_result: RetrievalResult
    generated_response: GeneratedResponse
    processing_time: float
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def pages_cited(self) -> List[int]:
        """Páginas citadas nas fontes."""
        return self.retrieval_result.pages
    
    @property
    def confidence(self) -> float:
        """Confiança da resposta."""
        return self.generated_response.confidence
    
    def to_dict(self) -> dict:
        return {
            "query": self.query,
            "answer": self.answer,
            "confidence": self.confidence,
            "pages": self.pages_cited,
            "sources": self.sources,
            "processing_time": self.processing_time,
            "metadata": self.metadata,
        }
    
    def format_answer(self) -> str:
        """Formata resposta para exibição."""
        lines = [
            "=" * 60,
            "RESPOSTA",
            "=" * 60,
            "",
            self.answer,
            "",
            "-" * 60,
            f"Fontes: Páginas {', '.join(map(str, self.pages_cited))}",
            f"Confiança: {self.confidence:.0%}",
            f"Tempo: {self.processing_time:.2f}s",
            "=" * 60,
        ]
        return "\n".join(lines)


class RAGPipeline:
    """
    Pipeline RAG completo para análise de contratos.
    
    Implementa o fluxo:
    Document → Chunking → Embedding → Indexing → Retrieval → Generation
    """
    
    def __init__(
        self,
        config: Optional[RAGConfig] = None,
        settings: Optional[Settings] = None,
        progress_callback: Optional[Callable[[str, float], None]] = None
    ):
        self.config = config or RAGConfig()
        self.settings = settings or get_settings()
        self.progress_callback = progress_callback
        
        # Componentes (lazy loading)
        self._embedding_provider: Optional[EmbeddingProvider] = None
        self._chunker: Optional[TextChunker] = None
        self._vector_store: Optional[VectorStore] = None
        self._retriever: Optional[Retriever] = None
        self._generator: Optional[ResponseGenerator] = None
        
        # Estado
        self._indexed = False
        self._chunks: List[Chunk] = []
    
    def _report_progress(self, message: str, percent: float) -> None:
        """Reporta progresso."""
        logger.info(f"[{percent:.0%}] {message}")
        if self.progress_callback:
            self.progress_callback(message, percent)
    
    @property
    def embedding_provider(self) -> EmbeddingProvider:
        """Obtém provedor de embeddings."""
        if self._embedding_provider is None:
            if self.config.mode == "local":
                self._embedding_provider = LocalEmbeddings(self.settings)
            else:
                self._embedding_provider = CloudEmbeddings(self.settings)
        return self._embedding_provider
    
    @property
    def chunker(self) -> TextChunker:
        """Obtém chunker."""
        if self._chunker is None:
            chunk_config = ChunkingConfig(
                strategy=self.config.chunking_strategy,
                chunk_size=self.config.chunk_size,
                chunk_overlap=self.config.chunk_overlap,
            )
            self._chunker = TextChunker(chunk_config, self.settings)
        return self._chunker
    
    @property
    def vector_store(self) -> VectorStore:
        """Obtém vector store."""
        if self._vector_store is None:
            if self.config.use_faiss:
                try:
                    self._vector_store = FAISSVectorStore(self.embedding_provider)
                except ImportError:
                    logger.warning("FAISS não disponível. Usando SimpleVectorStore.")
                    self._vector_store = SimpleVectorStore(self.embedding_provider)
            else:
                self._vector_store = SimpleVectorStore(self.embedding_provider)
        return self._vector_store
    
    @property
    def retriever(self) -> Retriever:
        """Obtém retriever."""
        if self._retriever is None:
            if self.config.use_hybrid_search:
                self._retriever = HybridRetriever(self.vector_store, self.settings)
            else:
                self._retriever = Retriever(self.vector_store, self.settings)
        return self._retriever
    
    @property
    def generator(self) -> ResponseGenerator:
        """Obtém gerador."""
        if self._generator is None:
            if self.config.mode == "local":
                self._generator = LocalGenerator(self.settings)
            else:
                self._generator = CloudGenerator(self.settings)
        return self._generator
    
    def index_document(self, document: Document) -> int:
        """
        Indexa um documento no vector store.
        
        Args:
            document: Documento a indexar.
        
        Returns:
            int: Número de chunks indexados.
        """
        self._report_progress("Dividindo documento em chunks...", 0.1)
        
        # Divide em chunks
        chunks = self.chunker.chunk_document(document)
        self._chunks = chunks
        
        self._report_progress(f"Gerando embeddings para {len(chunks)} chunks...", 0.3)
        
        # Inicializa embedding provider
        self.embedding_provider.ensure_initialized()
        
        self._report_progress("Indexando no vector store...", 0.6)
        
        # Adiciona ao vector store
        self.vector_store.add_chunks(chunks)
        
        self._indexed = True
        
        self._report_progress(f"Indexação concluída: {len(chunks)} chunks", 1.0)
        
        return len(chunks)
    
    def index_text(self, text: str, source_name: str = "text") -> int:
        """
        Indexa texto diretamente.
        
        Args:
            text: Texto para indexar.
            source_name: Nome da fonte.
        
        Returns:
            int: Número de chunks.
        """
        chunks = self.chunker.chunk_text(text)
        
        for chunk in chunks:
            chunk.metadata["source"] = source_name
        
        self._chunks = chunks
        self.embedding_provider.ensure_initialized()
        self.vector_store.add_chunks(chunks)
        self._indexed = True
        
        return len(chunks)
    
    def query(
        self,
        question: str,
        top_k: Optional[int] = None,
        generate_response: bool = True
    ) -> RAGResponse:
        """
        Executa query RAG completa.
        
        Args:
            question: Pergunta/instrução.
            top_k: Número de chunks a recuperar.
            generate_response: Se deve gerar resposta com LLM.
        
        Returns:
            RAGResponse: Resposta completa.
        """
        if not self._indexed:
            raise RuntimeError("Nenhum documento indexado. Use index_document() primeiro.")
        
        start_time = time.time()
        top_k = top_k or self.config.top_k
        
        # Retrieval
        if self.config.use_mmr:
            retrieval_result = self.retriever.retrieve_with_mmr(
                question,
                top_k,
                self.config.mmr_diversity
            )
        else:
            retrieval_result = self.retriever.retrieve(
                question,
                top_k,
                self.config.min_score,
                rerank=self.config.use_reranking
            )
        
        # Generation
        if generate_response and retrieval_result.chunks:
            self.generator.ensure_initialized()
            generated = self.generator.generate_from_retrieval(
                question,
                retrieval_result
            )
        else:
            # Sem geração, apenas retorna contexto
            if retrieval_result.chunks:
                answer = f"Contexto encontrado ({len(retrieval_result.chunks)} trechos):\n\n"
                answer += retrieval_result.context
            else:
                answer = "Nenhuma informação relevante encontrada no documento."
            
            generated = GeneratedResponse(
                answer=answer,
                sources=[],
                confidence=0.5 if retrieval_result.chunks else 0.0
            )
        
        processing_time = time.time() - start_time
        
        return RAGResponse(
            query=question,
            answer=generated.answer,
            sources=generated.sources,
            retrieval_result=retrieval_result,
            generated_response=generated,
            processing_time=processing_time,
            metadata={
                "mode": self.config.mode,
                "top_k": top_k,
                "chunks_retrieved": len(retrieval_result.chunks),
            }
        )
    
    def query_multiple(
        self,
        questions: List[str],
        generate_responses: bool = True
    ) -> List[RAGResponse]:
        """
        Executa múltiplas queries.
        
        Args:
            questions: Lista de perguntas.
            generate_responses: Se deve gerar respostas.
        
        Returns:
            List[RAGResponse]: Respostas para cada pergunta.
        """
        responses = []
        
        for i, question in enumerate(questions):
            self._report_progress(
                f"Processando pergunta {i+1}/{len(questions)}...",
                i / len(questions)
            )
            response = self.query(question, generate_response=generate_responses)
            responses.append(response)
        
        self._report_progress("Queries concluídas", 1.0)
        
        return responses
    
    def analyze_contract(
        self,
        document: Document,
        instructions: List[str]
    ) -> Dict[str, RAGResponse]:
        """
        Analisa contrato baseado em instruções.
        
        Args:
            document: Documento do contrato.
            instructions: Lista de instruções de busca.
        
        Returns:
            Dict[str, RAGResponse]: Respostas por instrução.
        """
        # Indexa documento
        self._report_progress("Indexando documento...", 0.1)
        self.index_document(document)
        
        # Processa cada instrução
        results = {}
        total = len(instructions)
        
        for i, instruction in enumerate(instructions):
            self._report_progress(
                f"Analisando: {instruction[:50]}...",
                0.2 + (0.8 * i / total)
            )
            
            response = self.query(instruction)
            results[instruction] = response
        
        self._report_progress("Análise concluída", 1.0)
        
        return results
    
    def save_index(self, path: Path) -> None:
        """Salva índice em disco."""
        path = Path(path)
        self.vector_store.save(path)
        
        if self.config.cache_embeddings:
            cache_path = path / "embedding_cache.pkl"
            self.embedding_provider.save_cache(cache_path)
        
        logger.info(f"Índice salvo em: {path}")
    
    def load_index(self, path: Path) -> None:
        """Carrega índice do disco."""
        path = Path(path)
        self.vector_store.load(path)
        
        cache_path = path / "embedding_cache.pkl"
        if cache_path.exists():
            self.embedding_provider.load_cache(cache_path)
        
        self._indexed = True
        logger.info(f"Índice carregado de: {path}")
    
    def get_similar_chunks(
        self,
        text: str,
        top_k: int = 5
    ) -> List[Chunk]:
        """
        Encontra chunks similares a um texto.
        
        Args:
            text: Texto de referência.
            top_k: Número de chunks.
        
        Returns:
            List[Chunk]: Chunks similares.
        """
        if not self._indexed:
            return []
        
        result = self.retriever.retrieve(text, top_k)
        return result.chunks
    
    def clear(self) -> None:
        """Limpa índice e estado."""
        if self._vector_store:
            self._vector_store.clear()
        self._chunks.clear()
        self._indexed = False


class RAGPipelineBuilder:
    """Builder para configuração flexível do pipeline RAG."""
    
    def __init__(self):
        self._config = RAGConfig()
        self._settings: Optional[Settings] = None
        self._progress_callback: Optional[Callable] = None
    
    def with_mode(self, mode: str) -> "RAGPipelineBuilder":
        """Define modo (local/cloud)."""
        self._config.mode = mode
        return self
    
    def with_chunk_size(self, size: int, overlap: int = 50) -> "RAGPipelineBuilder":
        """Define tamanho dos chunks."""
        self._config.chunk_size = size
        self._config.chunk_overlap = overlap
        return self
    
    def with_top_k(self, k: int) -> "RAGPipelineBuilder":
        """Define número de chunks a recuperar."""
        self._config.top_k = k
        return self
    
    def with_reranking(self) -> "RAGPipelineBuilder":
        """Ativa re-ranking."""
        self._config.use_reranking = True
        return self
    
    def with_hybrid_search(self) -> "RAGPipelineBuilder":
        """Ativa busca híbrida."""
        self._config.use_hybrid_search = True
        return self
    
    def with_mmr(self, diversity: float = 0.3) -> "RAGPipelineBuilder":
        """Ativa MMR para diversificação."""
        self._config.use_mmr = True
        self._config.mmr_diversity = diversity
        return self
    
    def with_settings(self, settings: Settings) -> "RAGPipelineBuilder":
        """Define configurações."""
        self._settings = settings
        return self
    
    def with_progress_callback(
        self,
        callback: Callable[[str, float], None]
    ) -> "RAGPipelineBuilder":
        """Define callback de progresso."""
        self._progress_callback = callback
        return self
    
    def build(self) -> RAGPipeline:
        """Constrói o pipeline."""
        return RAGPipeline(
            config=self._config,
            settings=self._settings,
            progress_callback=self._progress_callback
        )
    
    @classmethod
    def for_legal_analysis(cls) -> "RAGPipelineBuilder":
        """Cria builder pré-configurado para análise jurídica."""
        builder = cls()
        builder._config.chunk_size = 600
        builder._config.chunk_overlap = 100
        builder._config.chunking_strategy = ChunkingStrategy.RECURSIVE
        builder._config.top_k = 5
        builder._config.min_score = 0.3
        builder._config.use_reranking = True
        return builder
