"""Utilitários para processamento de texto."""

from __future__ import annotations

import re
import unicodedata
from typing import List, Tuple


class TextUtils:
    """Utilitários para manipulação de texto."""
    
    @staticmethod
    def normalize_text(text: str) -> str:
        """
        Normaliza texto removendo caracteres especiais.
        
        Args:
            text: Texto para normalizar.
        
        Returns:
            str: Texto normalizado.
        """
        # Normaliza Unicode
        text = unicodedata.normalize("NFKC", text)
        
        # Remove caracteres de controle (exceto newlines)
        text = "".join(
            c for c in text
            if unicodedata.category(c) != "Cc" or c in "\n\r\t"
        )
        
        # Normaliza espaços
        text = re.sub(r"[ \t]+", " ", text)
        text = re.sub(r"\n\s*\n", "\n\n", text)
        
        return text.strip()
    
    @staticmethod
    def split_sentences(text: str) -> List[str]:
        """
        Divide texto em sentenças.
        
        Args:
            text: Texto para dividir.
        
        Returns:
            List[str]: Lista de sentenças.
        """
        # Padrão para fim de sentença
        pattern = r'(?<=[.!?])\s+'
        sentences = re.split(pattern, text)
        
        return [s.strip() for s in sentences if s.strip()]
    
    @staticmethod
    def split_paragraphs(text: str) -> List[str]:
        """
        Divide texto em parágrafos.
        
        Args:
            text: Texto para dividir.
        
        Returns:
            List[str]: Lista de parágrafos.
        """
        paragraphs = text.split("\n\n")
        return [p.strip() for p in paragraphs if p.strip()]
    
    @staticmethod
    def extract_numbers(text: str) -> List[str]:
        """
        Extrai números do texto.
        
        Args:
            text: Texto fonte.
        
        Returns:
            List[str]: Números encontrados.
        """
        # Padrão para números (inclui decimais e monetários)
        pattern = r"R?\$?\s*\d{1,3}(?:[.,]\d{3})*(?:[.,]\d{2})?"
        matches = re.findall(pattern, text)
        
        return matches
    
    @staticmethod
    def extract_dates(text: str) -> List[str]:
        """
        Extrai datas do texto.
        
        Args:
            text: Texto fonte.
        
        Returns:
            List[str]: Datas encontradas.
        """
        patterns = [
            r"\d{1,2}/\d{1,2}/\d{2,4}",  # dd/mm/yyyy
            r"\d{1,2}-\d{1,2}-\d{2,4}",  # dd-mm-yyyy
            r"\d{1,2}\s+de\s+\w+\s+de\s+\d{4}",  # dd de mês de yyyy
        ]
        
        dates = []
        for pattern in patterns:
            dates.extend(re.findall(pattern, text, re.IGNORECASE))
        
        return dates
    
    @staticmethod
    def extract_cpf(text: str) -> List[str]:
        """
        Extrai CPFs do texto.
        
        Args:
            text: Texto fonte.
        
        Returns:
            List[str]: CPFs encontrados.
        """
        pattern = r"\d{3}[.\s]?\d{3}[.\s]?\d{3}[-.\s]?\d{2}"
        return re.findall(pattern, text)
    
    @staticmethod
    def extract_cnpj(text: str) -> List[str]:
        """
        Extrai CNPJs do texto.
        
        Args:
            text: Texto fonte.
        
        Returns:
            List[str]: CNPJs encontrados.
        """
        pattern = r"\d{2}[.\s]?\d{3}[.\s]?\d{3}[/.\s]?\d{4}[-.\s]?\d{2}"
        return re.findall(pattern, text)
    
    @staticmethod
    def highlight_in_text(
        text: str,
        search_terms: List[str],
        marker_start: str = ">>>",
        marker_end: str = "<<<"
    ) -> str:
        """
        Destaca termos no texto.
        
        Args:
            text: Texto fonte.
            search_terms: Termos para destacar.
            marker_start: Marcador de início.
            marker_end: Marcador de fim.
        
        Returns:
            str: Texto com destaques.
        """
        result = text
        
        for term in search_terms:
            pattern = re.compile(re.escape(term), re.IGNORECASE)
            result = pattern.sub(f"{marker_start}\\g<0>{marker_end}", result)
        
        return result
    
    @staticmethod
    def calculate_word_count(text: str) -> int:
        """
        Conta palavras no texto.
        
        Args:
            text: Texto fonte.
        
        Returns:
            int: Número de palavras.
        """
        words = text.split()
        return len(words)
    
    @staticmethod
    def truncate_text(
        text: str,
        max_length: int,
        suffix: str = "..."
    ) -> str:
        """
        Trunca texto para tamanho máximo.
        
        Args:
            text: Texto fonte.
            max_length: Tamanho máximo.
            suffix: Sufixo a adicionar.
        
        Returns:
            str: Texto truncado.
        """
        if len(text) <= max_length:
            return text
        
        return text[:max_length - len(suffix)].rsplit(" ", 1)[0] + suffix
    
    @staticmethod
    def clean_ocr_text(text: str) -> str:
        """
        Limpa texto extraído por OCR.
        
        Remove artefatos comuns de OCR.
        
        Args:
            text: Texto OCR.
        
        Returns:
            str: Texto limpo.
        """
        # Remove linhas com apenas caracteres especiais
        lines = text.split("\n")
        cleaned_lines = []
        
        for line in lines:
            # Remove linha se for só caracteres especiais
            if re.match(r"^[\s\W]*$", line) and len(line.strip()) > 0:
                continue
            
            # Remove múltiplos espaços
            line = re.sub(r"\s+", " ", line)
            
            cleaned_lines.append(line)
        
        return "\n".join(cleaned_lines)
    
    @staticmethod
    def find_context(
        text: str,
        position: int,
        context_chars: int = 100
    ) -> Tuple[str, str]:
        """
        Encontra contexto ao redor de uma posição.
        
        Args:
            text: Texto fonte.
            position: Posição central.
            context_chars: Caracteres de contexto.
        
        Returns:
            Tuple[str, str]: (contexto_antes, contexto_depois)
        """
        start = max(0, position - context_chars)
        end = min(len(text), position + context_chars)
        
        before = text[start:position].strip()
        after = text[position:end].strip()
        
        # Limpa até início/fim de palavra
        if start > 0 and before:
            space_pos = before.find(" ")
            if space_pos != -1:
                before = before[space_pos + 1:]
        
        if end < len(text) and after:
            space_pos = after.rfind(" ")
            if space_pos != -1:
                after = after[:space_pos]
        
        return before, after
