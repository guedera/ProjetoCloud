# Plataforma Escalável em Nuvem para Processamento de Pagamentos — MVP

Projeto da disciplina de Computação em Nuvem (Insper, 1º semestre de 2026).
O objetivo é construir um **MVP** de plataforma de pagamentos na AWS com cadastro de usuários, criação de pagamentos, processamento assíncrono via fila e consulta de status, acompanhada de um painel administrativo simples e testes de carga com JMeter.

> **Filosofia do MVP:** simplicidade primeiro. Cada sprint entrega um pedaço **funcional e testável** ponta a ponta. Nada de otimização precoce, nada de serviço a mais "por garantia".

---

## Convenção de localização das tarefas

Cada item de cada sprint indica **ONDE** ele é feito:

- 🟦 **[AWS Console]** — configurado manualmente na interface web da AWS (console.aws.amazon.com).
- 🟩 **[Repositório]** — código/arquivos versionados neste repositório Git.
- 🟨 **[Local]** — executado na máquina do desenvolvedor (testes, scripts, JMeter).
- 🟪 **[Documentação]** — escrito em arquivos `.md` dentro de [docs/](docs/).

---

## Estrutura prevista do repositório (será criada ao longo das sprints)

```
ProjetoCloud/
├── README.md                  ← este arquivo (visão geral + sprints)
├── backend/                   ← código das Lambdas (API + worker)
│   ├── api/
│   └── worker/
├── frontend/                  ← painel administrativo
├── infra/                     ← anotações/diagramas da infraestrutura AWS
├── load-tests/                ← planos JMeter (.jmx) e resultados
└── docs/                      ← documentação técnica e relatório final
```

---

# Sprints

## Sprint 0 — Fundação do projeto

**Objetivo:** preparar conta AWS, organizar repositório e alinhar a arquitetura no papel antes de escrever qualquer código.

| # | Tarefa | Onde |
|---|--------|------|
| 0.1 | Criar/validar conta AWS e usuário IAM com permissões mínimas para Lambda, DynamoDB, SQS, API Gateway, CloudWatch e S3. | 🟦 [AWS Console] |
| 0.2 | Configurar AWS CLI localmente (`aws configure`) com chaves do usuário IAM criado. | 🟨 [Local] |
| 0.3 | Definir região padrão do projeto (sugestão: `us-east-1`) e documentar. | 🟪 [Documentação] |
| 0.4 | Criar estrutura de pastas vazia conforme árvore acima (`backend/`, `frontend/`, `infra/`, `load-tests/`, `docs/`). | 🟩 [Repositório] |
| 0.5 | Desenhar diagrama de arquitetura inicial (API Gateway → Lambda → DynamoDB + SQS → Lambda Worker). | 🟪 [Documentação] em [docs/arquitetura.md](docs/arquitetura.md) |
| 0.6 | Definir contratos das APIs (rotas, payloads, status codes) — só no papel. | 🟪 [Documentação] em [docs/api-contract.md](docs/api-contract.md) |

**Entrega:** repositório organizado, conta AWS pronta, arquitetura desenhada e contratos de API definidos.

---

## Sprint 1 — Cadastro de usuários (primeira fatia ponta a ponta)

**Objetivo:** primeira rota funcionando ponta a ponta — `POST /users` e `GET /users/{id}` — para validar a integração API Gateway + Lambda + DynamoDB.

| # | Tarefa | Onde |
|---|--------|------|
| 1.1 | Criar tabela DynamoDB `Users` com chave primária `userId` (string). | 🟦 [AWS Console] |
| 1.2 | Implementar Lambda em Python (ou Node.js) com handlers para `createUser` e `getUser`. | 🟩 [Repositório] em [backend/api/](backend/api/) |
| 1.3 | Empacotar e fazer upload da Lambda (`.zip`) e configurar variáveis de ambiente (nome da tabela, região). | 🟦 [AWS Console] (upload) + 🟩 [Repositório] (código) |
| 1.4 | Conceder permissão IAM à Lambda para `dynamodb:PutItem` e `dynamodb:GetItem` na tabela `Users`. | 🟦 [AWS Console] |
| 1.5 | Criar API REST no API Gateway com recursos `/users` (POST) e `/users/{id}` (GET) integrados à Lambda. | 🟦 [AWS Console] |
| 1.6 | Habilitar CORS no API Gateway (necessário para o painel da Sprint 4). | 🟦 [AWS Console] |
| 1.7 | Fazer deploy do estágio `dev` no API Gateway e anotar a URL pública. | 🟦 [AWS Console] |
| 1.8 | Testar com `curl`/Postman e documentar exemplos de requisição/resposta. | 🟨 [Local] + 🟪 [Documentação] |

