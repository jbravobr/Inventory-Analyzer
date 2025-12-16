# Modelos de Linguagem Offline

Este documento explica como configurar e utilizar diferentes modelos de linguagem no Document Analyzer.

---

## Status Atual do Repositorio

| Componente | Status | Acao Necessaria |
|------------|--------|-----------------|
| GPT-2 Portuguese | JA INCLUSO | Nenhuma |
| TinyLlama GGUF | JA INCLUSO | Nenhuma (modelo de ~670 MB incluso) |
| llama-cpp-python | **REQUER INSTALACAO** | Executar script de instalacao |

**O modelo TinyLlama ja esta no repositorio!**
**Para usa-lo, basta instalar o llama-cpp-python.**

---

## Ativar TinyLlama (Recomendado)

O modelo TinyLlama ja esta baixado. Para ativa-lo, execute:

**PowerShell:**
```powershell
.\scripts\install_llama_cpp.ps1
```

**Prompt de Comando (CMD):**
```cmd
scripts\install_llama_cpp.cmd
```

**Ou manualmente:**
```bash
pip install llama-cpp-python
```

**Nota:** Requer compilador C++ (Visual Studio Build Tools).
Se a instalacao falhar, o sistema usa GPT-2 Portuguese automaticamente.

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

**Com internet:**
```bash
pip install llama-cpp-python
```

**Offline (baixar wheel primeiro):**
1. Acesse: https://github.com/abetlen/llama-cpp-python/releases
2. Baixe wheel para Windows: `llama_cpp_python-*-cp311-cp311-win_amd64.whl`
3. Coloque em `wheels/`
4. Instale: `pip install wheels/llama_cpp_python-*.whl`

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

### Instalacao Offline

Se voce esta em ambiente corporativo sem internet:

1. Baixe o wheel apropriado de: https://github.com/abetlen/llama-cpp-python/releases
2. Coloque na pasta `wheels/`
3. Execute:
   ```bash
   pip install wheels/llama_cpp_python-*.whl
   ```

---

## Configuracao

### Via config.yaml

```yaml
rag:
  generation:
    default_model: "tinyllama"  # Modelo padrao
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
| Desktop comum | TinyLlama | Equilibrio |
| Laptop basico | GPT-2 Portuguese | Menor consumo |
| Servidor | Phi-3 Mini ou Mistral | Melhor qualidade |
| Respostas rapidas | TinyLlama | Velocidade |
| Analises detalhadas | Phi-3 Mini | Qualidade |

---

## Estrutura de Pastas

```
models/
├── embeddings/
│   └── models--neuralmind--bert-base-portuguese-cased/
│       └── ...
└── generator/
    ├── tinyllama-1.1b-chat-v1.0.Q4_K_M.gguf     # GGUF
    ├── Phi-3-mini-4k-instruct-q4.gguf            # GGUF
    ├── mistral-7b-instruct-v0.2.Q4_K_M.gguf     # GGUF
    └── models--pierreguillou--gpt2-small-portuguese/
        └── ...                                    # HuggingFace
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
| TinyLlama 1.1B | `tinyllama-1.1b-chat-v1.0.Q4_K_M.gguf` | 670 MB | 2 GB | 2048 | 5-15s |
| Phi-3 Mini | `Phi-3-mini-4k-instruct-q4.gguf` | 2.3 GB | 6 GB | 4096 | 15-30s |
| Mistral 7B | `mistral-7b-instruct-v0.2.Q4_K_M.gguf` | 4.1 GB | 8 GB | 4096 | 30-60s |
| GPT-2 Port. | (ja incluso) | 500 MB | 2 GB | 1024 | 3-8s |

### Qualidade de Respostas

| Modelo | Portugues | Contexto Longo | Instrucoes Complexas | Recomendado Para |
|--------|-----------|----------------|---------------------|------------------|
| TinyLlama | Bom | Limitado | Basico | Uso geral |
| Phi-3 Mini | Muito Bom | Bom | Excelente | Analises detalhadas |
| Mistral 7B | Excelente | Excelente | Excelente | Maxima qualidade |
| GPT-2 Port. | Basico | Muito Limitado | Basico | Fallback |

