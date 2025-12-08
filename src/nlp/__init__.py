"""Módulos de processamento de linguagem natural."""

from .base_processor import BaseNLPProcessor
from .local_processor import LocalNLPProcessor
from .cloud_processor import CloudNLPProcessor
from .processor_factory import NLPProcessorFactory, get_nlp_processor

__all__ = [
    "BaseNLPProcessor",
    "LocalNLPProcessor",
    "CloudNLPProcessor",
    "NLPProcessorFactory",
    "get_nlp_processor",
]
