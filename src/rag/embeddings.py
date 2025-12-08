"""
Módulo de embeddings para vetorização de texto.

Suporta:
- Embeddings locais com sentence-transformers (sem custo de tokens)
- Embeddings via API (OpenAI, etc.)
"""

from __future__ import annotations

import hashlib
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Union
import pickle

import numpy as np

from config.settings import Settings, get_settings

logger = logging.getLogger(__name__)


@dataclass
class EmbeddingResult:
    """Resultado de uma operação de embedding."""
    
    embeddings: np.ndarray
    model_name: str
    dimension: int
    token_count: int = 0


class EmbeddingProvider(ABC):
    """Classe base abstrata para provedores de embeddings."""
    
    def __init__(self, settings: Optional[Settings] = None):
        self.settings = settings or get_settings()
        self._dimension: int = 0
        self._model_name: str = ""
        self._cache: dict = {}
        self._initialized: bool = False
    
    @property
    def dimension(self) -> int:
        """Dimensão dos vetores de embedding."""
        return self._dimension
    
    @property
    def model_name(self) -> str:
        """Nome do modelo utilizado."""
        return self._model_name
    
    @abstractmethod
    def initialize(self) -> None:
        """Inicializa o provedor de embeddings."""
        pass
    
    @abstractmethod
    def embed_text(self, text: str) -> np.ndarray:
        """
        Gera embedding para um texto.
        
        Args:
            text: Texto para vetorizar.
        
        Returns:
            np.ndarray: Vetor de embedding.
        """
        pass
    
    @abstractmethod
    def embed_texts(self, texts: List[str]) -> np.ndarray:
        """
        Gera embeddings para múltiplos textos.
        
        Args:
            texts: Lista de textos.
        
        Returns:
            np.ndarray: Matriz de embeddings (n_texts x dimension).
        """
        pass
    
    def ensure_initialized(self) -> None:
        """Garante que o provedor está inicializado."""
        if not self._initialized:
            self.initialize()
    
    def _get_cache_key(self, text: str) -> str:
        """Gera chave de cache para um texto."""
        return hashlib.md5(text.encode()).hexdigest()
    
    def _get_cached(self, text: str) -> Optional[np.ndarray]:
        """Obtém embedding do cache se disponível."""
        key = self._get_cache_key(text)
        return self._cache.get(key)
    
    def _set_cache(self, text: str, embedding: np.ndarray) -> None:
        """Armazena embedding no cache."""
        # Limita tamanho do cache
        if len(self._cache) > 10000:
            # Remove metade dos itens mais antigos
            keys = list(self._cache.keys())[:5000]
            for k in keys:
                del self._cache[k]
        
        key = self._get_cache_key(text)
        self._cache[key] = embedding
    
    def save_cache(self, path: Path) -> None:
        """Salva cache em disco."""
        with open(path, 'wb') as f:
            pickle.dump(self._cache, f)
        logger.info(f"Cache de embeddings salvo: {path}")
    
    def load_cache(self, path: Path) -> None:
        """Carrega cache do disco."""
        if path.exists():
            with open(path, 'rb') as f:
                self._cache = pickle.load(f)
            logger.info(f"Cache de embeddings carregado: {len(self._cache)} entradas")


class LocalEmbeddings(EmbeddingProvider):
    """
    Provedor de embeddings local usando sentence-transformers.
    
    Não requer API externa nem consome tokens.
    """
    
    def __init__(
        self,
        settings: Optional[Settings] = None,
        model_name: Optional[str] = None
    ):
        super().__init__(settings)
        self._model = None
        self._custom_model_name = model_name
    
    def initialize(self) -> None:
        """Inicializa o modelo sentence-transformers."""
        if self._initialized:
            return
        
        try:
            from sentence_transformers import SentenceTransformer
            
            # Usa modelo customizado ou da configuração
            self._model_name = (
                self._custom_model_name or 
                self.settings.nlp.local.sentence_transformer
            )
            
            logger.info(f"Carregando modelo de embeddings: {self._model_name}")
            self._model = SentenceTransformer(self._model_name)
            
            # Obtém dimensão do modelo
            self._dimension = self._model.get_sentence_embedding_dimension()
            
            self._initialized = True
            logger.info(
                f"Modelo carregado: {self._model_name} "
                f"(dimensão: {self._dimension})"
            )
            
        except ImportError:
            raise ImportError(
                "sentence-transformers não instalado. "
                "Instale com: pip install sentence-transformers"
            )
        except Exception as e:
            logger.error(f"Erro ao carregar modelo: {e}")
            raise
    
    def embed_text(self, text: str) -> np.ndarray:
        """Gera embedding para um texto."""
        self.ensure_initialized()
        
        # Verifica cache
        cached = self._get_cached(text)
        if cached is not None:
            return cached
        
        # Gera embedding
        embedding = self._model.encode(text, convert_to_numpy=True)
        
        # Armazena no cache
        self._set_cache(text, embedding)
        
        return embedding
    
    def embed_texts(self, texts: List[str]) -> np.ndarray:
        """Gera embeddings para múltiplos textos em batch."""
        self.ensure_initialized()
        
        if not texts:
            return np.array([])
        
        # Separa textos com e sem cache
        results = [None] * len(texts)
        texts_to_embed = []
        indices_to_embed = []
        
        for i, text in enumerate(texts):
            cached = self._get_cached(text)
            if cached is not None:
                results[i] = cached
            else:
                texts_to_embed.append(text)
                indices_to_embed.append(i)
        
        # Gera embeddings para textos não cacheados
        if texts_to_embed:
            new_embeddings = self._model.encode(
                texts_to_embed,
                convert_to_numpy=True,
                show_progress_bar=len(texts_to_embed) > 100
            )
            
            for idx, embedding, text in zip(
                indices_to_embed, new_embeddings, texts_to_embed
            ):
                results[idx] = embedding
                self._set_cache(text, embedding)
        
        return np.array(results)
    
    def embed_query(self, query: str) -> np.ndarray:
        """
        Gera embedding otimizado para queries.
        
        Alguns modelos têm prefixos especiais para queries vs documentos.
        """
        self.ensure_initialized()
        
        # Adiciona prefixo se o modelo suportar
        if "e5" in self._model_name.lower():
            query = f"query: {query}"
        elif "bge" in self._model_name.lower():
            query = f"Represent this sentence for searching: {query}"
        
        return self.embed_text(query)


