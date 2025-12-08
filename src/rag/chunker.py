"""
Módulo de chunking para divisão inteligente de documentos.

Estratégias de chunking:
- Por tamanho fixo com overlap
- Por sentenças
- Por parágrafos
- Semântico (agrupa por similaridade)
"""

from __future__ import annotations

import logging
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional, Tuple

from config.settings import Settings, get_settings
from models.document import Document, Page

logger = logging.getLogger(__name__)


class ChunkingStrategy(Enum):
    """Estratégias disponíveis de chunking."""
    
    FIXED_SIZE = "fixed_size"
    SENTENCE = "sentence"
    PARAGRAPH = "paragraph"
    SEMANTIC = "semantic"
    RECURSIVE = "recursive"


@dataclass
class Chunk:
    """Representa um chunk de texto do documento."""
    
    text: str
    chunk_id: str
    page_number: int
    start_char: int
    end_char: int
    metadata: dict = field(default_factory=dict)
    
    @property
    def length(self) -> int:
        """Comprimento do chunk em caracteres."""
        return len(self.text)
    
    @property
    def word_count(self) -> int:
        """Contagem de palavras."""
        return len(self.text.split())
    
    def to_dict(self) -> dict:
        """Converte para dicionário."""
        return {
            "chunk_id": self.chunk_id,
            "text": self.text,
            "page_number": self.page_number,
            "start_char": self.start_char,
            "end_char": self.end_char,
            "length": self.length,
            "word_count": self.word_count,
            "metadata": self.metadata,
        }


@dataclass
class ChunkingConfig:
    """Configuração para chunking."""
    
    strategy: ChunkingStrategy = ChunkingStrategy.RECURSIVE
    chunk_size: int = 512
    chunk_overlap: int = 50
    min_chunk_size: int = 100
    separators: List[str] = field(default_factory=lambda: [
        "\n\n",  # Parágrafos
        "\n",    # Linhas
        ". ",    # Sentenças
        "! ",
        "? ",
        "; ",    # Cláusulas
        ", ",    # Frases
        " ",     # Palavras
    ])


class BaseChunker(ABC):
    """Classe base para chunkers."""
    
    def __init__(
        self,
        config: Optional[ChunkingConfig] = None,
        settings: Optional[Settings] = None
    ):
        self.config = config or ChunkingConfig()
        self.settings = settings or get_settings()
    
    @abstractmethod
    def chunk_text(self, text: str, page_number: int = 1) -> List[Chunk]:
        """
        Divide texto em chunks.
        
        Args:
            text: Texto para dividir.
            page_number: Número da página de origem.
        
        Returns:
            List[Chunk]: Lista de chunks.
        """
        pass
    
    def chunk_document(self, document: Document) -> List[Chunk]:
        """
        Divide um documento inteiro em chunks.
        
        Args:
            document: Documento para dividir.
        
        Returns:
            List[Chunk]: Lista de chunks de todas as páginas.
        """
        all_chunks = []
        
        for page in document.pages:
            if not page.text:
                continue
            
            page_chunks = self.chunk_text(page.text, page.number)
            
            # Adiciona metadados do documento
            for chunk in page_chunks:
                chunk.metadata.update({
                    "source": str(document.source_path),
                    "total_pages": document.total_pages,
                })
            
            all_chunks.extend(page_chunks)
        
        logger.info(f"Documento dividido em {len(all_chunks)} chunks")
        return all_chunks
    
    def _generate_chunk_id(self, page: int, index: int) -> str:
        """Gera ID único para o chunk."""
        return f"p{page}_c{index}"


class FixedSizeChunker(BaseChunker):
    """Chunker por tamanho fixo com overlap."""
    
    def chunk_text(self, text: str, page_number: int = 1) -> List[Chunk]:
        """Divide texto em chunks de tamanho fixo."""
        chunks = []
        chunk_size = self.config.chunk_size
        overlap = self.config.chunk_overlap
        
        start = 0
        index = 0
        
        while start < len(text):
            end = start + chunk_size
            
            # Ajusta para não cortar palavras
            if end < len(text):
                # Procura espaço mais próximo
                space_pos = text.rfind(" ", start, end)
                if space_pos > start:
                    end = space_pos
            
            chunk_text = text[start:end].strip()
            
            if len(chunk_text) >= self.config.min_chunk_size:
                chunks.append(Chunk(
                    text=chunk_text,
                    chunk_id=self._generate_chunk_id(page_number, index),
                    page_number=page_number,
                    start_char=start,
                    end_char=end,
                ))
                index += 1
            
            start = end - overlap
        
        return chunks


class SentenceChunker(BaseChunker):
    """Chunker que agrupa sentenças."""
    
    def chunk_text(self, text: str, page_number: int = 1) -> List[Chunk]:
        """Divide texto agrupando sentenças até atingir tamanho."""
        # Divide em sentenças
        sentences = re.split(r'(?<=[.!?])\s+', text)
        
        chunks = []
        current_chunk = []
        current_length = 0
        current_start = 0
        index = 0
        char_pos = 0
        
        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence:
                continue
            
            sentence_length = len(sentence)
            
            # Se adicionar esta sentença excede o limite
            if current_length + sentence_length > self.config.chunk_size and current_chunk:
                # Salva chunk atual
                chunk_text = " ".join(current_chunk)
                if len(chunk_text) >= self.config.min_chunk_size:
                    chunks.append(Chunk(
                        text=chunk_text,
                        chunk_id=self._generate_chunk_id(page_number, index),
                        page_number=page_number,
                        start_char=current_start,
                        end_char=char_pos,
                    ))
                    index += 1
                
                # Inicia novo chunk com overlap
                overlap_sentences = current_chunk[-2:] if len(current_chunk) > 2 else []
                current_chunk = overlap_sentences + [sentence]
                current_length = sum(len(s) for s in current_chunk)
                current_start = char_pos - sum(len(s) + 1 for s in overlap_sentences)
            else:
                current_chunk.append(sentence)
                current_length += sentence_length + 1
            
            char_pos += sentence_length + 1
        
        # Último chunk
        if current_chunk:
            chunk_text = " ".join(current_chunk)
            if len(chunk_text) >= self.config.min_chunk_size:
                chunks.append(Chunk(
                    text=chunk_text,
                    chunk_id=self._generate_chunk_id(page_number, index),
                    page_number=page_number,
                    start_char=current_start,
                    end_char=len(text),
                ))
        
        return chunks


