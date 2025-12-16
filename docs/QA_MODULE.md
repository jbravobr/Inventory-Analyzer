# Modulo Q&A - Sistema de Perguntas e Respostas

## Visao Geral

O modulo Q&A permite fazer perguntas em linguagem natural sobre documentos PDF e receber respostas baseadas no conteudo do documento.

### Funcionalidades

- **Perguntas em linguagem natural**: Faca perguntas como faria a um especialista
- **Modo offline/online**: Funciona 100% local ou com APIs cloud
- **Multiplos modelos de linguagem**: TinyLlama, Phi-3, Mistral, GPT-2
- **Templates personalizaveis**: Arquivos `.txt` faceis de editar
- **Deteccao automatica de tipo de documento**: Seleciona o template ideal
- **Historico de conversa**: Permite perguntas de acompanhamento
- **Cache de respostas**: Respostas rapidas para perguntas repetidas
- **Cache de OCR**: Evita reprocessamento de PDFs ja lidos
- **Exportacao para TXT**: Salva respostas em arquivo de texto
- **Validacao anti-alucinacao**: Verifica se respostas estao fundamentadas
- **DKR (Domain Knowledge Rules)**: Regras de dominio para corrigir respostas automaticamente

---

## Inicio Rapido

### Pergunta Unica

```bash
python run.py qa documento.pdf -q "Qual e a licenca mais critica?"
```

### Modo Interativo

```bash
python run.py qa documento.pdf -i
```

### Com Template Especifico

```bash
python run.py qa documento.pdf -q "pergunta" --template licencas_software
```

### Salvar Resposta em TXT

```bash
python run.py qa documento.pdf -q "pergunta" --save-txt resposta.txt
```

### Usar Modelo Especifico

```bash
python run.py qa documento.pdf -q "pergunta" --model tinyllama
```

---

## Comandos Disponiveis

### Comando Principal: `qa`

```bash
python run.py qa <pdf_path> [opcoes]
```

**Opcoes:**

| Opcao | Descricao |
|-------|-----------|
| `-q, --question` | Pergunta unica (modo nao-interativo) |
| `-i, --interactive` | Modo interativo de perguntas |
| `-t, --template` | Nome do template a usar |
| `-o, --output` | Arquivo para exportar conversa |
| `--save-txt` | Salva resposta em arquivo TXT |
| `--model` | Modelo de linguagem (tinyllama, phi3-mini, gpt2-portuguese) |
| `--no-cache` | Desabilita cache de respostas |
| `--no-ocr-cache` | Desabilita cache de OCR |
| `--list-templates` | Lista templates disponiveis |

### Gerenciamento de Cache de Respostas: `qa-cache`

```bash
python run.py qa-cache [opcoes]
```

| Opcao | Descricao |
|-------|-----------|
| `--stats` | Mostra estatisticas do cache |
| `--clear` | Limpa o cache |
| `--frequent` | Mostra perguntas frequentes |

### Gerenciamento de Cache OCR: `ocr-cache`

```bash
python run.py ocr-cache [opcoes]
```

| Opcao | Descricao |
|-------|-----------|
| `--list` | Lista documentos em cache |
| `--stats` | Mostra estatisticas do cache |
| `--clear` | Limpa todo o cache |
| `--remove <arquivo>` | Remove documento especifico |
| `--cleanup` | Remove entradas expiradas |

---

## Modelos de Linguagem

O sistema suporta multiplos modelos de linguagem para geracao de respostas.

### Modelos Disponiveis

| Modelo | ID | RAM | Qualidade | Velocidade | Contexto |
|--------|-----|-----|-----------|------------|----------|
| TinyLlama-1.1B | `tinyllama` | ~2 GB | Boa | Rapido | ~1200 chars |
| Phi-3-Mini | `phi3-mini` | ~6 GB | Excelente | Media | ~2500 chars |
| Mistral-7B | `mistral-7b` | ~8 GB | Excelente | Lento | ~3000 chars |
| GPT-2 Portuguese | `gpt2-portuguese` | ~2 GB | Basica | Rapido | ~500 chars |

> **Nota**: O TinyLlama agora suporta ~1200 caracteres de contexto (~1000 tokens), melhorando significativamente a qualidade das respostas.

### Como Usar

