# Modelos de Linguagem Offline

Este documento explica como configurar e utilizar diferentes modelos de linguagem no Document Analyzer.

---

## Comparativo de Modelos

| Modelo | Tamanho | RAM | Qualidade PT-BR | Recomendacao |
|--------|---------|-----|-----------------|--------------|
| **Llama 3.1 8B** | ~4.7 GB | ~8 GB | ⭐⭐⭐⭐⭐ Excelente | **MELHOR para Portugues** |
| Mistral 7B | ~4 GB | ~8 GB | ⭐⭐⭐⭐ Muito Boa | Alternativa de qualidade |
| TinyLlama 1.1B | ~670 MB | ~2 GB | ⭐⭐⭐ Boa | Recursos limitados |
| Phi-3 Mini | ~2.3 GB | ~6 GB | ⭐⭐ Limitada | Nao recomendado para PT-BR |
| GPT-2 Portuguese | ~500 MB | ~1 GB | ⭐ Basica | Fallback apenas |

---

## Status Atual do Repositorio

| Componente | Status | Acao Necessaria |
|------------|--------|-----------------|
| Llama 3.1 8B | **RECOMENDADO** | Download (~4.7 GB) - Melhor para portugues |
| Mistral 7B | Disponivel | Download (~4 GB) - Alternativa |
| TinyLlama GGUF | JA INCLUSO | Nenhuma (para recursos limitados) |
| GPT-2 Portuguese | JA INCLUSO | Nenhuma (fallback) |
| llama-cpp-python | **JA INCLUSO** | Nenhuma (wheel pre-compilado em `wheels/`) |

---

## Baixar Llama 3.1 8B (RECOMENDADO para Portugues)

O Llama 3.1 8B oferece a melhor qualidade para portugues brasileiro.

**PowerShell:**
```powershell
# Download automatico
.\scripts\download_models.ps1 -Model llama3
```

**Prompt de Comando (CMD):**
```batch
REM Download automatico
scripts\download_models.cmd llama3
```

**Download manual (PowerShell):**
```powershell
Invoke-WebRequest -Uri "https://huggingface.co/bartowski/Meta-Llama-3.1-8B-Instruct-GGUF/resolve/main/Meta-Llama-3.1-8B-Instruct-Q4_K_M.gguf" -OutFile "models\generator\Meta-Llama-3.1-8B-Instruct-Q4_K_M.gguf"
```

**Linux/Mac:**
```bash
wget -P models/generator/ "https://huggingface.co/bartowski/Meta-Llama-3.1-8B-Instruct-GGUF/resolve/main/Meta-Llama-3.1-8B-Instruct-Q4_K_M.gguf"
```

**Usar o modelo:**
```powershell
python run.py qa documento.pdf -q "sua pergunta" --model llama3-8b
```

---

## Ativar TinyLlama (Recursos Limitados)

O modelo TinyLlama ja esta baixado e o wheel `llama-cpp-python` **ja esta incluso** na pasta `wheels/`. A instalacao offline (`install_offline.cmd` ou `install_offline.ps1`) instala automaticamente.

Se precisar reinstalar manualmente:

**PowerShell:**
```powershell
.\scripts\install_llama_cpp.ps1
```

**Prompt de Comando (CMD):**
```cmd
scripts\install_llama_cpp.cmd
```

> **Nota:** O wheel pre-compilado ja esta incluso - **nao e necessario compilador C++**.

### Verificar Status

```powershell
python run.py models --check
```

---

## Visao Geral

O sistema suporta dois tipos de modelos:

| Tipo | Formato | Vantagens | Desvantagens |
|------|---------|-----------|--------------|
| **HuggingFace** | PyTorch (.bin) | Ja incluso | Menor qualidade |
| **GGUF** | Quantizado (.gguf) | Melhor qualidade | Requer download manual |

---

## Download Rapido (TinyLlama)

### Passo 1: Baixar o Modelo (~670 MB)

