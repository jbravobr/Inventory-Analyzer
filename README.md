# Document Analyzer 📄

Analisador de documentos PDF para ambientes corporativos, com suporte a **múltiplos perfis de análise** e **múltiplos modos de operação**.

## 🌐 Modos de Operação

O sistema suporta três modos de operação, configuráveis via `config.yaml` ou flags CLI:

| Modo | Descrição | Quando Usar |
|------|-----------|-------------|
| `offline` | 100% local, sem conexão à internet | **PADRÃO** - Ambientes corporativos restritos |
| `online` | Permite downloads do HuggingFace e APIs cloud | Desenvolvimento, atualizações |
| `hybrid` | Tenta online, usa cache local se falhar | Conectividade intermitente |

**Configuração permanente** (`config.yaml`):
```yaml
system:
  mode: "offline"  # ou "online" ou "hybrid"
```

**Override temporário** (CLI):
```bash
python run.py --offline analyze documento.pdf   # Força offline
python run.py --online analyze documento.pdf    # Força online  
python run.py --hybrid analyze documento.pdf    # Força híbrido
```

> 📖 Para detalhes completos, veja [docs/MODOS_OPERACAO.md](docs/MODOS_OPERACAO.md)

## 🎯 Perfis de Análise Disponíveis

### 📜 Perfil: `inventory` - Escritura de Inventário

Analisa escrituras públicas de inventário e extrai:

| Cláusula | Informação Extraída | Cor no PDF |
|----------|---------------------|------------|
| **A** | Herdeiros (nome, CPF, parentesco) | 🟡 Amarelo |
| **B** | Inventariante nomeado | 🟢 Verde |
| **C** | Bens com menção a BTG | 🔵 Azul |
| **D** | Divisão dos bens BTG entre herdeiros | 🩷 Rosa |

### 📋 Perfil: `meeting_minutes` - Ata de Reunião de Quotistas

Analisa atas de reunião e assembleias para extrair:

| Cláusula | Informação Extraída | Cor no PDF |
|----------|---------------------|------------|
| **A** | Ativos (ações, CRA, CRI, debêntures, cotas, CDB, etc.) | 🟠 Laranja |
| **B** | Quantidades e valores dos ativos | 🔵 Azul |
| - | Informações do fundo | 🟢 Verde |
| - | Deliberações | 🩷 Rosa |

## 📤 Saídas Geradas

1. **Relatório TXT** - Arquivo de texto com todas as informações extraídas
2. **PDF Destacado** - Documento original com marcações coloridas (marca-texto)
3. **JSON** (opcional) - Dados estruturados para integração

## 📋 Pré-requisitos

| Software | Versão | Notas |
|----------|--------|-------|
| Python | 3.14+ | Já instalado pela TI |
| Tesseract OCR | 5.x | Já instalado pela TI |
| PowerShell | 5.1+ | Nativo do Windows |
| (Opcional) Git + Git LFS | Última | Apenas para quem for clonar o repositório completo |

## 🚀 Instalação

### Opção A – Instalação via pacote ZIP de Assets (recomendada para uso offline)

Esta é a forma mais simples para o usuário final, sem necessidade de Git ou Git LFS.

1. Acesse a página de **Releases** do projeto no GitHub.
2. Baixe o arquivo ZIP de assets, por exemplo:  
   `inventory_analyzer_offline_assets.zip`.
3. Extraia o conteúdo do ZIP para uma pasta, por exemplo:  
   `C:\inventory_analyzer_offline`.
4. Abra o **PowerShell** ou **Prompt de Comando** nesta pasta.
5. Execute o instalador offline:
   - PowerShell (se scripts estiverem liberados):
     ```powershell
     .\install_offline.ps1
     ```
   - Prompt de Comando (alternativa em ambientes com restrição a scripts PowerShell):
     ```bat
     install_offline.cmd
     ```
6. Após a instalação, ative o ambiente virtual:
   - PowerShell:
     ```powershell
     .\activate_env.ps1
     ```
   - Prompt de Comando:
     ```bat
     call venv\Scripts\activate.bat
     ```

Depois disso, utilize os comandos descritos na seção **📖 Uso** para rodar as análises.

### Opção B – Clonar o repositório via Git + Git LFS (para times de desenvolvimento)

1. Instale **Git** e **Git LFS** e execute:
   ```bash
   git lfs install
   ```
2. Clone o repositório:
   ```bash
   git clone https://github.com/jbravobr/Inventory-Analyzer.git
   cd Inventory-Analyzer
   git lfs pull   # normalmente automático, por garantia
   ```
3. Execute o instalador offline:
   ```powershell
   .\install_offline.ps1
   # ou
   install_offline.cmd
   ```
4. Ative o ambiente virtual:
   ```powershell
   .\activate_env.ps1
   ```
   ou
   ```bat
   call venv\Scripts\activate.bat
   ```

## 📖 Uso

### Análise de Escritura de Inventário (perfil padrão)

```powershell
python run.py analyze escritura_inventario.pdf
```

### Análise de Ata de Reunião de Quotistas

```powershell
python run.py analyze ata_reuniao.pdf --profile meeting_minutes
```

ou usando a forma curta:

```powershell
python run.py analyze ata_reuniao.pdf -p meeting_minutes
```

### Com diretório de saída específico

```powershell
python run.py analyze documento.pdf -o C:\Resultados
```

### Gerar também JSON

```powershell
python run.py analyze documento.pdf --json
```

### Forçar modo online (para baixar modelos atualizados)

```powershell
python run.py --online --allow-download analyze documento.pdf
```

### Usar modo híbrido (online com fallback offline)

```powershell
python run.py --hybrid analyze documento.pdf
```

### Apenas extrair texto (sem análise)

```powershell
python run.py extract documento.pdf
```

### Listar perfis disponíveis

```powershell
python run.py profiles
```

### Ver configurações

```powershell
python run.py info
```

### Mudar perfil padrão

Edite o arquivo `config.yaml` e altere:

```yaml
analysis:
  active_profile: "meeting_minutes"  # ou "inventory"
```

## 📁 Estrutura de Saída

Após a análise, serão gerados na pasta `output/`:

```
output/
├── escritura_inventario_relatorio_20241208_143000.txt   # Relatório TXT
├── escritura_inventario_destacado_20241208_143000.pdf   # PDF com highlights
└── escritura_inventario_resultado_20241208_143000.json  # JSON (se --json)
```

