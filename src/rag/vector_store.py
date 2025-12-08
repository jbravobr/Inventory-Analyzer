"""
Módulo de Vector Store para armazenamento e busca de embeddings.

Implementa armazenamento vetorial usando FAISS (local) para
busca eficiente por similaridade.
"""

from __future__ import annotations

import json
import logging
import pickle
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np

from .chunker import Chunk
from .embeddings import EmbeddingProvider

logger = logging.getLogger(__name__)


@dataclass
class VectorSearchResult:
    """Resultado de uma busca vetorial."""
    
    chunk: Chunk
    score: float
    rank: int
    
    def to_dict(self) -> dict:
        return {
            "chunk": self.chunk.to_dict(),
            "score": self.score,
            "rank": self.rank,
        }


class VectorStore(ABC):
    """Classe base abstrata para vector stores."""
    
    def __init__(self, embedding_provider: EmbeddingProvider):
        self.embedding_provider = embedding_provider
        self._chunks: Dict[str, Chunk] = {}
        self._initialized = False
    
    @abstractmethod
    def add_chunks(self, chunks: List[Chunk]) -> None:
        """
        Adiciona chunks ao vector store.
        
        Args:
            chunks: Lista de chunks para indexar.
        """
        pass
    
    @abstractmethod
    def search(
        self,
        query: str,
        top_k: int = 5
    ) -> List[VectorSearchResult]:
        """
        Busca chunks similares à query.
        
        Args:
            query: Texto de busca.
            top_k: Número de resultados.
        
        Returns:
            List[VectorSearchResult]: Resultados ordenados por similaridade.
        """
        pass
    
    @abstractmethod
    def search_by_vector(
        self,
        vector: np.ndarray,
        top_k: int = 5
    ) -> List[VectorSearchResult]:
        """
        Busca por vetor de embedding.
        
        Args:
            vector: Vetor de query.
            top_k: Número de resultados.
        
        Returns:
            List[VectorSearchResult]: Resultados.
        """
        pass
    
    @abstractmethod
    def save(self, path: Path) -> None:
        """Salva o índice em disco."""
        pass
    
    @abstractmethod
    def load(self, path: Path) -> None:
        """Carrega o índice do disco."""
        pass
    
    @property
    def size(self) -> int:
        """Número de chunks no store."""
        return len(self._chunks)
    
    def get_chunk(self, chunk_id: str) -> Optional[Chunk]:
        """Obtém chunk por ID."""
        return self._chunks.get(chunk_id)
    
    def clear(self) -> None:
        """Limpa o store."""
        self._chunks.clear()
        self._initialized = False


