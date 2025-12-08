"""Módulo para extração de texto via OCR usando Tesseract."""

from __future__ import annotations

import logging
import os
import time
from pathlib import Path
from typing import Optional, Tuple

import cv2
import numpy as np
import pytesseract
from PIL import Image

from config.settings import Settings, get_settings
from models.document import Document, Page
from models.extraction_result import ExtractionResult

logger = logging.getLogger(__name__)


class OCRExtractor:
    """Extrator de texto usando Tesseract OCR."""
    
    def __init__(self, settings: Optional[Settings] = None):
        """
        Inicializa o extrator OCR.
        
        Args:
            settings: Configurações do aplicativo.
        """
        self.settings = settings or get_settings()
        self._configure_tesseract()
    
    def _configure_tesseract(self) -> None:
        """Configura o caminho do Tesseract."""
        tesseract_path = self.settings.ocr.tesseract_path
        
        if os.path.exists(tesseract_path):
            pytesseract.pytesseract.tesseract_cmd = tesseract_path
            logger.info(f"Tesseract configurado: {tesseract_path}")
        else:
            logger.warning(
                f"Tesseract não encontrado em {tesseract_path}. "
                "Usando caminho do sistema."
            )
    
    def extract(self, document: Document) -> ExtractionResult:
        """
        Extrai texto de todas as páginas do documento.
        
        Args:
            document: Documento com imagens das páginas.
        
        Returns:
            ExtractionResult: Resultado da extração.
        """
        result = ExtractionResult()
        start_time = time.time()
        
        logger.info(f"Iniciando extração OCR de {document.total_pages} páginas")
        
        try:
            for page in document.pages:
                if page.image is None:
                    result.add_warning(f"Página {page.number} sem imagem")
                    continue
                
                text, confidence = self._extract_from_page(page)
                page.text = text
                page.confidence = confidence
                page.word_count = len(text.split()) if text else 0
                
                logger.debug(
                    f"Página {page.number}: {page.word_count} palavras, "
                    f"confiança: {confidence:.2f}"
                )
            
            result.success = True
            result.text = document.full_text
            result.page_count = document.total_pages
            
        except Exception as e:
            logger.error(f"Erro durante extração OCR: {e}")
            result.add_error(str(e))
        
        result.processing_time = time.time() - start_time
        logger.info(f"Extração concluída em {result.processing_time:.2f}s")
        
        return result
    
    def _extract_from_page(self, page: Page) -> Tuple[str, float]:
        """
        Extrai texto de uma única página.
        
        Args:
            page: Página com imagem.
        
        Returns:
            Tuple[str, float]: Texto extraído e confiança.
        """
        if page.image is None:
            return "", 0.0
        
        # Pré-processa a imagem para melhorar OCR
        processed_image = self._preprocess_image(page.image.image)
        
        # Configuração do Tesseract
        config = self.settings.ocr.config
        lang = self.settings.ocr.language
        
        try:
            # Extrai texto
            text = pytesseract.image_to_string(
                processed_image,
                lang=lang,
                config=config
            )
            
            # Obtém dados detalhados para calcular confiança
            data = pytesseract.image_to_data(
                processed_image,
                lang=lang,
                config=config,
                output_type=pytesseract.Output.DICT
            )
            
            # Calcula confiança média
            confidences = [
                int(c) for c in data["conf"] 
                if c != "-1" and str(c).isdigit()
            ]
            avg_confidence = sum(confidences) / len(confidences) if confidences else 0.0
            
            return text.strip(), avg_confidence / 100.0
            
        except Exception as e:
            logger.error(f"Erro no OCR da página {page.number}: {e}")
            return "", 0.0
    
    def _preprocess_image(self, image: np.ndarray) -> np.ndarray:
        """
        Pré-processa a imagem para melhorar a qualidade do OCR.
        
        Args:
            image: Imagem numpy array.
        
        Returns:
            np.ndarray: Imagem pré-processada.
        """
        # Converte para escala de cinza se necessário
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)
        else:
            gray = image.copy()
        
        # Aplica threshold adaptativo para melhorar contraste
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
    
    def extract_with_boxes(self, page: Page) -> dict:
        """
        Extrai texto com informações de bounding boxes.
        
        Args:
            page: Página com imagem.
        
        Returns:
            dict: Dados do OCR incluindo posições.
        """
        if page.image is None:
            return {}
        
        processed_image = self._preprocess_image(page.image.image)
        config = self.settings.ocr.config
        lang = self.settings.ocr.language
        
        try:
            data = pytesseract.image_to_data(
                processed_image,
                lang=lang,
                config=config,
                output_type=pytesseract.Output.DICT
            )
            return data
        except Exception as e:
            logger.error(f"Erro ao extrair boxes: {e}")
            return {}
    
    def get_available_languages(self) -> list:
        """
        Retorna os idiomas disponíveis no Tesseract.
        
        Returns:
            list: Lista de códigos de idiomas.
        """
        try:
            langs = pytesseract.get_languages()
            return langs
        except Exception as e:
            logger.error(f"Erro ao obter idiomas: {e}")
            return []
