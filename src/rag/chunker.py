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
    SEMANTIC_SECTIONS = "semantic_sections"  # Novo: por seções lógicas


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


class ParagraphChunker(BaseChunker):
    """
    Chunker que preserva parágrafos inteiros.
    
    Agrupa parágrafos até atingir o tamanho máximo,
    sem cortar no meio de um parágrafo.
    
    Ideal para documentos jurídicos onde parágrafos
    contêm informações completas.
    """
    
    def chunk_text(self, text: str, page_number: int = 1) -> List[Chunk]:
        """Divide texto por parágrafos."""
        # Divide em parágrafos (2+ quebras de linha)
        paragraphs = re.split(r'\n\s*\n', text)
        paragraphs = [p.strip() for p in paragraphs if p.strip()]
        
        chunks = []
        current_paragraphs = []
        current_length = 0
        current_start = 0
        index = 0
        char_pos = 0
        
        for paragraph in paragraphs:
            paragraph_length = len(paragraph)
            
            # Se adicionar este parágrafo excede o limite
            if (current_length + paragraph_length > self.config.chunk_size 
                and current_paragraphs):
                
                # Salva chunk atual
                chunk_text = "\n\n".join(current_paragraphs)
                
                if len(chunk_text) >= self.config.min_chunk_size:
                    chunks.append(Chunk(
                        text=chunk_text,
                        chunk_id=self._generate_chunk_id(page_number, index),
                        page_number=page_number,
                        start_char=current_start,
                        end_char=char_pos,
                        metadata={"type": "paragraph"}
                    ))
                    index += 1
                
                # Overlap: mantém último parágrafo se couber
                if self.config.chunk_overlap > 0 and current_paragraphs:
                    last_para = current_paragraphs[-1]
                    if len(last_para) < self.config.chunk_overlap:
                        current_paragraphs = [last_para]
                        current_length = len(last_para)
                        current_start = char_pos - len(last_para)
                    else:
                        current_paragraphs = []
                        current_length = 0
                        current_start = char_pos
                else:
                    current_paragraphs = []
                    current_length = 0
                    current_start = char_pos
            
            # Adiciona parágrafo ao chunk atual
            current_paragraphs.append(paragraph)
            current_length += paragraph_length + 2  # +2 para \n\n
            char_pos += paragraph_length + 2
        
        # Último chunk
        if current_paragraphs:
            chunk_text = "\n\n".join(current_paragraphs)
            if len(chunk_text) >= self.config.min_chunk_size:
                chunks.append(Chunk(
                    text=chunk_text,
                    chunk_id=self._generate_chunk_id(page_number, index),
                    page_number=page_number,
                    start_char=current_start,
                    end_char=len(text),
                    metadata={"type": "paragraph"}
                ))
        
        return chunks


