"""Módulo para leitura de arquivos PDF usando PyMuPDF (fitz).

Esta implementação usa PyMuPDF que:
- Não requer Poppler ou outras dependências nativas externas
- Distribui como wheel puro (instalável via pip em qualquer ambiente)
- É mais rápido e usa menos memória que pdf2image
- Funciona offline sem problemas
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import List, Optional, Generator

import numpy as np
import fitz  # PyMuPDF
from PIL import Image

from config.settings import Settings, get_settings
from models.document import Document, Page, PageImage

logger = logging.getLogger(__name__)


class PDFReader:
    """Leitor de arquivos PDF com suporte a imagens e texto usando PyMuPDF."""
    
    def __init__(self, settings: Optional[Settings] = None):
        """
        Inicializa o leitor de PDF.
        
        Args:
            settings: Configurações do aplicativo.
        """
        self.settings = settings or get_settings()
        self.dpi = self.settings.ocr.dpi
        # Fator de zoom para PyMuPDF (DPI / 72, pois 72 é o DPI padrão do PDF)
        self.zoom = self.dpi / 72.0
    
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
        Extrai metadados do PDF usando PyMuPDF.
        
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
            doc = fitz.open(pdf_path)
            metadata["page_count"] = len(doc)
            
            # Extrai metadados do PDF
            pdf_metadata = doc.metadata
            if pdf_metadata:
                metadata.update({
                    "title": pdf_metadata.get("title", ""),
                    "author": pdf_metadata.get("author", ""),
                    "creator": pdf_metadata.get("creator", ""),
                    "creation_date": pdf_metadata.get("creationDate", ""),
                    "producer": pdf_metadata.get("producer", ""),
                    "subject": pdf_metadata.get("subject", ""),
                })
            
            doc.close()
        except Exception as e:
            logger.warning(f"Erro ao extrair metadados: {e}")
        
        return metadata
    
    def _convert_to_images(self, pdf_path: Path) -> Generator[Page, None, None]:
        """
        Converte páginas do PDF para imagens usando PyMuPDF.
        
        Args:
            pdf_path: Caminho para o arquivo PDF.
        
        Yields:
            Page: Página com imagem convertida.
        """
        try:
            doc = fitz.open(pdf_path)
            
            # Matriz de transformação para o DPI desejado
            mat = fitz.Matrix(self.zoom, self.zoom)
            
            for page_num in range(len(doc)):
                fitz_page = doc[page_num]
                
                # Renderiza página como pixmap (imagem)
                pixmap = fitz_page.get_pixmap(matrix=mat, alpha=False)
                
                # Converte pixmap para numpy array RGB
                # PyMuPDF retorna dados em formato RGB
                np_image = np.frombuffer(pixmap.samples, dtype=np.uint8)
                np_image = np_image.reshape(pixmap.height, pixmap.width, pixmap.n)
                
                # Se tiver 4 canais (RGBA), converte para RGB
                if pixmap.n == 4:
                    np_image = np_image[:, :, :3]
                
                # Cria PageImage
                page_image = PageImage(
                    page_number=page_num + 1,  # 1-indexed
                    image=np_image,
                    width=pixmap.width,
                    height=pixmap.height,
                    dpi=self.dpi
                )
                
                # Cria Page
                page = Page(
                    number=page_num + 1,  # 1-indexed
                    image=page_image
                )
                
                logger.debug(f"Página {page_num + 1} convertida: {pixmap.width}x{pixmap.height}")
                
                yield page
            
            doc.close()
                
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
            doc = fitz.open(pdf_path)
            count = len(doc)
            doc.close()
            return count
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
            doc = fitz.open(pdf_path)
            
            # Converte para 0-indexed
            page_idx = page_number - 1
            
            if page_idx < 0 or page_idx >= len(doc):
                logger.error(f"Página {page_number} fora do intervalo (1-{len(doc)})")
                doc.close()
                return None
            
            fitz_page = doc[page_idx]
            
            # Matriz de transformação para o DPI desejado
            mat = fitz.Matrix(self.zoom, self.zoom)
            
            # Renderiza página como pixmap
            pixmap = fitz_page.get_pixmap(matrix=mat, alpha=False)
            
            # Converte para numpy array
            np_image = np.frombuffer(pixmap.samples, dtype=np.uint8)
            np_image = np_image.reshape(pixmap.height, pixmap.width, pixmap.n)
            
            if pixmap.n == 4:
                np_image = np_image[:, :, :3]
            
            page_image = PageImage(
                page_number=page_number,
                image=np_image,
                width=pixmap.width,
                height=pixmap.height,
                dpi=self.dpi
            )
            
            doc.close()
            
            return Page(number=page_number, image=page_image)
            
        except Exception as e:
            logger.error(f"Erro ao ler página {page_number}: {e}")
            return None
    
    def extract_text(self, pdf_path: Path) -> str:
        """
        Extrai texto de todas as páginas do PDF.
        
        Args:
            pdf_path: Caminho para o arquivo PDF.
        
        Returns:
            str: Texto extraído de todas as páginas.
        """
        try:
            doc = fitz.open(pdf_path)
            text_parts = []
            
            for page_num in range(len(doc)):
                page = doc[page_num]
                text = page.get_text()
                if text.strip():
                    text_parts.append(f"--- Página {page_num + 1} ---\n{text}")
            
            doc.close()
            return "\n\n".join(text_parts)
            
        except Exception as e:
            logger.error(f"Erro ao extrair texto: {e}")
            return ""
    
    def extract_text_from_page(self, pdf_path: Path, page_number: int) -> str:
        """
        Extrai texto de uma página específica.
        
        Args:
            pdf_path: Caminho para o arquivo PDF.
            page_number: Número da página (1-indexed).
        
        Returns:
            str: Texto da página.
        """
        try:
            doc = fitz.open(pdf_path)
            page_idx = page_number - 1
            
            if page_idx < 0 or page_idx >= len(doc):
                doc.close()
                return ""
            
            text = doc[page_idx].get_text()
            doc.close()
            return text
            
        except Exception as e:
            logger.error(f"Erro ao extrair texto da página {page_number}: {e}")
            return ""
