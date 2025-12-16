"""
Base de Conhecimento Estruturado.

Extrai e organiza informações estruturadas dos documentos
para melhorar a qualidade das respostas do Q&A.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Set
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class ExtractedEntity:
    """Entidade extraída do documento."""
    
    name: str
    entity_type: str  # license, person, value, date, etc.
    value: Optional[str] = None
    properties: Dict[str, Any] = field(default_factory=dict)
    source_pages: List[int] = field(default_factory=list)
    confidence: float = 0.8
    
    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "type": self.entity_type,
            "value": self.value,
            "properties": self.properties,
            "pages": self.source_pages,
            "confidence": self.confidence,
        }


@dataclass
class LicenseInfo:
    """Informações estruturadas de uma licença de software."""
    
    name: str
    full_name: str = ""
    aliases: List[str] = field(default_factory=list)
    criticality: str = ""  # ALTO, MÉDIO, BAIXO
    criticality_reason: str = ""
    conditions: List[str] = field(default_factory=list)
    compatible_with: List[str] = field(default_factory=list)
    incompatible_with: List[str] = field(default_factory=list)
    recommendations: str = ""
    source_pages: List[int] = field(default_factory=list)
    
    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "full_name": self.full_name,
            "aliases": self.aliases,
            "criticality": self.criticality,
            "criticality_reason": self.criticality_reason,
            "conditions": self.conditions,
            "compatible_with": self.compatible_with,
            "incompatible_with": self.incompatible_with,
            "recommendations": self.recommendations,
            "pages": self.source_pages,
        }


@dataclass
class Definition:
    """Definição extraída do documento."""
    
    term: str
    definition: str
    source_page: int = 0
    context: str = ""
    
    def to_dict(self) -> dict:
        return {
            "term": self.term,
            "definition": self.definition,
            "page": self.source_page,
        }


class KnowledgeBase:
    """
    Base de conhecimento estruturado extraído de documentos.
    
    Organiza entidades, definições e relacionamentos para
    melhorar a qualidade das respostas do Q&A.
    """
    
    def __init__(self):
        """Inicializa a base de conhecimento."""
        self.entities: Dict[str, ExtractedEntity] = {}
        self.licenses: Dict[str, LicenseInfo] = {}
        self.definitions: Dict[str, Definition] = {}
        self.recommendations: List[str] = []
        self.document_name: str = ""
        self._indexed = False
    
    def index_document(
        self,
        full_text: str,
        document_name: str = "",
        pages: Optional[List[str]] = None
    ) -> None:
        """
        Indexa um documento e extrai informações estruturadas.
        
        Args:
            full_text: Texto completo do documento
            document_name: Nome do documento
            pages: Lista de textos por página (opcional)
        """
        self.document_name = document_name
        
        # Extrai diferentes tipos de informação
        self._extract_licenses(full_text, pages)
        self._extract_definitions(full_text, pages)
        self._extract_recommendations(full_text)
        self._extract_general_entities(full_text, pages)
        
        self._indexed = True
        
        logger.info(
            f"Base de conhecimento indexada: "
            f"{len(self.licenses)} licenças, "
            f"{len(self.definitions)} definições, "
            f"{len(self.recommendations)} recomendações"
        )
    
    def _extract_licenses(
        self,
        text: str,
        pages: Optional[List[str]] = None
    ) -> None:
        """Extrai informações sobre licenças de software."""
        
        # Padrões para identificar licenças
        license_patterns = [
            r'\b(GPL-?[23]\.0(?:-only|-or-later)?)\b',
            r'\b(AGPL-?3\.0(?:-only)?)\b',
            r'\b(LGPL-?[23]\.?[01]?\+?(?:-only|-or-later)?)\b',
            r'\b(Apache-?2\.0)\b',
            r'\b(MIT)\b',
            r'\b(BSD)\b',
            r'\b(MPL-?[12]\.?[01]?)\b',
            r'\b(EPL-?[12]\.0)\b',
            r'\b(CDDL-?1\.[01])\b',
        ]
        
        found_licenses: Set[str] = set()
        
        for pattern in license_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            found_licenses.update(matches)
        
        # ========== EXTRAÇÃO MELHORADA DE CRITICIDADE ==========
        # Padrão 1: Formato de tabela (LICENÇA + GRAU + EXPLICAÇÃO)
        # Ex: "AGPL-3.0-only\n\nALTO\nRecomendamos..."
        criticality_patterns = [
            # Padrão para tabela com ALTO/MÉDIO/BAIXO após nome da licença
            r'(AGPL[^\n]*?|GPL[^\n]*?|LGPL[^\n]*?|Apache[^\n]*?|MPL[^\n]*?|EPL[^\n]*?|MIT|BSD)[^\n]*?\n+\s*(ALTO|MÉDIO|MÉDIO/BAIXO|BAIXO)\s*\n*([^A-Z\n]*)',
            # Padrão alternativo
            r'(\w+[-\w.]+)\s+(?:licença\s+)?(ALTO|MÉDIO|BAIXO)',
        ]
        
        criticality_map = {}
        
        for pattern in criticality_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE | re.MULTILINE)
            for match in matches:
                license_name = match[0].strip()
                level = match[1].upper().replace("MÉDIO/BAIXO", "MÉDIO")
                reason = match[2].strip()[:200] if len(match) > 2 else ""
                
                # Normaliza nome da licença
                normalized = license_name.upper().replace(" ", "-")
                normalized = re.sub(r'[^\w\d\-\.]', '', normalized)
                
                if normalized and level in ["ALTO", "MÉDIO", "BAIXO"]:
                    criticality_map[normalized] = (level, reason)
                    logger.debug(f"Criticidade extraída: {normalized} = {level}")
        
        # ========== FALLBACK: Criticidade conhecida de licenças ==========
        # Se não encontrou no documento, usa conhecimento padrão do domínio
        KNOWN_CRITICALITY = {
            "AGPL-3.0-ONLY": ("ALTO", "Copyleft forte com obrigação de disponibilização em rede"),
            "AGPL-3.0": ("ALTO", "Copyleft forte com obrigação de disponibilização em rede"),
            "GPL-2.0-ONLY": ("MÉDIO", "Copyleft forte, baixa compatibilidade"),
            "GPL-3.0-OR-LATER": ("BAIXO", "Copyleft com boa compatibilidade"),
            "GPL-3.0": ("BAIXO", "Copyleft com boa compatibilidade"),
            "LGPL-2.0-ONLY": ("MÉDIO", "Copyleft fraco, compatibilidade limitada"),
            "LGPL-2.1+": ("BAIXO", "Copyleft fraco, boa compatibilidade"),
            "LGPL-3.0": ("BAIXO", "Copyleft fraco, boa compatibilidade"),
            "APACHE-2.0": ("BAIXO", "Licença permissiva, poucas obrigações"),
            "MIT": ("BAIXO", "Licença permissiva, poucas obrigações"),
            "BSD": ("BAIXO", "Licença permissiva, poucas obrigações"),
            "MPL-2.0": ("BAIXO", "Licença permissiva com copyleft por arquivo"),
            "MPL-1.1": ("MÉDIO", "Menor compatibilidade que MPL-2.0"),
            "EPL-2.0": ("BAIXO", "Licença permissiva com copyleft fraco"),
        }
        
        # Cria objetos LicenseInfo
        for license_name in found_licenses:
            normalized = license_name.upper().replace(" ", "-")
            
            # Tenta extraído do documento primeiro, depois fallback
            crit_info = criticality_map.get(normalized)
            if not crit_info:
                # Busca parcial no mapa extraído
                for key, val in criticality_map.items():
                    if normalized in key or key in normalized:
                        crit_info = val
                        break
            
            if not crit_info:
                # Usa conhecimento padrão
                crit_info = KNOWN_CRITICALITY.get(normalized, ("", ""))
            
            self.licenses[normalized] = LicenseInfo(
                name=license_name,
                criticality=crit_info[0],
                criticality_reason=crit_info[1],
            )
        
        logger.info(f"Licenças extraídas com criticidade: {len([l for l in self.licenses.values() if l.criticality])}")
    
    def _extract_definitions(
        self,
        text: str,
        pages: Optional[List[str]] = None
    ) -> None:
        """Extrai definições de termos do documento."""
        
        # Padrões para definições
        definition_patterns = [
            # "Termo" significa/significa: definição
            r'"([^"]+)"\s+(?:significa|signiﬁca)[:\s]+([^.]+\.)',
            # Termo: definição
            r'([A-Z][a-záéíóúâêîôûãõç]+(?:\s+[a-záéíóúâêîôûãõç]+)?)[:\s]+(?:significa|signiﬁca|é|são)\s+([^.]+\.)',
            # "termo" = definição
            r'"([^"]+)"\s*[=:]\s*([^.]+\.)',
        ]
        
        for pattern in definition_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            
            for match in matches:
                term = match[0].strip()
                definition = match[1].strip()
                
                # Ignora definições muito curtas ou muito longas
                if len(definition) < 10 or len(definition) > 500:
                    continue
                
                # Ignora termos genéricos
                generic_terms = {"você", "ela", "ele", "isso", "isto", "aquilo"}
                if term.lower() in generic_terms:
                    continue
                
                self.definitions[term.lower()] = Definition(
                    term=term,
                    definition=definition,
                )
    
    def _extract_recommendations(self, text: str) -> None:
        """Extrai recomendações do documento."""
        
        # Padrões para recomendações
        recommendation_patterns = [
            r'(?:recomend(?:amos|a-se|ação)|evitar?|priorizar?|buscar)[:\s]+([^.]+\.)',
            r'(?:deve-se|devemos|é preciso|é necessário)[:\s]+([^.]+\.)',
        ]
        
        for pattern in recommendation_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            
            for match in matches:
                rec = match.strip()
                if len(rec) > 20 and rec not in self.recommendations:
                    self.recommendations.append(rec)
    
    def _extract_general_entities(
        self,
        text: str,
        pages: Optional[List[str]] = None
    ) -> None:
        """Extrai entidades gerais do documento."""
        
        # CNPJs
        cnpj_pattern = r'\d{2}[.\s]?\d{3}[.\s]?\d{3}[/\s]?\d{4}[-\s]?\d{2}'
        cnpjs = re.findall(cnpj_pattern, text)
        
        for cnpj in cnpjs:
            self.entities[f"cnpj_{cnpj}"] = ExtractedEntity(
                name=cnpj,
                entity_type="cnpj",
                value=cnpj,
            )
        
        # Datas
        date_pattern = r'\d{1,2}[/.-]\d{1,2}[/.-]\d{2,4}'
        dates = re.findall(date_pattern, text)
        
        for date in set(dates):
            self.entities[f"date_{date}"] = ExtractedEntity(
                name=date,
                entity_type="date",
                value=date,
            )
        
        # Valores monetários
        value_pattern = r'R\$\s*[\d.,]+(?:\s*(?:mil|milhão|milhões|bi|bilhão|bilhões))?'
        values = re.findall(value_pattern, text, re.IGNORECASE)
        
        for value in set(values):
            self.entities[f"value_{value}"] = ExtractedEntity(
                name=value,
                entity_type="monetary_value",
                value=value,
            )
    
    def query_license(self, license_name: str) -> Optional[LicenseInfo]:
        """
        Consulta informações de uma licença.
        
        Args:
            license_name: Nome da licença
        
        Returns:
            LicenseInfo ou None
        """
        normalized = license_name.upper().replace(" ", "-")
        
        # Busca exata
        if normalized in self.licenses:
            return self.licenses[normalized]
        
        # Busca parcial
        for name, info in self.licenses.items():
            if normalized in name or name in normalized:
                return info
            # Busca em aliases
            for alias in info.aliases:
                if normalized in alias.upper() or alias.upper() in normalized:
                    return info
        
        return None
    
    def query_definition(self, term: str) -> Optional[Definition]:
        """
        Consulta definição de um termo.
        
        Args:
            term: Termo a consultar
        
        Returns:
            Definition ou None
        """
        term_lower = term.lower()
        
        # Busca exata
        if term_lower in self.definitions:
            return self.definitions[term_lower]
        
        # Busca parcial
        for key, definition in self.definitions.items():
            if term_lower in key or key in term_lower:
                return definition
        
        return None
    
    def check_compatibility(
        self,
        license_a: str,
        license_b: str
    ) -> Dict[str, Any]:
        """
        Verifica compatibilidade entre duas licenças.
        
        Args:
            license_a: Primeira licença
            license_b: Segunda licença
        
        Returns:
            Dict com resultado da verificação
        """
        info_a = self.query_license(license_a)
        info_b = self.query_license(license_b)
        
        result = {
            "license_a": license_a,
            "license_b": license_b,
            "compatible": None,  # True, False, ou None se desconhecido
            "reason": "",
            "found_a": info_a is not None,
            "found_b": info_b is not None,
        }
        
        if not info_a or not info_b:
            result["reason"] = "Uma ou ambas as licenças não foram encontradas na base de conhecimento."
            return result
        
        # Verifica compatibilidade
        norm_b = license_b.upper().replace(" ", "-")
        norm_a = license_a.upper().replace(" ", "-")
        
        if norm_b in info_a.compatible_with:
            result["compatible"] = True
            result["reason"] = f"{license_a} é compatível com {license_b}."
        elif norm_b in info_a.incompatible_with:
            result["compatible"] = False
            result["reason"] = f"{license_a} NÃO é compatível com {license_b}."
        elif norm_a in info_b.compatible_with:
            result["compatible"] = True
            result["reason"] = f"{license_b} é compatível com {license_a}."
        elif norm_a in info_b.incompatible_with:
            result["compatible"] = False
            result["reason"] = f"{license_b} NÃO é compatível com {license_a}."
        else:
            result["reason"] = (
                "Compatibilidade não determinada. "
                "Consulte o documento para mais detalhes."
            )
        
        return result
    
    def get_recommendations(self) -> List[str]:
        """Retorna todas as recomendações extraídas."""
        return self.recommendations.copy()
    
    def get_critical_licenses(self) -> List[LicenseInfo]:
        """Retorna licenças com criticidade ALTO."""
        return [
            lic for lic in self.licenses.values()
            if lic.criticality == "ALTO"
        ]
    
    def get_safe_licenses(self) -> List[LicenseInfo]:
        """Retorna licenças com criticidade BAIXO."""
        return [
            lic for lic in self.licenses.values()
            if lic.criticality == "BAIXO"
        ]
    
    def search(self, query: str) -> Dict[str, Any]:
        """
        Busca na base de conhecimento.
        
        Args:
            query: Termo de busca
        
        Returns:
            Dict com resultados encontrados
        """
        query_lower = query.lower()
        results = {
            "licenses": [],
            "definitions": [],
            "entities": [],
            "recommendations": [],
        }
        
        # Busca em licenças
        for name, info in self.licenses.items():
            if query_lower in name.lower() or query_lower in info.full_name.lower():
                results["licenses"].append(info.to_dict())
        
        # Busca em definições
        for term, definition in self.definitions.items():
            if query_lower in term or query_lower in definition.definition.lower():
                results["definitions"].append(definition.to_dict())
        
        # Busca em entidades
        for key, entity in self.entities.items():
            if query_lower in entity.name.lower():
                results["entities"].append(entity.to_dict())
        
        # Busca em recomendações
        for rec in self.recommendations:
            if query_lower in rec.lower():
                results["recommendations"].append(rec)
        
        return results
    
    def get_summary(self) -> Dict[str, Any]:
        """Retorna resumo da base de conhecimento."""
        return {
            "document": self.document_name,
            "indexed": self._indexed,
            "licenses_count": len(self.licenses),
            "definitions_count": len(self.definitions),
            "entities_count": len(self.entities),
            "recommendations_count": len(self.recommendations),
            "critical_licenses": [
                lic.name for lic in self.get_critical_licenses()
            ],
        }
    
    def clear(self) -> None:
        """Limpa a base de conhecimento."""
        self.entities.clear()
        self.licenses.clear()
        self.definitions.clear()
        self.recommendations.clear()
        self.document_name = ""
        self._indexed = False