---

## Configuracao de Contexto (max_context_chars)

O parametro `max_context_chars` controla a quantidade maxima de caracteres do documento que e enviada ao modelo. Este e um dos parametros mais importantes para a qualidade das respostas.

### Valores Recomendados

| Modelo | max_context_chars | Justificativa |
|--------|-------------------|---------------|
| TinyLlama | 1000-1200 | ⭐ **Otimizado** - Janela de 2048 tokens. Configurado para ~1000 tokens de contexto efetivo (~1200 chars PT-BR). |
| Phi-3 Mini | 2000-3000 | Janela de 4096 tokens permite mais contexto. Melhor compreensao de documentos longos. |
| Mistral 7B | 2500-3500 | Janela grande e modelo robusto. Consegue processar contextos maiores com qualidade. |
| GPT-2 Portuguese | 400-600 | Modelo muito limitado. Contextos maiores degradam a qualidade. |

### Como Ajustar

Edite o arquivo `config.yaml`:

```yaml
rag:
  generation:
    models:
      tinyllama:
        max_context_chars: 1000    # Aumente para mais contexto
        # ...
      phi3-mini:
        max_context_chars: 2500    # Phi-3 aguenta mais
        # ...
```

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

Se as respostas estao imprecisas, experimente:

1. **Aumentar max_context_chars** em 200-500 caracteres
2. **Testar com a mesma pergunta** para comparar
3. **Observar logs** para ver se contexto esta sendo truncado

```bash
# Ver logs detalhados
python run.py qa doc.pdf -q "pergunta" --model tinyllama 2>&1 | grep -i "truncado"
```

---

## Script de Download de Modelos

Crie o arquivo `scripts/download_models.ps1`:

```powershell
# Download de modelos adicionais
# Execute: .\scripts\download_models.ps1

param(
    [string]$Model = "all"
)

$modelsDir = "models\generator"

# Phi-3 Mini
if ($Model -eq "all" -or $Model -eq "phi3") {
    Write-Host "Baixando Phi-3 Mini (~2.3 GB)..." -ForegroundColor Cyan
    $phi3Url = "https://huggingface.co/microsoft/Phi-3-mini-4k-instruct-gguf/resolve/main/Phi-3-mini-4k-instruct-q4.gguf"
    Invoke-WebRequest -Uri $phi3Url -OutFile "$modelsDir\Phi-3-mini-4k-instruct-q4.gguf"
    Write-Host "Phi-3 Mini baixado!" -ForegroundColor Green
}

# Mistral 7B
if ($Model -eq "all" -or $Model -eq "mistral") {
    Write-Host "Baixando Mistral 7B (~4.1 GB)..." -ForegroundColor Cyan
    $mistralUrl = "https://huggingface.co/TheBloke/Mistral-7B-Instruct-v0.2-GGUF/resolve/main/mistral-7b-instruct-v0.2.Q4_K_M.gguf"
    Invoke-WebRequest -Uri $mistralUrl -OutFile "$modelsDir\mistral-7b-instruct-v0.2.Q4_K_M.gguf"
    Write-Host "Mistral 7B baixado!" -ForegroundColor Green
}

Write-Host "`nVerifique os modelos com: python run.py models --check" -ForegroundColor Yellow
```

**Uso:**
```powershell
# Baixar todos
.\scripts\download_models.ps1

# Apenas Phi-3
.\scripts\download_models.ps1 -Model phi3

# Apenas Mistral
.\scripts\download_models.ps1 -Model mistral
```

---

## Proximos Passos

Para melhorar ainda mais a qualidade offline:

1. **Fine-tuning**: Treinar modelo com documentos especificos
2. **RAG avancado**: Melhorar o retrieval para contexto mais relevante
3. **Cache**: Respostas frequentes sao cacheadas automaticamente

