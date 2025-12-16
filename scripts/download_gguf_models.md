# Download de Modelos GGUF para Uso Offline

Este documento explica como baixar os modelos GGUF e a biblioteca llama-cpp-python
para uso offline em ambientes corporativos.

## 1. Download do TinyLlama (RECOMENDADO)

### Opcao A: Download direto do HuggingFace

1. Acesse: https://huggingface.co/TheBloke/TinyLlama-1.1B-Chat-v1.0-GGUF
2. Baixe o arquivo: `tinyllama-1.1b-chat-v1.0.Q4_K_M.gguf` (~670 MB)
3. Coloque em: `models/generator/tinyllama-1.1b-chat-v1.0.Q4_K_M.gguf`

### Opcao B: Via wget/curl

```bash
# Windows (PowerShell)
Invoke-WebRequest -Uri "https://huggingface.co/TheBloke/TinyLlama-1.1B-Chat-v1.0-GGUF/resolve/main/tinyllama-1.1b-chat-v1.0.Q4_K_M.gguf" -OutFile "models/generator/tinyllama-1.1b-chat-v1.0.Q4_K_M.gguf"

# Linux/Mac
wget -P models/generator/ "https://huggingface.co/TheBloke/TinyLlama-1.1B-Chat-v1.0-GGUF/resolve/main/tinyllama-1.1b-chat-v1.0.Q4_K_M.gguf"
```

## 2. Download do llama-cpp-python (OBRIGATORIO para GGUF)

### Opcao A: Via pip (requer internet)

```bash
pip install llama-cpp-python
```

### Opcao B: Download do wheel para uso offline

1. Acesse: https://github.com/abetlen/llama-cpp-python/releases
2. Baixe o wheel apropriado para seu sistema:
   - Windows: `llama_cpp_python-*-cp311-cp311-win_amd64.whl` (ou cp314 se disponivel)
   - Linux: `llama_cpp_python-*-cp311-cp311-manylinux_*.whl`
3. Coloque em: `wheels/`
4. Instale offline:
   ```bash
   pip install wheels/llama_cpp_python-*.whl
   ```

**IMPORTANTE**: O llama-cpp-python pode ter dependencias nativas. Em alguns sistemas
pode ser necessario compilar do fonte.

### Opcao C: Usar pre-built wheels do PyPI

```bash
# Baixar wheel para cache local
pip download llama-cpp-python --dest wheels/
```

## 3. Outros Modelos (Opcionais)

### Phi-3 Mini (melhor qualidade, ~2.3 GB)

```bash
# Download
wget -P models/generator/ "https://huggingface.co/microsoft/Phi-3-mini-4k-instruct-gguf/resolve/main/Phi-3-mini-4k-instruct-q4.gguf"
```

### Mistral 7B (melhor qualidade, ~4 GB)

```bash
# Download
wget -P models/generator/ "https://huggingface.co/TheBloke/Mistral-7B-Instruct-v0.2-GGUF/resolve/main/mistral-7b-instruct-v0.2.Q4_K_M.gguf"
```

## 4. Verificar Instalacao

Apos baixar, verifique:

```bash
# Verificar modelos instalados
python run.py models --check

# Testar Q&A com TinyLlama
python run.py qa documento.pdf -q "teste" --model tinyllama
```

## 5. Estrutura Final

```
models/
└── generator/
    ├── tinyllama-1.1b-chat-v1.0.Q4_K_M.gguf     # ~670 MB (RECOMENDADO)
    ├── Phi-3-mini-4k-instruct-q4.gguf            # ~2.3 GB (opcional)
    ├── mistral-7b-instruct-v0.2.Q4_K_M.gguf     # ~4 GB (opcional)
    └── models--pierreguillou--gpt2-small-portuguese/  # Ja incluso

wheels/
└── llama_cpp_python-*-win_amd64.whl             # OBRIGATORIO para GGUF
```

## 6. Sem llama-cpp-python?

Se nao conseguir instalar o llama-cpp-python, o sistema usara automaticamente
o GPT-2 Portuguese como fallback. A qualidade sera menor, mas funcionara.

```yaml
# config.yaml - forcar GPT-2
rag:
  generation:
    default_model: "gpt2-portuguese"
```

