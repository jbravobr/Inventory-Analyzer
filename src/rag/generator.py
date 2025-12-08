"""
Módulo de geração de respostas usando LLM.

Suporta geração local (modelos pequenos) e via API (OpenAI, Anthropic).
"""

from __future__ import annotations

import logging
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any

from config.settings import Settings, get_settings
from .retriever import RetrievalResult

logger = logging.getLogger(__name__)


@dataclass
class GeneratedResponse:
    """Resposta gerada pelo LLM."""
    
    answer: str
    sources: List[Dict[str, Any]]
    confidence: float
    tokens_used: int = 0
    model_name: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def has_sources(self) -> bool:
        return len(self.sources) > 0
    
    def to_dict(self) -> dict:
        return {
            "answer": self.answer,
            "confidence": self.confidence,
            "sources": self.sources,
            "tokens_used": self.tokens_used,
            "model": self.model_name,
        }


class ResponseGenerator(ABC):
    """Classe base para geradores de resposta."""
    
    def __init__(self, settings: Optional[Settings] = None):
        self.settings = settings or get_settings()
        self._initialized = False
        self._total_tokens = 0
    
    @abstractmethod
    def initialize(self) -> None:
        """Inicializa o gerador."""
        pass
    
    @abstractmethod
    def generate(
        self,
        query: str,
        context: str,
        system_prompt: Optional[str] = None
    ) -> GeneratedResponse:
        """
        Gera resposta baseada no contexto.
        
        Args:
            query: Pergunta/instrução do usuário.
            context: Contexto relevante recuperado.
            system_prompt: Prompt de sistema customizado.
        
        Returns:
            GeneratedResponse: Resposta gerada.
        """
        pass
    
    def generate_from_retrieval(
        self,
        query: str,
        retrieval_result: RetrievalResult,
        system_prompt: Optional[str] = None
    ) -> GeneratedResponse:
        """
        Gera resposta a partir de resultado de retrieval.
        
        Args:
            query: Pergunta original.
            retrieval_result: Resultado do retriever.
            system_prompt: Prompt de sistema.
        
        Returns:
            GeneratedResponse: Resposta com fontes.
        """
        context = retrieval_result.context
        
        response = self.generate(query, context, system_prompt)
        
        # Adiciona informações de fonte
        response.sources = [
            {
                "page": chunk.page_number,
                "text_preview": chunk.text[:150] + "...",
                "score": score,
            }
            for chunk, score in zip(
                retrieval_result.chunks,
                retrieval_result.scores
            )
        ]
        
        return response
    
    def ensure_initialized(self) -> None:
        if not self._initialized:
            self.initialize()
    
    @property
    def total_tokens_used(self) -> int:
        return self._total_tokens
    
    def get_legal_system_prompt(self) -> str:
        """Retorna prompt de sistema para análise de contratos."""
        return """Você é um assistente especializado em análise de contratos de locação residencial no Brasil.

Sua tarefa é analisar o contexto fornecido e responder às perguntas de forma precisa e objetiva.

Diretrizes:
1. Baseie suas respostas APENAS no contexto fornecido
2. Se a informação não estiver no contexto, diga claramente que não foi encontrada
3. Cite as cláusulas ou trechos específicos quando relevante
4. Use linguagem clara e acessível
5. Destaque valores monetários, datas e prazos importantes
6. Identifique partes envolvidas (locador, locatário, fiador) quando mencionadas

Formato da resposta:
- Resposta direta e objetiva
- Citação do trecho relevante quando aplicável
- Indicação da página onde a informação foi encontrada"""


