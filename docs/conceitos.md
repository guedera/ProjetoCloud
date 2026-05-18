# Conceitos do Projeto

Este documento explica todos os conceitos técnicos utilizados na plataforma — serviços AWS, tecnologias de frontend e ferramentas de teste de carga.

---

## Serviços AWS

### Amazon API Gateway

Serviço gerenciado da AWS que expõe endpoints HTTP públicos e os conecta a outros serviços (neste projeto, ao AWS Lambda). Funciona como a "porta de entrada" da aplicação: recebe requisições do browser ou de clientes HTTP, autentica e roteia para o handler correto, e devolve a resposta.

Neste projeto foi criada uma API do tipo **REST** com estágio `dev`, CORS habilitado (necessário para o frontend React chamar a API do browser) e integração direta com a Lambda da API.

**Por que não HTTP API?** A API REST oferece mais controle sobre CORS e mapeamentos de integração, suficiente para o MVP.

---

### AWS Lambda

Serviço de computação **serverless** — você sobe o código (Python, Node.js, etc.) e a AWS executa sob demanda, sem precisar gerenciar servidores. Você paga apenas pelo tempo de execução efetivo (medido em milissegundos).

Neste projeto existem duas Lambdas:

- **payments-api:** contém toda a lógica da API (criar usuário, buscar usuário, criar pagamento, buscar pagamento, listar pagamentos). É invocada de forma síncrona pelo API Gateway a cada requisição.
- **payments-worker:** processa os pagamentos de forma assíncrona. É disparada automaticamente pelo trigger SQS sempre que chega uma nova mensagem na fila.

**Cold start:** quando uma Lambda fica inativa por alguns minutos, a AWS desaloca o container. Na próxima invocação, há um atraso de 300–800ms para inicializar o runtime Python e importar as dependências — isso é chamado de cold start. É o principal responsável pelos picos de latência observados nos testes de carga.

---

### Amazon DynamoDB

Banco de dados **NoSQL** totalmente gerenciado, baseado em chave-valor e documentos JSON. Não há servidor para configurar, escala automaticamente e oferece latência de milissegundos em qualquer volume.

Neste projeto existem duas tabelas:

- **Users:** chave primária `userId` (String). Armazena nome, e-mail e data de criação.
- **Payments:** chave primária `paymentId` (String), com um **GSI** (Global Secondary Index) por `userId` para permitir listar pagamentos de um usuário sem fazer scan completo da tabela.

**GSI (Global Secondary Index):** índice adicional criado sobre um atributo que não é a chave primária. Permite queries eficientes por `userId` sem varrer a tabela inteira.

**Modos de capacidade:**
- **Provisionado:** você define quantas leituras/escritas por segundo. Barato em volume constante, mas sofre throttling (erro 429) se exceder o limite.
- **On-demand:** a AWS escala automaticamente. Mais caro por operação, mas nunca sofre throttling.

As tabelas deste projeto usam **on-demand**.

---

### Amazon SQS (Simple Queue Service)

Serviço de **filas de mensagens** gerenciado. Permite desacoplar dois componentes: o produtor (API) coloca a mensagem na fila e segue em frente; o consumidor (worker) lê a mensagem no seu próprio ritmo.

Neste projeto:

- **payments-queue (Standard):** recebe uma mensagem por cada `POST /payments`. O worker Lambda consome essas mensagens e processa os pagamentos.
- **payments-dlq (Dead Letter Queue):** fila de "morgue". Se o worker falhar 5 vezes consecutivas ao processar uma mensagem, ela é movida automaticamente para a DLQ para análise posterior.

**SQS Standard vs FIFO:**
- **Standard:** entrega "pelo menos uma vez" (pode duplicar em casos raros), sem garantia de ordem, throughput ilimitado. Escolhido neste projeto.
- **FIFO:** entrega exatamente uma vez, ordem garantida, limitado a 3.000 msg/s.

**Por que Standard?** Pagamentos são independentes entre si (não precisam de ordem) e a idempotência implementada na API (`ConditionExpression` do DynamoDB) já protege contra duplicatas.

---

### Amazon EventBridge

Serviço de **barramento de eventos** (event bus). Permite que componentes publiquem eventos de domínio sem saber quem vai consumi-los — o desacoplamento máximo.

Neste projeto o worker publica dois eventos após processar cada pagamento:
- `PaymentApproved` — quando o pagamento é aprovado
- `PaymentRejected` — quando é rejeitado