**Entrega:** consigo cadastrar e consultar um usuário via HTTP real.

---

## Sprint 2 — Criação de pagamentos com processamento assíncrono

**Objetivo:** receber pagamentos via API, enfileirar para processamento e ter um worker que consome a fila e atualiza o estado da transação. **Núcleo arquitetural do projeto.**

| # | Tarefa | Onde |
|---|--------|------|
| 2.1 | Criar tabela DynamoDB `Payments` com chave primária `paymentId` (string) e atributos como `userId`, `amount`, `status`, `createdAt`. | 🟦 [AWS Console] |
| 2.2 | Criar fila SQS `payments-queue` (Standard) e uma DLQ associada (`payments-dlq`). | 🟦 [AWS Console] |
| 2.3 | Implementar handler `createPayment` na Lambda da API: valida payload, grava no DynamoDB com `status=PENDING` e envia mensagem para SQS. | 🟩 [Repositório] em [backend/api/](backend/api/) |
| 2.4 | Implementar Lambda **worker** que é acionada por mensagens da SQS, simula processamento (ex.: `sleep` aleatório + decisão de sucesso/falha) e atualiza o `status` no DynamoDB para `APPROVED` ou `REJECTED`. | 🟩 [Repositório] em [backend/worker/](backend/worker/) |
| 2.5 | Criar a Lambda worker no console e configurar **trigger** SQS apontando para `payments-queue`. | 🟦 [AWS Console] |
| 2.6 | Conceder permissões IAM ao worker (`sqs:ReceiveMessage`, `sqs:DeleteMessage`, `dynamodb:UpdateItem`). | 🟦 [AWS Console] |
| 2.7 | Adicionar a rota `POST /payments` no API Gateway integrada à Lambda da API. | 🟦 [AWS Console] |
| 2.8 | Testar fluxo completo: criar pagamento → verificar mensagem na fila → confirmar status atualizado no DynamoDB. | 🟨 [Local] |

**Entrega:** pagamento criado pela API é processado de forma assíncrona pelo worker e tem seu status final persistido.

---

## Sprint 3 — Consulta de pagamentos e listagens

**Objetivo:** completar os fluxos de leitura para que o painel administrativo (Sprint 4) tenha o que exibir.

| # | Tarefa | Onde |
|---|--------|------|
| 3.1 | Implementar handler `getPayment` (`GET /payments/{id}`) — retorna pagamento e status atual. | 🟩 [Repositório] em [backend/api/](backend/api/) |
| 3.2 | Implementar handler `listPayments` (`GET /payments?userId=...`) — lista pagamentos de um usuário. | 🟩 [Repositório] em [backend/api/](backend/api/) |
| 3.3 | Avaliar criação de **GSI** (Global Secondary Index) na tabela `Payments` por `userId` para listagem eficiente. | 🟦 [AWS Console] |
| 3.4 | Adicionar as novas rotas no API Gateway e fazer redeploy do estágio `dev`. | 🟦 [AWS Console] |
| 3.5 | Atualizar [docs/api-contract.md](docs/api-contract.md) com as novas rotas. | 🟪 [Documentação] |

**Entrega:** API completa com todos os endpoints CRUD necessários para o painel.

---

## Sprint 4 — Painel administrativo (frontend)

**Objetivo:** entregar uma interface simples que demonstre todos os fluxos da plataforma. Estética não é critério; clareza é.

