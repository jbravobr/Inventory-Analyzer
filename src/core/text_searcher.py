"""Módulo para busca de texto no documento."""

from __future__ import annotations

import logging
import re
import time
from typing import List, Optional, Tuple

from ..config.settings import Settings, get_settings
from ..models.document import Document
from ..models.search_result import (
    SearchResult,
    SearchMatch,
    InstructionMatch,
    TextPosition,
)
from ..nlp.base_processor import BaseNLPProcessor
from ..nlp.processor_factory import get_nlp_processor
from .instruction_parser import Instruction, ParsedInstructions

logger = logging.getLogger(__name__)


class TextSearcher:
    """
    Buscador de texto com suporte a busca semântica e por palavras-chave.
    
    Combina múltiplas estratégias de busca para encontrar informações
    relevantes no texto extraído do PDF.
    """
    
    def __init__(
        self,
        settings: Optional[Settings] = None,
        nlp_processor: Optional[BaseNLPProcessor] = None
    ):
        """
        Inicializa o buscador.
        
        Args:
            settings: Configurações do aplicativo.
            nlp_processor: Processador NLP a usar. Se não fornecido,
                          cria baseado nas configurações.
        """
        self.settings = settings or get_settings()
        self._nlp_processor = nlp_processor
        self._context_size = 100  # Caracteres de contexto
    
    @property
    def nlp_processor(self) -> BaseNLPProcessor:
        """Obtém processador NLP lazy-loaded."""
        if self._nlp_processor is None:
            self._nlp_processor = get_nlp_processor()
        return self._nlp_processor
    
    def search(
        self,
        document: Document,
        instructions: ParsedInstructions
    ) -> SearchResult:
        """
        Busca informações no documento baseado nas instruções.
        
        Args:
            document: Documento com texto extraído.
            instructions: Instruções de busca.
        
        Returns:
            SearchResult: Resultados da busca.
        """
        start_time = time.time()
        result = SearchResult()
        
        logger.info(f"Iniciando busca com {len(instructions)} instruções")
        
        # Inicializa NLP se necessário
        self.nlp_processor.ensure_initialized()
        
        # Processa cada instrução
        for idx, instruction in enumerate(instructions):
            instruction_match = self._search_instruction(
                document, instruction, idx
            )
            result.add_instruction_match(instruction_match)
        
        result.search_time = time.time() - start_time
        
        logger.info(
            f"Busca concluída em {result.search_time:.2f}s. "
            f"Encontrados {result.total_matches} matches"
        )
        
        return result
    
    def _search_instruction(
        self,
        document: Document,
        instruction: Instruction,
        index: int
    ) -> InstructionMatch:
        """
        Busca matches para uma instrução específica.
        
        Args:
            document: Documento fonte.
            instruction: Instrução de busca.
            index: Índice da instrução.
        
        Returns:
            InstructionMatch: Resultados para esta instrução.
        """
        match_result = InstructionMatch(
            instruction=instruction.raw_text,
            instruction_index=index
        )
        
        all_matches: List[SearchMatch] = []
        
        # Busca por palavras-chave
        if self.settings.search.use_keyword_search:
            keyword_matches = self._keyword_search(document, instruction)
            all_matches.extend(keyword_matches)
        
        # Busca semântica
        if self.settings.search.use_semantic_search:
            semantic_matches = self._semantic_search(document, instruction)
            all_matches.extend(semantic_matches)
        
        # Combina e deduplica resultados
        if self.settings.search.combine_results:
            all_matches = self._deduplicate_matches(all_matches)
        
        # Limita número de resultados
        max_results = self.settings.search.max_results
        all_matches = sorted(all_matches, key=lambda m: m.score, reverse=True)
        all_matches = all_matches[:max_results]
        
        for match in all_matches:
            match_result.add_match(match)
        
        return match_result
    
    def _keyword_search(
        self,
        document: Document,
        instruction: Instruction
    ) -> List[SearchMatch]:
        """
        Busca por palavras-chave exatas.
        
        Args:
            document: Documento fonte.
            instruction: Instrução com termos de busca.
        
        Returns:
            List[SearchMatch]: Matches encontrados.
        """
        matches = []
        
        if not instruction.search_terms:
            return matches
        
        for page in document.pages:
            if not page.text:
                continue
            
            text_lower = page.text.lower()
            
            for term in instruction.search_terms:
                term_lower = term.lower()
                
                # Busca todas as ocorrências
                for match in re.finditer(
                    re.escape(term_lower),
                    text_lower,
                    re.IGNORECASE
                ):
                    start, end = match.span()
                    
                    # Obtém texto original (com capitalização)
                    original_text = page.text[start:end]
                    
                    # Obtém contexto
                    context_before, context_after = self._get_context(
                        page.text, start, end
                    )
                    
                    # Calcula score (exato = 1.0)
                    score = 1.0
                    
                    search_match = SearchMatch(
                        text=original_text,
                        position=TextPosition(
                            page=page.number,
                            start_char=start,
                            end_char=end
                        ),
                        score=score,
                        context_before=context_before,
                        context_after=context_after,
                        match_type="exact"
                    )
                    
                    matches.append(search_match)
        
        return matches
    
    def _semantic_search(
        self,
        document: Document,
        instruction: Instruction
    ) -> List[SearchMatch]:
        """
        Busca semântica usando NLP.
        
        Args:
            document: Documento fonte.
            instruction: Instrução de busca.
        
        Returns:
            List[SearchMatch]: Matches encontrados.
        """
        matches = []
        
        query = instruction.semantic_query
        if not query:
            query = instruction.raw_text
        
        for page in document.pages:
            if not page.text:
                continue
            
            # Usa NLP para encontrar passagens similares
            try:
                similar_passages = self.nlp_processor.find_similar_passages(
                    query=query,
                    text=page.text,
                    top_k=5
                )
                
                for passage, score, position in similar_passages:
                    if score < self.settings.nlp.local.similarity_threshold:
                        continue
                    
                    # Encontra posição real no texto da página
                    actual_pos = page.text.find(passage)
                    if actual_pos == -1:
                        actual_pos = position
                    
                    context_before, context_after = self._get_context(
                        page.text,
                        actual_pos,
                        actual_pos + len(passage)
                    )
                    
                    search_match = SearchMatch(
                        text=passage,
                        position=TextPosition(
                            page=page.number,
                            start_char=actual_pos,
                            end_char=actual_pos + len(passage)
                        ),
                        score=score,
                        context_before=context_before,
                        context_after=context_after,
                        match_type="semantic"
                    )
                    
                    matches.append(search_match)
                    
            except Exception as e:
                logger.warning(
                    f"Erro na busca semântica página {page.number}: {e}"
                )
        
        return matches
    
    def _get_context(
        self,
        text: str,
        start: int,
        end: int
    ) -> Tuple[str, str]:
        """
        Obtém contexto antes e depois do match.
        
        Args:
            text: Texto completo.
            start: Posição inicial do match.
            end: Posição final do match.
        
        Returns:
            Tuple[str, str]: (contexto_antes, contexto_depois)
        """
        # Contexto antes
        context_start = max(0, start - self._context_size)
        context_before = text[context_start:start].strip()
        
        # Limpa até início de palavra
        if context_start > 0 and context_before:
            space_pos = context_before.find(" ")
            if space_pos != -1:
                context_before = context_before[space_pos + 1:]
        
        # Contexto depois
        context_end = min(len(text), end + self._context_size)
        context_after = text[end:context_end].strip()
        
        # Limpa até fim de palavra
        if context_end < len(text) and context_after:
            space_pos = context_after.rfind(" ")
            if space_pos != -1:
                context_after = context_after[:space_pos]
        
        return context_before, context_after
    
    def _deduplicate_matches(
        self,
        matches: List[SearchMatch]
    ) -> List[SearchMatch]:
        """
        Remove matches duplicados ou sobrepostos.
        
        Args:
            matches: Lista de matches.
        
        Returns:
            List[SearchMatch]: Matches sem duplicatas.
        """
        if not matches:
            return matches
        
        # Agrupa por página
        by_page: dict = {}
        for match in matches:
            page = match.position.page
            if page not in by_page:
                by_page[page] = []
            by_page[page].append(match)
        
        result = []
        
        for page_matches in by_page.values():
            # Ordena por posição
            page_matches.sort(key=lambda m: m.position.start_char)
            
            # Remove sobreposições, mantendo o de maior score
            deduped = []
            
            for match in page_matches:
                # Verifica se sobrepõe com algum existente
                overlaps = False
                for i, existing in enumerate(deduped):
                    if self._ranges_overlap(
                        match.position.start_char,
                        match.position.end_char,
                        existing.position.start_char,
                        existing.position.end_char
                    ):
                        overlaps = True
                        # Mantém o de maior score
                        if match.score > existing.score:
                            deduped[i] = match
                        break
                
                if not overlaps:
                    deduped.append(match)
            
            result.extend(deduped)
        
        return result
    
    def _ranges_overlap(
        self,
        start1: int,
        end1: int,
        start2: int,
        end2: int
    ) -> bool:
        """Verifica se dois ranges se sobrepõem."""
        return start1 < end2 and start2 < end1
    
    def quick_search(
        self,
        document: Document,
        query: str
    ) -> List[SearchMatch]:
        """
        Busca rápida por uma string simples.
        
        Args:
            document: Documento fonte.
            query: String de busca.
        
        Returns:
            List[SearchMatch]: Matches encontrados.
        """
        matches = []
        
        for page in document.pages:
            if not page.text:
                continue
            
            for match in re.finditer(
                re.escape(query),
                page.text,
                re.IGNORECASE
            ):
                start, end = match.span()
                
                context_before, context_after = self._get_context(
                    page.text, start, end
                )
                
                search_match = SearchMatch(
                    text=page.text[start:end],
                    position=TextPosition(
                        page=page.number,
                        start_char=start,
                        end_char=end
                    ),
                    score=1.0,
                    context_before=context_before,
                    context_after=context_after,
                    match_type="exact"
                )
                
                matches.append(search_match)
        
        return matches
