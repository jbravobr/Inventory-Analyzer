# Proposta de Arquitetura AWS - RAG Enabler Platform

> **Versão**: 1.0.0  
> **Data**: Dezembro 2024  
> **Status**: Proposta Técnica  
> **Autor**: Equipe de Arquitetura

---

## Sumário

1. [Visão Geral](#1-visão-geral)
2. [Requisitos de Recursos](#2-requisitos-de-recursos)
3. [Análise de Opções](#3-análise-de-opções)
4. [Arquitetura Recomendada](#4-arquitetura-recomendada)
5. [Design da API](#5-design-da-api)
6. [Modificações Necessárias](#6-modificações-necessárias)
7. [Infraestrutura como Código](#7-infraestrutura-como-código)
8. [Estimativa de Custos](#8-estimativa-de-custos)
9. [Plano de Implementação](#9-plano-de-implementação)
10. [Considerações de Segurança](#10-considerações-de-segurança)
11. [Monitoramento e Observabilidade](#11-monitoramento-e-observabilidade)
12. [Apêndices](#12-apêndices)

---

## 1. Visão Geral

### 1.1 Objetivo

Disponibilizar o projeto RAG (Retrieval-Augmented Generation) como uma **peça central de consumo via API** na AWS, funcionando como um **enabler** de apoio para operações com LLM dentro de um ecossistema de aplicações em conta privada.

### 1.2 Escopo

O sistema deve:
- Processar documentos PDF (OCR, chunking, indexação)
- Responder perguntas sobre documentos usando LLM local
- Aplicar regras de domínio (DKR) para validação e correção
- Expor APIs REST para integração com outras aplicações
- Operar 100% dentro da VPC privada da AWS

### 1.3 Princípios Arquiteturais

| Princípio | Descrição |
|-----------|-----------|
| **Serverless-first** | Usar serviços gerenciados sempre que possível |
| **Escalabilidade** | Auto-scaling baseado em demanda |
| **Resiliência** | Tolerância a falhas em todos os componentes |
| **Segurança** | Zero trust, tráfego interno via VPC |
| **Custo-efetivo** | Otimização de recursos (Spot, Reserved) |
| **Observabilidade** | Logs, métricas e traces centralizados |

---

## 2. Requisitos de Recursos

### 2.1 Componentes do Sistema

| Componente | Tamanho em Disco | RAM Necessária | Tempo de Processamento |
|------------|------------------|----------------|------------------------|
| **Llama 3.1 8B** | 4.7 GB | ~8 GB | 20-40s por resposta |
| **Embeddings BERT** | ~500 MB | ~2 GB | 1-5s por documento |
| **TinyLlama** | 670 MB | ~2 GB | 5-15s por resposta |
| **Tesseract OCR** | ~100 MB | ~500 MB | 2-10s por página |
| **Código + Deps** | ~500 MB | ~500 MB | N/A |
| **spaCy PT** | ~500 MB | ~1 GB | Inicialização |

### 2.2 Totais por Configuração

| Configuração | Disco Total | RAM Total | Tempo/Request |
|--------------|-------------|-----------|---------------|
| **Com Llama 3.1 8B** | ~6.5 GB | ~12 GB | 30-60s |
| **Com TinyLlama** | ~2.3 GB | ~6 GB | 10-30s |

### 2.3 Requisitos Não-Funcionais

| Requisito | Especificação |
|-----------|---------------|
| **Disponibilidade** | 99.5% (permite janelas de manutenção) |
| **Latência (P95)** | < 60s para perguntas, < 5min para indexação |
| **Throughput** | 100 requests/minuto (pico) |
| **Retenção de dados** | 90 dias para documentos processados |
| **Compliance** | Dados não saem da região AWS configurada |

---

## 3. Análise de Opções

### 3.1 Por que Lambda NÃO é Ideal

O AWS Lambda possui limitações que inviabilizam seu uso como componente principal:

| Limite Lambda | Valor | Impacto no Projeto |
|---------------|-------|-------------------|
| **Package size (zip)** | 250 MB | ❌ Modelos são ~5 GB |
| **Container image** | 10 GB | ⚠️ Apertado com Llama 3.1 |
| **Ephemeral storage** | 10 GB | ⚠️ Limite para modelos |
| **Memory** | 10 GB | ❌ Llama 3.1 precisa de ~12 GB |
| **Timeout** | 15 min | ✅ OK para maioria |
| **Cold start** | Variável | ❌ 30-60s com modelos grandes |

#### Problemas Específicos

```
┌─────────────────────────────────────────────────────────────────────┐
│  LIMITAÇÕES DO LAMBDA PARA ESTE PROJETO                             │
├─────────────────────────────────────────────────────────────────────┤
│  1. COLD START SEVERO                                               │
│     - Carregar modelo de 4.7 GB = 30-60 segundos                    │
│     - Cada nova instância = nova carga do modelo                    │
│     - Custo: $0.0000166667/GB-segundo (10 GB = caro)               │
│                                                                     │
│  2. MEMÓRIA INSUFICIENTE                                            │
│     - Lambda max: 10 GB                                             │
│     - Llama 3.1 8B precisa: ~12 GB                                  │
│     - Solução: usar TinyLlama (qualidade inferior)                  │
│                                                                     │
│  3. STORAGE LIMITADO                                                │
│     - /tmp max: 10 GB                                               │
│     - Modelos + deps: ~6.5 GB                                       │
│     - PDFs processados: variável                                    │
│                                                                     │
│  4. CUSTO ELEVADO                                                   │
│     - 10 GB RAM x 30s = $0.005/request                             │
│     - 10.000 requests/mês = $50 só de Lambda                       │
│     - + S3 + API Gateway + NAT = muito mais                        │
└─────────────────────────────────────────────────────────────────────┘
```

### 3.2 Opções Avaliadas

#### Opção A: ECS Fargate (Serverless Containers)

```
┌─────────────────────────────────────────────────────────────────────┐
│                         API Gateway                                  │
│                              │                                       │
│                              ▼                                       │
│  ┌────────────────────────────────────────────────────────────────┐ │
│  │                    Application Load Balancer                    │ │
│  └────────────────────────────────────────────────────────────────┘ │
│                              │                                       │
│          ┌───────────────────┼───────────────────┐                  │
│          ▼                   ▼                   ▼                  │
│  ┌──────────────┐   ┌──────────────┐   ┌──────────────┐            │
│  │  ECS Task    │   │  ECS Task    │   │  ECS Task    │            │
│  │  (Fargate)   │   │  (Fargate)   │   │  (Fargate)   │            │
│  │              │   │              │   │              │            │
│  │ - RAG API    │   │ - RAG API    │   │ - RAG API    │            │
│  │ - LLM        │   │ - LLM        │   │ - LLM        │            │
│  │ - Embeddings │   │ - Embeddings │   │ - Embeddings │            │
│  │ - OCR        │   │ - OCR        │   │ - OCR        │            │
│  └──────────────┘   └──────────────┘   └──────────────┘            │
│          │                   │                   │                  │
│          └───────────────────┴───────────────────┘                  │
│                              │                                       │
│                              ▼                                       │
│  ┌────────────────────────────────────────────────────────────────┐ │
│  │                        EFS / S3                                 │ │
│  │              (Modelos compartilhados + Cache)                   │ │
│  └────────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────┘
```

| Aspecto | Configuração | Justificativa |
|---------|--------------|---------------|
| **vCPU** | 4 vCPU | Inferência LLM é CPU-bound |
| **Memory** | 16 GB | Llama 3.1 + overhead |
| **Storage** | EFS (elastic) | Modelos compartilhados |
| **Auto Scaling** | 1-10 tasks | Baseado em requisições |
| **Spot Instances** | Sim (70% economia) | Tolerância a interrupções |

**Custo estimado**: ~$150-300/mês (uso moderado)

**Prós**: Simples, serverless, auto-scaling  
**Contras**: Custo pode escalar, cold start em scale-up

---

#### Opção B: ECS EC2 com GPU

```
┌─────────────────────────────────────────────────────────────────────┐
│                         API Gateway                                  │
│                              │                                       │
│                              ▼                                       │
│  ┌────────────────────────────────────────────────────────────────┐ │
│  │                    Application Load Balancer                    │ │
│  └────────────────────────────────────────────────────────────────┘ │
│                              │                                       │
│                              ▼                                       │
│  ┌────────────────────────────────────────────────────────────────┐ │
│  │                     ECS Cluster (EC2)                           │ │
│  │  ┌──────────────────────────────────────────────────────────┐  │ │
│  │  │            g4dn.xlarge (T4 GPU, 16 GB RAM)               │  │ │
│  │  │                                                          │  │ │
│  │  │   ┌────────────┐  ┌────────────┐  ┌────────────┐        │  │ │
│  │  │   │ Container  │  │ Container  │  │ Container  │        │  │ │
│  │  │   │ RAG API    │  │ LLM (GPU)  │  │ Embeddings │        │  │ │
│  │  │   └────────────┘  └────────────┘  └────────────┘        │  │ │
│  │  └──────────────────────────────────────────────────────────┘  │ │
│  └────────────────────────────────────────────────────────────────┘ │
│                              │                                       │
│                              ▼                                       │
│  ┌────────────────────────────────────────────────────────────────┐ │
│  │                      S3 + ElastiCache                           │ │
│  │              (Modelos + Cache de Respostas)                     │ │
│  └────────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────┘
```

**Performance com GPU**:

| Operação | CPU (4 vCPU) | GPU (T4) | Melhoria |
|----------|--------------|----------|----------|
| Llama 3.1 8B | 20-40s | 2-5s | **10x** |
| Embeddings | 1-5s | 0.2-1s | **5x** |
| OCR | 2-10s | 2-10s | Igual (CPU) |

**Custo estimado**: ~$300-600/mês (g4dn.xlarge on-demand)

**Prós**: Performance 10x melhor, custo previsível  
**Contras**: Gerenciamento de EC2, menos elástico

---

#### Opção C: Arquitetura Híbrida (RECOMENDADA)

```
┌─────────────────────────────────────────────────────────────────────────┐
│                                                                         │
│  ┌───────────────────────────────────────────────────────────────────┐  │
│  │                         API Gateway                                │  │
│  │                    (REST + WebSocket)                              │  │
│  └───────────────────────────────────────────────────────────────────┘  │
│                                    │                                     │
│            ┌───────────────────────┼───────────────────────┐            │
│            │                       │                       │            │
│            ▼                       ▼                       ▼            │
│  ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐     │
│  │   Lambda        │    │   Lambda        │    │   Lambda        │     │
│  │   API Router    │    │   DKR Engine    │    │   Cache Manager │     │
│  │   (leve)        │    │   (regras)      │    │   (leve)        │     │
│  └────────┬────────┘    └─────────────────┘    └────────┬────────┘     │
│           │                                              │              │
│           │              ┌──────────────┐               │              │
│           └──────────────►   SQS Queue  ◄───────────────┘              │
│                          │  (async jobs) │                              │
│                          └───────┬───────┘                              │
│                                  │                                       │
│                                  ▼                                       │
│  ┌───────────────────────────────────────────────────────────────────┐  │
│  │                        ECS Fargate                                 │  │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐               │  │
│  │  │   OCR       │  │  Embeddings │  │    LLM      │               │  │
│  │  │  Service    │  │   Service   │  │   Service   │               │  │
│  │  │  (CPU)      │  │   (CPU/GPU) │  │   (GPU)     │               │  │
│  │  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘               │  │
│  └─────────┼────────────────┼────────────────┼───────────────────────┘  │
│            │                │                │                          │
│            └────────────────┴────────────────┘                          │
│                             │                                            │
│            ┌────────────────┴────────────────┐                          │
│            ▼                                 ▼                          │
│  ┌─────────────────┐              ┌─────────────────┐                   │
│  │       S3        │              │   ElastiCache   │                   │
│  │  - PDFs         │              │   (Redis)       │                   │
│  │  - Modelos      │              │   - Q&A Cache   │                   │
│  │  - Resultados   │              │   - Embeddings  │                   │
│  └─────────────────┘              └─────────────────┘                   │
│                                                                         │
│  ┌───────────────────────────────────────────────────────────────────┐  │
│  │                        EFS (Elastic File System)                   │  │
│  │              Modelos compartilhados entre containers               │  │
│  └───────────────────────────────────────────────────────────────────┘  │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

**Prós**: Otimização por componente, escalabilidade granular, custo otimizado  
**Contras**: Maior complexidade operacional

---

### 3.3 Matriz de Decisão

| Critério | Peso | Opção A | Opção B | Opção C |
|----------|------|---------|---------|---------|
| **Performance** | 25% | 3 | 5 | 4 |
| **Custo** | 25% | 4 | 2 | 4 |
| **Escalabilidade** | 20% | 4 | 3 | 5 |
| **Simplicidade** | 15% | 5 | 3 | 2 |
| **Manutenibilidade** | 15% | 4 | 3 | 4 |
| **TOTAL** | 100% | **3.85** | **3.20** | **3.95** |

**Recomendação**: Opção C (Arquitetura Híbrida)

---

## 4. Arquitetura Recomendada

### 4.1 Visão como Plataforma Enabler

```
┌─────────────────────────────────────────────────────────────────────────┐
│                     RAG ENABLER PLATFORM                                 │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │                      PUBLIC API LAYER                            │   │
│  │                                                                  │   │
│  │  POST /documents         - Upload e indexação de documentos     │   │
│  │  POST /documents/{id}/ask - Perguntas sobre documentos          │   │
│  │  GET  /documents/{id}    - Status e metadados                   │   │
│  │  POST /batch             - Processamento em lote                │   │
│  │  WS   /stream            - Respostas em streaming               │   │
│  │                                                                  │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                    │                                     │
│                                    ▼                                     │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │                    INTERNAL SERVICES                             │   │
│  │                                                                  │   │
│  │  ┌────────────┐ ┌────────────┐ ┌────────────┐ ┌────────────┐   │   │
│  │  │  Document  │ │   RAG      │ │    LLM     │ │    DKR     │   │   │
│  │  │  Processor │ │   Engine   │ │   Service  │ │   Service  │   │   │
│  │  │            │ │            │ │            │ │            │   │   │
│  │  │ • PDF Parse│ │ • Chunk    │ │ • Llama 3.1│ │ • Rules    │   │   │
│  │  │ • OCR      │ │ • Index    │ │ • TinyLlama│ │ • Validate │   │   │
│  │  │ • Extract  │ │ • Retrieve │ │ • Stream   │ │ • Correct  │   │   │
│  │  └────────────┘ └────────────┘ └────────────┘ └────────────┘   │   │
│  │                                                                  │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                    │                                     │
│                                    ▼                                     │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │                    DATA LAYER                                    │   │
│  │                                                                  │   │
│  │  ┌────────────┐ ┌────────────┐ ┌────────────┐ ┌────────────┐   │   │
│  │  │     S3     │ │ ElastiCache│ │   Aurora   │ │    EFS     │   │   │
│  │  │            │ │   Redis    │ │ PostgreSQL │ │            │   │   │
│  │  │ • PDFs     │ │ • Q&A Cache│ │ • Metadata │ │ • Models   │   │   │
│  │  │ • Results  │ │ • Embed $  │ │ • Audit    │ │ • Shared   │   │   │
│  │  │ • Models   │ │ • Sessions │ │ • Analytics│ │            │   │   │
│  │  └────────────┘ └────────────┘ └────────────┘ └────────────┘   │   │
│  │                                                                  │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

### 4.2 Integração com Aplicações da Conta AWS

```
┌─────────────────────────────────────────────────────────────────────────┐
│                     AWS PRIVATE ACCOUNT                                  │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  ┌───────────────┐  ┌───────────────┐  ┌───────────────┐               │
│  │   App A       │  │   App B       │  │   App C       │               │
│  │   (Frontend)  │  │   (Backend)   │  │   (Bot)       │               │
│  │               │  │               │  │               │               │
│  │   React/Vue   │  │   Java/Node   │  │   Slack/Teams │               │
│  └───────┬───────┘  └───────┬───────┘  └───────┬───────┘               │
│          │                  │                  │                        │
│          └──────────────────┴──────────────────┘                        │
│                             │                                            │
│                    VPC Endpoint / PrivateLink                           │
│                             │                                            │
│                             ▼                                            │
│  ┌───────────────────────────────────────────────────────────────────┐  │
│  │                                                                    │  │
│  │                    ★ RAG ENABLER API ★                            │  │
│  │                                                                    │  │
│  │     Internal ALB: rag-enabler.internal.empresa.com               │  │
│  │                                                                    │  │
│  │     • POST /documents      - Upload de documentos                 │  │
│  │     • POST /documents/{id}/ask - Perguntas Q&A                   │  │
│  │     • POST /analyze        - Análise completa                     │  │
│  │     • GET  /health         - Health check                         │  │
│  │                                                                    │  │
│  └───────────────────────────────────────────────────────────────────┘  │
│                                                                         │
│  ┌───────────────────────────────────────────────────────────────────┐  │
│  │                    SHARED SERVICES                                 │  │
│  │                                                                    │  │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐               │  │
│  │  │   Cognito   │  │ CloudWatch  │  │   Secrets   │               │  │
│  │  │   (Auth)    │  │ (Logs/Metr) │  │   Manager   │               │  │
│  │  └─────────────┘  └─────────────┘  └─────────────┘               │  │
│  │                                                                    │  │
│  └───────────────────────────────────────────────────────────────────┘  │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

### 4.3 Fluxo de Processamento

```
┌─────────────────────────────────────────────────────────────────────────┐
│                      FLUXO: UPLOAD E INDEXAÇÃO                          │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  1. Cliente      2. API Gateway    3. Lambda        4. SQS             │
│     │                 │                │               │                │
│     │ POST /documents │                │               │                │
│     │ [PDF file]      │                │               │                │
│     │────────────────>│                │               │                │
│     │                 │ Invoke         │               │                │
│     │                 │───────────────>│               │                │
│     │                 │                │ Upload to S3  │                │
│     │                 │                │──────────────>│ S3             │
│     │                 │                │               │                │
│     │                 │                │ Enqueue job   │                │
│     │                 │                │──────────────>│                │
│     │                 │                │               │                │
│     │ 202 Accepted    │                │               │                │
│     │ {document_id}   │                │               │                │
│     │<────────────────│                │               │                │
│                                                                         │
│  5. ECS Worker (OCR)    6. ECS Worker (RAG)    7. ElastiCache          │
│        │                      │                      │                  │
│        │ Poll SQS             │                      │                  │
│        │<─────────────────────│                      │                  │
│        │                      │                      │                  │
│        │ Download PDF from S3 │                      │                  │
│        │                      │                      │                  │
│        │ Extract text (OCR)   │                      │                  │
│        │                      │                      │                  │
│        │ Chunk & Embed        │                      │                  │
│        │─────────────────────>│                      │                  │
│        │                      │ Store embeddings     │                  │
│        │                      │─────────────────────>│                  │
│        │                      │                      │                  │
│        │ Update status: READY │                      │                  │
│        │                      │                      │                  │
└─────────────────────────────────────────────────────────────────────────┘
```

```
┌─────────────────────────────────────────────────────────────────────────┐
│                      FLUXO: PERGUNTA (Q&A)                              │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  1. Cliente                     2. API/Lambda                           │
│     │                                │                                  │
│     │ POST /documents/{id}/ask       │                                  │
│     │ {question: "..."}              │                                  │
│     │───────────────────────────────>│                                  │
│     │                                │                                  │
│     │                                │ Check cache (Redis)              │
│     │                                │──────────────────>│ ElastiCache  │
│     │                                │                   │              │
│     │                                │ Cache HIT?        │              │
│     │                                │<──────────────────│              │
│     │                                │                                  │
│     │                         [Se cache HIT]                            │
│     │ 200 OK {answer}                │                                  │
│     │<───────────────────────────────│                                  │
│     │                                │                                  │
│     │                         [Se cache MISS]                           │
│     │                                │                                  │
│  3. ECS (RAG Engine)          4. ECS (LLM Service)                     │
│        │                            │                                   │
│        │ Retrieve context           │                                   │
│        │ (embeddings + BM25)        │                                   │
│        │                            │                                   │
│        │ Generate answer            │                                   │
│        │───────────────────────────>│                                   │
│        │                            │ LLM inference                     │
│        │                            │ (Llama 3.1 8B)                    │
│        │                            │                                   │
│        │ Apply DKR rules            │                                   │
│        │<───────────────────────────│                                   │
│        │                            │                                   │
│        │ Cache result               │                                   │
│        │                            │                                   │
│     │ 200 OK {answer, sources}      │                                   │
│     │<───────────────────────────────│                                  │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 5. Design da API

### 5.1 Especificação OpenAPI

```yaml
openapi: 3.0.3
info:
  title: RAG Enabler API
  description: API para processamento de documentos e Q&A com LLM
  version: 1.0.0
  contact:
    name: Equipe de Arquitetura

servers:
  - url: https://rag-enabler.internal.empresa.com/v1
    description: Ambiente de produção (interno)

security:
  - ApiKeyAuth: []
  - BearerAuth: []

paths:
  /documents:
    post:
      summary: Upload e indexa documento
      description: |
        Faz upload de um documento PDF e inicia o processo de 
        OCR, chunking e indexação. O processo é assíncrono.
      operationId: uploadDocument
      tags:
        - Documents
      requestBody:
        required: true
        content:
          multipart/form-data:
            schema:
              type: object
              required:
                - file
              properties:
                file:
                  type: string
                  format: binary
                  description: Arquivo PDF
                template:
                  type: string
                  enum: 
                    - licencas_software
                    - inventory
                    - meeting_minutes
                    - generic
                  default: generic
                  description: Template de regras DKR a aplicar
                metadata:
                  type: object
                  description: Metadados customizados
      responses:
        '202':
          description: Documento aceito para processamento
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/DocumentAccepted'
        '400':
          $ref: '#/components/responses/BadRequest'
        '413':
          description: Arquivo muito grande (max 50MB)

  /documents/{document_id}:
    get:
      summary: Obtém status do documento
      operationId: getDocument
      tags:
        - Documents
      parameters:
        - $ref: '#/components/parameters/DocumentId'
      responses:
        '200':
          description: Informações do documento
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/Document'
        '404':
          $ref: '#/components/responses/NotFound'

    delete:
      summary: Remove documento e seus dados
      operationId: deleteDocument
      tags:
        - Documents
      parameters:
        - $ref: '#/components/parameters/DocumentId'
      responses:
        '204':
          description: Documento removido
        '404':
          $ref: '#/components/responses/NotFound'

  /documents/{document_id}/ask:
    post:
      summary: Faz pergunta sobre documento
      description: |
        Realiza uma pergunta sobre um documento indexado.
        Usa RAG para recuperar contexto relevante e LLM para gerar resposta.
      operationId: askQuestion
      tags:
        - Q&A
      parameters:
        - $ref: '#/components/parameters/DocumentId'
      requestBody:
        required: true
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/QuestionRequest'
      responses:
        '200':
          description: Resposta gerada
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/AnswerResponse'
        '404':
          $ref: '#/components/responses/NotFound'
        '422':
          description: Documento ainda não está pronto

  /analyze:
    post:
      summary: Análise completa de documento
      description: |
        Executa análise estruturada do documento usando perfil específico
        (inventário, ata de reunião, etc.)
      operationId: analyzeDocument
      tags:
        - Analysis
      requestBody:
        required: true
        content:
          application/json:
            schema:
              type: object
              required:
                - document_id
                - profile
              properties:
                document_id:
                  type: string
                  format: uuid
                profile:
                  type: string
                  enum:
                    - inventory
                    - meeting_minutes
      responses:
        '200':
          description: Resultado da análise
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/AnalysisResult'

  /health:
    get:
      summary: Health check
      operationId: healthCheck
      tags:
        - System
      security: []
      responses:
        '200':
          description: Sistema saudável
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/HealthStatus'

components:
  securitySchemes:
    ApiKeyAuth:
      type: apiKey
      in: header
      name: X-API-Key
    BearerAuth:
      type: http
      scheme: bearer
      bearerFormat: JWT

  parameters:
    DocumentId:
      name: document_id
      in: path
      required: true
      schema:
        type: string
        format: uuid

  schemas:
    DocumentAccepted:
      type: object
      properties:
        document_id:
          type: string
          format: uuid
        status:
          type: string
          enum: [processing]
        estimated_time_seconds:
          type: integer
        status_url:
          type: string
          format: uri

    Document:
      type: object
      properties:
        id:
          type: string
          format: uuid
        filename:
          type: string
        status:
          type: string
          enum: [processing, ready, failed]
        page_count:
          type: integer
        word_count:
          type: integer
        template:
          type: string
        created_at:
          type: string
          format: date-time
        processed_at:
          type: string
          format: date-time
        error:
          type: string

    QuestionRequest:
      type: object
      required:
        - question
      properties:
        question:
          type: string
          minLength: 3
          maxLength: 1000
        model:
          type: string
          enum: [llama3-8b, tinyllama, auto]
          default: auto
        use_dkr:
          type: boolean
          default: true
        top_k:
          type: integer
          minimum: 1
          maximum: 20
          default: 5
        include_sources:
          type: boolean
          default: true

    AnswerResponse:
      type: object
      properties:
        answer:
          type: string
        confidence:
          type: number
          minimum: 0
          maximum: 1
        sources:
          type: array
          items:
            $ref: '#/components/schemas/Source'
        dkr_applied:
          type: boolean
        dkr_corrections:
          type: array
          items:
            type: string
        model_used:
          type: string
        processing_time_ms:
          type: integer
        cached:
          type: boolean

    Source:
      type: object
      properties:
        page:
          type: integer
        text:
          type: string
        score:
          type: number

    AnalysisResult:
      type: object
      properties:
        document_id:
          type: string
        profile:
          type: string
        result:
          type: object
        confidence:
          type: number
        processing_time_ms:
          type: integer

    HealthStatus:
      type: object
      properties:
        status:
          type: string
          enum: [healthy, degraded, unhealthy]
        version:
          type: string
        components:
          type: object
          additionalProperties:
            type: object
            properties:
              status:
                type: string
              latency_ms:
                type: integer

  responses:
    BadRequest:
      description: Requisição inválida
      content:
        application/json:
          schema:
            type: object
            properties:
              error:
                type: string
              details:
                type: array
                items:
                  type: string

    NotFound:
      description: Recurso não encontrado
      content:
        application/json:
          schema:
            type: object
            properties:
              error:
                type: string
```

### 5.2 Exemplos de Uso

#### Upload de Documento

```bash
curl -X POST https://rag-enabler.internal.empresa.com/v1/documents \
  -H "X-API-Key: $API_KEY" \
  -F "file=@documento.pdf" \
  -F "template=licencas_software"
```

**Resposta:**
```json
{
  "document_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "processing",
  "estimated_time_seconds": 120,
  "status_url": "/v1/documents/550e8400-e29b-41d4-a716-446655440000"
}
```

#### Pergunta sobre Documento

```bash
curl -X POST https://rag-enabler.internal.empresa.com/v1/documents/550e.../ask \
  -H "X-API-Key: $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "question": "Qual é a licença mais crítica?",
    "model": "llama3-8b",
    "use_dkr": true
  }'
```

**Resposta:**
```json
{
  "answer": "De acordo com o documento, a licença mais crítica é **AGPL-3.0-only** com grau de criticidade **ALTO**.\n\nJustificativa: Possui obrigações mesmo sem distribuição, introduzindo a modalidade SaaS.\n\nRecomendação: Evitar o uso desta licença.",
  "confidence": 0.92,
  "sources": [
    {
      "page": 3,
      "text": "AGPL-3.0-only: Criticidade ALTO...",
      "score": 0.89
    }
  ],
  "dkr_applied": true,
  "dkr_corrections": ["Normalização de termos aplicada"],
  "model_used": "llama3-8b",
  "processing_time_ms": 2340,
  "cached": false
}
```

---

## 6. Modificações Necessárias

### 6.1 Estrutura de Arquivos Proposta

```
src/
├── api/                          # NOVO - API Layer
│   ├── __init__.py
│   ├── main.py                   # FastAPI application
│   ├── config.py                 # Configurações da API
│   ├── dependencies.py           # Injeção de dependências
│   ├── routes/
│   │   ├── __init__.py
│   │   ├── documents.py          # POST /documents, GET /documents/{id}
│   │   ├── ask.py                # POST /documents/{id}/ask
│   │   ├── analyze.py            # POST /analyze
│   │   └── health.py             # GET /health
│   ├── middleware/
│   │   ├── __init__.py
│   │   ├── auth.py               # Autenticação API Key / JWT
│   │   ├── rate_limit.py         # Rate limiting
│   │   ├── logging.py            # Request/Response logging
│   │   └── error_handler.py      # Exception handling
│   └── schemas/
│       ├── __init__.py
│       ├── requests.py           # Pydantic request models
│       └── responses.py          # Pydantic response models
│
├── workers/                      # NOVO - Background Workers
│   ├── __init__.py
│   ├── document_processor.py     # SQS consumer para OCR/indexação
│   ├── llm_worker.py             # LLM inference worker
│   └── cleanup_worker.py         # Limpeza de dados antigos
│
├── storage/                      # NOVO - Storage Adapters
│   ├── __init__.py
│   ├── base.py                   # Interface abstrata
│   ├── s3_adapter.py             # S3 para PDFs e resultados
│   ├── efs_adapter.py            # EFS para modelos
│   ├── redis_adapter.py          # ElastiCache para cache
│   └── model_loader.py           # Carregamento de modelos
│
├── infra/                        # NOVO - Infrastructure as Code
│   ├── terraform/
│   │   ├── main.tf               # Provider e backend
│   │   ├── variables.tf          # Variáveis
│   │   ├── vpc.tf                # VPC e subnets
│   │   ├── ecs.tf                # ECS cluster e services
│   │   ├── alb.tf                # Application Load Balancer
│   │   ├── efs.tf                # Elastic File System
│   │   ├── elasticache.tf        # Redis cluster
│   │   ├── s3.tf                 # Buckets
│   │   ├── sqs.tf                # Filas
│   │   ├── iam.tf                # Roles e policies
│   │   ├── cloudwatch.tf         # Logs e métricas
│   │   └── outputs.tf            # Outputs
│   │
│   └── docker/
│       ├── Dockerfile.api        # Container da API
│       ├── Dockerfile.worker     # Container dos workers
│       ├── Dockerfile.llm        # Container do LLM (com modelo)
│       └── docker-compose.yml    # Dev environment
│
├── config/                       # MODIFICADO
│   ├── settings.py               # Adicionar configs AWS
│   └── aws_config.py             # NOVO - AWS specific configs
│
├── core/                         # MODIFICADO
│   ├── ocr_cache.py              # Adaptar para Redis
│   └── ...
│
├── qa/                           # MODIFICADO
│   ├── cache.py                  # Adaptar para Redis
│   └── ...
│
└── rag/                          # MODIFICADO
    ├── embeddings.py             # Adaptar para EFS models
    └── ...
```

### 6.2 Modificações por Componente

| Componente | Modificação | Esforço | Prioridade |
|------------|-------------|---------|------------|
| **Storage local → S3** | Adaptar upload/download de PDFs | Médio | P0 |
| **Cache arquivo → Redis** | Substituir ResponseCache e OCRCache | Médio | P0 |
| **Config → Secrets Manager** | Mover credenciais para AWS | Baixo | P0 |
| **API Layer** | Criar endpoints FastAPI | Alto | P0 |
| **Async Processing** | Implementar workers SQS | Alto | P0 |
| **Health Checks** | Endpoints /health, /ready | Baixo | P0 |
| **Logging → CloudWatch** | Structured logging | Baixo | P1 |
| **Modelos → EFS** | Loader de modelos do EFS | Médio | P1 |
| **Métricas** | Custom CloudWatch metrics | Médio | P2 |
| **Rate Limiting** | Implementar throttling | Baixo | P2 |

### 6.3 Código de Exemplo: S3 Adapter

```python
# src/storage/s3_adapter.py

import boto3
from pathlib import Path
from typing import Optional, BinaryIO
import logging

logger = logging.getLogger(__name__)


class S3StorageAdapter:
    """Adapter para armazenamento de documentos no S3."""
    
    def __init__(
        self,
        bucket_name: str,
        region: str = "us-east-1",
        prefix: str = "documents/"
    ):
        self.bucket_name = bucket_name
        self.prefix = prefix
        self.s3 = boto3.client("s3", region_name=region)
    
    def upload_document(
        self,
        document_id: str,
        file: BinaryIO,
        filename: str
    ) -> str:
        """
        Faz upload de documento para S3.
        
        Returns:
            S3 key do documento
        """
        key = f"{self.prefix}{document_id}/{filename}"
        
        self.s3.upload_fileobj(
            file,
            self.bucket_name,
            key,
            ExtraArgs={
                "ContentType": "application/pdf",
                "Metadata": {
                    "document_id": document_id,
                    "original_filename": filename
                }
            }
        )
        
        logger.info(f"Documento uploaded: s3://{self.bucket_name}/{key}")
        return key
    
    def download_document(
        self,
        document_id: str,
        filename: str,
        local_path: Path
    ) -> Path:
        """
        Baixa documento do S3 para path local.
        
        Returns:
            Path local do arquivo
        """
        key = f"{self.prefix}{document_id}/{filename}"
        local_file = local_path / filename
        
        self.s3.download_file(
            self.bucket_name,
            key,
            str(local_file)
        )
        
        logger.info(f"Documento downloaded: {local_file}")
        return local_file
    
    def get_presigned_url(
        self,
        document_id: str,
        filename: str,
        expiration: int = 3600
    ) -> str:
        """
        Gera URL pré-assinada para acesso direto.
        
        Args:
            expiration: Tempo de expiração em segundos
            
        Returns:
            URL pré-assinada
        """
        key = f"{self.prefix}{document_id}/{filename}"
        
        url = self.s3.generate_presigned_url(
            "get_object",
            Params={
                "Bucket": self.bucket_name,
                "Key": key
            },
            ExpiresIn=expiration
        )
        
        return url
    
    def delete_document(self, document_id: str) -> None:
        """Remove todos os arquivos de um documento."""
        prefix = f"{self.prefix}{document_id}/"
        
        # Lista e deleta todos os objetos
        paginator = self.s3.get_paginator("list_objects_v2")
        
        for page in paginator.paginate(Bucket=self.bucket_name, Prefix=prefix):
            if "Contents" in page:
                objects = [{"Key": obj["Key"]} for obj in page["Contents"]]
                self.s3.delete_objects(
                    Bucket=self.bucket_name,
                    Delete={"Objects": objects}
                )
        
        logger.info(f"Documento removido: {document_id}")
```

### 6.4 Código de Exemplo: Redis Cache Adapter

```python
# src/storage/redis_adapter.py

import redis
import json
import hashlib
from typing import Optional, Any
from dataclasses import asdict
import logging

logger = logging.getLogger(__name__)


class RedisCacheAdapter:
    """Adapter para cache usando ElastiCache Redis."""
    
    def __init__(
        self,
        host: str,
        port: int = 6379,
        db: int = 0,
        password: Optional[str] = None,
        prefix: str = "rag:",
        default_ttl: int = 86400  # 24 horas
    ):
        self.prefix = prefix
        self.default_ttl = default_ttl
        self.redis = redis.Redis(
            host=host,
            port=port,
            db=db,
            password=password,
            decode_responses=True
        )
    
    def _make_key(self, namespace: str, key: str) -> str:
        """Gera chave com prefixo e namespace."""
        return f"{self.prefix}{namespace}:{key}"
    
    def _hash_key(self, data: str) -> str:
        """Gera hash MD5 de uma string."""
        return hashlib.md5(data.encode()).hexdigest()
    
    # ============================================
    # Cache de Respostas Q&A
    # ============================================
    
    def get_qa_response(
        self,
        document_id: str,
        question: str,
        model: str,
        rules_hash: Optional[str] = None
    ) -> Optional[dict]:
        """
        Busca resposta cacheada.
        
        Args:
            document_id: ID do documento
            question: Pergunta feita
            model: Modelo usado
            rules_hash: Hash das regras DKR
            
        Returns:
            Resposta cacheada ou None
        """
        cache_data = f"{document_id}:{question}:{model}:{rules_hash or ''}"
        key = self._make_key("qa", self._hash_key(cache_data))
        
        cached = self.redis.get(key)
        if cached:
            logger.debug(f"Cache HIT: {key[:50]}...")
            return json.loads(cached)
        
        logger.debug(f"Cache MISS: {key[:50]}...")
        return None
    
    def set_qa_response(
        self,
        document_id: str,
        question: str,
        model: str,
        response: dict,
        rules_hash: Optional[str] = None,
        ttl: Optional[int] = None
    ) -> None:
        """Armazena resposta no cache."""
        cache_data = f"{document_id}:{question}:{model}:{rules_hash or ''}"
        key = self._make_key("qa", self._hash_key(cache_data))
        
        self.redis.setex(
            key,
            ttl or self.default_ttl,
            json.dumps(response, ensure_ascii=False)
        )
        logger.debug(f"Cache SET: {key[:50]}...")
    
    # ============================================
    # Cache de Embeddings
    # ============================================
    
    def get_embedding(self, text_hash: str) -> Optional[list]:
        """Busca embedding cacheado."""
        key = self._make_key("emb", text_hash)
        cached = self.redis.get(key)
        
        if cached:
            return json.loads(cached)
        return None
    
    def set_embedding(
        self,
        text_hash: str,
        embedding: list,
        ttl: Optional[int] = None
    ) -> None:
        """Armazena embedding no cache."""
        key = self._make_key("emb", text_hash)
        
        self.redis.setex(
            key,
            ttl or (self.default_ttl * 7),  # 7 dias
            json.dumps(embedding)
        )
    
    # ============================================
    # Cache de OCR
    # ============================================
    
    def get_ocr_result(self, document_hash: str) -> Optional[dict]:
        """Busca resultado OCR cacheado."""
        key = self._make_key("ocr", document_hash)
        cached = self.redis.get(key)
        
        if cached:
            return json.loads(cached)
        return None
    
    def set_ocr_result(
        self,
        document_hash: str,
        result: dict,
        ttl: Optional[int] = None
    ) -> None:
        """Armazena resultado OCR no cache."""
        key = self._make_key("ocr", document_hash)
        
        self.redis.setex(
            key,
            ttl or (self.default_ttl * 30),  # 30 dias
            json.dumps(result, ensure_ascii=False)
        )
    
    # ============================================
    # Utilidades
    # ============================================
    
    def invalidate_document_cache(self, document_id: str) -> int:
        """
        Invalida todo o cache relacionado a um documento.
        
        Returns:
            Número de chaves removidas
        """
        pattern = f"{self.prefix}*:{document_id}:*"
        keys = list(self.redis.scan_iter(match=pattern))
        
        if keys:
            deleted = self.redis.delete(*keys)
            logger.info(f"Cache invalidado: {deleted} chaves para doc {document_id}")
            return deleted
        
        return 0
    
    def health_check(self) -> bool:
        """Verifica se Redis está respondendo."""
        try:
            return self.redis.ping()
        except Exception as e:
            logger.error(f"Redis health check failed: {e}")
            return False
```

---

## 7. Infraestrutura como Código

### 7.1 Terraform - Estrutura Principal

```hcl
# infra/terraform/main.tf

terraform {
  required_version = ">= 1.0"
  
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
  
  backend "s3" {
    bucket         = "empresa-terraform-state"
    key            = "rag-enabler/terraform.tfstate"
    region         = "us-east-1"
    encrypt        = true
    dynamodb_table = "terraform-locks"
  }
}

provider "aws" {
  region = var.aws_region
  
  default_tags {
    tags = {
      Project     = "rag-enabler"
      Environment = var.environment
      ManagedBy   = "terraform"
    }
  }
}

# ============================================
# Data Sources
# ============================================

data "aws_caller_identity" "current" {}
data "aws_region" "current" {}

data "aws_vpc" "main" {
  id = var.vpc_id
}

data "aws_subnets" "private" {
  filter {
    name   = "vpc-id"
    values = [var.vpc_id]
  }
  
  filter {
    name   = "tag:Type"
    values = ["private"]
  }
}
```

### 7.2 Terraform - ECS Cluster

```hcl
# infra/terraform/ecs.tf

# ============================================
# ECS Cluster
# ============================================

resource "aws_ecs_cluster" "main" {
  name = "${var.project_name}-${var.environment}"
  
  setting {
    name  = "containerInsights"
    value = "enabled"
  }
  
  configuration {
    execute_command_configuration {
      logging = "OVERRIDE"
      
      log_configuration {
        cloud_watch_log_group_name = aws_cloudwatch_log_group.ecs_exec.name
      }
    }
  }
}

resource "aws_ecs_cluster_capacity_providers" "main" {
  cluster_name = aws_ecs_cluster.main.name
  
  capacity_providers = ["FARGATE", "FARGATE_SPOT"]
  
  default_capacity_provider_strategy {
    base              = 1
    weight            = 1
    capacity_provider = "FARGATE"
  }
  
  default_capacity_provider_strategy {
    weight            = 3
    capacity_provider = "FARGATE_SPOT"
  }
}

# ============================================
# ECS Task Definition - API
# ============================================

resource "aws_ecs_task_definition" "api" {
  family                   = "${var.project_name}-api"
  network_mode             = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  cpu                      = 1024  # 1 vCPU
  memory                   = 4096  # 4 GB
  execution_role_arn       = aws_iam_role.ecs_execution.arn
  task_role_arn            = aws_iam_role.ecs_task.arn
  
  container_definitions = jsonencode([
    {
      name      = "api"
      image     = "${aws_ecr_repository.api.repository_url}:latest"
      essential = true
      
      portMappings = [
        {
          containerPort = 8000
          hostPort      = 8000
          protocol      = "tcp"
        }
      ]
      
      environment = [
        {
          name  = "ENVIRONMENT"
          value = var.environment
        },
        {
          name  = "AWS_REGION"
          value = var.aws_region
        },
        {
          name  = "S3_BUCKET"
          value = aws_s3_bucket.documents.id
        },
        {
          name  = "REDIS_HOST"
          value = aws_elasticache_replication_group.main.primary_endpoint_address
        },
        {
          name  = "SQS_QUEUE_URL"
          value = aws_sqs_queue.document_processing.url
        }
      ]
      
      secrets = [
        {
          name      = "API_KEY"
          valueFrom = aws_secretsmanager_secret.api_key.arn
        }
      ]
      
      logConfiguration = {
        logDriver = "awslogs"
        options = {
          "awslogs-group"         = aws_cloudwatch_log_group.api.name
          "awslogs-region"        = var.aws_region
          "awslogs-stream-prefix" = "api"
        }
      }
      
      healthCheck = {
        command     = ["CMD-SHELL", "curl -f http://localhost:8000/health || exit 1"]
        interval    = 30
        timeout     = 5
        retries     = 3
        startPeriod = 60
      }
    }
  ])
}

# ============================================
# ECS Task Definition - LLM Worker
# ============================================

resource "aws_ecs_task_definition" "llm_worker" {
  family                   = "${var.project_name}-llm-worker"
  network_mode             = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  cpu                      = 4096   # 4 vCPU
  memory                   = 16384  # 16 GB
  execution_role_arn       = aws_iam_role.ecs_execution.arn
  task_role_arn            = aws_iam_role.ecs_task.arn
  
  volume {
    name = "models"
    
    efs_volume_configuration {
      file_system_id     = aws_efs_file_system.models.id
      transit_encryption = "ENABLED"
      
      authorization_config {
        access_point_id = aws_efs_access_point.models.id
        iam             = "ENABLED"
      }
    }
  }
  
  container_definitions = jsonencode([
    {
      name      = "llm-worker"
      image     = "${aws_ecr_repository.llm_worker.repository_url}:latest"
      essential = true
      
      mountPoints = [
        {
          sourceVolume  = "models"
          containerPath = "/models"
          readOnly      = true
        }
      ]
      
      environment = [
        {
          name  = "ENVIRONMENT"
          value = var.environment
        },
        {
          name  = "MODELS_PATH"
          value = "/models"
        },
        {
          name  = "DEFAULT_MODEL"
          value = "llama3-8b"
        },
        {
          name  = "SQS_QUEUE_URL"
          value = aws_sqs_queue.document_processing.url
        },
        {
          name  = "REDIS_HOST"
          value = aws_elasticache_replication_group.main.primary_endpoint_address
        }
      ]
      
      logConfiguration = {
        logDriver = "awslogs"
        options = {
          "awslogs-group"         = aws_cloudwatch_log_group.llm_worker.name
          "awslogs-region"        = var.aws_region
          "awslogs-stream-prefix" = "llm"
        }
      }
    }
  ])
}

# ============================================
# ECS Services
# ============================================

resource "aws_ecs_service" "api" {
  name            = "${var.project_name}-api"
  cluster         = aws_ecs_cluster.main.id
  task_definition = aws_ecs_task_definition.api.arn
  desired_count   = var.api_desired_count
  launch_type     = "FARGATE"
  
  network_configuration {
    subnets          = data.aws_subnets.private.ids
    security_groups  = [aws_security_group.ecs_api.id]
    assign_public_ip = false
  }
  
  load_balancer {
    target_group_arn = aws_lb_target_group.api.arn
    container_name   = "api"
    container_port   = 8000
  }
  
  service_registries {
    registry_arn = aws_service_discovery_service.api.arn
  }
  
  deployment_configuration {
    maximum_percent         = 200
    minimum_healthy_percent = 100
  }
  
  lifecycle {
    ignore_changes = [desired_count]
  }
}

resource "aws_ecs_service" "llm_worker" {
  name            = "${var.project_name}-llm-worker"
  cluster         = aws_ecs_cluster.main.id
  task_definition = aws_ecs_task_definition.llm_worker.arn
  desired_count   = var.llm_worker_desired_count
  
  capacity_provider_strategy {
    capacity_provider = "FARGATE_SPOT"
    weight            = 1
    base              = 1
  }
  
  network_configuration {
    subnets          = data.aws_subnets.private.ids
    security_groups  = [aws_security_group.ecs_worker.id]
    assign_public_ip = false
  }
  
  lifecycle {
    ignore_changes = [desired_count]
  }
}

# ============================================
# Auto Scaling
# ============================================

resource "aws_appautoscaling_target" "api" {
  max_capacity       = var.api_max_count
  min_capacity       = var.api_min_count
  resource_id        = "service/${aws_ecs_cluster.main.name}/${aws_ecs_service.api.name}"
  scalable_dimension = "ecs:service:DesiredCount"
  service_namespace  = "ecs"
}

resource "aws_appautoscaling_policy" "api_cpu" {
  name               = "${var.project_name}-api-cpu"
  policy_type        = "TargetTrackingScaling"
  resource_id        = aws_appautoscaling_target.api.resource_id
  scalable_dimension = aws_appautoscaling_target.api.scalable_dimension
  service_namespace  = aws_appautoscaling_target.api.service_namespace
  
  target_tracking_scaling_policy_configuration {
    predefined_metric_specification {
      predefined_metric_type = "ECSServiceAverageCPUUtilization"
    }
    target_value       = 70.0
    scale_in_cooldown  = 300
    scale_out_cooldown = 60
  }
}
```

### 7.3 Terraform - ElastiCache

```hcl
# infra/terraform/elasticache.tf

resource "aws_elasticache_subnet_group" "main" {
  name       = "${var.project_name}-${var.environment}"
  subnet_ids = data.aws_subnets.private.ids
}

resource "aws_elasticache_replication_group" "main" {
  replication_group_id       = "${var.project_name}-${var.environment}"
  description                = "Redis cluster for RAG Enabler"
  
  node_type                  = var.redis_node_type
  num_cache_clusters         = var.environment == "prod" ? 2 : 1
  port                       = 6379
  
  engine                     = "redis"
  engine_version             = "7.0"
  parameter_group_name       = "default.redis7"
  
  subnet_group_name          = aws_elasticache_subnet_group.main.name
  security_group_ids         = [aws_security_group.redis.id]
  
  at_rest_encryption_enabled = true
  transit_encryption_enabled = true
  auth_token                 = random_password.redis_auth.result
  
  automatic_failover_enabled = var.environment == "prod"
  multi_az_enabled           = var.environment == "prod"
  
  snapshot_retention_limit   = 7
  snapshot_window            = "05:00-09:00"
  maintenance_window         = "mon:10:00-mon:14:00"
  
  apply_immediately          = var.environment != "prod"
  
  log_delivery_configuration {
    destination      = aws_cloudwatch_log_group.redis.name
    destination_type = "cloudwatch-logs"
    log_format       = "json"
    log_type         = "slow-log"
  }
}

resource "random_password" "redis_auth" {
  length  = 32
  special = false
}

resource "aws_secretsmanager_secret" "redis_auth" {
  name = "${var.project_name}/${var.environment}/redis-auth"
}

resource "aws_secretsmanager_secret_version" "redis_auth" {
  secret_id     = aws_secretsmanager_secret.redis_auth.id
  secret_string = random_password.redis_auth.result
}
```

### 7.4 Terraform - EFS

```hcl
# infra/terraform/efs.tf

resource "aws_efs_file_system" "models" {
  creation_token = "${var.project_name}-models-${var.environment}"
  encrypted      = true
  
  performance_mode                = "generalPurpose"
  throughput_mode                 = "bursting"
  
  lifecycle_policy {
    transition_to_ia = "AFTER_30_DAYS"
  }
  
  tags = {
    Name = "${var.project_name}-models"
  }
}

resource "aws_efs_mount_target" "models" {
  count = length(data.aws_subnets.private.ids)
  
  file_system_id  = aws_efs_file_system.models.id
  subnet_id       = data.aws_subnets.private.ids[count.index]
  security_groups = [aws_security_group.efs.id]
}

resource "aws_efs_access_point" "models" {
  file_system_id = aws_efs_file_system.models.id
  
  posix_user {
    uid = 1000
    gid = 1000
  }
  
  root_directory {
    path = "/models"
    
    creation_info {
      owner_uid   = 1000
      owner_gid   = 1000
      permissions = "755"
    }
  }
  
  tags = {
    Name = "${var.project_name}-models-ap"
  }
}
```

---

## 8. Estimativa de Custos

### 8.1 Cenário: 10.000 requests/mês (Uso Moderado)

| Recurso | Configuração | Custo/mês (USD) |
|---------|--------------|-----------------|
| **ECS Fargate (API)** | 2 tasks x 1 vCPU x 4 GB | ~$70 |
| **ECS Fargate (Workers)** | 2 tasks x 4 vCPU x 16 GB | ~$210 |
| **EFS** | 20 GB + throughput | ~$10 |
| **ElastiCache** | cache.t3.medium | ~$50 |
| **ALB** | Internal | ~$20 |
| **S3** | 100 GB + requests | ~$5 |
| **CloudWatch** | Logs + métricas | ~$20 |
| **Secrets Manager** | 5 secrets | ~$5 |
| **ECR** | 10 GB images | ~$5 |
| **NAT Gateway** | (se necessário) | ~$50 |
| **TOTAL** | | **~$445/mês** |

### 8.2 Cenário: Com GPU (Alta Performance)

| Recurso | Configuração | Custo/mês (USD) |
|---------|--------------|-----------------|
| **EC2 g4dn.xlarge** | Spot (70% desconto) | ~$150 |
| **Outros serviços** | (igual acima) | ~$160 |
| **TOTAL** | | **~$310/mês** |

### 8.3 Cenário: 100.000 requests/mês (Alto Volume)

| Recurso | Configuração | Custo/mês (USD) |
|---------|--------------|-----------------|
| **ECS Fargate (API)** | 4-8 tasks auto-scaling | ~$200 |
| **ECS Fargate (Workers)** | 4-10 tasks | ~$500 |
| **ElastiCache** | cache.r6g.large | ~$200 |
| **Outros** | Proporcionalmente maior | ~$200 |
| **TOTAL** | | **~$1,100/mês** |

### 8.4 Otimizações de Custo

| Estratégia | Economia Potencial |
|------------|-------------------|
| **Fargate Spot** | 50-70% nos workers |
| **Reserved Capacity** | 30-40% (compromisso 1 ano) |
| **Cache agressivo** | 20-30% menos inferências |
| **Rightsizing** | 10-20% ajustando recursos |
| **Scheduled Scaling** | 20-30% fora do horário comercial |

---

## 9. Plano de Implementação

### 9.1 Cronograma

```
┌─────────────────────────────────────────────────────────────────────────┐
│                     CRONOGRAMA DE IMPLEMENTAÇÃO                          │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  FASE 1: Preparação (Semana 1)                                         │
│  ├── Definir VPC e subnets alvo                                        │
│  ├── Criar repositórios ECR                                            │
│  ├── Configurar Secrets Manager                                        │
│  └── Preparar ambiente de desenvolvimento local                        │
│                                                                         │
│  FASE 2: Storage Adapters (Semana 1-2)                                 │
│  ├── Implementar S3StorageAdapter                                      │
│  ├── Implementar RedisCacheAdapter                                     │
│  ├── Implementar EFSModelLoader                                        │
│  └── Testes unitários e integração                                     │
│                                                                         │
│  FASE 3: API Layer (Semana 2-3)                                        │
│  ├── Criar estrutura FastAPI                                           │
│  ├── Implementar endpoints                                             │
│  ├── Middleware (auth, logging, rate limit)                            │
│  └── Testes de API                                                      │
│                                                                         │
│  FASE 4: Workers (Semana 3-4)                                          │
│  ├── Implementar document_processor (SQS)                              │
│  ├── Implementar llm_worker                                            │
│  ├── Configurar dead-letter queues                                     │
│  └── Testes de integração                                              │
│                                                                         │
│  FASE 5: Infraestrutura (Semana 4-5)                                   │
│  ├── Desenvolver módulos Terraform                                     │
│  ├── Deploy em ambiente de staging                                     │
│  ├── Upload de modelos para EFS                                        │
│  └── Validação de infraestrutura                                       │
│                                                                         │
│  FASE 6: Testes e Ajustes (Semana 5-6)                                 │
│  ├── Testes de carga                                                    │
│  ├── Tuning de performance                                             │
│  ├── Ajustes de auto-scaling                                           │
│  └── Documentação final                                                 │
│                                                                         │
│  TOTAL ESTIMADO: 6 semanas                                              │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

### 9.2 Equipe Sugerida

| Papel | Responsabilidades | Alocação |
|-------|-------------------|----------|
| **Tech Lead** | Arquitetura, decisões técnicas | 50% |
| **Backend Developer** | API, adapters, workers | 100% |
| **DevOps Engineer** | Terraform, CI/CD, monitoring | 100% |
| **QA Engineer** | Testes, validação | 50% |

### 9.3 Riscos e Mitigações

| Risco | Probabilidade | Impacto | Mitigação |
|-------|---------------|---------|-----------|
| **Cold start elevado** | Alta | Médio | Provisioned concurrency, warmup |
| **Custo acima do esperado** | Média | Alto | Monitoramento, alerts, rightsizing |
| **Performance inadequada** | Média | Alto | GPU, cache agressivo, otimização |
| **Complexidade operacional** | Alta | Médio | Automação, runbooks, treinamento |
| **Latência de rede** | Baixa | Médio | VPC Endpoints, mesma AZ |

---

## 10. Considerações de Segurança

### 10.1 Segurança de Rede

```
┌─────────────────────────────────────────────────────────────────────────┐
│                          VPC SECURITY                                    │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │                     Public Subnets                               │   │
│  │                                                                  │   │
│  │  ┌─────────────────┐                                            │   │
│  │  │   NAT Gateway   │ ← Apenas saída para internet               │   │
│  │  └─────────────────┘   (download de deps se necessário)         │   │
│  │                                                                  │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                              │                                          │
│                              ▼                                          │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │                     Private Subnets                              │   │
│  │                                                                  │   │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐        │   │
│  │  │   ALB    │  │   ECS    │  │  Redis   │  │   EFS    │        │   │
│  │  │ (internal)│  │  Tasks   │  │          │  │          │        │   │
│  │  └──────────┘  └──────────┘  └──────────┘  └──────────┘        │   │
│  │       ▲                                                          │   │
│  │       │ VPC Endpoint                                             │   │
│  │       │                                                          │   │
│  │  ┌──────────┐                                                   │   │
│  │  │ PrivateLink│ ← Acesso das apps internas                      │   │
│  │  └──────────┘                                                   │   │
│  │                                                                  │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                                                         │
│  Security Groups:                                                       │
│  • ALB: Permite 443 de apps autorizadas                                │
│  • ECS: Permite 8000 apenas do ALB                                     │
│  • Redis: Permite 6379 apenas do ECS                                   │
│  • EFS: Permite 2049 apenas do ECS                                     │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

### 10.2 Autenticação e Autorização

| Método | Uso | Descrição |
|--------|-----|-----------|
| **API Key** | Machine-to-machine | Header `X-API-Key` |
| **JWT (Cognito)** | Usuários finais | Bearer token |
| **IAM Roles** | Serviços AWS | Task roles para S3, SQS, etc |

### 10.3 Criptografia

| Componente | Em Trânsito | Em Repouso |
|------------|-------------|------------|
| **ALB ↔ ECS** | TLS 1.3 | N/A |
| **ECS ↔ Redis** | TLS 1.2+ | AES-256 |
| **S3** | HTTPS | SSE-S3 |
| **EFS** | TLS | AES-256 |
| **Secrets** | HTTPS | AWS KMS |

### 10.4 Compliance

- [ ] Logs de auditoria em CloudWatch
- [ ] Retenção de logs conforme política
- [ ] Dados não saem da região configurada
- [ ] Acesso baseado em least privilege
- [ ] Rotação automática de credenciais

---

## 11. Monitoramento e Observabilidade

### 11.1 Métricas Principais

| Métrica | Descrição | Threshold Alerta |
|---------|-----------|------------------|
| **API Latency P95** | Tempo de resposta | > 5s |
| **API Error Rate** | Taxa de erros 5xx | > 1% |
| **LLM Inference Time** | Tempo de inferência | > 60s |
| **Cache Hit Rate** | Taxa de cache hits | < 50% |
| **Queue Depth** | Mensagens em SQS | > 100 |
| **ECS CPU** | Utilização de CPU | > 80% |
| **ECS Memory** | Utilização de memória | > 85% |
| **Redis Memory** | Uso de memória | > 80% |

### 11.2 Dashboards

```
┌─────────────────────────────────────────────────────────────────────────┐
│                     RAG ENABLER DASHBOARD                                │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐        │
│  │ Requests/min    │  │ Error Rate      │  │ Latency P95     │        │
│  │     ████████    │  │       0.3%      │  │     2.4s        │        │
│  │      156        │  │     ↓ 0.1%      │  │    ↑ 0.2s       │        │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘        │
│                                                                         │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐        │
│  │ Cache Hit Rate  │  │ Queue Depth     │  │ Active Tasks    │        │
│  │     ████████    │  │       12        │  │     4/10        │        │
│  │      78%        │  │     ↓ 5         │  │    ↑ 1          │        │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘        │
│                                                                         │
│  ┌─────────────────────────────────────────────────────────────────┐  │
│  │                    Request Latency (last 24h)                    │  │
│  │     ▁▂▃▄▅▆▇█▇▆▅▄▃▂▁▂▃▄▅▆▇█▇▆▅▄▃▂▁▂▃▄▅▆▇█▇▆▅▄▃▂▁             │  │
│  └─────────────────────────────────────────────────────────────────┘  │
│                                                                         │
│  ┌─────────────────────────────────────────────────────────────────┐  │
│  │                    Top Errors (last 1h)                          │  │
│  │                                                                  │  │
│  │  1. TimeoutError: LLM inference timeout (3)                     │  │
│  │  2. ValidationError: Invalid document format (2)                │  │
│  │                                                                  │  │
│  └─────────────────────────────────────────────────────────────────┘  │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

### 11.3 Alertas

| Alerta | Condição | Severidade | Ação |
|--------|----------|------------|------|
| **High Error Rate** | Error > 5% por 5min | Critical | Page on-call |
| **High Latency** | P95 > 30s por 10min | Warning | Investigate |
| **Queue Backlog** | Depth > 500 por 5min | Warning | Scale workers |
| **Memory Pressure** | > 90% por 5min | Warning | Investigate leaks |
| **Disk Full** | EFS > 90% | Warning | Cleanup/expand |

---

## 12. Apêndices

### 12.1 Checklist de Go-Live

- [ ] Infraestrutura provisionada e testada
- [ ] Modelos carregados no EFS
- [ ] Secrets configurados
- [ ] Health checks passando
- [ ] Alertas configurados
- [ ] Dashboards criados
- [ ] Runbooks documentados
- [ ] Testes de carga executados
- [ ] Rollback plan definido
- [ ] Comunicação aos stakeholders

### 12.2 Comandos Úteis

```bash
# Deploy via Terraform
cd infra/terraform
terraform init
terraform plan -var-file="environments/prod.tfvars"
terraform apply -var-file="environments/prod.tfvars"

# Build e push de imagens
aws ecr get-login-password | docker login --username AWS --password-stdin $ECR_REPO
docker build -t rag-enabler-api -f infra/docker/Dockerfile.api .
docker tag rag-enabler-api:latest $ECR_REPO/rag-enabler-api:latest
docker push $ECR_REPO/rag-enabler-api:latest

# Upload de modelos para EFS
aws efs create-mount-target --file-system-id $EFS_ID --subnet-id $SUBNET_ID
sudo mount -t efs $EFS_ID:/ /mnt/efs
sudo cp -r models/* /mnt/efs/models/

# Force deploy de serviço
aws ecs update-service --cluster rag-enabler --service api --force-new-deployment

# Logs em tempo real
aws logs tail /ecs/rag-enabler-api --follow

# Escalar workers manualmente
aws ecs update-service --cluster rag-enabler --service llm-worker --desired-count 5
```

### 12.3 Referências

- [AWS ECS Best Practices](https://docs.aws.amazon.com/AmazonECS/latest/bestpracticesguide/)
- [ElastiCache for Redis](https://docs.aws.amazon.com/AmazonElastiCache/latest/red-ug/)
- [EFS Performance](https://docs.aws.amazon.com/efs/latest/ug/performance.html)
- [FastAPI on AWS](https://fastapi.tiangolo.com/deployment/)
- [Terraform AWS Provider](https://registry.terraform.io/providers/hashicorp/aws/latest/docs)

---

## Histórico de Revisões

| Versão | Data | Autor | Descrição |
|--------|------|-------|-----------|
| 1.0.0 | Dez 2024 | Equipe de Arquitetura | Versão inicial |

---

*Documento gerado como parte do projeto RAG Enabler Platform*

