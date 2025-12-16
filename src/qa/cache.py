"""
Cache de Respostas do Q&A.

Armazena respostas frequentes para evitar reprocessamento
e melhorar a performance.
"""

from __future__ import annotations

import hashlib
import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Optional, Any, List
import threading

logger = logging.getLogger(__name__)


@dataclass
class CachedResponse:
    """Resposta armazenada em cache."""
    
    question: str
    answer: str
    context_hash: str
    pages: List[int]
    confidence: float
    template_used: str
    created_at: datetime
    access_count: int = 0
    last_accessed: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)
    rules_hash: str = ""  # Hash do arquivo .rules usado (para invalidação)
    
    def to_dict(self) -> dict:
        return {
            "question": self.question,
            "answer": self.answer,
            "context_hash": self.context_hash,
            "pages": self.pages,
            "confidence": self.confidence,
            "template_used": self.template_used,
            "created_at": self.created_at.isoformat(),
            "access_count": self.access_count,
            "last_accessed": self.last_accessed.isoformat(),
            "metadata": self.metadata,
            "rules_hash": self.rules_hash,
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "CachedResponse":
        return cls(
            question=data["question"],
            answer=data["answer"],
            context_hash=data["context_hash"],
            pages=data.get("pages", []),
            confidence=data.get("confidence", 0.0),
            template_used=data.get("template_used", ""),
            created_at=datetime.fromisoformat(data["created_at"]),
            access_count=data.get("access_count", 0),
            last_accessed=datetime.fromisoformat(
                data.get("last_accessed", data["created_at"])
            ),
            metadata=data.get("metadata", {}),
            rules_hash=data.get("rules_hash", ""),
        )


class ResponseCache:
    """
    Cache de respostas do Q&A.
    
    Funciona em memória com persistência opcional em disco.
    Usa TTL (time-to-live) e LRU (least recently used) para
    gerenciar o tamanho do cache.
    """
    
    def __init__(
        self,
        max_size: int = 1000,
        ttl_hours: int = 24,
        cache_dir: Optional[Path] = None,
        persist: bool = True
    ):
        """
        Inicializa o cache.
        
        Args:
            max_size: Número máximo de entradas
            ttl_hours: Tempo de vida em horas
            cache_dir: Diretório para persistência
            persist: Se deve persistir em disco
        """
        self.max_size = max_size
        self.ttl = timedelta(hours=ttl_hours)
        self.cache_dir = cache_dir or Path("./cache/qa_responses")
        self.persist = persist
        
        self._cache: Dict[str, CachedResponse] = {}
        self._lock = threading.Lock()
        
        if self.persist:
            self._load_from_disk()
    
    def _generate_key(
        self,
        question: str,
        document_name: str,
        template: str = ""
    ) -> str:
        """
        Gera chave única para uma pergunta.
        
        Args:
            question: Pergunta
            document_name: Nome do documento
            template: Template usado
        
        Returns:
            Hash único
        """
        content = f"{question.lower().strip()}|{document_name}|{template}"
        return hashlib.sha256(content.encode()).hexdigest()[:16]
    
    def _generate_context_hash(self, context: str) -> str:
        """Gera hash do contexto para verificar mudanças."""
        return hashlib.md5(context.encode()).hexdigest()[:8]
    
    def get(
        self,
        question: str,
        document_name: str,
        context: str,
        template: str = "",
        rules_hash: str = ""
    ) -> Optional[CachedResponse]:
        """
        Obtém resposta do cache.
        
        Args:
            question: Pergunta
            document_name: Nome do documento
            context: Contexto atual (para verificar se mudou)
            template: Template usado
            rules_hash: Hash do arquivo .rules atual
        
        Returns:
            CachedResponse ou None se não encontrado/expirado
        """
        key = self._generate_key(question, document_name, template)
        context_hash = self._generate_context_hash(context)
        
        with self._lock:
            if key not in self._cache:
                return None
            
            cached = self._cache[key]
            
            # Verifica TTL
            if datetime.now() - cached.created_at > self.ttl:
                del self._cache[key]
                logger.debug(f"Cache expirado: {key}")
                return None
            
            # Verifica se contexto mudou
            if cached.context_hash != context_hash:
                del self._cache[key]
                logger.debug(f"Contexto mudou, cache invalidado: {key}")
                return None
            
            # Verifica se regras DKR mudaram
            if rules_hash and cached.rules_hash and cached.rules_hash != rules_hash:
                del self._cache[key]
                logger.debug(f"Regras DKR mudaram, cache invalidado: {key}")
                return None
            
            # Atualiza estatísticas
            cached.access_count += 1
            cached.last_accessed = datetime.now()
            
            logger.debug(f"Cache hit: {key}")
            return cached
    
    def set(
        self,
        question: str,
        answer: str,
        document_name: str,
        context: str,
        pages: List[int],
        confidence: float,
        template: str = "",
        metadata: Optional[Dict[str, Any]] = None,
        rules_hash: str = ""
    ) -> str:
        """
        Armazena resposta no cache.
        
        Args:
            question: Pergunta
            answer: Resposta
            document_name: Nome do documento
            context: Contexto usado
            pages: Páginas referenciadas
            confidence: Confiança da resposta
            template: Template usado
            metadata: Metadados adicionais
            rules_hash: Hash do arquivo .rules usado
        
        Returns:
            Chave do cache
        """
        key = self._generate_key(question, document_name, template)
        context_hash = self._generate_context_hash(context)
        
        cached = CachedResponse(
            question=question,
            answer=answer,
            context_hash=context_hash,
            pages=pages,
            confidence=confidence,
            template_used=template,
            created_at=datetime.now(),
            metadata=metadata or {},
            rules_hash=rules_hash,
        )
        
        with self._lock:
            # Limpa cache se atingiu limite
            if len(self._cache) >= self.max_size:
                self._evict_lru()
            
            self._cache[key] = cached
        
        logger.debug(f"Cache set: {key}")
        
        # Persiste em background
        if self.persist:
            self._save_to_disk()
        
        return key
    
    def invalidate(
        self,
        question: Optional[str] = None,
        document_name: Optional[str] = None
    ) -> int:
        """
        Invalida entradas do cache.
        
        Args:
            question: Pergunta específica (opcional)
            document_name: Documento específico (opcional)
        
        Returns:
            Número de entradas removidas
        """
        removed = 0
        
        with self._lock:
            if question and document_name:
                # Remove entrada específica
                key = self._generate_key(question, document_name)
                if key in self._cache:
                    del self._cache[key]
                    removed = 1
            else:
                # Remove todas as entradas que correspondem
                keys_to_remove = []
                
                for key, cached in self._cache.items():
                    if document_name and document_name not in cached.metadata.get("document", ""):
                        continue
                    if question and question.lower() not in cached.question.lower():
                        continue
                    keys_to_remove.append(key)
                
                for key in keys_to_remove:
                    del self._cache[key]
                    removed += 1
        
        logger.info(f"Cache invalidado: {removed} entradas removidas")
        
        if self.persist and removed > 0:
            self._save_to_disk()
        
        return removed
    
    def clear(self) -> int:
        """
        Limpa todo o cache.
        
        Returns:
            Número de entradas removidas
        """
        with self._lock:
            count = len(self._cache)
            self._cache.clear()
        
        logger.info(f"Cache limpo: {count} entradas")
        
        if self.persist:
            self._save_to_disk()
        
        return count
    
    def _evict_lru(self) -> None:
        """Remove entradas menos recentemente usadas."""
        if not self._cache:
            return
        
        # Remove 10% das entradas mais antigas
        to_remove = max(1, len(self._cache) // 10)
        
        # Ordena por último acesso
        sorted_items = sorted(
            self._cache.items(),
            key=lambda x: x[1].last_accessed
        )
        
        for key, _ in sorted_items[:to_remove]:
            del self._cache[key]
        
        logger.debug(f"Evicted {to_remove} entradas LRU")
    
    def _save_to_disk(self) -> None:
        """Salva cache em disco."""
        if not self.persist:
            return
        
        try:
            self.cache_dir.mkdir(parents=True, exist_ok=True)
            cache_file = self.cache_dir / "qa_cache.json"
            
            with self._lock:
                data = {
                    key: cached.to_dict()
                    for key, cached in self._cache.items()
                }
            
            with open(cache_file, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            
            logger.debug(f"Cache salvo: {len(data)} entradas")
            
        except Exception as e:
            logger.warning(f"Erro ao salvar cache: {e}")
    
    def _load_from_disk(self) -> None:
        """Carrega cache do disco."""
        cache_file = self.cache_dir / "qa_cache.json"
        
        if not cache_file.exists():
            return
        
        try:
            with open(cache_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            
            loaded = 0
            now = datetime.now()
            
            for key, item_data in data.items():
                cached = CachedResponse.from_dict(item_data)
                
                # Ignora entradas expiradas
                if now - cached.created_at > self.ttl:
                    continue
                
                self._cache[key] = cached
                loaded += 1
            
            logger.info(f"Cache carregado: {loaded} entradas")
            
        except Exception as e:
            logger.warning(f"Erro ao carregar cache: {e}")
    
    def get_stats(self) -> Dict[str, Any]:
        """Retorna estatísticas do cache."""
        with self._lock:
            total_accesses = sum(c.access_count for c in self._cache.values())
            avg_confidence = (
                sum(c.confidence for c in self._cache.values()) / len(self._cache)
                if self._cache else 0
            )
        
        return {
            "entries": len(self._cache),
            "max_size": self.max_size,
            "ttl_hours": self.ttl.total_seconds() / 3600,
            "total_accesses": total_accesses,
            "avg_confidence": avg_confidence,
            "persist_enabled": self.persist,
            "cache_dir": str(self.cache_dir),
        }
    
    def get_frequent_questions(self, top_n: int = 10) -> List[Dict[str, Any]]:
        """
        Retorna as perguntas mais frequentes.
        
        Args:
            top_n: Número de perguntas a retornar
        
        Returns:
            Lista de perguntas ordenadas por frequência
        """
        with self._lock:
            sorted_items = sorted(
                self._cache.values(),
                key=lambda x: x.access_count,
                reverse=True
            )
        
        return [
            {
                "question": item.question,
                "access_count": item.access_count,
                "confidence": item.confidence,
            }
            for item in sorted_items[:top_n]
        ]

