"""
Gerenciador de modo de operação (Online/Offline/Hybrid).

Este módulo controla como o aplicativo se comporta em relação a:
- Download de modelos do HuggingFace
- Uso de APIs cloud (embeddings, geração)
- Configuração de variáveis de ambiente
"""

from __future__ import annotations

import logging
import os
import socket
from dataclasses import dataclass
from enum import Enum
from typing import Optional

logger = logging.getLogger(__name__)


class OperationMode(Enum):
    """Modos de operação disponíveis."""
    OFFLINE = "offline"
    ONLINE = "online"
    HYBRID = "hybrid"


@dataclass
class OnlineConfig:
    """Configurações para modo online."""
    allow_model_download: bool = True
    check_for_updates: bool = False
    use_cloud_embeddings: bool = False
    use_cloud_generation: bool = False
    connection_timeout: int = 10


@dataclass
class OfflineConfig:
    """Configurações para modo offline."""
    models_path: str = "./models"
    strict: bool = True


@dataclass
class HybridConfig:
    """Configurações para modo híbrido."""
    prefer: str = "online"  # "online" ou "offline"
    fallback_enabled: bool = True
    fallback_timeout: int = 5


@dataclass
class SystemConfig:
    """Configurações do sistema (modo de operação)."""
    mode: str = "offline"
    online: OnlineConfig = None
    offline: OfflineConfig = None
    hybrid: HybridConfig = None
    
    def __post_init__(self):
        if self.online is None:
            self.online = OnlineConfig()
        if self.offline is None:
            self.offline = OfflineConfig()
        if self.hybrid is None:
            self.hybrid = HybridConfig()


