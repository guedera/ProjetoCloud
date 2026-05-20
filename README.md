# Plataforma de Pagamentos — MVP em Nuvem

Projeto da disciplina de Computação em Nuvem (Insper, 1º semestre de 2026).

Plataforma serverless de pagamentos construída inteiramente na AWS, com processamento assíncrono via fila, painel administrativo web e observabilidade nativa. O foco é demonstrar uma arquitetura cloud-native escalável e suas decisões técnicas.

Vídeo demonstrativo: https://youtu.be/cuYXtR2rNTs

---

## O que o sistema faz

- Cadastro e consulta de usuários via API REST
- Criação de pagamentos com processamento assíncrono (API → SQS → Lambda Worker)
- Atualização de status: `PENDING` → `APPROVED` / `REJECTED`
- Idempotência via `Idempotency-Key` para evitar duplicatas em retries
- Publicação de eventos de domínio (`PaymentApproved`, `PaymentRejected`) no EventBridge
- Painel administrativo em React hospedado no S3
- Observabilidade com logs estruturados, dashboard e alarmes no CloudWatch

---

## Arquitetura

```
Cliente → API Gateway → Lambda API → DynamoDB
                                  └→ SQS → Lambda Worker → DynamoDB
                                                         └→ EventBridge → CloudWatch
```

Diagrama completo e infraestrutura em [`docs/arquitetura.md`](docs/arquitetura.md).

---

## API

| Método | Rota | Descrição |
|--------|------|-----------|
| `POST` | `/users` | Cadastra usuário |
| `GET` | `/users` | Lista todos os usuários |
| `GET` | `/users/{id}` | Busca usuário por ID |
| `POST` | `/payments` | Cria pagamento (aceita `Idempotency-Key`) |
| `GET` | `/payments/{id}` | Consulta pagamento e status atual |
| `GET` | `/payments?userId=` | Lista pagamentos de um usuário |

Contrato completo em [`docs/api-contract.md`](docs/api-contract.md).

---

## Frontend

Painel em React 19 + Vite, hospedado no S3:
**http://pagamentos-frontend.s3-website-us-east-1.amazonaws.com/**

```bash
cd frontend && npm install && npm run dev   # http://localhost:5173
```

Documentação em [`docs/frontend.md`](docs/frontend.md).

---

## Testes de carga

Executados com Apache JMeter 5.6.3 — três planos em [`load-tests/`](load-tests/):

| Plano | Cenário | Throughput | Latência média | Erros |
|-------|---------|-----------|----------------|-------|
| A | 1.000 POSTs em rajada (50 threads) | 50,4 req/s | 505 ms | 0% |
| B | 1.000 GETs simultâneos (50 threads) | 73,7 req/s | 431 ms | 0% |
| C | Fluxo misto sustentado por 3 min | 42,2 req/s | 470 ms | 0% |

Análise completa em [`docs/testes-de-carga.md`](docs/testes-de-carga.md).

---

## Documentação

| Arquivo | Conteúdo |
|---------|----------|
| [`docs/arquitetura.md`](docs/arquitetura.md) | Diagrama, fluxo de dados e infraestrutura criada |
| [`docs/api-contract.md`](docs/api-contract.md) | Contrato completo da API REST |
| [`docs/decisions.md`](docs/decisions.md) | Justificativa das escolhas técnicas (SQS, DynamoDB, Lambda, etc.) |
| [`docs/conceitos.md`](docs/conceitos.md) | Explicação dos conceitos técnicos do projeto |
| [`docs/frontend.md`](docs/frontend.md) | Como rodar e publicar o frontend |
| [`docs/testes-de-carga.md`](docs/testes-de-carga.md) | Resultados e análise dos testes de carga |
