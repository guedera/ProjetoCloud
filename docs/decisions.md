# Decisões Arquiteturais

Este documento reúne as principais escolhas técnicas do projeto e a justificativa para cada uma delas.

---

## 1. SQS Standard em vez de FIFO

**Contexto:** a criação de um pagamento (`POST /payments`) precisa ser desacoplada do processamento real. A AWS oferece dois tipos de fila SQS — Standard e FIFO.

**Decisão:** SQS Standard.

**Por quê:**

- **Ordem não é requisito.** Pagamentos são independentes entre si; não há motivo para que o pagamento A seja processado antes do B.
- **Idempotência já está resolvida na camada de dados.** A entrega "pelo menos uma vez" do Standard pode duplicar mensagens em casos raros, mas o `ConditionExpression: attribute_not_exists(paymentId)` no DynamoDB garante atomicamente que um pagamento nunca é gravado duas vezes.
- **Throughput ilimitado.** Standard não tem teto de vazão; FIFO limita a 3.000 msg/s — um gargalo desnecessário para os volumes do projeto.
- **Custo menor.** Standard cobra menos por mensagem que FIFO.

**Consequência:** se no futuro surgir requisito de ordem estrita (ex.: pagamentos de um mesmo usuário devem ser processados em sequência), a migração para FIFO com `MessageGroupId` por `userId` resolveria.

---

## 2. DynamoDB em vez de RDS

**Contexto:** o sistema precisa persistir usuários e pagamentos. As opções principais são um banco relacional gerenciado (RDS/Aurora) e o banco NoSQL serverless (DynamoDB).

**Decisão:** DynamoDB.

**Por quê:**

- **Sem servidor para gerenciar.** DynamoDB não exige instância EC2, patching ou configuração de VPC obrigatória — alinha-se com a arquitetura 100% serverless do projeto.
- **Padrões de acesso simples.** Os acessos do MVP são diretos: buscar usuário por `userId`, buscar pagamento por `paymentId`, listar pagamentos por `userId`. DynamoDB atende tudo com chave primária e um GSI, sem JOINs.
- **Sem problema de connection pool com Lambda.** RDS mantém conexões persistentes; Lambda sobe e desce instâncias dinamicamente, o que pode esgotar o pool de conexões sob carga. DynamoDB usa HTTP — cada invocação é stateless.
- **Escalabilidade automática no modo on-demand.** Nenhuma configuração de capacidade necessária; nunca sofre throttling por pico imprevisto.
- **Custo no MVP.** No nível gratuito da AWS, DynamoDB oferece 25 GB e 25 unidades de capacidade por mês. RDS cobra pela instância rodando continuamente, mesmo sem tráfego.

**Consequência:** sem suporte nativo a transações ACID entre tabelas e sem queries ad-hoc flexíveis. Para relatórios complexos no futuro, a saída seria exportar para S3 + Athena.

---

## 3. AWS Lambda (serverless) em vez de EC2 ou ECS

**Contexto:** a lógica da aplicação precisa de um ambiente de execução. As opções clássicas são uma instância EC2, contêineres no ECS/Fargate ou funções Lambda.

**Decisão:** AWS Lambda.

**Por quê:**

- **Paga por uso, não por tempo ocioso.** Lambda cobra por milissegundo de execução real. Uma API com tráfego variável não gera custo em momentos sem requisições — EC2 e ECS cobram pela capacidade reservada independentemente do uso.
- **Sem gerenciamento de infraestrutura.** Não há SO para atualizar, nem cluster para escalar, nem load balancer para configurar manualmente.
- **Escala automática e imediata.** Cada requisição pode rodar em uma instância separada; sob rajada, a AWS sobe novas instâncias em paralelo sem intervenção.
- **Integração nativa com API Gateway e SQS.** O event source mapping Lambda ↔ SQS é nativo — o trigger é configurado em segundos no console, sem código extra de polling.

**Trade-off conhecido:** cold start. Quando uma Lambda fica inativa, a próxima invocação adiciona 300–800ms de latência para inicializar o runtime Python. Nos testes de carga isso se manifestou como o pico de 1.604ms no início da rajada (Plano A). Para mitigar em produção: Provisioned Concurrency.

---

## 4. API Gateway REST em vez de HTTP API

**Contexto:** a AWS oferece dois tipos de API Gateway: REST API (v1) e HTTP API (v2). HTTP API é mais barato e tem menor latência, mas oferece menos recursos.

**Decisão:** API Gateway REST.

**Por quê:**