class ModeManager:
    """
    Gerenciador de modo de operação.
    
    Responsabilidades:
    - Determinar o modo ativo (config.yaml ou CLI override)
    - Configurar variáveis de ambiente apropriadas
    - Fornecer API para outros módulos consultarem o modo
    - Testar conectividade quando necessário
    - Controlar uso de cloud generation e embeddings
    """
    
    # URLs para teste de conectividade
    HUGGINGFACE_HOST = "huggingface.co"
    HUGGINGFACE_PORT = 443
    
    def __init__(
        self,
        config: Optional[SystemConfig] = None,
        cli_override: Optional[str] = None,
        allow_download_override: Optional[bool] = None,
        use_cloud_generation_override: Optional[bool] = None,
        use_cloud_embeddings_override: Optional[bool] = None
    ):
        """
        Inicializa o gerenciador de modo.
        
        Args:
            config: Configuração do sistema (do config.yaml)
            cli_override: Modo forçado via CLI (--online, --offline, --hybrid)
            allow_download_override: Override para permitir/bloquear downloads
            use_cloud_generation_override: Override para usar geração cloud
            use_cloud_embeddings_override: Override para usar embeddings cloud
        """
        self._config = config or SystemConfig()
        self._cli_override = cli_override
        self._allow_download_override = allow_download_override
        self._use_cloud_generation_override = use_cloud_generation_override
        self._use_cloud_embeddings_override = use_cloud_embeddings_override
        self._connectivity_tested = False
        self._is_connected = False
        
        # Determina o modo efetivo
        self._effective_mode = self._determine_effective_mode()
        
        logger.info(f"ModeManager inicializado - Modo: {self._effective_mode.value}")
    
    def _determine_effective_mode(self) -> OperationMode:
        """Determina o modo efetivo baseado em config e overrides."""
        if self._cli_override:
            try:
                return OperationMode(self._cli_override.lower())
            except ValueError:
                logger.warning(
                    f"Modo CLI inválido: {self._cli_override}. "
                    f"Usando configuração padrão."
                )
        
        try:
            return OperationMode(self._config.mode.lower())
        except ValueError:
            logger.warning(
                f"Modo inválido no config: {self._config.mode}. "
                f"Usando OFFLINE como padrão."
            )
            return OperationMode.OFFLINE
    
    @property
    def mode(self) -> OperationMode:
        """Retorna o modo de operação efetivo."""
        return self._effective_mode
    
    @property
    def is_offline(self) -> bool:
        """Verifica se está em modo offline."""
        return self._effective_mode == OperationMode.OFFLINE
    
    @property
    def is_online(self) -> bool:
        """Verifica se está em modo online."""
        return self._effective_mode == OperationMode.ONLINE
    
    @property
    def is_hybrid(self) -> bool:
        """Verifica se está em modo híbrido."""
        return self._effective_mode == OperationMode.HYBRID
    
    @property
    def allow_downloads(self) -> bool:
        """Verifica se downloads são permitidos."""
        # CLI override tem prioridade
        if self._allow_download_override is not None:
            return self._allow_download_override
        
        # Em modo offline, nunca permite downloads
        if self.is_offline:
            return False
        
        # Em modo online ou hybrid, verifica configuração
        return self._config.online.allow_model_download
    
    @property
    def allow_cloud_apis(self) -> bool:
        """Verifica se APIs cloud são permitidas."""
        if self.is_offline:
            return False
        
        return (
            self._config.online.use_cloud_embeddings or
            self._config.online.use_cloud_generation
        )
    
    @property
    def use_cloud_generation(self) -> bool:
        """
        Verifica se deve usar geração cloud (LLM).
        
        Condições:
        - Não pode estar em modo offline
        - CLI override tem prioridade
        - Senão, usa configuração do config.yaml
        """
        # CLI override tem prioridade
        if self._use_cloud_generation_override is not None:
            # Mesmo com override, não permite em modo offline
            if self.is_offline and self._use_cloud_generation_override:
                logger.warning("Geração cloud solicitada mas modo é OFFLINE. Ignorando.")
                return False
            return self._use_cloud_generation_override
        
        # Em modo offline, nunca usa cloud
        if self.is_offline:
            return False
        
        # Usa configuração
        return self._config.online.use_cloud_generation
    
    @property
    def use_cloud_embeddings(self) -> bool:
        """
        Verifica se deve usar embeddings cloud.
        
        Condições:
        - Não pode estar em modo offline
        - CLI override tem prioridade
        - Senão, usa configuração do config.yaml
        """
        # CLI override tem prioridade
        if self._use_cloud_embeddings_override is not None:
            # Mesmo com override, não permite em modo offline
            if self.is_offline and self._use_cloud_embeddings_override:
                logger.warning("Embeddings cloud solicitados mas modo é OFFLINE. Ignorando.")
                return False
            return self._use_cloud_embeddings_override
        
        # Em modo offline, nunca usa cloud
        if self.is_offline:
            return False
        
        # Usa configuração
        return self._config.online.use_cloud_embeddings
    
    @property
    def models_path(self) -> str:
        """Retorna o caminho dos modelos locais."""
        return self._config.offline.models_path
    
    @property
    def connection_timeout(self) -> int:
        """Retorna o timeout de conexão."""
        if self.is_hybrid:
            return self._config.hybrid.fallback_timeout
        return self._config.online.connection_timeout
    
    def configure_environment(self) -> None:
        """
        Configura variáveis de ambiente baseado no modo.
        
        Esta função deve ser chamada no início da execução para
        garantir que as bibliotecas (transformers, etc.) se comportem
        corretamente.
        """
        if self.is_offline:
            self._set_offline_environment()
        elif self.is_online:
            self._set_online_environment()
        else:  # hybrid
            # Em modo híbrido, testa conectividade primeiro
            if self.check_connectivity():
                self._set_online_environment()
            else:
                logger.info("Modo HYBRID: Sem conectividade, usando modo offline")
                self._set_offline_environment()
    
    def _set_offline_environment(self) -> None:
        """Configura variáveis de ambiente para modo offline."""
        os.environ["TRANSFORMERS_OFFLINE"] = "1"
        os.environ["HF_HUB_OFFLINE"] = "1"
        os.environ["HF_DATASETS_OFFLINE"] = "1"
        
        # Configura cache local
        models_path = os.path.abspath(self._config.offline.models_path)
        os.environ["HF_HOME"] = models_path
        os.environ["HF_HUB_CACHE"] = models_path
        os.environ["TRANSFORMERS_CACHE"] = models_path
        
        # Desabilita warning de symlinks
        os.environ["HF_HUB_DISABLE_SYMLINKS_WARNING"] = "1"
        
        logger.debug("Ambiente configurado para modo OFFLINE")
    
    def _set_online_environment(self) -> None:
        """Configura variáveis de ambiente para modo online."""
        os.environ["TRANSFORMERS_OFFLINE"] = "0"
        os.environ["HF_HUB_OFFLINE"] = "0"
        os.environ["HF_DATASETS_OFFLINE"] = "0"
        
        # Ainda usa cache local, mas permite downloads
        models_path = os.path.abspath(self._config.offline.models_path)
        os.environ["HF_HOME"] = models_path
        os.environ["HF_HUB_CACHE"] = models_path
        os.environ["TRANSFORMERS_CACHE"] = models_path
        
        logger.debug("Ambiente configurado para modo ONLINE")
    
    def check_connectivity(self, force: bool = False) -> bool:
        """
        Testa conectividade com HuggingFace Hub.
        
        Args:
            force: Força novo teste mesmo se já foi testado
        
        Returns:
            bool: True se há conectividade
        """
        if self._connectivity_tested and not force:
            return self._is_connected
        
        self._connectivity_tested = True
        
        try:
            socket.setdefaulttimeout(self.connection_timeout)
            socket.create_connection(
                (self.HUGGINGFACE_HOST, self.HUGGINGFACE_PORT),
                timeout=self.connection_timeout
            )
            self._is_connected = True
            logger.debug(f"Conectividade OK: {self.HUGGINGFACE_HOST}")
        except (socket.timeout, socket.error, OSError) as e:
            self._is_connected = False
            logger.debug(f"Sem conectividade: {e}")
        
        return self._is_connected
    
    def should_use_local_model(self) -> bool:
        """
        Determina se deve usar modelo local.
        
        Returns:
            bool: True se deve usar modelo local
        """
        if self.is_offline:
            return True
        
        if self.is_online and self.allow_cloud_apis:
            return False
        
        if self.is_hybrid:
            if self._config.hybrid.prefer == "offline":
                return True
            # Prefere online, mas verifica conectividade
            return not self.check_connectivity()
        
        # Default: usa local
        return True
    
    def get_status_message(self) -> str:
        """Retorna mensagem de status para exibição."""
        mode_names = {
            OperationMode.OFFLINE: "OFFLINE (100% local)",
            OperationMode.ONLINE: "ONLINE (permite downloads)",
            OperationMode.HYBRID: "HYBRID (online com fallback)"
        }
        
        status = mode_names.get(self._effective_mode, "DESCONHECIDO")
        
        if self.is_hybrid:
            connectivity = "conectado" if self._is_connected else "sem conexão"
            status += f" [{connectivity}]"
        
        return status
    
    def get_cloud_status(self) -> str:
        """Retorna status das funcionalidades cloud."""
        if self.is_offline:
            return "Desabilitado (modo offline)"
        
        features = []
        if self.use_cloud_generation:
            features.append("Geração LLM")
        if self.use_cloud_embeddings:
            features.append("Embeddings")
        
        if features:
            return f"Habilitado: {', '.join(features)}"
        return "Disponível mas não habilitado"
    
    def __repr__(self) -> str:
        return (
            f"ModeManager(mode={self._effective_mode.value}, "
            f"downloads={self.allow_downloads}, "
            f"cloud_generation={self.use_cloud_generation}, "
            f"cloud_embeddings={self.use_cloud_embeddings})"
        )


