"""
Módulo DKR - Domain Knowledge Rules.

Sistema de regras de domínio configuráveis para melhorar
a acurácia das respostas do Q&A sem necessidade de código.

Funcionalidades:
- Parser de arquivos .rules em linguagem humanizada
- Detecção de intenção de perguntas
- Expansão de queries para melhor retrieval
- Validação e correção de respostas
- Tudo 100% OFFLINE

Uso básico:
    from dkr import DKREngine
    
    engine = DKREngine("domain_rules/licencas_software.rules")
    result = engine.process(question, raw_answer, context)
"""

from .models import (
    DomainFact,
    IntentPattern,
    ValidationRule,
    QueryExpansion,
    Synonym,
    TermNormalization,
    CompiledRules,
    DKRResult,
)
from .parser import DKRParser
from .engine import DKREngine, get_dkr_engine
from .validator import DKRValidator, ValidationReport
from .cache import DKRCache, get_dkr_cache
from .wizard import DKRWizard, run_wizard
from .repl import DKREPL, run_repl

__all__ = [
    # Models
    "DomainFact",
    "IntentPattern", 
    "ValidationRule",
    "QueryExpansion",
    "Synonym",
    "TermNormalization",
    "CompiledRules",
    "DKRResult",
    # Core
    "DKRParser",
    "DKREngine",
    "get_dkr_engine",
    "DKRValidator",
    "ValidationReport",
    # Cache
    "DKRCache",
    "get_dkr_cache",
    # Tools
    "DKRWizard",
    "run_wizard",
    "DKREPL",
    "run_repl",
]

__version__ = "1.0.0"

