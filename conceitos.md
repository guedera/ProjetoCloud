# Glossário de Conceitos do Projeto

Explicações simples dos termos usados na arquitetura.

---

## CRUD

**C**reate, **R**ead, **U**pdate, **D**elete — as quatro operações básicas que qualquer sistema faz com dados.

| Letra | Operação | Exemplo no projeto |
|---|---|---|
| C | Criar | Cadastrar um usuário novo |
| R | Ler | Buscar os dados de um usuário |
| U | Atualizar | Mudar o status de um pagamento |
| D | Deletar | Remover um usuário |

É basicamente um nome bonito para "o sistema consegue salvar, buscar, editar e apagar coisas".

---

## Amazon CloudFront (CDN)

Imagine que seu site está hospedado num servidor em São Paulo. Um usuário no Japão acessa — ele vai ter que esperar o dado viajar de lá até aqui.

**CDN (Content Delivery Network)** resolve isso colocando cópias do seu site em servidores espalhados pelo mundo inteiro. Quando o usuário japonês acessa, ele busca a cópia mais próxima dele, não a original.

**CloudFront** é o CDN da AWS. No projeto, ele serve o painel administrativo (React) do ponto mais próximo de cada usuário, além de adicionar HTTPS automaticamente.

---

## Amazon S3

**S3 (Simple Storage Service)** é um serviço para guardar arquivos na nuvem. Pensa nele como um HD virtual gigante na internet.

No projeto, ele guarda os arquivos do painel administrativo: o HTML, o CSS e o JavaScript compilado do React. O CloudFront pega esses arquivos do S3 e entrega para o usuário.

> Curiosidade: S3 é tão confiável que a AWS garante 99.999999999% de durabilidade (11 noves). É praticamente impossível perder um arquivo guardado lá.

---

## React SPA

**React** é uma biblioteca JavaScript para construir interfaces de usuário (telas, botões, formulários).

**SPA (Single Page Application)** significa que o site inteiro é uma única página HTML. Em vez de o servidor mandar uma página nova a cada clique, o JavaScript atualiza só o trecho da tela que mudou — por isso é mais rápido e mais fluido (parecido com um app).

No projeto, o painel administrativo é um React SPA: você navega entre "Usuários", "Pagamentos" e "Dashboard" sem a página recarregar do zero.

---

## Amazon API Gateway

É a "porta de entrada" da sua aplicação. Quando o painel React quer buscar dados ou criar um pagamento, ele não fala diretamente com o banco de dados — ele manda uma requisição para o API Gateway, que decide o que fazer com ela.

Três coisas importantes que ele faz:

### REST API
**REST** é um padrão para criar APIs (interfaces de comunicação entre sistemas). Funciona sobre HTTP, igual um site. No projeto, o painel chama URLs como:
- `POST /payments` → para criar um pagamento
- `GET /payments/123` → para buscar o status do pagamento 123

### Throttling
Limita quantas requisições podem chegar por segundo. Se alguém tentar mandar 100.000 requisições de uma vez (acidente ou ataque), o API Gateway barra o excesso e responde `429 Too Many Requests`. Isso protege toda a arquitetura de travar.

### CORS
**Cross-Origin Resource Sharing** — uma regra de segurança dos navegadores. Por padrão, um site em `meu-painel.com` não pode fazer chamadas para uma API em `outra-api.com`. O CORS é a configuração que explicitamente permite isso. No projeto, precisa ser habilitado para o painel (S3/CloudFront) conseguir chamar o API Gateway.

### Autenticação via API Key
Uma chave secreta (tipo uma senha longa) que precisa ser enviada em toda requisição. Sem ela, o API Gateway rejeita. No MVP, é a forma mais simples de garantir que só o painel autorizado consegue usar a API.

---

## Invocação Síncrona

**Síncrono** = você pede, espera, recebe a resposta, aí continua.

Quando o API Gateway recebe uma requisição, ele chama (invoca) uma função Lambda e fica esperando ela terminar para devolver a resposta ao usuário. É igual ligar para alguém: você espera a outra pessoa atender e responder antes de desligar.

Oposto de assíncrono, onde você manda a mensagem e não espera resposta imediata.

---

## Camada de Aplicação

É onde fica o "cérebro" do sistema — o código que faz as coisas acontecerem.