## 📝 Exemplo de Relatório TXT

```
================================================================================
                        RELATÓRIO DE ANÁLISE DE INVENTÁRIO
================================================================================

Data de Geração: 08/12/2024 14:30:00
Documento Analisado: escritura_inventario.pdf

--------------------------------------------------------------------------------
INFORMAÇÕES GERAIS
--------------------------------------------------------------------------------
Falecido (Autor da Herança): JOÃO DA SILVA
Data do Óbito: 15/03/2023
Cartório: 5º Tabelionato de Notas de São Paulo

================================================================================
CLÁUSULA A - HERDEIROS IDENTIFICADOS
================================================================================

Total de herdeiros encontrados: 3
Páginas de referência: [2, 3]
Nível de confiança: 70%

  1. MARIA DA SILVA SANTOS
     CPF: 123.456.789-00
     Parentesco: cônjuge

  2. PEDRO DA SILVA
     CPF: 234.567.890-11
     Parentesco: filho(a)

  3. ANA DA SILVA
     CPF: 345.678.901-22
     Parentesco: filho(a)

================================================================================
CLÁUSULA B - INVENTARIANTE NOMEADO
================================================================================

Nome: MARIA DA SILVA SANTOS
CPF: 123.456.789-00
É também herdeiro: SIM
Páginas de referência: [2]

================================================================================
CLÁUSULA C - BENS COM MENÇÃO A BTG
================================================================================

Total de bens BTG encontrados: 2

  BEM 1:
  ----------------------------------------
    Tipo: CDB
    Conta/Identificador: 12345-6
    Valor: R$ 150.000,00

  BEM 2:
  ----------------------------------------
    Tipo: Fundo de Investimento
    Valor: R$ 250.000,00

  VALOR TOTAL DOS BENS BTG: R$ 400.000,00

================================================================================
CLÁUSULA D - DIVISÃO DOS BENS BTG ENTRE HERDEIROS
================================================================================

  BEM: CDB - Conta 12345-6
  
  DIVISÃO:
    - MARIA DA SILVA SANTOS: 50.0% (R$ 75.000,00)
    - PEDRO DA SILVA: 25.0% (R$ 37.500,00)
    - ANA DA SILVA: 25.0% (R$ 37.500,00)
```

## 🎨 Legenda do PDF Destacado

O PDF gerado inclui uma página inicial com legenda e resumo, seguida do documento original com destaques.

### Perfil `inventory` (Inventário)

- **🟡 Amarelo**: Nomes dos herdeiros
- **🟢 Verde**: Nome do inventariante
- **🔵 Azul**: Menções a "BTG" e números de conta
- **🩷 Rosa**: Percentuais de divisão

### Perfil `meeting_minutes` (Ata de Reunião)

- **🟠 Laranja**: Ativos identificados (CRA, CRI, debêntures, ações, cotas, etc.)
- **🔵 Azul**: Quantidades e valores monetários (R$)
- **🟢 Verde**: Informações do fundo (nome, CNPJ)
- **🩷 Rosa**: Deliberações

## ⚙️ Configuração

Edite `config.yaml` para ajustes:

```yaml
# Aumentar qualidade do OCR
ocr:
  dpi: 400    # Padrão: 300

# Ajustar sensibilidade da busca
rag:
  retrieval:
    top_k: 15        # Mais contexto
    min_score: 0.15  # Menos restritivo
```

---

## 📚 Referência Completa do config.yaml

Esta seção detalha **todas as configurações disponíveis** no arquivo `config.yaml`.

### 🏷️ Seção `app` - Configurações Gerais

```yaml
app:
  name: "Document Analyzer (Offline)"   # Nome da aplicação (exibido no banner)
  version: "1.1.0-offline"              # Versão do software
  language: "pt-BR"                     # Idioma da interface
  log_level: "INFO"                     # Nível de log: DEBUG, INFO, WARNING, ERROR
```

| Propriedade | Tipo | Padrão | Descrição |
|-------------|------|--------|-----------|
| `name` | string | "Document Analyzer" | Nome exibido no banner de inicialização |
| `version` | string | "1.1.0-offline" | Versão do software |
| `language` | string | "pt-BR" | Idioma (afeta formatação de datas/números) |
| `log_level` | string | "INFO" | Verbosidade dos logs: `DEBUG` (mais detalhado) → `ERROR` (apenas erros) |

---

### 📋 Seção `analysis` - Perfis de Análise

```yaml
analysis:
  active_profile: "inventory"           # Perfil padrão quando não especificado via CLI
  instructions_dir: "./instructions"    # Diretório com arquivos de instruções
  
  profiles:
    inventory:
      name: "Análise de Inventário"
      description: "Extrai herdeiros, inventariante, bens BTG e divisão patrimonial"
      instructions_file: "inventory_analysis.txt"
      analyzer_class: "InventoryAnalyzer"
      
    meeting_minutes:
      name: "Ata de Reunião de Quotistas"
      description: "Extrai ativos envolvidos e suas quantidades"
      instructions_file: "meeting_minutes_analysis.txt"
      analyzer_class: "MeetingMinutesAnalyzer"
```

| Propriedade | Tipo | Padrão | Descrição |
|-------------|------|--------|-----------|
| `active_profile` | string | "inventory" | Perfil usado quando `-p` não é especificado |
| `instructions_dir` | string | "./instructions" | Pasta com arquivos `.txt` de instruções |
| `profiles.*.name` | string | - | Nome amigável do perfil |
| `profiles.*.description` | string | - | Descrição do que o perfil extrai |
| `profiles.*.instructions_file` | string | - | Arquivo de instruções (queries RAG) |
| `profiles.*.analyzer_class` | string | - | Classe Python que implementa a análise |

---

### 🔍 Seção `ocr` - Configurações do Tesseract OCR

```yaml
ocr:
  tesseract_path: "C:\\Program Files\\Tesseract-OCR\\tesseract.exe"
  language: "por"        # Código ISO do idioma
  dpi: 300               # Resolução de conversão PDF → imagem
  config: "--psm 3 --oem 3"
```

| Propriedade | Tipo | Padrão | Descrição |
|-------------|------|--------|-----------|
| `tesseract_path` | string | (caminho Windows) | Caminho completo para o executável do Tesseract |
| `language` | string | "por" | Idioma do OCR: `por` (português), `eng` (inglês), `por+eng` (ambos) |
| `dpi` | int | 300 | Resolução em DPI. **↑ Maior = melhor qualidade, mais lento** |
| `config` | string | "--psm 3 --oem 3" | Parâmetros do Tesseract (ver tabela abaixo) |

