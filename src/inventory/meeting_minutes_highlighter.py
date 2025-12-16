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

from core.pdf_reader import PDFReader
from core.ocr_extractor import OCRExtractor
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
    
    # Keywords de ativos para highlight - padrões específicos para evitar falsos positivos
    ASSET_KEYWORDS = [
        # Siglas específicas (word boundaries)
        "CRA", "CRI", "CDB", "LCI", "LCA", "FII", "FIM", "FIC", "ETF",
        "FICFIA", "FICFIM", "FIDC", "FIP",
        # Títulos públicos
        "Tesouro", "Tesouro Selic", "Tesouro IPCA", "NTN-B", "NTN-F", "LFT", "LTN",
        # Outros (com cuidado)
        "debênture", "debêntures",
    ]
    
    # Padrões REGEX para highlight (mais precisos)
    HIGHLIGHT_PATTERNS = {
        "assets": [
            r'\b(CRA|CRI|CDB|LCI|LCA|FII|FIM|FIC|FICFIA|FICFIM|ETF|FIDC|FIP)\b',
            r'\bTesouro\s+(?:Selic|IPCA|Direto|Prefixado)\b',
            r'\b(NTN-?[BF]|LFT|LTN)\b',
            r'\bdebêntures?\b',
            r'\b[A-Z]{4}\d{1,2}\b',  # Tickers de ações
        ],
        "quantities": [
            r'R\$\s*[\d.,]+',
            r'\d+(?:[.,]\d+)*\s*(?:cotas?|unidades?)',
        ]
    }
    
    def __init__(self):
        self.reader = PDFReader()
        self.ocr = OCRExtractor()
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
        
        # Executa OCR para extrair texto das páginas
        logger.info("Executando OCR para extração de texto...")
        self.ocr.extract(document)
        
        # Processa cada página
        highlighted_images = []
        
        for page in document.pages:
            if page.image is None:
                continue
            
            # Converte para PIL Image se necessário
            if isinstance(page.image, np.ndarray):
                img = Image.fromarray(page.image)
            elif hasattr(page.image, 'image'):
                # PageImage object - acessa o array interno
                img = Image.fromarray(page.image.image)
            else:
                img = page.image.copy()
            
            # Aplica highlights baseado no conteúdo da página
            img = self._apply_highlights(
                img,
                page.text or "",
                page.number,
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
        """Aplica highlights em uma página usando padrões regex."""
        import re
        
        # Converte para RGBA para suportar transparência
        if image.mode != 'RGBA':
            image = image.convert('RGBA')
        
        # Cria layer de overlay
        overlay = Image.new('RGBA', image.size, (255, 255, 255, 0))
        draw = ImageDraw.Draw(overlay)
        
        text_lower = text.lower()
        highlighted_positions = []  # Para evitar sobreposição
        
        # Highlight ativos usando padrões REGEX
        if page_number in result.assets_pages or not result.assets_pages:
            for pattern in self.HIGHLIGHT_PATTERNS.get("assets", []):
                try:
                    for match in re.finditer(pattern, text, re.IGNORECASE):
                        matched_text = match.group(0)
                        pos = match.start()
                        
                        # Evita highlights muito próximos
                        if not any(abs(pos - p) < 20 for p in highlighted_positions):
                            self._highlight_at_position(
                                draw, image, text, pos, len(matched_text),
                                self.COLORS["assets"]
                            )
                            highlighted_positions.append(pos)
                except re.error:
                    continue
            
            # Destaca tickers específicos encontrados
            for asset in result.assets:
                if asset.ticker:
                    ticker_pattern = rf'\b{re.escape(asset.ticker)}\b'
                    for match in re.finditer(ticker_pattern, text, re.IGNORECASE):
                        pos = match.start()
                        if not any(abs(pos - p) < 20 for p in highlighted_positions):
                            self._highlight_at_position(
                                draw, image, text, pos, len(asset.ticker),
                                self.COLORS["assets"]
                            )
                            highlighted_positions.append(pos)
        
        # Highlight quantidades/valores
        if page_number in result.quantities_pages or not result.quantities_pages:
            for pattern in self.HIGHLIGHT_PATTERNS.get("quantities", []):
                try:
                    for match in re.finditer(pattern, text, re.IGNORECASE):
                        matched_text = match.group(0)
                        pos = match.start()
                        
                        if not any(abs(pos - p) < 20 for p in highlighted_positions):
                            self._highlight_at_position(
                                draw, image, text, pos, len(matched_text),
                                self.COLORS["quantities"]
                            )
                            highlighted_positions.append(pos)
                except re.error:
                    continue
        
        # Highlight info do fundo (primeiras páginas)
        if page_number <= 3:
            if result.fund_cnpj:
                pos = text.find(result.fund_cnpj)
                if pos != -1:
                    self._highlight_at_position(
                        draw, image, text, pos, len(result.fund_cnpj),
                        self.COLORS["fund_info"]
                    )
        
        # Combina layers
        return Image.alpha_composite(image, overlay)
    
    def _highlight_at_position(
        self,
        draw: ImageDraw.Draw,
        image: Image.Image,
        full_text: str,
        char_position: int,
        text_length: int,
        color: Tuple[int, int, int, int]
    ) -> None:
        """
        Destaca texto em uma imagem em uma posição específica.
        
        Usa a posição do caractere no texto para estimar a posição
        na imagem de forma mais precisa.
        """
        if char_position < 0:
            return
        
        img_width, img_height = image.size
        
        # Parâmetros ajustados para documentos típicos
        margin_x = int(img_width * 0.08)  # 8% de margem horizontal
        margin_y = int(img_height * 0.04)  # 4% de margem superior
        
        # Área útil do texto (onde o conteúdo está)
        text_area_width = img_width - 2 * margin_x
        text_area_height = img_height - 2 * margin_y
        
        # Estima caracteres por linha (baseado em documento A4 típico)
        chars_per_line = 80
        
        # Calcula linha e coluna aproximadas
        line_num = char_position // chars_per_line
        col_num = char_position % chars_per_line
        
        # Estima total de linhas no documento
        total_lines = max(len(full_text) // chars_per_line, 1)
        
        # Altura de cada linha
        line_height = text_area_height / max(total_lines, 40)  # Mínimo 40 linhas
        line_height = max(line_height, 15)  # Mínimo 15 pixels
        line_height = min(line_height, 40)  # Máximo 40 pixels
        
        # Posição Y
        y_pos = margin_y + int(line_num * line_height)
        
        # Posição X (baseada na coluna)
        x_start = margin_x + int((col_num / chars_per_line) * text_area_width)
        
        # Largura do highlight
        char_width = text_area_width / chars_per_line
        highlight_width = int(text_length * char_width)
        highlight_width = max(highlight_width, 50)  # Mínimo 50 pixels
        highlight_width = min(highlight_width, text_area_width - x_start + margin_x)
        
        # Coordenadas do retângulo
        x1 = x_start
        y1 = y_pos
        x2 = x_start + highlight_width
        y2 = y_pos + int(line_height * 1.2)  # Um pouco mais alto
        
        # Garante que está dentro dos limites
        x1 = max(margin_x, min(x1, img_width - margin_x))
        x2 = max(x1 + 50, min(x2, img_width - margin_x))
        y1 = max(margin_y, min(y1, img_height - margin_y - 20))
        y2 = max(y1 + 15, min(y2, img_height - margin_y))
        
        # Desenha retângulo de highlight com opacidade aumentada
        highlight_color = (color[0], color[1], color[2], 150)  # Aumenta opacidade
        draw.rectangle([x1, y1, x2, y2], fill=highlight_color)
    
    def _highlight_text_in_image(
        self,
        draw: ImageDraw.Draw,
        image: Image.Image,
        full_text: str,
        search_text: str,
        color: Tuple[int, int, int, int]
    ) -> None:
        """
        Destaca texto em uma imagem (método legado mantido para compatibilidade).
        """
        if not search_text:
            return
        
        text_lower = full_text.lower()
        search_lower = search_text.lower()
        
        pos = text_lower.find(search_lower)
        if pos == -1:
            return
        
        self._highlight_at_position(
            draw, image, full_text, pos, len(search_text), color
        )
    
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
        
        # Executa OCR para extrair texto das páginas
        logger.info("Executando OCR para extração de texto...")
        self.ocr.extract(document)
        
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        output_paths = []
        
        for page in document.pages:
            if page.image is None:
                continue
            
            # Converte para PIL Image
            if isinstance(page.image, np.ndarray):
                img = Image.fromarray(page.image)
            elif hasattr(page.image, 'image'):
                # PageImage object - acessa o array interno
                img = Image.fromarray(page.image.image)
            else:
                img = page.image.copy()
            
            # Aplica highlights
            img = self._apply_highlights(
                img,
                page.text or "",
                page.number,
                result
            )
            
            # Converte para RGB
            if img.mode == 'RGBA':
                background = Image.new('RGB', img.size, (255, 255, 255))
                background.paste(img, mask=img.split()[-1])
                img = background
            
            # Salva
            output_path = output_dir / f"page_{page.number:03d}_highlighted.png"
            img.save(output_path, "PNG")
            output_paths.append(output_path)
        
        logger.info(f"Geradas {len(output_paths)} imagens com highlights")
        return output_paths


