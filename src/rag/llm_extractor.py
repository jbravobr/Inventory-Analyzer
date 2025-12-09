"""
Extrator de dados via LLM.

Este módulo complementa a extração via regex, usando LLMs para:
- Dados que regex não captura (contexto, referências)
- Valores por extenso ("trinta mil reais")
- Nomes e entidades em contexto ambíguo

IMPORTANTE: Regex SEMPRE executa primeiro. LLM apenas COMPLEMENTA.
"""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from config.settings import get_settings, Settings, LLMExtractionConfig
from config.mode_manager import get_mode_manager, ModeManager
from rag.generator import CloudGenerator, GeneratedResponse

logger = logging.getLogger(__name__)


@dataclass
class LLMExtractedItem:
    """Item extraído pelo LLM."""
    
    name: str
    item_type: str
    value: Optional[float] = None
    quantity: Optional[float] = None
    raw_text: str = ""
    confidence: float = 0.85
    source: str = "llm"
    
    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "type": self.item_type,
            "value": self.value,
            "quantity": self.quantity,
            "confidence": self.confidence,
            "source": self.source
        }


@dataclass
class LLMExtractionResult:
    """Resultado da extração via LLM."""
    
    assets: List[LLMExtractedItem] = field(default_factory=list)
    quantities: List[LLMExtractedItem] = field(default_factory=list)
    names: List[str] = field(default_factory=list)
    dates: List[str] = field(default_factory=list)
    contextual_values: List[LLMExtractedItem] = field(default_factory=list)
    raw_response: str = ""
    tokens_used: int = 0