class LocalGenerator(ResponseGenerator):
    """
    Gerador usando modelos locais (sem API externa).
    
    Usa modelos menores que podem rodar localmente.
    Não consome tokens de API.
    """
    
    def __init__(
        self,
        settings: Optional[Settings] = None,
        model_name: Optional[str] = None
    ):
        super().__init__(settings)
        self._model = None
        self._tokenizer = None
        # Usa modelo local do settings se disponível
        default_model = "pierreguillou/gpt2-small-portuguese"
        if settings and hasattr(settings, 'rag') and settings.rag.generation.local_model:
            default_model = settings.rag.generation.local_model
        self._model_name = model_name or default_model
    
    def initialize(self) -> None:
        """Inicializa modelo local."""
        if self._initialized:
            return
        
        logger.info(f"Carregando modelo local: {self._model_name}")
        
        try:
            from transformers import AutoModelForCausalLM, AutoTokenizer
            
            # Usa local_files_only para evitar downloads
            self._tokenizer = AutoTokenizer.from_pretrained(
                self._model_name, 
                local_files_only=True
            )
            self._model = AutoModelForCausalLM.from_pretrained(
                self._model_name,
                local_files_only=True
            )
            
            # Configura padding token
            if self._tokenizer.pad_token is None:
                self._tokenizer.pad_token = self._tokenizer.eos_token
            
            self._initialized = True
            logger.info("Modelo local carregado")
            
        except ImportError:
            raise ImportError(
                "transformers não instalado. "
                "Instale com: pip install transformers torch"
            )
    
    def generate(
        self,
        query: str,
        context: str,
        system_prompt: Optional[str] = None
    ) -> GeneratedResponse:
        """Gera resposta usando modelo local."""
        self.ensure_initialized()
        
        # Limita contexto para não exceder limite do modelo GPT-2 (1024 tokens)
        # Reserva ~200 tokens para query + prompt, ~100 para resposta
        max_context_chars = 600  # ~150-200 tokens
        if len(context) > max_context_chars:
            context = context[:max_context_chars] + "..."
        
        # Monta prompt
        prompt = self._build_prompt(query, context, system_prompt)
        
        # Tokeniza com truncação segura para GPT-2
        inputs = self._tokenizer(
            prompt,
            return_tensors="pt",
            truncation=True,
            max_length=800  # Deixa margem para geração
        )
        
        # Gera
        outputs = self._model.generate(
            **inputs,
            max_new_tokens=150,  # Limita tokens gerados
            temperature=0.7,
            do_sample=True,
            pad_token_id=self._tokenizer.pad_token_id
        )
        
        # Decodifica
        response_text = self._tokenizer.decode(
            outputs[0],
            skip_special_tokens=True
        )
        
        # Extrai apenas a resposta (remove prompt)
        answer = response_text[len(prompt):].strip()
        
        return GeneratedResponse(
            answer=answer,
            sources=[],
            confidence=0.7,
            model_name=self._model_name
        )
    
    def _build_prompt(
        self,
        query: str,
        context: str,
        system_prompt: Optional[str]
    ) -> str:
        """Constrói prompt para o modelo."""
        if system_prompt:
            return f"""{system_prompt}

Contexto:
{context}

Pergunta: {query}

Resposta:"""
        else:
            return f"""Com base no seguinte contexto, responda à pergunta.

Contexto:
{context}

Pergunta: {query}

Resposta:"""


class CloudGenerator(ResponseGenerator):
    """
    Gerador usando APIs de LLM em nuvem.
    
    Suporta OpenAI e Anthropic.
    """
    
    def __init__(
        self,
        settings: Optional[Settings] = None,
        provider: Optional[str] = None
    ):
        super().__init__(settings)
        self._client = None
        self._provider = provider or self.settings.nlp.cloud.provider
        self._model = self.settings.nlp.cloud.model
    
    def initialize(self) -> None:
        """Inicializa cliente da API."""
        if self._initialized:
            return
        
        if self._provider == "openai":
            self._init_openai()
        elif self._provider == "anthropic":
            self._init_anthropic()
        else:
            raise ValueError(f"Provedor não suportado: {self._provider}")
        
        self._initialized = True
    
    def _init_openai(self) -> None:
        """Inicializa OpenAI."""
        try:
            from openai import OpenAI
            
            api_key = self.settings.nlp.cloud.api_key
            if not api_key:
                raise ValueError("API key não configurada")
            
            self._client = OpenAI(api_key=api_key)
            logger.info("Cliente OpenAI inicializado")
            
        except ImportError:
            raise ImportError("openai não instalado")
    
    def _init_anthropic(self) -> None:
        """Inicializa Anthropic."""
        try:
            from anthropic import Anthropic
            
            api_key = self.settings.nlp.cloud.api_key
            if not api_key:
                raise ValueError("API key não configurada")
            
            self._client = Anthropic(api_key=api_key)
            logger.info("Cliente Anthropic inicializado")
            
        except ImportError:
            raise ImportError("anthropic não instalado")
    
    def generate(
        self,
        query: str,
        context: str,
        system_prompt: Optional[str] = None
    ) -> GeneratedResponse:
        """Gera resposta via API."""
        self.ensure_initialized()
        
        system = system_prompt or self.get_legal_system_prompt()
        
        user_message = f"""Contexto do contrato:
---
{context}
---

Pergunta/Instrução: {query}

Por favor, responda baseado APENAS no contexto fornecido acima."""
        
        if self._provider == "openai":
            return self._generate_openai(system, user_message)
        elif self._provider == "anthropic":
            return self._generate_anthropic(system, user_message)
    
    def _generate_openai(
        self,
        system: str,
        user_message: str
    ) -> GeneratedResponse:
        """Gera com OpenAI."""
        response = self._client.chat.completions.create(
            model=self._model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user_message}
            ],
            temperature=self.settings.nlp.cloud.temperature,
            max_tokens=self.settings.nlp.cloud.max_tokens
        )
        
        self._total_tokens += response.usage.total_tokens
        
        return GeneratedResponse(
            answer=response.choices[0].message.content,
            sources=[],
            confidence=0.9,
            tokens_used=response.usage.total_tokens,
            model_name=self._model
        )
    
    def _generate_anthropic(
        self,
        system: str,
        user_message: str
    ) -> GeneratedResponse:
        """Gera com Anthropic."""
        response = self._client.messages.create(
            model=self._model,
            system=system,
            messages=[{"role": "user", "content": user_message}],
            max_tokens=self.settings.nlp.cloud.max_tokens
        )
        
        tokens_used = response.usage.input_tokens + response.usage.output_tokens
        self._total_tokens += tokens_used
        
        return GeneratedResponse(
            answer=response.content[0].text,
            sources=[],
            confidence=0.9,
            tokens_used=tokens_used,
            model_name=self._model
        )


