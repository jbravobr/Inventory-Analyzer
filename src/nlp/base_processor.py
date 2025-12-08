"""Classe base abstrata para processadores NLP."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import List, Optional, Tuple

from config.settings import Settings


class BaseNLPProcessor(ABC):
    """
    Classe base abstrata para processadores de linguagem natural.
    
    Define a interface comum para processadores locais e em nuvem.
    """
    
    def __init__(self, settings: Optional[Settings] = None):
        """
        Inicializa o processador.
        
        Args:
            settings: Configurações do aplicativo.
        """
        self.settings = settings
        self._initialized = False
    
    @abstractmethod
    def initialize(self) -> None:
        """
        Inicializa os recursos do processador.
        
        Deve ser chamado antes de usar o processador.
        """
        pass
    
    @abstractmethod
    def calculate_similarity(self, text1: str, text2: str) -> float:
        """
        Calcula a similaridade semântica entre dois textos.
        
        Args:
            text1: Primeiro texto.
            text2: Segundo texto.
        
        Returns:
            float: Score de similaridade (0-1).
        """
        pass
    
    @abstractmethod
    def find_similar_passages(
        self,
        query: str,
        text: str,
        top_k: int = 5
    ) -> List[Tuple[str, float, int]]:
        """
        Encontra passagens similares a uma query no texto.
        
        Args:
            query: Texto de busca.
            text: Texto fonte para busca.
            top_k: Número máximo de resultados.
        
        Returns:
            List[Tuple[str, float, int]]: Lista de (passagem, score, posição).
        """
        pass
    
    @abstractmethod
    def extract_key_phrases(self, text: str) -> List[str]:
        """
        Extrai frases-chave do texto.
        
        Args:
            text: Texto para análise.
        
        Returns:
            List[str]: Lista de frases-chave.
        """
        pass
    
    @abstractmethod
    def analyze_sentence_coherence(self, sentences: List[str]) -> float:
        """
        Analisa a coerência entre sentenças.
        
        Args:
            sentences: Lista de sentenças.
        
        Returns:
            float: Score de coerência (0-1).
        """
        pass
    
    @abstractmethod
    def identify_legal_entities(self, text: str) -> List[Tuple[str, str]]:
        """
        Identifica entidades jurídicas no texto.
        
        Args:
            text: Texto para análise.
        
        Returns:
            List[Tuple[str, str]]: Lista de (entidade, tipo).
        """
        pass
    
    @property
    def is_initialized(self) -> bool:
        """Verifica se o processador está inicializado."""
        return self._initialized
    
    def ensure_initialized(self) -> None:
        """Garante que o processador está inicializado."""
        if not self._initialized:
            self.initialize()
