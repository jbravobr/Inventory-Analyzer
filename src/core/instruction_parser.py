"""Módulo para parsing de instruções em linguagem natural."""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional, Set

from ..config.settings import Settings, get_settings

logger = logging.getLogger(__name__)


@dataclass
class Instruction:
    """Representa uma instrução de busca parseada."""
    
    raw_text: str
    search_terms: List[str] = field(default_factory=list)
    semantic_query: str = ""
    is_required: bool = False
    category: str = "general"
    
    @property
    def has_search_terms(self) -> bool:
        """Verifica se tem termos de busca."""
        return len(self.search_terms) > 0
    
    def __str__(self) -> str:
        return self.raw_text


@dataclass
class ParsedInstructions:
    """Conjunto de instruções parseadas."""
    
    instructions: List[Instruction] = field(default_factory=list)
    source_file: Optional[Path] = None
    
    @property
    def count(self) -> int:
        """Número de instruções."""
        return len(self.instructions)
    
    def __iter__(self):
        return iter(self.instructions)
    
    def __len__(self):
        return len(self.instructions)


class InstructionParser:
    """
    Parser de instruções em linguagem natural.
    
    Converte instruções em formato de bullet points para
    estruturas de busca otimizadas.
    """
    
    # Padrões de marcadores de bullets
    BULLET_PATTERNS = [
        r"^\s*[-•*]\s*",           # - bullet, • bullet, * bullet
        r"^\s*\d+[.)]\s*",         # 1. ou 1) numerado
        r"^\s*[a-zA-Z][.)]\s*",    # a. ou a) letras
        r"^\s*\[\s*\]\s*",         # [ ] checkbox vazio
        r"^\s*\[x\]\s*",           # [x] checkbox marcado
    ]
    
    # Palavras que indicam obrigatoriedade
    REQUIRED_MARKERS = {
        "obrigatório", "obrigatoriamente", "deve", "devem",
        "precisa", "precisam", "necessário", "essencial",
        "importante", "crítico", "fundamental"
    }
    
    # Categorias de instruções para contratos de locação
    CATEGORY_KEYWORDS = {
        "partes": ["locador", "locatário", "fiador", "nome", "cpf", "rg", "qualificação"],
        "imovel": ["imóvel", "endereço", "apartamento", "casa", "área", "cômodos"],
        "valores": ["aluguel", "valor", "preço", "reais", "r$", "pagamento"],
        "prazos": ["prazo", "vigência", "início", "término", "duração", "meses", "anos"],
        "garantias": ["garantia", "caução", "fiança", "seguro", "depósito"],
        "clausulas": ["cláusula", "condição", "multa", "rescisão", "penalidade"],
        "obrigacoes": ["obrigação", "dever", "responsabilidade", "manutenção"],
    }
    
    def __init__(self, settings: Optional[Settings] = None):
        """
        Inicializa o parser.
        
        Args:
            settings: Configurações do aplicativo.
        """
        self.settings = settings or get_settings()
        self._compiled_bullets = [
            re.compile(p, re.MULTILINE) for p in self.BULLET_PATTERNS
        ]
    
    def parse_file(self, file_path: Path) -> ParsedInstructions:
        """
        Parseia instruções de um arquivo.
        
        Args:
            file_path: Caminho do arquivo de instruções.
        
        Returns:
            ParsedInstructions: Instruções parseadas.
        
        Raises:
            FileNotFoundError: Se arquivo não existir.
        """
        file_path = Path(file_path)
        
        if not file_path.exists():
            raise FileNotFoundError(f"Arquivo não encontrado: {file_path}")
        
        logger.info(f"Lendo instruções de: {file_path}")
        
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
        
        result = self.parse_text(content)
        result.source_file = file_path
        
        return result
    
    def parse_text(self, text: str) -> ParsedInstructions:
        """
        Parseia instruções de uma string.
        
        Args:
            text: Texto com instruções em bullets.
        
        Returns:
            ParsedInstructions: Instruções parseadas.
        """
        result = ParsedInstructions()
        
        # Divide por linhas
        lines = text.strip().split("\n")
        
        for line in lines:
            line = line.strip()
            
            if not line:
                continue
            
            # Remove marcador de bullet
            clean_line = self._remove_bullet_marker(line)
            
            if clean_line and len(clean_line) > 2:
                instruction = self._parse_single_instruction(clean_line)
                result.instructions.append(instruction)
        
        logger.info(f"Parseadas {result.count} instruções")
        
        return result
    
    def _remove_bullet_marker(self, line: str) -> str:
        """
        Remove marcador de bullet da linha.
        
        Args:
            line: Linha de texto.
        
        Returns:
            str: Linha sem marcador.
        """
        for pattern in self._compiled_bullets:
            line = pattern.sub("", line)
        
        return line.strip()
    
    def _parse_single_instruction(self, text: str) -> Instruction:
        """
        Parseia uma única instrução.
        
        Args:
            text: Texto da instrução.
        
        Returns:
            Instruction: Instrução parseada.
        """
        instruction = Instruction(raw_text=text)
        
        # Extrai termos de busca
        instruction.search_terms = self._extract_search_terms(text)
        
        # Cria query semântica
        instruction.semantic_query = self._create_semantic_query(text)
        
        # Verifica se é obrigatório
        instruction.is_required = self._check_required(text)
        
        # Determina categoria
        instruction.category = self._determine_category(text)
        
        return instruction
    
    def _extract_search_terms(self, text: str) -> List[str]:
        """
        Extrai termos de busca do texto.
        
        Args:
            text: Texto da instrução.
        
        Returns:
            List[str]: Termos de busca.
        """
        terms = []
        text_lower = text.lower()
        
        # Adiciona termos jurídicos conhecidos
        legal_terms = self.settings.legal_terms
        
        for term in legal_terms.key_sections:
            if term.lower() in text_lower:
                terms.append(term)
        
        for term in legal_terms.parties:
            if term.lower() in text_lower:
                terms.append(term)
        
        # Extrai palavras entre aspas
        quoted = re.findall(r'"([^"]+)"', text)
        terms.extend(quoted)
        
        quoted_single = re.findall(r"'([^']+)'", text)
        terms.extend(quoted_single)
        
        # Extrai substantivos importantes (palavras capitalizadas)
        capitalized = re.findall(r'\b[A-Z][a-záéíóúâêîôûãõç]+\b', text)
        terms.extend(capitalized)
        
        # Remove duplicatas mantendo ordem
        seen: Set[str] = set()
        unique = []
        for term in terms:
            term_lower = term.lower()
            if term_lower not in seen:
                seen.add(term_lower)
                unique.append(term)
        
        return unique
    
    def _create_semantic_query(self, text: str) -> str:
        """
        Cria query semântica a partir da instrução.
        
        Args:
            text: Texto da instrução.
        
        Returns:
            str: Query semântica otimizada.
        """
        # Remove palavras comuns que não agregam à busca
        stopwords = {
            "encontrar", "localizar", "buscar", "procurar", "identificar",
            "verificar", "checar", "analisar", "o", "a", "os", "as", "de",
            "do", "da", "dos", "das", "em", "no", "na", "nos", "nas", "que",
            "qual", "quais", "onde", "como", "se", "para", "com", "sem"
        }
        
        words = text.lower().split()
        filtered = [w for w in words if w not in stopwords and len(w) > 2]
        
        return " ".join(filtered)
    
    def _check_required(self, text: str) -> bool:
        """
        Verifica se a instrução é obrigatória.
        
        Args:
            text: Texto da instrução.
        
        Returns:
            bool: True se obrigatório.
        """
        text_lower = text.lower()
        
        for marker in self.REQUIRED_MARKERS:
            if marker in text_lower:
                return True
        
        return False
    
    def _determine_category(self, text: str) -> str:
        """
        Determina a categoria da instrução.
        
        Args:
            text: Texto da instrução.
        
        Returns:
            str: Categoria identificada.
        """
        text_lower = text.lower()
        
        category_scores = {}
        
        for category, keywords in self.CATEGORY_KEYWORDS.items():
            score = sum(1 for kw in keywords if kw in text_lower)
            if score > 0:
                category_scores[category] = score
        
        if category_scores:
            return max(category_scores, key=category_scores.get)
        
        return "general"
    
    def create_example_file(self, output_path: Path) -> None:
        """
        Cria arquivo de exemplo de instruções.
        
        Args:
            output_path: Caminho do arquivo a criar.
        """
        example_content = """# Instruções para análise do contrato de locação
# Use bullets (-), números (1.) ou asteriscos (*) para cada instrução

- Encontrar o nome completo do LOCADOR (proprietário do imóvel)
- Identificar o nome completo do LOCATÁRIO (inquilino)
- Localizar o endereço completo do imóvel objeto da locação
- Verificar o valor mensal do aluguel em reais
- Encontrar a data de início e término do contrato (vigência)
- Identificar a forma de reajuste do aluguel (índice utilizado)
- Localizar informações sobre a garantia (caução, fiador ou seguro fiança)
- Verificar as condições de multa por rescisão antecipada
- Encontrar as obrigações do locatário quanto à manutenção
- Identificar as condições para devolução do imóvel
- Localizar informações sobre benfeitorias (quem paga, autorização)
- Verificar o foro eleito para resolução de conflitos
"""
        
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(example_content)
        
        logger.info(f"Arquivo de exemplo criado: {output_path}")