class LLMExtractor:
    """
    Extrator de dados via LLM (OpenAI, Anthropic).
    
    Usado como COMPLEMENTO ao regex quando:
    - llm_extraction.enabled = true
    - Modo é online ou hybrid com conectividade
    - use_cloud_generation = true
    
    Estratégias de merge:
    - regex_priority: Regex tem prioridade para valores numéricos (RECOMENDADO)
    - llm_priority: LLM tem prioridade (cuidado: menos preciso para números)
    - union: Une todos os resultados sem deduplicar
    """
    
    # Prompt para extração estruturada
    EXTRACTION_PROMPT = """Você é um assistente especializado em extração de dados de documentos financeiros brasileiros.

Analise o texto abaixo e extraia APENAS as informações que conseguir identificar com certeza.

TEXTO:
{context}

EXTRAIA em formato JSON:
{{
    "ativos": [
        {{"nome": "nome do ativo", "tipo": "ação|CRA|CRI|debênture|cota|CDB|LCI|LCA|titulo_publico", "ticker": "XXXX0 se houver"}}
    ],
    "valores": [
        {{"ativo": "nome do ativo", "valor": 0.00, "quantidade": 0, "texto_original": "trecho do texto"}}
    ],
    "pessoas": ["nome completo"],
    "datas": ["DD/MM/AAAA"],
    "valores_por_extenso": [
        {{"texto": "trinta mil reais", "valor_numerico": 30000.00}}
    ],
    "referencias_contextuais": [
        {{"referencia": "conforme item anterior", "valor_inferido": 0.00, "contexto": "explicação"}}
    ]
}}

REGRAS:
1. NÃO invente dados que não estão no texto
2. Para valores por extenso, converta para número (ex: "trinta mil" = 30000)
3. Para datas relativas, indique a referência (ex: "mês passado")
4. Retorne APENAS o JSON, sem explicações"""

    def __init__(
        self,
        settings: Optional[Settings] = None,
        mode_manager: Optional[ModeManager] = None,
        config: Optional[LLMExtractionConfig] = None
    ):
        """
        Inicializa o extrator LLM.
        
        Args:
            settings: Configurações do aplicativo
            mode_manager: Gerenciador de modo
            config: Configurações específicas de extração LLM
        """
        self._settings = settings or get_settings()
        self._mode_manager = mode_manager or get_mode_manager()
        self._config = config
        self._generator: Optional[CloudGenerator] = None
        self._initialized = False
        
        # Obtém config de extração LLM se não fornecido
        if self._config is None and hasattr(self._settings, 'rag'):
            self._config = self._settings.rag.generation.llm_extraction
    
    @property
    def is_available(self) -> bool:
        """Verifica se a extração LLM está disponível."""
        if not self._config or not self._config.enabled:
            return False
        
        if self._mode_manager.is_offline:
            return False
        
        return self._mode_manager.use_cloud_generation
    
    def initialize(self) -> bool:
        """
        Inicializa o gerador cloud.
        
        Returns:
            bool: True se inicializado com sucesso
        """
        if self._initialized:
            return True
        
        if not self.is_available:
            logger.debug("Extração LLM não disponível")
            return False
        
        try:
            provider = self._config.provider if self._config else "openai"
            self._generator = CloudGenerator(
                settings=self._settings,
                provider=provider,
                mode_manager=self._mode_manager
            )
            self._generator.initialize()
            self._initialized = True
            logger.info(f"LLMExtractor inicializado com provedor: {provider}")
            return True
        except Exception as e:
            logger.warning(f"Falha ao inicializar LLMExtractor: {e}")
            return False
    
    def extract(self, text: str) -> LLMExtractionResult:
        """
        Extrai dados do texto usando LLM.
        
        Args:
            text: Texto para extração
        
        Returns:
            LLMExtractionResult: Resultado da extração
        """
        result = LLMExtractionResult()
        
        if not self.initialize():
            logger.debug("LLMExtractor não inicializado, retornando resultado vazio")
            return result
        
        # Limita contexto para não exceder limites do modelo
        max_context = 4000
        if len(text) > max_context:
            text = text[:max_context]
        
        try:
            prompt = self.EXTRACTION_PROMPT.format(context=text)
            
            response = self._generator.generate(
                query="Extraia os dados estruturados do texto",
                context=text,
                system_prompt=prompt
            )
            
            result.raw_response = response.answer
            result.tokens_used = response.tokens_used or 0
            
            # Parse do JSON
            parsed = self._parse_json_response(response.answer)
            
            # Converte para objetos tipados
            result = self._convert_to_result(parsed, result)
            
        except Exception as e:
            logger.error(f"Erro na extração LLM: {e}")
            if self._config and self._config.fallback_to_regex:
                logger.info("Fallback para regex ativo")
        
        return result
    
    def _parse_json_response(self, response: str) -> dict:
        """Parse da resposta JSON do LLM."""
        try:
            # Tenta encontrar JSON na resposta
            json_match = re.search(r'\{[\s\S]*\}', response)
            if json_match:
                return json.loads(json_match.group())
            return {}
        except json.JSONDecodeError as e:
            logger.warning(f"Erro ao parsear JSON: {e}")
            return {}
    
    def _convert_to_result(
        self,
        parsed: dict,
        result: LLMExtractionResult
    ) -> LLMExtractionResult:
        """Converte dicionário parseado para resultado tipado."""
        
        # Ativos
        for asset in parsed.get("ativos", []):
            item = LLMExtractedItem(
                name=asset.get("nome", ""),
                item_type=asset.get("tipo", "outros"),
                source="llm"
            )
            if item.name:
                result.assets.append(item)
        
        # Valores
        for valor in parsed.get("valores", []):
            item = LLMExtractedItem(
                name=valor.get("ativo", ""),
                item_type="valor",
                value=self._parse_number(valor.get("valor")),
                quantity=self._parse_number(valor.get("quantidade")),
                raw_text=valor.get("texto_original", ""),
                source="llm"
            )
            if item.value or item.quantity:
                result.quantities.append(item)
        
        # Valores por extenso
        for extenso in parsed.get("valores_por_extenso", []):
            item = LLMExtractedItem(
                name=extenso.get("texto", ""),
                item_type="valor_extenso",
                value=self._parse_number(extenso.get("valor_numerico")),
                raw_text=extenso.get("texto", ""),
                source="llm_extenso"
            )
            if item.value:
                result.contextual_values.append(item)
        
        # Referências contextuais
        for ref in parsed.get("referencias_contextuais", []):
            item = LLMExtractedItem(
                name=ref.get("referencia", ""),
                item_type="referencia",
                value=self._parse_number(ref.get("valor_inferido")),
                raw_text=ref.get("contexto", ""),
                source="llm_contexto"
            )
            if item.value:
                result.contextual_values.append(item)
        
        # Pessoas
        result.names = parsed.get("pessoas", [])
        
        # Datas
        result.dates = parsed.get("datas", [])
        
        return result
    
    def _parse_number(self, value: Any) -> Optional[float]:
        """Parse de valor numérico."""
        if value is None:
            return None
        try:
            if isinstance(value, (int, float)):
                return float(value)
            if isinstance(value, str):
                # Remove formatação brasileira
                clean = value.replace(".", "").replace(",", ".")
                clean = re.sub(r'[^\d.-]', '', clean)
                return float(clean) if clean else None
        except (ValueError, TypeError):
            return None
        return None


