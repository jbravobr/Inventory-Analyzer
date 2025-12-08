"""
Gerador de relatórios em TXT para análise de inventário.
"""

from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path
from typing import Optional

from .analyzer import InventoryAnalysisResult

logger = logging.getLogger(__name__)


class ReportGenerator:
    """Gera relatórios em formato TXT."""
    
    def __init__(self):
        self.line_width = 80
    
    def generate(
        self,
        result: InventoryAnalysisResult,
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
        
        # Cláusula A - Herdeiros
        lines.extend(self._generate_heirs_section(result))
        lines.append("")
        
        # Cláusula B - Inventariante
        lines.extend(self._generate_administrator_section(result))
        lines.append("")
        
        # Cláusula C - Bens BTG
        lines.extend(self._generate_btg_section(result))
        lines.append("")
        
        # Cláusula D - Divisão
        lines.extend(self._generate_division_section(result))
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
            self._center("RELATÓRIO DE ANÁLISE DE INVENTÁRIO"),
            self._separator("="),
            "",
            f"Data de Geração: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}",
        ]
        
        if source_file:
            lines.append(f"Documento Analisado: {source_file}")
        
        return lines
    
    def _generate_general_info(self, result: InventoryAnalysisResult) -> list:
        lines = [
            self._separator("-"),
            "INFORMAÇÕES GERAIS",
            self._separator("-"),
        ]
        
        if result.deceased_name:
            lines.append(f"Falecido (Autor da Herança): {result.deceased_name}")
        else:
            lines.append("Falecido (Autor da Herança): Não identificado")
        
        if result.death_date:
            lines.append(f"Data do Óbito: {result.death_date}")
        
        if result.notary_office:
            lines.append(f"Cartório: {result.notary_office}")
        
        lines.append(f"Total de Páginas Analisadas: {result.total_pages}")
        
        return lines
    
    def _generate_heirs_section(self, result: InventoryAnalysisResult) -> list:
        lines = [
            self._separator("="),
            "CLÁUSULA A - HERDEIROS IDENTIFICADOS",
            self._separator("="),
        ]
        
        if not result.heirs:
            lines.append("")
            lines.append(">>> NENHUM HERDEIRO IDENTIFICADO <<<")
            lines.append("")
            lines.append("Contexto encontrado:")
            lines.append(result.heirs_raw_text[:500] if result.heirs_raw_text else "Nenhum contexto relevante encontrado.")
        else:
            lines.append("")
            lines.append(f"Total de herdeiros encontrados: {len(result.heirs)}")
            lines.append(f"Páginas de referência: {result.heirs_pages}")
            lines.append(f"Nível de confiança: {result.confidence_scores.get('heirs', 0)*100:.0f}%")
            lines.append("")
            
            for i, heir in enumerate(result.heirs, 1):
                lines.append(f"  {i}. {heir.name}")
                if heir.cpf:
                    lines.append(f"     CPF: {heir.cpf}")
                if heir.relationship:
                    lines.append(f"     Parentesco: {heir.relationship}")
                if heir.is_minor:
                    lines.append(f"     MENOR DE IDADE")
                    if heir.legal_representative:
                        lines.append(f"     Representante Legal: {heir.legal_representative}")
                lines.append("")
        
        return lines
    
    def _generate_administrator_section(self, result: InventoryAnalysisResult) -> list:
        lines = [
            self._separator("="),
            "CLÁUSULA B - INVENTARIANTE NOMEADO",
            self._separator("="),
        ]
        
        if not result.administrator_name:
            lines.append("")
            lines.append(">>> INVENTARIANTE NÃO IDENTIFICADO <<<")
            lines.append("")
            lines.append("Contexto encontrado:")
            lines.append(result.administrator_raw_text[:500] if result.administrator_raw_text else "Nenhum contexto relevante encontrado.")
        else:
            lines.append("")
            lines.append(f"Nome: {result.administrator_name}")
            
            if result.administrator_cpf:
                lines.append(f"CPF: {result.administrator_cpf}")
            
            lines.append(f"É também herdeiro: {'SIM' if result.administrator_is_heir else 'NÃO'}")
            lines.append(f"Páginas de referência: {result.administrator_pages}")
            lines.append(f"Nível de confiança: {result.confidence_scores.get('administrator', 0)*100:.0f}%")
        
        return lines
    
    def _generate_btg_section(self, result: InventoryAnalysisResult) -> list:
        lines = [
            self._separator("="),
            "CLÁUSULA C - BENS COM MENÇÃO A BTG",
            self._separator("="),
        ]
        
        if not result.btg_assets:
            lines.append("")
            lines.append(">>> NENHUM BEM BTG IDENTIFICADO <<<")
            lines.append("")
            lines.append("O documento não contém menção a bens ou ativos")
            lines.append("relacionados ao BTG Pactual.")
            
            if result.btg_raw_text:
                lines.append("")
                lines.append("Contexto pesquisado:")
                lines.append(result.btg_raw_text[:500])
        else:
            lines.append("")
            lines.append(f"Total de bens BTG encontrados: {len(result.btg_assets)}")
            lines.append(f"Páginas de referência: {result.btg_pages}")
            lines.append(f"Nível de confiança: {result.confidence_scores.get('btg_assets', 0)*100:.0f}%")
            lines.append("")
            
            total_value = 0
            
            for i, asset in enumerate(result.btg_assets, 1):
                lines.append(f"  BEM {i}:")
                lines.append(f"  {'-' * 40}")
                
                if asset.asset_type:
                    lines.append(f"    Tipo: {asset.asset_type}")
                
                if asset.account_number:
                    lines.append(f"    Conta/Identificador: {asset.account_number}")
                
                if asset.value:
                    lines.append(f"    Valor: R$ {asset.value:,.2f}")
                    total_value += asset.value
                
                lines.append(f"    Descrição: {asset.description[:200]}...")
                lines.append("")
            
            if total_value > 0:
                lines.append(f"  VALOR TOTAL DOS BENS BTG: R$ {total_value:,.2f}")
        
        return lines
    
    def _generate_division_section(self, result: InventoryAnalysisResult) -> list:
        lines = [
            self._separator("="),
            "CLÁUSULA D - DIVISÃO DOS BENS BTG ENTRE HERDEIROS",
            self._separator("="),
        ]
        
        if not result.btg_assets:
            lines.append("")
            lines.append(">>> NÃO APLICÁVEL <<<")
            lines.append("")
            lines.append("Não foram encontrados bens BTG para análise de divisão.")
        elif not result.asset_divisions:
            lines.append("")
            lines.append(">>> DIVISÃO NÃO IDENTIFICADA <<<")
            lines.append("")
            lines.append("Bens BTG foram encontrados, mas não foi possível")
            lines.append("identificar a divisão entre os herdeiros.")
            lines.append("")
            lines.append("Contexto encontrado:")
            lines.append(result.divisions_raw_text[:500] if result.divisions_raw_text else "Nenhum contexto de divisão encontrado.")
        else:
            lines.append("")
            lines.append(f"Páginas de referência: {result.divisions_pages}")
            lines.append(f"Nível de confiança: {result.confidence_scores.get('divisions', 0)*100:.0f}%")
            lines.append("")
            
            for division in result.asset_divisions:
                lines.append(f"  BEM: {division.asset.description[:50]}...")
                if division.asset.asset_type:
                    lines.append(f"  Tipo: {division.asset.asset_type}")
                lines.append("")
                
                lines.append("  DIVISÃO:")
                for div in division.divisions:
                    heir_name = div.get("herdeiro", "N/A")
                    percentage = div.get("percentual", 0)
                    value = div.get("valor")
                    
                    line = f"    - {heir_name}: {percentage:.1f}%"
                    if value:
                        line += f" (R$ {value:,.2f})"
                    lines.append(line)
                
                lines.append("")
        
        return lines
    
    def _generate_footer(self, result: InventoryAnalysisResult) -> list:
        lines = [
            self._separator("="),
            "RESUMO DA ANÁLISE",
            self._separator("="),
            "",
            f"Herdeiros identificados: {len(result.heirs)}",
            f"Inventariante identificado: {'SIM' if result.administrator_name else 'NÃO'}",
            f"Bens BTG encontrados: {len(result.btg_assets)}",
            f"Divisões identificadas: {len(result.asset_divisions)}",
            "",
            f"Tempo de processamento: {result.processing_time:.2f} segundos",
            "",
            self._separator("="),
            self._center("FIM DO RELATÓRIO"),
            self._separator("="),
        ]
        
        return lines