**Windows PowerShell:**
```powershell
cd D:\sources\RAG\inventory_analyzer_offline
Invoke-WebRequest -Uri "https://huggingface.co/TheBloke/TinyLlama-1.1B-Chat-v1.0-GGUF/resolve/main/tinyllama-1.1b-chat-v1.0.Q4_K_M.gguf" -OutFile "models\generator\tinyllama-1.1b-chat-v1.0.Q4_K_M.gguf"
```

**Linux/Mac:**
```bash
wget -P models/generator/ "https://huggingface.co/TheBloke/TinyLlama-1.1B-Chat-v1.0-GGUF/resolve/main/tinyllama-1.1b-chat-v1.0.Q4_K_M.gguf"
```

**Ou download manual:**
1. Acesse: https://huggingface.co/TheBloke/TinyLlama-1.1B-Chat-v1.0-GGUF/tree/main
2. Baixe: `tinyllama-1.1b-chat-v1.0.Q4_K_M.gguf`
3. Coloque em: `models/generator/`

### Passo 2: Instalar llama-cpp-python

O wheel **ja esta incluso** na pasta `wheels/` e e instalado automaticamente pelo `install_offline.cmd`.

Se precisar reinstalar:

**PowerShell:**
```powershell
.\scripts\install_llama_cpp.ps1
```

**CMD:**
```cmd
scripts\install_llama_cpp.cmd
```

### Passo 3: Verificar

```bash
python run.py models --check
```

---

## Modelos Disponiveis

### 1. TinyLlama-1.1B (RECOMENDADO)

**O modelo padrao para uso offline.**

| Caracteristica | Valor |
|----------------|-------|
| Tamanho | ~670 MB |
| RAM Necessaria | ~2 GB |
| Qualidade Q&A | Boa |
| Velocidade CPU | Rapido |

