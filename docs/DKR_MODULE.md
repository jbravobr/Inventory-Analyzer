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
│         Query          Normalization ──► Answer             │
│        Expansion       (fix terms)      Correction          │
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

### Seção 5: Normalizar Termos

```
NORMALIZAR TERMOS:

# Correções de siglas inexistentes (alucinações do LLM)
"GPLA" corrigir para: "GPL"
"AGPLA" corrigir para: "AGPL"

# Normalização de versões
"GPLv2" corrigir para: "GPL-2.0"
"GPLv3" corrigir para: "GPL-3.0"

# Com opção case-sensitive
"mit" corrigir para: "MIT" [case-sensitive]
```

Normaliza termos incorretos ou variantes **antes** de aplicar as regras de validação. Útil para:
- Corrigir alucinações do LLM (siglas inventadas como "GPLA")
- Padronizar variações de termos (GPLv2 → GPL-2.0)
- Corrigir erros de OCR no documento fonte

### Seção 6: Regras de Validação

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

### Seção 7: Sinônimos

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
════════════════════════════════════════════════════════════
  DKR TRACE
════════════════════════════════════════════════════════════
Domínio: Licenças de Software Open Source
Intenção detectada: criticidade_alta (67%)
Query expandida: Sim
  Termos adicionados: ['GRAU DE CRITICIDADE', 'ALTO']
Termos normalizados: Sim
  • "GPLA" → "GPL"
  • "GPLA-2.0" → "GPL-2.0"
Regras avaliadas: 7
Regras ativadas: 1
  • rule_99
Resposta corrigida: SIM
  Motivo: Regra 'rule_99': Resposta corrigida
Tempo: 0.5ms
════════════════════════════════════════════════════════════
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
3. Expande Query (adiciona termos para melhor retrieval)
       ↓
4. RAG busca contexto (query expandida)
       ↓
5. LLM gera resposta
       ↓
6. NORMALIZA TERMOS (corrige siglas erradas: GPLA → GPL)
       ↓
7. Aplica Regras de Validação (verifica condições)
       ↓
8. Se regra ativa → Corrige resposta
       ↓
9. Retorna resposta final
```

## Exemplo Completo de Arquivo .rules

A seguir, um exemplo completo e comentado de um arquivo `.rules` válido. Este exemplo demonstra todas as seções disponíveis e suas funcionalidades.

### Arquivo: `domain_rules/contratos_comerciais.rules`

```
# ═══════════════════════════════════════════════════════════
#  REGRAS DE DOMÍNIO: Contratos Comerciais
#  
#  Este arquivo define conhecimento estruturado sobre
#  contratos comerciais para melhorar a acurácia das respostas.
#  
#  Autor: Equipe Jurídica
#  Última atualização: 16/12/2024
# ═══════════════════════════════════════════════════════════

# ┌─────────────────────────────────────────────────────────┐
# │ SEÇÃO 1: DOMÍNIO                                        │
# │                                                         │
# │ Define o nome do domínio de conhecimento.               │
# │ Este nome aparece nos logs e no trace (--explain).      │
# │                                                         │
# │ Sintaxe: DOMÍNIO: <nome descritivo>                     │
# └─────────────────────────────────────────────────────────┘

DOMÍNIO: Contratos Comerciais

# ┌─────────────────────────────────────────────────────────┐
# │ SEÇÃO 2: FATOS CONHECIDOS                               │
# │                                                         │
# │ Fatos são conhecimentos estruturados do domínio.        │
# │ O DKR usa esses fatos para:                             │
# │   • Gerar intents automáticos                           │
# │   • Validar respostas do LLM                            │
# │   • Fornecer informações corretas nas correções         │
# │                                                         │
# │ Sintaxe:                                                │
# │   A/O <nome> tem criticidade <ALTO|MÉDIO|BAIXO>.        │
# │     Motivo: <justificativa>                             │
# │     Ação: <recomendação>                                │
# │                                                         │
# │ Níveis de Criticidade:                                  │
# │   ALTO  = Crítico, requer atenção imediata              │
# │   MÉDIO = Moderado, verificar caso a caso               │
# │   BAIXO = Seguro, geralmente sem problemas              │
# └─────────────────────────────────────────────────────────┘

─────────────────────────────────────────────────────────────
FATOS CONHECIDOS:
─────────────────────────────────────────────────────────────

# === CLÁUSULAS DE ALTO RISCO ===

A cláusula de exclusividade tem criticidade ALTO.
  Motivo: Impede negociação com outros fornecedores por período extenso.
  Ação: Evitar ou limitar a 6 meses no máximo.

