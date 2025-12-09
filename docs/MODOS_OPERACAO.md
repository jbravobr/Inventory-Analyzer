# Modos de Operação - Guia Detalhado

O Document Analyzer suporta três modos de operação que controlam como o sistema se comporta em relação a conexões de rede, downloads de modelos e uso de APIs cloud.

## Visão Geral

| Modo | Descrição | Quando Usar |
|------|-----------|-------------|
| **offline** | 100% local, sem conexão à internet | Ambientes corporativos restritos (PADRÃO) |
| **online** | Permite downloads e APIs cloud | Desenvolvimento, atualizações |
| **hybrid** | Tenta online, fallback para offline | Conectividade intermitente |

---

## Modo OFFLINE (Padrão)

### O que acontece

- Variáveis de ambiente são configuradas para bloquear conexões:
  - `TRANSFORMERS_OFFLINE=1`
  - `HF_HUB_OFFLINE=1`
  - `HF_DATASETS_OFFLINE=1`
- Modelos são carregados exclusivamente de `./models/`
- Nenhuma conexão de rede é tentada
- Se modelo não existir localmente → **ERRO**

### Requisitos

- Modelos pré-baixados em `./models/`
- Tesseract OCR instalado localmente
- Não requer acesso à internet

### Configuração

**config.yaml:**
```yaml
system:
  mode: "offline"
  
  offline:
    models_path: "./models"
    strict: true  # Falha se modelo não existir
```

**CLI (override temporário):**
```bash
python run.py --offline analyze documento.pdf
```

### Comportamento

```
┌─────────────────────────────────────────────────────────────┐
│                     MODO OFFLINE                            │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│   Usuário solicita modelo                                   │
│           │                                                 │
│           ▼                                                 │
│   ┌───────────────────┐                                     │
│   │ Busca em ./models │                                     │
│   └─────────┬─────────┘                                     │
│             │                                               │
│      ┌──────┴──────┐                                        │
│      │             │                                        │
│      ▼             ▼                                        │
│  ┌───────┐    ┌───────┐                                     │
│  │ Existe │   │ Não   │                                     │
│  │        │   │ existe│                                     │
│  └───┬────┘   └───┬───┘                                     │
│      │            │                                         │
│      ▼            ▼                                         │
│  ┌───────┐    ┌───────┐                                     │
│  │  USA  │    │ ERRO  │                                     │
│  └───────┘    └───────┘                                     │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## Modo ONLINE

### O que acontece

- Conexão com HuggingFace Hub é permitida
- Modelos podem ser baixados/atualizados automaticamente
- Cache local (`./models/`) é usado quando disponível
- APIs cloud podem ser habilitadas

### Requisitos

- Conexão com internet
- Acesso ao HuggingFace Hub (não bloqueado por firewall)
- (Opcional) API keys para serviços cloud

### Configuração

**config.yaml:**
```yaml
system:
  mode: "online"
  
  online:
    allow_model_download: true    # Baixa modelos faltantes
    check_for_updates: false      # Verifica versões mais novas
    use_cloud_embeddings: false   # Usar API de embeddings (OpenAI)
    use_cloud_generation: false   # Usar API de geração (GPT-4)
    connection_timeout: 10        # Timeout em segundos
```

**CLI (override temporário):**
```bash
python run.py --online analyze documento.pdf

# Com download permitido explicitamente
python run.py --online --allow-download analyze documento.pdf
```

### Comportamento

```
┌─────────────────────────────────────────────────────────────┐
│                     MODO ONLINE                             │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│   Usuário solicita modelo                                   │
│           │                                                 │
│           ▼                                                 │
│   ┌───────────────────┐                                     │
│   │ Busca em ./models │                                     │
│   └─────────┬─────────┘                                     │
│             │                                               │
│      ┌──────┴──────┐                                        │
│      │             │                                        │
│      ▼             ▼                                        │
│  ┌───────┐    ┌────────────┐                                │
│  │ Existe │   │ Não existe │                                │
│  │        │   │            │                                │
│  └───┬────┘   └──────┬─────┘                                │
│      │               │                                      │
│      │               ▼                                      │
│      │        ┌─────────────┐                               │
│      │        │  Download   │                               │
│      │        │ HuggingFace │                               │
│      │        └──────┬──────┘                               │
│      │               │                                      │
│      ▼               ▼                                      │
│  ┌───────────────────────┐                                  │
│  │         USA           │                                  │
│  └───────────────────────┘                                  │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## Modo HYBRID

### O que acontece

1. Testa conectividade com HuggingFace Hub (com timeout)
2. Se conectado → comporta-se como ONLINE
3. Se sem conexão → comporta-se como OFFLINE (fallback)
4. Log indica qual modo foi usado

### Requisitos

- Modelos locais em `./models/` para garantir fallback
- Conexão com internet (opcional)

### Configuração

**config.yaml:**
```yaml
system:
  mode: "hybrid"
  
  hybrid:
    prefer: "online"          # "online" ou "offline"
    fallback_enabled: true    # Usa cache local se online falhar
    fallback_timeout: 5       # Segundos antes de fallback
```

**CLI (override temporário):**
```bash
python run.py --hybrid analyze documento.pdf
```

### Comportamento

