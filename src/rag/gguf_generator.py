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
    
    # Limite de caracteres de contexto do documento
    # Este valor controla quanto do documento e enviado ao modelo
    # Valores maiores = mais contexto = respostas potencialmente melhores
    # Mas deve respeitar o limite de tokens do modelo
    max_context_chars: int = 800
    
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
            "max_context_chars": self.max_context_chars,
        }


# Configuracoes pre-definidas para modelos populares
# max_context_chars: controla quanto do documento e enviado ao modelo
# Valores recomendados baseados em testes de qualidade vs performance
# NOTA: TinyLlama tem 2048 tokens de contexto. Com ~4 chars/token em PT-BR,
#       podemos usar ~1200-1500 chars de contexto para o documento
#       + ~500 chars para prompt/instruções = margem segura
PREDEFINED_MODELS = {
    "tinyllama": GGUFModelConfig(
        name="TinyLlama-1.1B-Chat",
        path="./models/generator/tinyllama-1.1b-chat-v1.0.Q4_K_M.gguf",
        description="TinyLlama 1.1B - Leve e rapido, bom para Q&A basico",
        context_length=2048,
        max_tokens=512,  # Aumentado para respostas mais completas
        max_context_chars=500,  # Contexto conservador para balancear com resposta
        prompt_template="chatml",
    ),
    "phi3-mini": GGUFModelConfig(
        name="Phi-3-Mini-4K-Instruct",
        path="./models/generator/Phi-3-mini-4k-instruct-q4.gguf",
        description="Phi-3 Mini - Excelente qualidade, requer mais RAM",
        context_length=4096,
        max_tokens=1024,
        max_context_chars=2500,  # Janela maior, melhor compreensao
        prompt_template="chatml",
    ),
    "mistral-7b": GGUFModelConfig(
        name="Mistral-7B-Instruct",
        path="./models/generator/mistral-7b-instruct-v0.2.Q4_K_M.gguf",
        description="Mistral 7B - Alta qualidade, requer 8GB+ RAM",
        context_length=4096,
        max_tokens=1024,
        max_context_chars=3000,  # Janela grande, modelo robusto
        prompt_template="llama",
    ),
    "llama3-8b": GGUFModelConfig(
        name="Llama-3.1-8B-Instruct",
        path="./models/generator/Meta-Llama-3.1-8B-Instruct-Q4_K_M.gguf",
        description="Llama 3.1 8B - Melhor para portugues, requer 8GB+ RAM",
        context_length=8192,  # Suporta ate 128K, mas 8K e suficiente
        max_tokens=1024,
        max_context_chars=4000,  # 8x mais contexto que TinyLlama
        prompt_template="llama3",  # Formato especifico do Llama 3
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
        model_name: str = "tinyllama",
        settings = None
    ):
        """
        Inicializa o gerador GGUF.
        
        Args:
            model_config: Configuracao customizada do modelo
            model_name: Nome do modelo pre-definido (se model_config nao fornecido)
            settings: Configurações (opcional)
        """
        # Não chama super().__init__() para evitar dependência de settings
        self.settings = settings
        self._total_tokens = 0
        
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
    
    def initialize(self) -> None:
        """Implementação do método abstrato - inicializa o modelo."""
        self.ensure_initialized()
    
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
        # Para modelos com contexto pequeno, usa prompt simplificado
        simple_system = (
            "Voce e um assistente que responde perguntas sobre documentos. "
            "Responda apenas com base no contexto fornecido. "
            "Se a informacao nao estiver no contexto, diga que nao foi encontrada."
        )
        
        # Se o contexto total for muito grande, usa prompt simples
        if system_prompt and len(system_prompt) > 500:
            logger.debug("Usando prompt simplificado devido ao tamanho do contexto")
            system_prompt = simple_system
        elif not system_prompt:
            system_prompt = simple_system
        
        if self.config.prompt_template == "chatml":
            # Formato ChatML (TinyLlama, Phi-3)
            return (
                f"<|im_start|>system\n{system_prompt}<|im_end|>\n"
                f"<|im_start|>user\nCom base no contexto abaixo, responda a pergunta.\n\n"
                f"CONTEXTO:\n{context}\n\n"
                f"PERGUNTA: {query}\n\nResponda de forma direta e objetiva.<|im_end|>\n"
                f"<|im_start|>assistant\nRESPOSTA: "
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
        
        elif self.config.prompt_template == "llama3":
            # Formato Llama 3 / Llama 3.1 (oficial)
            # Ref: https://llama.meta.com/docs/model-cards-and-prompt-formats/meta-llama-3/
            return (
                f"<|begin_of_text|><|start_header_id|>system<|end_header_id|>\n\n"
                f"{system_prompt}<|eot_id|>"
                f"<|start_header_id|>user<|end_header_id|>\n\n"
                f"Com base no contexto abaixo, responda a pergunta.\n\n"
                f"CONTEXTO:\n{context}\n\n"
                f"PERGUNTA: {query}<|eot_id|>"
                f"<|start_header_id|>assistant<|end_header_id|>\n\n"
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
        
        # Usa o limite de caracteres configurado para o modelo
        # Este valor e definido em GGUFModelConfig.max_context_chars
        # e pode ser ajustado via config.yaml para cada modelo
        max_context_chars = self.config.max_context_chars
        
        # Trunca contexto se muito grande
        truncated_context = context
        if len(context) > max_context_chars:
            truncated_context = context[:max_context_chars] + "\n...[truncado]"
            logger.info(f"Contexto truncado de {len(context)} para {max_context_chars} caracteres")
        
        # Formata prompt com contexto possivelmente truncado
        prompt = self._format_prompt(query, truncated_context, system_prompt)
        
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
                sources=[],
                confidence=confidence,
                model_name=self.config.name,
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
                sources=[],
                confidence=0.0,
                model_name=self.config.name,
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