A cláusula de multa rescisória 100% tem criticidade ALTO.
  Motivo: Valor desproporcional que pode inviabilizar rescisão.
  Ação: Negociar para máximo de 20% do valor restante.

A cláusula de renovação automática tem criticidade ALTO.
  Motivo: Pode prender a empresa em contratos indesejados.
  Ação: Exigir notificação prévia de 60 dias.

# === CLÁUSULAS DE MÉDIO RISCO ===

A cláusula de reajuste pelo IGP-M tem criticidade MÉDIO.
  Motivo: Índice pode ter variação alta em períodos de crise.
  Ação: Preferir IPCA ou média ponderada.

A cláusula de foro diferente tem criticidade MÉDIO.
  Motivo: Pode dificultar ações judiciais.
  Ação: Verificar viabilidade antes de aceitar.

# === CLÁUSULAS DE BAIXO RISCO (Seguras) ===

A cláusula de confidencialidade padrão tem criticidade BAIXO.
  Motivo: Cláusula comum e geralmente equilibrada.
  Ação: Aceitar como está na maioria dos casos.

A cláusula de vigência de 12 meses tem criticidade BAIXO.
  Motivo: Período padrão e razoável.
  Ação: Aceitar.

A cláusula de pagamento em 30 dias tem criticidade BAIXO.
  Motivo: Prazo padrão de mercado.
  Ação: Aceitar.

# ┌─────────────────────────────────────────────────────────┐
# │ SEÇÃO 3: PADRÕES DE INTENÇÃO                            │
# │                                                         │
# │ Intents são padrões que identificam o TIPO de pergunta. │
# │ Quando um intent é detectado, o DKR pode:               │
# │   • Expandir a query de busca                           │
# │   • Aplicar regras específicas                          │
# │                                                         │
# │ Sintaxe:                                                │
# │   nome_do_intent:                                       │
# │     - "padrão 1"                                        │
# │     - "padrão 2"                                        │
# │     Resposta deve conter: "termo1", "termo2"            │
# │                                                         │
# │ Dica: Use nomes descritivos em snake_case               │
# └─────────────────────────────────────────────────────────┘

─────────────────────────────────────────────────────────────
PADRÕES DE INTENÇÃO:
─────────────────────────────────────────────────────────────

# Intent para perguntas sobre riscos/problemas
clausulas_perigosas:
  - "mais perigosa"
  - "maior risco"
  - "devo evitar"
  - "preocupar"
  - "cuidado"
  - "problemática"
  Resposta deve conter: "ALTO", "evitar"

# Intent para perguntas sobre cláusulas seguras
clausulas_seguras:
  - "pode aceitar"
  - "segura"
  - "tranquila"
  - "sem problema"
  - "normal"
  - "padrão"
  Resposta deve conter: "BAIXO", "aceitar"

# Intent para perguntas sobre multas
multas:
  - "multa"
  - "rescisão"
  - "penalidade"
  - "quebra de contrato"
  Resposta deve conter: "rescisória", "valor"

# Intent para perguntas sobre prazos
prazos:
  - "prazo"
  - "vigência"
  - "duração"
  - "vencimento"
  - "renovação"
  Resposta deve conter: "meses", "dias"

# ┌─────────────────────────────────────────────────────────┐
# │ SEÇÃO 4: EXPANSÃO DE BUSCA                              │
# │                                                         │
# │ Quando um intent é detectado, esses termos são          │
# │ adicionados à query para melhorar a recuperação         │
# │ de chunks relevantes via RAG.                           │
# │                                                         │
# │ Sintaxe:                                                │
# │   Para "nome_intent", adicionar: "termo1", "termo2"     │
# │                                                         │
# │ Dica: Use termos que aparecem no documento original     │
# └─────────────────────────────────────────────────────────┘

─────────────────────────────────────────────────────────────
EXPANSÃO DE BUSCA:
─────────────────────────────────────────────────────────────

Para "clausulas_perigosas", adicionar: "CLÁUSULA", "RISCO", "ALTO", "evitar"
Para "clausulas_seguras", adicionar: "CLÁUSULA", "padrão", "aceitar"
Para "multas", adicionar: "MULTA", "RESCISÓRIA", "percentual", "valor"
Para "prazos", adicionar: "VIGÊNCIA", "PRAZO", "renovação", "meses"