class FAISSVectorStore(VectorStore):
    """
    Vector Store usando FAISS para busca eficiente.
    
    FAISS é uma biblioteca da Meta para busca de similaridade
    em grandes conjuntos de vetores.
    """
    
    def __init__(
        self,
        embedding_provider: EmbeddingProvider,
        use_gpu: bool = False
    ):
        super().__init__(embedding_provider)
        self._index = None
        self._use_gpu = use_gpu
        self._id_mapping: List[str] = []  # Mapeia índice FAISS -> chunk_id
    
    def _ensure_faiss(self):
        """Garante que FAISS está disponível."""
        try:
            import faiss
            return faiss
        except ImportError:
            raise ImportError(
                "faiss não instalado. Instale com: pip install faiss-cpu "
                "ou pip install faiss-gpu para suporte a GPU"
            )
    
    def _create_index(self, dimension: int):
        """Cria índice FAISS."""
        faiss = self._ensure_faiss()
        
        # Usa índice L2 (distância euclidiana) ou IP (produto interno)
        # Para embeddings normalizados, IP é equivalente a similaridade de cosseno
        self._index = faiss.IndexFlatIP(dimension)
        
        if self._use_gpu:
            try:
                res = faiss.StandardGpuResources()
                self._index = faiss.index_cpu_to_gpu(res, 0, self._index)
                logger.info("FAISS usando GPU")
            except Exception as e:
                logger.warning(f"GPU não disponível: {e}. Usando CPU.")
    
    def add_chunks(self, chunks: List[Chunk]) -> None:
        """Adiciona chunks ao índice FAISS."""
        if not chunks:
            return
        
        faiss = self._ensure_faiss()
        
        # Garante que embedding provider está inicializado
        self.embedding_provider.ensure_initialized()
        
        # Extrai textos e gera embeddings
        texts = [chunk.text for chunk in chunks]
        embeddings = self.embedding_provider.embed_texts(texts)
        
        # Normaliza para usar produto interno como similaridade de cosseno
        faiss.normalize_L2(embeddings)
        
        # Cria índice se necessário
        if self._index is None:
            self._create_index(embeddings.shape[1])
        
        # Adiciona ao índice
        self._index.add(embeddings)
        
        # Atualiza mapeamentos
        for chunk in chunks:
            self._chunks[chunk.chunk_id] = chunk
            self._id_mapping.append(chunk.chunk_id)
        
        self._initialized = True
        logger.info(f"Adicionados {len(chunks)} chunks ao índice. Total: {self.size}")
    
    def search(
        self,
        query: str,
        top_k: int = 5
    ) -> List[VectorSearchResult]:
        """Busca chunks similares à query."""
        if not self._initialized or self._index is None:
            logger.warning("Índice não inicializado")
            return []
        
        faiss = self._ensure_faiss()
        
        # Gera embedding da query
        query_embedding = self.embedding_provider.embed_text(query)
        query_embedding = query_embedding.reshape(1, -1).astype(np.float32)
        
        # Normaliza
        faiss.normalize_L2(query_embedding)
        
        return self.search_by_vector(query_embedding[0], top_k)
    
    def search_by_vector(
        self,
        vector: np.ndarray,
        top_k: int = 5
    ) -> List[VectorSearchResult]:
        """Busca por vetor."""
        if not self._initialized or self._index is None:
            return []
        
        # Prepara vetor
        vector = vector.reshape(1, -1).astype(np.float32)
        
        # Busca
        k = min(top_k, self.size)
        scores, indices = self._index.search(vector, k)
        
        # Monta resultados
        results = []
        for rank, (score, idx) in enumerate(zip(scores[0], indices[0])):
            if idx < 0 or idx >= len(self._id_mapping):
                continue
            
            chunk_id = self._id_mapping[idx]
            chunk = self._chunks.get(chunk_id)
            
            if chunk:
                results.append(VectorSearchResult(
                    chunk=chunk,
                    score=float(score),
                    rank=rank + 1
                ))
        
        return results
    
    def save(self, path: Path) -> None:
        """Salva índice e metadados."""
        path = Path(path)
        path.mkdir(parents=True, exist_ok=True)
        
        faiss = self._ensure_faiss()
        
        # Salva índice FAISS
        index_path = path / "index.faiss"
        if self._use_gpu:
            cpu_index = faiss.index_gpu_to_cpu(self._index)
            faiss.write_index(cpu_index, str(index_path))
        else:
            faiss.write_index(self._index, str(index_path))
        
        # Salva chunks e mapeamento
        metadata = {
            "chunks": {cid: c.to_dict() for cid, c in self._chunks.items()},
            "id_mapping": self._id_mapping,
            "model_name": self.embedding_provider.model_name,
            "dimension": self.embedding_provider.dimension,
        }
        
        metadata_path = path / "metadata.json"
        with open(metadata_path, "w", encoding="utf-8") as f:
            json.dump(metadata, f, ensure_ascii=False, indent=2)
        
        logger.info(f"Índice salvo em: {path}")
    
    def load(self, path: Path) -> None:
        """Carrega índice do disco."""
        path = Path(path)
        
        if not path.exists():
            raise FileNotFoundError(f"Índice não encontrado: {path}")
        
        faiss = self._ensure_faiss()
        
        # Carrega índice FAISS
        index_path = path / "index.faiss"
        self._index = faiss.read_index(str(index_path))
        
        if self._use_gpu:
            try:
                res = faiss.StandardGpuResources()
                self._index = faiss.index_cpu_to_gpu(res, 0, self._index)
            except Exception:
                pass
        
        # Carrega metadados
        metadata_path = path / "metadata.json"
        with open(metadata_path, "r", encoding="utf-8") as f:
            metadata = json.load(f)
        
        # Reconstrói chunks
        self._chunks = {}
        for cid, cdata in metadata["chunks"].items():
            self._chunks[cid] = Chunk(
                text=cdata["text"],
                chunk_id=cdata["chunk_id"],
                page_number=cdata["page_number"],
                start_char=cdata["start_char"],
                end_char=cdata["end_char"],
                metadata=cdata.get("metadata", {}),
            )
        
        self._id_mapping = metadata["id_mapping"]
        self._initialized = True
        
        logger.info(f"Índice carregado: {self.size} chunks")
    
    def clear(self) -> None:
        """Limpa o índice."""
        super().clear()
        self._index = None
        self._id_mapping.clear()