**Valores de PSM (Page Segmentation Mode):**
| Valor | Descrição |
|-------|-----------|
| `--psm 1` | Segmentação automática com OSD |
| `--psm 3` | Segmentação automática (padrão) |
| `--psm 6` | Bloco de texto uniforme |
| `--psm 11` | Texto esparso sem ordem |

**Valores de OEM (OCR Engine Mode):**
| Valor | Descrição |
|-------|-----------|
| `--oem 0` | Apenas motor legacy |
| `--oem 1` | Apenas LSTM (neural) |
| `--oem 3` | Ambos (padrão, mais preciso) |

---

### 🧠 Seção `nlp` - Processamento de Linguagem Natural

```yaml
nlp:
  mode: "local"                    # "local" (offline) ou "cloud" (API)
  
  local:
    spacy_model: "pt_core_news_lg"
    sentence_transformer: "./models/embeddings/..."
    similarity_threshold: 0.75
  
  cloud:
    enabled: false                 # Desabilita chamadas à nuvem
```

| Propriedade | Tipo | Padrão | Descrição |
|-------------|------|--------|-----------|
| `mode` | string | "local" | `local` = 100% offline, `cloud` = usa APIs externas |
| `local.spacy_model` | string | "pt_core_news_lg" | Modelo spaCy para NLP (tokenização, NER) |
| `local.sentence_transformer` | string | (caminho) | Modelo de embeddings local |
| `local.similarity_threshold` | float | 0.75 | Limiar de similaridade (0.0-1.0) |
| `cloud.enabled` | bool | false | Se `true`, permite chamadas a APIs externas |

---

### 🔗 Seção `rag` - Pipeline RAG (Retrieval-Augmented Generation)

Esta é a seção mais importante para tuning de performance e qualidade.

#### Chunking (Divisão do Documento)

```yaml
rag:
  enabled: true
  
  chunking:
    strategy: "recursive"    # Estratégia de divisão
    chunk_size: 400          # Tamanho máximo de cada chunk (caracteres)
    chunk_overlap: 100       # Sobreposição entre chunks
    min_chunk_size: 80       # Tamanho mínimo para um chunk válido
```

| Propriedade | Tipo | Padrão | Descrição |
|-------------|------|--------|-----------|
| `enabled` | bool | true | Habilita/desabilita o pipeline RAG |
| `chunking.strategy` | string | "recursive" | `fixed_size`, `sentence`, `paragraph`, `recursive` |
| `chunking.chunk_size` | int | 400 | **↓ Menor = mais preciso, mais chunks** |
| `chunking.chunk_overlap` | int | 100 | Caracteres compartilhados entre chunks adjacentes |
| `chunking.min_chunk_size` | int | 80 | Chunks menores são descartados |

**Estratégias de Chunking:**
```
┌─────────────────────────────────────────────────────────────────┐
│ fixed_size   : Divide em blocos de tamanho fixo                 │
│ sentence     : Divide por sentenças (pontuação)                 │
│ paragraph    : Divide por parágrafos (quebras de linha)         │
│ recursive    : Tenta dividir por parágrafos, depois sentenças,  │
│                depois tamanho fixo (RECOMENDADO)                │
└─────────────────────────────────────────────────────────────────┘
```

#### Embeddings (Vetorização)

```yaml
  embeddings:
    local_model: "./models/embeddings/..."   # Caminho do modelo BERT
    cache_enabled: true                      # Cache de embeddings calculados
    cache_path: "./cache/embeddings"         # Onde salvar o cache
```

| Propriedade | Tipo | Padrão | Descrição |
|-------------|------|--------|-----------|
| `local_model` | string | (caminho) | Modelo Sentence Transformer para embeddings |
| `cache_enabled` | bool | true | Reutiliza embeddings já calculados |
| `cache_path` | string | "./cache/embeddings" | Diretório do cache |

#### Vector Store (Armazenamento de Vetores)

```yaml
  vector_store:
    type: "faiss"            # Biblioteca de busca vetorial
    use_gpu: false           # Aceleração por GPU (requer CUDA)
    index_path: "./cache/index"
```

| Propriedade | Tipo | Padrão | Descrição |
|-------------|------|--------|-----------|
| `type` | string | "faiss" | `faiss` (Facebook AI) ou `simple` (em memória) |
| `use_gpu` | bool | false | `true` requer NVIDIA CUDA instalado |
| `index_path` | string | "./cache/index" | Onde salvar índices persistentes |

#### Retrieval (Recuperação de Contexto)

```yaml
  retrieval:
    top_k: 10                # Número de chunks a recuperar por query
    min_score: 0.2           # Score mínimo de similaridade
    use_reranking: true      # Re-ordenar resultados por relevância
    use_hybrid_search: true  # Combinar busca semântica + keywords
    use_mmr: true            # Maximal Marginal Relevance (diversidade)
    mmr_diversity: 0.3       # Peso da diversidade (0.0-1.0)
```

| Propriedade | Tipo | Padrão | Descrição |
|-------------|------|--------|-----------|
| `top_k` | int | 10 | **↑ Maior = mais contexto, mais lento** |
| `min_score` | float | 0.2 | Chunks com score menor são descartados (0.0-1.0) |
| `use_reranking` | bool | true | Segunda passada para ordenar por relevância |
| `use_hybrid_search` | bool | true | Combina busca vetorial + busca por palavras-chave |
| `use_mmr` | bool | true | Evita chunks muito similares entre si |
| `mmr_diversity` | float | 0.3 | 0.0 = só relevância, 1.0 = só diversidade |

#### Generation (Geração de Respostas)

```yaml
  generation:
    mode: "local"
    local_model: "./models/generator/..."
    generate_answers: false   # ⚠️ IMPORTANTE: true = usa LLM, false = só retrieval
    max_tokens: 500
    temperature: 0.1
```

| Propriedade | Tipo | Padrão | Descrição |
|-------------|------|--------|-----------|
| `mode` | string | "local" | `local` (GPT-2 offline) ou `cloud` (API) |
| `local_model` | string | (caminho) | Caminho do modelo de linguagem local |
| `generate_answers` | bool | **false** | `false` = **60% mais rápido**, mesmo resultado |
| `max_tokens` | int | 500 | Limite de tokens na resposta gerada |
| `temperature` | float | 0.1 | Criatividade: 0.0 = determinístico, 1.0 = criativo |

