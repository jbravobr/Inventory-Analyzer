"""Módulo para leitura de arquivos PDF."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import List, Optional, Generator

import numpy as np
from pdf2image import convert_from_path
from PIL import Image
import PyPDF2

from ..config.settings import Settings, get_settings
from ..models.document import Document, Page, PageImage

logger = logging.getLogger(__name__)


class PDFReader:
    """Leitor de arquivos PDF com suporte a imagens e texto."""
    
    def __init__(self, settings: Optional[Settings] = None):
        """
        Inicializa o leitor de PDF.
        
        Args:
            settings: Configurações do aplicativo.
        """
        self.settings = settings or get_settings()
        self.dpi = self.settings.ocr.dpi
    
    def read(self, pdf_path: Path) -> Document:
        """
        Lê um arquivo PDF e retorna um Document.
        
        Args:
            pdf_path: Caminho para o arquivo PDF.
        
        Returns:
            Document: Documento com páginas e imagens.
        
        Raises:
            FileNotFoundError: Se o arquivo não existir.
            ValueError: Se o arquivo não for um PDF válido.
        """
        pdf_path = Path(pdf_path)
        
        if not pdf_path.exists():
            raise FileNotFoundError(f"Arquivo não encontrado: {pdf_path}")
        
        if pdf_path.suffix.lower() != ".pdf":
            raise ValueError(f"Arquivo deve ser PDF: {pdf_path}")
        
        logger.info(f"Lendo PDF: {pdf_path}")
        
        # Cria documento
        document = Document(source_path=pdf_path)
        
        # Extrai metadados
        document.metadata = self._extract_metadata(pdf_path)
        
        # Converte páginas para imagens
        pages = list(self._convert_to_images(pdf_path))
        
        for page in pages:
            document.add_page(page)
        
        logger.info(f"PDF lido com sucesso: {document.total_pages} páginas")
        
        return document
    
    def _extract_metadata(self, pdf_path: Path) -> dict:
        """
        Extrai metadados do PDF.
        
        Args:
            pdf_path: Caminho para o arquivo PDF.
        
        Returns:
            dict: Metadados do PDF.
        """
        metadata = {
            "filename": pdf_path.name,
            "file_size": pdf_path.stat().st_size,
        }
        
        try:
            with open(pdf_path, "rb") as f:
                reader = PyPDF2.PdfReader(f)
                metadata["page_count"] = len(reader.pages)
                
                if reader.metadata:
                    metadata.update({
                        "title": reader.metadata.get("/Title", ""),
                        "author": reader.metadata.get("/Author", ""),
                        "creator": reader.metadata.get("/Creator", ""),
                        "creation_date": str(reader.metadata.get("/CreationDate", "")),
                    })
        except Exception as e:
            logger.warning(f"Erro ao extrair metadados: {e}")
        
        return metadata
    
    def _convert_to_images(self, pdf_path: Path) -> Generator[Page, None, None]:
        """
        Converte páginas do PDF para imagens.
        
        Args:
            pdf_path: Caminho para o arquivo PDF.
        
        Yields:
            Page: Página com imagem convertida.
        """
        try:
            # Converte PDF para lista de imagens PIL
            images = convert_from_path(
                pdf_path,
                dpi=self.dpi,
                fmt="png"
            )
            
            for page_num, pil_image in enumerate(images, start=1):
                # Converte PIL Image para numpy array
                np_image = np.array(pil_image)
                
                # Cria PageImage
                page_image = PageImage(
                    page_number=page_num,
                    image=np_image,
                    width=pil_image.width,
                    height=pil_image.height,
                    dpi=self.dpi
                )
                
                # Cria Page
                page = Page(
                    number=page_num,
                    image=page_image
                )
                
                logger.debug(f"Página {page_num} convertida: {pil_image.width}x{pil_image.height}")
                
                yield page
                
        except Exception as e:
            logger.error(f"Erro ao converter PDF para imagens: {e}")
            raise
    
    def get_page_count(self, pdf_path: Path) -> int:
        """
        Retorna o número de páginas do PDF sem carregar as imagens.
        
        Args:
            pdf_path: Caminho para o arquivo PDF.
        
        Returns:
            int: Número de páginas.
        """
        try:
            with open(pdf_path, "rb") as f:
                reader = PyPDF2.PdfReader(f)
                return len(reader.pages)
        except Exception as e:
            logger.error(f"Erro ao contar páginas: {e}")
            return 0
    
    def read_single_page(self, pdf_path: Path, page_number: int) -> Optional[Page]:
        """
        Lê uma única página do PDF.
        
        Args:
            pdf_path: Caminho para o arquivo PDF.
            page_number: Número da página (1-indexed).
        
        Returns:
            Page: Página lida ou None se falhar.
        """
        try:
            images = convert_from_path(
                pdf_path,
                dpi=self.dpi,
                first_page=page_number,
                last_page=page_number,
                fmt="png"
            )
            
            if images:
                pil_image = images[0]
                np_image = np.array(pil_image)
                
                page_image = PageImage(
                    page_number=page_number,
                    image=np_image,
                    width=pil_image.width,
                    height=pil_image.height,
                    dpi=self.dpi
                )
                
                return Page(number=page_number, image=page_image)
            
        except Exception as e:
            logger.error(f"Erro ao ler página {page_number}: {e}")
        
        return None
