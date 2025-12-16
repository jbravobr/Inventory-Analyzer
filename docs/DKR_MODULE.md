# Módulo DKR - Domain Knowledge Rules

## Visão Geral

O módulo DKR (Domain Knowledge Rules) é um sistema de regras de domínio que melhora a acurácia das respostas do Q&A sem necessidade de modificar código. Permite definir conhecimento estruturado e regras de validação em arquivos `.rules` usando uma linguagem humanizada.

## Características

- **100% Offline**: Funciona completamente local, sem dependências de rede
- **Linguagem Humanizada**: Sintaxe em português, fácil de ler e escrever
- **Não-Intrusivo**: Integração opcional com o Q&A existente
- **Cache Inteligente**: Invalida automaticamente quando regras mudam
- **Ferramentas de Debug**: REPL interativo, flag `--explain`, validador

## Arquitetura

```
┌─────────────────────────────────────────────────────────────┐
│                       QA Engine                              │
├─────────────────────────────────────────────────────────────┤
│  Pergunta ─────► DKR Engine ─────► Resposta Validada        │
│                      │                                       │
│              ┌───────┴───────┐                              │
│              │               │                              │
│         Intent          Validation                          │
│        Detection         Rules                              │
│              │               │                              │
│              ▼               ▼                              │
│         Query           Answer                              │
│        Expansion       Correction                           │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
                    ┌─────────────────┐
                    │  arquivo.rules  │
                    │   (DSL Human)   │
                    └─────────────────┘
```

## Estrutura do Arquivo .rules

### Seção 1: Domínio

```
DOMÍNIO: Nome do Domínio
```

Define o nome do domínio de conhecimento.

### Seção 2: Fatos Conhecidos

```
FATOS CONHECIDOS:

A licença AGPL-3.0 tem criticidade ALTO.
  Motivo: Exige disponibilização do código para SaaS.
  Ação: Evitar uso.

A licença MIT tem criticidade BAIXO.
  Motivo: Licença permissiva.
  Ação: Seguro para uso.
```

Fatos são conhecimento estruturado do domínio. Níveis de criticidade:
- **ALTO**: Requer atenção especial
- **MÉDIO**: Verificar caso a caso
- **BAIXO**: Geralmente seguro

### Seção 3: Padrões de Intenção

```
PADRÕES DE INTENÇÃO:

criticidade_alta:
  - "mais crítica"
  - "mais perigosa"
  - "devo evitar"
  Resposta deve conter: "ALTO", "AGPL"
```

Intents são padrões que identificam o tipo de pergunta. O sistema gera intents automáticos baseados nos fatos, mas você pode definir os seus.

### Seção 4: Expansão de Busca

```
EXPANSÃO DE BUSCA:

Para "criticidade_alta", adicionar: "GRAU DE CRITICIDADE", "ALTO"
```

Quando um intent é detectado, esses termos são adicionados à query para melhorar a recuperação de chunks relevantes.

### Seção 5: Regras de Validação

```
REGRAS DE VALIDAÇÃO:

QUANDO usuário pergunta "mais crítica"
  E resposta menciona "MIT"
  E resposta NÃO menciona "AGPL"
ENTÃO corrigir para:
  A licença mais crítica é **AGPL-3.0** (criticidade ALTO).
  
  (Resposta corrigida pelo DKR)
```

Regras definem quando e como corrigir respostas incorretas.

### Seção 6: Sinônimos

```
SINÔNIMOS:

"crítica" também pode ser: "perigosa", "arriscada", "restritiva"
```

Define sinônimos para melhorar a detecção de termos.

## Comandos CLI

### Listar Arquivos .rules

```bash
python run.py dkr list
```

### Validar Arquivo

```bash
python run.py dkr validate domain_rules/licencas_software.rules
```

### Exibir Informações

```bash
python run.py dkr info domain_rules/licencas_software.rules
```

### Testar Regras

```bash
# Com pergunta e resposta simulada
python run.py dkr test domain_rules/licencas_software.rules \
  -q "Qual é a licença mais crítica?" \
  -a "A licença mais crítica é Apache 2.0"

# Interativo
python run.py dkr test domain_rules/licencas_software.rules
```

### Assistente de Criação (Wizard)

```bash
python run.py dkr wizard
```

Guia interativo para criar novos arquivos .rules.

### REPL Interativo

```bash
python run.py dkr repl domain_rules/licencas_software.rules
```

Terminal interativo para debugging de regras.

## Integração com Q&A

### Uso Automático

O DKR é carregado automaticamente quando há um arquivo `.rules` correspondente ao template:

```
Template: licencas_software
Arquivo:  domain_rules/licencas_software.rules
```

### Flag --explain

Mostra trace detalhado do processamento DKR:

```bash
python run.py qa documento.pdf -q "pergunta" --explain
```