class CloudEmbeddings(EmbeddingProvider):
    """
    Provedor de embeddings via API cloud (OpenAI, etc.).
    
    Requer API key e consome tokens.
    """
    
    def __init__(
        self,
        settings: Optional[Settings] = None,
        provider: Optional[str] = None
    ):
        super().__init__(settings)
        self._client = None
        self._provider = provider or self.settings.nlp.cloud.provider
        self._token_count = 0
    
    @property
    def tokens_used(self) -> int:
        """Total de tokens utilizados."""
        return self._token_count
    
    def initialize(self) -> None:
        """Inicializa cliente da API."""
        if self._initialized:
            return
        
        if self._provider == "openai":
            self._init_openai()
        else:
            raise ValueError(f"Provedor não suportado para embeddings: {self._provider}")
        
        self._initialized = True
    
    def _init_openai(self) -> None:
        """Inicializa cliente OpenAI."""
        try:
            from openai import OpenAI
            
            api_key = self.settings.nlp.cloud.api_key
            if not api_key:
                raise ValueError(
                    "API key não configurada. "
                    f"Defina {self.settings.nlp.cloud.api_key_env}"
                )
            
            self._client = OpenAI(api_key=api_key)
            self._model_name = "text-embedding-3-small"
            self._dimension = 1536
            
            logger.info(f"Cliente OpenAI inicializado para embeddings")
            
        except ImportError:
            raise ImportError("openai não instalado. Instale com: pip install openai")
    
    def embed_text(self, text: str) -> np.ndarray:
        """Gera embedding via API."""
        self.ensure_initialized()
        
        # Verifica cache
        cached = self._get_cached(text)
        if cached is not None:
            return cached
        
        if self._provider == "openai":
            response = self._client.embeddings.create(
                model=self._model_name,
                input=text
            )
            embedding = np.array(response.data[0].embedding)
            self._token_count += response.usage.total_tokens
        else:
            raise ValueError(f"Provedor não suportado: {self._provider}")
        
        self._set_cache(text, embedding)
        return embedding
    
    def embed_texts(self, texts: List[str]) -> np.ndarray:
        """Gera embeddings em batch via API."""
        self.ensure_initialized()
        
        if not texts:
            return np.array([])
        
        # Separa textos com e sem cache
        results = [None] * len(texts)
        texts_to_embed = []
        indices_to_embed = []
        
        for i, text in enumerate(texts):
            cached = self._get_cached(text)
            if cached is not None:
                results[i] = cached
            else:
                texts_to_embed.append(text)
                indices_to_embed.append(i)
        
        # Gera embeddings para textos não cacheados
        if texts_to_embed:
            if self._provider == "openai":
                # OpenAI suporta batch de até 2048 textos
                batch_size = 100
                for batch_start in range(0, len(texts_to_embed), batch_size):
                    batch = texts_to_embed[batch_start:batch_start + batch_size]
                    batch_indices = indices_to_embed[batch_start:batch_start + batch_size]
                    
                    response = self._client.embeddings.create(
                        model=self._model_name,
                        input=batch
                    )
                    
                    self._token_count += response.usage.total_tokens
                    
                    for j, data in enumerate(response.data):
                        embedding = np.array(data.embedding)
                        idx = batch_indices[j]
                        results[idx] = embedding
                        self._set_cache(texts_to_embed[batch_start + j], embedding)
        
        return np.array(results)


def get_embedding_provider(
    mode: Optional[str] = None,
    settings: Optional[Settings] = None
) -> EmbeddingProvider:
    """
    Factory para obter provedor de embeddings.
    
    Args:
        mode: "local" ou "cloud". Se None, usa configuração.
        settings: Configurações do aplicativo.
    
    Returns:
        EmbeddingProvider: Provedor configurado.
    """
    settings = settings or get_settings()
    mode = mode or settings.nlp.mode
    
    if mode == "local":
        return LocalEmbeddings(settings)
    elif mode == "cloud":
        return CloudEmbeddings(settings)
    else:
        raise ValueError(f"Modo não suportado: {mode}")