```
┌─────────────────────────────────────────────────────────────┐
│                     MODO HYBRID                             │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│   Inicialização                                             │
│           │                                                 │
│           ▼                                                 │
│   ┌───────────────────────┐                                 │
│   │ Testa conectividade   │                                 │
│   │ (timeout: 5s)         │                                 │
│   └─────────┬─────────────┘                                 │
│             │                                               │
│      ┌──────┴──────┐                                        │
│      │             │                                        │
│      ▼             ▼                                        │
│  ┌───────┐    ┌──────────┐                                  │
│  │ Online │   │ Timeout/ │                                  │
│  │        │   │ Erro     │                                  │
│  └───┬────┘   └────┬─────┘                                  │
│      │             │                                        │
│      ▼             ▼                                        │
│  ┌────────┐   ┌────────────┐                                │
│  │ Modo   │   │ Modo       │                                │
│  │ ONLINE │   │ OFFLINE    │                                │
│  └────────┘   │ (fallback) │                                │
│               └────────────┘                                │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### Casos de Uso

- **Laptops corporativos**: Funcionam offline no escritório, online em home office
- **Ambientes instáveis**: Conexão intermitente com datacenter
- **Desenvolvimento**: Testa online, mas não quebra se perder conexão

---

## Configuração via CLI vs config.yaml

### Prioridade

```
CLI (--online/--offline/--hybrid)  →  Maior prioridade
              │
              ▼
         config.yaml                →  Menor prioridade
```

### Exemplos

**Configuração padrão offline, mas forçar online para uma execução:**
```bash
# config.yaml tem mode: "offline"
python run.py --online analyze documento.pdf
# Esta execução usa modo ONLINE
```

**Configuração online, mas forçar offline:**
```bash
# config.yaml tem mode: "online"
python run.py --offline analyze documento.pdf
# Esta execução usa modo OFFLINE
```

---

## Controle de Downloads

O parâmetro `--allow-download` / `--no-download` controla especificamente se downloads são permitidos, independente do modo:

```bash
# Modo online, mas sem baixar novos modelos
python run.py --online --no-download analyze documento.pdf

# Modo offline com tentativa de download (não faz sentido, será ignorado)
python run.py --offline --allow-download analyze documento.pdf
```

---

## Verificando o Modo Atual

Use o comando `info` para ver a configuração atual:

```bash
python run.py info
```

Saída exemplo:
```
╔═══════════════════════════════════════════════════════════╗
║       DOCUMENT ANALYZER v1.1.0 - OFFLINE                  ║
╚═══════════════════════════════════════════════════════════╝

                    Configuração Atual
┏━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ Parâmetro            ┃ Valor                            ┃
┡━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┩
│ Modo de Operação     │ OFFLINE (100% local)             │
│ Downloads Permitidos │ Não                              │
│ APIs Cloud           │ Desabilitadas                    │
│ Caminho dos Modelos  │ ./models                         │
│                      │                                  │
│ Perfil Ativo         │ inventory                        │
│ Modo NLP             │ local                            │
└──────────────────────┴──────────────────────────────────┘
```

---

## Troubleshooting

### Erro: "Modelo não encontrado" em modo OFFLINE

**Causa**: O modelo não está disponível localmente.

**Solução**:
1. Verifique se a pasta `./models/` contém os modelos necessários
2. Use modo ONLINE temporariamente para baixar:
   ```bash
   python run.py --online --allow-download analyze documento.pdf
   ```
3. Depois volte para OFFLINE

### Erro: Timeout em modo ONLINE

**Causa**: Não consegue conectar ao HuggingFace Hub.

**Soluções**:
1. Verifique sua conexão com internet
2. Verifique se `huggingface.co` não está bloqueado pelo firewall
3. Use modo OFFLINE com modelos locais
4. Aumente o timeout no `config.yaml`:
   ```yaml
   system:
     online:
       connection_timeout: 30
   ```

### Modo HYBRID sempre usa OFFLINE

**Causa**: Teste de conectividade falhando.

**Soluções**:
1. Verifique conexão com internet
2. Aumente `fallback_timeout`:
   ```yaml
   system:
     hybrid:
       fallback_timeout: 10
   ```
3. Verifique logs para mensagens de erro de conexão

---

## Arquitetura

### ModeManager

O componente `ModeManager` (`src/config/mode_manager.py`) é responsável por:

1. **Ler configuração**: Do `config.yaml` e flags CLI
2. **Configurar ambiente**: Define variáveis `TRANSFORMERS_OFFLINE`, etc.
3. **Fornecer API**: Para outros módulos consultarem o modo atual
4. **Testar conectividade**: Para modo HYBRID

```python
from config.mode_manager import get_mode_manager

mode_mgr = get_mode_manager()

if mode_mgr.is_offline:
    print("Modo offline ativo")
    
if mode_mgr.allow_downloads:
    # Pode tentar baixar modelo
    pass
```

### Fluxo de Inicialização

```
┌──────────────────────────────────────────────────────────────┐
│                      INICIALIZAÇÃO                           │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│   1. CLI parseia argumentos (--online, --offline, --hybrid)  │
│                         │                                    │
│                         ▼                                    │
│   2. Carrega config.yaml                                     │
│                         │                                    │
│                         ▼                                    │
│   3. Inicializa ModeManager                                  │
│      - CLI override tem prioridade                           │
│      - Senão usa config.yaml                                 │
│      - Senão usa "offline" (padrão)                          │
│                         │                                    │
│                         ▼                                    │
│   4. ModeManager.configure_environment()                     │
│      - Define TRANSFORMERS_OFFLINE, HF_HUB_OFFLINE, etc.     │
│      - (HYBRID) Testa conectividade                          │
│                         │                                    │
│                         ▼                                    │
│   5. Executa análise no modo configurado                     │
│                                                              │
└──────────────────────────────────────────────────────────────┘
```