class ExtractionMerger:
    """
    Mescla resultados de extração Regex e LLM.
    
    Estratégias:
    - regex_priority: Regex tem prioridade para valores numéricos
    - llm_priority: LLM tem prioridade
    - union: Une tudo sem priorização
    """
    
    def __init__(self, strategy: str = "regex_priority"):
        """
        Inicializa o merger.
        
        Args:
            strategy: Estratégia de merge (regex_priority, llm_priority, union)
        """
        self.strategy = strategy
    
    def merge_assets(
        self,
        regex_assets: List[Any],
        llm_assets: List[LLMExtractedItem]
    ) -> List[Any]:
        """
        Mescla ativos de regex e LLM.
        
        Args:
            regex_assets: Ativos extraídos via regex
            llm_assets: Ativos extraídos via LLM
        
        Returns:
            Lista mesclada de ativos
        """
        if not llm_assets:
            return regex_assets
        
        if not regex_assets:
            return llm_assets
        
        # Cria índice de ativos regex por nome normalizado
        regex_names = set()
        for asset in regex_assets:
            name = getattr(asset, 'name', '') or getattr(asset, 'ticker', '') or ''
            regex_names.add(self._normalize(name))
        
        # Adiciona ativos LLM que não foram encontrados pelo regex
        result = list(regex_assets)
        
        for llm_asset in llm_assets:
            norm_name = self._normalize(llm_asset.name)
            if norm_name not in regex_names:
                # Converte LLMExtractedItem para o tipo esperado
                result.append(llm_asset)
                logger.debug(f"LLM adicionou ativo: {llm_asset.name}")
        
        return result
    
    def merge_quantities(
        self,
        regex_quantities: List[Any],
        llm_quantities: List[LLMExtractedItem]
    ) -> List[Any]:
        """
        Mescla quantidades de regex e LLM.
        
        IMPORTANTE: Para valores numéricos, regex tem PRIORIDADE
        pois é mais preciso para padrões estruturados.
        
        LLM adiciona valores que regex não capturou.
        """
        if not llm_quantities:
            return regex_quantities
        
        if not regex_quantities:
            return llm_quantities
        
        # Cria índice de valores regex
        regex_index = {}
        for qty in regex_quantities:
            asset = getattr(qty, 'asset', None)
            name = getattr(asset, 'name', '') if asset else ''
            norm_name = self._normalize(name)
            if norm_name:
                regex_index[norm_name] = qty
        
        result = list(regex_quantities)
        
        for llm_qty in llm_quantities:
            norm_name = self._normalize(llm_qty.name)
            
            if self.strategy == "regex_priority":
                # Só adiciona se não existe no regex
                if norm_name not in regex_index:
                    result.append(llm_qty)
                    logger.debug(f"LLM adicionou valor: {llm_qty.name} = {llm_qty.value}")
            
            elif self.strategy == "llm_priority":
                # LLM sobrescreve
                if norm_name in regex_index:
                    # Remove o regex
                    result = [q for q in result if self._normalize(
                        getattr(getattr(q, 'asset', None), 'name', '')
                    ) != norm_name]
                result.append(llm_qty)
            
            else:  # union
                result.append(llm_qty)
        
        return result
    
    def _normalize(self, text: str) -> str:
        """Normaliza texto para comparação."""
        if not text:
            return ""
        return re.sub(r'\s+', ' ', text.lower().strip())


def get_llm_extractor(
    settings: Optional[Settings] = None,
    mode_manager: Optional[ModeManager] = None
) -> Optional[LLMExtractor]:
    """
    Factory para obter extrator LLM se disponível.
    
    Returns:
        LLMExtractor ou None se não disponível
    """
    settings = settings or get_settings()
    mode_mgr = mode_manager or get_mode_manager()
    
    extractor = LLMExtractor(settings=settings, mode_manager=mode_mgr)
    
    if extractor.is_available:
        return extractor
    
    return None

