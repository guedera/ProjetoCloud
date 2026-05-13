# Documentos do Projeto

> Região padrão: **us-east-1** (todas as tarefas AWS usam essa região)

---

## Diagrama de Arquitetura

Arquivo de referência: [docs/arquitetura.md](docs/arquitetura.md)

```
┌─────────────────────────────────────────────────────────────────────────┐
│                              Cliente / Painel                           │
│                         (browser ou curl/Postman)                       │
└──────────────────────────────────┬──────────────────────────────────────┘
                                   │ HTTPS
                                   ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                          API Gateway (REST)                             │
│                                                                         │
│  POST /users          GET /users/{id}                                   │
│  POST /payments       GET /payments/{id}      GET /payments?userId=...  │
└──────┬───────────────────────────────────────────────────────────────── ┘
       │ invoke (sync)
       ▼
┌──────────────────────────────────┐
│        Lambda — API Handler      │
│  (Python/Node, us-east-1)        │
│                                  │
│  createUser  / getUser           │
│  createPayment / getPayment      │
│  listPayments                    │
└───┬───────────────┬──────────────┘
    │ PutItem/Get   │ SendMessage
    │               │
    ▼               ▼
┌──────────────┐  ┌──────────────────────────────┐
│   DynamoDB   │  │          SQS                 │
│              │  │                              │
│  ┌─────────┐ │  │  payments-queue (Standard)   │
│  │  Users  │ │  │  payments-dlq  (DLQ)         │
│  └─────────┘ │  └──────────────┬───────────────┘
│  ┌─────────┐ │                 │ trigger (event source mapping)
│  │Payments │ │                 ▼
│  └─────────┘ │  ┌──────────────────────────────┐
└──────▲───────┘  │      Lambda — Worker         │
       │          │  (Python/Node, us-east-1)    │
       │          │                              │
       │          │  • consome mensagem SQS      │
       │          │  • simula aprovação/rejeição │
       │          │  • UpdateItem → APPROVED     │
       └──────────│    ou REJECTED               │
      UpdateItem  │  • publica evento no         │
                  │    EventBridge               │
                  └──────────────┬───────────────┘
                                 │ PutEvents
                                 ▼
                  ┌──────────────────────────────┐
                  │         EventBridge          │
                  │  PaymentApproved             │
                  │  PaymentRejected             │
                  └──────────────┬───────────────┘
                                 │ regra → log
                                 ▼
                  ┌──────────────────────────────┐
                  │   CloudWatch Logs / Metrics  │
                  │   Dashboard + Alarmes        │
                  └──────────────────────────────┘
```

### Fluxo resumido

1. **Cliente** faz requisição HTTP para o **API Gateway**.
2. API Gateway aciona a **Lambda API Handler** de forma síncrona.
3. Para operações de usuário (`/users`): Lambda lê/grava direto no **DynamoDB › Users**.
4. Para `POST /payments`: Lambda grava o pagamento em **DynamoDB › Payments** com `status=PENDING` e envia mensagem para **SQS `payments-queue`**.
5. A **Lambda Worker** é disparada automaticamente pelo trigger SQS, simula o processamento e atualiza o `status` no DynamoDB para `APPROVED` ou `REJECTED`.
6. Após atualizar, o Worker publica um evento de domínio no **EventBridge**.
7. Uma regra do EventBridge registra os eventos no **CloudWatch Logs** (consumidor de exemplo).
8. Métricas de latência, erros e profundidade de fila ficam visíveis no **dashboard CloudWatch**.

### Serviços AWS utilizados

| Serviço | Papel |
|---------|-------|
| API Gateway (REST) | Entrada HTTP pública, CORS habilitado |
| Lambda — API | Lógica de usuários e pagamentos (síncrona) |
| Lambda — Worker | Processamento assíncrono dos pagamentos |
| DynamoDB — Users | Persistência dos usuários |
| DynamoDB — Payments | Persistência e status dos pagamentos |
| SQS Standard | Fila de processamento de pagamentos |
| SQS DLQ | Captura mensagens com falha repetida |
| EventBridge | Publicação de eventos de domínio desacoplados |
| CloudWatch | Logs estruturados, métricas, dashboard, alarmes |
| S3 + CloudFront | (opcional, Sprint 4) Hospedagem do painel frontend |
| IAM | Permissões mínimas por Lambda (least-privilege) |

---

## Infraestrutura criada

### Sprint 1
| Recurso | Nome | Detalhes |
|---------|------|----------|
| DynamoDB | `Users` | Partition key: `userId` (String), on-demand |
| Lambda | `payments-api` | Python 3.12, handler: `lambda_function.lambda_handler` |
| API Gateway | `payments-api` | REST, estágio `dev`, CORS habilitado |
| IAM Policy | `lambda-users-dynamodb` | `PutItem` + `GetItem` em `Users`, `PutItem` + `GetItem` + `Query` em `Payments`, `SendMessage` em `payments-queue` |

### Sprint 2
| Recurso | Nome | Detalhes |
|---------|------|----------|
| DynamoDB | `Payments` | Partition key: `paymentId` (String), on-demand |
| SQS | `payments-queue` | Standard, DLQ: `payments-dlq`, max receives: 5 |
| SQS | `payments-dlq` | Standard |
| Lambda | `payments-worker` | Python 3.12, trigger: `payments-queue`, batch size: 1 |
| IAM Policy | `lambda-worker-permissions` | `ReceiveMessage` + `DeleteMessage` + `GetQueueAttributes` em `payments-queue`, `UpdateItem` em `Payments` |