# ┌─────────────────────────────────────────────────────────┐
# │ SEÇÃO 5: REGRAS DE VALIDAÇÃO                            │
# │                                                         │
# │ Regras definem QUANDO e COMO corrigir respostas do LLM. │
# │ São a parte MAIS IMPORTANTE do arquivo .rules.          │
# │                                                         │
# │ Sintaxe:                                                │
# │   QUANDO usuário pergunta "<padrão>"                    │
# │     E resposta menciona "<termo incorreto>"             │
# │     E resposta NÃO menciona "<termo esperado>"          │
# │   ENTÃO corrigir para:                                  │
# │     <texto de correção>                                 │
# │                                                         │
# │ Condições disponíveis:                                  │
# │   E resposta menciona "..."     → Contém este termo     │
# │   E resposta NÃO menciona "..." → NÃO contém este termo │
# │   OU "..."                      → Alternativa ao padrão │
# │                                                         │
# │ ATENÇÃO:                                                │
# │   • A primeira regra que casar será aplicada            │
# │   • Coloque regras específicas ANTES das genéricas      │
# │   • Use condições negativas para evitar falsos positivos│
# └─────────────────────────────────────────────────────────┘

─────────────────────────────────────────────────────────────
REGRAS DE VALIDAÇÃO:
─────────────────────────────────────────────────────────────

# === REGRA 1: Corrige quando pergunta sobre "cláusula perigosa" ===
# Problema: LLM pode mencionar cláusulas seguras como perigosas
# Solução: Garantir que exclusividade/multa alta sejam citadas

QUANDO usuário pergunta "mais perigosa"
  E resposta menciona "confidencialidade"
  E resposta NÃO menciona "exclusividade"
ENTÃO corrigir para:
  As cláusulas mais perigosas são:
  
  1. **Cláusula de Exclusividade** (criticidade ALTO)
     Impede negociação com outros fornecedores.
     Recomendação: Evitar ou limitar a 6 meses.
  
  2. **Multa Rescisória de 100%** (criticidade ALTO)
     Valor desproporcional que inviabiliza rescisão.
     Recomendação: Negociar para máximo de 20%.
  
  3. **Renovação Automática** (criticidade ALTO)
     Pode prender a empresa em contratos indesejados.
     Recomendação: Exigir notificação prévia de 60 dias.
  
  (Resposta validada pelo sistema de regras de domínio)

# === REGRA 2: Corrige inversão sobre multa ===
# Problema: LLM pode dizer que multa de 100% é aceitável
# Solução: Alertar sobre o risco

QUANDO usuário pergunta "multa"
  E resposta menciona "aceitar"
  E resposta menciona "100%"
ENTÃO corrigir para:
  **ATENÇÃO**: Multa rescisória de 100% tem criticidade **ALTO**.
  
  Esta cláusula é desproporcional e pode inviabilizar a rescisão 
  do contrato mesmo em casos de descumprimento pela outra parte.
  
  **Recomendação**: Negociar para no máximo 20% do valor restante 
  do contrato.
  
  (Resposta validada pelo sistema de regras de domínio)

# === REGRA 3: Corrige quando diz que exclusividade é segura ===
# Problema: LLM pode minimizar o risco de exclusividade
# Solução: Alertar sobre as implicações

QUANDO usuário pergunta "exclusividade"
  E resposta menciona "segura"
ENTÃO corrigir para:
  A **cláusula de exclusividade** tem criticidade **ALTO**.
  
  Esta cláusula impede a empresa de negociar com outros fornecedores 
  durante o período do contrato, limitando opções e poder de barganha.
  
  **Riscos**:
  • Dependência de fornecedor único
  • Impossibilidade de buscar melhores preços
  • Dificuldade em caso de problemas com o fornecedor
  
  **Recomendação**: Evitar ou limitar a no máximo 6 meses.
  
  (Resposta validada pelo sistema de regras de domínio)

# === REGRA 4: Corrige quando pergunta sobre cláusulas seguras ===
# Problema: LLM pode listar cláusulas de alto risco como seguras
# Solução: Garantir que apenas cláusulas BAIXO sejam listadas

QUANDO usuário pergunta "segura"
  E resposta menciona "exclusividade"
ENTÃO corrigir para:
  As cláusulas mais seguras (criticidade BAIXO) são:
  
  1. **Confidencialidade padrão** - Cláusula comum e equilibrada
  2. **Vigência de 12 meses** - Período razoável de mercado
  3. **Pagamento em 30 dias** - Prazo padrão de mercado
  
  **Nota**: Cláusulas como "exclusividade" e "renovação automática" 
  NÃO são consideradas seguras e têm criticidade ALTO.
  
  (Resposta validada pelo sistema de regras de domínio)

# === REGRA 5: Corrige quando lista renovação automática como OK ===

QUANDO usuário pergunta "renovação"
  E resposta menciona "pode aceitar"
  E resposta NÃO menciona "notificação"
