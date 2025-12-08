#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Document Analyzer - Analisador de Documentos PDF

Suporta múltiplos perfis de análise:

Perfil 'inventory' (Escritura de Inventário):
  - Herdeiros
  - Inventariante
  - Bens BTG
  - Divisão patrimonial

Perfil 'meeting_minutes' (Ata de Reunião de Quotistas):
  - Ativos envolvidos (ações, CRA, CRI, debêntures, cotas, CDB, etc.)
  - Quantidade e valores dos ativos

Gera relatório TXT e PDF com highlights coloridos (marca-texto).

Uso:
  python run.py analyze documento.pdf --profile inventory
  python run.py analyze ata.pdf --profile meeting_minutes
  python run.py profiles  # lista perfis disponíveis
"""

import sys
from pathlib import Path

# Adiciona src ao path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from inventory_main import main

if __name__ == "__main__":
    main()