No projeto, essa camada é formada pelas funções Lambda. Quando chega uma requisição, é aqui que o sistema decide:
- Esse usuário já existe? Posso criar o pagamento?
- Quais dados devo salvar no banco?
- O que devo responder?

Separar essa lógica em uma camada própria facilita manutenção: se a regra de negócio muda, você mexe só aqui, sem tocar no banco ou na API.

---

## Lambda (as três funções)

**AWS Lambda** é um serviço que executa código sem você precisar gerenciar nenhum servidor. Você escreve a função, sobe para a AWS, e ela roda automaticamente quando chamada — e para quando termina. Você paga só pelo tempo que ela rodou.

No projeto existem quatro Lambdas, cada uma com uma responsabilidade:

### `users-handler`
Cuida de tudo relacionado a usuários: criar, listar e buscar. Quando o painel clica em "Novo Usuário", é essa Lambda que recebe os dados, valida e salva no banco.

### `payments-handler`
Cuida da criação de pagamentos. Quando o painel cria um pagamento novo, essa Lambda salva o registro no banco com status `PENDING` e coloca uma mensagem na fila SQS para processamento posterior. Ela não processa o pagamento em si — só registra e enfileira.

### `status-handler`
Cuida das consultas. Quando o painel quer saber o status de um pagamento, essa Lambda simplesmente busca o registro no DynamoDB e devolve. Leitura pura, sem efeitos colaterais.

---

## Camada de Persistência

É onde os dados ficam guardados de forma permanente (mesmo que o servidor reinicie, os dados continuam lá).

No projeto, essa camada é o DynamoDB. Sem ela, tudo que o sistema fizesse seria esquecido assim que a Lambda terminasse de rodar.

---

## DynamoDB

Banco de dados da AWS. Diferente de bancos relacionais tradicionais (como MySQL ou PostgreSQL), o DynamoDB é **NoSQL** — não usa tabelas com colunas fixas nem SQL para consultas.

Principais características:
- **Rápido:** Respostas em 1–5 milissegundos, independente do tamanho do banco
- **Escalável:** Aguenta milhões de requisições por segundo sem configuração manual
- **Flexível:** Cada item pode ter campos diferentes (um pagamento via PIX pode ter campos que um boleto não tem)
- **Sem servidor:** A AWS gerencia tudo — você só cria a tabela e usa

No projeto temos duas tabelas: `users` (guarda usuários) e `payments` (guarda transações).

---

## UUID

**Universally Unique Identifier** — um identificador gerado aleatoriamente que é praticamente impossível de repetir.

Exemplo: `a3f7c2e1-4b8d-4f9a-b1c2-d3e4f5a6b7c8`

Em vez de usar IDs sequenciais (1, 2, 3...), o projeto usa UUIDs porque:
- Dois servidores podem gerar IDs ao mesmo tempo sem colisão
- Não expõe quantos registros existem no banco (segurança)
- Funciona perfeitamente em sistemas distribuídos

---

## GSI (Global Secondary Index)

No DynamoDB, você pesquisa rápido usando a chave primária (PK). Mas e se quiser pesquisar por outro campo?

**GSI** é um índice adicional que você cria para pesquisar por campos diferentes da PK, com a mesma velocidade.

**Exemplo no projeto:**
- A tabela `payments` tem PK = `paymentId`
- Para buscar "todos os pagamentos do usuário X", precisaria varrer a tabela inteira (lento e caro)
- Com o GSI `userId-createdAt-index`, a consulta é direta e instantânea

Pensa no GSI como o índice de um livro: em vez de ler página por página para achar um assunto, você vai direto no índice e pula para a página certa.

---

## Camada de Processamento Assíncrono

É a parte do sistema que processa trabalhos pesados em segundo plano, sem fazer o usuário esperar.

No projeto, quando um pagamento é criado, ele não é processado imediatamente. Em vez disso, vai para uma fila (SQS), e um worker (Lambda) processa depois, de forma independente. O usuário já recebeu a resposta e fechou a conexão — o processamento acontece sem ele saber.

---

## Amazon SQS

**Simple Queue Service** — um serviço de fila de mensagens.

Funciona exatamente como uma fila de banco: quem chega primeiro é atendido primeiro. Mas aqui, em vez de pessoas, são mensagens (dados).

**Por que usar uma fila?**
- O `payments-handler` joga mensagens na fila rápido
- O `payment-worker` consome no ritmo dele
- Se chegarem 10.000 pagamentos de uma vez, a fila segura tudo sem travar o sistema

