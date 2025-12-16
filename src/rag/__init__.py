"""
Módulo RAG (Retrieval-Augmented Generation) para análise de contratos.

Este módulo implementa o padrão RAG para permitir:
- Indexação semântica de documentos
- Recuperação de trechos relevantes (BM25 + embeddings)
- Geração de respostas contextualizadas

Arquitetura:
    Document → Chunker → Embeddings → VectorStore
                    ↓                      ↓
                  BM25 ←  Retriever  → Embeddings
                                ↓
                    Query → Generator → Response
"""

from .embeddings import EmbeddingProvider, LocalEmbeddings, CloudEmbeddings
from .chunker import TextChunker, Chunk, ChunkingStrategy, ChunkingConfig
from .vector_store import VectorStore, FAISSVectorStore
from .retriever import Retriever, HybridRetriever, HybridRetrieverV2, RetrievalResult
from .bm25_retriever import BM25Retriever, BM25Index, BM25Result
from .generator import ResponseGenerator, GeneratedResponse
from .rag_pipeline import RAGPipeline, RAGConfig, RAGResponse, RAGPipelineBuilder
from .gguf_generator import (
    GGUFGenerator,
    GGUFModelConfig,
    PREDEFINED_MODELS,
    get_gguf_generator,
)
from .smart_generator import (
    SmartGenerator,
    get_smart_generator,
    list_available_models,
    check_llama_cpp_available,
    get_best_available_model,
    MODEL_CONFIGS,
    MODEL_PRIORITY,
)

__all__ = [
    # Embeddings
    "EmbeddingProvider",
    "LocalEmbeddings",
    "CloudEmbeddings",
    # Chunking
    "TextChunker",
    "Chunk",
    "ChunkingStrategy",
    "ChunkingConfig",
    # Vector Store
    "VectorStore",
    "FAISSVectorStore",
    # Retriever
    "Retriever",
    "HybridRetriever",
    "HybridRetrieverV2",
    "RetrievalResult",
    # BM25 Retriever
    "BM25Retriever",
    "BM25Index",
    "BM25Result",
    # Generator
    "ResponseGenerator",
    "GeneratedResponse",
    # GGUF Generator
    "GGUFGenerator",
    "GGUFModelConfig",
    "PREDEFINED_MODELS",
    "get_gguf_generator",
    # Smart Generator
    "SmartGenerator",
    "get_smart_generator",
    "list_available_models",
    "check_llama_cpp_available",
    "get_best_available_model",
    "MODEL_CONFIGS",
    "MODEL_PRIORITY",
    # Pipeline
    "RAGPipeline",
    "RAGConfig",
    "RAGResponse",
    "RAGPipelineBuilder",
]
