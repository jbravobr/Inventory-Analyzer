"""
Gerador de PDF com highlights coloridos.

Cria uma versão do documento original com marcações estilo marca-texto
para cada tipo de informação encontrada.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Dict, List, Tuple, Optional
import io

from PIL import Image, ImageDraw, ImageFont
import numpy as np

from ..core.pdf_reader import PDFReader
from .analyzer import InventoryAnalysisResult

logger = logging.getLogger(__name__)


class PDFHighlighter:
    """
    Gera PDF com highlights coloridos.
    
    Cores por categoria:
    - Amarelo: Herdeiros (Cláusula A)
    - Verde: Inventariante (Cláusula B)
    - Azul: Bens BTG (Cláusula C)
    - Rosa: Divisão (Cláusula D)
    """
    
    # Cores RGB com transparência
    COLORS = {
        "heirs": (255, 255, 0, 100),         # Amarelo
        "administrator": (0, 255, 0, 100),    # Verde
        "btg_assets": (0, 191, 255, 100),     # Azul claro
        "divisions": (255, 182, 193, 100)     # Rosa
    }
    
    # Labels para legenda
    LABELS = {
        "heirs": "Herdeiros (Cláusula A)",
        "administrator": "Inventariante (Cláusula B)",
        "btg_assets": "Bens BTG (Cláusula C)",
        "divisions": "Divisão (Cláusula D)"
    }
    
    def __init__(self):
        self.reader = PDFReader()
        self._images: List[Image.Image] = []
    
    def generate_highlighted_pdf(
        self,
        pdf_path: Path,
        result: InventoryAnalysisResult,
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
        result: InventoryAnalysisResult
    ) -> Image.Image:
        """Aplica highlights em uma página."""
        
        # Converte para RGBA para suportar transparência
        if image.mode != 'RGBA':
            image = image.convert('RGBA')
        
        # Cria layer de overlay
        overlay = Image.new('RGBA', image.size, (255, 255, 255, 0))
        draw = ImageDraw.Draw(overlay)
        
        text_lower = text.lower()
        
        # Highlight herdeiros
        if page_number in result.heirs_pages:
            for heir in result.heirs:
                if heir.name and heir.name.lower() in text_lower:
                    self._highlight_text_in_image(
                        draw, image, text, heir.name, self.COLORS["heirs"]
                    )
        
        # Highlight inventariante
        if page_number in result.administrator_pages:
            if result.administrator_name and result.administrator_name.lower() in text_lower:
                self._highlight_text_in_image(
                    draw, image, text, result.administrator_name, 
                    self.COLORS["administrator"]
                )
        
        # Highlight BTG
        if page_number in result.btg_pages:
            # Sempre destaca "BTG"
            if "btg" in text_lower:
                self._highlight_text_in_image(
                    draw, image, text, "BTG", self.COLORS["btg_assets"]
                )
            # Destaca números de conta
            for asset in result.btg_assets:
                if asset.account_number and asset.account_number in text:
                    self._highlight_text_in_image(
                        draw, image, text, asset.account_number,
                        self.COLORS["btg_assets"]
                    )
        
        # Highlight divisões
        if page_number in result.divisions_pages:
            # Destaca percentuais
            import re
            percentages = re.findall(r'\d+[,.]?\d*\s*%', text)
            for pct in percentages:
                self._highlight_text_in_image(
                    draw, image, text, pct, self.COLORS["divisions"]
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
        result: InventoryAnalysisResult
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
        title = "ANÁLISE DE INVENTÁRIO"
        draw.text((width // 2, y), title, fill=(0, 0, 0), font=font_large, anchor="mt")
        y += 100
        
        subtitle = "Documento com Destaques"
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
            f"• Herdeiros identificados: {len(result.heirs)}",
            f"• Inventariante: {result.administrator_name or 'Não identificado'}",
            f"• Bens BTG encontrados: {len(result.btg_assets)}",
            f"• Divisões identificadas: {len(result.asset_divisions)}",
        ]
        
        for line in summary:
            draw.text((120, y), line, fill=(0, 0, 0), font=font_small)
            y += 50
        
        y += 50
        
        # Lista de herdeiros
        if result.heirs:
            draw.text((100, y), "HERDEIROS:", fill=(0, 0, 0), font=font_medium)
            y += 60
            
            for heir in result.heirs[:10]:  # Limita a 10
                text = f"  • {heir.name}"
                if heir.relationship:
                    text += f" ({heir.relationship})"
                draw.text((120, y), text, fill=(0, 0, 0), font=font_small)
                y += 40
        
        y += 50
        
        # Bens BTG
        if result.btg_assets:
            draw.text((100, y), "BENS BTG:", fill=(0, 0, 0), font=font_medium)
            y += 60
            
            for asset in result.btg_assets[:5]:  # Limita a 5
                text = f"  • {asset.asset_type or 'Ativo'}"
                if asset.value:
                    text += f": R$ {asset.value:,.2f}"
                draw.text((120, y), text, fill=(0, 0, 0), font=font_small)
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
        result: InventoryAnalysisResult,
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