ENTÃO corrigir para:
  A **renovação automática** tem criticidade **ALTO**.
  
  Esta cláusula pode prender a empresa em contratos indesejados 
  se não houver controle do calendário de notificações.
  
  **Recomendação**: Só aceitar se houver cláusula de notificação 
  prévia de pelo menos 60 dias antes do vencimento.
  
  (Resposta validada pelo sistema de regras de domínio)

# ┌─────────────────────────────────────────────────────────┐
# │ SEÇÃO 6: SINÔNIMOS                                      │
# │                                                         │
# │ Define sinônimos para melhorar a detecção de termos.    │
# │ Útil quando usuários usam termos diferentes para        │
# │ o mesmo conceito.                                       │
# │                                                         │
# │ Sintaxe:                                                │
# │   "termo" também pode ser: "sinônimo1", "sinônimo2"     │
# │                                                         │
# │ Dica: Inclua termos informais e abreviações             │
# └─────────────────────────────────────────────────────────┘

─────────────────────────────────────────────────────────────
SINÔNIMOS:
─────────────────────────────────────────────────────────────

"perigosa" também pode ser: "arriscada", "problemática", "complicada", "ruim"
"segura" também pode ser: "tranquila", "ok", "normal", "padrão", "boa"
"multa" também pode ser: "penalidade", "sanção", "punição"
"exclusividade" também pode ser: "exclusivo", "único fornecedor"
"rescisão" também pode ser: "quebra", "cancelamento", "término antecipado"
"renovação" também pode ser: "prorrogação", "extensão", "continuidade"
"contrato" também pode ser: "acordo", "instrumento", "documento"

# ═══════════════════════════════════════════════════════════
#  FIM DO ARQUIVO
# ═══════════════════════════════════════════════════════════
```

### Validando o Arquivo

Após criar o arquivo, valide a sintaxe:

```bash
python run.py dkr validate domain_rules/contratos_comerciais.rules
```

Saída esperada:
```
✓ Arquivo válido: domain_rules/contratos_comerciais.rules
  Domínio: Contratos Comerciais
  Fatos: 8
  Intents: 4
  Regras: 5
  Sinônimos: 7
```

### Testando uma Regra

Teste uma regra específica com pergunta e resposta simuladas:

```bash
python run.py dkr test domain_rules/contratos_comerciais.rules \
  -q "Qual a cláusula mais perigosa?" \
  -a "A cláusula de confidencialidade é a mais perigosa do contrato."
```

Saída esperada:
```
--- Teste DKR ---
Pergunta: Qual a cláusula mais perigosa?
Resposta original: A cláusula de confidencialidade é a mais perigosa do contrato.

Intent detectado: clausulas_perigosas (confiança: 85%)
Regra ativada: Regra 1

✓ RESPOSTA CORRIGIDA:
As cláusulas mais perigosas são:

1. **Cláusula de Exclusividade** (criticidade ALTO)
   Impede negociação com outros fornecedores.
   ...
```

### Usando no Q&A

Para usar automaticamente, o arquivo deve ter o mesmo nome do template:

```
Template Q&A:    contratos_comerciais
Arquivo DKR:     domain_rules/contratos_comerciais.rules
```

Depois, execute:

```bash
# Com trace para ver o DKR em ação
python run.py qa contrato.pdf -q "Qual cláusula devo evitar?" --explain

# Sem DKR para comparar
python run.py qa contrato.pdf -q "Qual cláusula devo evitar?" --no-dkr
```

## Guia Prático: Adicionando Novas Regras

Este guia mostra como adicionar novas regras a um arquivo `.rules` existente, com exemplos para cada tipo de seção.

### Onde Adicionar?

Cada tipo de elemento deve ser adicionado na sua seção correspondente:

```
DOMÍNIO: ...                    ← Não modificar

FATOS CONHECIDOS:               ← Adicionar novos fatos aqui
  ... fatos existentes ...
  ... NOVO FATO AQUI ...

PADRÕES DE INTENÇÃO:            ← Adicionar novos intents aqui
  ... intents existentes ...
  ... NOVO INTENT AQUI ...

EXPANSÃO DE BUSCA:              ← Adicionar novas expansões aqui
  ... expansões existentes ...
  ... NOVA EXPANSÃO AQUI ...

NORMALIZAR TERMOS:              ← Adicionar novas normalizações aqui
  ... normalizações existentes ...
  ... NOVA NORMALIZAÇÃO AQUI ...

REGRAS DE VALIDAÇÃO:            ← Adicionar novas regras aqui
  ... regras existentes ...
  ... NOVA REGRA AQUI ...        ← Adicionar ANTES de SINÔNIMOS

