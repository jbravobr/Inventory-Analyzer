"""
Cache de Extracao OCR.

Armazena o texto extraido de documentos PDF para evitar
reprocessamento custoso do OCR.

O cache usa hash SHA-256 do conteudo do PDF para identificacao
unica, garantindo que alteracoes no documento invalidem o cache.
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any

logger = logging.getLogger(__name__)


@dataclass
class OCRCacheEntry:
    """Entrada do cache de OCR."""
    
    file_name: str
    file_hash: str
    file_size: int
    num_pages: int
    total_words: int
    extracted_at: str
    extraction_time_seconds: float
    cache_file: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> dict:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: dict) -> "OCRCacheEntry":
        return cls(**data)
    
    @property
    def age_hours(self) -> float:
        """Idade do cache em horas."""
        extracted = datetime.fromisoformat(self.extracted_at)
        delta = datetime.now() - extracted
        return delta.total_seconds() / 3600


@dataclass
class CachedDocument:
    """Documento com texto em cache."""
    
    file_name: str
    file_hash: str
    pages: List[Dict[str, Any]]  # [{"number": 1, "text": "..."}, ...]
    full_text: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> dict:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: dict) -> "CachedDocument":
        return cls(**data)


class OCRCache:
    """
    Gerenciador de cache para extracoes OCR.
    
    Funcionalidades:
    - Armazena texto extraido por hash do PDF
    - Lista documentos em cache
    - Remove entradas individuais ou limpa todo o cache
    - Verifica validade do cache
    """
    
    def __init__(
        self,
        cache_dir: Optional[Path] = None,
        max_age_hours: int = 720,  # 30 dias
        enabled: bool = True
    ):
        """
        Inicializa o cache de OCR.
        
        Args:
            cache_dir: Diretorio do cache
            max_age_hours: Idade maxima do cache em horas
            enabled: Se o cache esta habilitado
        """
        self.cache_dir = cache_dir or Path("./cache/ocr")
        self.max_age_hours = max_age_hours
        self.enabled = enabled
        self._index_file = self.cache_dir / "index.json"
        self._index: Dict[str, OCRCacheEntry] = {}
        
        if self.enabled:
            self._ensure_cache_dir()
            self._load_index()
    
    def _ensure_cache_dir(self) -> None:
        """Garante que o diretorio de cache existe."""
        self.cache_dir.mkdir(parents=True, exist_ok=True)
    
    def _load_index(self) -> None:
        """Carrega indice do cache."""
        if self._index_file.exists():
            try:
                with open(self._index_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self._index = {
                        k: OCRCacheEntry.from_dict(v)
                        for k, v in data.items()
                    }
                logger.debug(f"Indice do cache carregado: {len(self._index)} entradas")
            except Exception as e:
                logger.warning(f"Erro ao carregar indice do cache: {e}")
                self._index = {}
    
    def _save_index(self) -> None:
        """Salva indice do cache."""
        try:
            with open(self._index_file, 'w', encoding='utf-8') as f:
                data = {k: v.to_dict() for k, v in self._index.items()}
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.warning(f"Erro ao salvar indice do cache: {e}")
    
    @staticmethod
    def calculate_file_hash(file_path: Path) -> str:
        """
        Calcula hash SHA-256 do arquivo.
        
        Args:
            file_path: Caminho do arquivo
        
        Returns:
            Hash em hexadecimal
        """
        sha256 = hashlib.sha256()
        with open(file_path, 'rb') as f:
            for chunk in iter(lambda: f.read(8192), b''):
                sha256.update(chunk)
        return sha256.hexdigest()
    
    def get_cache_key(self, file_path: Path) -> str:
        """Gera chave do cache baseada no hash do arquivo."""
        return self.calculate_file_hash(file_path)
    
    def has_cache(self, file_path: Path) -> bool:
        """
        Verifica se existe cache valido para o arquivo.
        
        Args:
            file_path: Caminho do PDF
        
        Returns:
            True se existe cache valido
        """
        if not self.enabled:
            return False
        
        file_hash = self.get_cache_key(file_path)
        
        if file_hash not in self._index:
            return False
        
        entry = self._index[file_hash]
        
        # Verifica idade
        if entry.age_hours > self.max_age_hours:
            logger.debug(f"Cache expirado para {file_path.name}")
            return False
        
        # Verifica se arquivo de cache existe
        cache_file = self.cache_dir / entry.cache_file
        if not cache_file.exists():
            logger.debug(f"Arquivo de cache nao encontrado: {entry.cache_file}")
            return False
        
        return True
    
    def get(self, file_path: Path) -> Optional[CachedDocument]:
        """
        Obtem documento do cache.
        
        Args:
            file_path: Caminho do PDF
        
        Returns:
            CachedDocument ou None se nao encontrado
        """
        if not self.has_cache(file_path):
            return None
        
        file_hash = self.get_cache_key(file_path)
        entry = self._index[file_hash]
        cache_file = self.cache_dir / entry.cache_file
        
        try:
            with open(cache_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                doc = CachedDocument.from_dict(data)
                logger.info(f"Cache hit: {file_path.name} ({entry.num_pages} paginas)")
                return doc
        except Exception as e:
            logger.warning(f"Erro ao ler cache: {e}")
            return None
    
    def save(
        self,
        file_path: Path,
        pages: List[Dict[str, Any]],
        extraction_time: float,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Salva documento no cache.
        
        Args:
            file_path: Caminho do PDF original
            pages: Lista de paginas [{"number": 1, "text": "..."}, ...]
            extraction_time: Tempo de extracao em segundos
            metadata: Metadados adicionais
        """
        if not self.enabled:
            return
        
        file_hash = self.get_cache_key(file_path)
        cache_filename = f"{file_hash[:16]}.json"
        cache_file = self.cache_dir / cache_filename
        
        # Calcula estatisticas
        full_text = "\n\n".join(p.get("text", "") for p in pages)
        total_words = len(full_text.split())
        
        # Cria documento
        doc = CachedDocument(
            file_name=file_path.name,
            file_hash=file_hash,
            pages=pages,
            full_text=full_text,
            metadata=metadata or {}
        )
        
        # Salva documento
        try:
            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump(doc.to_dict(), f, ensure_ascii=False)
        except Exception as e:
            logger.warning(f"Erro ao salvar cache: {e}")
            return
        
        # Atualiza indice
        entry = OCRCacheEntry(
            file_name=file_path.name,
            file_hash=file_hash,
            file_size=file_path.stat().st_size,
            num_pages=len(pages),
            total_words=total_words,
            extracted_at=datetime.now().isoformat(),
            extraction_time_seconds=extraction_time,
            cache_file=cache_filename,
            metadata=metadata or {}
        )
        
        self._index[file_hash] = entry
        self._save_index()
        
        logger.info(
            f"Cache salvo: {file_path.name} "
            f"({len(pages)} paginas, {total_words} palavras)"
        )
    
    def remove(self, file_path: Path) -> bool:
        """
        Remove entrada do cache.
        
        Args:
            file_path: Caminho do PDF
        
        Returns:
            True se removido com sucesso
        """
        file_hash = self.get_cache_key(file_path)
        
        if file_hash not in self._index:
            return False
        
        entry = self._index[file_hash]
        cache_file = self.cache_dir / entry.cache_file
        
        # Remove arquivo
        if cache_file.exists():
            cache_file.unlink()
        
        # Remove do indice
        del self._index[file_hash]
        self._save_index()
        
        logger.info(f"Cache removido: {file_path.name}")
        return True
    
    def remove_by_name(self, file_name: str) -> int:
        """
        Remove entradas do cache pelo nome do arquivo.
        
        Args:
            file_name: Nome do arquivo (pode ser parcial)
        
        Returns:
            Numero de entradas removidas
        """
        to_remove = []
        
        for file_hash, entry in self._index.items():
            if file_name.lower() in entry.file_name.lower():
                to_remove.append((file_hash, entry))
        
        for file_hash, entry in to_remove:
            cache_file = self.cache_dir / entry.cache_file
            if cache_file.exists():
                cache_file.unlink()
            del self._index[file_hash]
        
        if to_remove:
            self._save_index()
        
        return len(to_remove)
    
    def clear(self) -> int:
        """
        Limpa todo o cache.
        
        Returns:
            Numero de entradas removidas
        """
        count = len(self._index)
        
        # Remove arquivos
        for entry in self._index.values():
            cache_file = self.cache_dir / entry.cache_file
            if cache_file.exists():
                cache_file.unlink()
        
        # Limpa indice
        self._index.clear()
        self._save_index()
        
        logger.info(f"Cache limpo: {count} entradas removidas")
        return count
    
    def cleanup_expired(self) -> int:
        """
        Remove entradas expiradas do cache.
        
        Returns:
            Numero de entradas removidas
        """
        to_remove = []
        
        for file_hash, entry in self._index.items():
            if entry.age_hours > self.max_age_hours:
                to_remove.append((file_hash, entry))
        
        for file_hash, entry in to_remove:
            cache_file = self.cache_dir / entry.cache_file
            if cache_file.exists():
                cache_file.unlink()
            del self._index[file_hash]
        
        if to_remove:
            self._save_index()
            logger.info(f"Limpeza: {len(to_remove)} entradas expiradas removidas")
        
        return len(to_remove)
    
    def list_entries(self) -> List[OCRCacheEntry]:
        """
        Lista todas as entradas do cache.
        
        Returns:
            Lista de entradas ordenadas por data
        """
        entries = list(self._index.values())
        entries.sort(key=lambda e: e.extracted_at, reverse=True)
        return entries
    
    def get_entry_info(self, file_name: str) -> Optional[OCRCacheEntry]:
        """
        Obtem informacoes de uma entrada pelo nome do arquivo.
        
        Args:
            file_name: Nome do arquivo
        
        Returns:
            OCRCacheEntry ou None
        """
        for entry in self._index.values():
            if entry.file_name.lower() == file_name.lower():
                return entry
        return None
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Retorna estatisticas do cache.
        
        Returns:
            Dicionario com estatisticas
        """
        entries = list(self._index.values())
        
        if not entries:
            return {
                "enabled": self.enabled,
                "total_entries": 0,
                "total_pages": 0,
                "total_words": 0,
                "total_size_mb": 0,
                "total_time_saved_seconds": 0,
                "cache_dir": str(self.cache_dir),
            }
        
        total_pages = sum(e.num_pages for e in entries)
        total_words = sum(e.total_words for e in entries)
        total_size = sum(e.file_size for e in entries)
        total_time = sum(e.extraction_time_seconds for e in entries)
        
        # Calcula tamanho do cache em disco
        cache_size = 0
        for entry in entries:
            cache_file = self.cache_dir / entry.cache_file
            if cache_file.exists():
                cache_size += cache_file.stat().st_size
        
        return {
            "enabled": self.enabled,
            "total_entries": len(entries),
            "total_pages": total_pages,
            "total_words": total_words,
            "total_original_size_mb": round(total_size / (1024 * 1024), 2),
            "total_cache_size_mb": round(cache_size / (1024 * 1024), 2),
            "total_time_saved_seconds": round(total_time, 1),
            "max_age_hours": self.max_age_hours,
            "cache_dir": str(self.cache_dir),
        }


# Instancia global
_cache: Optional[OCRCache] = None


def get_ocr_cache() -> OCRCache:
    """Obtem instancia global do cache de OCR."""
    global _cache
    if _cache is None:
        _cache = OCRCache()
    return _cache


def init_ocr_cache(
    cache_dir: Optional[Path] = None,
    max_age_hours: int = 720,
    enabled: bool = True
) -> OCRCache:
    """
    Inicializa o cache de OCR com configuracoes especificas.
    
    Args:
        cache_dir: Diretorio do cache
        max_age_hours: Idade maxima em horas
        enabled: Se o cache esta habilitado
    
    Returns:
        Instancia do OCRCache
    """
    global _cache
    _cache = OCRCache(
        cache_dir=cache_dir,
        max_age_hours=max_age_hours,
        enabled=enabled
    )
    return _cache