```bash
# Usar TinyLlama (padrao)
python run.py qa doc.pdf -q "pergunta" --model tinyllama

# Usar Phi-3 para melhor qualidade
python run.py qa doc.pdf -q "pergunta" --model phi3-mini
```

### Configuracao Padrao

Em `config.yaml`:

```yaml
rag:
  generation:
    default_model: "tinyllama"
```

> Veja [MODELOS_OFFLINE.md](MODELOS_OFFLINE.md) para instrucoes de instalacao.

---

## Modo Interativo

No modo interativo, voce pode fazer multiplas perguntas em sequencia:

```bash
python run.py qa documento.pdf -i
```

### Comandos Especiais

| Comando | Descricao |
|---------|-----------|
| `/sair` | Encerra a sessao |
| `/limpar` | Limpa historico da conversa |
| `/exportar` | Exporta conversa para arquivo |
| `/template <nome>` | Muda o template |
| `/info` | Mostra informacoes do documento |

### Exemplo de Sessão

```
📄 Documento: analise-licencas.pdf
📊 Páginas: 15 | Chunks: 42
📝 Template: licencas_software

> Quais licenças são consideradas de alta criticidade?

╭─────────────────────────────────────────────────────╮
│ As licenças de alta criticidade são:                │
│ - GPL-3.0                                           │
│ - AGPL-3.0                                          │
│                                                     │
│ 📚 Páginas: 3, 5 | Confiança: 87%                   │
╰─────────────────────────────────────────────────────╯

> E qual a razão para GPL-3.0 ser crítica?

╭─────────────────────────────────────────────────────╮
│ A GPL-3.0 é considerada crítica porque...           │
╰─────────────────────────────────────────────────────╯

> /sair
Encerrando sessão...
```

---

## Templates de Prompts

### O que são Templates?

Templates são arquivos `.txt` que definem como o sistema deve responder às perguntas. Eles ficam em:

```
instructions/qa_templates/
```

### Templates Incluídos

| Template | Descrição | Uso Ideal |
|----------|-----------|-----------|
| `sistema_padrao` | Template genérico | Qualquer documento |
| `licencas_software` | Licenças open source | GPL, MIT, Apache, etc. |
| `contratos` | Documentos jurídicos | Contratos, termos |
| `atas_reuniao` | Atas corporativas | Assembleias, reuniões |
| `inventario` | Escrituras | Inventários, partilhas |
| `geral` | Template mínimo | Uso rápido |

### Detecção Automática

O sistema detecta automaticamente o tipo de documento e seleciona o template adequado baseado em palavras-chave:

- Licenças: GPL, MIT, Apache, open source → `licencas_software`
- Contratos: contrato, cláusula, locação → `contratos`
- Atas: reunião, assembleia, quotista → `atas_reuniao`
- Inventários: herdeiro, espólio, partilha → `inventario`

### Criando Seus Próprios Templates

Veja o guia completo em:

```
instructions/qa_templates/_COMO_CRIAR_TEMPLATES.txt
```

#### Estrutura Básica

```
[INSTRUCAO_SISTEMA]
Defina o papel do assistente e regras gerais.

[INSTRUCAO_USUARIO]
Use variáveis como {contexto}, {pergunta}, {documento}, {paginas}.

[FORMATO_RESPOSTA]
Defina como a resposta deve ser estruturada.
```

#### Variáveis Disponíveis

| Variável | Descrição |
|----------|-----------|
| `{contexto}` | Trecho relevante do documento |
| `{pergunta}` | Pergunta do usuário |
| `{documento}` | Nome do arquivo PDF |
| `{paginas}` | Páginas de referência |
| `{data}` | Data atual (DD/MM/AAAA) |
| `{hora}` | Hora atual (HH:MM) |

---

## Configuração

### Arquivo config.yaml

```yaml
qa:
  enabled: true
  
  templates:
    dir: "./instructions/qa_templates"
    default: "sistema_padrao"
    auto_detect:
      enabled: true
  
  conversation:
    max_turns: 10
    memory_type: "sliding_window"
  
  validation:
    enabled: true
    min_confidence: 0.5
  
  cache:
    enabled: true
    ttl_hours: 24

# Configurações RAG que afetam o Q&A
rag:
  chunking:
    strategy: "semantic_sections"  # ⭐ Chunking por seções lógicas
    chunk_size: 800
    chunk_overlap: 100

  retrieval:
    top_k: 10
    use_hybrid_search: true        # ⭐ Busca híbrida (BM25 + Embeddings)
    bm25_weight: 0.4               # Peso do BM25
    semantic_weight: 0.6           # Peso dos embeddings
    use_reranking: true

  generation:
    models:
      tinyllama:
        max_context_chars: 1200    # ⭐ ~1000 tokens de contexto
```

