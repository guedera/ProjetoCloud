# Plataforma Escalável em Nuvem para Processamento de Pagamentos — MVP

Projeto da disciplina de Computação em Nuvem (Insper, 1º semestre de 2026).

Plataforma de pagamentos construída na AWS com arquitetura serverless, processamento assíncrono via fila e painel administrativo web. Desenvolvida como MVP com foco em escalabilidade, observabilidade e decisões técnicas justificadas.

---

## O que o sistema faz

- Cadastro e consulta de usuários
- Criação de pagamentos com processamento assíncrono (fila SQS → worker Lambda)
- Consulta de status de pagamentos (`PENDING` → `APPROVED` / `REJECTED`)
- Publicação de eventos de domínio (`PaymentApproved`, `PaymentRejected`) no EventBridge
- Painel administrativo web (React + Vite) hospedado no S3
- Idempotência via `Idempotency-Key` para evitar pagamentos duplicados em retries
- Observabilidade com logs estruturados, dashboard e alarmes no CloudWatch

---

## Arquitetura


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


Diagrama completo e fluxo detalhado em [`arquitetura.md`](arquitetura.md).

---

## Serviços AWS utilizados

| Serviço | Papel | Por que foi escolhido |
|---------|-------|-----------------------|
| **API Gateway (REST)** | Entrada HTTP pública com CORS | Gerenciado, escala automática, integração nativa com Lambda |
| **Lambda — API** | Lógica de usuários e pagamentos | Serverless, sem custo em ociosidade, sem servidor para gerenciar |
| **Lambda — Worker** | Processamento assíncrono dos pagamentos | Desacopla a API do tempo de processamento; escala independente |
| **DynamoDB** | Persistência de usuários e pagamentos | Serverless, latência baixa, escala automática on-demand, sem VPC obrigatória |
| **SQS Standard** | Fila de pagamentos + DLQ | Desacoplamento, retry automático, DLQ para falhas; Standard escolhido sobre FIFO por throughput ilimitado e ordem desnecessária (ver ADR-001) |
| **EventBridge** | Eventos de domínio pós-processamento | Desacoplamento total: novos consumidores sem alterar o worker |
| **CloudWatch** | Logs, métricas, dashboard, alarmes | Nativo AWS, zero configuração de infra |
| **S3** | Hospedagem do frontend estático | Simples, barato, sem servidor web |
| **IAM** | Permissões mínimas por Lambda | Least-privilege: cada Lambda acessa só o que precisa |

Decisões arquiteturais detalhadas em [`docs/adr/`](docs/adr/).

---

## API

Base URL: `https://zll9wu9brj.execute-api.us-east-1.amazonaws.com/dev`

| Método | Rota | Descrição |
|--------|------|-----------|
| `POST` | `/users` | Cadastra usuário |
| `GET` | `/users` | Lista todos os usuários |
| `GET` | `/users/{id}` | Busca usuário por ID |
| `POST` | `/payments` | Cria pagamento (aceita `Idempotency-Key`) |
| `GET` | `/payments/{id}` | Consulta pagamento e status |
| `GET` | `/payments?userId=` | Lista pagamentos de um usuário |

Contrato completo em [`docs/api-contract.md`](docs/api-contract.md).

---

## Testes de carga

Executados com Apache JMeter 5.6.3. Três planos em [`load-tests/`](load-tests/):

| Plano | Cenário | Resultado |
|-------|---------|-----------|
| A | 1.000 POSTs em rajada (50 threads) | 50,4 req/s · 505ms avg · 0% erro |
| B | 1.000 GETs simultâneos (50 threads) | 73,7 req/s · 431ms avg · 0% erro |
| C | Fluxo misto sustentado por 3 min (50 threads) | 42,2 req/s · 470ms avg · 0% erro |

Análise completa em [`docs/relatorio-carga.md`](docs/relatorio-carga.md).

---

## Frontend

Painel administrativo em React 19 + Vite, hospedado no S3.

```bash
cd frontend
npm install
npm run dev   # http://localhost:5173
```

Documentação em [`docs/frontend.md`](docs/frontend.md).

---

## Documentação

| Arquivo | Conteúdo |
|---------|----------|
| [`arquitetura.md`](arquitetura.md) | Diagrama, fluxo de dados e infraestrutura criada |
| [`docs/api-contract.md`](docs/api-contract.md) | Contrato completo da API REST |
| [`docs/conceitos.md`](docs/conceitos.md) | Explicação de todos os conceitos técnicos do projeto |
| [`docs/frontend.md`](docs/frontend.md) | Como rodar e publicar o frontend |
| [`docs/relatorio-carga.md`](docs/relatorio-carga.md) | Resultados e análise dos testes de carga |
| [`docs/adr/ADR-001`](docs/adr/ADR-001-sqs-standard-vs-fifo.md) | Decisão: SQS Standard vs FIFO |
| [`docs/adr/ADR-002`](docs/adr/ADR-002-dynamodb-vs-rds.md) | Decisão: DynamoDB vs RDS |
| [`sprints.md`](sprints.md) | Histórico completo das sprints do projeto |
