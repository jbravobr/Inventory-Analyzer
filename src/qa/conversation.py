"""
Gerenciamento de Histórico de Conversa.

Mantém o contexto das perguntas anteriores para permitir
perguntas de acompanhamento como "E sobre o valor?" ou
"Pode explicar melhor?".
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional, Dict, Any
from enum import Enum

logger = logging.getLogger(__name__)


class MemoryType(Enum):
    """Tipo de memória de conversa."""
    FULL = "full"                  # Mantém todas as interações
    SUMMARY = "summary"            # Resume interações antigas
    SLIDING_WINDOW = "sliding_window"  # Janela deslizante


@dataclass
class ConversationTurn:
    """Representa um turno de conversa (pergunta + resposta)."""
    
    question: str
    answer: str
    timestamp: datetime = field(default_factory=datetime.now)
    context_used: str = ""
    pages_referenced: List[int] = field(default_factory=list)
    confidence: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> dict:
        return {
            "question": self.question,
            "answer": self.answer,
            "timestamp": self.timestamp.isoformat(),
            "pages": self.pages_referenced,
            "confidence": self.confidence,
        }
    
    def format_for_context(self) -> str:
        """Formata o turno para incluir no contexto."""
        return f"Pergunta anterior: {self.question}\nResposta: {self.answer}"


class Conversation:
    """
    Gerencia o histórico de uma conversa de Q&A.
    
    Permite manter contexto entre perguntas para que o usuário
    possa fazer perguntas de acompanhamento.
    """
    
    def __init__(
        self,
        max_turns: int = 10,
        memory_type: MemoryType = MemoryType.SLIDING_WINDOW,
        document_name: str = ""
    ):
        """
        Inicializa uma nova conversa.
        
        Args:
            max_turns: Máximo de turnos a manter
            memory_type: Tipo de memória a usar
            document_name: Nome do documento sendo analisado
        """
        self.max_turns = max_turns
        self.memory_type = memory_type
        self.document_name = document_name
        self._turns: List[ConversationTurn] = []
        self._summary: str = ""
        self._created_at = datetime.now()
    
    def add_turn(
        self,
        question: str,
        answer: str,
        context_used: str = "",
        pages: Optional[List[int]] = None,
        confidence: float = 0.0,
        **metadata
    ) -> ConversationTurn:
        """
        Adiciona um novo turno à conversa.
        
        Args:
            question: Pergunta do usuário
            answer: Resposta gerada
            context_used: Contexto usado para gerar resposta
            pages: Páginas referenciadas
            confidence: Confiança da resposta
            **metadata: Metadados adicionais
        
        Returns:
            ConversationTurn criado
        """
        turn = ConversationTurn(
            question=question,
            answer=answer,
            context_used=context_used,
            pages_referenced=pages or [],
            confidence=confidence,
            metadata=metadata
        )
        
        self._turns.append(turn)
        
        # Aplica limite conforme tipo de memória
        if self.memory_type == MemoryType.SLIDING_WINDOW:
            if len(self._turns) > self.max_turns:
                self._turns = self._turns[-self.max_turns:]
        
        elif self.memory_type == MemoryType.SUMMARY:
            if len(self._turns) > self.max_turns:
                # Sumariza turnos antigos
                old_turns = self._turns[:-self.max_turns//2]
                self._update_summary(old_turns)
                self._turns = self._turns[-self.max_turns//2:]
        
        logger.debug(f"Turno adicionado. Total: {len(self._turns)}")
        
        return turn
    
    def _update_summary(self, turns: List[ConversationTurn]) -> None:
        """Atualiza o resumo com turnos antigos."""
        if not turns:
            return
        
        # Resumo simples: lista de tópicos discutidos
        topics = []
        for turn in turns:
            # Extrai palavras-chave da pergunta
            words = turn.question.lower().split()
            keywords = [w for w in words if len(w) > 4][:3]
            if keywords:
                topics.append(", ".join(keywords))
        
        if topics:
            self._summary = f"Tópicos anteriores: {'; '.join(topics)}"
    
    def get_context_for_new_question(self, include_turns: int = 3) -> str:
        """
        Obtém contexto da conversa para nova pergunta.
        
        Args:
            include_turns: Número de turnos recentes a incluir
        
        Returns:
            Contexto formatado
        """
        parts = []
        
        # Adiciona resumo se existir
        if self._summary:
            parts.append(f"[Histórico resumido: {self._summary}]")
        
        # Adiciona turnos recentes
        recent_turns = self._turns[-include_turns:] if self._turns else []
        
        for i, turn in enumerate(recent_turns):
            parts.append(f"\n--- Interação {i+1} ---")
            parts.append(turn.format_for_context())
        
        return "\n".join(parts) if parts else ""
    
    def get_last_turn(self) -> Optional[ConversationTurn]:
        """Retorna o último turno da conversa."""
        return self._turns[-1] if self._turns else None
    
    def get_all_turns(self) -> List[ConversationTurn]:
        """Retorna todos os turnos."""
        return self._turns.copy()
    
    def get_all_questions(self) -> List[str]:
        """Retorna todas as perguntas feitas."""
        return [turn.question for turn in self._turns]
    
    def get_all_pages_referenced(self) -> List[int]:
        """Retorna todas as páginas referenciadas na conversa."""
        pages = set()
        for turn in self._turns:
            pages.update(turn.pages_referenced)
        return sorted(pages)
    
    def clear(self) -> None:
        """Limpa o histórico da conversa."""
        self._turns.clear()
        self._summary = ""
        logger.info("Histórico da conversa limpo")
    
    def is_follow_up_question(self, question: str) -> bool:
        """
        Detecta se a pergunta é de acompanhamento.
        
        Args:
            question: Nova pergunta
        
        Returns:
            True se parece ser pergunta de acompanhamento
        """
        if not self._turns:
            return False
        
        question_lower = question.lower().strip()
        
        # Padrões de perguntas de acompanhamento
        follow_up_patterns = [
            "e ",
            "e o",
            "e a",
            "e sobre",
            "e quanto",
            "e qual",
            "mais sobre",
            "pode explicar",
            "explique melhor",
            "o que mais",
            "algo mais",
            "além disso",
            "também",
            "igualmente",
            "da mesma forma",
            "por quê",
            "por que",
            "como assim",
            "o que significa",
            "isso significa",
            "nesse caso",
            "neste caso",
        ]
        
        for pattern in follow_up_patterns:
            if question_lower.startswith(pattern):
                return True
        
        # Pergunta muito curta após contexto
        if len(question.split()) <= 5 and len(self._turns) > 0:
            return True
        
        return False
    
    def enrich_follow_up_question(self, question: str) -> str:
        """
        Enriquece uma pergunta de acompanhamento com contexto.
        
        Args:
            question: Pergunta original
        
        Returns:
            Pergunta enriquecida
        """
        if not self._turns or not self.is_follow_up_question(question):
            return question
        
        last_turn = self._turns[-1]
        
        # Adiciona contexto da pergunta anterior
        enriched = (
            f"Considerando a pergunta anterior: '{last_turn.question}' "
            f"e a resposta dada, agora: {question}"
        )
        
        return enriched
    
    @property
    def turn_count(self) -> int:
        """Número de turnos na conversa."""
        return len(self._turns)
    
    @property
    def duration_minutes(self) -> float:
        """Duração da conversa em minutos."""
        if not self._turns:
            return 0.0
        
        first = self._created_at
        last = self._turns[-1].timestamp
        
        return (last - first).total_seconds() / 60
    
    def to_dict(self) -> dict:
        """Serializa a conversa para dicionário."""
        return {
            "document": self.document_name,
            "created_at": self._created_at.isoformat(),
            "turn_count": len(self._turns),
            "memory_type": self.memory_type.value,
            "turns": [turn.to_dict() for turn in self._turns],
            "summary": self._summary,
        }
    
    def export_transcript(self) -> str:
        """
        Exporta a conversa como texto formatado.
        
        Returns:
            Transcrição da conversa
        """
        lines = [
            "=" * 60,
            "TRANSCRIÇÃO DA CONVERSA",
            "=" * 60,
            f"Documento: {self.document_name}",
            f"Data: {self._created_at.strftime('%d/%m/%Y %H:%M')}",
            f"Total de perguntas: {len(self._turns)}",
            "=" * 60,
            "",
        ]
        
        for i, turn in enumerate(self._turns, 1):
            lines.append(f"[Pergunta {i}] {turn.timestamp.strftime('%H:%M')}")
            lines.append(f"Usuário: {turn.question}")
            lines.append("")
            lines.append(f"Assistente: {turn.answer}")
            if turn.pages_referenced:
                lines.append(f"(Páginas: {', '.join(map(str, turn.pages_referenced))})")
            lines.append("")
            lines.append("-" * 40)
            lines.append("")
        
        return "\n".join(lines)

