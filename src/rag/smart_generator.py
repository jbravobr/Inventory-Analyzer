"""
Gerador Inteligente de Respostas.

Seleciona automaticamente o melhor modelo disponivel:
1. TinyLlama GGUF (se llama-cpp-python instalado e modelo existe)
2. GPT-2 Portuguese (fallback)

O usuario nao precisa se preocupar com qual modelo esta disponivel,
o sistema escolhe automaticamente.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional, Dict, Any

from .generator import ResponseGenerator, GeneratedResponse, LocalGenerator

logger = logging.getLogger(__name__)


# Configuracoes dos modelos
# max_context_chars: limite de caracteres do documento enviados ao modelo
MODEL_CONFIGS = {
    "tinyllama": {
        "type": "gguf",
        "path": "./models/generator/tinyllama-1.1b-chat-v1.0.Q4_K_M.gguf",
        "name": "TinyLlama-1.1B-Chat",
        "context_length": 2048,
        "max_tokens": 512,
        "max_context_chars": 700,  # Modelo pequeno, janela limitada
        "quality": "good",
    },
    "phi3-mini": {
        "type": "gguf", 
        "path": "./models/generator/Phi-3-mini-4k-instruct-q4.gguf",
        "name": "Phi-3-Mini-4K-Instruct",
        "context_length": 4096,
        "max_tokens": 1024,
        "max_context_chars": 2500,  # Janela maior, melhor compreensao
        "quality": "excellent",
    },
    "mistral-7b": {
        "type": "gguf",
        "path": "./models/generator/mistral-7b-instruct-v0.2.Q4_K_M.gguf",
        "name": "Mistral-7B-Instruct",
        "context_length": 4096,
        "max_tokens": 1024,
        "max_context_chars": 3000,  # Janela grande, modelo robusto
        "quality": "excellent",
    },
    "gpt2-portuguese": {
        "type": "huggingface",
        "path": "./models/generator/models--pierreguillou--gpt2-small-portuguese/snapshots/89a916c041b54c8b925e1a3282a5a334684280cb",
        "name": "GPT-2 Small Portuguese",
        "context_length": 1024,
        "max_tokens": 500,
        "max_context_chars": 500,  # Muito limitado
        "quality": "basic",
    },
}

# Ordem de preferencia
MODEL_PRIORITY = ["tinyllama", "phi3-mini", "mistral-7b", "gpt2-portuguese"]


def check_llama_cpp_available() -> bool:
    """Verifica se llama-cpp-python esta instalado."""
    try:
        import llama_cpp
        return True
    except ImportError:
        return False


def check_model_available(model_id: str) -> bool:
    """Verifica se um modelo esta disponivel."""
    if model_id not in MODEL_CONFIGS:
        return False
    
    config = MODEL_CONFIGS[model_id]
    model_path = Path(config["path"])
    
    if not model_path.exists():
        return False
    
    # Para GGUF, verifica se llama-cpp-python esta instalado
    if config["type"] == "gguf":
        return check_llama_cpp_available()
    
    return True


def get_best_available_model() -> tuple[str, Dict[str, Any]]:
    """
    Retorna o melhor modelo disponivel.
    
    Returns:
        Tupla (model_id, config)
    """
    for model_id in MODEL_PRIORITY:
        if check_model_available(model_id):
            logger.info(f"Modelo selecionado: {MODEL_CONFIGS[model_id]['name']}")
            return model_id, MODEL_CONFIGS[model_id]
    
    # Fallback final - GPT-2 (deve sempre existir)
    logger.warning("Nenhum modelo otimo disponivel, usando GPT-2 Portuguese")
    return "gpt2-portuguese", MODEL_CONFIGS["gpt2-portuguese"]


class SmartGenerator(ResponseGenerator):
    """
    Gerador inteligente que seleciona automaticamente o melhor modelo.
    
    Prioridade:
    1. TinyLlama GGUF (melhor qualidade offline)
    2. Phi-3 Mini GGUF (se disponivel)
    3. GPT-2 Portuguese (fallback garantido)
    """
    
    def __init__(
        self,
        preferred_model: Optional[str] = None,
        fallback_enabled: bool = True,
        settings = None
    ):
        """
        Inicializa o gerador inteligente.
        
        Args:
            preferred_model: Modelo preferido (opcional)
            fallback_enabled: Habilitar fallback automatico
            settings: Configurações (opcional)
        """
        # Não chama super().__init__() para evitar dependência de settings
        self.settings = settings
        self.preferred_model = preferred_model
        self.fallback_enabled = fallback_enabled
        self._generator: Optional[ResponseGenerator] = None
        self._model_id: Optional[str] = None
        self._model_config: Optional[Dict[str, Any]] = None
        self._initialized = False
        self._fallback_used = False
        self._total_tokens = 0
    
    def initialize(self) -> None:
        """Implementação do método abstrato - inicializa o gerador."""
        self.ensure_initialized()
    
    def _select_model(self) -> tuple[str, Dict[str, Any]]:
        """Seleciona o modelo a ser usado."""
        # Se modelo preferido especificado, tenta usar
        if self.preferred_model:
            if check_model_available(self.preferred_model):
                return self.preferred_model, MODEL_CONFIGS[self.preferred_model]
            elif self.fallback_enabled:
                logger.warning(
                    f"Modelo preferido '{self.preferred_model}' nao disponivel, "
                    "usando fallback"
                )
                self._fallback_used = True
            else:
                raise RuntimeError(
                    f"Modelo '{self.preferred_model}' nao disponivel e fallback desabilitado"
                )
        
        return get_best_available_model()
    
    def _create_generator(self, model_id: str, config: Dict[str, Any]) -> ResponseGenerator:
        """Cria o gerador apropriado para o modelo."""
        if config["type"] == "gguf":
            from .gguf_generator import GGUFGenerator, GGUFModelConfig
            
            gguf_config = GGUFModelConfig(
                name=config["name"],
                path=config["path"],
                context_length=config["context_length"],
                max_tokens=config["max_tokens"],
                max_context_chars=config.get("max_context_chars", 800),
            )
            return GGUFGenerator(model_config=gguf_config)
        
        else:
            # HuggingFace (GPT-2)
            return LocalGenerator(
                model_name=config["path"],
            )
    
    def ensure_initialized(self) -> None:
        """Garante que o gerador esta inicializado."""
        if self._initialized:
            return
        
        self._model_id, self._model_config = self._select_model()
        self._generator = self._create_generator(self._model_id, self._model_config)
        
        # Inicializa o gerador subjacente
        if hasattr(self._generator, 'ensure_initialized'):
            self._generator.ensure_initialized()
        
        self._initialized = True
        
        logger.info(
            f"SmartGenerator inicializado com: {self._model_config['name']} "
            f"(fallback: {self._fallback_used})"
        )
    
    def generate(
        self,
        query: str,
        context: str,
        system_prompt: Optional[str] = None,
        **kwargs
    ) -> GeneratedResponse:
        """
        Gera resposta usando o melhor modelo disponivel.
        
        Args:
            query: Pergunta do usuario
            context: Contexto do documento
            system_prompt: Instrucao de sistema
        
        Returns:
            GeneratedResponse com a resposta gerada
        """
        self.ensure_initialized()
        
        try:
            response = self._generator.generate(
                query=query,
                context=context,
                system_prompt=system_prompt,
                **kwargs
            )
            
            # Adiciona info sobre o modelo usado
            if response.metadata is None:
                response.metadata = {}
            
            response.metadata["smart_generator"] = {
                "model_id": self._model_id,
                "model_name": self._model_config["name"],
                "model_type": self._model_config["type"],
                "fallback_used": self._fallback_used,
            }
            
            return response
            
        except Exception as e:
            logger.error(f"Erro na geracao: {e}")
            
            # Se fallback habilitado e nao estamos ja no fallback, tenta GPT-2
            if self.fallback_enabled and self._model_id != "gpt2-portuguese":
                logger.warning("Tentando fallback para GPT-2 Portuguese")
                self._model_id = "gpt2-portuguese"
                self._model_config = MODEL_CONFIGS["gpt2-portuguese"]
                self._generator = self._create_generator(self._model_id, self._model_config)
                self._fallback_used = True
                
                return self._generator.generate(
                    query=query,
                    context=context,
                    system_prompt=system_prompt,
                    **kwargs
                )
            
            raise
    
    def get_model_info(self) -> Dict[str, Any]:
        """Retorna informacoes do modelo em uso."""
        self.ensure_initialized()
        
        return {
            "model_id": self._model_id,
            "model_name": self._model_config["name"],
            "model_type": self._model_config["type"],
            "model_quality": self._model_config["quality"],
            "fallback_used": self._fallback_used,
            "llama_cpp_available": check_llama_cpp_available(),
        }
    
    @property
    def model_name(self) -> str:
        """Nome do modelo em uso."""
        self.ensure_initialized()
        return self._model_config["name"]
    
    @property
    def is_using_fallback(self) -> bool:
        """Se esta usando modelo de fallback."""
        return self._fallback_used


def get_smart_generator(
    preferred_model: Optional[str] = None,
    fallback_enabled: bool = True
) -> SmartGenerator:
    """
    Obtem um gerador inteligente configurado.
    
    Args:
        preferred_model: Modelo preferido (tinyllama, phi3-mini, gpt2-portuguese)
        fallback_enabled: Habilitar fallback automatico
    
    Returns:
        SmartGenerator configurado
    """
    return SmartGenerator(
        preferred_model=preferred_model,
        fallback_enabled=fallback_enabled
    )


def list_available_models() -> list[Dict[str, Any]]:
    """
    Lista modelos disponiveis e seu status.
    
    Returns:
        Lista de dicionarios com info dos modelos
    """
    models = []
    llama_available = check_llama_cpp_available()
    
    for model_id in MODEL_PRIORITY:
        config = MODEL_CONFIGS[model_id]
        model_path = Path(config["path"])
        
        model_exists = model_path.exists()
        
        if config["type"] == "gguf":
            available = model_exists and llama_available
            reason = None
            if not available:
                if not model_exists:
                    reason = "modelo nao encontrado"
                elif not llama_available:
                    reason = "llama-cpp-python nao instalado"
        else:
            available = model_exists
            reason = "modelo nao encontrado" if not available else None
        
        models.append({
            "id": model_id,
            "name": config["name"],
            "type": config["type"],
            "quality": config["quality"],
            "path": config["path"],
            "available": available,
            "exists": model_exists,
            "reason": reason,
        })
    
    return models