| # | Tarefa | Onde |
|---|--------|------|
| 4.1 | Escolher stack mínima (sugestão: HTML + JS puro ou React com Vite) e justificar em [docs/arquitetura.md](docs/arquitetura.md). | 🟪 [Documentação] |
| 4.2 | Implementar tela de **cadastro de usuários** consumindo `POST /users`. | 🟩 [Repositório] em [frontend/](frontend/) |
| 4.3 | Implementar tela de **criação de pagamentos** consumindo `POST /payments`. | 🟩 [Repositório] em [frontend/](frontend/) |
| 4.4 | Implementar tela de **listagem/consulta de pagamentos** com indicador visual de status (PENDING/APPROVED/REJECTED). | 🟩 [Repositório] em [frontend/](frontend/) |
| 4.5 | (Opcional) Criar bucket S3 com hospedagem estática + CloudFront para servir o painel publicamente. | 🟦 [AWS Console] |
| 4.6 | Documentar como rodar o frontend localmente apontando para a API real. | 🟪 [Documentação] |

**Entrega:** painel funcional capaz de exercitar todos os fluxos do sistema.

---

## Sprint 5 — Testes de carga com JMeter

**Objetivo:** simular cenários de estresse e analisar criticamente o comportamento da arquitetura.

| # | Tarefa | Onde |
|---|--------|------|
| 5.1 | Instalar Apache JMeter localmente. | 🟨 [Local] |
| 5.2 | Criar plano de teste **A** — rajada de `POST /payments` (ex.: 1000 requisições, 50 threads). | 🟩 [Repositório] em [load-tests/](load-tests/) (`.jmx`) |
| 5.3 | Criar plano de teste **B** — consultas simultâneas `GET /payments/{id}`. | 🟩 [Repositório] em [load-tests/](load-tests/) |
| 5.4 | Criar plano de teste **C** — fluxo misto (criação + consulta) sustentado por alguns minutos. | 🟩 [Repositório] em [load-tests/](load-tests/) |
| 5.5 | Habilitar métricas no CloudWatch (latência API Gateway, invocações Lambda, mensagens SQS, throttling DynamoDB). | 🟦 [AWS Console] |
| 5.6 | Executar os planos e exportar relatórios HTML do JMeter. | 🟨 [Local] |
| 5.7 | Escrever análise crítica: latência, taxa de erro, comportamento da fila sob carga, gargalos identificados. | 🟪 [Documentação] em [docs/relatorio-carga.md](docs/relatorio-carga.md) |

**Entrega:** evidências numéricas + interpretação técnica do comportamento sob carga.

---

## Sprint 6 — Documentação final, vídeo e entrega

**Objetivo:** consolidar entregáveis para a apresentação.

| # | Tarefa | Onde |
|---|--------|------|
| 6.1 | Finalizar [docs/arquitetura.md](docs/arquitetura.md) com diagrama atualizado e justificativa de cada serviço AWS escolhido. | 🟪 [Documentação] |
| 6.2 | Escrever relatório técnico consolidado em [docs/relatorio-final.md](docs/relatorio-final.md). | 🟪 [Documentação] |
| 6.3 | Garantir que README, contratos de API e instruções de execução estão atualizados. | 🟩 [Repositório] |
| 6.4 | Gravar vídeo de **5 minutos** apresentando arquitetura, demo do painel e resultados dos testes de carga. | 🟨 [Local] |
| 6.5 | Revisar custos AWS (CloudWatch Billing) e desligar/limpar recursos não usados após a entrega. | 🟦 [AWS Console] |

**Entrega:** projeto pronto para apresentação — código, documentação, testes, vídeo.

---

## Resumo do que vive ONDE

| Componente | Onde é feito | Observação |
|------------|--------------|------------|
| Tabelas DynamoDB | 🟦 AWS Console | criação manual, sem IaC neste MVP |
| Filas SQS (+ DLQ) | 🟦 AWS Console | idem |
| API Gateway (rotas, CORS, deploy) | 🟦 AWS Console | idem |
| Permissões IAM | 🟦 AWS Console | idem |
| Código das Lambdas (API + worker) | 🟩 Repositório | upload do `.zip` é feito no console |
| Frontend (painel) | 🟩 Repositório | hospedagem opcional em S3 (🟦) |
| Planos de teste JMeter | 🟩 Repositório | execução em 🟨 Local |
| Diagramas, contratos, relatórios | 🟪 Documentação (`docs/`) | tudo versionado |

---

## Próximo passo

Começar pela **Sprint 0** — preparar conta AWS, criar a estrutura de pastas e desenhar a arquitetura antes de escrever código.
