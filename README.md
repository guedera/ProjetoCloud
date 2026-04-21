# ProjetoCloud — Plataforma Escalável de Pagamentos em Nuvem

> **Curso:** Computação em Nuvem — Engenharia de Computação, Insper (2026/1)  
> **Tema:** MVP de processamento de pagamentos sobre AWS

---

## Sumário

1. [Visão Geral](#1-visão-geral)
2. [Mapa da Arquitetura](#2-mapa-da-arquitetura)
3. [Fluxo de Orquestração Passo a Passo](#3-fluxo-de-orquestração-passo-a-passo)
4. [Serviços AWS — Escolhas e Justificativas](#4-serviços-aws--escolhas-e-justificativas)
5. [Camadas do Sistema](#5-camadas-do-sistema)
6. [Modelos de Dados (DynamoDB)](#6-modelos-de-dados-dynamodb)
7. [API — Rotas e Contratos](#7-api--rotas-e-contratos)
8. [Processamento Assíncrono — SQS + Worker Lambda](#8-processamento-assíncrono--sqs--worker-lambda)
9. [Frontend — Painel Administrativo](#9-frontend--painel-administrativo)
10. [Observabilidade](#10-observabilidade)
11. [Testes de Carga com JMeter](#11-testes-de-carga-com-jmeter)
12. [Configurações de Capacidade e Limites](#12-configurações-de-capacidade-e-limites)
13. [Estrutura de Diretórios do Repositório](#13-estrutura-de-diretórios-do-repositório)
14. [Decisões Arquiteturais e Trade-offs](#14-decisões-arquiteturais-e-trade-offs)

---

## 1. Visão Geral

Este projeto implementa um **MVP de plataforma de meios de pagamento** totalmente serverless e orientada a eventos na AWS. O objetivo é demonstrar, em escala reduzida, os mesmos desafios técnicos de uma fintech real: alta disponibilidade, baixa latência, desacoplamento entre componentes e processamento assíncrono de transações.

A solução entrega:

| Funcionalidade | Descrição |
|---|---|
| Cadastro de usuários | CRUD de usuários da plataforma |
| Criação de pagamentos | Registro e enfileiramento de transações |
| Processamento assíncrono | Worker consome a fila e processa cada pagamento |
| Consulta de status | Leitura do estado atual de qualquer transação |
| Painel administrativo | Interface web para operar todos os fluxos acima |
| Testes de carga | Scripts JMeter simulando milhares de requisições simultâneas |

---

## 2. Mapa da Arquitetura

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                            USUÁRIO / NAVEGADOR                              │
└──────────────────────────────────┬──────────────────────────────────────────┘
                                   │  HTTPS
                                   ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│                        CAMADA DE APRESENTAÇÃO                                │
│                                                                              │
│   ┌───────────────────────────┐      ┌─────────────────────────────────┐    │
│   │   Amazon CloudFront (CDN) │ ───► │  Amazon S3 (site estático)      │    │
│   │   Cache + HTTPS global    │      │  React SPA (Painel Admin)       │    │
│   └───────────────────────────┘      └─────────────────────────────────┘    │
└──────────────────────────────────────────────────────────────────────────────┘
                                   │  chamadas REST
                                   ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│                           CAMADA DE ENTRADA                                  │
│                                                                              │
│              ┌──────────────────────────────────────┐                       │
│              │         Amazon API Gateway           │                       │
│              │   (REST API — throttling, CORS,      │                       │
│              │    autenticação via API Key)          │                       │
│              └──────────────┬───────────────────────┘                       │
└─────────────────────────────┼────────────────────────────────────────────────┘
                              │  invocação síncrona
                              ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│                         CAMADA DE APLICAÇÃO                                  │
│                                                                              │
│  ┌────────────────────┐  ┌────────────────────┐  ┌───────────────────────┐  │
│  │  Lambda            │  │  Lambda            │  │  Lambda               │  │
│  │  users-handler     │  │  payments-handler  │  │  status-handler       │  │
│  │                    │  │                    │  │                       │  │
│  │  POST /users       │  │  POST /payments    │  │  GET /payments/{id}   │  │
│  │  GET  /users       │  │  GET  /payments    │  │  GET /payments        │  │
│  │  GET  /users/{id}  │  │  (enfileira no SQS)│  │  (leitura DynamoDB)   │  │
│  └────────┬───────────┘  └────────┬───────────┘  └──────────┬────────────┘  │
└───────────┼──────────────────────┼──────────────────────────┼───────────────┘
            │                      │                           │
            ▼                      ▼                           ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│                          CAMADA DE PERSISTÊNCIA                              │
│                                                                              │
│   ┌──────────────────────────┐      ┌───────────────────────────────────┐   │
│   │  DynamoDB                │      │  DynamoDB                         │   │
│   │  Tabela: users           │      │  Tabela: payments                 │   │
│   │  PK: userId (UUID)       │      │  PK: paymentId (UUID)             │   │
│   │                          │      │  GSI: userId-createdAt-index      │   │
│   └──────────────────────────┘      └───────────────────────────────────┘   │
└──────────────────────────────────────────────────────────────────────────────┘
                              │
                              │  (payments-handler publica mensagem)
                              ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│                       CAMADA DE PROCESSAMENTO ASSÍNCRONO                     │
│                                                                              │
│   ┌────────────────────────────────────────────────────┐                    │
│   │              Amazon SQS                            │                    │
│   │        Fila: payments-queue (Standard)             │                    │
│   │        DLQ:  payments-dlq  (Dead-Letter Queue)     │                    │
│   └─────────────────────────┬──────────────────────────┘                    │
│                             │  trigger (Event Source Mapping)               │
│                             ▼                                               │
│   ┌────────────────────────────────────────────────────┐                    │
│   │              Lambda                                │                    │
│   │         payment-worker                             │                    │
│   │                                                    │                    │
│   │  1. Lê mensagem da fila                            │                    │
│   │  2. Valida dados do pagamento                      │                    │
│   │  3. Simula processamento (delay / lógica)          │                    │
│   │  4. Atualiza status no DynamoDB                    │                    │
│   │     (PENDING → PROCESSING → COMPLETED | FAILED)   │                    │
│   │  5. Publica evento no EventBridge                  │                    │
│   └─────────────────────────┬──────────────────────────┘                    │
└─────────────────────────────┼────────────────────────────────────────────────┘
                              │  evento payment.processed / payment.failed
                              ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│                         CAMADA DE EVENTOS (EventBridge)                      │
│                                                                              │
│   ┌──────────────────────────────────────────────────────────────────────┐  │
│   │  Event Bus: payments-bus                                             │  │
│   │                                                                      │  │
│   │  Regra: payment.completed → (extensível: notificação, auditoria...)  │  │
│   │  Regra: payment.failed    → (extensível: retry, alerta...)           │  │
│   └──────────────────────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────────────────┐
│                            OBSERVABILIDADE                                   │
│                                                                              │
│   CloudWatch Logs ←── todas as Lambdas                                      │
│   CloudWatch Metrics ←── API Gateway (latência, 4xx, 5xx)                   │
│                      ←── SQS (profundidade da fila, mensagens na DLQ)       │
│                      ←── Lambda (duração, erros, throttles)                  │
│   CloudWatch Dashboard ←── painel unificado de métricas                     │
└──────────────────────────────────────────────────────────────────────────────┘
```

---

## 3. Fluxo de Orquestração Passo a Passo

### Fluxo 1 — Cadastro de Usuário

```
Browser (Painel Admin)
  │
  │  POST /users  { name, email, cpf }
  ▼
API Gateway
  │  invoca síncronamente
  ▼
Lambda: users-handler
  │  1. Valida campos obrigatórios (name, email, cpf)
  │  2. Verifica duplicidade de email no DynamoDB
  │  3. Gera userId (UUID v4)
  │  4. Persiste item na tabela `users`
  │  5. Retorna 201 Created com o objeto criado
  ▼
DynamoDB (tabela: users)
```

### Fluxo 2 — Criação de Pagamento (entrada assíncrona)

```
Browser (Painel Admin)
  │
  │  POST /payments  { userId, amount, description, method }
  ▼
API Gateway
  │
  ▼
Lambda: payments-handler
  │  1. Valida campos e verifica se userId existe
  │  2. Gera paymentId (UUID v4)
  │  3. Persiste pagamento com status = PENDING no DynamoDB
  │  4. Publica mensagem na fila SQS (payments-queue)
  │     com o paymentId e dados relevantes
  │  5. Retorna 202 Accepted  { paymentId, status: "PENDING" }
  ▼
DynamoDB (tabela: payments, status=PENDING)
  +
SQS (payments-queue) ← mensagem com paymentId enfileirada
```

### Fluxo 3 — Processamento Assíncrono pelo Worker

```
SQS (payments-queue) — trigger automático (Event Source Mapping)
  │
  ▼
Lambda: payment-worker  [executa de forma independente do cliente]
  │  1. Recebe batch de mensagens (até 10 por invocação)
  │  2. Para cada mensagem:
  │     a. Atualiza status → PROCESSING no DynamoDB
  │     b. Executa lógica de validação/processamento
  │        (verificação de saldo, regras anti-fraude simuladas)
  │     c. Atualiza status → COMPLETED ou FAILED
  │     d. Registra timestamp de processamento
  │  3. Publica evento no EventBridge (payments-bus)
  │     { detail-type: "payment.completed" | "payment.failed" }
  │  4. Mensagem processada com sucesso → removida da fila
  │     Em caso de exceção → vai para DLQ após 3 tentativas
  ▼
DynamoDB (tabela: payments, status atualizado)
  +
EventBridge (payments-bus) ← evento publicado
```

### Fluxo 4 — Consulta de Status

```
Browser (Painel Admin)
  │
  │  GET /payments/{paymentId}
  ▼
API Gateway
  │
  ▼
Lambda: status-handler
  │  1. Busca item no DynamoDB pelo paymentId
  │  2. Retorna status atual e metadados
  ▼
DynamoDB (leitura consistente eventual)
  │
  ▼
Response: { paymentId, status, amount, userId, createdAt, updatedAt }
```

---

## 4. Serviços AWS — Escolhas e Justificativas

### 4.1 AWS Lambda

**O que é:** Execução de código serverless sob demanda, sem gerenciar servidores.

**Por que usar:**
- **Escalabilidade automática:** Lambda escala de 0 a milhares de execuções concorrentes sem nenhuma configuração manual. Num sistema de pagamentos com picos imprevisíveis, isso é fundamental.
- **Custo proporcional ao uso:** Cobrança por invocação e por milissegundo de execução. Em ambiente acadêmico (e em MVPs reais), é muito mais barato do que manter instâncias EC2 ativas 24/7.
- **Sem overhead operacional:** Não há SO para patchear, nem servidor web para configurar. O foco fica 100% na lógica de negócio.
- **Integração nativa com SQS, API Gateway e EventBridge:** Reduz cola entre serviços a praticamente zero configuração.

**Por que NÃO usar EC2:**
- EC2 exigiria gerenciamento de AMI, security groups, auto-scaling groups, load balancers e patching. Para um MVP onde o foco é a arquitetura e não a operação de infra, isso seria overhead desnecessário.

**Configurações planejadas:**

| Função Lambda | Memória | Timeout | Concorrência Reservada |
|---|---|---|---|
| users-handler | 256 MB | 10 s | — (burst padrão) |
| payments-handler | 256 MB | 10 s | — (burst padrão) |
| status-handler | 128 MB | 5 s | — (burst padrão) |
| payment-worker | 512 MB | 60 s | 10 (controla consumo da fila) |

> **Justificativa das memórias:** O worker recebe 512 MB porque faz múltiplas operações de I/O (leitura DynamoDB + escrita + EventBridge) em batch. Os handlers síncronos precisam de menos memória porque cada invocação processa uma única requisição simples.

---

### 4.2 Amazon API Gateway (REST API)

**O que é:** Gateway gerenciado para exposição de APIs HTTP com autenticação, throttling e roteamento.

**Por que usar:**
- **Ponto de entrada único:** Centraliza CORS, autenticação e controle de rate para todos os endpoints.
- **Throttling nativo:** Limita requisições por segundo (rate limit) e em bursts, protegendo as Lambdas de sobrecarga acidental ou de ataques.
- **Integração direta com Lambda:** Sem necessidade de configurar um servidor HTTP intermediário.
- **Estágios de deploy (dev/prod):** Permite manter ambientes separados com a mesma configuração de infraestrutura.

**Configurações planejadas:**
- Throttling padrão: `10.000 req/s` (limite de burst), `5.000 req/s` (limite sustentado)
- API Key obrigatória para todos os endpoints (autenticação básica no MVP)
- CORS habilitado para a origin do CloudFront

---

### 4.3 Amazon DynamoDB

**O que é:** Banco de dados NoSQL gerenciado, chave-valor e documento, com latência em milissegundos.

**Por que usar:**
- **Schema flexível:** Pagamentos podem ter campos variáveis dependendo do método (PIX, boleto, cartão). DynamoDB não exige schema fixo por linha.
- **Escalabilidade horizontal nativa:** Não há tuning de réplicas, shards ou connection pools. A AWS gerencia tudo.
- **Latência consistente em qualquer escala:** Leitura/escrita em ~1-5 ms independentemente do volume de dados, algo crítico para consulta de status de pagamentos.
- **Pay-per-request (On-Demand):** No MVP, o tráfego é imprevisível. Modo on-demand elimina a necessidade de prever WCU/RCU.
- **Integração com Lambda via SDK:** Simples, sem drivers de conexão a gerenciar (diferente de um RDS).

**Por que NÃO usar RDS (Postgres/MySQL):**
- RDS exige VPC, subnets privadas, gerenciamento de conexões (connection pool) e não escala automaticamente. Lambda tem cold starts que esgotariam connection pools de RDS rapidamente em escala.

**Tabelas:**

| Tabela | PK | SK | GSI |
|---|---|---|---|
| `users` | `userId` (String) | — | `email-index` (email → userId) |
| `payments` | `paymentId` (String) | — | `userId-createdAt-index` |

> O GSI `userId-createdAt-index` permite buscar "todos os pagamentos de um usuário ordenados por data" sem fazer scan na tabela inteira — essencial para a página de transações do painel.

---

### 4.4 Amazon SQS (Simple Queue Service)

**O que é:** Serviço de fila de mensagens gerenciado para desacoplar produtores de consumidores.

**Por que usar:**
- **Desacoplamento total:** O `payments-handler` (produtor) não precisa esperar o processamento terminar. Ele enfileira e responde `202 Accepted` imediatamente — o cliente não fica bloqueado.
- **Resiliência a picos:** Se 10.000 pagamentos chegarem ao mesmo tempo, a fila absorve o volume e o worker processa no seu ritmo, sem derrubar o banco ou a aplicação.
- **Retry automático:** Mensagens que falham são reentregues automaticamente (até 3 tentativas configuradas). Após isso, vão para a DLQ para análise.
- **Dead Letter Queue (DLQ):** Pagamentos que falharam repetidamente ficam na DLQ para inspeção e reprocessamento manual — fundamental para auditoria financeira.
- **Integração nativa com Lambda:** Event Source Mapping garante que o worker é invocado automaticamente quando há mensagens, sem polling manual.

**Configurações planejadas:**

| Parâmetro | Valor | Justificativa |
|---|---|---|
| Tipo de fila | Standard | Order não é garantida, mas throughput é ilimitado. Suficiente para MVP. |
| Visibility Timeout | 90 s | Maior que o timeout do worker (60 s) para evitar reprocessamento duplo. |
| Message Retention | 4 dias | Janela para investigar falhas sem perder mensagens. |
| Max Receive Count (antes da DLQ) | 3 | 3 tentativas antes de mover para DLQ. |
| Batch Size (Lambda trigger) | 10 | Worker processa até 10 pagamentos por invocação — balanceia throughput e custo. |

---

### 4.5 Amazon EventBridge

**O que é:** Barramento de eventos serverless para arquitetura orientada a eventos.

**Por que usar:**
- **Extensibilidade:** Quando o worker termina de processar um pagamento, ele publica um evento (`payment.completed` ou `payment.failed`). Qualquer novo consumidor (notificação por email, sistema de auditoria, dashboard em tempo real) pode ser adicionado sem alterar o worker — princípio Open/Closed.
- **Desacoplamento entre domínios:** O worker não precisa conhecer quem vai consumir o evento. O barramento roteia conforme regras configuradas.
- **Rastreabilidade:** Todos os eventos ficam registrados e podem ser usados para auditoria.

**Regras planejadas no MVP:**

| Evento | Target | Descrição |
|---|---|---|
| `payment.completed` | CloudWatch Logs | Registra evento para análise e evidências |
| `payment.failed` | CloudWatch Logs | Registra falha para investigação |

> Em uma evolução futura, `payment.completed` poderia acionar um Lambda de notificação por SNS/SES.

---

### 4.6 Amazon S3 + CloudFront

**O que é:** S3 armazena arquivos estáticos; CloudFront os serve globalmente via CDN com HTTPS.

**Por que usar (para o frontend):**
- **Zero custo de servidor:** O painel React é compilado em arquivos estáticos (HTML, CSS, JS) e servido diretamente do S3. Não há servidor Node.js/Nginx para manter.
- **HTTPS automático:** CloudFront gerencia certificado SSL sem custo adicional.
- **Cache global:** Assets estáticos (JS, CSS) ficam em cache nas edges, reduzindo latência para o usuário.
- **Bucket privado + OAC:** O S3 fica privado; só o CloudFront pode acessar via Origin Access Control — boa prática de segurança.

---

### 4.7 Amazon CloudWatch

**O que é:** Serviço de monitoramento, logs e alertas da AWS.

**Por que usar:**
- **Logs centralizados:** Todas as Lambdas enviam logs automaticamente para CloudWatch Logs, sem configuração adicional.
- **Métricas de SQS:** Profundidade da fila (`ApproximateNumberOfMessagesVisible`) e mensagens na DLQ são métricas críticas para entender o comportamento sob carga.
- **Dashboard unificado:** Um único painel com latência da API, taxa de erro, throughput da fila e duração do worker — evidência visual obrigatória para o relatório técnico.
- **Alarmes:** Alerta se DLQ tiver mensagens (indica falhas no processamento) ou se a taxa de erro da API ultrapassar 5%.

---

## 5. Camadas do Sistema

```
┌─────────────────────────────────────────────────────────┐
│  CAMADA DE APRESENTAÇÃO                                  │
│  React SPA → S3 + CloudFront                            │
│  Responsável: renderizar UI, chamar API REST             │
├─────────────────────────────────────────────────────────┤
│  CAMADA DE ENTRADA                                       │
│  API Gateway (REST)                                      │
│  Responsável: roteamento, throttling, CORS, auth         │
├─────────────────────────────────────────────────────────┤
│  CAMADA DE APLICAÇÃO                                     │
│  Lambda Functions (handlers + worker)                    │
│  Responsável: lógica de negócio, validação, orquestração │
├─────────────────────────────────────────────────────────┤
│  CAMADA DE MENSAGERIA                                    │
│  SQS (payments-queue + payments-dlq)                     │
│  Responsável: desacoplar criação de processamento        │
├─────────────────────────────────────────────────────────┤
│  CAMADA DE EVENTOS                                       │
│  EventBridge (payments-bus)                              │
│  Responsável: propagar eventos de estado para consumers  │
├─────────────────────────────────────────────────────────┤
│  CAMADA DE PERSISTÊNCIA                                  │
│  DynamoDB (users + payments)                             │
│  Responsável: armazenar e consultar dados duráveis       │
├─────────────────────────────────────────────────────────┤
│  CAMADA DE OBSERVABILIDADE                               │
│  CloudWatch (Logs + Metrics + Dashboard + Alarms)        │
│  Responsável: visibilidade operacional do sistema        │
└─────────────────────────────────────────────────────────┘
```

---

## 6. Modelos de Dados (DynamoDB)

### Tabela `users`

```json
{
  "userId":    "uuid-v4",           // PK — partition key
  "name":      "João Silva",
  "email":     "joao@email.com",   // indexado no GSI email-index
  "cpf":       "123.456.789-00",
  "status":    "ACTIVE",           // ACTIVE | INACTIVE
  "createdAt": "2026-04-20T10:00:00Z"
}
```

**GSI `email-index`:** Permite verificar duplicidade de email em O(1) sem scan.

---

### Tabela `payments`

```json
{
  "paymentId":   "uuid-v4",         // PK — partition key
  "userId":      "uuid-v4",         // indexado no GSI userId-createdAt-index
  "amount":      150.00,
  "description": "Compra produto X",
  "method":      "PIX",             // PIX | BOLETO | CREDIT_CARD
  "status":      "COMPLETED",       // PENDING | PROCESSING | COMPLETED | FAILED
  "createdAt":   "2026-04-20T10:00:00Z",
  "updatedAt":   "2026-04-20T10:00:05Z",
  "errorReason": null               // preenchido quando status=FAILED
}
```

**GSI `userId-createdAt-index`:** Sort key = `createdAt`. Permite buscar todos os pagamentos de um usuário ordenados por data, com paginação eficiente.

**Máquina de estados do campo `status`:**

```
[criação via API]
       │
       ▼
   PENDING
       │
       │  worker inicia processamento
       ▼
  PROCESSING
       │
       ├──────────────────┐
       │ sucesso           │ falha
       ▼                  ▼
  COMPLETED           FAILED
```

---

## 7. API — Rotas e Contratos

Todos os endpoints são prefixados pelo URL base do API Gateway, ex: `https://<id>.execute-api.us-east-1.amazonaws.com/prod`

### Usuários

| Método | Rota | Descrição | Lambda |
|---|---|---|---|
| `POST` | `/users` | Cadastra novo usuário | users-handler |
| `GET` | `/users` | Lista todos os usuários | users-handler |
| `GET` | `/users/{userId}` | Busca usuário por ID | users-handler |

**POST /users — Request:**
```json
{
  "name":  "Maria Souza",
  "email": "maria@email.com",
  "cpf":   "987.654.321-00"
}
```

**POST /users — Response 201:**
```json
{
  "userId":    "a1b2c3d4-...",
  "name":      "Maria Souza",
  "email":     "maria@email.com",
  "status":    "ACTIVE",
  "createdAt": "2026-04-20T10:00:00Z"
}
```

---

### Pagamentos

| Método | Rota | Descrição | Lambda |
|---|---|---|---|
| `POST` | `/payments` | Cria e enfileira pagamento | payments-handler |
| `GET` | `/payments` | Lista todos os pagamentos (com filtros) | payments-handler |
| `GET` | `/payments/{paymentId}` | Consulta status de um pagamento | status-handler |
| `GET` | `/users/{userId}/payments` | Lista pagamentos de um usuário | payments-handler |

**POST /payments — Request:**
```json
{
  "userId":      "a1b2c3d4-...",
  "amount":      250.00,
  "description": "Assinatura mensal",
  "method":      "PIX"
}
```

**POST /payments — Response 202 (Accepted):**
```json
{
  "paymentId": "e5f6g7h8-...",
  "status":    "PENDING",
  "message":   "Pagamento recebido e enfileirado para processamento."
}
```

**GET /payments/{paymentId} — Response 200:**
```json
{
  "paymentId":   "e5f6g7h8-...",
  "userId":      "a1b2c3d4-...",
  "amount":      250.00,
  "method":      "PIX",
  "status":      "COMPLETED",
  "createdAt":   "2026-04-20T10:00:00Z",
  "updatedAt":   "2026-04-20T10:00:07Z",
  "errorReason": null
}
```

> **Por que 202 e não 201 para criação de pagamento?**  
> O pagamento ainda não foi processado quando a resposta é enviada. HTTP 202 ("Accepted") indica que a requisição foi recebida e está sendo processada de forma assíncrona — semanticamente correto e alinhado com REST.

---

## 8. Processamento Assíncrono — SQS + Worker Lambda

### Por que o processamento é assíncrono?

Em sistemas de pagamento reais, o processamento de uma transação pode envolver:
- Verificação anti-fraude (pode levar segundos)
- Consulta a sistemas externos (bancos, bandeiras de cartão)
- Fila de autorização com concorrência controlada

Se tudo fosse síncrono, o usuário ficaria aguardando por vários segundos com uma conexão HTTP aberta — péssima experiência e desperdício de recursos. Com a fila:

1. O cliente recebe resposta imediata (`202 PENDING`)
2. O processamento ocorre em background no ritmo que o sistema suporta
3. O cliente consulta o status quando quiser (`GET /payments/{id}`)

### Mensagem na fila SQS

```json
{
  "paymentId": "e5f6g7h8-...",
  "userId":    "a1b2c3d4-...",
  "amount":    250.00,
  "method":    "PIX",
  "timestamp": "2026-04-20T10:00:00Z"
}
```

### Lógica do Worker (payment-worker Lambda)

```
Para cada mensagem no batch:
  1. Parse da mensagem JSON
  2. Atualiza DynamoDB: status = PROCESSING
  3. Valida regras de negócio (simuladas):
     - amount > 0
     - userId existe na tabela users
     - method é válido
  4. Simula delay de processamento (ex: 500ms–2s aleatório)
  5. Decide resultado (para MVP: 95% sucesso, 5% falha aleatória)
  6. Atualiza DynamoDB: status = COMPLETED ou FAILED
  7. Publica evento no EventBridge
  8. Loga resultado no CloudWatch
```

### Dead Letter Queue (DLQ)

Se o worker lançar uma exceção não tratada (ex: DynamoDB indisponível), a mensagem retorna para a fila e será reentregue até 3 vezes. Após isso, vai para `payments-dlq`. Um alarme no CloudWatch dispara se a DLQ tiver qualquer mensagem, alertando a equipe de que há pagamentos que precisam de atenção manual.

---

## 9. Frontend — Painel Administrativo

**Tecnologia:** React (ou HTML/JS puro, se preferido pelo grupo)  
**Deploy:** Build estático hospedado no S3, servido via CloudFront

### Páginas e Funcionalidades

#### Página 1 — Dashboard (/)
- Contador de usuários cadastrados
- Contador de pagamentos por status (PENDING, PROCESSING, COMPLETED, FAILED)
- Gráfico de pagamentos criados nas últimas 24h (via CloudWatch Metrics ou contagem no DynamoDB)
- Link rápido para criar usuário e criar pagamento

**Por que:** Dá visibilidade operacional imediata — exigência do enunciado para "visualização de dados operacionais".

#### Página 2 — Usuários (/users)
- Tabela listando todos os usuários (id, nome, email, status, data de criação)
- Botão "Novo Usuário" → abre modal/formulário → chama `POST /users`
- Clique em usuário → navega para detalhe com pagamentos do usuário

**Por que:** Cumpre o requisito de cadastro de usuários com interface operável.

#### Página 3 — Pagamentos (/payments)
- Tabela listando todos os pagamentos com colunas: ID, usuário, valor, método, status, data
- Badge colorido por status (cinza=PENDING, amarelo=PROCESSING, verde=COMPLETED, vermelho=FAILED)
- Botão "Novo Pagamento" → modal com campos userId, amount, description, method → chama `POST /payments`
- Filtro por status e por userId
- Auto-refresh a cada 5 segundos (para ver status mudar de PENDING → COMPLETED em tempo real)

**Por que:** Central do MVP — demonstra o fluxo assíncrono visualmente ao avaliador.

#### Página 4 — Detalhe do Pagamento (/payments/:id)
- Todos os campos do pagamento
- Histórico de status com timestamps (createdAt, updatedAt)
- Botão "Atualizar Status" (consulta API novamente)
- Exibição de `errorReason` quando status=FAILED

**Por que:** Permite rastrear individualmente uma transação — fundamental para demonstração técnica.

#### Página 5 — Transações por Usuário (/users/:id)
- Dados do usuário
- Lista de todos os pagamentos daquele usuário (via GSI `userId-createdAt-index`)
- Sumário: total pago, número de transações por status

**Por que:** Usa o GSI do DynamoDB — demonstra uso correto de índices secundários.

---

## 10. Observabilidade

### CloudWatch Dashboard — Métricas essenciais

| Widget | Métrica monitorada | Justificativa |
|---|---|---|
| Latência API | `Latency` (API Gateway) | Detecta degradação de performance |
| Taxa de erro API | `4XXError` + `5XXError` | Identifica bugs ou sobrecarga |
| Invocações Lambda | `Invocations` por função | Volume de operações por componente |
| Duração Lambda | `Duration` (P50, P95, P99) | Identifica funções lentas |
| Profundidade da fila | `ApproximateNumberOfMessagesVisible` (SQS) | Detecta acúmulo de pagamentos pendentes |
| Mensagens na DLQ | `NumberOfMessagesSent` (DLQ) | Alerta de falhas no processamento |
| Erros Lambda | `Errors` por função | Identifica exceções não tratadas |

### Alarmes configurados

| Alarme | Condição | Ação |
|---|---|---|
| `DLQMessagesAlarm` | DLQ recebe qualquer mensagem | Log + notificação |
| `APIErrorRateAlarm` | Taxa de 5xx > 5% em 5 min | Log + notificação |
| `WorkerDurationAlarm` | P99 do worker > 45 s | Log (indica sobrecarga) |

---

## 11. Testes de Carga com JMeter

### Objetivo

Validar que a arquitetura suporta alta concorrência sem degradação severa de latência ou aumento significativo de taxa de erro.

### Cenários de Teste

#### Cenário 1 — Stress de Criação de Pagamentos
- **Objetivo:** Estressar o fluxo `POST /payments` + SQS + Worker
- **Configuração:** 500 threads, ramp-up de 60 s, duração 5 min
- **Métricas observadas:** Throughput (req/s), latência média/P99, taxa de erro
- **Critério de sucesso:** Taxa de erro < 1%, latência P99 < 2 s

#### Cenário 2 — Consultas Simultâneas de Status
- **Objetivo:** Estressar leituras no DynamoDB via `GET /payments/{id}`
- **Configuração:** 1000 threads, ramp-up de 30 s, duração 3 min
- **Métricas observadas:** Latência (espera-se < 200 ms no P99 — DynamoDB é muito rápido)
- **Critério de sucesso:** Taxa de erro < 0.1%, latência P99 < 500 ms

#### Cenário 3 — Carga Mista (Realista)
- **Objetivo:** Simular tráfego real com mix de operações
- **Configuração:** 300 threads com proporção: 20% POST /users, 40% POST /payments, 40% GET /payments/{id}
- **Métricas observadas:** Comportamento geral do sistema, throughput da fila SQS, duração do worker

#### Cenário 4 — Rajada (Burst)
- **Objetivo:** Testar o comportamento do API Gateway e Lambda diante de pico repentino
- **Configuração:** 0 → 2000 threads em 10 s, mantidos por 1 min
- **Métricas observadas:** Throttling responses (429), recuperação após pico

### Relatório Esperado

Para cada cenário, documentar:
1. Configuração do teste (screenshot do JMeter)
2. Gráficos de throughput e latência (exportados pelo JMeter)
3. Screenshot do CloudWatch Dashboard durante o teste
4. Análise crítica: o que aconteceu? O sistema comportou-se conforme esperado? Quais gargalos foram identificados?

---

## 12. Configurações de Capacidade e Limites

### DynamoDB — Modo On-Demand

Escolha do modo **On-Demand** (pay-per-request) ao invés de Provisioned:
- Em MVP/ambiente de teste, o tráfego é altamente variável (zero em repouso, picos durante testes JMeter)
- On-Demand escala automaticamente sem necessidade de estimar WCU/RCU antecipadamente
- Custo: paga-se exatamente pelo que é consumido, sem desperdício de capacidade provisionada ociosa

### Lambda — Concorrência Reservada do Worker

O `payment-worker` terá **concorrência reservada = 10**:
- Evita que o worker consuma toda a concorrência disponível da conta AWS durante testes de carga
- Controla a taxa de consumo da fila (10 workers × batch de 10 = 100 pagamentos processados simultaneamente)
- Protege o DynamoDB de writes excessivos simultâneos que poderiam causar throttling

### SQS — Visibility Timeout

**Visibility Timeout = 90 s** (worker timeout = 60 s):
- A regra é: `Visibility Timeout > Timeout da Lambda que consome`
- Se o worker trava ou cai, a mensagem só fica disponível para reprocessamento após 90 s — evita que dois workers processem o mesmo pagamento ao mesmo tempo

### API Gateway — Throttling

- **Rate:** 5.000 req/s por estágio (limite padrão)
- **Burst:** 10.000 req (pico instantâneo permitido)
- Durante os testes JMeter de burst, observaremos quantos `429 Too Many Requests` são retornados — isso faz parte da análise

---

## 13. Estrutura de Diretórios do Repositório

```
ProjetoCloud/
│
├── README.md                        ← este arquivo
│
├── infrastructure/                  ← definições de infra (IaC)
│   ├── template.yaml                ← AWS SAM ou CloudFormation
│   └── samconfig.toml               ← configuração de deploy do SAM
│
├── backend/                         ← código das Lambda Functions
│   ├── users/
│   │   ├── handler.py               ← Lambda: users-handler
│   │   └── requirements.txt
│   ├── payments/
│   │   ├── handler.py               ← Lambda: payments-handler
│   │   └── requirements.txt
│   ├── status/
│   │   ├── handler.py               ← Lambda: status-handler
│   │   └── requirements.txt
│   └── worker/
│       ├── handler.py               ← Lambda: payment-worker
│       └── requirements.txt
│
├── frontend/                        ← painel administrativo React
│   ├── public/
│   ├── src/
│   │   ├── pages/
│   │   │   ├── Dashboard.jsx
│   │   │   ├── Users.jsx
│   │   │   ├── Payments.jsx
│   │   │   ├── PaymentDetail.jsx
│   │   │   └── UserPayments.jsx
│   │   ├── services/
│   │   │   └── api.js               ← chamadas para o API Gateway
│   │   └── App.jsx
│   └── package.json
│
├── load-tests/                      ← scripts Apache JMeter
│   ├── stress-create-payments.jmx
│   ├── stress-query-status.jmx
│   ├── mixed-load.jmx
│   └── burst-test.jmx
│
└── docs/                            ← documentação técnica
    ├── architecture-diagram.png     ← diagrama exportado
    ├── api-spec.yaml                ← OpenAPI spec dos endpoints
    ├── load-test-report.md          ← análise dos resultados JMeter
    └── decisions.md                 ← ADRs (Architecture Decision Records)
```

---

## 14. Decisões Arquiteturais e Trade-offs

### Por que serverless e não contêineres (ECS/EKS)?

**Prós do serverless (Lambda):**
- Zero gerenciamento de SO e runtime
- Escala de zero automaticamente (ideal para MVP com tráfego variável)
- Integração nativa com SQS, API Gateway, EventBridge

**Contras (aceitos no MVP):**
- Cold start: primeira invocação após período de inatividade pode levar 500ms–1s a mais
- Limite de 15 min de execução por função (irrelevante para nosso caso)
- Debugging local é mais complexo (mitigado com AWS SAM Local)

**Conclusão:** Para um MVP com tráfego imprevisível e equipe pequena, Lambda é a escolha dominante. ECS/EKS faria sentido quando o sistema precisar de execução longa ou workloads que não se encaixam no modelo de invocação por evento.

---

### Por que DynamoDB e não PostgreSQL (RDS)?

**Prós do DynamoDB:**
- Sem VPC obrigatória, sem connection pool, sem gerenciamento de instância
- Latência < 5ms garantida em qualquer escala
- Paga pelo que usa (on-demand)

**Contras (aceitos no MVP):**
- Sem joins nativos — relacionamentos entre `users` e `payments` são resolvidos via GSI + queries separadas
- Sem transações ACID completas por padrão (DynamoDB tem TransactWrite, mas é mais limitado que SQL)

**Conclusão:** Para o padrão de acesso deste sistema (busca por ID, busca por userId, escrita intensiva durante testes de carga), DynamoDB é superiormente adequado. Se o projeto evoluísse para relatórios complexos com múltiplos joins, adicionaríamos um pipeline de analytics (ex: DynamoDB Streams → S3 → Athena).

---

### Por que SQS Standard e não FIFO?

**SQS FIFO** garante ordem de entrega e exatamente uma entrega — mas tem limite de **3.000 msg/s**.

**SQS Standard** não garante ordem, mas tem throughput virtualmente ilimitado.

Para pagamentos neste MVP, a ordem entre pagamentos diferentes não importa (cada um é independente). O risco de entrega duplicada é mitigado pelo worker verificar o status atual no DynamoDB antes de processar (idempotência: se status ≠ PENDING, o worker ignora a mensagem). Portanto, Standard é a escolha correta para maximizar throughput nos testes de carga.

---

### Por que React para o frontend?

- Componentização facilita construir tabelas reutilizáveis (mesma estrutura para users e payments)
- Ecossistema maduro (React Router para navegação entre páginas, Axios para chamadas HTTP)
- Build estático (`npm run build`) gera artefatos prontos para hospedar no S3

Se o grupo preferir simplicidade máxima, HTML + JavaScript puro também é válido — o enunciado permite. O importante é que o frontend seja funcional e demonstre todos os fluxos.

---

*Documento de rascunho arquitetural — sujeito a revisão conforme implementação avançar.*
