# 📈 Guia de Melhoria de Acurácia do Document Analyzer

Este documento explica como melhorar a precisão da extração de informações do Document Analyzer, detalhando cada componente do pipeline e como otimizá-lo.

---

## 📋 Índice

1. [Visão Geral do Pipeline](#visão-geral-do-pipeline)
2. [Diagnóstico de Problemas](#diagnóstico-de-problemas)
3. [Melhorias no OCR](#1-melhorias-no-ocr)
4. [Melhorias no Chunking](#2-melhorias-no-chunking)
5. [Melhorias no Retrieval](#3-melhorias-no-retrieval)
6. [Melhorias nas Instruções](#4-melhorias-nas-instruções)
7. [Melhorias nos Padrões de Extração](#5-melhorias-nos-padrões-de-extração)
8. [Melhorias no Dicionário de Termos](#6-melhorias-no-dicionário-de-termos)
9. [Checklist de Otimização](#checklist-de-otimização)

---

## Visão Geral do Pipeline

```
┌─────────┐    ┌─────────┐    ┌──────────┐    ┌───────────┐    ┌──────────┐
│   PDF   │───►│   OCR   │───►│ Chunking │───►│ Retrieval │───►│ Extração │
│         │    │         │    │          │    │   (RAG)   │    │  (Regex) │
└─────────┘    └─────────┘    └──────────┘    └───────────┘    └──────────┘
     │              │              │               │                │
     │              │              │               │                │
   INPUT      Qualidade do    Divisão do      Busca dos        Padrões de
              texto extraído  texto em        chunks           extração
                              pedaços         relevantes       de dados
```

**Cada etapa pode afetar a acurácia final. Problemas em etapas anteriores se propagam.**

---

## Diagnóstico de Problemas

Antes de otimizar, identifique onde está o problema:

### Sintomas e Causas Prováveis

| Sintoma | Causa Provável | Seção a Consultar |
|---------|----------------|-------------------|
| Texto extraído ilegível ou com erros | OCR de baixa qualidade | [Melhorias no OCR](#1-melhorias-no-ocr) |
| Informação existe mas não é encontrada | Retrieval não recupera chunks certos | [Melhorias no Retrieval](#3-melhorias-no-retrieval) |
| Informação encontrada mas não extraída | Padrões regex não reconhecem formato | [Melhorias nos Padrões](#5-melhorias-nos-padrões-de-extração) |
| Muitos falsos positivos | Padrões muito genéricos | [Melhorias nos Padrões](#5-melhorias-nos-padrões-de-extração) |
| Chunks cortam informação importante | Chunking inadequado | [Melhorias no Chunking](#2-melhorias-no-chunking) |
| Tipo de ativo não reconhecido | Dicionário de termos incompleto | [Dicionário de Termos](#6-melhorias-no-dicionário-de-termos) |

### Como Diagnosticar

1. **Verificar saída do OCR:**
   ```powershell
   python run.py extract documento.pdf
   ```
   Analise o arquivo `.txt` gerado para verificar qualidade do texto.

2. **Verificar chunks recuperados:**
   Ative logs detalhados em `config.yaml`:
   ```yaml
   app:
     log_level: "DEBUG"
   ```

3. **Testar queries manualmente:**
   Use o modo interativo (se disponível) ou analise os logs de retrieval.

---

## 1. Melhorias no OCR

O OCR é a **base de tudo**. Texto mal extraído = análise ruim.

### 1.1 Aumentar Resolução (DPI)

**O que é:** DPI (dots per inch) define a resolução da imagem usada no OCR.

**Como fazer:**

Edite `config.yaml`:
```yaml
ocr:
  dpi: 400    # Padrão é 300. Aumente para documentos de baixa qualidade
```

| DPI | Qualidade | Velocidade | Uso Recomendado |
|-----|-----------|------------|-----------------|
| 200 | Baixa | Muito rápido | PDFs digitais nativos |
| 300 | Média | Rápido | Documentos escaneados normais |
| 400 | Alta | Médio | Documentos com fontes pequenas |
| 600 | Muito Alta | Lento | Documentos antigos ou deteriorados |

**Trade-off:** ↑ DPI = ↑ Qualidade + ↓ Velocidade + ↑ Memória

---

### 1.2 Ajustar Modo de Segmentação (PSM)

**O que é:** O PSM define como o Tesseract interpreta a estrutura da página.

**Como fazer:**

Edite `config.yaml`:
```yaml
ocr:
  config: "--psm 6 --oem 3"    # Experimente diferentes valores de PSM
```

| PSM | Descrição | Quando Usar |
|-----|-----------|-------------|
| `--psm 1` | Auto com OSD | Documentos com rotação |
| `--psm 3` | Auto (padrão) | Maioria dos documentos |
| `--psm 4` | Coluna única de texto | Documentos simples |
| `--psm 6` | Bloco de texto uniforme | Tabelas, formulários |
| `--psm 11` | Texto esparso | Documentos com muito espaço em branco |
| `--psm 12` | Texto esparso com OSD | Documentos mistos |

**Experimente:** Se o documento tem tabelas, tente `--psm 6`. Se tem múltiplas colunas, tente `--psm 1`.

---

### 1.3 Usar Múltiplos Idiomas

**O que é:** Documentos podem ter termos em inglês misturados com português.

**Como fazer:**

```yaml
ocr:
  language: "por+eng"    # Português + Inglês
```

**Opções:**
- `por` - Apenas português
- `eng` - Apenas inglês
- `por+eng` - Ambos (mais lento, mais preciso para docs mistos)

---

### 1.4 Pré-processamento de Imagem

**O que é:** Melhorar a imagem antes do OCR.

**Como fazer:** Modifique `src/core/ocr_extractor.py`:

```python
import cv2
import numpy as np

def preprocess_image(image):
    """Pré-processa imagem para melhorar OCR."""
    # Converter para escala de cinza
    gray = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2GRAY)
    
    # Aumentar contraste
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
    enhanced = clahe.apply(gray)
    
    # Binarização adaptativa (remove sombras)
    binary = cv2.adaptiveThreshold(
        enhanced, 255, 
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
        cv2.THRESH_BINARY, 11, 2
    )
    
    # Remoção de ruído
    denoised = cv2.fastNlMeansDenoising(binary, None, 10, 7, 21)
    
    return Image.fromarray(denoised)
```

**Técnicas disponíveis:**
| Técnica | Efeito | Quando Usar |
|---------|--------|-------------|
| Binarização | Converte para preto e branco | Documentos com fundo colorido |
| CLAHE | Aumenta contraste local | Documentos desbotados |
| Denoising | Remove ruído | Documentos escaneados |
| Deskew | Corrige inclinação | Documentos tortos |

---

## 2. Melhorias no Chunking

O chunking divide o documento em pedaços. Chunks mal divididos = contexto perdido.

### 2.1 Ajustar Tamanho do Chunk

**O que é:** Tamanho máximo de cada pedaço de texto.

**Como fazer:**

```yaml
rag:
  chunking:
    chunk_size: 500      # Aumente se informações estão sendo cortadas
    chunk_overlap: 150   # Aumente para mais contexto compartilhado
```

| Cenário | chunk_size | chunk_overlap | Motivo |
|---------|------------|---------------|--------|
| Documentos técnicos | 300-400 | 100 | Precisão em termos específicos |
| Documentos narrativos | 500-600 | 150 | Manter contexto de parágrafos |
| Tabelas e listas | 200-300 | 50 | Evitar misturar linhas |
| Contratos longos | 400-500 | 100 | Balanceado |

**Regra geral:**
- **↓ chunk_size** = Mais preciso, mas pode perder contexto
- **↑ chunk_size** = Mais contexto, mas menos preciso
- **↑ overlap** = Menos chance de cortar informação importante

---

### 2.2 Escolher Estratégia de Chunking

**O que é:** Como o texto é dividido.

**Como fazer:**

```yaml
rag:
  chunking:
    strategy: "semantic_sections"    # Opções: fixed_size, sentence, paragraph, recursive, semantic_sections
```

| Estratégia | Descrição | Melhor Para |
|------------|-----------|-------------|
| `fixed_size` | Divide a cada N caracteres | Textos uniformes |
| `sentence` | Divide por sentenças (pontuação) | Textos narrativos |
| `paragraph` | Divide por parágrafos | Documentos bem formatados |
| `recursive` | Tenta parágrafo → sentença → tamanho | Documentos gerais |
| `semantic_sections` | ⭐ **NOVO** - Detecta seções lógicas (headers, numeração, palavras-chave) | **Recomendado para documentos estruturados** |

### 2.2.1 ⭐ Chunking Semântico por Seções (NOVO)

A estratégia `semantic_sections` é ideal para documentos estruturados como:
- Licenças de software
- Contratos jurídicos
- Atas de reunião
- Escrituras de inventário

**O que ela detecta:**
- Headers em maiúsculas
- Numeração de seções (1., 1.1, I., a), etc.)
- Palavras-chave de domínio (GPL, AGPL, COMPATIBILIDADE, etc.)
- Cláusulas e artigos

**Configuração otimizada para licenças:**
```yaml
rag:
  chunking:
    strategy: "semantic_sections"
    chunk_size: 800       # Chunks maiores para mais contexto
    chunk_overlap: 100    # 50-100 recomendado
```

---

### 2.3 Ajustar Tamanho Mínimo

**O que é:** Chunks menores que este valor são descartados.

```yaml
rag:
  chunking:
    min_chunk_size: 50    # Reduza se informações curtas são importantes
```

**Quando reduzir:** Se o documento tem listas ou itens curtos importantes.

---

## 3. Melhorias no Retrieval

O retrieval busca os chunks relevantes para cada pergunta.

### 3.1 Aumentar Número de Chunks Recuperados

**O que é:** Quantos chunks são retornados por query.

**Como fazer:**

```yaml
rag:
  retrieval:
    top_k: 15    # Padrão é 10. Aumente para mais contexto
```

| top_k | Efeito | Trade-off |
|-------|--------|-----------|
| 5 | Apenas os mais relevantes | Pode perder informação |
| 10 | Balanceado | Padrão recomendado |
| 15-20 | Mais abrangente | Pode incluir ruído |
| 30+ | Máxima cobertura | Lento, muito ruído |

---

### 3.2 Ajustar Score Mínimo

**O que é:** Limiar de similaridade para aceitar um chunk.

```yaml
rag:
  retrieval:
    min_score: 0.15    # Padrão é 0.2. Reduza para ser menos restritivo
```

| min_score | Efeito |
|-----------|--------|
| 0.3+ | Muito restritivo (pode perder informação) |
| 0.2 | Balanceado |
| 0.1-0.15 | Permissivo (mais resultados, mais ruído) |
| 0.05 | Muito permissivo |

**Dica:** Se informações não estão sendo encontradas, reduza o `min_score`.

---

### 3.3 Habilitar Busca Híbrida (BM25 + Embeddings)

**O que é:** Combina busca semântica (embeddings) + busca lexical BM25 (palavras exatas).

```yaml
rag:
  retrieval:
    use_hybrid_search: true    # Recomendado: true
    bm25_weight: 0.4           # ⭐ NOVO: Peso do BM25
    semantic_weight: 0.6       # ⭐ NOVO: Peso dos embeddings
```

**Por que usar:**
- **Embeddings semânticos** encontram sinônimos ("herdeiro" ≈ "sucessor"), significado contextual
- **BM25** encontra termos técnicos exatos (GPL, AGPL, CPF, números de conta, tickers)
- Combinadas via **RRF (Reciprocal Rank Fusion)** = melhor cobertura

**Quando ajustar os pesos:**

| Cenário | bm25_weight | semantic_weight | Motivo |
|---------|-------------|-----------------|--------|
| Documentos técnicos (licenças, contratos) | 0.4-0.5 | 0.5-0.6 | Termos técnicos importantes |
| Perguntas em linguagem natural | 0.3 | 0.7 | Semântica mais relevante |
| Busca por siglas/códigos | 0.6 | 0.4 | BM25 melhor para exatos |
| Balanceado (padrão) | 0.4 | 0.6 | Bom para maioria |

---

### 3.4 Habilitar MMR (Diversidade)

**O que é:** Evita retornar chunks muito similares entre si.

```yaml
rag:
  retrieval:
    use_mmr: true
    mmr_diversity: 0.3    # 0.0 = só relevância, 1.0 = só diversidade
```

**Quando usar:**
- `mmr_diversity: 0.2-0.3` - Padrão, boa diversidade
- `mmr_diversity: 0.5` - Mais diversidade (documento com repetições)
- `mmr_diversity: 0.0` - Desabilitado (documento pequeno)

---

### 3.5 Habilitar Re-ranking

**O que é:** Segunda passada para reordenar resultados por relevância.

```yaml
rag:
  retrieval:
    use_reranking: true    # Recomendado: true
```

**Benefício:** Melhora a ordenação dos resultados, colocando os mais relevantes primeiro.

---

## 4. Melhorias nas Instruções

As instruções definem as queries usadas para buscar informações.

### 4.1 Localização dos Arquivos

```
instructions/
├── inventory_analysis.txt        # Instruções para inventário
└── meeting_minutes_analysis.txt  # Instruções para atas de reunião
```

### 4.2 Estrutura das Instruções

Cada linha é uma query separada:

```text
# Comentários começam com #
# Linhas em branco são ignoradas

Quais são os herdeiros mencionados no documento?
Identifique o inventariante nomeado
Liste todos os bens com menção a BTG
```

### 4.3 Boas Práticas para Queries

**✅ BOM - Queries específicas:**
```text
Quais são os nomes completos dos herdeiros com seus respectivos CPFs?
Identifique o inventariante e suas qualificações
Liste as ações e suas quantidades com os tickers
```

**❌ RUIM - Queries vagas:**
```text
Herdeiros
Inventariante
Ações
```

### 4.4 Técnicas para Melhorar Queries

| Técnica | Exemplo | Benefício |
|---------|---------|-----------|
| Ser específico | "Qual o CPF de cada herdeiro?" vs "CPFs" | Contexto claro |
| Usar sinônimos | "herdeiros OU sucessores OU beneficiários" | Maior cobertura |
| Incluir contexto | "Na seção de partilha, quais percentuais..." | Direciona busca |
| Perguntas múltiplas | Dividir em várias queries específicas | Melhor precisão |

### 4.5 Exemplo de Arquivo de Instruções Otimizado

```text
# ============================================
# Instruções de Análise - Ata de Reunião
# ============================================

# ATIVOS - Queries específicas por tipo
Identifique todas as ações mencionadas com seus tickers (ex: PETR4, VALE3)
Liste os CRAs (Certificados de Recebíveis do Agronegócio) com emissor e série
Liste os CRIs (Certificados de Recebíveis Imobiliários) com emissor e série
Identifique as debêntures com nome do emissor e características
Quais cotas de fundos de investimento são mencionadas?
Liste os títulos públicos (Tesouro, NTN, LFT, LTN)

# QUANTIDADES - Queries específicas
Qual a quantidade de cada ação mencionada?
Qual o valor nominal dos títulos de renda fixa?
Qual o valor total da operação ou distribuição?
Identifique preços unitários e totais

# INFORMAÇÕES DO FUNDO
Qual o nome completo do fundo de investimento?
Qual o CNPJ do fundo?
Quem é o administrador do fundo?
Quem é o gestor do fundo?

# DELIBERAÇÕES
Quais foram as deliberações aprovadas na reunião?
Qual foi o resultado das votações?
```

---

## 5. Melhorias nos Padrões de Extração

Os padrões regex extraem dados estruturados dos chunks recuperados.

### 5.1 Localização do Código

- **Inventário:** `src/inventory/analyzer.py`
- **Atas de Reunião:** `src/inventory/meeting_minutes_analyzer.py`

### 5.2 Padrões Existentes

Exemplo de padrões em `meeting_minutes_analyzer.py`:

```python
# Padrão para ações
STOCK_PATTERN = r"(\d+[\d.]*)\s*(ações?|papéis?)\s+(?:de\s+)?(\w+)"

# Padrão para valores monetários
MONEY_PATTERN = r"R\$\s*([\d.,]+)"

# Padrão para percentuais
PERCENT_PATTERN = r"(\d+[,.]?\d*)\s*%"

# Padrão para CPF
CPF_PATTERN = r"\d{3}[.\s]?\d{3}[.\s]?\d{3}[-.\s]?\d{2}"

# Padrão para CNPJ
CNPJ_PATTERN = r"\d{2}[.\s]?\d{3}[.\s]?\d{3}[/\s]?\d{4}[-.\s]?\d{2}"
```

### 5.3 Como Adicionar Novos Padrões

**Exemplo:** Adicionar extração de ISINs (código internacional de ativos)

1. **Identifique o formato:** ISIN = 2 letras + 10 caracteres alfanuméricos
   - Exemplo: `BRPABORCTF18`

2. **Crie o padrão regex:**
   ```python
   ISIN_PATTERN = r"\b([A-Z]{2}[A-Z0-9]{10})\b"
   ```

3. **Adicione ao código de extração:**
   ```python
   def _extract_isins(self, text: str) -> List[str]:
       """Extrai códigos ISIN do texto."""
       import re
       matches = re.findall(ISIN_PATTERN, text)
       return list(set(matches))  # Remove duplicatas
   ```

### 5.4 Testando Padrões Regex

Use o Python interativo para testar:

```python
import re

text = """
A operação envolve 1.500 ações PETR4 ao preço de R$ 32,50,
totalizando R$ 48.750,00. O ISIN é BRPABORCTF18.
"""

# Teste seu padrão
pattern = r"\b([A-Z]{2}[A-Z0-9]{10})\b"
matches = re.findall(pattern, text)
print(matches)  # ['BRPABORCTF18']
```

### 5.5 Padrões Comuns para Documentos Financeiros

```python
# Tickers de ações brasileiras
TICKER_BR = r"\b([A-Z]{4}\d{1,2})\b"  # PETR4, VALE3, BBDC4

# Códigos de fundos
FUND_CODE = r"\b(\d{6})\b"  # Código ANBIMA de 6 dígitos

# Datas brasileiras
DATE_BR = r"\b(\d{1,2}[/.-]\d{1,2}[/.-]\d{2,4})\b"

# Valores monetários (com variações)
MONEY_FULL = r"R\$\s*([\d.,]+(?:\s*(?:mil|milhão|milhões|bi|bilhão|bilhões))?)"

# Quantidades com unidades
QTY_UNITS = r"(\d+[\d.,]*)\s*(unidades?|cotas?|ações?|títulos?)"

# Séries de títulos
SERIES = r"[Ss]érie\s*[:\s]*([A-Z0-9]+)"

# Emissões
EMISSION = r"(\d+)[ªº]?\s*[Ee]missão"
```

---

## 6. Melhorias no Dicionário de Termos

Os dicionários de termos ajudam a identificar entidades no texto.

### 6.1 Localização

Edite `config.yaml`, seções `legal_terms` e `meeting_terms`.

### 6.2 Adicionar Novos Termos

**Exemplo:** Adicionar novos tipos de ativos

```yaml
meeting_terms:
  asset_keywords:
    # Termos existentes
    - "ações"
    - "CRA"
    - "CRI"
    
    # Novos termos adicionados
    - "BDR"           # Brazilian Depositary Receipts
    - "units"         # Units de ações
    - "bônus"         # Bônus de subscrição
    - "warrants"      # Warrants
    - "FIDC"          # Fundo de Direitos Creditórios
    - "FIP"           # Fundo de Investimento em Participações
    - "FIAGRO"        # Fundo de Investimento Agro
    - "letra financeira"
    - "COE"           # Certificado de Operações Estruturadas
```

### 6.3 Adicionar Variações e Sinônimos

```yaml
legal_terms:
  heir_keywords:
    # Termo principal
    - "herdeiro"
    - "herdeira"
    
    # Variações
    - "herdeiros"
    - "herdeiras"
    
    # Sinônimos
    - "sucessor"
    - "sucessora"
    - "beneficiário"
    - "beneficiária"
    
    # Termos específicos
    - "legatário"      # Quem recebe legado específico
    - "meeiro"         # Cônjuge com direito à meação
    - "preterido"      # Herdeiro não incluído
```

### 6.4 Organizar por Categorias

```yaml
meeting_terms:
  # Renda Variável
  equity_keywords:
    - "ações"
    - "units"
    - "BDR"
    - "ETF"
    
  # Renda Fixa
  fixed_income_keywords:
    - "CDB"
    - "LCI"
    - "LCA"
    - "debênture"
    - "CRA"
    - "CRI"
    
  # Fundos
  fund_keywords:
    - "FII"
    - "FIM"
    - "FIC"
    - "FIDC"
    - "FIP"
```

---

## Checklist de Otimização

Use este checklist para otimizar sistematicamente:

### OCR
- [ ] DPI adequado ao tipo de documento (300-400 para escaneados)
- [ ] PSM correto para estrutura do documento
- [ ] Idioma(s) configurado(s) corretamente
- [ ] Pré-processamento de imagem se necessário

### Chunking
- [ ] chunk_size adequado ao tipo de conteúdo
- [ ] chunk_overlap suficiente para não cortar contexto
- [ ] Estratégia de chunking apropriada (recursive para maioria)
- [ ] min_chunk_size não descartando informação importante

### Retrieval
- [ ] top_k suficiente para encontrar todas as informações
- [ ] min_score não muito restritivo
- [ ] Busca híbrida habilitada
- [ ] MMR habilitado para diversidade
- [ ] Re-ranking habilitado

### Instruções
- [ ] Queries específicas e descritivas
- [ ] Cobertura de todos os tipos de informação necessários
- [ ] Uso de sinônimos quando apropriado
- [ ] Queries separadas para diferentes categorias

### Padrões de Extração
- [ ] Regex cobrindo todas as variações de formato
- [ ] Padrões testados com dados reais
- [ ] Tratamento de casos especiais

### Dicionário de Termos
- [ ] Todos os tipos de ativos relevantes incluídos
- [ ] Variações e sinônimos cobertos
- [ ] Termos específicos do domínio adicionados

---

## Exemplo Prático de Otimização

### Cenário: Melhorar extração de CRAs/CRIs

**Problema:** O sistema não está extraindo todos os CRAs mencionados.

**Diagnóstico:**
1. Verificar texto do OCR → OK
2. Verificar se chunks contêm a informação → Chunks cortando descrição do CRA
3. Verificar queries → Query muito genérica

**Solução:**

1. **Ajustar chunking:**
   ```yaml
   rag:
     chunking:
       chunk_size: 500
       chunk_overlap: 150
   ```

2. **Melhorar queries em `meeting_minutes_analysis.txt`:**
   ```text
   # Antes (genérico)
   Quais CRAs são mencionados?
   
   # Depois (específico)
   Liste todos os CRAs (Certificados de Recebíveis do Agronegócio) mencionados, incluindo:
   - Nome do emissor/emissora
   - Número da série
   - Valor nominal
   - Quantidade
   ```

3. **Adicionar padrões no código:**
   ```python
   CRA_PATTERN = r"CRA[s]?\s+(?:da\s+)?([A-Za-zÀ-ú\s]+?)(?:\s+[Ss]érie\s+([A-Z0-9]+))?"
   ```

4. **Adicionar termos ao dicionário:**
   ```yaml
   meeting_terms:
     asset_keywords:
       - "CRA"
       - "Certificado de Recebíveis do Agronegócio"
       - "certificados de recebíveis"
   ```

**Resultado:** Extração completa de CRAs com emissor, série e valores.

---

## Suporte

Em caso de dúvidas ou problemas:
1. Verifique os logs em modo DEBUG
2. Analise o arquivo de texto extraído pelo OCR
3. Teste queries manualmente
4. Valide padrões regex com dados reais

