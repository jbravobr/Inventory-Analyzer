"""
Módulo de Retrieval BM25 para busca lexical.

BM25 (Best Matching 25) é um algoritmo de ranking baseado em TF-IDF
que funciona bem para busca por keywords e complementa embeddings semânticos.

Vantagens:
- Rápido e eficiente (não requer GPU)
- Funciona bem com termos técnicos e nomes próprios
- Complementa embeddings semânticos que podem perder termos exatos
- 100% offline
"""

from __future__ import annotations

import logging
import re
import unicodedata
from dataclasses import dataclass
from typing import List, Optional, Dict, Set

from .chunker import Chunk

logger = logging.getLogger(__name__)


# Stopwords em português para BM25
PORTUGUESE_STOPWORDS = {
    "a", "ao", "aos", "aquela", "aquelas", "aquele", "aqueles", "aquilo",
    "as", "até", "com", "como", "da", "das", "de", "dela", "delas", "dele",
    "deles", "depois", "do", "dos", "e", "ela", "elas", "ele", "eles", "em",
    "entre", "era", "eram", "essa", "essas", "esse", "esses", "esta", "estas",
    "este", "estes", "eu", "foi", "fomos", "for", "fora", "foram", "forem",
    "fosse", "fossem", "há", "isso", "isto", "já", "lhe", "lhes", "lo", "mas",
    "me", "mesmo", "meu", "meus", "minha", "minhas", "muito", "na", "nas",
    "nem", "no", "nos", "nossa", "nossas", "nosso", "nossos", "num", "numa",
    "não", "nós", "o", "os", "ou", "para", "pela", "pelas", "pelo", "pelos",
    "por", "qual", "quando", "que", "quem", "se", "seja", "sejam", "sem",
    "seu", "seus", "só", "somos", "sou", "sua", "suas", "são", "também",
    "te", "tem", "temos", "ter", "teu", "teus", "tinha", "tinham", "tu",
    "tua", "tuas", "tudo", "um", "uma", "umas", "uns", "você", "vocês", "vos",
    "à", "às", "é", "éramos",
    # Termos comuns em documentos que não agregam valor semântico
    "conforme", "referente", "mediante", "presente", "sendo", "tendo",
}


@dataclass
class BM25Result:
    """Resultado de uma busca BM25."""
    
    chunk: Chunk
    score: float
    matched_terms: List[str]
    
    def to_dict(self) -> dict:
        return {
            "chunk_id": self.chunk.chunk_id,
            "score": self.score,
            "matched_terms": self.matched_terms,
            "page": self.chunk.page_number,
        }


class PortugueseTokenizer:
    """
    Tokenizador otimizado para português.
    
    Características:
    - Remove acentos para matching mais flexível
    - Remove stopwords
    - Normaliza números e siglas
    - Preserva termos técnicos (GPL, AGPL, etc.)
    """
    
    def __init__(
        self,
        stopwords: Optional[Set[str]] = None,
        min_token_length: int = 2,
        preserve_technical_terms: bool = True
    ):
        self.stopwords = stopwords or PORTUGUESE_STOPWORDS
        self.min_token_length = min_token_length
        self.preserve_technical_terms = preserve_technical_terms
        
        # Termos técnicos que devem ser preservados (licenças, etc.)
        self.technical_terms = {
            "gpl", "agpl", "lgpl", "mit", "apache", "bsd", "mpl",
            "btg", "cdb", "lci", "lca", "cri", "cra", "fii", "etf",
            "cpf", "cnpj", "rg", "ntn", "lft", "ltn",
        }
    
    def normalize_text(self, text: str) -> str:
        """Remove acentos e normaliza texto."""
        # Normaliza para NFD (decompõe caracteres acentuados)
        normalized = unicodedata.normalize('NFD', text)
        # Remove marcas diacríticas (acentos)
        without_accents = ''.join(
            char for char in normalized
            if unicodedata.category(char) != 'Mn'
        )
        return without_accents.lower()
    
    def tokenize(self, text: str) -> List[str]:
        """
        Tokeniza texto em português.
        
        Args:
            text: Texto para tokenizar
            
        Returns:
            Lista de tokens normalizados
        """
        # Normaliza texto
        normalized = self.normalize_text(text)
        
        # Extrai tokens (palavras e números)
        raw_tokens = re.findall(r'\b[\w\d]+\b', normalized)
        
        # Filtra e processa tokens
        tokens = []
        for token in raw_tokens:
            # Preserva termos técnicos independente do tamanho
            if self.preserve_technical_terms and token in self.technical_terms:
                tokens.append(token)
                continue
            
            # Ignora tokens muito curtos
            if len(token) < self.min_token_length:
                continue
            
            # Remove stopwords
            if token in self.stopwords:
                continue
            
            tokens.append(token)
        
        return tokens