> ⚡ **Dica de Performance**: Manter `generate_answers: false` é recomendado para uso offline. Para usar extração LLM cloud, veja a seção "Extração LLM Cloud" abaixo.

---

### 🤖 Extração LLM Cloud (opcional)

Quando em **modo online**, você pode habilitar extração complementar via LLM cloud (GPT-4, Claude). O LLM **complementa** o regex, não substitui.

```yaml
rag:
  generation:
    generate_answers: true   # Habilita geração
    
    llm_extraction:
      enabled: true                        # Habilita extração LLM
      provider: "openai"                   # openai | anthropic
      merge_strategy: "regex_priority"     # Regex tem prioridade para números
      
    cloud_providers:
      openai:
        api_key_env: "OPENAI_API_KEY"
        generation_model: "gpt-4o-mini"
```

| Propriedade | Tipo | Padrão | Descrição |
|-------------|------|--------|-----------|
| `llm_extraction.enabled` | bool | **false** | Habilita extração via LLM cloud |
| `llm_extraction.provider` | string | "openai" | `openai` ou `anthropic` |
| `llm_extraction.merge_strategy` | string | "regex_priority" | Como mesclar resultados |
| `cloud_providers.*.api_key_env` | string | - | Variável de ambiente com API key |
| `cloud_providers.*.generation_model` | string | - | Modelo a usar |

---

### ✅ Seção `validation` - Validação de Texto

```yaml
validation:
  min_word_count: 10           # Mínimo de palavras para página válida
  min_sentence_coherence: 0.6  # Coerência mínima do texto
  check_encoding: true         # Verificar encoding UTF-8
  language_detection: true     # Detectar idioma automaticamente
```

| Propriedade | Tipo | Padrão | Descrição |
|-------------|------|--------|-----------|
| `min_word_count` | int | 10 | Páginas com menos palavras são ignoradas |
| `min_sentence_coherence` | float | 0.6 | Filtro de qualidade do OCR (0.0-1.0) |
| `check_encoding` | bool | true | Valida caracteres UTF-8 |
| `language_detection` | bool | true | Verifica se o texto está em português |

---

### 🔎 Seção `search` - Configurações de Busca

```yaml
search:
  use_semantic_search: true    # Busca por significado
  use_keyword_search: true     # Busca por palavras exatas
  combine_results: true        # Mesclar resultados dos dois métodos
  max_results: 50              # Limite de resultados
```

| Propriedade | Tipo | Padrão | Descrição |
|-------------|------|--------|-----------|
| `use_semantic_search` | bool | true | Busca por similaridade de significado |
| `use_keyword_search` | bool | true | Busca por correspondência exata de palavras |
| `combine_results` | bool | true | Une resultados de ambos os métodos |
| `max_results` | int | 50 | Limite total de resultados |

---

### 📤 Seção `output` - Configurações de Saída

```yaml
output:
  default_dir: "./output"
  highlight_colors:
    heirs: [255, 255, 0]           # RGB: Amarelo
    administrator: [0, 255, 0]     # RGB: Verde
    btg_assets: [0, 191, 255]      # RGB: Azul claro
    divisions: [255, 182, 193]     # RGB: Rosa
  output_format: "png"
```

| Propriedade | Tipo | Padrão | Descrição |
|-------------|------|--------|-----------|
| `default_dir` | string | "./output" | Pasta padrão para arquivos gerados |
| `highlight_colors.*` | [R,G,B] | (ver acima) | Cores RGB para cada tipo de destaque |
| `output_format` | string | "png" | Formato interno das imagens |

---

### 📖 Seções `legal_terms` e `meeting_terms` - Dicionários de Termos

Estas seções contêm listas de palavras-chave usadas para identificar entidades nos documentos. Você pode adicionar ou remover termos conforme necessário.

```yaml
legal_terms:
  heir_keywords:         # Palavras que indicam herdeiros
    - "herdeiro"
    - "cônjuge"
    - "filho"
    # ... adicione mais termos aqui

meeting_terms:
  asset_keywords:        # Palavras que indicam ativos financeiros
    - "CRA"
    - "CRI"
    - "debênture"
    # ... adicione mais termos aqui
```

---

## 🔄 Diagrama de Workflow do Algoritmo

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                        DOCUMENT ANALYZER - WORKFLOW                             │
└─────────────────────────────────────────────────────────────────────────────────┘

                              ┌─────────────┐
                              │  ENTRADA    │
                              │  PDF File   │
                              └──────┬──────┘
                                     │
                                     ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│  FASE 1: EXTRAÇÃO DE TEXTO (OCR)                                                │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                 │
│    ┌──────────┐      ┌──────────────┐      ┌──────────────┐                     │
│    │   PDF    │ ───► │   PyMuPDF    │ ───► │  Tesseract   │                     │
│    │          │      │   (fitz)     │      │    OCR       │                     │
│    └──────────┘      └──────────────┘      └──────┬───────┘                     │
│                                                    │                            │
│                                                    ▼                            │
│                                           ┌──────────────┐                      │
│                                           │ Texto Bruto  │                      │
│                                           │ (por página) │                      │
│                                           └──────────────┘                      │
└─────────────────────────────────────────────────────────────────────────────────┘
                                     │
                                     ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│  FASE 2: PIPELINE RAG - INDEXAÇÃO                                               │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                 │
│    ┌──────────┐      ┌──────────────┐      ┌──────────────┐                     │
│    │  Texto   │ ───► │   Chunker    │ ───► │  Embeddings  │                     │
│    │  Bruto   │      │  (divisão)   │      │   (BERT)     │                     │
│    └──────────┘      └──────────────┘      └──────┬───────┘                     │
│                              │                     │                            │
│                              │ 38 chunks           │ 38 vetores (768 dim)       │
│                              ▼                     ▼                            │
│                       ┌──────────────┐      ┌──────────────┐                    │
│                       │   Chunks     │      │    FAISS     │                    │
│                       │  (texto)     │      │  VectorStore │                    │
│                       └──────────────┘      └──────────────┘                    │
│                                                                                 │
└─────────────────────────────────────────────────────────────────────────────────┘
                                     │
                                     ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│  FASE 3: PIPELINE RAG - RETRIEVAL (para cada query)                             │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                 │
