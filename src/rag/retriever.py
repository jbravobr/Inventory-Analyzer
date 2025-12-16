"""
Módulo de Retrieval para recuperação de contexto relevante.

Combina busca vetorial com BM25 e re-ranking para obter os chunks
mais relevantes para uma query.

Estratégias disponíveis:
- Retriever: Busca vetorial simples com embeddings
- HybridRetriever: Combina vetorial + keywords básico
- HybridRetrieverV2: Combina BM25 + embeddings com RRF (Recomendado)
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any

import numpy as np

from config.settings import Settings, get_settings
from .chunker import Chunk
from .vector_store import VectorStore, VectorSearchResult
from .bm25_retriever import BM25Retriever, BM25Result

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


class HybridRetrieverV2(Retriever):
    """
    Retriever híbrido avançado que combina BM25 + embeddings semânticos.
    
    Usa Reciprocal Rank Fusion (RRF) para combinar os rankings de forma
    mais robusta que soma simples de scores.
    
    Vantagens sobre HybridRetriever:
    - BM25 é mais sofisticado que busca por keywords simples
    - RRF é mais robusto para combinar rankings
    - Melhor performance com termos técnicos e nomes próprios
    """
    
    def __init__(
        self,
        vector_store: VectorStore,
        settings: Optional[Settings] = None,
        bm25_weight: float = 0.4,
        semantic_weight: float = 0.6,
        rrf_k: int = 60  # Parâmetro RRF (padrão: 60)
    ):
        """
        Args:
            vector_store: Store de vetores para busca semântica
            settings: Configurações
            bm25_weight: Peso do BM25 no score final (0.0 a 1.0)
            semantic_weight: Peso dos embeddings no score final (0.0 a 1.0)
            rrf_k: Constante k do RRF (valores maiores = rankings mais suaves)
        """
        super().__init__(vector_store, settings)
        self.bm25_weight = bm25_weight
        self.semantic_weight = semantic_weight
        self.rrf_k = rrf_k
        
        # Inicializa BM25 retriever
        self._bm25_retriever: Optional[BM25Retriever] = None
        self._chunks_indexed = False
    
    def _ensure_bm25_indexed(self) -> None:
        """Garante que o índice BM25 está construído."""
        if self._bm25_retriever is None:
            self._bm25_retriever = BM25Retriever()
        
        if not self._chunks_indexed:
            # Obtém chunks do vector store
            chunks = list(self.vector_store._chunks.values())
            if chunks:
                self._bm25_retriever.index_chunks(chunks)
                self._chunks_indexed = True
                logger.info(f"BM25 indexado com {len(chunks)} chunks")
    
    def _rrf_score(self, rank: int) -> float:
        """
        Calcula score RRF (Reciprocal Rank Fusion).
        
        RRF = 1 / (k + rank)
        
        Onde k é uma constante (padrão 60) e rank começa em 1.
        """
        return 1.0 / (self.rrf_k + rank)
    
    def retrieve(
        self,
        query: str,
        top_k: int = 5,
        min_score: float = 0.0,
        page_filter: Optional[List[int]] = None,
        rerank: bool = False
    ) -> RetrievalResult:
        """
        Busca híbrida combinando BM25 e embeddings semânticos.
        
        O processo:
        1. Busca com BM25 (lexical)
        2. Busca com embeddings (semântico)
        3. Combina usando RRF (Reciprocal Rank Fusion)
        4. Aplica filtros e retorna top_k
        """
        self._ensure_bm25_indexed()
        
        # Número de candidatos a buscar de cada método
        candidates_per_method = top_k * 3
        
        # 1. Busca BM25
        bm25_results = []
        if self._bm25_retriever:
            bm25_results = self._bm25_retriever.retrieve(
                query, 
                top_k=candidates_per_method,
                min_score=0.0
            )
        
        # 2. Busca semântica
        semantic_results = self.vector_store.search(query, candidates_per_method)
        
        # 3. Combina com RRF
        combined_scores: Dict[str, Dict[str, Any]] = {}
        
        # Processa resultados BM25
        for rank, result in enumerate(bm25_results, start=1):
            chunk_id = result.chunk.chunk_id
            rrf = self._rrf_score(rank) * self.bm25_weight
            
            if chunk_id not in combined_scores:
                combined_scores[chunk_id] = {
                    "chunk": result.chunk,
                    "bm25_score": result.score,
                    "bm25_rank": rank,
                    "semantic_score": 0.0,
                    "semantic_rank": 0,
                    "rrf_score": 0.0,
                    "matched_terms": result.matched_terms,
                }
            
            combined_scores[chunk_id]["rrf_score"] += rrf
        
        # Processa resultados semânticos
        for rank, result in enumerate(semantic_results, start=1):
            chunk_id = result.chunk.chunk_id
            rrf = self._rrf_score(rank) * self.semantic_weight
            
            if chunk_id not in combined_scores:
                combined_scores[chunk_id] = {
                    "chunk": result.chunk,
                    "bm25_score": 0.0,
                    "bm25_rank": 0,
                    "semantic_score": result.score,
                    "semantic_rank": rank,
                    "rrf_score": 0.0,
                    "matched_terms": [],
                }
            
            combined_scores[chunk_id]["semantic_score"] = result.score
            combined_scores[chunk_id]["semantic_rank"] = rank
            combined_scores[chunk_id]["rrf_score"] += rrf
        
        # 4. Ordena por RRF score
        sorted_results = sorted(
            combined_scores.values(),
            key=lambda x: x["rrf_score"],
            reverse=True
        )
        
        # Aplica filtros
        if page_filter:
            sorted_results = [
                r for r in sorted_results
                if r["chunk"].page_number in page_filter
            ]
        
        if min_score > 0:
            # Normaliza RRF score para [0, 1] antes de filtrar
            max_rrf = max((r["rrf_score"] for r in sorted_results), default=1.0)
            sorted_results = [
                r for r in sorted_results
                if r["rrf_score"] / max_rrf >= min_score
            ]
        
        # Seleciona top_k
        sorted_results = sorted_results[:top_k]
        
        # Re-ranking opcional
        if rerank and sorted_results:
            sorted_results = self._rerank_hybrid_results(query, sorted_results, top_k)
        
        # Monta resultado
        chunks = [r["chunk"] for r in sorted_results]
        
        # Score final é RRF normalizado
        max_rrf = max((r["rrf_score"] for r in sorted_results), default=1.0)
        scores = [r["rrf_score"] / max_rrf if max_rrf > 0 else 0.0 for r in sorted_results]
        
        return RetrievalResult(
            query=query,
            chunks=chunks,
            scores=scores,
            total_retrieved=len(chunks),
            metadata={
                "method": "hybrid_v2",
                "bm25_weight": self.bm25_weight,
                "semantic_weight": self.semantic_weight,
                "bm25_candidates": len(bm25_results),
                "semantic_candidates": len(semantic_results),
            }
        )
    
    def _rerank_hybrid_results(
        self,
        query: str,
        results: List[Dict[str, Any]],
        top_k: int
    ) -> List[Dict[str, Any]]:
        """Re-rankeia resultados híbridos usando cross-encoder."""
        try:
            if self._reranker is None:
                self._load_reranker()
            
            if self._reranker is None:
                return results[:top_k]
            
            # Prepara pares
            pairs = [(query, r["chunk"].text) for r in results]
            
            # Calcula scores
            rerank_scores = self._reranker.predict(pairs)
            
            # Atualiza RRF scores com rerank
            for i, score in enumerate(rerank_scores):
                # Combina RRF com rerank score
                results[i]["rerank_score"] = float(score)
                results[i]["rrf_score"] = (
                    results[i]["rrf_score"] * 0.7 + 
                    float(score) * 0.3
                )
            
            # Reordena
            results.sort(key=lambda x: x["rrf_score"], reverse=True)
            
            return results[:top_k]
            
        except Exception as e:
            logger.warning(f"Erro no re-ranking híbrido: {e}")
            return results[:top_k]
    
    def get_bm25_stats(self) -> Dict[str, Any]:
        """Retorna estatísticas do índice BM25."""
        if self._bm25_retriever:
            return self._bm25_retriever.index.get_stats()
        return {"indexed": False}
