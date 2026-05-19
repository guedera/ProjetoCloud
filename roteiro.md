# Roteiro — Vídeo do Projeto (5 minutos)

---

## [0:00 – 0:30] Introdução

Falar direto para a câmera ou narrar com a tela do repositório aberta.

> "Neste projeto desenvolvemos uma plataforma de pagamentos serverless na AWS como MVP da disciplina de Computação em Nuvem do Insper. O sistema permite cadastrar usuários, criar pagamentos, processar transações de forma assíncrona e consultar o status em tempo real — tudo usando serviços gerenciados da AWS, sem nenhum servidor para operar."

---

## [0:30 – 1:30] Arquitetura

Abrir o diagrama em `docs/arquitetura.md` ou uma imagem do diagrama. Passar pelos componentes enquanto fala.

> "A arquitetura é totalmente serverless. O cliente acessa a API pelo **API Gateway**, que aciona a **Lambda de API** de forma síncrona. Essa Lambda lê e grava no **DynamoDB** — duas tabelas: Users e Payments."

> "Quando um pagamento é criado, além de gravar no DynamoDB com status PENDING, a Lambda envia uma mensagem para uma fila **SQS Standard**. Isso devolve o 202 imediatamente para o cliente — sem esperar o processamento."

> "A **Lambda Worker** consome essa fila de forma assíncrona, simula a aprovação ou rejeição do pagamento, atualiza o status no DynamoDB e publica um evento no **EventBridge** — PaymentApproved ou PaymentRejected. Esses eventos ficam registrados no **CloudWatch Logs**."

> "Usamos SQS Standard ao invés de FIFO porque pagamentos são independentes entre si e a idempotência já está garantida no DynamoDB via ConditionExpression. Escolhemos DynamoDB ao invés de RDS porque é serverless, sem problema de connection pool com Lambda, e atende bem os padrões de acesso do MVP."

---

## [1:30 – 2:30] Demonstração — Painel Web

Abrir o painel no browser: `http://pagamentos-frontend.s3-website-us-east-1.amazonaws.com/`

**Passo 1 — Cadastrar usuário**
- Ir na aba Usuários
- Preencher nome e e-mail e cadastrar
- Mostrar o userId retornado (ex: `usr_8e5dd28b`)

> "O painel está hospedado no S3 como site estático — sem servidor web. Aqui cadastramos um usuário e recebemos o ID gerado."

**Passo 2 — Criar pagamento**
- Ir na aba Criar Pagamento
- Preencher userId, valor, moeda e descrição
- Mostrar o status PENDING na resposta

> "Criamos um pagamento. O sistema responde 202 imediatamente com status PENDING — o processamento está acontecendo de forma assíncrona na fila."

**Passo 3 — Consultar status**
- Ir na aba Consultar Pagamentos
- Buscar pelo paymentId
- Mostrar o status APPROVED ou REJECTED

> "Alguns segundos depois, consultamos o mesmo pagamento e o status já foi atualizado pelo worker para APPROVED ou REJECTED."

---

## [2:30 – 3:15] Demonstração — Console AWS

Mostrar rapidamente no console AWS (não precisa entrar em detalhes, só evidenciar que está rodando):

1. **Lambda** — mostrar as duas funções: `payments-api` e `payments-worker`
2. **SQS** — mostrar a `payments-queue` e a `payments-dlq`
3. **DynamoDB** — abrir a tabela Payments e mostrar alguns itens com status APPROVED/REJECTED
4. **CloudWatch** — mostrar o dashboard `payments-dashboard` com métricas de invocações e latência

> "Aqui vemos as duas Lambdas, a fila SQS com a DLQ para captura de falhas, os dados gravados no DynamoDB e o dashboard de observabilidade no CloudWatch com métricas de latência e invocações."

---

## [3:15 – 4:15] Testes de Carga

Abrir o relatório HTML do JMeter ou o `docs/testes-de-carga.md`.

> "Para validar a robustez da arquitetura, executamos três planos de teste com Apache JMeter."

Mostrar a tabela de resultados enquanto fala:

> "No Plano A, simulamos uma rajada de 1.000 POSTs com 50 threads simultâneas — atingimos 50 req/s com latência média de 505ms e **zero erros**."

> "No Plano B, 1.000 GETs simultâneos — 73 req/s e 431ms de média. Leituras são mais rápidas porque fazem uma única operação no DynamoDB, sem passar pela fila."

> "No Plano C, carga mista sustentada por 3 minutos — 42 req/s e latência estável ao longo de toda a execução, sem degradação progressiva. Isso evidencia que a arquitetura serverless escala automaticamente sem acúmulo de filas ou esgotamento de recursos."

> "O principal gargalo identificado foi o cold start da Lambda, responsável pelo pico de 1.600ms no início da rajada. A solução para produção seria Provisioned Concurrency."

---

## [4:15 – 5:00] Conclusão

Voltar para câmera ou tela do repositório/README.

> "O projeto entrega todos os requisitos: API REST, processamento assíncrono via fila, eventos de domínio no EventBridge, painel web funcional e testes de carga com análise crítica dos resultados."

> "As decisões arquiteturais — serverless, SQS Standard, DynamoDB, EventBridge — foram todas tomadas com justificativa técnica explícita, documentadas em `docs/decisions.md`."

> "O repositório com todo o código, infraestrutura e documentação está disponível no GitHub."

---

## Dicas de gravação

- Grave em **1080p** e sem fundo de janelas desnecessárias abertas
- Antes de gravar: tenha o painel aberto, o console AWS logado e o JMeter/relatório prontos
- Faça o cadastro de usuário **antes** de gravar para ter um userId real na mão para a demo de pagamento
- Se o worker demorar para processar na hora da gravação, grave o `GET /payments/{id}` em loop até mudar de PENDING — ou use um paymentId já processado de uma execução anterior
