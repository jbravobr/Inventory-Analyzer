"""
Analisador de Atas de Reunião de Quotistas.

Extrai informações sobre ativos envolvidos e suas respectivas quantidades.

Estratégia de Extração:
1. REGEX (sempre executa) - Extração precisa de padrões estruturados
2. LLM (opcional) - Complementa regex para dados contextuais

O LLM só é usado se:
- generate_answers: true
- llm_extraction.enabled: true
- Modo online ou hybrid com use_cloud_generation: true
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple

from rag.rag_pipeline import RAGPipeline, RAGConfig
from rag.llm_extractor import get_llm_extractor, ExtractionMerger, LLMExtractor
from core.pdf_reader import PDFReader
from core.ocr_extractor import OCRExtractor
from core.ocr_cache import get_ocr_cache
from config.settings import get_settings
from config.mode_manager import get_mode_manager

logger = logging.getLogger(__name__)


@dataclass
class Asset:
    """Representa um ativo/valor mobiliário."""
    name: str
    asset_type: str  # ação, CRA, CRI, debênture, cota, CDB, etc.
    ticker: Optional[str] = None
    issuer: Optional[str] = None  # emissor/emissora
    series: Optional[str] = None  # série
    custodian: Optional[str] = None  # custodiante
    
    def to_dict(self) -> dict:
        return {
            "nome": self.name,
            "tipo": self.asset_type,
            "ticker": self.ticker,
            "emissor": self.issuer,
            "serie": self.series,
            "custodiante": self.custodian
        }


@dataclass
class AssetQuantity:
    """Representa a quantidade/volume de um ativo."""
    asset: Asset
    quantity: Optional[float] = None  # quantidade/número de unidades
    unit_price: Optional[float] = None  # preço unitário
    total_value: Optional[float] = None  # valor total
    nominal_value: Optional[float] = None  # valor nominal/face
    issue_date: Optional[str] = None  # data emissão
    maturity_date: Optional[str] = None  # data vencimento
    raw_text: str = ""  # texto original onde foi encontrado
    
    def to_dict(self) -> dict:
        return {
            "ativo": self.asset.to_dict(),
            "quantidade": self.quantity,
            "preco_unitario": self.unit_price,
            "valor_total": self.total_value,
            "valor_nominal": self.nominal_value,
            "data_emissao": self.issue_date,
            "data_vencimento": self.maturity_date
        }


@dataclass
class MeetingMinutesResult:
    """Resultado completo da análise de Ata de Reunião."""
    
    # Informações básicas do documento
    fund_name: Optional[str] = None
    fund_cnpj: Optional[str] = None
    administrator: Optional[str] = None
    manager: Optional[str] = None
    meeting_date: Optional[str] = None
    
    # Cláusula A - Ativos Identificados
    assets: List[Asset] = field(default_factory=list)
    assets_raw_text: str = ""
    assets_pages: List[int] = field(default_factory=list)
    
    # Cláusula B - Quantidades dos Ativos
    asset_quantities: List[AssetQuantity] = field(default_factory=list)
    quantities_raw_text: str = ""
    quantities_pages: List[int] = field(default_factory=list)
    
    # Informações complementares
    participants: List[str] = field(default_factory=list)
    deliberations: List[str] = field(default_factory=list)
    
    # Metadados
    total_pages: int = 0
    processing_time: float = 0.0
    confidence_scores: Dict[str, float] = field(default_factory=dict)
    
    def to_dict(self) -> dict:
        return {
            "informacoes_gerais": {
                "nome_fundo": self.fund_name,
                "cnpj": self.fund_cnpj,
                "administrador": self.administrator,
                "gestor": self.manager,
                "data_reuniao": self.meeting_date,
                "total_paginas": self.total_pages
            },
            "clausula_a_ativos": {
                "ativos": [a.to_dict() for a in self.assets],
                "quantidade": len(self.assets),
                "paginas": self.assets_pages,
                "confianca": self.confidence_scores.get("assets", 0)
            },
            "clausula_b_quantidades": {
                "detalhamento": [q.to_dict() for q in self.asset_quantities],
                "quantidade": len(self.asset_quantities),
                "paginas": self.quantities_pages,
                "confianca": self.confidence_scores.get("quantities", 0)
            },
            "informacoes_complementares": {
                "participantes": self.participants,
                "deliberacoes": self.deliberations
            },
            "tempo_processamento": self.processing_time
        }


class MeetingMinutesAnalyzer:
    """
    Analisador de Atas de Reunião de Quotistas.
    
    Utiliza RAG para extrair informações específicas sobre:
    - Ativos envolvidos (ações, CRA, CRI, debêntures, cotas, CDB, etc.)
    - Quantidade e valores dos ativos
    """
    
    # Cores para highlight (RGB)
    HIGHLIGHT_COLORS = {
        "assets": (255, 200, 0),        # Laranja - Ativos
        "quantities": (0, 191, 255),     # Azul claro - Quantidades
        "fund_info": (0, 255, 0),        # Verde - Info do Fundo
        "deliberations": (255, 182, 193) # Rosa - Deliberações
    }
    
    # Padrões REGEX específicos para cada tipo de ativo (evita falsos positivos)
    # Usam word boundaries \b para não capturar partes de palavras
    ASSET_PATTERNS = {
        "ação": [
            # Padrões específicos para ações (não captura "convocação", "publicação", etc.)
            r'\b(\d+[\d.,]*)\s*(?:ações?|papéis?)\s+(?:(?:ordinárias?|preferenciais?|ON|PN)\s+)?(?:da?\s+)?([A-Z][A-Za-zÀ-ú\s]+?)(?:\s*[-–]\s*|\s*\()?([A-Z]{4}\d{1,2})?',
            r'\b([A-Z]{4}\d{1,2})\b',  # Tickers de ações brasileiras (PETR4, VALE3, etc.)
            r'\bações?\s+([A-Z]{4}\d{1,2})\b',
            r'\bações?\s+(?:da|do|de)\s+([A-Z][A-Za-zÀ-ú\s]+)',
        ],
        "CRA": [
            # CRA específico - não captura "democracia", etc.
            r'\bCRA[s]?\b(?:\s+(?:da|do|de)\s+)?([A-Za-zÀ-ú\s]+)?',
            r'\bCertificados?\s+de\s+Recebíveis?\s+do\s+Agronegócio\b',
        ],
        "CRI": [
            # CRI específico - não captura "descrição", "escrita", etc.
            r'\bCRI[s]?\b(?:\s+(?:da|do|de)\s+)?([A-Za-zÀ-ú\s]+)?',
            r'\bCertificados?\s+de\s+Recebíveis?\s+Imobiliários?\b',
        ],
        "debênture": [
            r'\bdebêntures?\b(?:\s+(?:da|do|de)\s+)?([A-Za-zÀ-ú\s]+)?',
            r'\bdebentures?\b(?:\s+(?:da|do|de)\s+)?([A-Za-zÀ-ú\s]+)?',
            r'\b(\d+)\s*debêntures?\b',
        ],
        "cota_fundo": [
            # Cotas de fundos - padrões específicos
            r'\bcotas?\s+(?:do|da|de)\s+(?:fundo\s+)?([A-Za-zÀ-ú\s]+)',
            r'\b(FII|FIM|FIC|FICFI[AM]|ETF)\s*[:\s]*([A-Za-zÀ-ú\s]+)?',
            r'\bfundo\s+(?:de\s+)?(?:investimento\s+)?([A-Za-zÀ-ú\s]+)',
        ],
        "CDB": [
            r'\bCDB[s]?\b(?:\s+(?:da|do|de)\s+)?([A-Za-zÀ-ú\s]+)?',
            r'\bCertificados?\s+de\s+Depósitos?\s+Bancários?\b',
        ],
        "LCI": [
            r'\bLCI[s]?\b(?:\s+(?:da|do|de)\s+)?([A-Za-zÀ-ú\s]+)?',
            r'\bLetras?\s+de\s+Créditos?\s+Imobiliários?\b',
        ],
        "LCA": [
            r'\bLCA[s]?\b(?:\s+(?:da|do|de)\s+)?([A-Za-zÀ-ú\s]+)?',
            r'\bLetras?\s+de\s+Créditos?\s+do\s+Agronegócio\b',
        ],
        "titulo_publico": [
            r'\bTesouro\s+(?:Direto|Selic|IPCA|Prefixado)\b[^,\n]*',
            r'\bNTN[-\s]?[BF]\b',
            r'\bLFT\b',
            r'\bLTN\b',
        ],
    }
    
    # Padrões para extrair valores monetários associados a ativos
    VALUE_PATTERNS = [
        r'R\$\s*([\d.,]+(?:\s*(?:mil|milhão|milhões|bi|bilhão|bilhões))?)',
        r'(?:valor|montante|total)[:\s]+R?\$?\s*([\d.,]+)',
        r'(?:no valor de|equivalente a|correspondente a)\s*R?\$?\s*([\d.,]+)',
    ]
    
    # Padrões para extrair quantidades
    QUANTITY_PATTERNS = [
        r'(\d+[\d.,]*)\s*(?:cotas?|ações?|unidades?|títulos?|papéis?)',
        r'(?:quantidade|volume|total)\s*(?:de)?[:\s]+(\d+[\d.,]*)',
        r'(\d+[\d.,]*)\s*(?:\(\s*[\w\s]+\s*\))?\s*(?:cotas?|ações?)',
    ]
    
    # Padrões para identificar beneficiários/pessoas
    BENEFICIARY_PATTERNS = [
        r'(?:beneficiário|titular|quotista|cotista|herdeiro)[:\s]+([A-ZÁÉÍÓÚÂÊÎÔÛÃÕÇ][A-Za-záéíóúâêîôûãõç\s]+)',
        r'(?:em nome de|para|destinado a)[:\s]+([A-ZÁÉÍÓÚÂÊÎÔÛÃÕÇ][A-Za-záéíóúâêîôûãõç\s]+)',
        r'([A-ZÁÉÍÓÚÂÊÎÔÛÃÕÇ][A-Za-záéíóúâêîôûãõç\s]+?)(?:\s*[-–]\s*CPF|\s*,\s*(?:brasileiro|nascido))',
    ]
    
    def __init__(self, config: Optional[RAGConfig] = None):
        """
        Inicializa o analisador.
        
        Args:
            config: Configuração do pipeline RAG.
        """
        self.config = config or RAGConfig(
            mode="local",
            chunk_size=400,
            chunk_overlap=100,
            top_k=10,
            use_hybrid_search=True,
            generate_answers=False  # Usa apenas retrieval por padrão
        )
        self.rag = RAGPipeline(self.config)
        self.reader = PDFReader()
        self.ocr = OCRExtractor()
        self._document = None
        self._full_text = ""
        
        # Inicializa extrator LLM se disponível
        self._llm_extractor: Optional[LLMExtractor] = None
        self._merger: Optional[ExtractionMerger] = None
        self._init_llm_extractor()
    
    def _init_llm_extractor(self) -> None:
        """
        Inicializa o extrator LLM se disponível e configurado.
        
        O LLM é usado como COMPLEMENTO ao regex quando:
        - llm_extraction.enabled = true no config.yaml
        - Modo é online ou hybrid
        - use_cloud_generation = true
        """
        try:
            settings = get_settings()
            mode_mgr = get_mode_manager()
            
            # Verifica se extração LLM está habilitada
            llm_config = settings.rag.generation.llm_extraction
            
            if llm_config.enabled and mode_mgr.use_cloud_generation:
                self._llm_extractor = get_llm_extractor(settings, mode_mgr)
                
                if self._llm_extractor:
                    self._merger = ExtractionMerger(strategy=llm_config.merge_strategy)
                    logger.info(
                        f"Extração LLM habilitada (provider: {llm_config.provider}, "
                        f"merge: {llm_config.merge_strategy})"
                    )
                else:
                    logger.debug("LLMExtractor não disponível")
            else:
                logger.debug(
                    f"Extração LLM desabilitada "
                    f"(enabled={llm_config.enabled}, "
                    f"cloud_gen={mode_mgr.use_cloud_generation if mode_mgr else 'N/A'})"
                )
        except Exception as e:
            logger.warning(f"Erro ao inicializar extração LLM: {e}")
            self._llm_extractor = None
    
    def analyze(self, pdf_path: Path) -> MeetingMinutesResult:
        """
        Analisa uma ata de reunião de quotistas.
        
        Args:
            pdf_path: Caminho para o PDF.
        
        Returns:
            MeetingMinutesResult: Resultado completo da análise.
        """
        import time
        start_time = time.time()
        
        logger.info(f"Iniciando análise de ata de reunião: {pdf_path}")
        
        # Lê o PDF
        self._document = self.reader.read(pdf_path)
        
        # Verifica cache de OCR
        ocr_cache = get_ocr_cache()
        cached_doc = ocr_cache.get(pdf_path)
        
        if cached_doc:
            logger.info(f"Usando cache de OCR para: {pdf_path.name}")
            # Preenche documento com texto do cache
            for i, page in enumerate(self._document.pages):
                if i < len(cached_doc.pages):
                    page.text = cached_doc.pages[i].get("text", "")
        else:
            logger.info(f"Extraindo texto via OCR: {pdf_path.name}")
            ocr_start = time.time()
            self.ocr.extract(self._document)
            ocr_time = time.time() - ocr_start
            
            # Salva no cache
            pages_data = [
                {"number": p.number, "text": p.text}
                for p in self._document.pages
            ]
            ocr_cache.save(pdf_path, pages_data, ocr_time)
        
        # Indexa no RAG
        self.rag.index_document(self._document)
        
        # Concatena texto completo
        self._full_text = "\n\n".join([
            page.text for page in self._document.pages if page.text
        ])
        
        result = MeetingMinutesResult()
        result.total_pages = len(self._document.pages)
        
        # Analisa cada cláusula
        self._analyze_assets(result)
        self._analyze_quantities(result)
        self._analyze_general_info(result)
        
        result.processing_time = time.time() - start_time
        
        logger.info(f"Análise concluída em {result.processing_time:.2f}s")
        
        return result
    
    def _analyze_assets(self, result: MeetingMinutesResult) -> None:
        """Analisa e extrai ativos mencionados (Cláusula A)."""
        logger.info("Analisando ativos envolvidos...")
        
        queries = [
            "Quais são os ativos mencionados na ata?",
            "Liste todas as ações, CRA, CRI, debêntures mencionadas",
            "Quais valores mobiliários são mencionados?",
            "Identifique os títulos e cotas de fundos",
            "Quais CDB, LCI, LCA ou títulos públicos são mencionados?"
        ]
        
        all_contexts = []
        all_pages = set()
        
        for query in queries:
            response = self.rag.query(query)
            if response.retrieval_result and response.retrieval_result.chunks:
                for chunk in response.retrieval_result.chunks:
                    all_contexts.append(chunk.text)
                    all_pages.add(chunk.page_number)
        
        result.assets_raw_text = "\n---\n".join(all_contexts)
        result.assets_pages = sorted(list(all_pages))
        
        # ETAPA 1: Extrai ativos via REGEX (sempre executa)
        regex_assets = self._extract_assets_from_text(result.assets_raw_text)
        logger.info(f"Regex extraiu {len(regex_assets)} ativos")
        
        # ETAPA 2: Extrai via LLM se disponível (complementa regex)
        if self._llm_extractor and self._merger:
            try:
                llm_result = self._llm_extractor.extract(result.assets_raw_text)
                if llm_result.assets:
                    logger.info(f"LLM extraiu {len(llm_result.assets)} ativos adicionais")
                    # ETAPA 3: Merge dos resultados
                    result.assets = self._merger.merge_assets(regex_assets, llm_result.assets)
                    logger.info(f"Total após merge: {len(result.assets)} ativos")
                else:
                    result.assets = regex_assets
            except Exception as e:
                logger.warning(f"Erro na extração LLM de ativos: {e}")
                result.assets = regex_assets
        else:
            result.assets = regex_assets
        
        result.confidence_scores["assets"] = 0.7 if result.assets else 0.3
    
    def _analyze_quantities(self, result: MeetingMinutesResult) -> None:
        """Analisa e extrai quantidades dos ativos (Cláusula B)."""
        logger.info("Analisando quantidades dos ativos...")
        
        queries = [
            "Qual a quantidade de cada ativo?",
            "Qual o volume total a ser distribuído?",
            "Identifique os valores e quantidades mencionados",
            "Qual o valor nominal dos títulos?",
            "Qual o número total de ações ou cotas?"
        ]
        
        all_contexts = []
        all_pages = set()
        
        for query in queries:
            response = self.rag.query(query)
            if response.retrieval_result and response.retrieval_result.chunks:
                for chunk in response.retrieval_result.chunks:
                    all_contexts.append(chunk.text)
                    all_pages.add(chunk.page_number)
        
        result.quantities_raw_text = "\n---\n".join(all_contexts)
        result.quantities_pages = sorted(list(all_pages))
        
        # ETAPA 1: Extrai quantidades via REGEX (sempre executa)
        regex_quantities = self._extract_quantities_from_text(
            result.quantities_raw_text,
            result.assets
        )
        logger.info(f"Regex extraiu {len(regex_quantities)} quantidades")
        
        # ETAPA 2: Extrai via LLM se disponível (complementa regex)
        if self._llm_extractor and self._merger:
            try:
                llm_result = self._llm_extractor.extract(result.quantities_raw_text)
                llm_quantities = llm_result.quantities + llm_result.contextual_values
                
                if llm_quantities:
                    logger.info(f"LLM extraiu {len(llm_quantities)} valores adicionais")
                    # ETAPA 3: Merge dos resultados
                    result.asset_quantities = self._merger.merge_quantities(
                        regex_quantities, llm_quantities
                    )
                    logger.info(f"Total após merge: {len(result.asset_quantities)} quantidades")
                else:
                    result.asset_quantities = regex_quantities
            except Exception as e:
                logger.warning(f"Erro na extração LLM de quantidades: {e}")
                result.asset_quantities = regex_quantities
        else:
            result.asset_quantities = regex_quantities
        
        result.confidence_scores["quantities"] = 0.7 if result.asset_quantities else 0.3
    
    def _analyze_general_info(self, result: MeetingMinutesResult) -> None:
        """Extrai informações gerais do documento."""
        logger.info("Extraindo informações gerais...")
        
        # Busca nome do fundo
        response = self.rag.query("Qual o nome do fundo ou veículo de investimento?")
        if response.retrieval_result and response.retrieval_result.chunks:
            text = response.retrieval_result.chunks[0].text
            patterns = [
                r"(?:fundo|fii|fim)[:\s]+([A-ZÁÉÍÓÚÂÊÎÔÛÃÕÇ][A-Za-záéíóúâêîôûãõç\s]+)",
                r"([A-Z][A-Z\s]+(?:FII|FIM|FIC|FUNDO)[A-Z\s]*)"
            ]
            for pattern in patterns:
                match = re.search(pattern, text, re.IGNORECASE)
                if match:
                    result.fund_name = match.group(1).strip()
                    break
        
        # Busca CNPJ
        response = self.rag.query("Qual o CNPJ do fundo?")
        if response.retrieval_result and response.retrieval_result.chunks:
            text = response.retrieval_result.chunks[0].text
            cnpj_pattern = r"\d{2}[.\s]?\d{3}[.\s]?\d{3}[/\s]?\d{4}[-\s]?\d{2}"
            match = re.search(cnpj_pattern, text)
            if match:
                result.fund_cnpj = match.group()
        
        # Busca administrador
        response = self.rag.query("Qual o administrador do fundo?")
        if response.retrieval_result and response.retrieval_result.chunks:
            text = response.retrieval_result.chunks[0].text
            patterns = [
                r"administrad[oa][:\s]+([A-ZÁÉÍÓÚÂÊÎÔÛÃÕÇ][A-Za-záéíóúâêîôûãõç\s]+)",
                r"administração[:\s]+([A-ZÁÉÍÓÚÂÊÎÔÛÃÕÇ][A-Za-záéíóúâêîôûãõç\s]+)"
            ]
            for pattern in patterns:
                match = re.search(pattern, text, re.IGNORECASE)
                if match:
                    result.administrator = match.group(1).strip()[:100]
                    break
        
        # Busca data da reunião
        response = self.rag.query("Qual a data da reunião ou assembleia?")
        if response.retrieval_result and response.retrieval_result.chunks:
            text = response.retrieval_result.chunks[0].text
            date_pattern = r"\d{1,2}[/.-]\d{1,2}[/.-]\d{2,4}"
            match = re.search(date_pattern, text)
            if match:
                result.meeting_date = match.group()
    
    def _extract_assets_from_text(self, text: str) -> List[Asset]:
        """Extrai lista de ativos do texto usando padrões específicos."""
        assets = []
        seen_assets = set()
        
        # Procura cada tipo de ativo usando padrões REGEX específicos
        for asset_type, patterns in self.ASSET_PATTERNS.items():
            for pattern in patterns:
                try:
                    matches = re.finditer(pattern, text, re.IGNORECASE | re.MULTILINE)
                    
                    for match in matches:
                        full_match = match.group(0).strip()
                        
                        # Ignora matches muito curtos ou que são claramente errados
                        if len(full_match) < 3:
                            continue
                        
                        # Normaliza para evitar duplicatas
                        normalized = full_match.lower()[:50]
                        if normalized in seen_assets:
                            continue
                        
                        # Validação adicional para evitar falsos positivos
                        if not self._is_valid_asset(full_match, asset_type):
                            continue
                        
                        seen_assets.add(normalized)
                        
                        asset = Asset(
                            name=full_match[:200],
                            asset_type=asset_type
                        )
                        
                        # Extrai ticker se disponível nos grupos
                        if match.lastindex and match.lastindex >= 1:
                            potential_ticker = match.group(1) if match.group(1) else None
                            if potential_ticker and re.match(r'^[A-Z]{4}\d{1,2}$', potential_ticker):
                                asset.ticker = potential_ticker
                        
                        # Busca ticker separadamente
                        if not asset.ticker:
                            ticker_match = re.search(r'\b([A-Z]{4}\d{1,2})\b', full_match)
                            if ticker_match:
                                asset.ticker = ticker_match.group(1)
                        
                        # Extrai emissor
                        issuer_match = re.search(
                            r'(?:emiss[ãa]o|emitid[oa]|emissora?|da|do)[:\s]+([A-ZÁÉÍÓÚÂÊÎÔÛÃÕÇ][A-Za-záéíóúâêîôûãõç\s]{2,50})',
                            full_match, re.IGNORECASE
                        )
                        if issuer_match:
                            issuer = issuer_match.group(1).strip()
                            # Filtra emissores que são palavras comuns
                            if issuer.lower() not in ['de', 'da', 'do', 'que', 'para', 'com']:
                                asset.issuer = issuer[:100]
                        
                        # Extrai série
                        series_match = re.search(
                            r'(?:série|series|sr\.?)[:\s]+([A-Z0-9]+)',
                            full_match, re.IGNORECASE
                        )
                        if series_match:
                            asset.series = series_match.group(1)
                        
                        assets.append(asset)
                        
                except re.error as e:
                    logger.warning(f"Erro no padrão regex {pattern}: {e}")
                    continue
        
        return assets
    
    def _is_valid_asset(self, text: str, asset_type: str) -> bool:
        """Valida se o texto é realmente um ativo válido."""
        text_lower = text.lower()
        
        # Lista de palavras que indicam falsos positivos
        false_positives = {
            "ação": [
                "convocação", "publicação", "declaração", "deliberação",
                "manifestação", "certificação", "autenticação", "comunicação",
                "votação", "notificação", "ratificação", "retificação",
                "identificação", "qualificação", "participação", "apresentação",
                "descrição", "inscrição", "prescrição", "transcrição",
                "atribuição", "distribuição", "contribuição", "constituição",
            ],
            "CRI": [
                "descrição", "inscrição", "prescrição", "transcrição",
                "escrita", "escritura", "manuscrito", "escrito",
            ],
            "cota_fundo": [
                "certificamos", "certifico", "verificamos", "verifico",
                "fica sujeito", "ficamos",
            ],
        }
        
        # Verifica se o texto contém palavras que indicam falsos positivos
        if asset_type in false_positives:
            for fp in false_positives[asset_type]:
                if fp in text_lower:
                    return False
        
        # Validações específicas por tipo
        if asset_type == "ação":
            # Ação deve estar em contexto financeiro
            financial_context = [
                "r$", "valor", "quantidade", "cotas", "ticker",
                "bolsa", "b3", "bovespa", "capital", "patrimônio",
                "resgate", "aplicação", "investimento", "carteira"
            ]
            has_financial_context = any(ctx in text_lower for ctx in financial_context)
            # Se o texto é curto, precisa ter contexto financeiro
            if len(text) < 30 and not has_financial_context:
                # Verifica se parece ser um ticker
                if not re.search(r'\b[A-Z]{4}\d{1,2}\b', text):
                    return False
        
        return True
    
    def _extract_quantities_from_text(
        self,
        text: str,
        assets: List[Asset]
    ) -> List[AssetQuantity]:
        """Extrai quantidades dos ativos do texto com padrões melhorados."""
        quantities = []
        seen_values = set()  # Para evitar duplicatas por valor+nome
        
        # PADRÃO 1: Tickers com formato completo
        # Exemplo: "AMER3 — Quantidade Total: 36 unid. Valor unitário R$ 6,14 — Valor Total: R$ 221,04."
        # ou: "MGLU3 — Quantidade Total: 862 unid. — Valor R$ 7.137,36."
        ticker_pattern = r'([A-Z]{4,6}\d{1,2})\s*[—–-]\s*Quantidade\s+Total[:\s]*\s*([\d.,]+)\s*unid\.?\s*(?:Valor\s+[Uu]nit[áa]rio\s*R?\$?\s*([\d.,]+))?\s*[—–-]?\s*Valor\s*(?:Total)?[:\s]*\s*R?\$?\s*([\d.,]+)'
        
        for match in re.finditer(ticker_pattern, text, re.IGNORECASE):
            ticker = match.group(1).upper()
            quantity_str = match.group(2)
            unit_price_str = match.group(3)
            total_value_str = match.group(4)
            
            try:
                quantity = self._parse_brazilian_number(quantity_str)
                total_value = self._parse_brazilian_number(total_value_str)
                unit_price = self._parse_brazilian_number(unit_price_str) if unit_price_str else None
                
                # Ignora valores muito pequenos
                if total_value < 1:
                    continue
                
                # Cria chave única: ticker + valor total (para evitar duplicatas)
                unique_key = f"{ticker}_{total_value:.2f}"
                if unique_key in seen_values:
                    continue
                seen_values.add(unique_key)
                
                # Determina o tipo pelo ticker
                asset_type = self._determine_asset_type_by_ticker(ticker)
                
                asset = Asset(
                    name=ticker,
                    asset_type=asset_type,
                    ticker=ticker
                )
                
                quantity_info = AssetQuantity(
                    asset=asset,
                    quantity=quantity,
                    unit_price=unit_price,
                    total_value=total_value,
                    raw_text=match.group(0)
                )
                
                quantities.append(quantity_info)
                
            except ValueError:
                continue
        
        # PADRÃO 2: Nomes de fundos com valores
        # Exemplo: "FIM CRPR: R$ 224.567,89" ou "Tesouro Selic: R$ 3.456,78"
        asset_value_pattern = r'([A-Z][A-Za-zÀ-ú\s]{2,30}?):\s*R\$\s*([\d.,]+)'
        
        for match in re.finditer(asset_value_pattern, text):
            asset_name = match.group(1).strip()
            value_str = match.group(2)
            
            try:
                value = self._parse_brazilian_number(value_str)
                
                # Ignora valores muito pequenos
                if value < 10:
                    continue
                
                # Ignora nomes genéricos
                if asset_name.lower().strip() in ['valor', 'valor total', 'total', 'soma', 'quantidade']:
                    continue
                
                # Ignora se já tem ticker extraído com mesmo valor aproximado
                unique_key = f"{asset_name.lower()[:20]}_{value:.2f}"
                if unique_key in seen_values:
                    continue
                seen_values.add(unique_key)
                
                asset_type = self._determine_asset_type(asset_name)
                
                asset = Asset(name=asset_name, asset_type=asset_type)
                
                quantity_info = AssetQuantity(
                    asset=asset,
                    total_value=value,
                    raw_text=match.group(0)
                )
                
                quantities.append(quantity_info)
                
            except ValueError:
                continue
        
        return quantities
    
    def _determine_asset_type_by_ticker(self, ticker: str) -> str:
        """Determina o tipo de ativo pelo formato do ticker."""
        ticker = ticker.upper()
        
        # BDRs terminam em 31, 32, 33, 34, 35
        if ticker[-2:] in ['31', '32', '33', '34', '35']:
            return "BDR"
        
        # ETFs terminam em 11
        if ticker.endswith('11'):
            return "ETF"
        
        # Ações ordinárias terminam em 3
        if ticker.endswith('3'):
            return "ação"
        
        # Ações preferenciais terminam em 4
        if ticker.endswith('4'):
            return "ação"
        
        # Units terminam em 11 (já tratado como ETF) ou sem número
        # FIIs terminam em 11 (também já tratado)
        
        return "ação"  # Default para tickers
    
    def _parse_brazilian_number(self, value_str: str) -> float:
        """Converte string de número brasileiro para float."""
        # Remove espaços
        value_str = value_str.strip()
        
        # Trata números no formato brasileiro: 1.234.567,89
        # Conta quantos pontos e vírgulas existem
        dots = value_str.count('.')
        commas = value_str.count(',')
        
        if commas == 1 and dots >= 1:
            # Formato brasileiro: 1.234.567,89
            value_str = value_str.replace('.', '').replace(',', '.')
        elif commas == 1 and dots == 0:
            # Pode ser 1234,56 (brasileiro) ou 1,234 (americano)
            # Se tem 2 dígitos depois da vírgula, é brasileiro
            parts = value_str.split(',')
            if len(parts[1]) == 2:
                value_str = value_str.replace(',', '.')
            else:
                # Provavelmente é americano (milhar)
                value_str = value_str.replace(',', '')
        elif dots == 1 and commas == 0:
            # Pode ser 1234.56 (americano) ou 1.234 (brasileiro milhar)
            parts = value_str.split('.')
            if len(parts[1]) == 3:
                # É milhar brasileiro
                value_str = value_str.replace('.', '')
        else:
            # Remove todos os pontos (milhares)
            value_str = value_str.replace('.', '').replace(',', '.')
        
        return float(value_str)
    
    def _determine_asset_type(self, name: str) -> str:
        """Determina o tipo de ativo pelo nome."""
        name_upper = name.upper()
        
        # Fundos - padrões comuns
        if any(x in name_upper for x in ['FIM', 'FIC', 'FICFI', 'FII', 'TNB', 'INSTITUCIONAL', 'MULTIMERCADO']):
            return "cota_fundo"
        elif 'TESOURO' in name_upper or 'NTN' in name_upper or 'LFT' in name_upper:
            return "titulo_publico"
        elif 'CRA' in name_upper:
            return "CRA"
        elif 'CRI' in name_upper:
            return "CRI"
        elif 'CDB' in name_upper:
            return "CDB"
        elif 'LCI' in name_upper:
            return "LCI"
        elif 'LCA' in name_upper:
            return "LCA"
        elif 'DEBENTURE' in name_upper or 'DEBÊNTURE' in name_upper:
            return "debênture"
        elif any(x in name_upper for x in ['AÇÃO', 'AÇÕES', 'ACOES']):
            return "ação"
        else:
            return "outros"
    
    def get_highlights(self, result: MeetingMinutesResult) -> Dict[str, List[Tuple[str, List[int]]]]:
        """
        Retorna os textos e páginas para highlight.
        
        Returns:
            Dict com categoria -> [(texto, páginas)]
        """
        highlights = {
            "assets": [],
            "quantities": [],
            "fund_info": [],
            "deliberations": []
        }
        
        # Ativos
        for asset in result.assets:
            if asset.name:
                highlights["assets"].append((asset.name, result.assets_pages))
            if asset.ticker:
                highlights["assets"].append((asset.ticker, result.assets_pages))
        
        # Adiciona keywords de ativos para highlight
        asset_keywords = ["CRA", "CRI", "CDB", "LCI", "LCA", "FII", "FIM", "ETF",
                         "debênture", "ações", "cotas"]
        for kw in asset_keywords:
            highlights["assets"].append((kw, result.assets_pages))
        
        # Quantidades - destaca valores monetários e números
        all_quantity_pages = list(set(result.assets_pages + result.quantities_pages))
        for qty in result.asset_quantities:
            if qty.quantity:
                highlights["quantities"].append(
                    (str(int(qty.quantity)), all_quantity_pages)
                )
            if qty.total_value:
                highlights["quantities"].append(
                    (f"R$", all_quantity_pages)
                )
        
        # Info do fundo
        if result.fund_name:
            highlights["fund_info"].append(
                (result.fund_name, list(range(1, min(4, result.total_pages + 1))))
            )
        if result.fund_cnpj:
            highlights["fund_info"].append(
                (result.fund_cnpj, list(range(1, min(4, result.total_pages + 1))))
            )
        
        return highlights