class SemanticSectionChunker(BaseChunker):
    """
    Chunker que detecta e preserva seções lógicas do documento.
    
    Detecta seções baseado em:
    - Headers/títulos (linhas curtas em maiúsculas ou com marcadores)
    - Padrões de numeração (1., 1.1, I., a), etc.)
    - Palavras-chave de seção (CLÁUSULA, ARTIGO, SEÇÃO, etc.)
    - Separadores visuais (---, ***, ===)
    
    Ideal para documentos estruturados como:
    - Contratos
    - Documentos de licença
    - Atas de reunião
    - Inventários
    """
    
    # Padrões de detecção de seção
    SECTION_PATTERNS = [
        # Headers em maiúsculas
        r'^[A-ZÁÉÍÓÚÂÊÎÔÛÃÕÇ][A-ZÁÉÍÓÚÂÊÎÔÛÃÕÇ\s\-:]{5,50}$',
        
        # Numeração de seção
        r'^\d+\.\s+[A-ZÁÉÍÓÚÂÊÎÔÛÃÕÇ]',          # 1. SEÇÃO
        r'^\d+\.\d+\.?\s+',                        # 1.1 ou 1.1.
        r'^[IVXLCDM]+\.\s+',                       # I. II. III.
        r'^[a-z]\)\s+',                            # a) b) c)
        r'^\(\d+\)\s+',                            # (1) (2) (3)
        
        # Palavras-chave de seção jurídica
        r'^CLÁUSULA\s+',
        r'^ARTIGO\s+',
        r'^ART\.\s*\d+',
        r'^SEÇÃO\s+',
        r'^PARÁGRAFO\s+',
        r'^§\s*\d+',
        r'^CAPÍTULO\s+',
        r'^TÍTULO\s+',
        
        # Palavras-chave de licença
        r'^GPL|^AGPL|^LGPL|^MIT|^APACHE|^BSD|^MPL',
        r'^LICEN[CÇ]A[S]?\s*:?',
        r'^COMPATIBILIDADE',
        r'^GRAU DE CRITICIDADE',
        r'^RECOMENDAÇÕES',
        
        # Separadores visuais
        r'^-{3,}$',
        r'^\*{3,}$',
        r'^={3,}$',
        r'^_{3,}$',
    ]
    
    def __init__(
        self,
        config: Optional[ChunkingConfig] = None,
        settings: Optional[Settings] = None
    ):
        super().__init__(config, settings)
        # Compila padrões para performance
        self._compiled_patterns = [
            re.compile(p, re.MULTILINE | re.IGNORECASE) 
            for p in self.SECTION_PATTERNS
        ]
    
    def _is_section_header(self, line: str) -> bool:
        """Verifica se uma linha é um header de seção."""
        line = line.strip()
        
        if not line or len(line) < 3:
            return False
        
        # Verifica padrões
        for pattern in self._compiled_patterns:
            if pattern.match(line):
                return True
        
        # Header curto em maiúsculas (menos que 60 chars)
        if len(line) < 60 and line.isupper() and ' ' in line:
            return True
        
        return False
    
    def _detect_sections(self, text: str) -> List[Tuple[int, str, str]]:
        """
        Detecta seções no texto.
        
        Returns:
            Lista de tuplas (start_pos, header, content)
        """
        lines = text.split('\n')
        sections = []
        
        current_header = ""
        current_content = []
        current_start = 0
        char_pos = 0
        
        for line in lines:
            line_length = len(line) + 1  # +1 para \n
            
            if self._is_section_header(line):
                # Salva seção anterior
                if current_content:
                    content = '\n'.join(current_content).strip()
                    if content:
                        sections.append((current_start, current_header, content))
                
                # Inicia nova seção
                current_header = line.strip()
                current_content = []
                current_start = char_pos
            else:
                current_content.append(line)
            
            char_pos += line_length
        
        # Última seção
        if current_content:
            content = '\n'.join(current_content).strip()
            if content:
                sections.append((current_start, current_header, content))
        
        return sections
    
    def chunk_text(self, text: str, page_number: int = 1) -> List[Chunk]:
        """Divide texto por seções lógicas."""
        sections = self._detect_sections(text)
        
        if not sections:
            # Fallback para chunking recursivo
            fallback = RecursiveChunker(self.config, self.settings)
            return fallback.chunk_text(text, page_number)
        
        chunks = []
        index = 0
        
        for start_pos, header, content in sections:
            # Combina header com conteúdo
            section_text = f"{header}\n\n{content}" if header else content
            
            # Se a seção é muito grande, subdivide
            if len(section_text) > self.config.chunk_size:
                sub_chunks = self._subdivide_section(
                    section_text, 
                    page_number, 
                    index, 
                    start_pos,
                    header
                )
                chunks.extend(sub_chunks)
                index += len(sub_chunks)
            elif len(section_text) >= self.config.min_chunk_size:
                chunks.append(Chunk(
                    text=section_text,
                    chunk_id=self._generate_chunk_id(page_number, index),
                    page_number=page_number,
                    start_char=start_pos,
                    end_char=start_pos + len(section_text),
                    metadata={
                        "type": "section",
                        "section_header": header[:50] if header else ""
                    }
                ))
                index += 1
        
        # Se não encontrou seções suficientes, agrupa chunks pequenos
        if len(chunks) > 0:
            chunks = self._merge_small_chunks(chunks, page_number)
        
        return chunks
    
    def _subdivide_section(
        self,
        section_text: str,
        page_number: int,
        start_index: int,
        start_pos: int,
        header: str
    ) -> List[Chunk]:
        """Subdivide uma seção grande preservando contexto."""
        # Usa chunker por parágrafo para subdividir
        para_chunker = ParagraphChunker(self.config, self.settings)
        sub_chunks = para_chunker.chunk_text(section_text, page_number)
        
        # Adiciona header como contexto aos chunks
        result = []
        for i, chunk in enumerate(sub_chunks):
            # Adiciona header como prefixo se não é o primeiro chunk
            if i > 0 and header and not chunk.text.startswith(header):
                chunk.text = f"[Seção: {header}]\n\n{chunk.text}"
            
            chunk.chunk_id = self._generate_chunk_id(page_number, start_index + i)
            chunk.start_char = start_pos + chunk.start_char
            chunk.end_char = start_pos + chunk.end_char
            chunk.metadata["section_header"] = header[:50] if header else ""
            result.append(chunk)
        
        return result
    
    def _merge_small_chunks(
        self, 
        chunks: List[Chunk], 
        page_number: int
    ) -> List[Chunk]:
        """Agrupa chunks muito pequenos."""
        if not chunks:
            return chunks
        
        merged = []
        current = None
        
        for chunk in chunks:
            if current is None:
                current = chunk
            elif (len(current.text) + len(chunk.text) < self.config.chunk_size * 0.8):
                # Agrupa
                current.text = f"{current.text}\n\n{chunk.text}"
                current.end_char = chunk.end_char
            else:
                merged.append(current)
                current = chunk
        
        if current:
            merged.append(current)
        
        # Re-numera IDs
        for i, chunk in enumerate(merged):
            chunk.chunk_id = self._generate_chunk_id(page_number, i)
        
        return merged