### Opções de Configuração

| Seção | Opção | Descrição | Padrão |
|-------|-------|-----------|--------|
| templates | dir | Diretório dos templates | ./instructions/qa_templates |
| templates | default | Template padrão | sistema_padrao |
| templates.auto_detect | enabled | Detectar template automaticamente | true |
| conversation | max_turns | Máximo de turnos no histórico | 10 |
| conversation | memory_type | Tipo de memória | sliding_window |
| validation | enabled | Validar respostas | true |
| validation | min_confidence | Confiança mínima | 0.5 |
| cache | enabled | Usar cache | true |
| cache | ttl_hours | Tempo de vida do cache | 24 |

---

## Modo Offline vs Online

### Modo Offline (Padrão)

```bash
python run.py qa documento.pdf -q "pergunta"
```

- Usa modelos locais (GPT-2 português)
- Não requer internet
- Respostas mais simples

### Modo Online

```bash
python run.py --online qa documento.pdf -q "pergunta"
```

- Pode usar APIs cloud (OpenAI, Anthropic)
- Respostas mais elaboradas
- Requer configuração de API keys

---

## Arquitetura

```
src/qa/
├── __init__.py          # Exportações do módulo
├── qa_engine.py         # Motor principal de Q&A
├── template_loader.py   # Carrega templates .txt
├── conversation.py      # Histórico de conversa
├── knowledge_base.py    # Base de conhecimento estruturado
├── qa_validator.py      # Validação de respostas
└── cache.py             # Cache de respostas
```

### Fluxo de Processamento

```
1. Carrega documento PDF
       ↓
2. Extrai texto (OCR se necessário) → Cache de OCR
       ↓
3. Chunking Semântico (detecta seções lógicas)
       ↓
4. Embeddings em Português (neuralmind/bert-base-portuguese-cased)
       ↓
5. Indexa chunks no VectorStore (FAISS)
       ↓
6. Recebe pergunta do usuário
       ↓
7. Verifica cache de respostas
       ↓
8. Busca Híbrida:
   • BM25 (40%) - termos técnicos, siglas
   • Embeddings (60%) - significado, contexto
   • RRF (Reciprocal Rank Fusion) - combinação
       ↓
9. Re-ranking dos resultados
       ↓
10. Gera resposta com template + modelo (TinyLlama)
       ↓
11. Valida resposta (anti-alucinação)
       ↓
12. Retorna ao usuário + Cache
```

---

## Validação de Respostas

O sistema inclui validação para evitar "alucinações" (respostas inventadas):

### Critérios de Validação

1. **Fundamentação**: Resposta deve estar baseada no contexto
2. **Relevância**: Resposta deve ser relevante para a pergunta
3. **Completude**: Resposta não deve ser vazia ou muito curta
4. **Especificidade**: Evita respostas excessivamente genéricas

### Níveis de Confiança

| Confiança | Cor | Significado |
|-----------|-----|-------------|
| ≥70% | Verde | Alta - resposta bem fundamentada |
| 40-69% | Amarelo | Média - revisar se necessário |
| <40% | Vermelho | Baixa - verificar no documento |

---

## Cache de Respostas

O cache armazena respostas para melhorar performance:

### Funcionamento

- Respostas são cacheadas por pergunta + documento
- Cache expira após TTL (padrão: 24h)
- Invalidado automaticamente se contexto mudar

### Gerenciamento

```bash
# Ver estatísticas
python run.py qa-cache --stats

# Limpar cache
python run.py qa-cache --clear

# Ver perguntas frequentes
python run.py qa-cache --frequent
```

---

## Base de Conhecimento

O sistema extrai automaticamente informações estruturadas:

### Para Documentos de Licenças

- Nomes das licenças encontradas
- Níveis de criticidade (ALTO/MÉDIO/BAIXO)
- Condições de uso
- Recomendações

### Consultas Especiais

