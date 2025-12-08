"""
Gerador de PDF com highlights coloridos para Atas de Reunião.

Cria uma versão do documento original com marcações estilo marca-texto
para ativos e quantidades encontradas.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Dict, List, Tuple, Optional
import io

from PIL import Image, ImageDraw, ImageFont
import numpy as np

from ..core.pdf_reader import PDFReader
from .meeting_minutes_analyzer import MeetingMinutesResult

logger = logging.getLogger(__name__)


class MeetingMinutesPDFHighlighter:
    """
    Gera PDF com highlights coloridos para Atas de Reunião.
    
    Cores por categoria:
    - Laranja: Ativos (Cláusula A)
    - Azul: Quantidades/Valores (Cláusula B)
    - Verde: Info do Fundo
    - Rosa: Deliberações
    """
    
    # Cores RGB com transparência
    COLORS = {
        "assets": (255, 200, 0, 100),         # Laranja - Ativos
        "quantities": (0, 191, 255, 100),      # Azul claro - Quantidades
        "fund_info": (0, 255, 0, 100),         # Verde - Info do Fundo
        "deliberations": (255, 182, 193, 100)  # Rosa - Deliberações
    }
    
    # Labels para legenda
    LABELS = {
        "assets": "Ativos Identificados (Cláusula A)",
        "quantities": "Quantidades/Valores (Cláusula B)",
        "fund_info": "Informações do Fundo",
        "deliberations": "Deliberações"
    }
    
    # Keywords de ativos para highlight
    ASSET_KEYWORDS = [
        "CRA", "CRI", "CDB", "LCI", "LCA", "FII", "FIM", "FIC", "ETF",
        "debênture", "debêntures", "ações", "ação", "cotas", "cota",
        "título", "títulos", "Tesouro", "NTN", "LFT", "LTN"
    ]
    
    def __init__(self):
        self.reader = PDFReader()
        self._images: List[Image.Image] = []
    
    def generate_highlighted_pdf(
        self,
        pdf_path: Path,
        result: MeetingMinutesResult,
        output_path: Path
    ) -> Path:
        """
        Gera PDF com highlights.
        
        Args:
            pdf_path: Caminho do PDF original.
            result: Resultado da análise.
            output_path: Caminho para o PDF de saída.
        
        Returns:
            Path: Caminho do PDF gerado.
        """
        logger.info(f"Gerando PDF com highlights: {output_path}")
        
        # Lê o documento
        document = self.reader.read(pdf_path)
        
        # Processa cada página
        highlighted_images = []
        
        for page in document.pages:
            if page.image is None:
                continue
            
            # Converte para PIL Image se necessário
            if isinstance(page.image, np.ndarray):
                img = Image.fromarray(page.image)
            else:
                img = page.image.copy()
            
            # Aplica highlights baseado no conteúdo da página
            img = self._apply_highlights(
                img,
                page.text or "",
                page.page_number,
                result
            )
            
            highlighted_images.append(img)
        
        # Adiciona página de legenda no início
        legend_page = self._create_legend_page(
            highlighted_images[0].size if highlighted_images else (2480, 3508),
            result
        )
        
        all_pages = [legend_page] + highlighted_images
        
        # Salva como PDF
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        if all_pages:
            # Converte para RGB se necessário
            rgb_pages = []
            for img in all_pages:
                if img.mode == 'RGBA':
                    background = Image.new('RGB', img.size, (255, 255, 255))
                    background.paste(img, mask=img.split()[-1])
                    rgb_pages.append(background)
                elif img.mode != 'RGB':
                    rgb_pages.append(img.convert('RGB'))
                else:
                    rgb_pages.append(img)
            
            # Salva PDF
            rgb_pages[0].save(
                output_path,
                "PDF",
                save_all=True,
                append_images=rgb_pages[1:],
                resolution=150
            )
        
        logger.info(f"PDF com highlights gerado: {output_path}")
        return output_path
    
    def _apply_highlights(
        self,
        image: Image.Image,
        text: str,
        page_number: int,
        result: MeetingMinutesResult
    ) -> Image.Image:
        """Aplica highlights em uma página."""
        
        # Converte para RGBA para suportar transparência
        if image.mode != 'RGBA':
            image = image.convert('RGBA')
        
        # Cria layer de overlay
        overlay = Image.new('RGBA', image.size, (255, 255, 255, 0))
        draw = ImageDraw.Draw(overlay)
        
        text_lower = text.lower()
        
        # Highlight ativos
        if page_number in result.assets_pages:
            # Destaca keywords de ativos
            for keyword in self.ASSET_KEYWORDS:
                if keyword.lower() in text_lower:
                    self._highlight_text_in_image(
                        draw, image, text, keyword, self.COLORS["assets"]
                    )
            
            # Destaca ativos específicos encontrados
            for asset in result.assets:
                if asset.name and asset.name.lower()[:20] in text_lower:
                    self._highlight_text_in_image(
                        draw, image, text, asset.name[:30], self.COLORS["assets"]
                    )
                if asset.ticker and asset.ticker.lower() in text_lower:
                    self._highlight_text_in_image(
                        draw, image, text, asset.ticker, self.COLORS["assets"]
                    )
        
        # Highlight quantidades/valores
        if page_number in result.quantities_pages:
            # Destaca valores monetários (R$)
            import re
            values = re.findall(r'R\$\s*[\d.,]+', text)
            for val in values:
                self._highlight_text_in_image(
                    draw, image, text, val, self.COLORS["quantities"]
                )
            
            # Destaca quantidades numéricas seguidas de unidades
            qty_patterns = re.findall(r'\d+(?:[.,]\d+)*\s*(?:unidades?|cotas?|ações?)', text, re.IGNORECASE)
            for qty in qty_patterns:
                self._highlight_text_in_image(
                    draw, image, text, qty, self.COLORS["quantities"]
                )
        
        # Highlight info do fundo (primeiras páginas)
        if page_number <= 3:
            if result.fund_name and result.fund_name.lower() in text_lower:
                self._highlight_text_in_image(
                    draw, image, text, result.fund_name, self.COLORS["fund_info"]
                )
            if result.fund_cnpj and result.fund_cnpj in text:
                self._highlight_text_in_image(
                    draw, image, text, result.fund_cnpj, self.COLORS["fund_info"]
                )
        
        # Combina layers
        return Image.alpha_composite(image, overlay)
    
    def _highlight_text_in_image(
        self,
        draw: ImageDraw.Draw,
        image: Image.Image,
        full_text: str,
        search_text: str,
        color: Tuple[int, int, int, int]
    ) -> None:
        """
        Destaca texto em uma imagem.
        
        Esta é uma aproximação simples que adiciona faixas coloridas
        nas regiões onde o texto provavelmente está.
        """
        if not search_text:
            return
        
        # Encontra posição aproximada do texto
        text_lower = full_text.lower()
        search_lower = search_text.lower()
        
        # Calcula posição proporcional
        pos = text_lower.find(search_lower)
        if pos == -1:
            return
        
        # Estima posição vertical baseada na proporção do texto
        text_proportion = pos / max(len(full_text), 1)
        
        img_width, img_height = image.size
        
        # Margem (assume ~10% de margem em cada lado)
        margin_x = int(img_width * 0.1)
        margin_y = int(img_height * 0.05)
        
        # Área útil do texto
        text_area_width = img_width - 2 * margin_x
        text_area_height = img_height - 2 * margin_y
        
        # Posição Y estimada
        y_pos = margin_y + int(text_proportion * text_area_height)
        
        # Altura da linha de texto (estimada)
        line_height = int(img_height * 0.02)  # ~2% da altura
        
        # Largura do highlight (proporcional ao tamanho do texto)
        highlight_width = min(
            int(len(search_text) / 50 * text_area_width),
            text_area_width
        )
        
        # Desenha retângulo de highlight
        x1 = margin_x
        y1 = y_pos - line_height // 2
        x2 = margin_x + highlight_width
        y2 = y_pos + line_height // 2
        
        # Garante que está dentro dos limites
        y1 = max(margin_y, min(y1, img_height - margin_y - line_height))
        y2 = max(margin_y + line_height, min(y2, img_height - margin_y))
        
        draw.rectangle([x1, y1, x2, y2], fill=color)
    
    def _create_legend_page(
        self,
        size: Tuple[int, int],
        result: MeetingMinutesResult
    ) -> Image.Image:
        """Cria página de legenda no início do documento."""
        
        img = Image.new('RGB', size, (255, 255, 255))
        draw = ImageDraw.Draw(img)
        
        # Tenta carregar fonte
        try:
            font_large = ImageFont.truetype("arial.ttf", 60)
            font_medium = ImageFont.truetype("arial.ttf", 40)
            font_small = ImageFont.truetype("arial.ttf", 30)
        except:
            font_large = ImageFont.load_default()
            font_medium = font_large
            font_small = font_large
        
        width, height = size
        y = 100
        
        # Título
        title = "ANÁLISE DE ATA DE REUNIÃO"
        draw.text((width // 2, y), title, fill=(0, 0, 0), font=font_large, anchor="mt")
        y += 100
        
        subtitle = "Documento com Destaques - Ativos e Quantidades"
        draw.text((width // 2, y), subtitle, fill=(100, 100, 100), font=font_medium, anchor="mt")
        y += 150
        
        # Legenda de cores
        draw.text((100, y), "LEGENDA DE CORES:", fill=(0, 0, 0), font=font_medium)
        y += 80
        
        for key, label in self.LABELS.items():
            color = self.COLORS[key][:3]  # RGB sem alpha
            
            # Retângulo de cor
            draw.rectangle([100, y, 200, y + 40], fill=color)
            
            # Texto
            draw.text((220, y + 5), label, fill=(0, 0, 0), font=font_small)
            y += 60
        
        y += 50
        
        # Resumo da análise
        draw.text((100, y), "RESUMO DA ANÁLISE:", fill=(0, 0, 0), font=font_medium)
        y += 80
        
        summary = [
            f"• Nome do Fundo: {result.fund_name or 'Não identificado'}",
            f"• CNPJ: {result.fund_cnpj or 'Não identificado'}",
            f"• Data da Reunião: {result.meeting_date or 'Não identificada'}",
            f"• Ativos identificados: {len(result.assets)}",
            f"• Quantidades extraídas: {len(result.asset_quantities)}",
        ]
        
        for line in summary:
            draw.text((120, y), line, fill=(0, 0, 0), font=font_small)
            y += 50
        
        y += 50
        
        # Lista de ativos por tipo
        if result.assets:
            draw.text((100, y), "ATIVOS IDENTIFICADOS:", fill=(0, 0, 0), font=font_medium)
            y += 60
            
            # Agrupa por tipo
            by_type: Dict[str, List] = {}
            for asset in result.assets:
                asset_type = asset.asset_type or "Outros"
                if asset_type not in by_type:
                    by_type[asset_type] = []
                by_type[asset_type].append(asset)
            
            for asset_type, assets in list(by_type.items())[:5]:  # Limita a 5 tipos
                type_label = {
                    "ação": "Ações",
                    "CRA": "CRA",
                    "CRI": "CRI",
                    "debênture": "Debêntures",
                    "cota_fundo": "Cotas de Fundo",
                    "CDB": "CDB",
                    "LCI": "LCI",
                    "LCA": "LCA",
                    "titulo_publico": "Títulos Públicos"
                }.get(asset_type, asset_type)
                
                text = f"  • {type_label}: {len(assets)} encontrado(s)"
                draw.text((120, y), text, fill=(0, 0, 0), font=font_small)
                y += 40
        
        y += 50
        
        # Detalhes de quantidades
        if result.asset_quantities:
            draw.text((100, y), "VALORES IDENTIFICADOS:", fill=(0, 0, 0), font=font_medium)
            y += 60
            
            for qty in result.asset_quantities[:5]:  # Limita a 5
                text = f"  • {qty.asset.asset_type or 'Ativo'}"
                if qty.quantity:
                    text += f": {qty.quantity:,.0f} unidades"
                if qty.total_value:
                    text += f" (R$ {qty.total_value:,.2f})"
                draw.text((120, y), text[:80], fill=(0, 0, 0), font=font_small)
                y += 40
        
        # Rodapé
        footer_y = height - 100
        draw.line([(100, footer_y - 20), (width - 100, footer_y - 20)], fill=(200, 200, 200), width=2)
        
        from datetime import datetime
        footer = f"Gerado em {datetime.now().strftime('%d/%m/%Y %H:%M')}"
        draw.text((width // 2, footer_y), footer, fill=(150, 150, 150), font=font_small, anchor="mt")
        
        return img
    
    def generate_highlighted_images(
        self,
        pdf_path: Path,
        result: MeetingMinutesResult,
        output_dir: Path
    ) -> List[Path]:
        """
        Gera imagens PNG individuais com highlights.
        
        Args:
            pdf_path: Caminho do PDF original.
            result: Resultado da análise.
            output_dir: Diretório de saída.
        
        Returns:
            List[Path]: Lista de caminhos das imagens geradas.
        """
        logger.info(f"Gerando imagens com highlights em: {output_dir}")
        
        # Lê o documento
        document = self.reader.read(pdf_path)
        
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        output_paths = []
        
        for page in document.pages:
            if page.image is None:
                continue
            
            # Converte para PIL Image
            if isinstance(page.image, np.ndarray):
                img = Image.fromarray(page.image)
            else:
                img = page.image.copy()
            
            # Aplica highlights
            img = self._apply_highlights(
                img,
                page.text or "",
                page.page_number,
                result
            )
            
            # Converte para RGB
            if img.mode == 'RGBA':
                background = Image.new('RGB', img.size, (255, 255, 255))
                background.paste(img, mask=img.split()[-1])
                img = background
            
            # Salva
            output_path = output_dir / f"page_{page.page_number:03d}_highlighted.png"
            img.save(output_path, "PNG")
            output_paths.append(output_path)
        
        logger.info(f"Geradas {len(output_paths)} imagens com highlights")
        return output_paths