class ExtractionGenerator(ResponseGenerator):
    """
    Gerador especializado em extração de informações.
    
    Otimizado para extrair dados específicos sem gerar texto livre.
    """
    
    def __init__(
        self,
        settings: Optional[Settings] = None,
        provider: Optional[str] = None
    ):
        super().__init__(settings)
        self._base_generator: Optional[ResponseGenerator] = None
        self._provider = provider or self.settings.nlp.mode
    
    def initialize(self) -> None:
        """Inicializa gerador base."""
        if self._provider == "local":
            self._base_generator = LocalGenerator(self.settings)
        else:
            self._base_generator = CloudGenerator(self.settings)
        
        self._base_generator.initialize()
        self._initialized = True
    
    def generate(
        self,
        query: str,
        context: str,
        system_prompt: Optional[str] = None
    ) -> GeneratedResponse:
        """Gera extração estruturada."""
        self.ensure_initialized()
        
        extraction_prompt = """Você é um extrator de informações de contratos.
        
Extraia APENAS a informação solicitada do contexto.
Se não encontrar, responda "NÃO ENCONTRADO".
Seja conciso e direto.
Não invente informações."""
        
        return self._base_generator.generate(
            query,
            context,
            extraction_prompt
        )
    
    def extract_field(
        self,
        field_name: str,
        context: str
    ) -> str:
        """
        Extrai um campo específico.
        
        Args:
            field_name: Nome do campo (ex: "valor do aluguel")
            context: Contexto do contrato
        
        Returns:
            str: Valor extraído ou "NÃO ENCONTRADO"
        """
        query = f"Extraia o {field_name} do contrato."
        response = self.generate(query, context)
        return response.answer.strip()
    
    def extract_multiple(
        self,
        fields: List[str],
        context: str
    ) -> Dict[str, str]:
        """
        Extrai múltiplos campos.
        
        Args:
            fields: Lista de campos a extrair
            context: Contexto do contrato
        
        Returns:
            Dict[str, str]: Dicionário campo -> valor
        """
        results = {}
        
        for field in fields:
            results[field] = self.extract_field(field, context)
        
        return results


def get_response_generator(
    mode: Optional[str] = None,
    settings: Optional[Settings] = None
) -> ResponseGenerator:
    """
    Factory para obter gerador de respostas.
    
    Args:
        mode: "local" ou "cloud"
        settings: Configurações
    
    Returns:
        ResponseGenerator: Gerador configurado
    """
    settings = settings or get_settings()
    mode = mode or settings.nlp.mode
    
    if mode == "local":
        return LocalGenerator(settings)
    else:
        return CloudGenerator(settings)