### Variáveis de ambiente

**payments-api:**
| Variável | Valor |
|----------|-------|
| `USERS_TABLE` | `Users` |
| `PAYMENTS_TABLE` | `Payments` |
| `PAYMENTS_QUEUE_URL` | URL da `payments-queue` (salva no `.env`) |

**payments-worker:**
| Variável | Valor |
|----------|-------|
| `PAYMENTS_TABLE` | `Payments` |

---

## Contratos de API

Base URL: `https://<api-id>.execute-api.us-east-1.amazonaws.com/dev`

Todas as respostas usam `Content-Type: application/json`.

---

### POST /users

Cadastra um novo usuário.

**Request**
```json
POST /users
Content-Type: application/json

{
  "name": "João Silva",
  "email": "joao@exemplo.com"
}
```

| Campo | Tipo | Obrigatório | Descrição |
|-------|------|-------------|-----------|
| name | string | sim | Nome completo |
| email | string | sim | E-mail único do usuário |

**Responses**

`201 Created`
```json
{
  "userId": "usr_a1b2c3d4",
  "name": "João Silva",
  "email": "joao@exemplo.com",
  "createdAt": "2026-05-13T18:00:00Z"
}
```

`400 Bad Request` — campo obrigatório ausente ou inválido
```json
{ "error": "missing_field", "message": "email is required" }
```

`409 Conflict` — e-mail já cadastrado
```json
{ "error": "conflict", "message": "email already exists" }
```

---

### GET /users/{id}

Retorna os dados de um usuário.

**Request**
```
GET /users/usr_a1b2c3d4
```

**Responses**

`200 OK`
```json
{
  "userId": "usr_a1b2c3d4",
  "name": "João Silva",
  "email": "joao@exemplo.com",
  "createdAt": "2026-05-13T18:00:00Z"
}
```

`404 Not Found`
```json
{ "error": "not_found", "message": "user not found" }
```

---

### POST /payments

Cria um pagamento. Aceita `Idempotency-Key` para evitar duplicatas em retries.

**Request**
```json
POST /payments
Content-Type: application/json
Idempotency-Key: <uuid-gerado-pelo-cliente>

{
  "userId": "usr_a1b2c3d4",
  "amount": 150.00,
  "currency": "BRL",
  "description": "Pedido #42"
}
```

| Campo | Tipo | Obrigatório | Descrição |
|-------|------|-------------|-----------|
| userId | string | sim | ID do usuário pagador |
| amount | number | sim | Valor positivo |
| currency | string | sim | Código ISO 4217 (ex: `BRL`) |
| description | string | não | Texto livre |

**Responses**

`202 Accepted` — pagamento enfileirado para processamento
```json
{
  "paymentId": "pay_x9y8z7w6",
  "userId": "usr_a1b2c3d4",
  "amount": 150.00,
  "currency": "BRL",
  "description": "Pedido #42",
  "status": "PENDING",
  "createdAt": "2026-05-13T18:01:00Z"
}
```

`400 Bad Request`
```json
{ "error": "missing_field", "message": "amount is required" }
```

`404 Not Found` — userId inexistente
```json
{ "error": "not_found", "message": "user not found" }
```

`409 Conflict` — `Idempotency-Key` já processada (retorna o pagamento original)
```json
{
  "paymentId": "pay_x9y8z7w6",
  "status": "PENDING",
  "createdAt": "2026-05-13T18:01:00Z"
}
```

---

### GET /payments/{id}

Retorna um pagamento e seu status atual.

**Request**
```
GET /payments/pay_x9y8z7w6
```

**Responses**

`200 OK`
```json
{
  "paymentId": "pay_x9y8z7w6",
  "userId": "usr_a1b2c3d4",
  "amount": 150.00,
  "currency": "BRL",
  "description": "Pedido #42",
  "status": "APPROVED",
  "createdAt": "2026-05-13T18:01:00Z",
  "updatedAt": "2026-05-13T18:01:05Z"
}
```

| Campo `status` | Significado |
|----------------|-------------|
| `PENDING` | Enfileirado, aguardando worker |
| `APPROVED` | Processado com sucesso |
| `REJECTED` | Processamento falhou |

`404 Not Found`
```json
{ "error": "not_found", "message": "payment not found" }
```

---

### GET /payments?userId={userId}

Lista todos os pagamentos de um usuário.

**Request**
```
GET /payments?userId=usr_a1b2c3d4
```

**Query params**

| Param | Tipo | Obrigatório | Descrição |
|-------|------|-------------|-----------|
| userId | string | sim | Filtra pagamentos do usuário |

**Responses**

`200 OK`
```json
{
  "items": [
    {
      "paymentId": "pay_x9y8z7w6",
      "amount": 150.00,
      "currency": "BRL",
      "status": "APPROVED",
      "createdAt": "2026-05-13T18:01:00Z"
    },
    {
      "paymentId": "pay_a1b2c3d4",
      "amount": 75.00,
      "currency": "BRL",
      "status": "PENDING",
      "createdAt": "2026-05-13T18:05:00Z"
    }
  ],
  "count": 2
}
```

`400 Bad Request` — `userId` ausente
```json
{ "error": "missing_param", "message": "userId is required" }
```

`200 OK` com lista vazia — userId válido mas sem pagamentos
```json
{ "items": [], "count": 0 }
```
