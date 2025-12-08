"""Módulo para geração dos arquivos de saída."""

from __future__ import annotations

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Tuple

import cv2
import numpy as np

from config.settings import Settings, get_settings
from models.document import Document, Page
from models.search_result import SearchResult, SearchMatch

logger = logging.getLogger(__name__)


class OutputGenerator:
    """
    Gerador de arquivos de saída.
    
    Produz três tipos de saída:
    1. Arquivo com textos encontrados
    2. Imagens com texto destacado (usando OpenCV)
    3. Relatório de páginas onde textos foram encontrados
    """
    
    def __init__(self, settings: Optional[Settings] = None):
        """
        Inicializa o gerador.
        
        Args:
            settings: Configurações do aplicativo.
        """
        self.settings = settings or get_settings()
        self.highlight_color = self.settings.output.highlight_color
        self.highlight_opacity = self.settings.output.highlight_opacity
    
    def generate_all(
        self,
        document: Document,
        search_result: SearchResult,
        output_dir: Path
    ) -> dict:
        """
        Gera todos os arquivos de saída.
        
        Args:
            document: Documento processado.
            search_result: Resultados da busca.
            output_dir: Diretório de saída.
        
        Returns:
            dict: Caminhos dos arquivos gerados.
        """
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        base_name = document.source_path.stem
        
        generated_files = {}
        
        # 1. Arquivo com textos encontrados
        found_texts_path = output_dir / f"{base_name}_{timestamp}_found_texts.txt"
        self.generate_found_texts(search_result, found_texts_path)
        generated_files["found_texts"] = str(found_texts_path)
        
        # 2. Imagens com destaque
        if search_result.found_any:
            highlighted_dir = output_dir / f"{base_name}_{timestamp}_highlighted"
            highlighted_paths = self.generate_highlighted_images(
                document, search_result, highlighted_dir
            )
            generated_files["highlighted_images"] = highlighted_paths
        
        # 3. Relatório de páginas
        report_path = output_dir / f"{base_name}_{timestamp}_report.json"
        self.generate_page_report(document, search_result, report_path)
        generated_files["report"] = str(report_path)
        
        logger.info(f"Arquivos gerados em: {output_dir}")
        
        return generated_files
    
    def generate_found_texts(
        self,
        search_result: SearchResult,
        output_path: Path
    ) -> None:
        """
        Gera arquivo com todos os textos encontrados.
        
        Args:
            search_result: Resultados da busca.
            output_path: Caminho do arquivo de saída.
        """
        output_path = Path(output_path)
        
        with open(output_path, "w", encoding="utf-8") as f:
            f.write("=" * 60 + "\n")
            f.write("TEXTOS ENCONTRADOS NO DOCUMENTO\n")
            f.write(f"Gerado em: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}\n")
            f.write("=" * 60 + "\n\n")
            
            if not search_result.found_any:
                f.write("Nenhum texto encontrado para as instruções fornecidas.\n")
                return
            
            for instr_match in search_result.instruction_matches:
                f.write("-" * 60 + "\n")
                f.write(f"INSTRUÇÃO {instr_match.instruction_index + 1}:\n")
                f.write(f"{instr_match.instruction}\n")
                f.write("-" * 60 + "\n\n")
                
                if not instr_match.found:
                    f.write("  [Não encontrado]\n\n")
                    continue
                
                for i, match in enumerate(instr_match.matches, 1):
                    f.write(f"  Match {i} (Score: {match.score:.2f}):\n")
                    f.write(f"  Página: {match.position.page}\n")
                    f.write(f"  Texto: {match.text}\n")
                    if match.context_before or match.context_after:
                        f.write(f"  Contexto: ...{match.context_before} [{match.text}] {match.context_after}...\n")
                    f.write("\n")
        
        logger.info(f"Arquivo de textos encontrados: {output_path}")
    
    def generate_highlighted_images(
        self,
        document: Document,
        search_result: SearchResult,
        output_dir: Path
    ) -> List[str]:
        """
        Gera imagens com texto destacado usando OpenCV.
        
        Args:
            document: Documento com imagens das páginas.
            search_result: Resultados da busca.
            output_dir: Diretório de saída.
        
        Returns:
            List[str]: Caminhos das imagens geradas.
        """
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        generated_paths = []
        pages_with_matches = search_result.all_pages
        
        for page_num in pages_with_matches:
            page = document.get_page(page_num)
            
            if page is None or page.image is None:
                logger.warning(f"Página {page_num} sem imagem disponível")
                continue
            
            # Obtém matches desta página
            page_matches = search_result.get_matches_by_page(page_num)
            
            if not page_matches:
                continue
            
            # Cria imagem destacada
            highlighted_image = self._highlight_text_in_image(
                page.image.image.copy(),
                page.text,
                page_matches
            )
            
            # Salva imagem
            output_format = self.settings.output.output_format
            output_path = output_dir / f"page_{page_num:03d}.{output_format}"
            
            # Converte RGB para BGR para OpenCV salvar corretamente
            if len(highlighted_image.shape) == 3:
                highlighted_image = cv2.cvtColor(highlighted_image, cv2.COLOR_RGB2BGR)
            
            cv2.imwrite(str(output_path), highlighted_image)
            generated_paths.append(str(output_path))
            
            logger.debug(f"Imagem destacada gerada: {output_path}")
        
        logger.info(f"Geradas {len(generated_paths)} imagens destacadas")
        
        return generated_paths
    
    def _highlight_text_in_image(
        self,
        image: np.ndarray,
        page_text: str,
        matches: List[SearchMatch]
    ) -> np.ndarray:
        """
        Destaca texto encontrado na imagem da página.
        
        Usa técnica de overlay com cor de destaque.
        
        Args:
            image: Imagem da página.
            page_text: Texto completo da página.
            matches: Lista de matches para destacar.
        
        Returns:
            np.ndarray: Imagem com destaques.
        """
        # Cria overlay para os destaques
        overlay = image.copy()
        
        # Estimativa de posição baseada em proporção do texto
        # (aproximação quando não temos coordenadas exatas do OCR)
        text_length = len(page_text) if page_text else 1
        height, width = image.shape[:2]
        
        # Área aproximada de texto (margem de 10%)
        margin_x = int(width * 0.1)
        margin_y = int(height * 0.1)
        text_width = width - 2 * margin_x
        text_height = height - 2 * margin_y
        
        for match in matches:
            # Calcula posição aproximada baseada na posição do caractere
            char_start = match.position.start_char
            char_end = match.position.end_char
            
            # Proporção no texto
            start_ratio = char_start / text_length
            end_ratio = char_end / text_length
            
            # Converte para coordenadas de imagem (layout vertical)
            y_start = margin_y + int(start_ratio * text_height)
            y_end = margin_y + int(end_ratio * text_height)
            
            # Garante altura mínima visível
            if y_end - y_start < 20:
                y_end = y_start + 20
            
            # Desenha retângulo de destaque
            pt1 = (margin_x, max(0, y_start - 5))
            pt2 = (width - margin_x, min(height, y_end + 5))
            
            cv2.rectangle(
                overlay,
                pt1,
                pt2,
                self.highlight_color,
                -1  # Preenchido
            )
        
        # Combina overlay com imagem original usando alpha blending
        alpha = self.highlight_opacity
        result = cv2.addWeighted(overlay, alpha, image, 1 - alpha, 0)
        
        return result
    
    def generate_page_report(
        self,
        document: Document,
        search_result: SearchResult,
        output_path: Path
    ) -> None:
        """
        Gera relatório JSON com informações das páginas.
        
        Args:
            document: Documento processado.
            search_result: Resultados da busca.
            output_path: Caminho do arquivo de saída.
        """
        output_path = Path(output_path)
        
        report = {
            "documento": {
                "arquivo": str(document.source_path),
                "total_paginas": document.total_pages,
                "total_palavras": document.total_words,
                "confianca_media_ocr": round(document.average_confidence, 2),
            },
            "busca": {
                "total_instrucoes": len(search_result.instruction_matches),
                "instrucoes_satisfeitas": search_result.found_count,
                "total_matches": search_result.total_matches,
                "tempo_busca_segundos": round(search_result.search_time, 2),
            },
            "paginas_com_matches": [],
            "detalhes_por_pagina": {},
            "resultados_por_instrucao": []
        }
        
        # Páginas com matches
        report["paginas_com_matches"] = search_result.all_pages
        
        # Detalhes por página
        for page_num in search_result.all_pages:
            page_matches = search_result.get_matches_by_page(page_num)
            report["detalhes_por_pagina"][str(page_num)] = {
                "quantidade_matches": len(page_matches),
                "matches": [
                    {
                        "texto": m.text[:100] + "..." if len(m.text) > 100 else m.text,
                        "score": round(m.score, 2),
                        "tipo": m.match_type,
                        "posicao_char": m.position.start_char
                    }
                    for m in page_matches
                ]
            }
        
        # Resultados por instrução
        for instr_match in search_result.instruction_matches:
            report["resultados_por_instrucao"].append({
                "indice": instr_match.instruction_index,
                "instrucao": instr_match.instruction,
                "encontrado": instr_match.found,
                "quantidade_matches": len(instr_match.matches),
                "paginas": instr_match.pages_found
            })
        
        # Salva JSON
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        
        logger.info(f"Relatório gerado: {output_path}")
    
    def generate_summary_text(
        self,
        document: Document,
        search_result: SearchResult
    ) -> str:
        """
        Gera resumo textual dos resultados.
        
        Args:
            document: Documento processado.
            search_result: Resultados da busca.
        
        Returns:
            str: Resumo formatado.
        """
        lines = [
            "=" * 60,
            "RESUMO DA ANÁLISE DO CONTRATO",
            "=" * 60,
            "",
            f"Documento: {document.source_path.name}",
            f"Total de páginas: {document.total_pages}",
            f"Total de palavras: {document.total_words}",
            f"Confiança média OCR: {document.average_confidence:.1%}",
            "",
            "-" * 60,
            "RESULTADOS DA BUSCA",
            "-" * 60,
            "",
            f"Instruções processadas: {len(search_result.instruction_matches)}",
            f"Instruções satisfeitas: {search_result.found_count}",
            f"Total de matches: {search_result.total_matches}",
            f"Páginas com resultados: {', '.join(map(str, search_result.all_pages)) or 'Nenhuma'}",
            f"Tempo de busca: {search_result.search_time:.2f}s",
            "",
        ]
        
        if search_result.found_any:
            lines.extend([
                "-" * 60,
                "INSTRUÇÕES SATISFEITAS",
                "-" * 60,
                ""
            ])
            
            for instr in search_result.instruction_matches:
                status = "✓" if instr.found else "✗"
                lines.append(f"  {status} {instr.instruction}")
                if instr.found:
                    lines.append(f"      → Encontrado em: página(s) {', '.join(map(str, instr.pages_found))}")
        
        return "\n".join(lines)
