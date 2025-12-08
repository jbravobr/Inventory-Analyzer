"""
Analisador de Escrituras Públicas de Inventário.

Extrai informações sobre herdeiros, inventariante, bens BTG e divisão patrimonial.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple

from rag.rag_pipeline import RAGPipeline, RAGConfig
from core.pdf_reader import PDFReader
from core.ocr_extractor import OCRExtractor

logger = logging.getLogger(__name__)


@dataclass
class Heir:
    """Representa um herdeiro."""
    name: str
    cpf: Optional[str] = None
    relationship: Optional[str] = None  # cônjuge, filho, neto, etc
    is_minor: bool = False
    legal_representative: Optional[str] = None
    
    def to_dict(self) -> dict:
        return {
            "nome": self.name,
            "cpf": self.cpf,
            "parentesco": self.relationship,
            "menor_idade": self.is_minor,
            "representante_legal": self.legal_representative
        }


@dataclass
class BTGAsset:
    """Representa um bem/ativo BTG."""
    description: str
    asset_type: Optional[str] = None  # conta, CDB, fundo, ações
    account_number: Optional[str] = None
    value: Optional[float] = None
    agency: Optional[str] = None
    
    def to_dict(self) -> dict:
        return {
            "descricao": self.description,
            "tipo": self.asset_type,
            "numero_conta": self.account_number,
            "valor": self.value,
            "agencia": self.agency
        }


@dataclass
class AssetDivision:
    """Representa a divisão de um bem entre herdeiros."""
    asset: BTGAsset
    divisions: List[Dict[str, Any]] = field(default_factory=list)
    # divisions = [{"herdeiro": "Nome", "percentual": 50.0, "valor": 10000.0}]
    
    def to_dict(self) -> dict:
        return {
            "bem": self.asset.to_dict(),
            "divisoes": self.divisions
        }


@dataclass
class InventoryAnalysisResult:
    """Resultado completo da análise de inventário."""
    
    # Informações básicas
    deceased_name: Optional[str] = None
    death_date: Optional[str] = None
    notary_office: Optional[str] = None
    
    # Cláusula A - Herdeiros
    heirs: List[Heir] = field(default_factory=list)
    heirs_raw_text: str = ""
    heirs_pages: List[int] = field(default_factory=list)
    
    # Cláusula B - Inventariante
    administrator_name: Optional[str] = None
    administrator_cpf: Optional[str] = None
    administrator_is_heir: bool = False
    administrator_raw_text: str = ""
    administrator_pages: List[int] = field(default_factory=list)
    
    # Cláusula C - Bens BTG
    btg_assets: List[BTGAsset] = field(default_factory=list)
    btg_raw_text: str = ""
    btg_pages: List[int] = field(default_factory=list)
    
    # Cláusula D - Divisão dos bens
    asset_divisions: List[AssetDivision] = field(default_factory=list)
    divisions_raw_text: str = ""
    divisions_pages: List[int] = field(default_factory=list)
    
    # Metadados
    total_pages: int = 0
    processing_time: float = 0.0
    confidence_scores: Dict[str, float] = field(default_factory=dict)
    
    def to_dict(self) -> dict:
        return {
            "informacoes_gerais": {
                "falecido": self.deceased_name,
                "data_obito": self.death_date,
                "cartorio": self.notary_office,
                "total_paginas": self.total_pages
            },
            "clausula_a_herdeiros": {
                "herdeiros": [h.to_dict() for h in self.heirs],
                "quantidade": len(self.heirs),
                "paginas": self.heirs_pages,
                "confianca": self.confidence_scores.get("heirs", 0)
            },
            "clausula_b_inventariante": {
                "nome": self.administrator_name,
                "cpf": self.administrator_cpf,
                "e_herdeiro": self.administrator_is_heir,
                "paginas": self.administrator_pages,
                "confianca": self.confidence_scores.get("administrator", 0)
            },
            "clausula_c_bens_btg": {
                "bens": [a.to_dict() for a in self.btg_assets],
                "quantidade": len(self.btg_assets),
                "paginas": self.btg_pages,
                "confianca": self.confidence_scores.get("btg_assets", 0)
            },
            "clausula_d_divisao": {
                "divisoes": [d.to_dict() for d in self.asset_divisions],
                "paginas": self.divisions_pages,
                "confianca": self.confidence_scores.get("divisions", 0)
            },
            "tempo_processamento": self.processing_time
        }


class InventoryAnalyzer:
    """
    Analisador de Escrituras Públicas de Inventário.
    
    Utiliza RAG para extrair informações específicas sobre:
    - Herdeiros
    - Inventariante
    - Bens BTG
    - Divisão patrimonial
    """
    
    # Cores para highlight (RGB)
    HIGHLIGHT_COLORS = {
        "heirs": (255, 255, 0),        # Amarelo - Herdeiros
        "administrator": (0, 255, 0),   # Verde - Inventariante
        "btg_assets": (0, 191, 255),    # Azul claro - Bens BTG
        "divisions": (255, 182, 193)    # Rosa - Divisão
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
            use_hybrid_search=True,
            generate_answers=False  # Usa apenas retrieval por padrão
        )
        self.rag = RAGPipeline(self.config)
        self.reader = PDFReader()
        self.ocr = OCRExtractor()
        self._document = None
        self._full_text = ""
    
    def analyze(self, pdf_path: Path) -> InventoryAnalysisResult:
        """
        Analisa uma escritura de inventário.
        
        Args:
            pdf_path: Caminho para o PDF.
        
        Returns:
            InventoryAnalysisResult: Resultado completo da análise.
        """
        import time
        start_time = time.time()
        
        logger.info(f"Iniciando análise de inventário: {pdf_path}")
        
        # Lê e processa o PDF
        self._document = self.reader.read(pdf_path)
        self.ocr.extract(self._document)
        
        # Indexa no RAG
        self.rag.index_document(self._document)
        
        # Concatena texto completo
        self._full_text = "\n\n".join([
            page.text for page in self._document.pages if page.text
        ])
        
        result = InventoryAnalysisResult()
        result.total_pages = len(self._document.pages)
        
        # Analisa cada cláusula
        self._analyze_heirs(result)
        self._analyze_administrator(result)
        self._analyze_btg_assets(result)
        self._analyze_divisions(result)
        self._analyze_general_info(result)
        
        result.processing_time = time.time() - start_time
        
        logger.info(f"Análise concluída em {result.processing_time:.2f}s")
        
        return result
    
    def _analyze_heirs(self, result: InventoryAnalysisResult) -> None:
        """Analisa e extrai informações dos herdeiros (Cláusula A)."""
        logger.info("Analisando herdeiros...")
        
        queries = [
            "Quem são os herdeiros mencionados na escritura?",
            "Liste todos os herdeiros com seus nomes completos",
            "Quais são os filhos e cônjuge do falecido?",
            "Identifique os sucessores e seu grau de parentesco"
        ]
        
        all_contexts = []
        all_pages = set()
        
        for query in queries:
            response = self.rag.query(query)
            if response.retrieval_result and response.retrieval_result.chunks:
                for chunk in response.retrieval_result.chunks:
                    all_contexts.append(chunk.text)
                    all_pages.add(chunk.page_number)
        
        result.heirs_raw_text = "\n---\n".join(all_contexts)
        result.heirs_pages = sorted(list(all_pages))
        
        # Extrai herdeiros do texto
        result.heirs = self._extract_heirs_from_text(result.heirs_raw_text)
        result.confidence_scores["heirs"] = 0.7 if result.heirs else 0.3
    
    def _analyze_administrator(self, result: InventoryAnalysisResult) -> None:
        """Analisa e extrai informações do inventariante (Cláusula B)."""
        logger.info("Analisando inventariante...")
        
        queries = [
            "Quem foi nomeado inventariante?",
            "Qual o nome do inventariante nomeado?",
            "Identifique o inventariante e seu CPF"
        ]
        
        all_contexts = []
        all_pages = set()
        
        for query in queries:
            response = self.rag.query(query)
            if response.retrieval_result and response.retrieval_result.chunks:
                for chunk in response.retrieval_result.chunks:
                    all_contexts.append(chunk.text)
                    all_pages.add(chunk.page_number)
        
        result.administrator_raw_text = "\n---\n".join(all_contexts)
        result.administrator_pages = sorted(list(all_pages))
        
        # Extrai inventariante do texto
        admin_info = self._extract_administrator_from_text(result.administrator_raw_text)
        if admin_info:
            result.administrator_name = admin_info.get("name")
            result.administrator_cpf = admin_info.get("cpf")
            
            # Verifica se é herdeiro
            if result.administrator_name and result.heirs:
                for heir in result.heirs:
                    if heir.name and result.administrator_name.lower() in heir.name.lower():
                        result.administrator_is_heir = True
                        break
        
        result.confidence_scores["administrator"] = 0.7 if result.administrator_name else 0.3
    
    def _analyze_btg_assets(self, result: InventoryAnalysisResult) -> None:
        """Analisa e extrai bens BTG (Cláusula C)."""
        logger.info("Analisando bens BTG...")
        
        queries = [
            "Quais bens mencionam BTG ou BTG Pactual?",
            "Liste os investimentos, contas ou ativos do BTG",
            "Identifique valores e contas no BTG Pactual",
            "Quais são os bens financeiros no banco BTG?"
        ]
        
        all_contexts = []
        all_pages = set()
        
        for query in queries:
            response = self.rag.query(query)
            if response.retrieval_result and response.retrieval_result.chunks:
                for chunk in response.retrieval_result.chunks:
                    # Filtra apenas chunks que mencionam BTG
                    if "btg" in chunk.text.lower():
                        all_contexts.append(chunk.text)
                        all_pages.add(chunk.page_number)
        
        result.btg_raw_text = "\n---\n".join(all_contexts)
        result.btg_pages = sorted(list(all_pages))
        
        # Extrai bens BTG do texto
        result.btg_assets = self._extract_btg_assets_from_text(result.btg_raw_text)
        result.confidence_scores["btg_assets"] = 0.8 if result.btg_assets else 0.2
    
    def _analyze_divisions(self, result: InventoryAnalysisResult) -> None:
        """Analisa a divisão dos bens BTG (Cláusula D)."""
        logger.info("Analisando divisão de bens...")
        
        if not result.btg_assets:
            logger.info("Nenhum bem BTG encontrado para analisar divisão")
            return
        
        queries = [
            "Como os bens BTG foram divididos entre os herdeiros?",
            "Qual o percentual de cada herdeiro nos bens do BTG?",
            "Identifique a partilha dos investimentos BTG",
            "Qual a fração de cada herdeiro nos ativos BTG?"
        ]
        
        all_contexts = []
        all_pages = set()
        
        for query in queries:
            response = self.rag.query(query)
            if response.retrieval_result and response.retrieval_result.chunks:
                for chunk in response.retrieval_result.chunks:
                    all_contexts.append(chunk.text)
                    all_pages.add(chunk.page_number)
        
        result.divisions_raw_text = "\n---\n".join(all_contexts)
        result.divisions_pages = sorted(list(all_pages))
        
        # Extrai divisões
        result.asset_divisions = self._extract_divisions_from_text(
            result.divisions_raw_text,
            result.btg_assets,
            result.heirs
        )
        result.confidence_scores["divisions"] = 0.6 if result.asset_divisions else 0.2
    
    def _analyze_general_info(self, result: InventoryAnalysisResult) -> None:
        """Extrai informações gerais do documento."""
        logger.info("Extraindo informações gerais...")
        
        # Busca nome do falecido
        response = self.rag.query("Qual o nome do falecido ou autor da herança?")
        if response.retrieval_result and response.retrieval_result.chunks:
            text = response.retrieval_result.chunks[0].text
            # Tenta extrair nome após padrões comuns
            patterns = [
                r"(?:falecido|de cujus|autor da herança)[:\s]+([A-ZÁÉÍÓÚÂÊÎÔÛÃÕÇ][A-Za-záéíóúâêîôûãõç\s]+)",
                r"espólio de[:\s]+([A-ZÁÉÍÓÚÂÊÎÔÛÃÕÇ][A-Za-záéíóúâêîôûãõç\s]+)",
                r"inventário de[:\s]+([A-ZÁÉÍÓÚÂÊÎÔÛÃÕÇ][A-Za-záéíóúâêîôûãõç\s]+)"
            ]
            for pattern in patterns:
                match = re.search(pattern, text, re.IGNORECASE)
                if match:
                    result.deceased_name = match.group(1).strip()
                    break
        
        # Busca data do óbito
        response = self.rag.query("Qual a data do óbito ou falecimento?")
        if response.retrieval_result and response.retrieval_result.chunks:
            text = response.retrieval_result.chunks[0].text
            date_pattern = r"\d{1,2}[/.-]\d{1,2}[/.-]\d{2,4}"
            match = re.search(date_pattern, text)
            if match:
                result.death_date = match.group()
        
        # Busca cartório
        response = self.rag.query("Qual o cartório que lavrou a escritura?")
        if response.retrieval_result and response.retrieval_result.chunks:
            text = response.retrieval_result.chunks[0].text
            patterns = [
                r"(\d+[ºª]?\s*(?:Tabelionato|Cartório|Ofício)[^,\n]*)",
                r"(Cartório[^,\n]*Notas[^,\n]*)"
            ]
            for pattern in patterns:
                match = re.search(pattern, text, re.IGNORECASE)
                if match:
                    result.notary_office = match.group(1).strip()
                    break
    
    def _extract_heirs_from_text(self, text: str) -> List[Heir]:
        """Extrai lista de herdeiros do texto."""
        heirs = []
        
        # Padrões para identificar herdeiros
        patterns = [
            # Padrão: "NOME COMPLETO, brasileiro(a), CPF nº XXX"
            r"([A-ZÁÉÍÓÚÂÊÎÔÛÃÕÇ][A-Za-záéíóúâêîôûãõç\s]+),\s*(?:brasileir[oa]|casad[oa]|solteir[oa])[^,]*,\s*(?:CPF|RG)[^\d]*(\d{3}[\.\s]?\d{3}[\.\s]?\d{3}[-\s]?\d{2})?",
            # Padrão: "herdeiro(a) NOME"
            r"herdeir[oa][:\s]+([A-ZÁÉÍÓÚÂÊÎÔÛÃÕÇ][A-Za-záéíóúâêîôûãõç\s]+)",
            # Padrão: filho/filha NOME
            r"(?:filh[oa]|cônjuge|viúv[oa]|net[oa])[:\s]+([A-ZÁÉÍÓÚÂÊÎÔÛÃÕÇ][A-Za-záéíóúâêîôûãõç\s]+)"
        ]
        
        seen_names = set()
        
        for pattern in patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                name = match.group(1).strip()
                # Limpa o nome
                name = re.sub(r'\s+', ' ', name)
                name = name.strip(',.:;')
                
                # Evita duplicatas e nomes muito curtos
                if len(name) > 5 and name.lower() not in seen_names:
                    seen_names.add(name.lower())
                    
                    cpf = match.group(2) if len(match.groups()) > 1 else None
                    
                    # Tenta identificar parentesco
                    relationship = None
                    context = text[max(0, match.start()-50):match.end()+50].lower()
                    if "cônjuge" in context or "viúv" in context:
                        relationship = "cônjuge"
                    elif "filh" in context:
                        relationship = "filho(a)"
                    elif "net" in context:
                        relationship = "neto(a)"
                    
                    heirs.append(Heir(
                        name=name,
                        cpf=cpf,
                        relationship=relationship
                    ))
        
        return heirs
    
    def _extract_administrator_from_text(self, text: str) -> Optional[Dict[str, str]]:
        """Extrai informações do inventariante."""
        patterns = [
            r"inventariante[:\s]+([A-ZÁÉÍÓÚÂÊÎÔÛÃÕÇ][A-Za-záéíóúâêîôûãõç\s]+)",
            r"nomead[oa]\s+inventariante[:\s]+([A-ZÁÉÍÓÚÂÊÎÔÛÃÕÇ][A-Za-záéíóúâêîôûãõç\s]+)",
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                name = match.group(1).strip()
                name = re.sub(r'\s+', ' ', name)
                name = name.strip(',.:;')
                
                # Tenta encontrar CPF próximo
                cpf_pattern = r"CPF[^\d]*(\d{3}[\.\s]?\d{3}[\.\s]?\d{3}[-\s]?\d{2})"
                cpf_match = re.search(cpf_pattern, text[match.start():match.start()+200])
                cpf = cpf_match.group(1) if cpf_match else None
                
                return {"name": name, "cpf": cpf}
        
        return None
    
    def _extract_btg_assets_from_text(self, text: str) -> List[BTGAsset]:
        """Extrai bens BTG do texto."""
        assets = []
        
        # Divide o texto em sentenças que mencionam BTG
        sentences = re.split(r'[.;\n]', text)
        
        for sentence in sentences:
            if "btg" not in sentence.lower():
                continue
            
            asset = BTGAsset(description=sentence.strip())
            
            # Identifica tipo do ativo
            sentence_lower = sentence.lower()
            if any(x in sentence_lower for x in ["conta corrente", "c/c"]):
                asset.asset_type = "Conta Corrente"
            elif any(x in sentence_lower for x in ["cdb", "certificado"]):
                asset.asset_type = "CDB"
            elif any(x in sentence_lower for x in ["fundo", "fic", "fim"]):
                asset.asset_type = "Fundo de Investimento"
            elif any(x in sentence_lower for x in ["ação", "ações", "bovespa"]):
                asset.asset_type = "Ações"
            elif any(x in sentence_lower for x in ["poupança"]):
                asset.asset_type = "Poupança"
            else:
                asset.asset_type = "Investimento"
            
            # Tenta extrair número da conta
            account_match = re.search(r"(?:conta|ag)[^\d]*(\d+[-/]?\d*)", sentence, re.IGNORECASE)
            if account_match:
                asset.account_number = account_match.group(1)
            
            # Tenta extrair valor
            value_match = re.search(r"R\$\s*([\d.,]+)", sentence)
            if value_match:
                try:
                    value_str = value_match.group(1).replace(".", "").replace(",", ".")
                    asset.value = float(value_str)
                except ValueError:
                    pass
            
            if asset.description:
                assets.append(asset)
        
        return assets
    
    def _extract_divisions_from_text(
        self,
        text: str,
        assets: List[BTGAsset],
        heirs: List[Heir]
    ) -> List[AssetDivision]:
        """Extrai divisão de bens entre herdeiros."""
        divisions = []
        
        if not assets or not heirs:
            return divisions
        
        # Para cada bem, tenta encontrar a divisão
        for asset in assets:
            division = AssetDivision(asset=asset)
            
            # Busca percentuais mencionados para cada herdeiro
            for heir in heirs:
                if not heir.name:
                    continue
                
                # Procura menção do herdeiro próximo a percentuais
                heir_pattern = re.escape(heir.name.split()[0])  # Primeiro nome
                context_pattern = f"{heir_pattern}[^%]*?(\\d+[,.]?\\d*)\\s*%"
                
                match = re.search(context_pattern, text, re.IGNORECASE)
                if match:
                    try:
                        percentage = float(match.group(1).replace(",", "."))
                        value = (asset.value * percentage / 100) if asset.value else None
                        
                        division.divisions.append({
                            "herdeiro": heir.name,
                            "percentual": percentage,
                            "valor": value
                        })
                    except ValueError:
                        pass
            
            # Se encontrou alguma divisão, adiciona
            if division.divisions:
                divisions.append(division)
        
        return divisions
    
    def get_highlights(self, result: InventoryAnalysisResult) -> Dict[str, List[Tuple[str, List[int]]]]:
        """
        Retorna os textos e páginas para highlight.
        
        Returns:
            Dict com categoria -> [(texto, páginas)]
        """
        highlights = {
            "heirs": [],
            "administrator": [],
            "btg_assets": [],
            "divisions": []
        }
        
        # Herdeiros
        for heir in result.heirs:
            if heir.name:
                highlights["heirs"].append((heir.name, result.heirs_pages))
        
        # Inventariante
        if result.administrator_name:
            highlights["administrator"].append(
                (result.administrator_name, result.administrator_pages)
            )
        
        # Bens BTG
        for asset in result.btg_assets:
            # Adiciona "BTG" como termo para highlight
            highlights["btg_assets"].append(("BTG", result.btg_pages))
            if asset.account_number:
                highlights["btg_assets"].append(
                    (asset.account_number, result.btg_pages)
                )
        
        return highlights

