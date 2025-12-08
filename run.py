#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Inventory Analyzer - Analisador de Escrituras de Inventário

Analisa documentos PDF de inventário para extrair:
- Herdeiros
- Inventariante
- Bens BTG
- Divisão patrimonial

Gera relatório TXT e PDF com highlights coloridos.
"""

import sys
from pathlib import Path

# Adiciona src ao path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from inventory_main import main

if __name__ == "__main__":
    main()

