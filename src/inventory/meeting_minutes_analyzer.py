"""
Analisador de Atas de Reunião de Quotistas.

Extrai informações sobre ativos envolvidos e suas respectivas quantidades.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple

from ..rag.rag_pipeline import RAGPipeline, RAGConfig
from ..core.pdf_reader import PDFReader
from ..core.ocr_extractor import OCRExtractor

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
    
    # Tipos de ativos conhecidos
    ASSET_TYPES = {
        "ação": ["ação", "ações", "ação ordinária", "ação preferencial", "on", "pn"],
        "CRA": ["cra", "certificado de recebíveis do agronegócio"],
        "CRI": ["cri", "certificado de recebíveis imobiliários"],
        "debênture": ["debênture", "debêntures", "debenture"],
        "cota_fundo": ["cota", "cotas", "fii", "fim", "fic", "etf", "fundo"],
        "CDB": ["cdb", "certificado de depósito bancário"],
        "LCI": ["lci", "letra de crédito imobiliário"],
        "LCA": ["lca", "letra de crédito do agronegócio"],
        "titulo_publico": ["tesouro", "ntn", "lft", "ltn", "título público"]
    }
    
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
            use_hybrid_search=True
        )
        self.rag = RAGPipeline(self.config)
        self.reader = PDFReader()
        self.ocr = OCRExtractor()
        self._document = None
        self._full_text = ""
    
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
        
        # Lê e processa o PDF
        self._document = self.reader.read(pdf_path)
        self.ocr.extract(self._document)
        
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
            if response.chunks:
                for chunk in response.chunks:
                    all_contexts.append(chunk.text)
                    all_pages.add(chunk.page_number)
        
        result.assets_raw_text = "\n---\n".join(all_contexts)
        result.assets_pages = sorted(list(all_pages))
        
        # Extrai ativos do texto
        result.assets = self._extract_assets_from_text(result.assets_raw_text)
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
            if response.chunks:
                for chunk in response.chunks:
                    all_contexts.append(chunk.text)
                    all_pages.add(chunk.page_number)
        
        result.quantities_raw_text = "\n---\n".join(all_contexts)
        result.quantities_pages = sorted(list(all_pages))
        
        # Extrai quantidades associadas aos ativos
        result.asset_quantities = self._extract_quantities_from_text(
            result.quantities_raw_text,
            result.assets
        )
        result.confidence_scores["quantities"] = 0.7 if result.asset_quantities else 0.3
    
    def _analyze_general_info(self, result: MeetingMinutesResult) -> None:
        """Extrai informações gerais do documento."""
        logger.info("Extraindo informações gerais...")
        
        # Busca nome do fundo
        response = self.rag.query("Qual o nome do fundo ou veículo de investimento?")
        if response.chunks:
            text = response.chunks[0].text
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
        if response.chunks:
            text = response.chunks[0].text
            cnpj_pattern = r"\d{2}[.\s]?\d{3}[.\s]?\d{3}[/\s]?\d{4}[-\s]?\d{2}"
            match = re.search(cnpj_pattern, text)
            if match:
                result.fund_cnpj = match.group()
        
        # Busca administrador
        response = self.rag.query("Qual o administrador do fundo?")
        if response.chunks:
            text = response.chunks[0].text
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
        if response.chunks:
            text = response.chunks[0].text
            date_pattern = r"\d{1,2}[/.-]\d{1,2}[/.-]\d{2,4}"
            match = re.search(date_pattern, text)
            if match:
                result.meeting_date = match.group()
    
    def _extract_assets_from_text(self, text: str) -> List[Asset]:
        """Extrai lista de ativos do texto."""
        assets = []
        seen_assets = set()
        text_lower = text.lower()
        
        # Procura cada tipo de ativo
        for asset_type, keywords in self.ASSET_TYPES.items():
            for keyword in keywords:
                if keyword in text_lower:
                    # Tenta extrair mais contexto sobre o ativo
                    pattern = rf"({keyword}[^,.\n]*)"
                    matches = re.finditer(pattern, text, re.IGNORECASE)
                    
                    for match in matches:
                        asset_text = match.group(1).strip()
                        
                        # Normaliza para evitar duplicatas
                        normalized = asset_text.lower()[:50]
                        if normalized in seen_assets:
                            continue
                        seen_assets.add(normalized)
                        
                        asset = Asset(
                            name=asset_text[:200],
                            asset_type=asset_type
                        )
                        
                        # Tenta extrair ticker (código de 4-6 letras/números)
                        ticker_match = re.search(
                            r'\b([A-Z]{4}[0-9]{1,2}|[A-Z]{3,4}[0-9]?)\b',
                            asset_text
                        )
                        if ticker_match:
                            asset.ticker = ticker_match.group(1)
                        
                        # Tenta extrair emissor
                        issuer_match = re.search(
                            r'(?:emiss[ãa]o|emitid[oa]|emissora?)[:\s]+([A-Za-záéíóúâêîôûãõç\s]+)',
                            asset_text, re.IGNORECASE
                        )
                        if issuer_match:
                            asset.issuer = issuer_match.group(1).strip()[:100]
                        
                        # Tenta extrair série
                        series_match = re.search(
                            r'(?:série|series)[:\s]+(\S+)',
                            asset_text, re.IGNORECASE
                        )
                        if series_match:
                            asset.series = series_match.group(1)
                        
                        assets.append(asset)
        
        return assets
    
    def _extract_quantities_from_text(
        self,
        text: str,
        assets: List[Asset]
    ) -> List[AssetQuantity]:
        """Extrai quantidades dos ativos do texto."""
        quantities = []
        
        # Padrões para extrair números e valores
        quantity_patterns = [
            r"(\d+(?:[.,]\d+)*)\s*(?:unidades?|cotas?|ações?)",
            r"(?:quantidade|volume)[:\s]+(\d+(?:[.,]\d+)*)",
            r"(?:total\s+de)[:\s]+(\d+(?:[.,]\d+)*)",
        ]
        
        value_patterns = [
            r"R\$\s*(\d+(?:[.,]\d+)*(?:[.,]\d{2})?)",
            r"(?:valor\s+(?:nominal|total|unitário))[:\s]+R?\$?\s*(\d+(?:[.,]\d+)*)"
        ]
        
        date_pattern = r"(\d{1,2}[/.-]\d{1,2}[/.-]\d{2,4})"
        
        # Para cada ativo, tenta encontrar quantidades relacionadas
        for asset in assets:
            quantity_info = AssetQuantity(asset=asset)
            
            # Procura contexto próximo ao ativo
            asset_keyword = asset.name.split()[0] if asset.name else asset.asset_type
            
            # Encontra sentenças que mencionam o ativo
            sentences = re.split(r'[.;\n]', text)
            relevant_sentences = [
                s for s in sentences
                if asset_keyword.lower() in s.lower()
            ]
            
            context = " ".join(relevant_sentences)
            
            if context:
                quantity_info.raw_text = context[:500]
                
                # Extrai quantidade
                for pattern in quantity_patterns:
                    match = re.search(pattern, context, re.IGNORECASE)
                    if match:
                        try:
                            qty_str = match.group(1).replace(".", "").replace(",", ".")
                            quantity_info.quantity = float(qty_str)
                            break
                        except ValueError:
                            pass
                
                # Extrai valores
                for pattern in value_patterns:
                    matches = re.findall(pattern, context, re.IGNORECASE)
                    if matches:
                        try:
                            # Pega o maior valor encontrado como total
                            values = []
                            for m in matches:
                                val_str = m.replace(".", "").replace(",", ".")
                                values.append(float(val_str))
                            
                            if values:
                                quantity_info.total_value = max(values)
                                if len(values) > 1:
                                    quantity_info.unit_price = min(values)
                        except ValueError:
                            pass
                
                # Extrai datas
                dates = re.findall(date_pattern, context)
                if len(dates) >= 1:
                    quantity_info.issue_date = dates[0]
                if len(dates) >= 2:
                    quantity_info.maturity_date = dates[1]
            
            # Só adiciona se encontrou alguma informação útil
            if (quantity_info.quantity or quantity_info.total_value or
                quantity_info.unit_price or quantity_info.nominal_value):
                quantities.append(quantity_info)
        
        return quantities
    
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