Uma regra do EventBridge captura esses eventos e os envia para um log group no CloudWatch (consumidor de exemplo). No futuro, outros consumidores (notificação por e-mail, atualização de saldo, webhook) poderiam ser adicionados sem alterar o worker.

---

### Amazon CloudWatch

Serviço de **observabilidade** da AWS. Agrega logs, métricas e alarmes de todos os serviços.

Neste projeto:

- **Logs estruturados:** todas as Lambdas emitem logs em JSON com `correlationId` para rastrear uma requisição do início ao fim.
- **Dashboard:** painel com métricas de latência p95/p99 do API Gateway, invocações e erros das Lambdas, profundidade da fila SQS e throttling do DynamoDB.
- **Alarme:** dispara quando a mensagem mais antiga da fila tem mais de 60 segundos — indica que o worker está lento ou parado.

---

### Amazon S3 (Simple Storage Service)

Serviço de **armazenamento de objetos**. Usado neste projeto para hospedar o frontend React como site estático — os arquivos HTML, CSS e JavaScript são servidos diretamente pelo S3 sem necessidade de servidor web.

**Static website hosting:** funcionalidade do S3 que habilita um bucket a responder requisições HTTP como se fosse um servidor web tradicional.

---

### AWS IAM (Identity and Access Management)

Serviço de **controle de acesso** da AWS. Define quem pode fazer o quê em quais recursos.

Neste projeto cada Lambda tem uma **IAM Role** com permissões mínimas necessárias (princípio do least privilege):

- **payments-api:** pode fazer `PutItem` e `GetItem` nas tabelas Users e Payments, `Query` em Payments, e `SendMessage` na payments-queue.
- **payments-worker:** pode fazer `ReceiveMessage`, `DeleteMessage` e `GetQueueAttributes` na payments-queue, `UpdateItem` em Payments, e `PutEvents` no EventBridge.

Nenhuma Lambda tem credenciais hardcoded — as permissões são concedidas via Role associada à função.

---

### Idempotência

Conceito de que uma operação executada múltiplas vezes produz o mesmo resultado que executada uma única vez. Importante em sistemas distribuídos onde retries são comuns.

Neste projeto a idempotência é implementada em dois pontos:

1. **POST /payments com Idempotency-Key:** o cliente envia um header `Idempotency-Key` único. A API usa esse valor para gerar um `paymentId` determinístico e usa `ConditionExpression: attribute_not_exists(paymentId)` no DynamoDB — se o pagamento já existe, a operação é rejeitada atomicamente e o pagamento original é retornado.
2. **Worker:** o `UpdateItem` do DynamoDB é naturalmente idempotente — atualizar o status de um pagamento já processado não causa dano.

---

### Processamento assíncrono

Padrão arquitetural onde a operação não precisa ser concluída para que o sistema responda ao cliente. A API aceita o pedido (HTTP 202 Accepted), persiste a intenção e devolve imediatamente. O processamento real acontece em background, desacoplado.

Neste projeto: `POST /payments` retorna 202 com `status=PENDING` assim que grava no DynamoDB e enfileira na SQS. O worker processa depois e atualiza o status para `APPROVED` ou `REJECTED`. O cliente consulta o status com `GET /payments/{id}`.

---

### Eventos de domínio

Eventos que representam fatos relevantes do negócio — algo que aconteceu. São imutáveis e carregam o contexto necessário para qualquer consumidor reagir.

Neste projeto: `PaymentApproved` e `PaymentRejected` são eventos de domínio publicados no EventBridge. Qualquer serviço futuro (notificações, auditoria, analytics) pode reagir a eles sem alterar o worker.

---

## Frontend

### React

Biblioteca JavaScript para construção de interfaces de usuário baseadas em **componentes**. Cada componente é uma função que retorna HTML (via JSX) e gerencia seu próprio estado. O React re-renderiza automaticamente a interface quando o estado muda.

Neste projeto os componentes principais são:
- `Users.jsx` — tela de cadastro e listagem de usuários
- `CreatePayment.jsx` — formulário de criação de pagamento
- `Payments.jsx` — consulta e listagem de pagamentos

---

### Vite

Ferramenta de **build e desenvolvimento** para projetos JavaScript modernos. Substitui o webpack com uma abordagem mais rápida: em desenvolvimento serve os arquivos diretamente via ES modules (sem bundle), e em produção gera um bundle otimizado.

