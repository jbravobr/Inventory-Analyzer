"""
Módulo de Retrieval para recuperação de contexto relevante.

Combina busca vetorial com re-ranking para obter os chunks
mais relevantes para uma query.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any

import numpy as np

from ..config.settings import Settings, get_settings
from .chunker import Chunk
from .vector_store import VectorStore, VectorSearchResult

logger = logging.getLogger(__name__)


@dataclass
class RetrievalResult:
    """Resultado de uma operação de retrieval."""
    
    query: str
    chunks: List[Chunk]
    scores: List[float]
    total_retrieved: int
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def context(self) -> str:
        """Retorna contexto concatenado dos chunks."""
        return "\n\n---\n\n".join(chunk.text for chunk in self.chunks)
    
    @property
    def best_chunk(self) -> Optional[Chunk]:
        """Retorna o chunk mais relevante."""
        return self.chunks[0] if self.chunks else None
    
    @property
    def pages(self) -> List[int]:
        """Lista de páginas dos chunks recuperados."""
        return sorted(set(chunk.page_number for chunk in self.chunks))
    
    def to_dict(self) -> dict:
        return {
            "query": self.query,
            "total_retrieved": self.total_retrieved,
            "pages": self.pages,
            "chunks": [
                {
                    "text": c.text[:200] + "..." if len(c.text) > 200 else c.text,
                    "page": c.page_number,
                    "score": s,
                }
                for c, s in zip(self.chunks, self.scores)
            ],
        }


class Retriever:
    """
    Retriever para recuperação de chunks relevantes.
    
    Suporta:
    - Busca vetorial simples
    - Re-ranking por relevância
    - Filtragem por metadados
    - Diversificação de resultados
    """
    
    def __init__(
        self,
        vector_store: VectorStore,
        settings: Optional[Settings] = None
    ):
        self.vector_store = vector_store
        self.settings = settings or get_settings()
        self._reranker = None
    
    def retrieve(
        self,
        query: str,
        top_k: int = 5,
        min_score: float = 0.0,
        page_filter: Optional[List[int]] = None,
        rerank: bool = False
    ) -> RetrievalResult:
        """
        Recupera chunks relevantes para uma query.
        
        Args:
            query: Texto da query.
            top_k: Número de chunks a retornar.
            min_score: Score mínimo de similaridade.
            page_filter: Filtrar por páginas específicas.
            rerank: Se deve aplicar re-ranking.
        
        Returns:
            RetrievalResult: Resultado da recuperação.
        """
        # Busca inicial (pega mais se vai re-rankear)
        initial_k = top_k * 3 if rerank else top_k
        
        search_results = self.vector_store.search(query, initial_k)
        
        # Filtra por score mínimo
        if min_score > 0:
            search_results = [
                r for r in search_results 
                if r.score >= min_score
            ]
        
        # Filtra por páginas
        if page_filter:
            search_results = [
                r for r in search_results
                if r.chunk.page_number in page_filter
            ]
        
        # Re-ranking
        if rerank and search_results:
            search_results = self._rerank_results(query, search_results, top_k)
        else:
            search_results = search_results[:top_k]
        
        # Monta resultado
        chunks = [r.chunk for r in search_results]
        scores = [r.score for r in search_results]
        
        return RetrievalResult(
            query=query,
            chunks=chunks,
            scores=scores,
            total_retrieved=len(chunks),
            metadata={
                "min_score": min_score,
                "reranked": rerank,
                "page_filter": page_filter,
            }
        )
    
    def retrieve_for_questions(
        self,
        questions: List[str],
        top_k_per_question: int = 3,
        deduplicate: bool = True
    ) -> RetrievalResult:
        """
        Recupera chunks para múltiplas perguntas.
        
        Útil quando se quer contexto para várias instruções.
        
        Args:
            questions: Lista de perguntas/queries.
            top_k_per_question: Chunks por pergunta.
            deduplicate: Remove chunks duplicados.
        
        Returns:
            RetrievalResult: Resultado combinado.
        """
        all_chunks = []
        all_scores = []
        seen_ids = set()
        
        for question in questions:
            result = self.retrieve(question, top_k_per_question)
            
            for chunk, score in zip(result.chunks, result.scores):
                if deduplicate and chunk.chunk_id in seen_ids:
                    continue
                
                all_chunks.append(chunk)
                all_scores.append(score)
                seen_ids.add(chunk.chunk_id)
        
        # Ordena por score
        pairs = sorted(zip(all_chunks, all_scores), key=lambda x: x[1], reverse=True)
        
        if pairs:
            all_chunks, all_scores = zip(*pairs)
            all_chunks = list(all_chunks)
            all_scores = list(all_scores)
        else:
            all_chunks = []
            all_scores = []
        
        return RetrievalResult(
            query=" | ".join(questions),
            chunks=all_chunks,
            scores=all_scores,
            total_retrieved=len(all_chunks),
            metadata={"questions": questions}
        )
    
    def _rerank_results(
        self,
        query: str,
        results: List[VectorSearchResult],
        top_k: int
    ) -> List[VectorSearchResult]:
        """
        Re-rankeia resultados usando cross-encoder.
        
        Cross-encoders são mais precisos que bi-encoders para ranking.
        """
        if not results:
            return results
        
        try:
            if self._reranker is None:
                self._load_reranker()
            
            if self._reranker is None:
                # Fallback se reranker não disponível
                return results[:top_k]
            
            # Prepara pares query-documento
            pairs = [(query, r.chunk.text) for r in results]
            
            # Calcula scores
            rerank_scores = self._reranker.predict(pairs)
            
            # Reordena
            for i, score in enumerate(rerank_scores):
                results[i].score = float(score)
            
            results.sort(key=lambda x: x.score, reverse=True)
            
            return results[:top_k]
            
        except Exception as e:
            logger.warning(f"Erro no re-ranking: {e}. Usando ranking original.")
            return results[:top_k]
    
    def _load_reranker(self) -> None:
        """Carrega modelo de re-ranking."""
        try:
            from sentence_transformers import CrossEncoder
            
            # Usa modelo multilíngue
            model_name = "cross-encoder/ms-marco-MiniLM-L-6-v2"
            self._reranker = CrossEncoder(model_name)
            logger.info(f"Reranker carregado: {model_name}")
            
        except ImportError:
            logger.warning(
                "sentence-transformers não instalado. "
                "Re-ranking não disponível."
            )
        except Exception as e:
            logger.warning(f"Erro ao carregar reranker: {e}")
    
    def retrieve_with_mmr(
        self,
        query: str,
        top_k: int = 5,
        diversity: float = 0.3
    ) -> RetrievalResult:
        """
        Recupera com Maximal Marginal Relevance (MMR).
        
        MMR balanceia relevância com diversidade, evitando
        chunks muito similares entre si.
        
        Args:
            query: Texto da query.
            top_k: Número de chunks.
            diversity: Peso da diversidade (0-1).
        
        Returns:
            RetrievalResult: Resultado diversificado.
        """
        # Busca inicial mais ampla
        initial_results = self.vector_store.search(query, top_k * 5)
        
        if not initial_results:
            return RetrievalResult(
                query=query,
                chunks=[],
                scores=[],
                total_retrieved=0
            )
        
        # Embedding da query
        query_embedding = self.vector_store.embedding_provider.embed_text(query)
        
        # Embeddings dos candidatos
        candidate_texts = [r.chunk.text for r in initial_results]
        candidate_embeddings = self.vector_store.embedding_provider.embed_texts(
            candidate_texts
        )
        
        # Normaliza
        query_embedding = query_embedding / np.linalg.norm(query_embedding)
        candidate_embeddings = candidate_embeddings / np.linalg.norm(
            candidate_embeddings, axis=1, keepdims=True
        )
        
        # MMR iterativo
        selected_indices = []
        remaining_indices = list(range(len(initial_results)))
        
        while len(selected_indices) < top_k and remaining_indices:
            best_score = -float('inf')
            best_idx = -1
            
            for idx in remaining_indices:
                # Similaridade com query
                query_sim = np.dot(candidate_embeddings[idx], query_embedding)
                
                # Máxima similaridade com já selecionados
                if selected_indices:
                    selected_embeddings = candidate_embeddings[selected_indices]
                    max_sim_selected = np.max(
                        np.dot(selected_embeddings, candidate_embeddings[idx])
                    )
                else:
                    max_sim_selected = 0
                
                # Score MMR
                mmr_score = (1 - diversity) * query_sim - diversity * max_sim_selected
                
                if mmr_score > best_score:
                    best_score = mmr_score
                    best_idx = idx
            
            if best_idx >= 0:
                selected_indices.append(best_idx)
                remaining_indices.remove(best_idx)
        
        # Monta resultado
        chunks = [initial_results[i].chunk for i in selected_indices]
        scores = [initial_results[i].score for i in selected_indices]
        
        return RetrievalResult(
            query=query,
            chunks=chunks,
            scores=scores,
            total_retrieved=len(chunks),
            metadata={"method": "mmr", "diversity": diversity}
        )


class HybridRetriever(Retriever):
    """
    Retriever híbrido que combina busca vetorial com busca por keywords.
    """
    
    def __init__(
        self,
        vector_store: VectorStore,
        settings: Optional[Settings] = None,
        keyword_weight: float = 0.3
    ):
        super().__init__(vector_store, settings)
        self.keyword_weight = keyword_weight
    
    def retrieve(
        self,
        query: str,
        top_k: int = 5,
        min_score: float = 0.0,
        page_filter: Optional[List[int]] = None,
        rerank: bool = False
    ) -> RetrievalResult:
        """Busca híbrida combinando vetorial e keywords."""
        
        # Busca vetorial
        vector_results = self.vector_store.search(query, top_k * 2)
        
        # Busca por keywords
        keywords = self._extract_keywords(query)
        keyword_scores = self._keyword_search(keywords)
        
        # Combina scores
        combined_scores = {}
        
        for result in vector_results:
            cid = result.chunk.chunk_id
            combined_scores[cid] = {
                "chunk": result.chunk,
                "vector_score": result.score,
                "keyword_score": keyword_scores.get(cid, 0),
            }
        
        # Score final
        for cid, data in combined_scores.items():
            data["final_score"] = (
                (1 - self.keyword_weight) * data["vector_score"] +
                self.keyword_weight * data["keyword_score"]
            )
        
        # Ordena e filtra
        sorted_items = sorted(
            combined_scores.values(),
            key=lambda x: x["final_score"],
            reverse=True
        )
        
        # Aplica filtros
        if min_score > 0:
            sorted_items = [x for x in sorted_items if x["final_score"] >= min_score]
        
        if page_filter:
            sorted_items = [
                x for x in sorted_items 
                if x["chunk"].page_number in page_filter
            ]
        
        sorted_items = sorted_items[:top_k]
        
        chunks = [x["chunk"] for x in sorted_items]
        scores = [x["final_score"] for x in sorted_items]
        
        return RetrievalResult(
            query=query,
            chunks=chunks,
            scores=scores,
            total_retrieved=len(chunks),
            metadata={"method": "hybrid", "keyword_weight": self.keyword_weight}
        )
    
    def _extract_keywords(self, query: str) -> List[str]:
        """Extrai keywords da query."""
        import re
        
        # Remove stopwords simples
        stopwords = {
            "o", "a", "os", "as", "de", "da", "do", "das", "dos",
            "em", "no", "na", "nos", "nas", "que", "qual", "quais",
            "onde", "como", "quando", "por", "para", "com", "sem",
            "encontrar", "localizar", "buscar", "identificar", "verificar"
        }
        
        words = re.findall(r'\b\w+\b', query.lower())
        keywords = [w for w in words if w not in stopwords and len(w) > 2]
        
        return keywords
    
    def _keyword_search(self, keywords: List[str]) -> Dict[str, float]:
        """Calcula scores de keyword para todos os chunks."""
        scores = {}
        
        for chunk_id, chunk in self.vector_store._chunks.items():
            text_lower = chunk.text.lower()
            
            # Conta keywords encontradas
            found = sum(1 for kw in keywords if kw in text_lower)
            
            if found > 0:
                scores[chunk_id] = found / len(keywords)
        
        return scores