**Download:**
- HuggingFace: [TinyLlama-1.1B-Chat-GGUF](https://huggingface.co/TheBloke/TinyLlama-1.1B-Chat-v1.0-GGUF)
- Arquivo: `tinyllama-1.1b-chat-v1.0.Q4_K_M.gguf`

**Instalacao:**
```bash
# Baixe o arquivo e coloque em:
models/generator/tinyllama-1.1b-chat-v1.0.Q4_K_M.gguf
```

---

### 2. Phi-3 Mini (Alta Qualidade)

**Para quem precisa de respostas mais elaboradas.**

| Caracteristica | Valor |
|----------------|-------|
| Tamanho | ~2.3 GB |
| RAM Necessaria | ~6 GB |
| Qualidade Q&A | Excelente |
| Velocidade CPU | Media |
| Contexto | 4096 tokens |

**Download:**
- HuggingFace: [Phi-3-mini-4k-instruct-GGUF](https://huggingface.co/microsoft/Phi-3-mini-4k-instruct-gguf)
- Arquivo: `Phi-3-mini-4k-instruct-q4.gguf`

**Download Rapido (PowerShell):**
```powershell
# Baixar Phi-3 Mini (~2.3 GB)
Invoke-WebRequest -Uri "https://huggingface.co/microsoft/Phi-3-mini-4k-instruct-gguf/resolve/main/Phi-3-mini-4k-instruct-q4.gguf" -OutFile "models\generator\Phi-3-mini-4k-instruct-q4.gguf"
```

**Download Rapido (CMD com curl):**
```cmd
curl -L -o models\generator\Phi-3-mini-4k-instruct-q4.gguf "https://huggingface.co/microsoft/Phi-3-mini-4k-instruct-gguf/resolve/main/Phi-3-mini-4k-instruct-q4.gguf"
```

**Uso:**
```bash
python run.py qa documento.pdf -q "pergunta" --model phi3-mini
```

---

### 3. Mistral-7B (Melhor Qualidade)

**Para hardware mais potente.**

| Caracteristica | Valor |
|----------------|-------|
| Tamanho | ~4.1 GB |
| RAM Necessaria | ~8 GB |
| Qualidade Q&A | Excelente |
| Velocidade CPU | Lento |
| Contexto | 4096 tokens |

**Download:**
- HuggingFace: [Mistral-7B-Instruct-GGUF](https://huggingface.co/TheBloke/Mistral-7B-Instruct-v0.2-GGUF)
- Arquivo: `mistral-7b-instruct-v0.2.Q4_K_M.gguf`

**Download Rapido (PowerShell):**
```powershell
# Baixar Mistral 7B (~4.1 GB)
Invoke-WebRequest -Uri "https://huggingface.co/TheBloke/Mistral-7B-Instruct-v0.2-GGUF/resolve/main/mistral-7b-instruct-v0.2.Q4_K_M.gguf" -OutFile "models\generator\mistral-7b-instruct-v0.2.Q4_K_M.gguf"
```

**Download Rapido (CMD com curl):**
```cmd
curl -L -o models\generator\mistral-7b-instruct-v0.2.Q4_K_M.gguf "https://huggingface.co/TheBloke/Mistral-7B-Instruct-v0.2-GGUF/resolve/main/mistral-7b-instruct-v0.2.Q4_K_M.gguf"
```

**Uso:**
```bash
python run.py qa documento.pdf -q "pergunta" --model mistral-7b
```

---

### 4. GPT-2 Portuguese (Fallback)

**Modelo mais simples, sempre disponivel.**

| Caracteristica | Valor |
|----------------|-------|
| Tamanho | ~500 MB |
| RAM Necessaria | ~2 GB |
| Qualidade Q&A | Basica |
| Velocidade CPU | Rapido |

Este modelo ja vem pre-instalado no pacote.

---

## Instalacao do llama-cpp-python

Para usar modelos GGUF (TinyLlama, Phi-3, Mistral), voce precisa instalar o `llama-cpp-python`:

### Windows (Sem GPU)

```bash
pip install llama-cpp-python
```

### Windows (Com GPU NVIDIA)

```bash
# Requer CUDA instalado
pip install llama-cpp-python --extra-index-url https://abetlen.github.io/llama-cpp-python/whl/cu121
```

### Instalacao Offline (Ambiente Corporativo)

O wheel pré-compilado **já está incluso** no repositório:

```
wheels/llama_cpp_python-0.3.16-cp314-cp314-win_amd64.whl
```

A instalação offline (`install_offline.cmd`) automaticamente:
1. ✅ Instala o wheel pré-compilado (sem necessidade de compilador)
2. ✅ Habilita TinyLlama e Llama 3.1 8B
3. ✅ Funciona em ambientes sem Visual Studio Build Tools

**Não é necessário nenhum passo adicional!**

Se precisar de outra versão do Python, baixe o wheel apropriado de:
https://github.com/abetlen/llama-cpp-python/releases

---

## Configuracao

### Via config.yaml

```yaml
rag:
  generation:
    default_model: "llama3-8b"  # MELHOR para PT-BR (fallback automatico)
    # Ordem de fallback: llama3-8b -> mistral-7b -> tinyllama -> gpt2-portuguese
```

### Via CLI

```bash
# Usar modelo especifico
python run.py qa documento.pdf -q "pergunta" --model tinyllama

# Listar modelos
python run.py models --list

# Verificar modelos instalados
python run.py models --check
```

---

## Comparativo de Qualidade

### Pergunta de Teste
"Quais licencas sao de alta criticidade?"

**GPT-2 Portuguese:**
```
(Resposta vazia ou parcial)
```

**TinyLlama:**
```
As licencas de alta criticidade mencionadas no documento sao:
- GPL-3.0
- AGPL-3.0

Estas licencas exigem que codigo derivado seja disponibilizado
sob a mesma licenca, o que pode impactar software proprietario.
```

**Phi-3 Mini:**
```
Com base no documento analisado, as seguintes licencas sao 
classificadas como de ALTA criticidade:

1. GPL-3.0 (GNU General Public License v3.0)
   - Motivo: Obriga distribuicao do codigo-fonte
   
2. AGPL-3.0 (GNU Affero General Public License v3.0)
   - Motivo: Alem da GPL, inclui uso via rede

Recomendacao: Evitar uso direto em produtos comerciais sem 
consulta juridica.
```

---

## Recomendacoes por Caso de Uso

| Caso de Uso | Modelo Recomendado | Motivo |
|-------------|-------------------|--------|
| **Portugues (melhor qualidade)** | **Llama 3.1 8B** | Excelente suporte PT-BR |
| Servidor de producao | Llama 3.1 8B ou Mistral | Qualidade e confiabilidade |
| Desktop comum (~8 GB RAM) | Mistral 7B | Equilibrio qualidade/recursos |
| Laptop/PC limitado (~2 GB RAM) | TinyLlama | Menor consumo |
| Fallback garantido | GPT-2 Portuguese | Sempre funciona |
| Respostas rapidas | TinyLlama | Velocidade |
| Analises detalhadas em PT-BR | **Llama 3.1 8B** | Melhor compreensao |

---

## Estrutura de Pastas

```
models/
├── embeddings/
│   └── models--neuralmind--bert-base-portuguese-cased/
│       └── ...
└── generator/
    ├── Meta-Llama-3.1-8B-Instruct-Q4_K_M.gguf   # GGUF (RECOMENDADO)
    ├── mistral-7b-instruct-v0.2.Q4_K_M.gguf     # GGUF (alternativa)
    ├── tinyllama-1.1b-chat-v1.0.Q4_K_M.gguf     # GGUF (recursos limitados)
    ├── Phi-3-mini-4k-instruct-q4.gguf           # GGUF (nao recomendado)
    └── models--pierreguillou--gpt2-small-portuguese/
        └── ...                                   # HuggingFace (fallback)
```

---

## Solucao de Problemas

### "Modelo GGUF nao encontrado"

1. Verifique se o arquivo `.gguf` esta na pasta correta
2. Verifique o nome do arquivo no config.yaml
3. Execute `python run.py models --check`

### "llama-cpp-python nao instalado"

1. Instale: `pip install llama-cpp-python`
2. Ou baixe o wheel e instale offline

### "Memoria insuficiente"

1. Use um modelo menor (TinyLlama em vez de Mistral)
2. Feche outros programas
3. Use GPT-2 Portuguese como fallback

### "Resposta muito lenta"

1. Modelos GGUF sao otimizados para CPU, mas ainda assim levam tempo
2. TinyLlama: ~5-15 segundos por resposta
3. Mistral: ~30-60 segundos por resposta
4. Considere usar GPU se disponivel

---

## Comparativo de Hardware e Qualidade

### Requisitos de Hardware

| Modelo | Arquivo | Tamanho | RAM | Contexto | Tempo/Resposta |
|--------|---------|---------|-----|----------|----------------|
| **Llama 3.1 8B** | `Meta-Llama-3.1-8B-Instruct-Q4_K_M.gguf` | 4.7 GB | 8 GB | 8192 | 20-40s |
| Mistral 7B | `mistral-7b-instruct-v0.2.Q4_K_M.gguf` | 4.1 GB | 8 GB | 4096 | 30-60s |
| TinyLlama 1.1B | `tinyllama-1.1b-chat-v1.0.Q4_K_M.gguf` | 670 MB | 2 GB | 2048 | 5-15s |
| Phi-3 Mini | `Phi-3-mini-4k-instruct-q4.gguf` | 2.3 GB | 6 GB | 4096 | 15-30s |
| GPT-2 Port. | (ja incluso) | 500 MB | 2 GB | 1024 | 3-8s |

### Qualidade de Respostas

| Modelo | Portugues | Contexto Longo | Instrucoes Complexas | Recomendado Para |
|--------|-----------|----------------|---------------------|------------------|
| **Llama 3.1 8B** | ⭐⭐⭐⭐⭐ Excelente | ⭐⭐⭐⭐⭐ Excelente | ⭐⭐⭐⭐⭐ Excelente | **PT-BR, analises** |
| Mistral 7B | ⭐⭐⭐⭐ Muito Bom | ⭐⭐⭐⭐ Excelente | ⭐⭐⭐⭐ Excelente | Alternativa |
| TinyLlama | ⭐⭐⭐ Bom | ⭐⭐ Limitado | ⭐⭐ Basico | Recursos limitados |
| Phi-3 Mini | ⭐⭐ Limitado | ⭐⭐⭐ Bom | ⭐⭐⭐⭐ Bom | NAO recomendado PT-BR |
| GPT-2 Port. | ⭐ Basico | ⭐ Muito Limitado | ⭐ Basico | Fallback apenas |

---

## Configuracao de Contexto (max_context_chars)

O parametro `max_context_chars` controla a quantidade maxima de caracteres do documento que e enviada ao modelo. Este e um dos parametros mais importantes para a qualidade das respostas.

### Valores Recomendados

| Modelo | max_context_chars | max_tokens | Justificativa |
|--------|-------------------|------------|---------------|
| **Llama 3.1 8B** | 4000 | 1024 | ⭐ **MELHOR** - Janela enorme (8192 tokens), excelente para PT-BR |
| Mistral 7B | 3000 | 1024 | Janela grande e modelo robusto. Consegue processar contextos maiores com qualidade. |
| TinyLlama | 500 | 512 | **Balanceado** - Contexto conservador com respostas completas. Trade-off entre contexto e tamanho da resposta. |
| Phi-3 Mini | 2500 | 1024 | Janela de 4096 tokens permite mais contexto. NAO recomendado para PT-BR. |
| GPT-2 Portuguese | 500 | 500 | Modelo muito limitado. Contextos maiores degradam a qualidade. |

### Como Ajustar

Edite o arquivo `config.yaml`:

```yaml
rag:
  generation:
    models:
      llama3-8b:
        max_context_chars: 4000   # Janela grande (8192 tokens)
        max_tokens: 1024          # Respostas completas
        # ...
      tinyllama:
        max_context_chars: 500    # Contexto conservador
        max_tokens: 512           # Balanceado com contexto
        # ...
```

> **Nota**: O Llama 3.1 8B tem janela de 8192 tokens (ou até 128K em variantes), permitindo muito mais contexto que modelos menores.

### Impacto na Qualidade

**Contexto muito pequeno:**
- Respostas incompletas ou genericas
- Modelo nao tem informacao suficiente
- Pode "alucinar" informacoes

**Contexto muito grande:**
- Excede limite de tokens do modelo
- Respostas truncadas ou erros
- Performance degradada

### Dica: Ajuste Fino

Se as respostas estao imprecisas ou cortadas, experimente:

1. **Respostas cortadas?** Aumente `max_tokens` (ex: 384 → 512)
2. **Falta contexto?** Aumente `max_context_chars` (mas reduza `max_tokens`)
3. **Testar com a mesma pergunta** para comparar
4. **Observar logs** para ver se contexto esta sendo truncado
5. **Usar modelo maior** (Phi-3 ou Mistral) para perguntas complexas

```bash
# Ver logs detalhados
python run.py qa doc.pdf -q "pergunta" --model tinyllama 2>&1 | grep -i "truncado"
```

---

## Scripts de Download de Modelos

Os scripts de download estao disponiveis em `scripts/`:

### PowerShell

```powershell
# Baixar todos os modelos
.\scripts\download_models.ps1

# Apenas Llama 3.1 (RECOMENDADO)
.\scripts\download_models.ps1 -Model llama3

# Apenas TinyLlama
.\scripts\download_models.ps1 -Model tinyllama

# Apenas Phi-3 Mini
.\scripts\download_models.ps1 -Model phi3

# Apenas Mistral
.\scripts\download_models.ps1 -Model mistral
```

### Prompt de Comando (CMD)

```batch
REM Baixar todos os modelos
scripts\download_models.cmd all

REM Apenas Llama 3.1 (RECOMENDADO)
scripts\download_models.cmd llama3

REM Apenas TinyLlama
scripts\download_models.cmd tinyllama

REM Apenas Phi-3 Mini
scripts\download_models.cmd phi3

REM Apenas Mistral
scripts\download_models.cmd mistral
```

### Verificar Modelos

```bash
python run.py models --check
```

---

## Proximos Passos

Para melhorar ainda mais a qualidade offline:

1. **Fine-tuning**: Treinar modelo com documentos especificos
2. **RAG avancado**: Melhorar o retrieval para contexto mais relevante
3. **Cache**: Respostas frequentes sao cacheadas automaticamente