Neste projeto `npm run dev` inicia o servidor de desenvolvimento com hot reload, e `npm run build` gera os arquivos estáticos em `frontend/dist/` prontos para upload no S3.

---

### JSX

Extensão de sintaxe do JavaScript que permite escrever HTML dentro do código JS. O Vite transforma JSX em chamadas `React.createElement()` durante o build. Não é HTML real — é açúcar sintático para construção de componentes React.

---

### Variáveis de ambiente (`.env`)

Mecanismo para configurar valores que variam por ambiente (desenvolvimento, produção) sem hardcodar no código. O Vite expõe variáveis prefixadas com `VITE_` para o código do frontend.

Neste projeto `VITE_API_URL` define a URL base da API Gateway, permitindo que o frontend aponte para a API real na AWS.

---

### CORS (Cross-Origin Resource Sharing)

Mecanismo de segurança do browser que bloqueia requisições HTTP feitas de um domínio para outro domínio diferente, a menos que o servidor destino autorize explicitamente.

Neste projeto o frontend está em um domínio S3 e a API está no domínio do API Gateway — domínios diferentes. Por isso o API Gateway precisa responder com headers `Access-Control-Allow-Origin: *` para que o browser permita as chamadas. Isso foi configurado no API Gateway e também é retornado pela Lambda em todas as respostas.

---

## Testes de carga

### Apache JMeter

Ferramenta open-source de **teste de carga e performance**. Simula múltiplos usuários fazendo requisições simultâneas a um sistema e coleta métricas de latência, throughput e taxa de erro.

Neste projeto foram criados três planos de teste (`.jmx`):

- **Plano A:** rajada de 1.000 `POST /payments` com 50 threads simultâneas
- **Plano B:** 1.000 consultas `GET /payments/{id}` com 50 threads simultâneas
- **Plano C:** fluxo misto sustentado por 3 minutos — 30 threads criando + 20 consultando

---

### Thread group

No JMeter, um **thread group** representa um grupo de usuários virtuais. Cada thread simula um usuário independente fazendo requisições sequencialmente. Configurações principais:

- **Número de threads:** quantos usuários simultâneos
- **Ramp-up:** tempo para atingir o número total de threads (evita sobrecarregar o sistema de uma vez)
- **Loops:** quantas vezes cada thread repete o plano

---

### Throughput (req/s)

Número de requisições que o sistema processa por segundo. Indica a **capacidade** do sistema. Nos testes deste projeto:

| Cenário | Throughput |
|---------|-----------|
| Escrita pura | 50,4 req/s |
| Leitura pura | 73,7 req/s |
| Misto sustentado | 42,2 req/s |

---

### Latência

Tempo entre o envio da requisição e o recebimento da resposta. Métricas importantes:

- **Média (Avg):** valor central, sensível a outliers
- **Mínimo/Máximo:** piso e teto observados
- **p95/p99:** 95% ou 99% das requisições ficaram abaixo desse valor — mais representativo que a média para avaliar experiência do usuário

Nos testes deste projeto a latência média ficou entre 431ms e 505ms dependendo do cenário.

---

### Taxa de erro

Percentual de requisições que retornaram erro (status HTTP 4xx/5xx ou timeout). Nos três planos executados a taxa foi **0%** — nenhuma requisição falhou.

---

### Relatório HTML do JMeter

O JMeter gera um relatório HTML completo com gráficos de throughput, latência ao longo do tempo, distribuição de tempos de resposta e erros. Gerado com as flags `-e -o <diretório>` ao rodar em modo headless.

---

### Dead Letter Queue (DLQ)

Fila especial que recebe mensagens que não puderam ser processadas após um número máximo de tentativas. Evita que mensagens problemáticas fiquem travando a fila principal em loop infinito.

Neste projeto a `payments-dlq` recebe mensagens que falharam 5 vezes na `payments-queue`. Para reprocessar, basta mover as mensagens de volta para a fila principal (redrive) pelo console AWS.

---

### ConditionExpression (DynamoDB)

Operação condicional do DynamoDB que só executa a escrita se uma condição for verdadeira — de forma **atômica**. Se a condição falhar, a operação inteira é rejeitada sem efeito colateral.

Neste projeto usado em dois lugares:
- `POST /users`: `attribute_not_exists(email)` — impede e-mails duplicados
- `POST /payments` com Idempotency-Key: `attribute_not_exists(paymentId)` — impede pagamentos duplicados