│    ┌───────────────────┐                                                        │
│    │ "Quais ações são  │                                                        │
│    │  mencionadas?"    │                                                        │
│    └─────────┬─────────┘                                                        │
│              │                                                                  │
│              ▼                                                                  │
│    ┌──────────────┐      ┌──────────────┐      ┌──────────────┐                 │
│    │  Embedding   │ ───► │    FAISS     │ ───► │   Top-K      │                 │
│    │  da Query    │      │   Search     │      │   Chunks     │                 │
│    └──────────────┘      └──────────────┘      └──────┬───────┘                 │
│                                                       │                         │
│                                    ┌──────────────────┼──────────────────┐      │
│                                    ▼                  ▼                  ▼      │
│                              ┌──────────┐      ┌──────────┐      ┌──────────┐   │
│                              │ Chunk 1  │      │ Chunk 2  │      │ Chunk N  │   │
│                              │ score:95%│      │ score:87%│      │ score:72%│   │
│                              └──────────┘      └──────────┘      └──────────┘   │
│                                                                                 │
└─────────────────────────────────────────────────────────────────────────────────┘
                                     │
                                     ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│  FASE 4: EXTRAÇÃO DE DADOS (Regex + LLM opcional)                               │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                 │
│    ┌──────────────┐                                                             │
│    │   Chunks     │                                                             │
│    │ Recuperados  │                                                             │
│    └──────┬───────┘                                                             │
│           │                                                                     │
│           ├────────────────────────────────────────────┐                        │
│           │ (SEMPRE)                                   │ (SE HABILITADO)        │
│           ▼                                            ▼                        │
│    ┌──────────────────────────────────────┐   ┌──────────────────┐              │
│    │          REGEX PATTERNS              │   │   LLM CLOUD      │              │
│    │                                      │   │  (complementa)   │              │
│    │  • CPF: \d{3}\.\d{3}\.\d{3}-\d{2}    │   │                  │              │
│    │  • Valores: R\$\s*[\d.,]+            │   │ • Valores extenso│              │
│    │  • Ativos: CRA|CRI|CDB|ações|...     │   │ • Contexto       │              │
│    │  • Percentuais: \d+[,.]?\d*\s*%      │   │ • Referências    │              │
│    └──────────────────┬───────────────────┘   └────────┬─────────┘              │
│                       │                                │                        │
│                       └───────────┬────────────────────┘                        │
│                                   │ MERGE (regex_priority)                      │
│                                   ▼                                             │
│                          ┌──────────────────┐                                   │
│                          │  Dados Extraídos │                                   │
│                          │  (estruturados)  │                                   │
│                          └──────────────────┘                                   │
│                                                                                 │
└─────────────────────────────────────────────────────────────────────────────────┘
                                     │
                                     ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│  FASE 5: GERAÇÃO DE SAÍDAS                                                      │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                 │
│    ┌──────────────────┐                                                         │
│    │  Dados Extraídos │                                                         │
│    └────────┬─────────┘                                                         │
│             │                                                                   │
│             ├─────────────────┬─────────────────┬─────────────────┐             │
│             ▼                 ▼                 ▼                 ▼             │
│    ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐       │
│    │  Relatório   │  │     PDF      │  │    JSON      │  │   Console    │       │
│    │    .TXT      │  │  Highlights  │  │  (opcional)  │  │   Summary    │       │
│    └──────────────┘  └──────────────┘  └──────────────┘  └──────────────┘       │
│                                                                                 │
└─────────────────────────────────────────────────────────────────────────────────┘
```

---

## 🧩 Processo RAG Detalhado

### O que é RAG?

**RAG (Retrieval-Augmented Generation)** é uma técnica que combina:
1. **Retrieval** (Recuperação): Buscar informações relevantes em uma base de conhecimento
2. **Generation** (Geração): Usar um modelo de linguagem para gerar respostas

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                          ARQUITETURA RAG                                        │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                 │
│     DOCUMENTO                    QUERY                     RESPOSTA             │
│         │                          │                          ▲                 │
│         ▼                          ▼                          │                 │
│    ┌─────────┐              ┌─────────────┐            ┌─────────────┐          │
│    │ INDEXAR │              │  RECUPERAR  │            │   EXTRAIR   │          │
│    │         │              │  (Retrieval)│───────────►│   (Regex)   │          │
│    └────┬────┘              └─────────────┘            └─────────────┘          │
│         │                          ▲                                            │
│         ▼                          │                                            │
│    ┌─────────────────────────────────────────┐                                  │
│    │           VECTOR STORE (FAISS)          │                                  │
│    │     [vetor1] [vetor2] [vetor3] ...      │                                  │
│    └─────────────────────────────────────────┘                                  │
│                                                                                 │
└─────────────────────────────────────────────────────────────────────────────────┘
```

### Implementação no Document Analyzer

#### Passo 1: Leitura e OCR (`PDFReader` + `OCRExtractor`)

```
Arquivo: src/core/pdf_reader.py, src/core/ocr_extractor.py

┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│  PDF File   │────►│   PyMuPDF   │────►│  Tesseract  │
│             │     │   (fitz)    │     │    OCR      │
└─────────────┘     └─────────────┘     └──────┬──────┘
                                               │
                         Para cada página:     │
                         - Converte para imagem (300 DPI)
                         - Aplica OCR           │
                         - Extrai texto         ▼
                                        ┌─────────────┐
                                        │  Document   │
                                        │  (6 pages)  │
                                        └─────────────┘
```

**Código relevante:**
```python
# PDFReader.read()
images = convert_from_path(pdf_path, dpi=300)
for img in images:
    text = pytesseract.image_to_string(img, lang='por')
```

---

#### Passo 2: Chunking (`TextChunker`)

```
Arquivo: src/rag/chunker.py

┌───────────────────────────────────────────────────────────────┐
│                     TEXTO DO DOCUMENTO                        │
│  "O herdeiro João da Silva, CPF 123.456.789-00, cônjuge       │
│   sobrevivente, ficou responsável por... [continua...]"       │
└───────────────────────────────────────────────────────────────┘
                              │
                              │ Estratégia: RECURSIVE
                              │ chunk_size: 400
                              │ overlap: 100
                              ▼
┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐
│   Chunk 1   │  │   Chunk 2   │  │   Chunk 3   │  │   Chunk N   │
│ (~400 char) │  │ (~400 char) │  │ (~400 char) │  │ (~400 char) │
│  page: 1    │  │  page: 1    │  │  page: 2    │  │  page: 6    │
└─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘
        │                │                │                │
        └────────────────┴────────────────┴────────────────┘
                              │
                        100 chars de overlap
                     (contexto compartilhado)
```

