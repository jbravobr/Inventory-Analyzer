"""
Módulo de Q&A (Perguntas e Respostas) sobre documentos.

Este módulo permite fazer perguntas em linguagem natural sobre
o conteúdo de documentos PDF, com respostas baseadas no contexto
encontrado via RAG.

Funciona em modo offline e online, seguindo a mesma lógica do
restante do sistema.

Componentes:
- QAEngine: Motor principal de Q&A
- TemplateLoader: Carrega templates de prompts de arquivos .txt
- Conversation: Gerencia histórico de conversa
- KnowledgeBase: Base de conhecimento estruturado
- QAValidator: Valida qualidade das respostas
- ResponseCache: Cache de respostas frequentes
"""

from .template_loader import TemplateLoader, PromptTemplate
from .qa_engine import QAEngine, QAResponse, QAConfig
from .conversation import Conversation, ConversationTurn
from .knowledge_base import KnowledgeBase
from .qa_validator import QAValidator, ValidationResult
from .cache import ResponseCache

__all__ = [
    "QAEngine",
    "QAResponse", 
    "QAConfig",
    "TemplateLoader",
    "PromptTemplate",
    "Conversation",
    "ConversationTurn",
    "KnowledgeBase",
    "QAValidator",
    "ValidationResult",
    "ResponseCache",
]

