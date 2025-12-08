"""Utilitários para processamento de imagens."""

from __future__ import annotations

from pathlib import Path
from typing import Optional, Tuple

import cv2
import numpy as np


class ImageUtils:
    """Utilitários para manipulação de imagens."""
    
    @staticmethod
    def load_image(path: Path) -> Optional[np.ndarray]:
        """
        Carrega uma imagem do disco.
        
        Args:
            path: Caminho da imagem.
        
        Returns:
            np.ndarray: Imagem carregada ou None.
        """
        try:
            image = cv2.imread(str(path))
            if image is not None:
                # Converte BGR para RGB
                image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
            return image
        except Exception:
            return None
    
    @staticmethod
    def save_image(image: np.ndarray, path: Path) -> bool:
        """
        Salva uma imagem no disco.
        
        Args:
            image: Imagem numpy array.
            path: Caminho de destino.
        
        Returns:
            bool: True se salvou com sucesso.
        """
        try:
            path = Path(path)
            path.parent.mkdir(parents=True, exist_ok=True)
            
            # Converte RGB para BGR para OpenCV
            if len(image.shape) == 3:
                image = cv2.cvtColor(image, cv2.COLOR_RGB2BGR)
            
            cv2.imwrite(str(path), image)
            return True
        except Exception:
            return False
    
    @staticmethod
    def resize_image(
        image: np.ndarray,
        max_width: int = 1920,
        max_height: int = 1080
    ) -> np.ndarray:
        """
        Redimensiona imagem mantendo proporção.
        
        Args:
            image: Imagem para redimensionar.
            max_width: Largura máxima.
            max_height: Altura máxima.
        
        Returns:
            np.ndarray: Imagem redimensionada.
        """
        height, width = image.shape[:2]
        
        if width <= max_width and height <= max_height:
            return image
        
        # Calcula fator de escala
        scale_w = max_width / width
        scale_h = max_height / height
        scale = min(scale_w, scale_h)
        
        new_width = int(width * scale)
        new_height = int(height * scale)
        
        return cv2.resize(image, (new_width, new_height), interpolation=cv2.INTER_AREA)
    
    @staticmethod
    def convert_to_grayscale(image: np.ndarray) -> np.ndarray:
        """
        Converte imagem para escala de cinza.
        
        Args:
            image: Imagem colorida.
        
        Returns:
            np.ndarray: Imagem em escala de cinza.
        """
        if len(image.shape) == 2:
            return image
        
        return cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)
    
    @staticmethod
    def enhance_for_ocr(image: np.ndarray) -> np.ndarray:
        """
        Melhora imagem para OCR.
        
        Aplica técnicas de pré-processamento para melhorar
        a qualidade da extração de texto.
        
        Args:
            image: Imagem original.
        
        Returns:
            np.ndarray: Imagem processada.
        """
        # Converte para escala de cinza
        gray = ImageUtils.convert_to_grayscale(image)
        
        # Aplica threshold adaptativo
        binary = cv2.adaptiveThreshold(
            gray,
            255,
            cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY,
            11,
            2
        )
        
        # Remove ruído
        denoised = cv2.fastNlMeansDenoising(binary, None, 10, 7, 21)
        
        return denoised
    
    @staticmethod
    def add_highlight_overlay(
        image: np.ndarray,
        region: Tuple[int, int, int, int],
        color: Tuple[int, int, int] = (255, 255, 0),
        opacity: float = 0.4
    ) -> np.ndarray:
        """
        Adiciona overlay de destaque em região da imagem.
        
        Args:
            image: Imagem base.
            region: Região (x1, y1, x2, y2).
            color: Cor RGB do destaque.
            opacity: Opacidade do overlay.
        
        Returns:
            np.ndarray: Imagem com overlay.
        """
        overlay = image.copy()
        x1, y1, x2, y2 = region
        
        cv2.rectangle(overlay, (x1, y1), (x2, y2), color, -1)
        
        return cv2.addWeighted(overlay, opacity, image, 1 - opacity, 0)
    
    @staticmethod
    def draw_text_box(
        image: np.ndarray,
        text: str,
        position: Tuple[int, int],
        font_scale: float = 0.5,
        color: Tuple[int, int, int] = (0, 0, 0),
        bg_color: Tuple[int, int, int] = (255, 255, 255)
    ) -> np.ndarray:
        """
        Desenha texto com fundo na imagem.
        
        Args:
            image: Imagem base.
            text: Texto a desenhar.
            position: Posição (x, y).
            font_scale: Escala da fonte.
            color: Cor do texto.
            bg_color: Cor do fundo.
        
        Returns:
            np.ndarray: Imagem com texto.
        """
        result = image.copy()
        font = cv2.FONT_HERSHEY_SIMPLEX
        thickness = 1
        
        # Calcula tamanho do texto
        (text_width, text_height), baseline = cv2.getTextSize(
            text, font, font_scale, thickness
        )
        
        x, y = position
        
        # Desenha fundo
        cv2.rectangle(
            result,
            (x, y - text_height - 5),
            (x + text_width + 5, y + 5),
            bg_color,
            -1
        )
        
        # Desenha texto
        cv2.putText(
            result,
            text,
            (x, y),
            font,
            font_scale,
            color,
            thickness
        )
        
        return result
    
    @staticmethod
    def get_image_dimensions(image: np.ndarray) -> Tuple[int, int]:
        """
        Retorna dimensões da imagem.
        
        Args:
            image: Imagem numpy array.
        
        Returns:
            Tuple[int, int]: (largura, altura)
        """
        height, width = image.shape[:2]
        return width, height