**Por que fazer chunking?**
- Modelos de embedding têm limite de tokens (~512)
- Chunks menores permitem recuperação mais precisa
- Overlap evita perder contexto nas bordas

---

#### Passo 3: Embeddings (`EmbeddingProvider`)

```
Arquivo: src/rag/embeddings.py

┌─────────────┐     ┌─────────────────────┐     ┌─────────────────┐
│   Chunk 1   │────►│   BERT Português    │────►│  Vetor [768]    │
│   (texto)   │     │   (neuralmind)      │     │  [0.23, -0.45,  │
└─────────────┘     └─────────────────────┘     │   0.12, ...]    │
                                                └─────────────────┘

Embedding = representação numérica do SIGNIFICADO do texto
- Textos similares → vetores próximos no espaço
- Textos diferentes → vetores distantes
```

**Modelo utilizado:** `neuralmind/bert-base-portuguese-cased`
- Treinado em português brasileiro
- 768 dimensões por vetor
- Executa 100% offline

---

#### Passo 4: Indexação (`VectorStore` - FAISS)

```
Arquivo: src/rag/vector_store.py

              ┌─────────────────────────────────────────┐
              │          FAISS INDEX                    │
              │                                         │
              │   Vetor 1 ──► Chunk 1 (page 1)          │
              │   Vetor 2 ──► Chunk 2 (page 1)          │
              │   Vetor 3 ──► Chunk 3 (page 2)          │
              │   ...                                   │
              │   Vetor 38 ──► Chunk 38 (page 6)        │
              │                                         │
              │   Indexação: IVF (Inverted File)        │
              │   Busca: Approximate Nearest Neighbors  │
              └─────────────────────────────────────────┘
```

**FAISS (Facebook AI Similarity Search):**
- Busca vetorial ultra-rápida
- Suporta milhões de vetores
- Funciona 100% offline

---

#### Passo 5: Retrieval (`Retriever`)

```
Arquivo: src/rag/retriever.py

┌───────────────────────────┐
│ Query: "Quais ações são   │
│ mencionadas no documento?"│
└─────────────┬─────────────┘
              │
              ▼
┌─────────────────────────────┐
│  1. Gera embedding da query │
│     [0.34, -0.22, 0.56...]  │
└─────────────┬───────────────┘
              │
              ▼
┌─────────────────────────────┐
│  2. Busca no FAISS          │
│     - Calcula distância     │
│     - Retorna top_k=10      │
└─────────────┬───────────────┘
              │
              ▼
┌─────────────────────────────┐
│  3. Re-ranking (opcional)   │
│     - Ordena por relevância │
│     - Aplica MMR            │
└─────────────┬───────────────┘
              │
              ▼
┌─────────────────────────────────────────────────────────┐
│  RESULTADO: 10 chunks mais relevantes                   │
│                                                         │
│  [Chunk 15] score: 0.94 - "...ações PETR4, VALE3..."    │
│  [Chunk 23] score: 0.87 - "...cotas do fundo XYZ..."    │
│  [Chunk 8]  score: 0.82 - "...CRI série 2023..."        │
│  ...                                                    │
└─────────────────────────────────────────────────────────┘
```

**Técnicas de Retrieval utilizadas:**

| Técnica | Descrição | Config |
|---------|-----------|--------|
| **Busca Vetorial** | Similaridade de cosseno entre embeddings | Sempre ativo |
| **Hybrid Search** | Combina vetorial + BM25 (keywords) | `use_hybrid_search: true` |
| **Re-ranking** | Segunda passada para refinar ordem | `use_reranking: true` |
| **MMR** | Maximal Marginal Relevance (diversidade) | `use_mmr: true` |

---

#### Passo 6: Extração de Dados (`MeetingMinutesAnalyzer` / `InventoryAnalyzer`)

```
Arquivo: src/inventory/meeting_minutes_analyzer.py

┌───────────────────────────────────────────────────────────────┐
│               CHUNKS RECUPERADOS                              │
│                                                               │
│  "...deliberou-se pela aquisição de 1.500 ações PETR4         │
│   ao preço de R$ 32,50 por ação, totalizando R$ 48.750,00     │
│   conforme aprovado unanimemente pelos quotistas..."          │
└───────────────────────────────────────────────────────────────┘
                              │
                              │ Aplicação de REGEX
                              ▼
┌───────────────────────────────────────────────────────────────┐
│  PADRÕES APLICADOS:                                           │
│                                                               │
│  • Ações: r"(\d+[\d.]*)\s*(ações?|cotas?)\s+(\w+)"            │
│    Match: "1.500 ações PETR4"                                 │
│                                                               │
│  • Valores: r"R\$\s*([\d.,]+)"                                │
│    Match: "R$ 32,50", "R$ 48.750,00"                          │
│                                                               │
│  • Ativos: r"\b(CRA|CRI|CDB|LCI|LCA|PETR4|VALE3)\b"           │
│    Match: "PETR4"                                             │
└───────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌───────────────────────────────────────────────────────────────┐
│  DADOS ESTRUTURADOS:                                          │
│                                                               │
│  {                                                            │
│    "assets": [                                                │
│      {"tipo": "ação", "ticker": "PETR4", "quantidade": 1500}  │
│    ],                                                         │
│    "valores": [32.50, 48750.00],                              │
│    "pages": [3, 4]                                            │
│  }                                                            │
└───────────────────────────────────────────────────────────────┘
```

---

#### Passo 7: Geração de Saídas

```
Arquivo: src/inventory/meeting_minutes_report.py
         src/inventory/meeting_minutes_highlighter.py

┌────────────────────┐
│  Dados Extraídos   │
└─────────┬──────────┘
          │
          ├────────────────────────────────────────────────────┐
          │                                                    │
          ▼                                                    ▼
┌─────────────────────────┐                    ┌─────────────────────────┐
│   RELATÓRIO TXT         │                    │   PDF COM HIGHLIGHTS    │
│                         │                    │                         │
│   ================      │                    │   ┌─────────────────┐   │
│   ATIVOS ENCONTRADOS    │                    │   │ Página 1        │   │
│   ================      │                    │   │                 │   │
│                         │                    │   │ texto com       │   │
│   1. PETR4              │                    │   │ ██████████      │   │
│      Tipo: ação         │                    │   │ destacado       │   │
│      Qtd: 1.500         │                    │   └─────────────────┘   │
│                         │                    │                         │
└─────────────────────────┘                    └─────────────────────────┘
```

