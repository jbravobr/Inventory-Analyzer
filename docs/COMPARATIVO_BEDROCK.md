# Análise Comparativa: RAG Enabler vs Amazon Bedrock

> **Versão**: 1.0.0  
> **Data**: Dezembro 2024  
> **Status**: Análise Estratégica  
> **Documento Relacionado**: [PROPOSTA_AWS.md](./PROPOSTA_AWS.md)

---

## Sumário

1. [Visão Geral](#1-visão-geral)
2. [O que é Amazon Bedrock?](#2-o-que-é-amazon-bedrock)
3. [Comparativo Funcional](#3-comparativo-funcional)
4. [Análise de Custos](#4-análise-de-custos)
5. [Vantagens e Desvantagens](#5-vantagens-e-desvantagens)
6. [Matriz de Decisão](#6-matriz-de-decisão)
7. [Arquitetura Híbrida](#7-arquitetura-híbrida)
8. [Recomendações](#8-recomendações)
9. [Conclusão](#9-conclusão)

---

## 1. Visão Geral

### 1.1 Contexto

Este documento analisa se o projeto **RAG Enabler** (self-hosted na AWS) compete com o **Amazon Bedrock**, identificando cenários onde cada abordagem é mais adequada.

### 1.2 Pergunta Central

> *"Dado que a AWS oferece Bedrock com Knowledge Bases gerenciadas, faz sentido manter uma solução self-hosted?"*

### 1.3 Resposta Curta

```
┌─────────────────────────────────────────────────────────────────────────┐
│                                                                         │
│  COMPETEM?                                                              │
│  ├── ✅ SIM, em parte: Ambos resolvem Q&A sobre documentos              │
│  └── ❌ NÃO, em parte: DKR Module é EXCLUSIVO do RAG Enabler           │
│                                                                         │
│  CUSTO:                                                                 │
│  └── Bedrock é MAIS BARATO na maioria dos cenários (< 500K req/mês)    │
│                                                                         │
│  DECISÃO DEPENDE DE:                                                    │
│  ├── Se regras de domínio (DKR) são críticas → RAG Enabler             │
│  ├── Se quer modelos de ponta (Claude 3 Opus) → Bedrock                │
│  └── Se quer o melhor dos dois → Arquitetura Híbrida                   │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 2. O que é Amazon Bedrock?

### 2.1 Definição

**Amazon Bedrock** é um serviço gerenciado da AWS que oferece acesso a modelos fundacionais de IA via API, sem necessidade de gerenciar infraestrutura.

### 2.2 Componentes Principais

| Componente | Descrição |
|------------|-----------|
| **Foundation Models** | Acesso a Claude, Llama, Titan, Mistral, Cohere via API |
| **Knowledge Bases** | RAG gerenciado com indexação automática de documentos |
| **Agents** | Orquestração de tarefas complexas com múltiplas ferramentas |
| **Guardrails** | Filtros de segurança e políticas de conteúdo |
| **Fine-tuning** | Customização de modelos com dados próprios |
| **Model Evaluation** | Avaliação e comparação de modelos |

### 2.3 Modelos Disponíveis (Dezembro 2024)

| Provedor | Modelos | Destaque |
|----------|---------|----------|
| **Anthropic** | Claude 3 (Haiku, Sonnet, Opus) | Melhor para análise e raciocínio |
| **Meta** | Llama 2, Llama 3 (8B, 70B) | Open source, bom custo-benefício |
| **Amazon** | Titan Text, Titan Embeddings | Integração nativa AWS |
| **Mistral** | Mistral 7B, Mixtral 8x7B | Eficiente, multilíngue |
| **Cohere** | Command, Embed | Especializado em enterprise |
| **AI21** | Jurassic-2 | Geração de texto |

### 2.4 Knowledge Bases (RAG Gerenciado)

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    BEDROCK KNOWLEDGE BASES                               │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  ┌─────────────────┐      ┌─────────────────┐      ┌─────────────────┐ │
│  │   Data Source   │      │   Embeddings    │      │  Vector Store   │ │
│  │                 │      │                 │      │                 │ │
│  │  • S3 Bucket    │─────▶│  • Titan Embed  │─────▶│  • OpenSearch   │ │
│  │  • Confluence   │      │  • Cohere       │      │    Serverless   │ │
│  │  • SharePoint   │      │                 │      │  • Pinecone     │ │
│  │  • Web Crawler  │      │                 │      │  • Redis        │ │
│  └─────────────────┘      └─────────────────┘      └─────────────────┘ │
│                                                                         │
│                              │                                          │
│                              ▼                                          │
│                    ┌─────────────────┐                                  │
│                    │   Retrieve &    │                                  │
│                    │    Generate     │                                  │
│                    │                 │                                  │
│                    │  • Claude 3     │                                  │
│                    │  • Llama 3      │                                  │
│                    │  • Titan        │                                  │
│                    └─────────────────┘                                  │
│                                                                         │
│  Limitações:                                                            │
│  • Chunking automático (pouco controle)                                │
│  • Sem regras de domínio customizadas                                  │
│  • Sem normalização de termos                                          │
│  • Sem correção pós-geração                                            │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 3. Comparativo Funcional

### 3.1 Arquitetura

| Aspecto | RAG Enabler (Self-Hosted) | Amazon Bedrock |
|---------|---------------------------|----------------|
| **Infraestrutura** | ECS/EC2 gerenciado por você | 100% serverless/gerenciado |
| **Modelos LLM** | GGUF local (Llama 3.1 8B, TinyLlama) | Claude 3, Llama 3, Titan, Mistral |
| **Tamanho dos modelos** | Até 8B parâmetros (local) | Até 70B+ parâmetros (cloud) |
| **Embeddings** | BERT-Portuguese local | Titan Embeddings, Cohere |
| **Vector Store** | FAISS local ou OpenSearch | OpenSearch Serverless (integrado) |
| **RAG Pipeline** | Pipeline customizado total | Knowledge Bases (gerenciado) |
| **Regras de Domínio** | DKR Module (exclusivo) | ❌ Não existe |
| **OCR** | Tesseract local | Amazon Textract (adicional) |
| **Cache** | Redis/ElastiCache | ❌ Não nativo |

### 3.2 Funcionalidades Detalhadas

| Funcionalidade | RAG Enabler | Bedrock | Vencedor |
|----------------|-------------|---------|----------|
| **Controle do pipeline RAG** | ✅ Total | ⚠️ Limitado | 🏆 RAG Enabler |
| **Regras de domínio (DKR)** | ✅ Completo | ❌ Não existe | 🏆 RAG Enabler |
| **Normalização de termos** | ✅ Customizável | ❌ Não existe | 🏆 RAG Enabler |
| **Correção de respostas** | ✅ DKR rules | ⚠️ Guardrails (básico) | 🏆 RAG Enabler |
| **Embeddings PT-BR** | ✅ BERT-Portuguese | ⚠️ Genérico | 🏆 RAG Enabler |
| **Chunking customizado** | ✅ SemanticSections | ⚠️ Automático | 🏆 RAG Enabler |
| **Qualidade do LLM** | ⚠️ Llama 8B (bom) | ✅ Claude 3 Opus (excelente) | 🏆 Bedrock |
| **Fine-tuning** | ❌ Não | ✅ Sim | 🏆 Bedrock |
| **Agents (orquestração)** | ❌ Não | ✅ Sim | 🏆 Bedrock |
| **Streaming de resposta** | ⚠️ Implementar | ✅ Nativo | 🏆 Bedrock |
| **Histórico/Memória** | ⚠️ Básico | ✅ Nativo | 🏆 Bedrock |
| **Guardrails/Segurança** | ⚠️ Manual | ✅ Nativo | 🏆 Bedrock |
| **Operação offline** | ✅ Possível | ❌ Impossível | 🏆 RAG Enabler |
| **Vendor lock-in** | ✅ Nenhum | ❌ AWS | 🏆 RAG Enabler |
| **Atualizações de modelo** | ⚠️ Manual | ✅ Automático | 🏆 Bedrock |

### 3.3 O Diferencial: DKR Module

O **DKR Module** (Domain Knowledge Rules) é o principal diferencial do RAG Enabler:

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    DKR MODULE - EXCLUSIVO RAG ENABLER                    │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  FUNCIONALIDADES QUE BEDROCK NÃO POSSUI:                               │
│                                                                         │
│  1. FATOS CONHECIDOS                                                    │
│     ┌───────────────────────────────────────────────────────────────┐  │
│     │ A licença AGPL-3.0-only tem criticidade ALTO.                 │  │
│     │   Motivo: Obrigações mesmo sem distribuição (SaaS).           │  │
│     │   Ação: Evitar uso.                                           │  │
│     └───────────────────────────────────────────────────────────────┘  │
│                                                                         │
│  2. NORMALIZAÇÃO DE TERMOS (correção de alucinações)                   │
│     ┌───────────────────────────────────────────────────────────────┐  │
│     │ "GPLA" corrigir para: "GPL"                                   │  │
│     │ "GPLv2" corrigir para: "GPL-2.0"                              │  │
│     │ "Apache License" corrigir para: "Apache-2.0"                  │  │
│     └───────────────────────────────────────────────────────────────┘  │
│                                                                         │
│  3. REGRAS DE VALIDAÇÃO (correção de respostas invertidas)             │
│     ┌───────────────────────────────────────────────────────────────┐  │
│     │ QUANDO usuário pergunta "mais crítica"                        │  │
│     │   E resposta menciona "Apache"                                │  │
│     │   E resposta NÃO menciona "AGPL"                              │  │
│     │ ENTÃO corrigir para:                                          │  │
│     │   "A licença mais crítica é AGPL-3.0-only..."                 │  │
│     └───────────────────────────────────────────────────────────────┘  │
│                                                                         │
│  4. EXPANSÃO DE QUERY (melhora retrieval)                              │
│     ┌───────────────────────────────────────────────────────────────┐  │
│     │ Para "criticidade_alta", adicionar:                           │  │
│     │   "GRAU DE CRITICIDADE", "ALTO", "evitar"                     │  │
│     └───────────────────────────────────────────────────────────────┘  │
│                                                                         │
│  BEDROCK GUARDRAILS vs DKR:                                            │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │ Guardrails: Bloqueia conteúdo (filtro binário)                  │   │
│  │ DKR:        Corrige e melhora conteúdo (transformação)          │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 4. Análise de Custos

### 4.1 RAG Enabler Self-Hosted (Custo Fixo)

| Componente | Configuração | Custo/mês (USD) |
|------------|--------------|-----------------|
| ECS Fargate (API) | 2 tasks x 1 vCPU x 4 GB | ~$70 |
| ECS Fargate (Workers) | 2 tasks x 4 vCPU x 16 GB | ~$210 |
| EFS (modelos) | 20 GB | ~$10 |
| ElastiCache Redis | cache.t3.medium | ~$50 |
| ALB + S3 + CloudWatch | - | ~$50 |
| **TOTAL FIXO** | | **~$390/mês** |

> **Custo por request adicional**: ~$0 (após custo fixo)

### 4.2 Amazon Bedrock (Custo Variável)

#### Preços de Modelos (por 1.000 tokens)

| Modelo | Input | Output | Qualidade |
|--------|-------|--------|-----------|
| **Claude 3 Haiku** | $0.00025 | $0.00125 | Boa |
| **Claude 3 Sonnet** | $0.003 | $0.015 | Muito Boa |
| **Claude 3 Opus** | $0.015 | $0.075 | Excelente |
| **Llama 3 8B** | $0.0003 | $0.0006 | Boa |
| **Llama 3 70B** | $0.00265 | $0.0035 | Muito Boa |
| **Titan Text Express** | $0.0002 | $0.0006 | Básica |
| **Titan Embeddings** | $0.0001 | - | N/A |

#### Custo Knowledge Bases

| Componente | Custo |
|------------|-------|
| OpenSearch Serverless | ~$0.24/OCU-hora (mínimo 2 OCUs = $350/mês) |
| Armazenamento | ~$0.024/GB-mês |
| Ingestão | $0.10/1000 objetos |

> ⚠️ **OpenSearch Serverless tem custo mínimo alto** (~$350/mês)

### 4.3 Comparativo por Volume de Requests

#### Premissas
- Request médio: 500 tokens input + 300 tokens output
- Embeddings: 1 documento = 10 chunks = 10 embeddings
- Todos os requests usam RAG (Knowledge Base)

#### Cenário A: 10.000 requests/mês (Uso Moderado)

| Item | RAG Enabler | Bedrock (Haiku) | Bedrock (Llama 3 8B) |
|------|-------------|-----------------|----------------------|
| Infra fixa | $390 | $0 | $0 |
| Knowledge Base | $0 | $175* | $175* |
| Embeddings | $0 | $1 | $1 |
| LLM | $0 | $15 | $9 |
| **TOTAL** | **$390** | **$191** | **$185** |
| **Custo/request** | $0.039 | $0.019 | $0.018 |

*Usando OpenSearch com configuração mínima otimizada

> 🏆 **Bedrock é ~2x mais barato** para uso moderado

#### Cenário B: 50.000 requests/mês (Uso Alto)

| Item | RAG Enabler | Bedrock (Haiku) | Bedrock (Llama 3 8B) |
|------|-------------|-----------------|----------------------|
| Infra fixa | $450 | $0 | $0 |
| Knowledge Base | $0 | $175 | $175 |
| Embeddings | $0 | $5 | $5 |
| LLM | $0 | $75 | $45 |
| **TOTAL** | **$450** | **$255** | **$225** |
| **Custo/request** | $0.009 | $0.005 | $0.004 |

> 🏆 **Bedrock continua mais barato**

#### Cenário C: 200.000 requests/mês (Uso Muito Alto)

| Item | RAG Enabler | Bedrock (Haiku) | Bedrock (Llama 3 8B) |
|------|-------------|-----------------|----------------------|
| Infra fixa | $600 | $0 | $0 |
| Knowledge Base | $0 | $200 | $200 |
| Embeddings | $0 | $20 | $20 |
| LLM | $0 | $300 | $180 |
| **TOTAL** | **$600** | **$520** | **$400** |
| **Custo/request** | $0.003 | $0.0026 | $0.002 |

> 🏆 **Bedrock ainda mais barato**

#### Cenário D: 500.000 requests/mês (Enterprise)

| Item | RAG Enabler | Bedrock (Haiku) | Bedrock (Llama 3 8B) |
|------|-------------|-----------------|----------------------|
| Infra fixa | $900 | $0 | $0 |
| Knowledge Base | $0 | $300 | $300 |
| Embeddings | $0 | $50 | $50 |
| LLM | $0 | $750 | $450 |
| **TOTAL** | **$900** | **$1,100** | **$800** |
| **Custo/request** | $0.0018 | $0.0022 | $0.0016 |

> ⚖️ **Empate técnico** - RAG Enabler começa a competir

#### Cenário E: 1.000.000 requests/mês (Enterprise+)

| Item | RAG Enabler | Bedrock (Haiku) | Bedrock (Llama 3 8B) |
|------|-------------|-----------------|----------------------|
| Infra fixa | $1,500 | $0 | $0 |
| Knowledge Base | $0 | $400 | $400 |
| Embeddings | $0 | $100 | $100 |
| LLM | $0 | $1,500 | $900 |
| **TOTAL** | **$1,500** | **$2,000** | **$1,400** |
| **Custo/request** | $0.0015 | $0.002 | $0.0014 |

> 🏆 **RAG Enabler ganha** vs Claude Haiku, empata com Llama

### 4.4 Gráfico de Custo vs Volume

```
Custo Mensal (USD)
│
│                                              ╱ Bedrock (Claude Haiku)
│                                           ╱
│                                        ╱
│                                     ╱
│                                  ╱        ╱ Bedrock (Llama 3 8B)
│                               ╱        ╱
│                            ╱        ╱
│                         ╱        ╱
│                      ╱        ╱
│                   ╱        ╱
│                ╱        ╱
│             ╱        ╱
│          ╱────────────────────────────────── RAG Enabler
│       ╱     (custo fixo, cresce devagar)
│    ╱
│ ╱
├───────────────────────────────────────────────────────────────▶
0      100K     200K     300K     400K     500K     Requests/mês
                     │
                     └── PONTO DE EQUILÍBRIO (~400-500K req/mês)
```

### 4.5 Resumo de Custos

| Volume | Mais Barato | Diferença |
|--------|-------------|-----------|
| **< 50K req/mês** | 🏆 Bedrock | 40-50% mais barato |
| **50K - 200K req/mês** | 🏆 Bedrock | 20-30% mais barato |
| **200K - 500K req/mês** | ⚖️ Empate | Depende do modelo |
| **> 500K req/mês** | 🏆 RAG Enabler | 10-25% mais barato |

---

## 5. Vantagens e Desvantagens

### 5.1 RAG Enabler Self-Hosted

#### ✅ Vantagens

| Vantagem | Descrição | Impacto |
|----------|-----------|---------|
| **DKR Module** | Regras de domínio exclusivas | 🔴 Crítico |
| **Normalização de termos** | Corrige alucinações automaticamente | 🔴 Crítico |
| **Controle total** | Pipeline RAG 100% customizável | 🟡 Alto |
| **Embeddings PT-BR** | BERT-Portuguese otimizado | 🟡 Alto |
| **Sem vendor lock-in** | Portável para qualquer cloud | 🟡 Alto |
| **Offline possível** | Funciona air-gapped | 🟢 Médio |
| **Custo previsível** | Sem surpresas na fatura | 🟢 Médio |
| **Dados na VPC** | 100% controle de dados | 🟡 Alto |

#### ❌ Desvantagens

| Desvantagem | Descrição | Impacto |
|-------------|-----------|---------|
| **Custo fixo** | Paga mesmo sem uso | 🟡 Alto |
| **Manutenção** | Requer equipe DevOps | 🟡 Alto |
| **Modelos limitados** | Até 8B parâmetros (local) | 🟡 Alto |
| **Cold start** | Scale-up demora | 🟢 Médio |
| **Atualizações manuais** | Modelos não atualizam sozinhos | 🟢 Médio |
| **Sem fine-tuning** | Não suporta customização de modelo | 🟢 Médio |
| **Sem agents** | Não tem orquestração nativa | 🟢 Médio |

### 5.2 Amazon Bedrock

#### ✅ Vantagens

| Vantagem | Descrição | Impacto |
|----------|-----------|---------|
| **Zero infraestrutura** | 100% gerenciado | 🔴 Crítico |
| **Modelos de ponta** | Claude 3 Opus, Llama 70B | 🔴 Crítico |
| **Pay-per-use** | Só paga pelo que usar | 🟡 Alto |
| **Fine-tuning** | Customiza modelos | 🟡 Alto |
| **Agents** | Orquestração complexa | 🟡 Alto |
| **Streaming** | Respostas em tempo real | 🟢 Médio |
| **SLA AWS** | Garantia de disponibilidade | 🟢 Médio |
| **Atualizações automáticas** | Modelos sempre atualizados | 🟢 Médio |

#### ❌ Desvantagens

| Desvantagem | Descrição | Impacto |
|-------------|-----------|---------|
| **Sem DKR** | Não tem regras de domínio | 🔴 Crítico* |
| **Sem normalização** | Não corrige alucinações | 🔴 Crítico* |
| **Custo variável** | Pode explodir com volume | 🟡 Alto |
| **Vendor lock-in** | Difícil migrar | 🟡 Alto |
| **Knowledge Base limitado** | Pouco controle no RAG | 🟡 Alto |
| **Latência de rede** | Depende de internet | 🟢 Médio |
| **Dados na AWS** | Processados externamente | 🟢 Médio |

*Crítico apenas se regras de domínio forem necessárias

---

## 6. Matriz de Decisão

### 6.1 Árvore de Decisão

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         ÁRVORE DE DECISÃO                                │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  Regras de domínio (DKR) são CRÍTICAS?                                 │
│  │                                                                      │
│  ├── SIM ──────────────────────────────────────────┐                   │
│  │                                                  │                   │
│  │   Precisa de modelos de ponta (Claude 3 Opus)?  │                   │
│  │   │                                              │                   │
│  │   ├── SIM ──▶ HÍBRIDO (Bedrock + DKR)          │                   │
│  │   │                                              │                   │
│  │   └── NÃO ──▶ RAG ENABLER SELF-HOSTED          │                   │
│  │                                                  │                   │
│  └── NÃO ──────────────────────────────────────────┘                   │
│      │                                                                  │
│      Volume > 500K requests/mês?                                       │
│      │                                                                  │
│      ├── SIM ──▶ RAG ENABLER (custo-benefício)                        │
│      │                                                                  │
│      └── NÃO                                                           │
│          │                                                              │
│          Precisa funcionar offline/air-gapped?                         │
│          │                                                              │
│          ├── SIM ──▶ RAG ENABLER SELF-HOSTED                          │
│          │                                                              │
│          └── NÃO ──▶ AMAZON BEDROCK                                   │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

### 6.2 Cenários de Uso

#### Use RAG Enabler Self-Hosted quando:

```
┌─────────────────────────────────────────────────────────────────────────┐
│  ✅ ESCOLHA RAG ENABLER SELF-HOSTED                                     │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  • Regras de domínio (DKR) são obrigatórias                            │
│  • Normalização de termos é crítica                                     │
│  • Compliance exige dados 100% na sua VPC                              │
│  • Volume > 500K requests/mês (custo-benefício)                        │
│  • Precisa funcionar offline/air-gapped                                │
│  • Quer evitar vendor lock-in                                          │
│  • Tem equipe DevOps/MLOps disponível                                  │
│  • Pipeline RAG precisa de customização profunda                       │
│  • Embeddings em português são críticos                                │
│                                                                         │
│  Exemplos de casos de uso:                                              │
│  • Análise de contratos com terminologia específica                    │
│  • Documentos jurídicos com normas próprias                            │
│  • Compliance/auditoria com regras rígidas                             │
│  • Ambiente classificado/air-gapped                                     │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

#### Use Amazon Bedrock quando:

```
┌─────────────────────────────────────────────────────────────────────────┐
│  ✅ ESCOLHA AMAZON BEDROCK                                              │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  • Quer começar rápido (time-to-market)                                │
│  • Não tem equipe DevOps/MLOps                                         │
│  • Volume < 200K requests/mês                                          │
│  • Precisa de modelos de ponta (Claude 3 Opus)                         │
│  • Quer fine-tuning de modelos                                         │
│  • Precisa de Agents para orquestração                                 │
│  • Custo variável é aceitável                                          │
│  • Não precisa de regras de domínio customizadas                       │
│  • Streaming de respostas é importante                                 │
│                                                                         │
│  Exemplos de casos de uso:                                              │
│  • Chatbot genérico de atendimento                                     │
│  • Q&A sobre documentação de produto                                   │
│  • Assistente de código/desenvolvimento                                │
│  • Análise de sentimento genérica                                      │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

#### Use Arquitetura Híbrida quando:

```
┌─────────────────────────────────────────────────────────────────────────┐
│  ✅ ESCOLHA ARQUITETURA HÍBRIDA                                         │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  • Quer qualidade do Claude + regras do DKR                            │
│  • Precisa do melhor dos dois mundos                                   │
│  • Volume moderado (custo híbrido aceitável)                           │
│  • Quer flexibilidade para evoluir                                     │
│  • Regras de domínio + modelos de ponta                                │
│                                                                         │
│  Exemplos de casos de uso:                                              │
│  • Análise de licenças com correção de termos                          │
│  • Documentos jurídicos com IA de ponta                                │
│  • Compliance com respostas de alta qualidade                          │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 7. Arquitetura Híbrida

### 7.1 Conceito

Combinar o **melhor do Bedrock** (modelos de ponta, zero infraestrutura) com o **melhor do RAG Enabler** (DKR, normalização, correção).

### 7.2 Diagrama

```
┌─────────────────────────────────────────────────────────────────────────┐
│                     ARQUITETURA HÍBRIDA                                  │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │                         API Gateway                              │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                    │                                     │
│                                    ▼                                     │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │              DKR ORCHESTRATOR (Lambda/ECS Leve)                  │   │
│  │                                                                  │   │
│  │  1. Recebe pergunta                                             │   │
│  │  2. Carrega regras .rules do domínio                            │   │
│  │  3. Detecta intenção (DKR)                                      │   │
│  │  4. Expande query (DKR)                                         │   │
│  │  5. Chama Bedrock ────────────────────────────────────────┐     │   │
│  │  6. Recebe resposta ◄─────────────────────────────────────┤     │   │
│  │  7. Aplica normalização de termos (DKR)                   │     │   │
│  │  8. Valida resposta contra regras (DKR)                   │     │   │
│  │  9. Corrige se necessário (DKR)                           │     │   │
│  │  10. Retorna resposta final                               │     │   │
│  │                                                            │     │   │
│  └────────────────────────────────────────────────────────────┼─────┘   │
│                                                               │         │
│                         ┌─────────────────────────────────────┘         │
│                         │                                               │
│                         ▼                                               │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │                      AMAZON BEDROCK                              │   │
│  │                                                                  │   │
│  │  ┌─────────────────┐      ┌─────────────────┐                   │   │
│  │  │ Knowledge Base  │      │    Claude 3     │                   │   │
│  │  │                 │─────▶│    Haiku        │                   │   │
│  │  │  • S3 Documents │      │                 │                   │   │
│  │  │  • OpenSearch   │      │  Ou Llama 3     │                   │   │
│  │  │  • Embeddings   │      │  Ou Titan       │                   │   │
│  │  └─────────────────┘      └─────────────────┘                   │   │
│  │                                                                  │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                                                         │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │                         STORAGE                                  │   │
│  │                                                                  │   │
│  │  ┌─────────────────┐      ┌─────────────────┐                   │   │
│  │  │   S3 Bucket     │      │   DynamoDB      │                   │   │
│  │  │   (rules)       │      │   (cache DKR)   │                   │   │
│  │  │                 │      │                 │                   │   │
│  │  │  • .rules files │      │  • Responses    │                   │   │
│  │  │  • Configs      │      │  • Metrics      │                   │   │
│  │  └─────────────────┘      └─────────────────┘                   │   │
│  │                                                                  │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

### 7.3 Fluxo de Processamento

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    FLUXO HÍBRIDO DETALHADO                               │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  USUÁRIO                                                                │
│     │                                                                   │
│     │ "Qual é a licença mais crítica?"                                 │
│     ▼                                                                   │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │                    DKR ORCHESTRATOR                              │   │
│  │                                                                  │   │
│  │  1. DETECTAR INTENÇÃO                                           │   │
│  │     └─▶ Intent: "criticidade_alta"                              │   │
│  │                                                                  │   │
│  │  2. EXPANDIR QUERY                                               │   │
│  │     └─▶ "licença mais crítica GRAU DE CRITICIDADE ALTO evitar"  │   │
│  │                                                                  │   │
│  └──────────────────────────────┬──────────────────────────────────┘   │
│                                 │                                       │
│                                 ▼                                       │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │                    AMAZON BEDROCK                                │   │
│  │                                                                  │   │
│  │  3. RETRIEVE (Knowledge Base)                                   │   │
│  │     └─▶ Chunks relevantes sobre licenças                        │   │
│  │                                                                  │   │
│  │  4. GENERATE (Claude 3 Haiku)                                   │   │
│  │     └─▶ "A licença Apache 2.0 é muito permissiva..."            │   │
│  │         (resposta potencialmente incorreta)                      │   │
│  │                                                                  │   │
│  └──────────────────────────────┬──────────────────────────────────┘   │
│                                 │                                       │
│                                 ▼                                       │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │                    DKR ORCHESTRATOR                              │   │
│  │                                                                  │   │
│  │  5. NORMALIZAR TERMOS                                           │   │
│  │     └─▶ (nenhuma correção necessária)                           │   │
│  │                                                                  │   │
│  │  6. VALIDAR RESPOSTA                                            │   │
│  │     └─▶ ⚠️ Regra ativada:                                       │   │
│  │         "pergunta 'mais crítica' + resposta 'Apache'"           │   │
│  │         "resposta NÃO menciona 'AGPL'"                          │   │
│  │                                                                  │   │
│  │  7. CORRIGIR RESPOSTA                                           │   │
│  │     └─▶ "A licença mais crítica é AGPL-3.0-only..."             │   │
│  │                                                                  │   │
│  └──────────────────────────────┬──────────────────────────────────┘   │
│                                 │                                       │
│                                 ▼                                       │
│  USUÁRIO                                                                │
│     │                                                                   │
│     │ "A licença mais crítica é AGPL-3.0-only com                      │
│     │  grau de criticidade ALTO..."                                    │
│     │  (resposta corrigida pelo DKR)                                   │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

### 7.4 Custo da Arquitetura Híbrida

| Volume | Só Bedrock | Híbrido | Diferença |
|--------|------------|---------|-----------|
| 10K req/mês | $191 | $210 | +$19 (DKR Lambda) |
| 50K req/mês | $255 | $280 | +$25 |
| 100K req/mês | $355 | $390 | +$35 |

> ⚠️ Custo adicional de ~10-15% para ter DKR, mas com qualidade do Claude

---

## 8. Recomendações

### 8.1 Recomendação por Perfil

| Perfil | Recomendação | Justificativa |
|--------|--------------|---------------|
| **Startup/MVP** | Bedrock | Time-to-market, sem DevOps |
| **PME (< 50K req)** | Bedrock | Custo menor, zero infra |
| **Enterprise (> 500K req)** | RAG Enabler | Custo-benefício, controle |
| **Compliance rígido** | RAG Enabler | Dados na VPC, auditoria |
| **Air-gapped/Offline** | RAG Enabler | Único que funciona |
| **Regras de domínio críticas** | RAG Enabler ou Híbrido | DKR exclusivo |
| **Qualidade máxima + regras** | Híbrido | Melhor dos dois mundos |

### 8.2 Roadmap Sugerido

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         ROADMAP SUGERIDO                                 │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  FASE 1: MVP com Bedrock (Semanas 1-2)                                 │
│  ├── Configurar Knowledge Base                                         │
│  ├── Integrar Claude 3 Haiku                                           │
│  ├── API básica                                                         │
│  └── Validar funcionalidade base                                       │
│                                                                         │
│  FASE 2: Adicionar DKR (Semanas 3-4)                                   │
│  ├── Implementar DKR Orchestrator (Lambda)                             │
│  ├── Migrar regras .rules existentes                                   │
│  ├── Integrar DKR no fluxo Bedrock                                     │
│  └── Testar correções                                                   │
│                                                                         │
│  FASE 3: Otimização (Semanas 5-6)                                      │
│  ├── Cache de respostas                                                 │
│  ├── Métricas de uso DKR                                               │
│  ├── Ajuste fino de regras                                             │
│  └── Documentação                                                       │
│                                                                         │
│  FASE 4: Avaliação (Mês 2)                                             │
│  ├── Analisar custos reais                                             │
│  ├── Avaliar se volume justifica self-hosted                           │
│  └── Decidir próximos passos                                           │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 9. Conclusão

### 9.1 Resumo Executivo

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         RESUMO EXECUTIVO                                 │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  COMPETEM?                                                              │
│  ├── SIM: Ambos resolvem Q&A sobre documentos                          │
│  └── NÃO: DKR Module é exclusivo do RAG Enabler                        │
│                                                                         │
│  CUSTO:                                                                 │
│  ├── Bedrock é mais barato para < 500K req/mês                         │
│  ├── RAG Enabler ganha em volumes muito altos                          │
│  └── Híbrido adiciona ~10-15% ao custo do Bedrock                      │
│                                                                         │
│  QUALIDADE:                                                             │
│  ├── Bedrock tem modelos superiores (Claude 3 Opus)                    │
│  ├── RAG Enabler tem DKR (correção de erros)                           │
│  └── Híbrido combina qualidade + correção                              │
│                                                                         │
│  RECOMENDAÇÃO FINAL:                                                    │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │                                                                  │   │
│  │  Se DKR é CRÍTICO para o negócio:                               │   │
│  │  └── Arquitetura HÍBRIDA (Bedrock + DKR Layer)                  │   │
│  │                                                                  │   │
│  │  Se DKR é NICE-TO-HAVE:                                         │   │
│  │  └── Amazon Bedrock puro                                        │   │
│  │                                                                  │   │
│  │  Se volume > 500K req/mês E DKR crítico:                        │   │
│  │  └── RAG Enabler Self-Hosted completo                           │   │
│  │                                                                  │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

### 9.2 Próximos Passos

1. **Definir** se DKR é crítico para o caso de uso
2. **Estimar** volume mensal de requests
3. **Escolher** arquitetura (Bedrock / Self-hosted / Híbrida)
4. **Implementar** MVP conforme roadmap
5. **Avaliar** e iterar

---

## Histórico de Revisões

| Versão | Data | Autor | Descrição |
|--------|------|-------|-----------|
| 1.0.0 | Dez 2024 | Equipe de Arquitetura | Versão inicial |

---

*Documento gerado como parte do projeto RAG Enabler Platform*

