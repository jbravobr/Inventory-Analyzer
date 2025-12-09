"""
Gerador de relatórios em TXT para análise de Ata de Reunião.
"""

from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, List

from .meeting_minutes_analyzer import MeetingMinutesResult

logger = logging.getLogger(__name__)


class MeetingMinutesReportGenerator:
    """Gera relatórios em formato TXT para Atas de Reunião."""
    
    def __init__(self):
        self.line_width = 80
    
    def generate(
        self,
        result: MeetingMinutesResult,
        output_path: Path,
        source_file: Optional[str] = None
    ) -> Path:
        """
        Gera relatório TXT.
        
        Args:
            result: Resultado da análise.
            output_path: Caminho para o arquivo de saída.
            source_file: Nome do arquivo fonte (opcional).
        
        Returns:
            Path: Caminho do arquivo gerado.
        """
        logger.info(f"Gerando relatório TXT: {output_path}")
        
        lines = []
        
        # Cabeçalho
        lines.extend(self._generate_header(source_file))
        lines.append("")
        
        # Informações gerais
        lines.extend(self._generate_general_info(result))
        lines.append("")
        
        # Cláusula A - Ativos
        lines.extend(self._generate_assets_section(result))
        lines.append("")
        
        # Cláusula B - Quantidades
        lines.extend(self._generate_quantities_section(result))
        lines.append("")
        
        # Rodapé
        lines.extend(self._generate_footer(result))
        
        # Escreve arquivo
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(lines))
        
        logger.info(f"Relatório gerado: {output_path}")
        return output_path
    
    def _separator(self, char: str = "=") -> str:
        return char * self.line_width
    
    def _center(self, text: str) -> str:
        return text.center(self.line_width)
    
    def _generate_header(self, source_file: Optional[str]) -> list:
        lines = [
            self._separator("="),
            self._center("RELATÓRIO DE ANÁLISE DE ATA DE REUNIÃO"),
            self._center("DE QUOTISTAS"),
            self._separator("="),
            "",
            f"Data de Geração: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}",
        ]
        
        if source_file:
            lines.append(f"Documento Analisado: {source_file}")
        
        return lines
    
    def _generate_general_info(self, result: MeetingMinutesResult) -> list:
        lines = [
            self._separator("-"),
            "INFORMAÇÕES GERAIS",
            self._separator("-"),
        ]
        
        if result.fund_name:
            lines.append(f"Nome do Fundo: {result.fund_name}")
        else:
            lines.append("Nome do Fundo: Não identificado")
        
        if result.fund_cnpj:
            lines.append(f"CNPJ: {result.fund_cnpj}")
        
        if result.administrator:
            lines.append(f"Administrador: {result.administrator}")
        
        if result.manager:
            lines.append(f"Gestor: {result.manager}")
        
        if result.meeting_date:
            lines.append(f"Data da Reunião: {result.meeting_date}")
        
        lines.append(f"Total de Páginas Analisadas: {result.total_pages}")
        
        return lines
    
    def _generate_assets_section(self, result: MeetingMinutesResult) -> list:
        lines = [
            self._separator("="),
            "CLÁUSULA A - ATIVOS IDENTIFICADOS",
            self._separator("="),
        ]
        
        if not result.assets:
            lines.append("")
            lines.append(">>> NENHUM ATIVO IDENTIFICADO <<<")
            lines.append("")
            lines.append("Contexto encontrado:")
            lines.append(result.assets_raw_text[:500] if result.assets_raw_text else "Nenhum contexto relevante encontrado.")
        else:
            lines.append("")
            lines.append(f"Total de ativos encontrados: {len(result.assets)}")
            lines.append(f"Páginas de referência: {result.assets_pages}")
            lines.append(f"Nível de confiança: {result.confidence_scores.get('assets', 0)*100:.0f}%")
            lines.append("")
            
            # Agrupa por tipo
            by_type: Dict[str, List] = {}
            for asset in result.assets:
                asset_type = asset.asset_type or "Outros"
                if asset_type not in by_type:
                    by_type[asset_type] = []
                by_type[asset_type].append(asset)
            
            type_labels = {
                "ação": "AÇÕES",
                "CRA": "CRA - Certificado de Recebíveis do Agronegócio",
                "CRI": "CRI - Certificado de Recebíveis Imobiliários",
                "debênture": "DEBÊNTURES",
                "cota_fundo": "COTAS DE FUNDO",
                "CDB": "CDB - Certificado de Depósito Bancário",
                "LCI": "LCI - Letra de Crédito Imobiliário",
                "LCA": "LCA - Letra de Crédito do Agronegócio",
                "titulo_publico": "TÍTULOS PÚBLICOS"
            }
            
            for asset_type, assets in by_type.items():
                type_label = type_labels.get(asset_type, asset_type.upper())
                lines.append(f"  {type_label}")
                lines.append(f"  {'-' * (len(type_label) + 2)}")
                
                for i, asset in enumerate(assets, 1):
                    lines.append(f"    {i}. {asset.name[:60]}...")
                    
                    if asset.ticker:
                        lines.append(f"       Ticker/Código: {asset.ticker}")
                    
                    if asset.issuer:
                        lines.append(f"       Emissor: {asset.issuer}")
                    
                    if asset.series:
                        lines.append(f"       Série: {asset.series}")
                    
                    if asset.custodian:
                        lines.append(f"       Custodiante: {asset.custodian}")
                    
                    lines.append("")
                
                lines.append("")
        
        return lines
    
    def _generate_quantities_section(self, result: MeetingMinutesResult) -> list:
        lines = [
            self._separator("="),
            "CLÁUSULA B - QUANTIDADES E VALORES DOS ATIVOS",
            self._separator("="),
        ]
        
        if not result.asset_quantities:
            lines.append("")
            lines.append(">>> NENHUMA QUANTIDADE IDENTIFICADA <<<")
            lines.append("")
            lines.append("Não foi possível extrair quantidades específicas dos ativos.")
            
            if result.quantities_raw_text:
                lines.append("")
                lines.append("Contexto encontrado:")
                lines.append(result.quantities_raw_text[:500])
        else:
            lines.append("")
            lines.append(f"Total de quantidades extraídas: {len(result.asset_quantities)}")
            lines.append(f"Páginas de referência: {result.quantities_pages}")
            lines.append(f"Nível de confiança: {result.confidence_scores.get('quantities', 0)*100:.0f}%")
            lines.append("")
            
            total_value = 0
            
            for i, qty in enumerate(result.asset_quantities, 1):
                lines.append(f"  ATIVO {i}:")
                lines.append(f"  {'-' * 40}")
                
                lines.append(f"    Tipo: {qty.asset.asset_type or 'Não especificado'}")
                
                if qty.asset.name:
                    lines.append(f"    Nome: {qty.asset.name[:50]}...")
                
                if qty.quantity:
                    lines.append(f"    Quantidade: {qty.quantity:,.0f} unidades")
                
                if qty.unit_price:
                    lines.append(f"    Preço Unitário: R$ {qty.unit_price:,.2f}")
                
                if qty.total_value:
                    lines.append(f"    Valor Total: R$ {qty.total_value:,.2f}")
                    total_value += qty.total_value
                
                if qty.nominal_value:
                    lines.append(f"    Valor Nominal: R$ {qty.nominal_value:,.2f}")
                
                if qty.issue_date:
                    lines.append(f"    Data de Emissão: {qty.issue_date}")
                
                if qty.maturity_date:
                    lines.append(f"    Data de Vencimento: {qty.maturity_date}")
                
                lines.append("")
            
            if total_value > 0:
                lines.append(self._separator("-"))
                lines.append(f"  VALOR TOTAL IDENTIFICADO: R$ {total_value:,.2f}")
                lines.append(self._separator("-"))
        
        return lines
    
    def _generate_footer(self, result: MeetingMinutesResult) -> list:
        lines = [
            self._separator("="),
            "RESUMO DA ANÁLISE",
            self._separator("="),
            "",
            f"Nome do Fundo: {result.fund_name or 'Não identificado'}",
            f"Data da Reunião: {result.meeting_date or 'Não identificada'}",
            "",
        ]
        
        # Resumo por tipo de ativo (da lista de ativos identificados)
        if result.assets:
            lines.append(f"ATIVOS IDENTIFICADOS: {len(result.assets)}")
            lines.append("")
            
            by_type: Dict[str, List] = {}
            for asset in result.assets:
                asset_type = asset.asset_type or "outros"
                if asset_type not in by_type:
                    by_type[asset_type] = []
                by_type[asset_type].append(asset)
            
            for asset_type, assets in sorted(by_type.items()):
                lines.append(f"  {asset_type.upper()}: {len(assets)}")
                for asset in assets:
                    asset_name = asset.ticker or asset.name[:40] if asset.name else "N/A"
                    lines.append(f"    • {asset_name}")
            
            lines.append("")
        
        # Resumo por tipo das quantidades/valores extraídos
        if result.asset_quantities:
            lines.append(f"VALORES EXTRAÍDOS: {len(result.asset_quantities)}")
            lines.append("")
            
            # Agrupa quantidades por tipo
            qty_by_type: Dict[str, List] = {}
            total_by_type: Dict[str, float] = {}
            
            for qty in result.asset_quantities:
                asset_type = qty.asset.asset_type or "outros"
                if asset_type not in qty_by_type:
                    qty_by_type[asset_type] = []
                    total_by_type[asset_type] = 0.0
                qty_by_type[asset_type].append(qty)
                if qty.total_value:
                    total_by_type[asset_type] += qty.total_value
            
            grand_total = 0.0
            for asset_type, quantities in sorted(qty_by_type.items()):
                type_total = total_by_type.get(asset_type, 0)
                grand_total += type_total
                lines.append(f"  {asset_type.upper()}: {len(quantities)} item(s) - R$ {type_total:,.2f}")
                for qty in quantities:
                    asset_name = qty.asset.name[:35] if qty.asset.name else "N/A"
                    value_str = f"R$ {qty.total_value:,.2f}" if qty.total_value else "N/A"
                    lines.append(f"    • {asset_name}... = {value_str}")
            
            lines.append("")
            lines.append(f"  TOTAL GERAL: R$ {grand_total:,.2f}")
            lines.append("")
        
        lines.extend([
            f"Tempo de processamento: {result.processing_time:.2f} segundos",
            "",
            self._separator("="),
            self._center("FIM DO RELATÓRIO"),
            self._separator("="),
        ])
        
        return lines


