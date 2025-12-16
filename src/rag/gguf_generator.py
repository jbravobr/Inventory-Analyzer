"""
Gerador de Respostas usando modelos GGUF.

Suporta modelos quantizados como TinyLlama, Phi-3, Mistral, etc.
via llama-cpp-python para inferencia eficiente em CPU.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Dict, Any, List

from .generator import ResponseGenerator, GeneratedResponse

logger = logging.getLogger(__name__)


@dataclass
class GGUFModelConfig:
    """Configuracao de um modelo GGUF."""
    
    name: str
    path: str
    description: str = ""
    context_length: int = 2048
    max_tokens: int = 512
    temperature: float = 0.1
    top_p: float = 0.95
    repeat_penalty: float = 1.1
    
    # Configuracoes de hardware
    n_gpu_layers: int = 0  # 0 = CPU only
    n_threads: Optional[int] = None  # None = auto
    
    # Template de prompt (formato ChatML, Llama, etc.)
    prompt_template: str = "chatml"  # chatml, llama, alpaca, raw
    
    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "path": self.path,
            "description": self.description,
            "context_length": self.context_length,
            "max_tokens": self.max_tokens,
        }


# Configuracoes pre-definidas para modelos populares
PREDEFINED_MODELS = {
    "tinyllama": GGUFModelConfig(
        name="TinyLlama-1.1B-Chat",
        path="./models/generator/tinyllama-1.1b-chat-v1.0.Q4_K_M.gguf",
        description="TinyLlama 1.1B - Leve e rapido, bom para Q&A basico",
        context_length=2048,
        max_tokens=512,
        prompt_template="chatml",
    ),
    "phi3-mini": GGUFModelConfig(
        name="Phi-3-Mini-4K-Instruct",
        path="./models/generator/Phi-3-mini-4k-instruct-q4.gguf",
        description="Phi-3 Mini - Excelente qualidade, requer mais RAM",
        context_length=4096,
        max_tokens=1024,
        prompt_template="chatml",
    ),
    "mistral-7b": GGUFModelConfig(
        name="Mistral-7B-Instruct",
        path="./models/generator/mistral-7b-instruct-v0.2.Q4_K_M.gguf",
        description="Mistral 7B - Alta qualidade, requer 8GB+ RAM",
        context_length=4096,
        max_tokens=1024,
        prompt_template="llama",
    ),
}


class GGUFGenerator(ResponseGenerator):
    """
    Gerador de respostas usando modelos GGUF via llama-cpp-python.
    
    Otimizado para execucao em CPU em ambientes corporativos.
    """
    
    def __init__(
        self,
        model_config: Optional[GGUFModelConfig] = None,
        model_name: str = "tinyllama"
    ):
        """
        Inicializa o gerador GGUF.
        
        Args:
            model_config: Configuracao customizada do modelo
            model_name: Nome do modelo pre-definido (se model_config nao fornecido)
        """
        if model_config:
            self.config = model_config
        elif model_name in PREDEFINED_MODELS:
            self.config = PREDEFINED_MODELS[model_name]
        else:
            raise ValueError(
                f"Modelo '{model_name}' nao encontrado. "
                f"Disponiveis: {list(PREDEFINED_MODELS.keys())}"
            )
        
        self._llm = None
        self._initialized = False
    
    def ensure_initialized(self) -> None:
        """Garante que o modelo esta carregado."""
        if self._initialized:
            return
        
        model_path = Path(self.config.path)
        
        if not model_path.exists():
            raise FileNotFoundError(
                f"Modelo GGUF nao encontrado: {model_path}\n"
                f"Baixe o modelo e coloque em: {model_path.parent}\n"
                f"Veja docs/MODELOS_OFFLINE.md para instrucoes."
            )
        
        try:
            from llama_cpp import Llama
            
            logger.info(f"Carregando modelo GGUF: {self.config.name}")
            
            self._llm = Llama(
                model_path=str(model_path),
                n_ctx=self.config.context_length,
                n_gpu_layers=self.config.n_gpu_layers,
                n_threads=self.config.n_threads,
                verbose=False,
            )
            
            self._initialized = True
            logger.info(f"Modelo GGUF carregado: {self.config.name}")
            
        except ImportError:
            raise ImportError(
                "llama-cpp-python nao esta instalado.\n"
                "Instale com: pip install llama-cpp-python\n"
                "Ou baixe o wheel apropriado para seu sistema."
            )
        except Exception as e:
            raise RuntimeError(f"Erro ao carregar modelo GGUF: {e}")
    
    def _format_prompt(
        self,
        query: str,
        context: str,
        system_prompt: Optional[str] = None
    ) -> str:
        """
        Formata o prompt de acordo com o template do modelo.
        
        Args:
            query: Pergunta do usuario
            context: Contexto do documento
            system_prompt: Instrucao de sistema
        
        Returns:
            Prompt formatado
        """
        if not system_prompt:
            system_prompt = (
                "Voce e um assistente que responde perguntas sobre documentos. "
                "Responda apenas com base no contexto fornecido. "
                "Se a informacao nao estiver no contexto, diga que nao foi encontrada."
            )
        
        if self.config.prompt_template == "chatml":
            # Formato ChatML (TinyLlama, Phi-3)
            return (
                f"<|im_start|>system\n{system_prompt}<|im_end|>\n"
                f"<|im_start|>user\n"
                f"Contexto:\n{context}\n\n"
                f"Pergunta: {query}<|im_end|>\n"
                f"<|im_start|>assistant\n"
            )
        
        elif self.config.prompt_template == "llama":
            # Formato Llama/Mistral
            return (
                f"[INST] {system_prompt}\n\n"
                f"Contexto:\n{context}\n\n"
                f"Pergunta: {query} [/INST]"
            )
        
        elif self.config.prompt_template == "alpaca":
            # Formato Alpaca
            return (
                f"### Instruction:\n{system_prompt}\n\n"
                f"### Input:\n"
                f"Contexto:\n{context}\n\n"
                f"Pergunta: {query}\n\n"
                f"### Response:\n"
            )
        
        else:
            # Formato raw/simples
            return (
                f"Sistema: {system_prompt}\n\n"
                f"Contexto:\n{context}\n\n"
                f"Pergunta: {query}\n\n"
                f"Resposta:"
            )
    
    def generate(
        self,
        query: str,
        context: str,
        system_prompt: Optional[str] = None,
        **kwargs
    ) -> GeneratedResponse:
        """
        Gera resposta usando o modelo GGUF.
        
        Args:
            query: Pergunta do usuario
            context: Contexto do documento
            system_prompt: Instrucao de sistema
        
        Returns:
            GeneratedResponse com a resposta gerada
        """
        self.ensure_initialized()
        
        # Formata prompt
        prompt = self._format_prompt(query, context, system_prompt)
        
        # Trunca contexto se necessario
        max_prompt_tokens = self.config.context_length - self.config.max_tokens - 100
        
        # Gera resposta
        try:
            output = self._llm(
                prompt,
                max_tokens=self.config.max_tokens,
                temperature=self.config.temperature,
                top_p=self.config.top_p,
                repeat_penalty=self.config.repeat_penalty,
                stop=["<|im_end|>", "[/INST]", "###", "\n\n\n"],
                echo=False,
            )
            
            # Extrai texto da resposta
            answer = output["choices"][0]["text"].strip()
            
            # Remove tokens de parada residuais
            for stop_token in ["<|im_end|>", "[/INST]", "###"]:
                if stop_token in answer:
                    answer = answer.split(stop_token)[0].strip()
            
            # Calcula confianca baseada no tamanho da resposta
            confidence = min(1.0, len(answer) / 200) * 0.8
            
            return GeneratedResponse(
                answer=answer,
                confidence=confidence,
                model=self.config.name,
                metadata={
                    "tokens_generated": output["usage"]["completion_tokens"],
                    "prompt_tokens": output["usage"]["prompt_tokens"],
                    "model_type": "gguf",
                }
            )
            
        except Exception as e:
            logger.error(f"Erro na geracao GGUF: {e}")
            return GeneratedResponse(
                answer=f"Erro ao gerar resposta: {str(e)[:100]}",
                confidence=0.0,
                model=self.config.name,
            )
    
    def get_model_info(self) -> Dict[str, Any]:
        """Retorna informacoes do modelo."""
        return {
            "name": self.config.name,
            "path": self.config.path,
            "description": self.config.description,
            "context_length": self.config.context_length,
            "max_tokens": self.config.max_tokens,
            "initialized": self._initialized,
            "type": "gguf",
        }


def list_available_models() -> List[Dict[str, Any]]:
    """
    Lista modelos GGUF disponiveis.
    
    Returns:
        Lista com informacoes dos modelos
    """
    models = []
    
    for name, config in PREDEFINED_MODELS.items():
        model_path = Path(config.path)
        models.append({
            "name": name,
            "full_name": config.name,
            "description": config.description,
            "path": config.path,
            "exists": model_path.exists(),
            "context_length": config.context_length,
        })
    
    return models


def get_gguf_generator(
    model_name: str = "tinyllama",
    model_path: Optional[str] = None
) -> GGUFGenerator:
    """
    Obtem um gerador GGUF.
    
    Args:
        model_name: Nome do modelo pre-definido
        model_path: Caminho customizado do modelo (opcional)
    
    Returns:
        GGUFGenerator configurado
    """
    if model_path:
        config = GGUFModelConfig(
            name=model_name,
            path=model_path,
        )
        return GGUFGenerator(model_config=config)
    
    return GGUFGenerator(model_name=model_name)

