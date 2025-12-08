"""Processador NLP local usando spaCy e sentence-transformers."""

from __future__ import annotations

import logging
import re
from typing import List, Optional, Tuple

import numpy as np

from ..config.settings import Settings, get_settings
from .base_processor import BaseNLPProcessor

logger = logging.getLogger(__name__)


class LocalNLPProcessor(BaseNLPProcessor):
    """
    Processador NLP que roda localmente sem necessidade de API.
    
    Usa spaCy para análise linguística e sentence-transformers
    para embeddings semânticos.
    """
    
    # Termos jurídicos específicos para contratos de locação
    LEGAL_ENTITY_PATTERNS = {
        "LOCADOR": r"\blocador[a]?\b",
        "LOCATARIO": r"\blocat[áa]ri[oa]\b",
        "FIADOR": r"\bfiador[a]?\b",
        "IMOVEL": r"\bim[óo]vel\b",
        "ALUGUEL": r"\balugu[ée]l\b",
        "CAUCAO": r"\bcau[çc][ãa]o\b",
        "MULTA": r"\bmulta\b",
        "PRAZO": r"\bprazo\b",
        "CLAUSULA": r"\bcl[áa]usula\b",
        "RESCISAO": r"\brescis[ãa]o\b",
        "REAJUSTE": r"\breajuste\b",
        "GARANTIA": r"\bgarantia\b",
        "VISTORIA": r"\bvistoria\b",
        "BENFEITORIAS": r"\bbenfeitorias?\b",
    }
    
    def __init__(self, settings: Optional[Settings] = None):
        """
        Inicializa o processador local.
        
        Args:
            settings: Configurações do aplicativo.
        """
        super().__init__(settings)
        self.settings = settings or get_settings()
        self._nlp = None
        self._sentence_model = None
        self._embeddings_cache = {}
    
    def initialize(self) -> None:
        """Inicializa os modelos NLP."""
        if self._initialized:
            return
        
        logger.info("Inicializando processador NLP local...")
        
        # Carrega spaCy
        self._load_spacy()
        
        # Carrega sentence-transformers
        self._load_sentence_transformer()
        
        self._initialized = True
        logger.info("Processador NLP local inicializado")
    
    def _load_spacy(self) -> None:
        """Carrega o modelo spaCy."""
        try:
            import spacy
            
            model_name = self.settings.nlp.local.spacy_model
            
            try:
                self._nlp = spacy.load(model_name)
                logger.info(f"Modelo spaCy carregado: {model_name}")
            except OSError:
                # Tenta baixar o modelo
                logger.warning(f"Modelo {model_name} não encontrado. Baixando...")
                spacy.cli.download(model_name)
                self._nlp = spacy.load(model_name)
                
        except ImportError:
            logger.error("spaCy não instalado. Instale com: pip install spacy")
            raise
        except Exception as e:
            logger.error(f"Erro ao carregar spaCy: {e}")
            # Usa modelo básico se disponível
            try:
                import spacy
                self._nlp = spacy.blank("pt")
                logger.warning("Usando modelo spaCy básico")
            except:
                raise
    
    def _load_sentence_transformer(self) -> None:
        """Carrega o modelo sentence-transformers."""
        try:
            from sentence_transformers import SentenceTransformer
            
            model_name = self.settings.nlp.local.sentence_transformer
            
            logger.info(f"Carregando sentence-transformer: {model_name}")
            self._sentence_model = SentenceTransformer(model_name)
            logger.info("Sentence-transformer carregado")
            
        except ImportError:
            logger.warning(
                "sentence-transformers não instalado. "
                "Similaridade semântica limitada."
            )
            self._sentence_model = None
        except Exception as e:
            logger.warning(f"Erro ao carregar sentence-transformer: {e}")
            self._sentence_model = None
    
    def calculate_similarity(self, text1: str, text2: str) -> float:
        """
        Calcula similaridade semântica entre dois textos.
        
        Args:
            text1: Primeiro texto.
            text2: Segundo texto.
        
        Returns:
            float: Score de similaridade (0-1).
        """
        self.ensure_initialized()
        
        if self._sentence_model is None:
            # Fallback para similaridade baseada em palavras
            return self._word_based_similarity(text1, text2)
        
        try:
            # Obtém embeddings
            emb1 = self._get_embedding(text1)
            emb2 = self._get_embedding(text2)
            
            # Calcula similaridade de cosseno
            similarity = np.dot(emb1, emb2) / (
                np.linalg.norm(emb1) * np.linalg.norm(emb2)
            )
            
            return float(max(0, min(1, similarity)))
            
        except Exception as e:
            logger.warning(f"Erro ao calcular similaridade: {e}")
            return self._word_based_similarity(text1, text2)
    
    def _get_embedding(self, text: str) -> np.ndarray:
        """
        Obtém embedding do texto com cache.
        
        Args:
            text: Texto para embedding.
        
        Returns:
            np.ndarray: Vetor de embedding.
        """
        # Limita tamanho do cache
        if len(self._embeddings_cache) > 1000:
            self._embeddings_cache.clear()
        
        text_hash = hash(text[:500])  # Hash dos primeiros 500 chars
        
        if text_hash not in self._embeddings_cache:
            self._embeddings_cache[text_hash] = self._sentence_model.encode(text)
        
        return self._embeddings_cache[text_hash]
    
    def _word_based_similarity(self, text1: str, text2: str) -> float:
        """
        Calcula similaridade baseada em palavras (fallback).
        
        Args:
            text1: Primeiro texto.
            text2: Segundo texto.
        
        Returns:
            float: Score de similaridade (0-1).
        """
        words1 = set(text1.lower().split())
        words2 = set(text2.lower().split())
        
        if not words1 or not words2:
            return 0.0
        
        intersection = len(words1.intersection(words2))
        union = len(words1.union(words2))
        
        return intersection / union if union > 0 else 0.0
    
    def find_similar_passages(
        self,
        query: str,
        text: str,
        top_k: int = 5
    ) -> List[Tuple[str, float, int]]:
        """
        Encontra passagens similares à query no texto.
        
        Args:
            query: Texto de busca.
            text: Texto fonte.
            top_k: Número máximo de resultados.
        
        Returns:
            List[Tuple[str, float, int]]: Lista de (passagem, score, posição).
        """
        self.ensure_initialized()
        
        # Divide texto em sentenças/parágrafos
        passages = self._split_into_passages(text)
        
        if not passages:
            return []
        
        results = []
        
        for passage, start_pos in passages:
            score = self.calculate_similarity(query, passage)
            results.append((passage, score, start_pos))
        
        # Ordena por score e retorna top_k
        results.sort(key=lambda x: x[1], reverse=True)
        
        threshold = self.settings.nlp.local.similarity_threshold
        filtered = [r for r in results if r[1] >= threshold]
        
        return filtered[:top_k]
    
    def _split_into_passages(
        self,
        text: str,
        max_length: int = 500
    ) -> List[Tuple[str, int]]:
        """
        Divide texto em passagens.
        
        Args:
            text: Texto para dividir.
            max_length: Tamanho máximo de cada passagem.
        
        Returns:
            List[Tuple[str, int]]: Lista de (passagem, posição inicial).
        """
        passages = []
        
        # Divide por parágrafos primeiro
        paragraphs = text.split("\n\n")
        current_pos = 0
        
        for para in paragraphs:
            para = para.strip()
            if not para:
                current_pos += 2
                continue
            
            # Se parágrafo é muito longo, divide em sentenças
            if len(para) > max_length:
                sentences = re.split(r'(?<=[.!?])\s+', para)
                sent_pos = current_pos
                
                for sent in sentences:
                    sent = sent.strip()
                    if sent:
                        passages.append((sent, sent_pos))
                        sent_pos += len(sent) + 1
            else:
                passages.append((para, current_pos))
            
            current_pos += len(para) + 2
        
        return passages
    
    def extract_key_phrases(self, text: str) -> List[str]:
        """
        Extrai frases-chave do texto usando spaCy.
        
        Args:
            text: Texto para análise.
        
        Returns:
            List[str]: Lista de frases-chave.
        """
        self.ensure_initialized()
        
        if self._nlp is None:
            return []
        
        key_phrases = []
        
        try:
            doc = self._nlp(text[:10000])  # Limita tamanho
            
            # Extrai noun chunks
            for chunk in doc.noun_chunks:
                if len(chunk.text) > 3:
                    key_phrases.append(chunk.text.lower())
            
            # Extrai entidades nomeadas
            for ent in doc.ents:
                if ent.label_ in ["ORG", "PER", "LOC", "MISC"]:
                    key_phrases.append(ent.text)
            
        except Exception as e:
            logger.warning(f"Erro ao extrair frases-chave: {e}")
        
        # Remove duplicatas mantendo ordem
        seen = set()
        unique = []
        for phrase in key_phrases:
            if phrase not in seen:
                seen.add(phrase)
                unique.append(phrase)
        
        return unique[:50]  # Limita resultado
    
    def analyze_sentence_coherence(self, sentences: List[str]) -> float:
        """
        Analisa coerência entre sentenças consecutivas.
        
        Args:
            sentences: Lista de sentenças.
        
        Returns:
            float: Score de coerência (0-1).
        """
        self.ensure_initialized()
        
        if len(sentences) < 2:
            return 1.0
        
        similarities = []
        
        for i in range(len(sentences) - 1):
            sim = self.calculate_similarity(sentences[i], sentences[i + 1])
            similarities.append(sim)
        
        return sum(similarities) / len(similarities) if similarities else 0.0
    
    def identify_legal_entities(self, text: str) -> List[Tuple[str, str]]:
        """
        Identifica entidades jurídicas no texto.
        
        Args:
            text: Texto para análise.
        
        Returns:
            List[Tuple[str, str]]: Lista de (texto encontrado, tipo).
        """
        self.ensure_initialized()
        
        entities = []
        text_lower = text.lower()
        
        for entity_type, pattern in self.LEGAL_ENTITY_PATTERNS.items():
            matches = re.finditer(pattern, text_lower, re.IGNORECASE)
            for match in matches:
                # Obtém texto original (com capitalização correta)
                start, end = match.span()
                original_text = text[start:end]
                entities.append((original_text, entity_type))
        
        # Remove duplicatas
        seen = set()
        unique = []
        for text_found, etype in entities:
            key = (text_found.lower(), etype)
            if key not in seen:
                seen.add(key)
                unique.append((text_found, etype))
        
        return unique
    
    def get_sentence_embeddings(self, sentences: List[str]) -> np.ndarray:
        """
        Obtém embeddings para lista de sentenças.
        
        Args:
            sentences: Lista de sentenças.
        
        Returns:
            np.ndarray: Matriz de embeddings.
        """
        self.ensure_initialized()
        
        if self._sentence_model is None:
            return np.zeros((len(sentences), 768))
        
        return self._sentence_model.encode(sentences)