class BM25Index:
    """
    Índice BM25 para busca lexical em chunks.
    
    Implementação do algoritmo Okapi BM25 otimizada para português.
    
    Parâmetros BM25:
    - k1: Controla saturação de frequência de termo (padrão: 1.5)
    - b: Controla normalização por tamanho do documento (padrão: 0.75)
    """
    
    def __init__(
        self,
        k1: float = 1.5,
        b: float = 0.75,
        tokenizer: Optional[PortugueseTokenizer] = None
    ):
        self.k1 = k1
        self.b = b
        self.tokenizer = tokenizer or PortugueseTokenizer()
        
        # Índice
        self._chunks: Dict[str, Chunk] = {}
        self._corpus: List[List[str]] = []
        self._chunk_ids: List[str] = []
        self._doc_freqs: Dict[str, int] = {}  # Frequência de documento
        self._doc_lens: List[int] = []
        self._avgdl: float = 0.0
        self._n_docs: int = 0
        
        self._indexed = False
    
    def index_chunks(self, chunks: List[Chunk]) -> int:
        """
        Indexa lista de chunks.
        
        Args:
            chunks: Lista de chunks para indexar
            
        Returns:
            Número de chunks indexados
        """
        self._chunks = {}
        self._corpus = []
        self._chunk_ids = []
        self._doc_freqs = {}
        self._doc_lens = []
        
        for chunk in chunks:
            # Tokeniza texto do chunk
            tokens = self.tokenizer.tokenize(chunk.text)
            
            if not tokens:
                continue
            
            self._chunks[chunk.chunk_id] = chunk
            self._corpus.append(tokens)
            self._chunk_ids.append(chunk.chunk_id)
            self._doc_lens.append(len(tokens))
            
            # Atualiza frequência de documento
            seen_terms = set()
            for token in tokens:
                if token not in seen_terms:
                    self._doc_freqs[token] = self._doc_freqs.get(token, 0) + 1
                    seen_terms.add(token)
        
        self._n_docs = len(self._corpus)
        self._avgdl = sum(self._doc_lens) / self._n_docs if self._n_docs > 0 else 0
        
        self._indexed = True
        logger.info(f"BM25: {self._n_docs} chunks indexados, {len(self._doc_freqs)} termos únicos")
        
        return self._n_docs
    
    def _idf(self, term: str) -> float:
        """Calcula IDF (Inverse Document Frequency) para um termo."""
        if term not in self._doc_freqs:
            return 0.0
        
        df = self._doc_freqs[term]
        # IDF com suavização
        import math
        return math.log((self._n_docs - df + 0.5) / (df + 0.5) + 1)
    
    def _score_document(
        self,
        query_tokens: List[str],
        doc_idx: int
    ) -> tuple[float, List[str]]:
        """
        Calcula score BM25 para um documento.
        
        Returns:
            Tuple (score, matched_terms)
        """
        doc_tokens = self._corpus[doc_idx]
        doc_len = self._doc_lens[doc_idx]
        
        # Conta frequências no documento
        term_freqs = {}
        for token in doc_tokens:
            term_freqs[token] = term_freqs.get(token, 0) + 1
        
        score = 0.0
        matched_terms = []
        
        for term in query_tokens:
            if term not in term_freqs:
                continue
            
            matched_terms.append(term)
            
            tf = term_freqs[term]
            idf = self._idf(term)
            
            # BM25 scoring formula
            numerator = tf * (self.k1 + 1)
            denominator = tf + self.k1 * (1 - self.b + self.b * doc_len / self._avgdl)
            
            score += idf * (numerator / denominator)
        
        return score, matched_terms
    
    def search(
        self,
        query: str,
        top_k: int = 10,
        min_score: float = 0.0
    ) -> List[BM25Result]:
        """
        Busca chunks usando BM25.
        
        Args:
            query: Texto da query
            top_k: Número máximo de resultados
            min_score: Score mínimo para incluir resultado
            
        Returns:
            Lista de BM25Result ordenados por score
        """
        if not self._indexed:
            logger.warning("BM25: Índice não construído")
            return []
        
        # Tokeniza query
        query_tokens = self.tokenizer.tokenize(query)
        
        if not query_tokens:
            logger.warning("BM25: Query vazia após tokenização")
            return []
        
        # Calcula scores para todos os documentos
        results = []
        for idx in range(self._n_docs):
            score, matched_terms = self._score_document(query_tokens, idx)
            
            if score > min_score and matched_terms:
                chunk_id = self._chunk_ids[idx]
                chunk = self._chunks[chunk_id]
                results.append(BM25Result(
                    chunk=chunk,
                    score=score,
                    matched_terms=matched_terms
                ))
        
        # Ordena por score e retorna top_k
        results.sort(key=lambda x: x.score, reverse=True)
        
        return results[:top_k]
    
    def get_stats(self) -> Dict[str, any]:
        """Retorna estatísticas do índice."""
        return {
            "n_docs": self._n_docs,
            "n_terms": len(self._doc_freqs),
            "avg_doc_length": self._avgdl,
            "indexed": self._indexed,
        }