class RecursiveChunker(BaseChunker):
    """
    Chunker recursivo que tenta dividir por separadores hierárquicos.
    
    Primeiro tenta dividir por parágrafos, depois linhas, 
    depois sentenças, etc.
    """
    
    def chunk_text(self, text: str, page_number: int = 1) -> List[Chunk]:
        """Divide texto recursivamente."""
        chunks_text = self._split_recursive(text, self.config.separators)
        
        chunks = []
        char_pos = 0
        
        for index, chunk_text in enumerate(chunks_text):
            chunk_text = chunk_text.strip()
            if len(chunk_text) >= self.config.min_chunk_size:
                # Encontra posição real no texto
                start = text.find(chunk_text, char_pos)
                if start == -1:
                    start = char_pos
                
                chunks.append(Chunk(
                    text=chunk_text,
                    chunk_id=self._generate_chunk_id(page_number, index),
                    page_number=page_number,
                    start_char=start,
                    end_char=start + len(chunk_text),
                ))
                
                char_pos = start + len(chunk_text)
        
        return chunks
    
    def _split_recursive(
        self,
        text: str,
        separators: List[str]
    ) -> List[str]:
        """Divide texto recursivamente usando separadores."""
        if not separators:
            return [text] if text else []
        
        separator = separators[0]
        remaining_separators = separators[1:]
        
        # Divide pelo separador atual
        splits = text.split(separator)
        
        # Processa cada parte
        final_chunks = []
        current_chunk = ""
        
        for split in splits:
            # Se adicionar este split ainda cabe no chunk
            test_chunk = current_chunk + separator + split if current_chunk else split
            
            if len(test_chunk) <= self.config.chunk_size:
                current_chunk = test_chunk
            else:
                # Chunk atual está cheio
                if current_chunk:
                    if len(current_chunk) > self.config.chunk_size:
                        # Ainda muito grande, divide recursivamente
                        final_chunks.extend(
                            self._split_recursive(current_chunk, remaining_separators)
                        )
                    else:
                        final_chunks.append(current_chunk)
                
                # Verifica se o novo split cabe
                if len(split) > self.config.chunk_size:
                    # Split muito grande, divide recursivamente
                    final_chunks.extend(
                        self._split_recursive(split, remaining_separators)
                    )
                    current_chunk = ""
                else:
                    current_chunk = split
        
        # Último chunk
        if current_chunk:
            if len(current_chunk) > self.config.chunk_size:
                final_chunks.extend(
                    self._split_recursive(current_chunk, remaining_separators)
                )
            else:
                final_chunks.append(current_chunk)
        
        return final_chunks


class TextChunker:
    """
    Classe principal de chunking que seleciona estratégia apropriada.
    """
    
    _chunkers = {
        ChunkingStrategy.FIXED_SIZE: FixedSizeChunker,
        ChunkingStrategy.SENTENCE: SentenceChunker,
        ChunkingStrategy.RECURSIVE: RecursiveChunker,
    }
    
    def __init__(
        self,
        config: Optional[ChunkingConfig] = None,
        settings: Optional[Settings] = None
    ):
        self.config = config or ChunkingConfig()
        self.settings = settings or get_settings()
        self._chunker = self._create_chunker()
    
    def _create_chunker(self) -> BaseChunker:
        """Cria chunker baseado na estratégia configurada."""
        chunker_class = self._chunkers.get(self.config.strategy)
        
        if chunker_class is None:
            logger.warning(
                f"Estratégia {self.config.strategy} não implementada. "
                "Usando RECURSIVE."
            )
            chunker_class = RecursiveChunker
        
        return chunker_class(self.config, self.settings)
    
    def chunk_text(self, text: str, page_number: int = 1) -> List[Chunk]:
        """Divide texto em chunks."""
        return self._chunker.chunk_text(text, page_number)
    
    def chunk_document(self, document: Document) -> List[Chunk]:
        """Divide documento em chunks."""
        return self._chunker.chunk_document(document)
    
    @classmethod
    def for_legal_documents(cls, settings: Optional[Settings] = None) -> "TextChunker":
        """
        Cria chunker otimizado para documentos jurídicos.
        
        Usa separadores específicos para contratos.
        """
        config = ChunkingConfig(
            strategy=ChunkingStrategy.RECURSIVE,
            chunk_size=600,
            chunk_overlap=100,
            min_chunk_size=150,
            separators=[
                "\n\nCLÁUSULA",  # Cláusulas
                "\n\nArtigo",
                "\n\nParágrafo",
                "\n\n§",
                "\n\n",          # Parágrafos
                "\n",            # Linhas
                ". ",            # Sentenças
                "; ",            # Itens
                ", ",
                " ",
            ]
        )
        return cls(config, settings)
