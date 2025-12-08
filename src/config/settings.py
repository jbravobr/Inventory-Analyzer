"""Gerenciador de configurações do aplicativo."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import yaml
from dotenv import load_dotenv


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
    
    highlight_color: Tuple[int, int, int] = (255, 255, 0)
    highlight_opacity: float = 0.4
    output_format: str = "png"
    create_summary: bool = True


@dataclass
class LegalTermsConfig:
    """Configurações de termos jurídicos."""
    
    contract_types: List[str] = field(default_factory=list)
    key_sections: List[str] = field(default_factory=list)
    parties: List[str] = field(default_factory=list)


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
    
    app: AppConfig = field(default_factory=AppConfig)
    ocr: OCRConfig = field(default_factory=OCRConfig)
    nlp: NLPConfig = field(default_factory=NLPConfig)
    validation: ValidationConfig = field(default_factory=ValidationConfig)
    search: SearchConfig = field(default_factory=SearchConfig)
    output: OutputConfig = field(default_factory=OutputConfig)
    legal_terms: LegalTermsConfig = field(default_factory=LegalTermsConfig)
    
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