```python
# Via código
kb = qa_engine.knowledge_base

# Consultar licença específica
info = kb.query_license("GPL-3.0")

# Verificar compatibilidade
result = kb.check_compatibility("MIT", "GPL-3.0")

# Buscar na base
results = kb.search("distribuição")
```

---

## Domain Knowledge Rules (DKR)

O módulo DKR permite definir regras de domínio para melhorar a acurácia das respostas.

### Uso Básico

```bash
# Q&A com trace de debug
python run.py qa documento.pdf -q "pergunta" --explain

# Desabilitar DKR temporariamente
python run.py qa documento.pdf -q "pergunta" --no-dkr
```

### Comandos DKR

```bash
# Listar arquivos de regras
python run.py dkr list

# Validar sintaxe
python run.py dkr validate domain_rules/licencas_software.rules

# Testar regra
python run.py dkr test domain_rules/licencas_software.rules -q "pergunta" -a "resposta"

# Criar novo arquivo (wizard)
python run.py dkr wizard

# REPL interativo
python run.py dkr repl domain_rules/licencas_software.rules
```

### Exemplo de Arquivo .rules

```
DOMÍNIO: Licenças de Software

FATOS CONHECIDOS:
A licença AGPL-3.0 tem criticidade ALTO.
  Motivo: Copyleft com obrigações SaaS.

REGRAS DE VALIDAÇÃO:
QUANDO usuário pergunta "mais crítica"
  E resposta menciona "MIT"
  E resposta NÃO menciona "AGPL"
ENTÃO corrigir para:
  A licença mais crítica é AGPL-3.0 (ALTO).
```

> Para documentação completa, veja [DKR_MODULE.md](DKR_MODULE.md)

---

## Solução de Problemas

### "Template não encontrado"

1. Verifique se o arquivo existe em `instructions/qa_templates/`
2. Confirme que o nome não tem extensão `.txt` no comando
3. Use `--list-templates` para ver disponíveis

### "Confiança baixa na resposta"

1. A informação pode não estar no documento
2. Tente reformular a pergunta
3. Use um template mais específico

### "Erro ao carregar documento"

1. Verifique se o PDF não está corrompido
2. Confirme permissões de leitura
3. Tente extrair texto primeiro: `python run.py extract documento.pdf`

### "Respostas muito genéricas"

1. Use modo online para LLMs melhores
2. Ajuste o template com instruções mais específicas
3. Faça perguntas mais diretas

---

## Exemplos de Uso

### Análise de Licenças

```bash
# Pergunta sobre criticidade
python run.py qa licencas.pdf -q "Quais licenças são de alta criticidade?"

# Verificar compatibilidade
python run.py qa licencas.pdf -q "GPL-3.0 é compatível com MIT?"

# Entender condições
python run.py qa licencas.pdf -q "O que é considerado distribuição?"
```

### Análise de Contratos

```bash
# Valor do contrato
python run.py qa contrato.pdf -q "Qual o valor mensal?" --template contratos

# Prazo
python run.py qa contrato.pdf -q "Quando vence o contrato?"

# Penalidades
python run.py qa contrato.pdf -q "Qual a multa por rescisão antecipada?"
```

### Análise de Atas

```bash
# Deliberações
python run.py qa ata.pdf -q "Quais ativos foram aprovados?" --template atas_reuniao

# Valores
python run.py qa ata.pdf -q "Qual o valor total envolvido?"
```

---

## Referência da API

### QAEngine

```python
from qa import QAEngine, QAConfig

# Inicializar
config = QAConfig()
engine = QAEngine(config=config)

# Carregar documento
num_chunks = engine.load_document("documento.pdf")

# Fazer pergunta
response = engine.ask("Qual é o valor total?")

print(response.answer)
print(response.pages)
print(response.confidence)
```

### QAResponse

```python
@dataclass
class QAResponse:
    question: str        # Pergunta original
    answer: str          # Resposta gerada
    pages: List[int]     # Páginas de referência
    confidence: float    # Confiança (0-1)
    context_used: str    # Contexto usado
    template_used: str   # Template usado
    processing_time: float  # Tempo em segundos
    from_cache: bool     # Se veio do cache
```

### TemplateLoader

```python
from qa import TemplateLoader

loader = TemplateLoader()

# Listar templates
templates = loader.list_templates()

# Obter template
template = loader.get_template("licencas_software")

# Recarregar templates
loader.reload()
```