Sem a fila, 10.000 requisições simultâneas precisariam ser processadas todas ao mesmo tempo — o banco de dados travaria.

---

## Fila

Uma estrutura onde mensagens entram por um lado e saem pelo outro na ordem que chegaram (**FIFO: First In, First Out** — primeiro a entrar, primeiro a sair).

```
Entrada →  [msg5] [msg4] [msg3] [msg2] [msg1]  → Saída (processamento)
```

No projeto, a fila `payments-queue` recebe os pagamentos criados e os entrega ao worker para processamento.

---

## DLQ (Dead Letter Queue)

**Fila de Mensagens Mortas** — uma fila separada para onde vão mensagens que falharam várias vezes.

**Exemplo:** Um pagamento foi para a fila, o worker tentou processar, deu erro. Tentou de novo, erro. Tentou uma terceira vez, erro. Em vez de ficar tentando para sempre, a mensagem vai para a DLQ.

A DLQ serve para:
- Não perder mensagens que falharam (auditoria)
- Investigar o que deu errado
- Reprocessar manualmente quando o problema for corrigido

No projeto, a `payments-dlq` é monitorada por um alarme: se qualquer mensagem chegar lá, o CloudWatch notifica.

---

## Event Source Mapping

É a configuração que conecta o SQS a uma função Lambda automaticamente.

Sem isso, você precisaria escrever um código que fica perguntando para o SQS a cada segundo "tem mensagem nova?". Com o Event Source Mapping, a própria AWS monitora a fila e chama a Lambda automaticamente quando há mensagens — sem polling manual.

É o "fio" que liga a fila ao worker.

---

## Lambda `payment-worker`

É a função Lambda responsável por processar os pagamentos da fila. Diferente dos handlers (que são chamados pelo API Gateway), o worker é chamado automaticamente pelo SQS via Event Source Mapping.

Fluxo do worker para cada mensagem recebida:
1. Pega o `paymentId` da mensagem
2. Atualiza status para `PROCESSING` no DynamoDB
3. Executa a lógica de validação (simula verificação anti-fraude, etc.)
4. Atualiza status para `COMPLETED` ou `FAILED`
5. Publica um evento no EventBridge avisando o resultado

O worker processa até 10 mensagens por vez (batch), o que é mais eficiente do que processar uma a uma.

---

## Camada de Eventos (EventBridge)

Depois que um pagamento é processado, o sistema precisa "avisar" que algo aconteceu. É aí que entra o EventBridge.

Em vez de o worker chamar diretamente outros sistemas (acoplamento), ele publica um evento genérico: "pagamento X foi concluído". Qualquer serviço que quiser saber disso pode se inscrever para receber esse aviso — sem o worker precisar conhecê-los.

**Vantagem:** Para adicionar uma nova funcionalidade (ex: enviar email quando pagamento for aprovado), você não precisa alterar o worker — só cria uma nova regra no EventBridge.

---

## Event Bus

É o "canal" pelo qual os eventos trafegam no EventBridge. Pensa nele como um rádio AM: o worker transmite (publica eventos), e quem quiser ouvir sintoniza no canal certo (cria uma regra).

No projeto, o Event Bus chama-se `payments-bus`. Ele recebe eventos como `payment.completed` e `payment.failed`, e roteia para os destinos configurados nas regras.

---

## CloudWatch

Serviço de monitoramento e logs da AWS. É os "olhos" do sistema — sem ele, você não sabe o que está acontecendo dentro da sua aplicação.

Três partes principais usadas no projeto:

### CloudWatch Logs
Toda vez que uma Lambda roda, ela pode escrever mensagens de log (tipo `print()` no Python). O CloudWatch armazena todos esses logs e permite pesquisar depois. Essencial para depurar erros.

### CloudWatch Metrics
Números sobre o comportamento do sistema ao longo do tempo:
- Quantas requisições chegaram por segundo?
- Qual foi a latência média?
- Quantos erros ocorreram?
- Quantas mensagens estão acumuladas na fila?

### CloudWatch Dashboard
Uma tela visual com gráficos dessas métricas em tempo real. É o painel de controle da infraestrutura — durante os testes JMeter, você olha aqui para ver o sistema sob pressão.

### CloudWatch Alarms
Regras automáticas: "se a DLQ receber qualquer mensagem, me avisa". O alarme monitora uma métrica e dispara uma ação quando ela ultrapassa um limite configurado.
