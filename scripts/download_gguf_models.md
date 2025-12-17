# Download de Modelos GGUF para Uso Offline

Este documento explica como baixar os modelos GGUF para uso offline em ambientes corporativos.

> **NOTA**: O wheel do `llama-cpp-python` já está incluso na pasta `wheels/` e será instalado automaticamente durante a instalação offline. Não é mais necessário compilar ou baixar separadamente.

> **🏢 AMBIENTE CORPORATIVO**: O modelo Llama 3.1 8B está disponível via **GitHub Releases** do repositório, compatível com proxies corporativos que confiam no GitHub. Os scripts de download usam automaticamente essa fonte.

## Tabela de Modelos Disponíveis

| Modelo | Tamanho | RAM | Qualidade PT-BR | Recomendação |
|--------|---------|-----|-----------------|--------------|
| **Llama 3.1 8B** | ~4.7 GB | ~8 GB | ⭐⭐⭐⭐⭐ Excelente | **MELHOR para Português** |
| Mistral 7B | ~4 GB | ~8 GB | ⭐⭐⭐⭐ Muito Boa | Alternativa de qualidade |
| TinyLlama 1.1B | ~670 MB | ~2 GB | ⭐⭐⭐ Boa | Recursos limitados |
| Phi-3 Mini | ~2.3 GB | ~6 GB | ⭐⭐ Limitada | Não recomendado para PT-BR |
| GPT-2 Portuguese | ~500 MB | ~1 GB | ⭐ Básica | Fallback apenas |

---

## 1. Download Automático via Script

### PowerShell
```powershell
# Baixar todos os modelos
.\scripts\download_models.ps1

# Baixar apenas Llama 3.1 (RECOMENDADO)
.\scripts\download_models.ps1 -Model llama3

# Baixar apenas TinyLlama
.\scripts\download_models.ps1 -Model tinyllama

# Baixar apenas Mistral
.\scripts\download_models.ps1 -Model mistral
```

### Prompt de Comando (CMD)
```batch
REM Baixar todos os modelos
scripts\download_models.cmd all

REM Baixar apenas Llama 3.1 (RECOMENDADO)
scripts\download_models.cmd llama3

REM Baixar apenas TinyLlama
scripts\download_models.cmd tinyllama

REM Baixar apenas Mistral
scripts\download_models.cmd mistral
```

---

## 2. Download do Llama 3.1 8B (MELHOR PARA PORTUGUÊS)

O Llama 3.1 8B possui excelente suporte ao português brasileiro e é recomendado
para obter respostas de alta qualidade.

### Opção A: Via GitHub Releases (RECOMENDADO para ambiente corporativo)

O modelo está disponível no GitHub Releases do repositório, dividido em partes
para contornar o limite de 2GB do GitHub. Os scripts baixam e juntam automaticamente.

**PowerShell:**
```powershell
.\scripts\download_llama3_github.ps1
```

**Prompt de Comando (CMD):**
```batch
scripts\download_llama3_github.cmd
```

**Vantagens:**
- ✅ Compatível com proxies corporativos que confiam no GitHub
- ✅ Baixa em partes (evita timeout em conexões lentas)
- ✅ Verificação de integridade SHA256
- ✅ Junta automaticamente as partes

### Opção B: Download direto do HuggingFace

Se o proxy permitir acesso ao HuggingFace:

1. Acesse: https://huggingface.co/bartowski/Meta-Llama-3.1-8B-Instruct-GGUF
2. Baixe o arquivo: `Meta-Llama-3.1-8B-Instruct-Q4_K_M.gguf` (~4.7 GB)
3. Coloque em: `models/generator/Meta-Llama-3.1-8B-Instruct-Q4_K_M.gguf`

### Opção C: Via PowerShell/curl (HuggingFace)

```powershell
# Windows (PowerShell)
Invoke-WebRequest -Uri "https://huggingface.co/bartowski/Meta-Llama-3.1-8B-Instruct-GGUF/resolve/main/Meta-Llama-3.1-8B-Instruct-Q4_K_M.gguf" -OutFile "models/generator/Meta-Llama-3.1-8B-Instruct-Q4_K_M.gguf"
```

```bash
# Linux/Mac
wget -P models/generator/ "https://huggingface.co/bartowski/Meta-Llama-3.1-8B-Instruct-GGUF/resolve/main/Meta-Llama-3.1-8B-Instruct-Q4_K_M.gguf"
```

---

## 3. Download do TinyLlama (RECURSOS LIMITADOS)

### Opção A: Download direto do HuggingFace

1. Acesse: https://huggingface.co/TheBloke/TinyLlama-1.1B-Chat-v1.0-GGUF
2. Baixe o arquivo: `tinyllama-1.1b-chat-v1.0.Q4_K_M.gguf` (~670 MB)
3. Coloque em: `models/generator/tinyllama-1.1b-chat-v1.0.Q4_K_M.gguf`

### Opção B: Via PowerShell/curl