class BM25Retriever:
    """
    Retriever baseado em BM25 para pré-filtro de chunks.
    
    Pode ser usado:
    1. Como pré-filtro antes de embeddings semânticos
    2. Em combinação com embeddings (busca híbrida)
    3. Sozinho para queries com termos técnicos específicos
    """
    
    def __init__(
        self,
        k1: float = 1.5,
        b: float = 0.75
    ):
        self.index = BM25Index(k1=k1, b=b)
        self._chunks: List[Chunk] = []
    
    def index_chunks(self, chunks: List[Chunk]) -> int:
        """Indexa chunks para busca."""
        self._chunks = chunks
        return self.index.index_chunks(chunks)
    
    def retrieve(
        self,
        query: str,
        top_k: int = 10,
        min_score: float = 0.0
    ) -> List[BM25Result]:
        """
        Recupera chunks relevantes usando BM25.
        
        Args:
            query: Pergunta ou texto de busca
            top_k: Número máximo de resultados
            min_score: Score mínimo
            
        Returns:
            Lista de resultados BM25
        """
        return self.index.search(query, top_k, min_score)
    
    def prefilter_chunks(
        self,
        query: str,
        expansion_factor: int = 3
    ) -> List[Chunk]:
        """
        Pré-filtra chunks para reduzir conjunto de candidatos
        antes de aplicar embeddings semânticos.
        
        Args:
            query: Texto da query
            expansion_factor: Multiplicador para número de candidatos
            
        Returns:
            Lista de chunks candidatos
        """
        # Busca mais candidatos que o necessário para dar margem
        results = self.index.search(query, top_k=50, min_score=0.0)
        
        if not results:
            # Fallback: retorna todos os chunks
            return self._chunks
        
        return [r.chunk for r in results]