- **Controle de CORS mais granular.** O frontend React está hospedado num domínio S3 diferente da API — CORS é obrigatório. A REST API permite configurar os headers de CORS por recurso e método diretamente no console, sem depender de lógica na Lambda.
- **Integração com estágio `dev`.** A REST API tem o conceito de estágios com deploy explícito, facilitando o rastreamento de versões em projetos acadêmicos.
- **Suficiente para o MVP.** O custo extra do REST em relação ao HTTP API é desprezível no volume do projeto.

**Consequência:** se o projeto evoluísse para produção com custo como prioridade, a migração para HTTP API reduziria ~70% o custo por requisição.

---

## 5. EventBridge em vez de chamar consumidores diretamente

**Contexto:** após processar um pagamento, o worker precisa notificar outros sistemas (logs, futuramente: notificações, auditoria, etc.).

**Decisão:** publicar eventos de domínio (`PaymentApproved`, `PaymentRejected`) no EventBridge.

**Por quê:**

- **Desacoplamento total entre produtor e consumidores.** O worker não precisa saber quem vai consumir o evento — publica e esquece. Novos consumidores (notificação por e-mail, webhook, analytics) são adicionados como regras no EventBridge sem alterar uma linha do worker.
- **Auditoria de domínio.** Os eventos ficam registrados no CloudWatch Logs com todos os campos necessários para rastrear o ciclo de vida de cada pagamento.
- **Extensibilidade.** Se a regra atual (log) for substituída ou complementada, a mudança é feita no EventBridge — o código permanece estável.

**Alternativa descartada:** invocar outra Lambda diretamente do worker. Isso criaria acoplamento e exigiria alteração do worker a cada novo consumidor.

---

## 6. CloudWatch em vez de ferramenta externa de observabilidade

**Contexto:** o sistema precisa de logs, métricas e alarmes.

**Decisão:** CloudWatch nativo.

**Por quê:**

- **Zero configuração de infraestrutura.** Lambda, API Gateway, SQS e DynamoDB já enviam métricas e logs para o CloudWatch automaticamente — sem agente, sem exportador, sem configuração extra.
- **Integração nativa com alarmes e dashboards.** O alarme `sqs-message-age-too-old` e o dashboard `payments-dashboard` foram criados em minutos no console.
- **Custo controlado no MVP.** O nível gratuito da AWS cobre 10 métricas customizadas, 5 GB de logs e 3 dashboards por mês — mais que suficiente para o projeto.

**Alternativa descartada:** Datadog ou Grafana + Prometheus. Teriam mais recursos de visualização, mas exigiriam agentes, exportadores e custo extra — overhead injustificável para um MVP.

---

## 7. S3 Static Website em vez de servidor web para o frontend

**Contexto:** o painel administrativo é uma aplicação React compilada — arquivos estáticos (HTML, CSS, JS).

**Decisão:** hospedagem estática no S3.

**Por quê:**

- **Sem servidor para gerenciar.** O S3 serve os arquivos diretamente via HTTP — não há instância EC2, Nginx ou contêiner para operar.
- **Custo mínimo.** Armazenamento e transferência de arquivos estáticos no S3 são extremamente baratos — praticamente zero no volume do projeto.
- **Deploy simples.** `npm run build` + `aws s3 sync` atualiza o frontend em segundos.

**Consequência:** sem HTTPS nativo no Static Website Hosting do S3 (o S3 serve HTTP puro). Para HTTPS em produção, a solução padrão é CloudFront na frente do bucket — não implementado no MVP por ser opcional.

---

## 8. IAM com permissões mínimas por Lambda (least privilege)

**Contexto:** as Lambdas precisam de permissão para acessar DynamoDB, SQS e EventBridge.

**Decisão:** uma IAM Role por Lambda, com permissões mínimas necessárias.

**Por quê:**

- **Superfície de ataque reduzida.** Se uma Lambda for comprometida, o atacante só tem acesso aos recursos que aquela função realmente precisa — não ao ambiente inteiro.
- **Rastreabilidade.** Logs do CloudTrail mostram exatamente qual função executou qual ação em qual recurso.
- **Boas práticas AWS.** Least privilege é o princípio fundamental de segurança em IAM — recomendado pela AWS Well-Architected Framework.

**Implementação:**
- `payments-api`: `PutItem` + `GetItem` + `Query` em Users/Payments + `SendMessage` em `payments-queue`
- `payments-worker`: `ReceiveMessage` + `DeleteMessage` + `GetQueueAttributes` em `payments-queue` + `UpdateItem` em Payments + `PutEvents` no EventBridge
