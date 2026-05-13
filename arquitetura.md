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
│  POST /users          GET /users/{id}                                   │
│  POST /payments       GET /payments/{id}      GET /payments?userId=...  │
└──────┬──────────────────────────────────────────────────────────────────┘
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

## Fluxo de dados

1. **Cliente** faz requisição HTTP para o **API Gateway**.
2. API Gateway aciona a **Lambda API Handler** de forma síncrona.
3. Para operações de usuário (`/users`): Lambda lê/grava direto no **DynamoDB › Users**.
4. Para `POST /payments`: Lambda grava com `status=PENDING` no **DynamoDB › Payments** e envia mensagem para **SQS `payments-queue`**.
5. A **Lambda Worker** é disparada automaticamente pelo trigger SQS, simula o processamento e atualiza o status para `APPROVED` ou `REJECTED`.
6. O Worker publica evento de domínio no **EventBridge** (`PaymentApproved` / `PaymentRejected`).
7. Regra do EventBridge registra os eventos no **CloudWatch Logs**.

## Serviços e justificativa

| Serviço | Papel | Justificativa |
|---------|-------|---------------|
| API Gateway (REST) | Entrada HTTP pública, CORS | Gerenciado, escala automática, integração nativa com Lambda |
| Lambda — API | Lógica de usuários e pagamentos | Sem servidor, paga por invocação, sem ociosidade |
| Lambda — Worker | Processamento assíncrono | Desacopla a API do tempo de processamento |
| DynamoDB | Persistência de Users e Payments | Latência baixa, escala horizontal, sem esquema fixo |
| SQS Standard | Fila de pagamentos + DLQ | Desacoplamento, retry automático, DLQ para falhas |
| EventBridge | Eventos de domínio | Extensível sem alterar Producer; log de auditoria |
| CloudWatch | Observabilidade | Nativo AWS, sem infra extra |
| S3 + CloudFront | Frontend (opcional) | Hospedagem estática de baixo custo |
| IAM | Permissões por Lambda | Least-privilege, sem credenciais no código |