---

### Fluxo de Dados Completo

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                                                                                 │
│   PDF ──► OCR ──► Texto ──► Chunks ──► Embeddings ──► FAISS Index               │
│                                                           │                     │
│                                                           │                     │
│   Query ──► Embedding ──► Busca FAISS ──► Top-K Chunks ──┘                      │
│                                                │                                │
│                                                ▼                                │
│                                    ┌──────────────────────┐                     │
│                                    │   Regex Extraction   │                     │
│                                    └──────────┬───────────┘                     │
│                                               │                                 │
│                                               ▼                                 │
│                                    ┌──────────────────────┐                     │
│                                    │   Dados Estruturados │                     │
│                                    └──────────┬───────────┘                     │
│                                               │                                 │
│                              ┌────────────────┼────────────────┐                │
│                              ▼                ▼                ▼                │
│                          [.TXT]           [.PDF]           [.JSON]              │
│                                                                                 │
└─────────────────────────────────────────────────────────────────────────────────┘
```

---

## 🔄 Fluxo com e sem Geração LLM

### Fluxo SEM Geração (padrão offline)

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                      FLUXO PADRÃO (generate_answers: false)                     │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                 │
│   PDF ──► OCR ──► Texto ──► Chunks ──► Embeddings ──► FAISS Index               │
│                                                           │                     │
│                                                           │                     │
│   Query ──► Embedding ──► Busca FAISS ──► Top-K Chunks ──┘                      │
│                                                │                                │
│                                                ▼                                │
│                                    ┌──────────────────────┐                     │
│                                    │   REGEX PATTERNS     │ ◄── 100% LOCAL      │
│                                    │   (SEMPRE EXECUTA)   │                     │
│                                    └──────────┬───────────┘                     │
│                                               │                                 │
│                                               ▼                                 │
│                                        ┌────────────┐                           │
│                                        │  SAÍDAS    │                           │
│                                        └────────────┘                           │
│                                                                                 │
│   ✅ Rápido (~60% mais rápido que com geração)                                  │
│   ✅ 100% offline                                                               │
│   ✅ Preciso para dados estruturados (valores, CPFs, CNPJs)                     │
│   ⚠️ Não captura valores por extenso ("trinta mil")                             │
│   ⚠️ Não entende referências contextuais ("conforme acima")                     │
│                                                                                 │
└─────────────────────────────────────────────────────────────────────────────────┘
```

### Fluxo COM Geração LLM Cloud (modo online)

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│              FLUXO COM LLM (generate_answers: true + modo online)               │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                 │
│   PDF ──► OCR ──► Texto ──► Chunks ──► Embeddings ──► FAISS Index               │
│                                                           │                     │
│                                                           │                     │
│   Query ──► Embedding ──► Busca FAISS ──► Top-K Chunks ──┘                      │
│                                                │                                │
│                         ┌──────────────────────┼──────────────────────┐         │
│                         │                      │                      │         │
│                         ▼                      ▼                      │         │
│            ┌──────────────────────┐   ┌──────────────────┐            │         │
│            │   REGEX PATTERNS     │   │   LLM CLOUD      │ ◄── API   │         │
│            │   (SEMPRE EXECUTA)   │   │   (COMPLEMENTA)  │    CALL   │         │
│            │                      │   │                  │            │         │
│            │ • Valores precisos   │   │ • "trinta mil"   │            │         │
│            │ • CPF/CNPJ           │   │   → 30.000       │            │         │
│            │ • Tickers            │   │ • "item anterior"│            │         │
│            └──────────┬───────────┘   │   → valor        │            │         │
│                       │               └────────┬─────────┘            │         │
│                       │                        │                      │         │
│                       └───────────┬────────────┘                      │         │
│                                   │                                   │         │
│                                   ▼                                   │         │
│                       ┌──────────────────────┐                        │         │
│                       │       MERGE          │                        │         │
│                       │  (regex_priority)    │                        │         │
│                       │                      │                        │         │
│                       │ • Regex: prioridade  │                        │         │
│                       │   para valores       │                        │         │
│                       │ • LLM: adiciona o    │                        │         │
│                       │   que regex não      │                        │         │
│                       │   capturou           │                        │         │
│                       └──────────┬───────────┘                        │         │
│                                  │                                    │         │
│                                  ▼                                    │         │
│                           ┌────────────┐                              │         │
│                           │  SAÍDAS    │                              │         │
│                           │ ENRIQUECIDAS│                             │         │
│                           └────────────┘                              │         │
│                                                                                 │
│   ✅ Captura valores por extenso e contextuais                                  │
│   ✅ Regex mantém precisão para dados estruturados                              │
│   ⚠️ Requer conexão internet + API key                                          │
│   ⚠️ Custo por documento (~R$ 0,10 - R$ 0,50)                                   │
│   ⚠️ Mais lento que offline                                                     │
│                                                                                 │
└─────────────────────────────────────────────────────────────────────────────────┘
```

---

## ⚖️ Comparativo: Regex vs LLM

| Tipo de Dado | Regex | LLM | Recomendação |
|--------------|-------|-----|--------------|
| `R$ 32,50` | ✅ 99% preciso | ✅ 95% | **Usar Regex** |
| `PETR4 = 1.500 ações` | ✅ 99% preciso | ✅ 90% | **Usar Regex** |
| `CPF: 123.456.789-00` | ✅ 100% preciso | ✅ 95% | **Usar Regex** |
| `trinta mil reais` | ❌ Não captura | ✅ Converte para 30.000 | **Usar LLM** |
| `valor aproximado de 1 milhão` | ❌ Parcial | ✅ Entende 1.000.000 | **Usar LLM** |
| `conforme item anterior` | ❌ Não entende | ✅ Infere contexto | **Usar LLM** |
| `mês passado` (data relativa) | ❌ Não converte | ✅ Calcula data | **Usar LLM** |
| Nome de pessoa em contexto | ⚠️ Parcial | ✅ Entende contexto | **Usar LLM** |

### Estratégia Recomendada

| Cenário | Modo | Geração | Por quê |
|---------|------|---------|---------|
| **Ambiente corporativo restrito** | `offline` | `false` | Sem internet, rápido, preciso para dados estruturados |
| **Máxima extração de dados** | `online` | `true` + LLM | LLM complementa regex para dados contextuais |
| **Desenvolvimento/testes** | `hybrid` | `false` | Flexível, usa cache local |
| **Documentos simples** | `offline` | `false` | Regex é suficiente, mais rápido |
| **Documentos complexos** | `online` | `true` + LLM | Valores por extenso, referências |

### CLI para cada cenário

```bash
# Cenário 1: Corporativo restrito (PADRÃO)
python run.py analyze documento.pdf

