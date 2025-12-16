"""
Cache de Regras DKR.

Armazena regras compiladas para evitar re-parsing
a cada pergunta. Invalida automaticamente quando
o arquivo .rules é modificado.
"""

from __future__ import annotations

import hashlib
import json
import logging
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional, Any

from .models import CompiledRules
from .parser import DKRParser

logger = logging.getLogger(__name__)


@dataclass
class CachedRules:
    """Regras em cache."""
    
    rules: CompiledRules
    file_path: str
    file_hash: str
    cached_at: datetime
    access_count: int = 0
    
    def is_stale(self, current_hash: str) -> bool:
        """Verifica se o cache está desatualizado."""
        return self.file_hash != current_hash


class DKRCache:
    """
    Cache de regras DKR compiladas.
    
    Mantém regras em memória para evitar re-parsing.
    Invalida automaticamente quando o arquivo fonte muda.
    
    Uso:
        cache = DKRCache()
        rules = cache.get("domain_rules/licencas_software.rules")
        
        if rules:
            # Usa regras do cache
            ...
        else:
            # Faz parse e armazena
            rules = parser.parse_file(path)
            cache.set(path, rules)
    """
    
    def __init__(
        self,
        max_entries: int = 50,
        persist: bool = False,
        cache_dir: Optional[Path] = None
    ):
        """
        Inicializa o cache.
        
        Args:
            max_entries: Número máximo de entradas
            persist: Se deve persistir em disco
            cache_dir: Diretório para persistência
        """
        self.max_entries = max_entries
        self.persist = persist
        self.cache_dir = cache_dir or Path("./cache/dkr")
        
        self._cache: Dict[str, CachedRules] = {}
        self._parser = DKRParser()
        
        if persist:
            self._load_metadata()
    
    def _compute_file_hash(self, file_path: Path) -> str:
        """Calcula hash do arquivo."""
        if not file_path.exists():
            return ""
        
        content = file_path.read_bytes()
        return hashlib.md5(content).hexdigest()[:12]
    
    def get(self, file_path: Path | str) -> Optional[CompiledRules]:
        """
        Obtém regras do cache.
        
        Args:
            file_path: Caminho do arquivo .rules
        
        Returns:
            CompiledRules ou None se não em cache ou desatualizado
        """
        file_path = Path(file_path)
        key = str(file_path.absolute())
        
        if key not in self._cache:
            return None
        
        cached = self._cache[key]
        current_hash = self._compute_file_hash(file_path)
        
        # Verifica se arquivo mudou
        if cached.is_stale(current_hash):
            logger.debug(f"Cache DKR stale: {file_path.name}")
            del self._cache[key]
            return None
        
        # Atualiza contador de acessos
        cached.access_count += 1
        
        logger.debug(f"Cache DKR hit: {file_path.name}")
        return cached.rules
    
    def get_or_load(self, file_path: Path | str) -> Optional[CompiledRules]:
        """
        Obtém do cache ou carrega do arquivo.
        
        Args:
            file_path: Caminho do arquivo .rules
        
        Returns:
            CompiledRules ou None se arquivo não existe
        """
        file_path = Path(file_path)
        
        # Tenta cache primeiro
        rules = self.get(file_path)
        if rules:
            return rules
        
        # Arquivo não existe
        if not file_path.exists():
            return None
        
        # Faz parse e armazena
        try:
            rules = self._parser.parse_file(file_path)
            self.set(file_path, rules)
            return rules
        except Exception as e:
            logger.error(f"Erro ao carregar DKR: {e}")
            return None
    
    def set(
        self,
        file_path: Path | str,
        rules: CompiledRules
    ) -> None:
        """
        Armazena regras no cache.
        
        Args:
            file_path: Caminho do arquivo .rules
            rules: Regras compiladas
        """
        file_path = Path(file_path)
        key = str(file_path.absolute())
        
        # Limpa cache se necessário
        if len(self._cache) >= self.max_entries:
            self._evict_lru()
        
        self._cache[key] = CachedRules(
            rules=rules,
            file_path=key,
            file_hash=self._compute_file_hash(file_path),
            cached_at=datetime.now(),
        )
        
        logger.debug(f"Cache DKR set: {file_path.name}")
        
        if self.persist:
            self._save_metadata()
    
    def invalidate(self, file_path: Optional[Path | str] = None) -> int:
        """
        Invalida entradas do cache.
        
        Args:
            file_path: Arquivo específico ou None para todos
        
        Returns:
            Número de entradas removidas
        """
        if file_path:
            file_path = Path(file_path)
            key = str(file_path.absolute())
            if key in self._cache:
                del self._cache[key]
                return 1
            return 0
        else:
            count = len(self._cache)
            self._cache.clear()
            return count
    
    def _evict_lru(self) -> None:
        """Remove entrada menos recentemente usada."""
        if not self._cache:
            return
        
        # Encontra entrada com menor contador de acessos
        lru_key = min(
            self._cache.keys(),
            key=lambda k: self._cache[k].access_count
        )
        
        del self._cache[lru_key]
        logger.debug(f"Cache DKR evicted: {lru_key}")
    
    def get_stats(self) -> Dict[str, Any]:
        """Retorna estatísticas do cache."""
        total_accesses = sum(c.access_count for c in self._cache.values())
        
        return {
            "entries": len(self._cache),
            "max_entries": self.max_entries,
            "total_accesses": total_accesses,
            "files": [
                {
                    "path": Path(c.file_path).name,
                    "domain": c.rules.domain,
                    "facts": sum(len(f) for f in c.rules.facts.values()),
                    "rules": len(c.rules.validation_rules),
                    "accesses": c.access_count,
                }
                for c in self._cache.values()
            ]
        }
    
    def _save_metadata(self) -> None:
        """Salva metadados em disco (não as regras, apenas referências)."""
        if not self.persist:
            return
        
        try:
            self.cache_dir.mkdir(parents=True, exist_ok=True)
            meta_file = self.cache_dir / "dkr_cache_meta.json"
            
            data = {
                "entries": [
                    {
                        "file_path": c.file_path,
                        "file_hash": c.file_hash,
                        "cached_at": c.cached_at.isoformat(),
                        "access_count": c.access_count,
                    }
                    for c in self._cache.values()
                ]
            }
            
            with open(meta_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
                
        except Exception as e:
            logger.warning(f"Erro ao salvar metadata DKR: {e}")
    
    def _load_metadata(self) -> None:
        """Carrega metadados do disco."""
        meta_file = self.cache_dir / "dkr_cache_meta.json"
        
        if not meta_file.exists():
            return
        
        # Nota: apenas carrega metadados
        # As regras serão carregadas sob demanda
        logger.debug("Metadata DKR encontrado (regras serão carregadas sob demanda)")


# Singleton global
_dkr_cache: Optional[DKRCache] = None


def get_dkr_cache() -> DKRCache:
    """Obtém instância singleton do cache DKR."""
    global _dkr_cache
    if _dkr_cache is None:
        _dkr_cache = DKRCache()
    return _dkr_cache

