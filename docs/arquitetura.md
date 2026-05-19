# Arquitetura da Plataforma de Pagamentos

Região AWS: **us-east-1**

## Diagrama

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
│  POST /users    GET /users    GET /users/{id}                           │
│  POST /payments GET /payments/{id}    GET /payments?userId=...          │
└──────┬──────────────────────────────────────────────────────────────────┘
       │ invoke (sync)
       ▼
┌──────────────────────────────────┐
│        Lambda — API Handler      │
│  (Python 3.12, us-east-1)        │
│                                  │
│  createUser  / listUsers         │
│  getUser     / createPayment     │
│  getPayment  / listPayments      │
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
       │          │  (Python 3.12, us-east-1)    │
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

## Fluxo de dados

1. **Cliente** faz requisição HTTP para o **API Gateway**.
2. API Gateway aciona a **Lambda API Handler** de forma síncrona.
3. Para operações de usuário (`/users`): Lambda lê/grava direto no **DynamoDB › Users**.
4. Para `POST /payments`: Lambda valida o usuário, grava o pagamento com `status=PENDING` no **DynamoDB › Payments** e envia mensagem para **SQS `payments-queue`**. Responde 202 imediatamente.
5. A **Lambda Worker** é disparada automaticamente pelo trigger SQS, simula o processamento e atualiza o status para `APPROVED` ou `REJECTED` no DynamoDB.
6. O Worker publica evento de domínio no **EventBridge** (`PaymentApproved` / `PaymentRejected`).
7. Regra do EventBridge registra os eventos no **CloudWatch Logs**.
8. Métricas de latência, erros e profundidade de fila ficam visíveis no dashboard do CloudWatch.

## Infraestrutura criada

| Recurso | Nome | Detalhes |
|---------|------|----------|
| DynamoDB | `Users` | Partition key: `userId` (String), on-demand |
| DynamoDB | `Payments` | Partition key: `paymentId` (String), GSI `userId-index`, on-demand |
| Lambda | `payments-api` | Python 3.12, invocada pelo API Gateway |
| Lambda | `payments-worker` | Python 3.12, trigger: `payments-queue`, batch size: 1 |
| API Gateway | `payments-api` | REST, estágio `dev`, CORS habilitado |
| SQS | `payments-queue` | Standard, DLQ: `payments-dlq`, max receives: 5 |
| SQS | `payments-dlq` | Standard — recebe mensagens com 5 falhas consecutivas |
| EventBridge | `payments-events` | Event bus customizado para eventos de domínio |
| EventBridge Rule | `log-payment-events` | Filtra `source: payments.worker` → CloudWatch Logs |
| CloudWatch Log Group | `/aws/events/payments` | Recebe `PaymentApproved` e `PaymentRejected` |
| CloudWatch Dashboard | `payments-dashboard` | Latência API Gateway p95, invocações/erros Lambda, profundidade SQS |
| CloudWatch Alarm | `sqs-message-age-too-old` | Dispara quando `ApproximateAgeOfOldestMessage` > 60s |
| S3 | `pagamentos-frontend` | Static website hosting — painel React |
| IAM Role | `payments-api-role` | Least-privilege: DynamoDB + SQS SendMessage |
| IAM Role | `payments-worker-role` | Least-privilege: SQS + DynamoDB UpdateItem + EventBridge |

## Variáveis de ambiente

**payments-api:**

| Variável | Valor |
|----------|-------|
| `USERS_TABLE` | `Users` |
| `PAYMENTS_TABLE` | `Payments` |
| `PAYMENTS_QUEUE_URL` | URL da `payments-queue` |

**payments-worker:**

| Variável | Valor |
|----------|-------|
| `PAYMENTS_TABLE` | `Payments` |
| `EVENT_BUS_NAME` | `payments-events` |

## Serviços utilizados

| Serviço | Papel |
|---------|-------|
| API Gateway (REST) | Entrada HTTP pública, CORS habilitado |
| Lambda — API | Lógica de usuários e pagamentos (síncrona) |
| Lambda — Worker | Processamento assíncrono dos pagamentos |
| DynamoDB | Persistência de Users e Payments |
| SQS Standard + DLQ | Fila de pagamentos com retry e captura de falhas |
| EventBridge | Eventos de domínio desacoplados |
| CloudWatch | Logs estruturados, métricas, dashboard, alarmes |
| S3 | Hospedagem do painel frontend estático |
| IAM | Permissões mínimas por Lambda (least-privilege) |

Decisões de escolha de cada serviço em [`decisions.md`](decisions.md).