# Cenário 2: Máxima extração (requer API key configurada)
python run.py --online --use-cloud-generation analyze documento.pdf

# Cenário 3: Desenvolvimento
python run.py --hybrid analyze documento.pdf

# Cenário 4: Forçar offline mesmo com internet
python run.py --offline analyze documento.pdf
```

---

## 🔑 Configuração de API Keys (modo online)

Para usar extração via LLM cloud (OpenAI, Anthropic), você precisa configurar a API key do provedor.

### Método 1: Arquivo `.env` (Recomendado)

Crie um arquivo chamado `.env` na raiz do projeto (mesmo diretório do `run.py`):

```env
# .env - NÃO commite este arquivo!

# OpenAI - Para usar GPT-4o-mini
# Obtenha em: https://platform.openai.com/api-keys
OPENAI_API_KEY=sk-proj-abc123...

# Anthropic - Para usar Claude (opcional)
# Obtenha em: https://console.anthropic.com/
ANTHROPIC_API_KEY=sk-ant-xyz789...
```

**Como criar o arquivo `.env`:**

```powershell
# PowerShell - cria o arquivo
New-Item -Path ".env" -ItemType File
notepad .env   # Abre para editar
```

```cmd
# CMD - cria o arquivo
echo. > .env
notepad .env
```

O sistema carrega automaticamente o arquivo `.env` na inicialização.

> ⚠️ **Segurança**: O arquivo `.env` está no `.gitignore` e **nunca** deve ser commitado.

### Método 2: Variáveis de Ambiente

**PowerShell (temporário - só para a sessão):**
```powershell
$env:OPENAI_API_KEY = "sk-proj-abc123..."
python run.py --online --use-cloud-generation analyze documento.pdf
```

**CMD (temporário):**
```cmd
set OPENAI_API_KEY=sk-proj-abc123...
python run.py --online --use-cloud-generation analyze documento.pdf
```

**Windows (permanente):**
1. Painel de Controle → Sistema → Configurações avançadas do sistema
2. Variáveis de Ambiente
3. Nova variável de usuário: `OPENAI_API_KEY` = `sk-proj-...`

### Variáveis por Provedor

| Provedor | Variável de Ambiente | Onde obter |
|----------|---------------------|------------|
| OpenAI | `OPENAI_API_KEY` | [platform.openai.com/api-keys](https://platform.openai.com/api-keys) |
| Anthropic | `ANTHROPIC_API_KEY` | [console.anthropic.com](https://console.anthropic.com/) |

### Verificar se está configurado

```powershell
# PowerShell - deve retornar a key (ou parte dela)
$env:OPENAI_API_KEY

# Se retornar vazio, não está configurada
```

### Exemplo Completo de Uso

```powershell
# 1. Crie o arquivo .env (uma única vez)
# Conteúdo: OPENAI_API_KEY=sk-proj-...

# 2. Ative o ambiente
.\activate_env.ps1

# 3. Execute com LLM cloud
python run.py --online --use-cloud-generation analyze ata_reuniao.pdf -p meeting_minutes
```

> 💡 **Dica**: Com o arquivo `.env` configurado, você não precisa definir a variável toda vez - basta usar a flag `--use-cloud-generation`.

---

### Componentes e Arquivos

| Componente | Arquivo | Responsabilidade |
|------------|---------|------------------|
| **PDFReader** | `src/core/pdf_reader.py` | Conversão PDF → Imagens |
| **OCRExtractor** | `src/core/ocr_extractor.py` | Extração de texto via Tesseract |
| **TextChunker** | `src/rag/chunker.py` | Divisão do texto em chunks |
| **EmbeddingProvider** | `src/rag/embeddings.py` | Geração de vetores BERT |
| **VectorStore** | `src/rag/vector_store.py` | Indexação FAISS |
| **Retriever** | `src/rag/retriever.py` | Busca semântica |
| **LLMExtractor** | `src/rag/llm_extractor.py` | Extração complementar via LLM cloud |
| **RAGPipeline** | `src/rag/rag_pipeline.py` | Orquestração do pipeline |
| **InventoryAnalyzer** | `src/inventory/analyzer.py` | Extração para inventários |
| **MeetingMinutesAnalyzer** | `src/inventory/meeting_minutes_analyzer.py` | Extração para atas |
| **ReportGenerator** | `src/inventory/*_report.py` | Geração de relatórios |
| **PDFHighlighter** | `src/inventory/*_highlighter.py` | PDF com destaques |

---

## 🔧 Solução de Problemas

### Erro: "tesseract is not installed"

Verifique o caminho no `config.yaml` ou se o Tesseract está no PATH.

### Erro: "Unable to get page count"

O PyMuPDF deve estar instalado. Execute `.\activate_env.ps1` antes de usar.

### Erro: "Modelo não encontrado" em modo OFFLINE

Verifique se a pasta `./models/` contém os modelos necessários. Se precisar baixar, use temporariamente:
```bash
python run.py --online --allow-download analyze documento.pdf
```

### PDF com highlights em branco

O documento pode ser muito longo. Tente aumentar o `top_k` no config.

### Texto extraído ilegível

Aumente o `dpi` no config.yaml para melhor qualidade de OCR.

## 📊 Tamanho do Pacote

| Componente | Tamanho |
|------------|---------|
| Wheels (Python) | ~300 MB |
| Modelos ML | ~1.8 GB |
| **Total** | **~2.1 GB** |

> Nota: Poppler não é mais necessário - o PyMuPDF (wheel puro) substituiu a dependência.

## ⚠️ Limitações

1. **OCR**: Documentos escaneados com baixa qualidade podem ter erros
2. **Extração**: Baseada em padrões - pode não encontrar todos os casos
3. **Offline**: Sem atualizações automáticas de modelos

## 📄 Licença

MIT License

