"""Gerenciador de configurações do aplicativo."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import yaml
from dotenv import load_dotenv

from .mode_manager import (
    SystemConfig,
    OnlineConfig,
    OfflineConfig,
    HybridConfig,
)


@dataclass
class OCRConfig:
    """Configurações do Tesseract OCR."""
    
    tesseract_path: str = "C:\\Program Files\\Tesseract-OCR\\tesseract.exe"
    language: str = "por"
    dpi: int = 300
    config: str = "--psm 3 --oem 3"


@dataclass
class LocalNLPConfig:
    """Configurações do processador NLP local."""
    
    spacy_model: str = "pt_core_news_lg"
    sentence_transformer: str = "neuralmind/bert-base-portuguese-cased"
    similarity_threshold: float = 0.75


@dataclass
class CloudNLPConfig:
    """Configurações do processador NLP em nuvem."""
    
    enabled: bool = False
    provider: str = "openai"
    model: str = "gpt-4o-mini"
    api_key_env: str = "OPENAI_API_KEY"
    max_tokens: int = 2000
    temperature: float = 0.1
    
    @property
    def api_key(self) -> Optional[str]:
        """Obtém a API key do ambiente."""
        return os.getenv(self.api_key_env)


@dataclass
class NLPConfig:
    """Configurações gerais de NLP."""
    
    mode: str = "local"
    local: LocalNLPConfig = field(default_factory=LocalNLPConfig)
    cloud: CloudNLPConfig = field(default_factory=CloudNLPConfig)
    
    @property
    def is_local(self) -> bool:
        """Verifica se está usando modo local."""
        return self.mode == "local"


@dataclass
class ValidationConfig:
    """Configurações de validação de texto."""
    
    min_word_count: int = 10
    min_sentence_coherence: float = 0.6
    check_encoding: bool = True
    language_detection: bool = True


@dataclass
class SearchConfig:
    """Configurações de busca."""
    
    use_semantic_search: bool = True
    use_keyword_search: bool = True
    combine_results: bool = True
    max_results: int = 50


@dataclass
class OutputConfig:
    """Configurações de saída."""
    
    default_dir: str = "./output"
    highlight_color: Tuple[int, int, int] = (255, 255, 0)
    highlight_colors: Dict[str, List[int]] = field(default_factory=dict)
    highlight_opacity: float = 0.4
    output_format: str = "png"
    create_summary: bool = True


@dataclass
class LegalTermsConfig:
    """Configurações de termos jurídicos."""
    
    contract_types: List[str] = field(default_factory=list)
    key_sections: List[str] = field(default_factory=list)
    parties: List[str] = field(default_factory=list)
    document_types: List[str] = field(default_factory=list)
    heir_keywords: List[str] = field(default_factory=list)
    administrator_keywords: List[str] = field(default_factory=list)
    btg_keywords: List[str] = field(default_factory=list)
    asset_types: List[str] = field(default_factory=list)
    division_keywords: List[str] = field(default_factory=list)


@dataclass
class CloudProviderConfig:
    """Configuração de um provedor cloud específico."""
    
    api_key_env: str = ""
    embedding_model: str = ""
    generation_model: str = ""
    max_tokens: int = 2000
    temperature: float = 0.1
    
    @property
    def api_key(self) -> Optional[str]:
        """Obtém a API key do ambiente."""
        if self.api_key_env:
            return os.getenv(self.api_key_env)
        return None


@dataclass
class CloudProvidersConfig:
    """Configurações dos provedores cloud disponíveis."""
    
    openai: CloudProviderConfig = field(default_factory=lambda: CloudProviderConfig(
        api_key_env="OPENAI_API_KEY",
        embedding_model="text-embedding-3-small",
        generation_model="gpt-4o-mini",
        max_tokens=2000,
        temperature=0.1
    ))
    anthropic: CloudProviderConfig = field(default_factory=lambda: CloudProviderConfig(
        api_key_env="ANTHROPIC_API_KEY",
        embedding_model="",
        generation_model="claude-3-haiku-20240307",
        max_tokens=2000,
        temperature=0.1
    ))


@dataclass
class LLMExtractionConfig:
    """Configurações de extração via LLM (complementa regex)."""
    
    enabled: bool = False
    provider: str = "openai"
    merge_strategy: str = "regex_priority"  # regex_priority | llm_priority | union
    fallback_to_regex: bool = True
    
    # Quais tipos de dados o LLM pode extrair
    extract_valores_monetarios: bool = False    # R$ - regex é mais preciso
    extract_quantidades: bool = False           # Números - regex é mais preciso
    extract_nomes_pessoas: bool = True          # LLM entende contexto
    extract_datas_relativas: bool = True        # "mês passado" - LLM entende
    extract_referencias_contextuais: bool = True  # "conforme acima" - LLM entende
    extract_valores_por_extenso: bool = True    # "trinta mil reais" - LLM entende


@dataclass
class LLMSummarizationConfig:
    """Configurações de sumarização via LLM."""
    
    enabled: bool = False
    generate_executive_summary: bool = False
    generate_insights: bool = False


@dataclass
class RAGGenerationConfig:
    """Configuracoes de geracao RAG."""
    
    mode: str = "local"
    generate_answers: bool = True
    max_tokens: int = 500
    temperature: float = 0.1
    
    # Modelo padrao (novo sistema GGUF)
    default_model: str = "tinyllama"  # tinyllama | phi3-mini | gpt2-portuguese
    
    # Configuracoes de modelos (dict para flexibilidade)
    models: Dict[str, Any] = field(default_factory=dict)
    
    # Path do modelo local (fallback - sera depreciado)
    local_model: str = "./models/generator/models--pierreguillou--gpt2-small-portuguese/snapshots/89a916c041b54c8b925e1a3282a5a334684280cb"
    
    # Configuracoes de LLM cloud
    cloud_providers: CloudProvidersConfig = field(default_factory=CloudProvidersConfig)
    llm_extraction: LLMExtractionConfig = field(default_factory=LLMExtractionConfig)
    llm_summarization: LLMSummarizationConfig = field(default_factory=LLMSummarizationConfig)


@dataclass
class RAGConfig:
    """Configurações do pipeline RAG."""
    
    enabled: bool = True
    generation: RAGGenerationConfig = field(default_factory=RAGGenerationConfig)


@dataclass
class AppConfig:
    """Configurações gerais do aplicativo."""
    
    name: str = "PDF Contract Analyzer"
    version: str = "1.0.0"
    language: str = "pt-BR"
    log_level: str = "INFO"


@dataclass
class Settings:
    """Configurações completas do aplicativo."""
    
    system: SystemConfig = field(default_factory=SystemConfig)
    app: AppConfig = field(default_factory=AppConfig)
    ocr: OCRConfig = field(default_factory=OCRConfig)
    nlp: NLPConfig = field(default_factory=NLPConfig)
    validation: ValidationConfig = field(default_factory=ValidationConfig)
    search: SearchConfig = field(default_factory=SearchConfig)
    output: OutputConfig = field(default_factory=OutputConfig)
    legal_terms: LegalTermsConfig = field(default_factory=LegalTermsConfig)
    rag: RAGConfig = field(default_factory=RAGConfig)
    
    @classmethod
    def from_yaml(cls, config_path: Path) -> "Settings":
        """Carrega configurações de um arquivo YAML."""
        with open(config_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        
        return cls._from_dict(data)
    
    @classmethod
    def _from_dict(cls, data: Dict[str, Any]) -> "Settings":
        """Cria Settings a partir de um dicionário."""
        settings = cls()
        
        # Carrega configuração de sistema (modo de operação)
        if "system" in data:
            system_data = data["system"]
            online_config = OnlineConfig(**system_data.get("online", {}))
            offline_config = OfflineConfig(**system_data.get("offline", {}))
            hybrid_config = HybridConfig(**system_data.get("hybrid", {}))
            settings.system = SystemConfig(
                mode=system_data.get("mode", "offline"),
                online=online_config,
                offline=offline_config,
                hybrid=hybrid_config
            )
        
        if "app" in data:
            settings.app = AppConfig(**data["app"])
        
        if "ocr" in data:
            settings.ocr = OCRConfig(**data["ocr"])
        
        if "nlp" in data:
            nlp_data = data["nlp"]
            local_config = LocalNLPConfig(**nlp_data.get("local", {}))
            cloud_config = CloudNLPConfig(**nlp_data.get("cloud", {}))
            settings.nlp = NLPConfig(
                mode=nlp_data.get("mode", "local"),
                local=local_config,
                cloud=cloud_config
            )
        
        if "validation" in data:
            settings.validation = ValidationConfig(**data["validation"])
        
        if "search" in data:
            settings.search = SearchConfig(**data["search"])
        
        if "output" in data:
            output_data = data["output"]
            if "highlight_color" in output_data:
                output_data["highlight_color"] = tuple(output_data["highlight_color"])
            settings.output = OutputConfig(**output_data)
        
        if "legal_terms" in data:
            settings.legal_terms = LegalTermsConfig(**data["legal_terms"])
        
        if "rag" in data:
            rag_data = data["rag"]
            generation_data = rag_data.get("generation", {})
            
            # Parse cloud providers
            cloud_providers_data = generation_data.get("cloud_providers", {})
            openai_config = CloudProviderConfig(**cloud_providers_data.get("openai", {})) if "openai" in cloud_providers_data else CloudProviderConfig(
                api_key_env="OPENAI_API_KEY",
                embedding_model="text-embedding-3-small",
                generation_model="gpt-4o-mini"
            )
            anthropic_config = CloudProviderConfig(**cloud_providers_data.get("anthropic", {})) if "anthropic" in cloud_providers_data else CloudProviderConfig(
                api_key_env="ANTHROPIC_API_KEY",
                generation_model="claude-3-haiku-20240307"
            )
            cloud_providers = CloudProvidersConfig(openai=openai_config, anthropic=anthropic_config)
            
            # Parse LLM extraction config
            llm_extraction_data = generation_data.get("llm_extraction", {})
            llm_extraction = LLMExtractionConfig(**llm_extraction_data) if llm_extraction_data else LLMExtractionConfig()
            
            # Parse LLM summarization config
            llm_summarization_data = generation_data.get("llm_summarization", {})
            llm_summarization = LLMSummarizationConfig(**llm_summarization_data) if llm_summarization_data else LLMSummarizationConfig()
            
            # Remove nested configs before passing to RAGGenerationConfig
            gen_data_clean = {k: v for k, v in generation_data.items() 
                           if k not in ["cloud_providers", "llm_extraction", "llm_summarization"]}
            
            generation_config = RAGGenerationConfig(
                **gen_data_clean,
                cloud_providers=cloud_providers,
                llm_extraction=llm_extraction,
                llm_summarization=llm_summarization
            )
            
            settings.rag = RAGConfig(
                enabled=rag_data.get("enabled", True),
                generation=generation_config
            )
        
        return settings
    
    def to_dict(self) -> Dict[str, Any]:
        """Converte configurações para dicionário."""
        from dataclasses import asdict
        return asdict(self)


# Singleton para configurações globais
_settings: Optional[Settings] = None


def get_settings(config_path: Optional[Path] = None) -> Settings:
    """
    Obtém as configurações globais do aplicativo.
    
    Args:
        config_path: Caminho para o arquivo de configuração.
                    Se não fornecido, usa o padrão.
    
    Returns:
        Settings: Instância das configurações.
    """
    global _settings
    
    # Carrega variáveis de ambiente
    load_dotenv()
    
    if _settings is None or config_path is not None:
        if config_path is None:
            # Procura config.yaml no diretório do projeto
            config_path = Path(__file__).parent.parent.parent / "config.yaml"
        
        if config_path.exists():
            _settings = Settings.from_yaml(config_path)
        else:
            _settings = Settings()
    
    return _settings


def reset_settings() -> None:
    """Reseta as configurações globais (útil para testes)."""
    global _settings
    _settings = None
