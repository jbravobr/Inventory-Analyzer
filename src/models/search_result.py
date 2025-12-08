"""Modelos para resultados de busca."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional, Tuple


@dataclass
class TextPosition:
    """Posição do texto no documento."""
    
    page: int
    start_char: int
    end_char: int
    line_number: Optional[int] = None
    
    @property
    def char_range(self) -> Tuple[int, int]:
        """Retorna o intervalo de caracteres."""
        return (self.start_char, self.end_char)


@dataclass
class SearchMatch:
    """Representa um match de busca no texto."""
    
    text: str
    position: TextPosition
    score: float = 1.0
    context_before: str = ""
    context_after: str = ""
    match_type: str = "exact"  # exact, semantic, fuzzy
    
    @property
    def full_context(self) -> str:
        """Retorna o texto com contexto."""
        parts = []
        if self.context_before:
            parts.append(f"...{self.context_before}")
        parts.append(f"[{self.text}]")
        if self.context_after:
            parts.append(f"{self.context_after}...")
        return " ".join(parts)
    
    def to_dict(self) -> dict:
        """Converte para dicionário."""
        return {
            "text": self.text,
            "page": self.position.page,
            "start_char": self.position.start_char,
            "end_char": self.position.end_char,
            "score": self.score,
            "match_type": self.match_type,
            "context": self.full_context,
        }


@dataclass
class InstructionMatch:
    """Resultado de busca para uma instrução específica."""
    
    instruction: str
    instruction_index: int
    matches: List[SearchMatch] = field(default_factory=list)
    found: bool = False
    
    def __post_init__(self):
        """Atualiza status após inicialização."""
        self.found = len(self.matches) > 0
    
    def add_match(self, match: SearchMatch) -> None:
        """Adiciona um match."""
        self.matches.append(match)
        self.found = True
    
    @property
    def best_match(self) -> Optional[SearchMatch]:
        """Retorna o melhor match por score."""
        if not self.matches:
            return None
        return max(self.matches, key=lambda m: m.score)
    
    @property
    def pages_found(self) -> List[int]:
        """Lista de páginas onde foram encontrados matches."""
        return sorted(set(m.position.page for m in self.matches))
    
    def to_dict(self) -> dict:
        """Converte para dicionário."""
        return {
            "instruction": self.instruction,
            "instruction_index": self.instruction_index,
            "found": self.found,
            "match_count": len(self.matches),
            "pages": self.pages_found,
            "matches": [m.to_dict() for m in self.matches],
        }


@dataclass
class SearchResult:
    """Resultado completo de uma busca."""
    
    instruction_matches: List[InstructionMatch] = field(default_factory=list)
    total_matches: int = 0
    search_time: float = 0.0
    
    def __post_init__(self):
        """Calcula total de matches."""
        self._update_total()
    
    def _update_total(self) -> None:
        """Atualiza contagem total."""
        self.total_matches = sum(
            len(im.matches) for im in self.instruction_matches
        )
    
    def add_instruction_match(self, match: InstructionMatch) -> None:
        """Adiciona resultado de uma instrução."""
        self.instruction_matches.append(match)
        self._update_total()
    
    @property
    def found_any(self) -> bool:
        """Verifica se encontrou algum match."""
        return self.total_matches > 0
    
    @property
    def all_found(self) -> bool:
        """Verifica se todas as instruções foram satisfeitas."""
        return all(im.found for im in self.instruction_matches)
    
    @property
    def found_count(self) -> int:
        """Número de instruções satisfeitas."""
        return sum(1 for im in self.instruction_matches if im.found)
    
    @property
    def all_pages(self) -> List[int]:
        """Todas as páginas com matches."""
        pages = set()
        for im in self.instruction_matches:
            pages.update(im.pages_found)
        return sorted(pages)
    
    @property
    def all_texts(self) -> List[str]:
        """Todos os textos encontrados."""
        texts = []
        for im in self.instruction_matches:
            for match in im.matches:
                texts.append(match.text)
        return texts
    
    def get_matches_by_page(self, page: int) -> List[SearchMatch]:
        """Obtém todos os matches de uma página."""
        matches = []
        for im in self.instruction_matches:
            for match in im.matches:
                if match.position.page == page:
                    matches.append(match)
        return matches
    
    def to_dict(self) -> dict:
        """Converte para dicionário."""
        return {
            "found_any": self.found_any,
            "total_matches": self.total_matches,
            "instructions_satisfied": f"{self.found_count}/{len(self.instruction_matches)}",
            "pages_with_matches": self.all_pages,
            "search_time": self.search_time,
            "results": [im.to_dict() for im in self.instruction_matches],
        }