SINÔNIMOS:                      ← Adicionar novos sinônimos aqui
  ... sinônimos existentes ...
  ... NOVO SINÔNIMO AQUI ...
```

### Exemplo 1: Adicionar um Novo Fato

**Cenário**: Você quer documentar que a licença CC-BY-4.0 é segura.

**Local**: Seção `FATOS CONHECIDOS`

**Código**:
```
# Adicione após os fatos existentes, antes de "PADRÕES DE INTENÇÃO:"

A licença CC-BY-4.0 tem criticidade BAIXO.
  Motivo: Licença Creative Commons permissiva, apenas requer atribuição.
  Ação: Segura para uso em documentação e mídia.
```

### Exemplo 2: Adicionar uma Normalização de Termo

**Cenário**: O LLM está gerando "GPLA" em vez de "GPL" (alucinação).

**Local**: Seção `NORMALIZAR TERMOS`

**Código**:
```
# Adicione na seção NORMALIZAR TERMOS

"GPLA" corrigir para: "GPL"
"GPLA-2.0" corrigir para: "GPL-2.0"
"GPLA-3.0" corrigir para: "GPL-3.0"
```

**Resultado**: Antes de aplicar as regras de validação, toda ocorrência de "GPLA" será substituída por "GPL" automaticamente.

### Exemplo 3: Adicionar uma Nova Regra de Validação

**Cenário**: Quando o usuário pergunta sobre "diferença entre GPL 2 e GPL 3", o LLM não menciona compatibilidade.

**Local**: Seção `REGRAS DE VALIDAÇÃO` (antes de `SINÔNIMOS`)

**Código**:
```
# Adicione antes da seção SINÔNIMOS

# Regra para perguntas sobre diferenças entre versões GPL
QUANDO usuário pergunta "diferença"
  E resposta menciona "GPL"
  E resposta NÃO menciona "compatibilidade"
ENTÃO corrigir para:
  **Principais diferenças entre GPL-2.0 e GPL-3.0:**
  
  | Aspecto | GPL-2.0 | GPL-3.0 |
  |---------|---------|---------|
  | Criticidade | MÉDIO | BAIXO |
  | Compatibilidade | Baixa | Alta |
  | Cláusula de patentes | Não | Sim |
  
  **GPL-2.0**: Copyleft forte, baixa compatibilidade entre versões.
  
  **GPL-3.0**: Versão moderna com proteções contra restrições de hardware
  e patentes. Melhor compatibilidade com outras licenças.
  
  (Resposta validada pelo sistema de regras de domínio)
```

### Exemplo 4: Adicionar um Novo Intent

**Cenário**: Você quer detectar perguntas sobre "compatibilidade entre licenças".

**Local**: Seção `PADRÕES DE INTENÇÃO`

**Código**:
```
# Adicione na seção PADRÕES DE INTENÇÃO

compatibilidade:
  - "compatível"
  - "compatibilidade"
  - "combinar"
  - "usar junto"
  - "misturar licenças"
  Resposta deve conter: "compatível", "incompatível"
```

### Exemplo 5: Adicionar Expansão de Busca

**Cenário**: Para perguntas sobre compatibilidade, adicionar termos que ajudam o RAG.

**Local**: Seção `EXPANSÃO DE BUSCA`

**Código**:
```
# Adicione na seção EXPANSÃO DE BUSCA

Para "compatibilidade", adicionar: "COMPATIBILIDADE ENTRE", "pode ser combinada", "incompatível"
```

### Exemplo 6: Adicionar Sinônimos

**Cenário**: Usuários podem perguntar sobre "combinar" em vez de "compatibilidade".

**Local**: Seção `SINÔNIMOS`

**Código**:
```
# Adicione na seção SINÔNIMOS

"compatibilidade" também pode ser: "combinar", "misturar", "usar junto", "integrar"
```

### Validar Após Adicionar

Sempre valide o arquivo após fazer alterações:

```bash
python run.py dkr validate domain_rules/licencas_software.rules
```

Saída esperada:
```
✓ Arquivo válido: domain_rules/licencas_software.rules
  Domínio: Licenças de Software Open Source
  Fatos: 11
  Intents: 4
  Regras: 8
  Normalizações: 15
  Sinônimos: 8
```

### Testar a Nova Regra

```bash
# Teste com pergunta e resposta simuladas
python run.py dkr test domain_rules/licencas_software.rules \
  -q "Qual a diferença entre GPL 2 e GPL 3?" \
  -a "A GPL-2.0 é mais antiga que a GPL-3.0."

# Teste em um documento real
python run.py qa documento.pdf -q "Qual a diferença entre GPL 2 e 3?" --explain
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