Saída:
```
--- DKR Trace ---
  Intent: criticidade_alta ██████░░░░ 67%
  Query expandida: Sim
    Termos: ['GRAU DE CRITICIDADE', 'ALTO']
  Regras avaliadas: 7
  Regras ativadas: 1
    > rule_99
  Resposta CORRIGIDA
    Motivo: Regra 'rule_99': Resposta corrigida
  Tempo DKR: 0.3ms
--- Fim DKR Trace ---
```

### Flag --no-dkr

Desabilita o DKR temporariamente:

```bash
python run.py qa documento.pdf -q "pergunta" --no-dkr
```

## Uso Programático

```python
from dkr import DKREngine

# Carrega regras
engine = DKREngine("domain_rules/licencas_software.rules")

# Processa pergunta/resposta
result = engine.process(
    question="Qual é a licença mais crítica?",
    answer="A licença mais crítica é MIT",
    context="..."
)

# Verifica se foi corrigido
if result.was_corrected:
    print(f"Corrigido: {result.final_answer}")
else:
    print(f"Mantido: {result.original_answer}")

# Expande query para melhor retrieval
expanded = engine.expand_query("Qual é a mais crítica?")
```

## Cache

O DKR utiliza dois níveis de cache:

1. **Cache de Regras**: Evita re-parsing do arquivo `.rules`
2. **Cache de Respostas**: Inclui `rules_hash` para invalidação automática

Quando você modifica um arquivo `.rules`, o cache de respostas é automaticamente invalidado.

## Boas Práticas

### 1. Seja Específico nas Regras

```
# RUIM - Muito genérico
QUANDO usuário pergunta "licença"
  E resposta menciona "MIT"
ENTÃO corrigir para: ...

# BOM - Específico
QUANDO usuário pergunta "mais crítica"
  E resposta menciona "MIT"
  E resposta NÃO menciona "AGPL"
ENTÃO corrigir para: ...
```

### 2. Teste Suas Regras

```bash
python run.py dkr test arquivo.rules -q "pergunta" -a "resposta simulada"
```

### 3. Use o REPL para Debug

```bash
python run.py dkr repl arquivo.rules
[DKR] > ask Qual é a mais crítica?
[DKR] > test Qual é a mais crítica?
```

### 4. Valide Antes de Usar

```bash
python run.py dkr validate arquivo.rules
```

### 5. Cuidado com Falsos Positivos

Termos curtos como "MIT" podem aparecer em outras palavras ("permite"). Use termos mais específicos:

```
# RUIM
E resposta menciona "MIT"

# BOM
E resposta menciona "MIT License"
E resposta NÃO menciona "BAIXO"
```

## Estrutura de Diretórios

```
inventory_analyzer_offline/
├── domain_rules/
│   ├── _EXEMPLO_COMENTADO.rules    # Template documentado
│   ├── licencas_software.rules     # Regras de licenças
│   └── contratos.rules             # Regras de contratos (exemplo)
├── src/dkr/
│   ├── __init__.py                 # Exports do módulo
│   ├── models.py                   # Modelos de dados
│   ├── parser.py                   # Parser da DSL
│   ├── engine.py                   # Motor de processamento
│   ├── validator.py                # Validador de arquivos
│   ├── cache.py                    # Cache de regras
│   ├── cli.py                      # Interface de linha de comando
│   ├── wizard.py                   # Assistente de criação
│   └── repl.py                     # REPL interativo
└── cache/dkr/                      # Cache persistente
```

## Fluxo de Processamento

```
1. Pergunta recebida
       ↓
2. Detecta Intent (padrões de texto)
       ↓
3. Expande Query (adiciona termos)
       ↓
4. RAG busca contexto (query expandida)
       ↓
5. LLM gera resposta
       ↓
6. DKR valida resposta (regras)
       ↓
7. Se regra ativa → Corrige resposta
       ↓
8. Retorna resposta final
```

## Troubleshooting

### DKR não está carregando

1. Verifique se o arquivo `.rules` existe:
   ```bash
   python run.py dkr list
   ```

2. Verifique o nome do arquivo (deve corresponder ao template):
   - Template: `licencas_software`
   - Arquivo: `domain_rules/licencas_software.rules`

3. Verifique erros de sintaxe:
   ```bash
   python run.py dkr validate arquivo.rules
   ```

### Regra não está ativando

1. Verifique o intent detectado:
   ```bash
   python run.py dkr repl arquivo.rules
   [DKR] > ask sua pergunta aqui
   ```

2. Verifique as condições da regra:
   ```bash
   [DKR] > rules
   ```

3. Teste com resposta simulada:
   ```bash
   python run.py dkr test arquivo.rules -q "pergunta" -a "resposta"
   ```

### Cache não está atualizando

1. O cache é invalidado automaticamente quando `rules_hash` muda
2. Para forçar recarga:
   ```bash
   python run.py qa documento.pdf -q "pergunta" --no-cache
   ```