class TextChunker:
    """
    Classe principal de chunking que seleciona estratégia apropriada.
    """
    
    _chunkers = {
        ChunkingStrategy.FIXED_SIZE: FixedSizeChunker,
        ChunkingStrategy.SENTENCE: SentenceChunker,
        ChunkingStrategy.RECURSIVE: RecursiveChunker,
        ChunkingStrategy.PARAGRAPH: ParagraphChunker,
        ChunkingStrategy.SEMANTIC_SECTIONS: SemanticSectionChunker,
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
    
    @classmethod
    def for_license_documents(cls, settings: Optional[Settings] = None) -> "TextChunker":
        """
        Cria chunker otimizado para documentos de licenças de software.
        
        Usa estratégia de seções semânticas para preservar
        a estrutura do documento de licenças.
        """
        config = ChunkingConfig(
            strategy=ChunkingStrategy.SEMANTIC_SECTIONS,
            chunk_size=800,      # Chunks maiores para contexto
            chunk_overlap=100,   # Overlap de ~100 tokens
            min_chunk_size=100,
            separators=[
                "\n\nLICENÇA",
                "\n\nGPL",
                "\n\nAGPL",
                "\n\nLGPL",
                "\n\nAPACHE",
                "\n\nCOMPATIBILIDADE",
                "\n\nGRAU DE CRITICIDADE",
                "\n\nRECOMENDAÇÕES",
                "\n\n",
                "\n",
                ". ",
            ]
        )
        return cls(config, settings)
    
    @classmethod
    def for_qa_context(cls, settings: Optional[Settings] = None) -> "TextChunker":
        """
        Cria chunker otimizado para Q&A.
        
        Chunks maiores com mais overlap para melhor contexto
        nas perguntas e respostas.
        """
        config = ChunkingConfig(
            strategy=ChunkingStrategy.SEMANTIC_SECTIONS,
            chunk_size=1000,     # Chunks maiores para contexto rico
            chunk_overlap=150,   # Mais overlap para não perder contexto
            min_chunk_size=100,
        )
        return cls(config, settings)
