"""
Módulo RAG (Retrieval-Augmented Generation) para análise de contratos.

Este módulo implementa o padrão RAG para permitir:
- Indexação semântica de documentos
- Recuperação de trechos relevantes
- Geração de respostas contextualizadas

Arquitetura:
    Document → Chunker → Embeddings → VectorStore
                                          ↓
    Query → Embeddings → Retriever → Generator → Response
"""

from .embeddings import EmbeddingProvider, LocalEmbeddings, CloudEmbeddings
from .chunker import TextChunker, Chunk, ChunkingStrategy
from .vector_store import VectorStore, FAISSVectorStore
from .retriever import Retriever, RetrievalResult
from .generator import ResponseGenerator, GeneratedResponse
from .rag_pipeline import RAGPipeline, RAGConfig, RAGResponse

__all__ = [
    # Embeddings
    "EmbeddingProvider",
    "LocalEmbeddings",
    "CloudEmbeddings",
    # Chunking
    "TextChunker",
    "Chunk",
    "ChunkingStrategy",
    # Vector Store
    "VectorStore",
    "FAISSVectorStore",
    # Retriever
    "Retriever",
    "RetrievalResult",
    # Generator
    "ResponseGenerator",
    "GeneratedResponse",
    # Pipeline
    "RAGPipeline",
    "RAGConfig",
    "RAGResponse",
]