# Singleton global
_mode_manager: Optional[ModeManager] = None


def get_mode_manager() -> ModeManager:
    """Obtém o gerenciador de modo global."""
    global _mode_manager
    if _mode_manager is None:
        _mode_manager = ModeManager()
    return _mode_manager


def init_mode_manager(
    config: Optional[SystemConfig] = None,
    cli_override: Optional[str] = None,
    allow_download_override: Optional[bool] = None,
    use_cloud_generation_override: Optional[bool] = None,
    use_cloud_embeddings_override: Optional[bool] = None
) -> ModeManager:
    """
    Inicializa o gerenciador de modo global.
    
    Esta função deve ser chamada uma vez no início da aplicação.
    
    Args:
        config: Configuração do sistema (do config.yaml)
        cli_override: Modo forçado via CLI (--online, --offline, --hybrid)
        allow_download_override: Override para permitir/bloquear downloads
        use_cloud_generation_override: Override para usar geração cloud (--use-cloud-generation)
        use_cloud_embeddings_override: Override para usar embeddings cloud (--use-cloud-embeddings)
    """
    global _mode_manager
    _mode_manager = ModeManager(
        config=config,
        cli_override=cli_override,
        allow_download_override=allow_download_override,
        use_cloud_generation_override=use_cloud_generation_override,
        use_cloud_embeddings_override=use_cloud_embeddings_override
    )
    _mode_manager.configure_environment()
    return _mode_manager


def reset_mode_manager() -> None:
    """Reseta o gerenciador de modo (útil para testes)."""
    global _mode_manager
    _mode_manager = None