class SimpleVectorStore(VectorStore):
    """
    Vector Store simples usando numpy (sem FAISS).
    
    Útil para conjuntos pequenos ou quando FAISS não está disponível.
    """
    
    def __init__(self, embedding_provider: EmbeddingProvider):
        super().__init__(embedding_provider)
        self._embeddings: Optional[np.ndarray] = None
        self._chunk_ids: List[str] = []
    
    def add_chunks(self, chunks: List[Chunk]) -> None:
        """Adiciona chunks."""
        if not chunks:
            return
        
        self.embedding_provider.ensure_initialized()
        
        texts = [chunk.text for chunk in chunks]
        new_embeddings = self.embedding_provider.embed_texts(texts)
        
        # Normaliza
        norms = np.linalg.norm(new_embeddings, axis=1, keepdims=True)
        new_embeddings = new_embeddings / norms
        
        if self._embeddings is None:
            self._embeddings = new_embeddings
        else:
            self._embeddings = np.vstack([self._embeddings, new_embeddings])
        
        for chunk in chunks:
            self._chunks[chunk.chunk_id] = chunk
            self._chunk_ids.append(chunk.chunk_id)
        
        self._initialized = True
    
    def search(self, query: str, top_k: int = 5) -> List[VectorSearchResult]:
        """Busca por texto."""
        if not self._initialized:
            return []
        
        query_embedding = self.embedding_provider.embed_text(query)
        query_embedding = query_embedding / np.linalg.norm(query_embedding)
        
        return self.search_by_vector(query_embedding, top_k)
    
    def search_by_vector(
        self,
        vector: np.ndarray,
        top_k: int = 5
    ) -> List[VectorSearchResult]:
        """Busca por vetor usando produto interno."""
        if self._embeddings is None:
            return []
        
        # Similaridade de cosseno (vetores já normalizados)
        scores = np.dot(self._embeddings, vector)
        
        # Top-k
        k = min(top_k, len(scores))
        top_indices = np.argsort(scores)[::-1][:k]
        
        results = []
        for rank, idx in enumerate(top_indices):
            chunk_id = self._chunk_ids[idx]
            chunk = self._chunks.get(chunk_id)
            
            if chunk:
                results.append(VectorSearchResult(
                    chunk=chunk,
                    score=float(scores[idx]),
                    rank=rank + 1
                ))
        
        return results
    
    def save(self, path: Path) -> None:
        """Salva em disco."""
        path = Path(path)
        path.mkdir(parents=True, exist_ok=True)
        
        data = {
            "embeddings": self._embeddings,
            "chunk_ids": self._chunk_ids,
            "chunks": {cid: c.to_dict() for cid, c in self._chunks.items()},
        }
        
        with open(path / "store.pkl", "wb") as f:
            pickle.dump(data, f)
    
    def load(self, path: Path) -> None:
        """Carrega do disco."""
        with open(Path(path) / "store.pkl", "rb") as f:
            data = pickle.load(f)
        
        self._embeddings = data["embeddings"]
        self._chunk_ids = data["chunk_ids"]
        
        for cid, cdata in data["chunks"].items():
            self._chunks[cid] = Chunk(
                text=cdata["text"],
                chunk_id=cdata["chunk_id"],
                page_number=cdata["page_number"],
                start_char=cdata["start_char"],
                end_char=cdata["end_char"],
                metadata=cdata.get("metadata", {}),
            )
        
        self._initialized = True
