"""Processador NLP em nuvem usando APIs de LLM."""

from __future__ import annotations

import json
import logging
import os
import re
from typing import List, Optional, Tuple

from config.settings import Settings, get_settings
from .base_processor import BaseNLPProcessor

logger = logging.getLogger(__name__)


class CloudNLPProcessor(BaseNLPProcessor):
    """
    Processador NLP que usa APIs de LLM em nuvem.
    
    Suporta OpenAI e Anthropic.
    Otimizado para minimizar consumo de tokens.
    """
    
    def __init__(self, settings: Optional[Settings] = None):
        """
        Inicializa o processador cloud.
        
        Args:
            settings: Configurações do aplicativo.
        """
        super().__init__(settings)
        self.settings = settings or get_settings()
        self._client = None
        self._provider = self.settings.nlp.cloud.provider
        self._model = self.settings.nlp.cloud.model
        self._token_count = 0  # Contador de tokens usados
    
    def initialize(self) -> None:
        """Inicializa o cliente da API."""
        if self._initialized:
            return
        
        logger.info(f"Inicializando processador NLP cloud ({self._provider})...")
        
        api_key = self.settings.nlp.cloud.api_key
        
        if not api_key:
            raise ValueError(
                f"API key não configurada. "
                f"Defina a variável de ambiente {self.settings.nlp.cloud.api_key_env}"
            )
        
        if self._provider == "openai":
            self._init_openai(api_key)
        elif self._provider == "anthropic":
            self._init_anthropic(api_key)
        else:
            raise ValueError(f"Provedor não suportado: {self._provider}")
        
        self._initialized = True
        logger.info("Processador NLP cloud inicializado")
    
    def _init_openai(self, api_key: str) -> None:
        """Inicializa cliente OpenAI."""
        try:
            from openai import OpenAI
            self._client = OpenAI(api_key=api_key)
        except ImportError:
            raise ImportError("openai não instalado. Instale com: pip install openai")
    
    def _init_anthropic(self, api_key: str) -> None:
        """Inicializa cliente Anthropic."""
        try:
            from anthropic import Anthropic
            self._client = Anthropic(api_key=api_key)
        except ImportError:
            raise ImportError("anthropic não instalado. Instale com: pip install anthropic")
    
    def _call_llm(self, prompt: str, max_tokens: int = 500) -> str:
        """
        Faz chamada ao LLM.
        
        Args:
            prompt: Prompt para o modelo.
            max_tokens: Máximo de tokens na resposta.
        
        Returns:
            str: Resposta do modelo.
        """
        self.ensure_initialized()
        
        try:
            if self._provider == "openai":
                response = self._client.chat.completions.create(
                    model=self._model,
                    messages=[{"role": "user", "content": prompt}],
                    max_tokens=max_tokens,
                    temperature=self.settings.nlp.cloud.temperature
                )
                self._token_count += response.usage.total_tokens
                return response.choices[0].message.content
            
            elif self._provider == "anthropic":
                response = self._client.messages.create(
                    model=self._model,
                    max_tokens=max_tokens,
                    messages=[{"role": "user", "content": prompt}]
                )
                self._token_count += response.usage.input_tokens + response.usage.output_tokens
                return response.content[0].text
            
        except Exception as e:
            logger.error(f"Erro na chamada ao LLM: {e}")
            raise
    
    def calculate_similarity(self, text1: str, text2: str) -> float:
        """
        Calcula similaridade usando LLM.
        
        NOTA: Esta operação consome tokens. Use com moderação.
        
        Args:
            text1: Primeiro texto.
            text2: Segundo texto.
        
        Returns:
            float: Score de similaridade (0-1).
        """
        # Limita tamanho para economizar tokens
        t1 = text1[:300]
        t2 = text2[:300]
        
        prompt = f"""Compare a similaridade semântica entre os dois textos abaixo.
Responda APENAS com um número de 0 a 1 (ex: 0.75).

Texto 1: {t1}

Texto 2: {t2}

Score (0-1):"""
        
        try:
            response = self._call_llm(prompt, max_tokens=10)
            # Extrai número da resposta
            numbers = re.findall(r"0?\.\d+|1\.0|1|0", response)
            if numbers:
                return float(numbers[0])
        except Exception as e:
            logger.warning(f"Erro ao calcular similaridade: {e}")
        
        return 0.0
    
    def find_similar_passages(
        self,
        query: str,
        text: str,
        top_k: int = 5
    ) -> List[Tuple[str, float, int]]:
        """
        Encontra passagens similares usando LLM.
        
        Args:
            query: Texto de busca.
            text: Texto fonte.
            top_k: Número máximo de resultados.
        
        Returns:
            List[Tuple[str, float, int]]: Lista de (passagem, score, posição).
        """
        # Limita texto para economizar tokens
        text_limited = text[:4000]
        
        prompt = f"""Analise o texto abaixo e encontre trechos que correspondam à seguinte busca.

BUSCA: {query}

TEXTO:
{text_limited}

Retorne até {top_k} trechos relevantes no formato JSON:
[{{"trecho": "texto encontrado", "relevancia": 0.9}}]

Responda APENAS com o JSON, sem explicações."""
        
        try:
            response = self._call_llm(prompt, max_tokens=1000)
            
            # Parse JSON
            json_match = re.search(r'\[.*\]', response, re.DOTALL)
            if json_match:
                results = json.loads(json_match.group())
                
                passages = []
                for r in results[:top_k]:
                    trecho = r.get("trecho", "")
                    relevancia = float(r.get("relevancia", 0))
                    
                    # Encontra posição no texto
                    pos = text.find(trecho)
                    if pos == -1:
                        pos = 0
                    
                    passages.append((trecho, relevancia, pos))
                
                return passages
                
        except Exception as e:
            logger.warning(f"Erro ao buscar passagens: {e}")
        
        return []
    
    def extract_key_phrases(self, text: str) -> List[str]:
        """
        Extrai frases-chave usando LLM.
        
        Args:
            text: Texto para análise.
        
        Returns:
            List[str]: Lista de frases-chave.
        """
        text_limited = text[:3000]
        
        prompt = f"""Extraia as principais frases-chave e termos importantes do texto abaixo.
Foque em termos jurídicos e informações relevantes para contratos de locação.

TEXTO:
{text_limited}

Retorne uma lista JSON de frases-chave (máximo 20):
["frase1", "frase2", ...]

Responda APENAS com o JSON."""
        
        try:
            response = self._call_llm(prompt, max_tokens=500)
            
            json_match = re.search(r'\[.*\]', response, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())
                
        except Exception as e:
            logger.warning(f"Erro ao extrair frases-chave: {e}")
        
        return []
    
    def analyze_sentence_coherence(self, sentences: List[str]) -> float:
        """
        Analisa coerência usando LLM.
        
        Args:
            sentences: Lista de sentenças.
        
        Returns:
            float: Score de coerência (0-1).
        """
        if len(sentences) < 2:
            return 1.0
        
        # Limita número de sentenças
        sample = sentences[:10]
        text = "\n".join(f"{i+1}. {s}" for i, s in enumerate(sample))
        
        prompt = f"""Analise a coerência do texto abaixo (se as sentenças fazem sentido juntas).
Considere: ordem lógica, conexão entre ideias, linguagem consistente.

SENTENÇAS:
{text}

Responda APENAS com um número de 0 a 1 indicando o nível de coerência:"""
        
        try:
            response = self._call_llm(prompt, max_tokens=10)
            numbers = re.findall(r"0?\.\d+|1\.0|1|0", response)
            if numbers:
                return float(numbers[0])
        except Exception as e:
            logger.warning(f"Erro ao analisar coerência: {e}")
        
        return 0.5
    
    def identify_legal_entities(self, text: str) -> List[Tuple[str, str]]:
        """
        Identifica entidades jurídicas usando LLM.
        
        Args:
            text: Texto para análise.
        
        Returns:
            List[Tuple[str, str]]: Lista de (entidade, tipo).
        """
        text_limited = text[:3000]
        
        prompt = f"""Identifique entidades jurídicas no texto de contrato abaixo.
Procure por: nomes de partes (locador, locatário, fiador), valores monetários,
datas, endereços, prazos, cláusulas importantes.

TEXTO:
{text_limited}

Retorne JSON no formato:
[{{"entidade": "texto", "tipo": "LOCADOR|LOCATARIO|VALOR|DATA|ENDERECO|PRAZO|CLAUSULA"}}]

Responda APENAS com o JSON."""
        
        try:
            response = self._call_llm(prompt, max_tokens=1000)
            
            json_match = re.search(r'\[.*\]', response, re.DOTALL)
            if json_match:
                results = json.loads(json_match.group())
                return [(r["entidade"], r["tipo"]) for r in results]
                
        except Exception as e:
            logger.warning(f"Erro ao identificar entidades: {e}")
        
        return []
    
    def analyze_contract_content(
        self,
        text: str,
        instructions: List[str]
    ) -> List[dict]:
        """
        Analisa conteúdo do contrato baseado em instruções.
        
        Este método é otimizado para processar múltiplas instruções
        em uma única chamada, economizando tokens.
        
        Args:
            text: Texto do contrato.
            instructions: Lista de instruções de busca.
        
        Returns:
            List[dict]: Resultados para cada instrução.
        """
        text_limited = text[:5000]
        instructions_text = "\n".join(f"- {inst}" for inst in instructions)
        
        prompt = f"""Analise o contrato de locação abaixo e encontre informações para cada instrução.

CONTRATO:
{text_limited}

INSTRUÇÕES (encontre informações sobre):
{instructions_text}

Para cada instrução, retorne JSON:
[
  {{
    "instrucao": "texto da instrução",
    "encontrado": true/false,
    "trechos": ["trecho1", "trecho2"],
    "resumo": "breve resumo do encontrado"
  }}
]

Responda APENAS com o JSON."""
        
        try:
            response = self._call_llm(prompt, max_tokens=2000)
            
            json_match = re.search(r'\[.*\]', response, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())
                
        except Exception as e:
            logger.error(f"Erro ao analisar contrato: {e}")
        
        return []
    
    @property
    def tokens_used(self) -> int:
        """Retorna total de tokens usados."""
        return self._token_count
    
    def reset_token_count(self) -> None:
        """Reseta contador de tokens."""
        self._token_count = 0