```powershell
# Windows (PowerShell)
Invoke-WebRequest -Uri "https://huggingface.co/TheBloke/TinyLlama-1.1B-Chat-v1.0-GGUF/resolve/main/tinyllama-1.1b-chat-v1.0.Q4_K_M.gguf" -OutFile "models/generator/tinyllama-1.1b-chat-v1.0.Q4_K_M.gguf"
```

```bash
# Linux/Mac
wget -P models/generator/ "https://huggingface.co/TheBloke/TinyLlama-1.1B-Chat-v1.0-GGUF/resolve/main/tinyllama-1.1b-chat-v1.0.Q4_K_M.gguf"
```

---

## 4. Outros Modelos (Opcionais)

### Mistral 7B (alternativa de qualidade, ~4 GB)

```powershell
# Windows (PowerShell)
Invoke-WebRequest -Uri "https://huggingface.co/TheBloke/Mistral-7B-Instruct-v0.2-GGUF/resolve/main/mistral-7b-instruct-v0.2.Q4_K_M.gguf" -OutFile "models/generator/mistral-7b-instruct-v0.2.Q4_K_M.gguf"
```

```bash
# Linux/Mac
wget -P models/generator/ "https://huggingface.co/TheBloke/Mistral-7B-Instruct-v0.2-GGUF/resolve/main/mistral-7b-instruct-v0.2.Q4_K_M.gguf"
```

### Phi-3 Mini (NÃO recomendado para português, ~2.3 GB)

⚠️ **AVISO**: O Phi-3 Mini tem suporte limitado ao português brasileiro.
Use apenas se não puder usar Llama 3.1 ou Mistral.

```powershell
# Windows (PowerShell)
Invoke-WebRequest -Uri "https://huggingface.co/microsoft/Phi-3-mini-4k-instruct-gguf/resolve/main/Phi-3-mini-4k-instruct-q4.gguf" -OutFile "models/generator/Phi-3-mini-4k-instruct-q4.gguf"
```

```bash
# Linux/Mac
wget -P models/generator/ "https://huggingface.co/microsoft/Phi-3-mini-4k-instruct-gguf/resolve/main/Phi-3-mini-4k-instruct-q4.gguf"
```

---

## 5. llama-cpp-python (Já Incluso)

O wheel pré-compilado do `llama-cpp-python` **já está incluso** na pasta `wheels/` e será instalado automaticamente durante a instalação offline.

### Verificar se está instalado

```bash
python -c "import llama_cpp; print('Versão:', llama_cpp.__version__)"
```

### Se precisar reinstalar manualmente

```powershell
# PowerShell
.\scripts\install_llama_cpp.ps1
```

```batch
REM Prompt de Comando
scripts\install_llama_cpp.cmd
```

### Atualizar o wheel (se necessário)

Se precisar atualizar para uma versão mais recente:

1. Acesse: https://github.com/abetlen/llama-cpp-python/releases
2. Baixe o wheel para seu sistema:
   - Windows: `llama_cpp_python-*-cp311-cp311-win_amd64.whl`
   - Linux: `llama_cpp_python-*-cp311-cp311-manylinux_*.whl`
3. Substitua o arquivo na pasta `wheels/`

---

## 6. Verificar Instalação

Após baixar, verifique:

```bash
# Verificar modelos instalados
python run.py models --check

# Testar Q&A com TinyLlama
python run.py qa documento.pdf -q "teste" --model tinyllama

# Testar Q&A com Llama 3.1 (se disponível)
python run.py qa documento.pdf -q "teste" --model llama3-8b
```

---

## 7. Estrutura Final

```
models/
└── generator/
    ├── Meta-Llama-3.1-8B-Instruct-Q4_K_M.gguf   # ~4.7 GB (MELHOR para PT-BR)
    ├── mistral-7b-instruct-v0.2.Q4_K_M.gguf     # ~4 GB (alternativa)
    ├── tinyllama-1.1b-chat-v1.0.Q4_K_M.gguf     # ~670 MB (recursos limitados)
    ├── Phi-3-mini-4k-instruct-q4.gguf           # ~2.3 GB (não recomendado)
    └── models--pierreguillou--gpt2-small-portuguese/  # Já incluso (fallback)

wheels/
└── llama_cpp_python-*-win_amd64.whl             # Já incluso na instalação
```

---

## 8. Sem llama-cpp-python?

Se por algum motivo o llama-cpp-python não funcionar, o sistema usará automaticamente
o GPT-2 Portuguese como fallback. A qualidade será menor, mas funcionará.

```yaml
# config.yaml - forçar GPT-2
rag:
  generation:
    default_model: "gpt2-portuguese"
```

---

## 9. Solução de Problemas

### Erro: "llama_cpp module not found"

```bash
# Reinstalar via script
scripts\install_llama_cpp.cmd
```

### Erro: "Model file not found"

Verifique se o modelo GGUF está na pasta correta:
```bash
python run.py models --check
```

### Performance lenta

- Use TinyLlama em máquinas com pouca RAM (<8 GB)
- Use Llama 3.1 em máquinas com boa RAM (≥16 GB)
- Feche outros programas durante o processamento
