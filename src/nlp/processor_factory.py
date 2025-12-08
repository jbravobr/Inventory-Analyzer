"""Factory para criação de processadores NLP."""

from __future__ import annotations

import logging
from typing import Optional

from config.settings import Settings, get_settings
from .base_processor import BaseNLPProcessor
from .local_processor import LocalNLPProcessor
from .cloud_processor import CloudNLPProcessor

logger = logging.getLogger(__name__)


class NLPProcessorFactory:
    """
    Factory para criar processadores NLP baseado na configuração.
    
    Implementa o padrão Factory para permitir fácil troca entre
    processadores local e cloud.
    """
    
    _processors = {
        "local": LocalNLPProcessor,
        "cloud": CloudNLPProcessor,
    }
    
    @classmethod
    def create(
        cls,
        mode: Optional[str] = None,
        settings: Optional[Settings] = None
    ) -> BaseNLPProcessor:
        """
        Cria um processador NLP baseado no modo especificado.
        
        Args:
            mode: Modo do processador ("local" ou "cloud").
                  Se não especificado, usa configuração.
            settings: Configurações do aplicativo.
        
        Returns:
            BaseNLPProcessor: Processador criado.
        
        Raises:
            ValueError: Se o modo não for suportado.
        """
        settings = settings or get_settings()
        
        if mode is None:
            mode = settings.nlp.mode
        
        if mode not in cls._processors:
            raise ValueError(
                f"Modo '{mode}' não suportado. "
                f"Use: {list(cls._processors.keys())}"
            )
        
        processor_class = cls._processors[mode]
        processor = processor_class(settings)
        
        logger.info(f"Processador NLP criado: {mode}")
        
        return processor
    
    @classmethod
    def register(cls, name: str, processor_class: type) -> None:
        """
        Registra um novo tipo de processador.
        
        Args:
            name: Nome do processador.
            processor_class: Classe do processador.
        """
        if not issubclass(processor_class, BaseNLPProcessor):
            raise TypeError(
                f"Processador deve herdar de BaseNLPProcessor"
            )
        
        cls._processors[name] = processor_class
        logger.info(f"Processador registrado: {name}")
    
    @classmethod
    def available_processors(cls) -> list:
        """Retorna lista de processadores disponíveis."""
        return list(cls._processors.keys())


# Singleton para processador global
_processor: Optional[BaseNLPProcessor] = None


def get_nlp_processor(
    mode: Optional[str] = None,
    force_new: bool = False
) -> BaseNLPProcessor:
    """
    Obtém processador NLP global.
    
    Args:
        mode: Modo do processador. Se não especificado, usa configuração.
        force_new: Se True, cria novo processador mesmo se já existir.
    
    Returns:
        BaseNLPProcessor: Processador NLP.
    """
    global _processor
    
    if _processor is None or force_new:
        _processor = NLPProcessorFactory.create(mode)
    
    return _processor


def reset_processor() -> None:
    """Reseta o processador global (útil para testes)."""
    global _processor
    _processor = None
