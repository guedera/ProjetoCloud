# Relatório de Testes de Carga — Sprint 5

## Ambiente

- **Data de execução:** 17/05/2026
- **Ferramenta:** Apache JMeter 5.6.3
- **Região AWS:** us-east-1
- **API Gateway:** `https://zll9wu9brj.execute-api.us-east-1.amazonaws.com/dev`
- **Arquitetura testada:** API Gateway → Lambda (Python) → DynamoDB + SQS → Lambda Worker

---

## Planos executados

### Plano A — Rajada de criação (`POST /payments`)

**Configuração:** 50 threads, 20 loops por thread, ramp-up de 10s → **1.000 requisições totais**

| Métrica | Valor |
|---------|-------|
| Total de requisições | 1.000 |
| Throughput | 50,4 req/s |
| Latência média | 505 ms |
| Latência mínima | 442 ms |
| Latência máxima | 1.604 ms |
| Taxa de erro | 0,00% |
| Duração total | ~20s |

**Observações:** A rajada de escrita foi absorvida sem erros. O pico de 1.604ms ocorreu no início do teste, provavelmente durante o cold start da Lambda ou no momento em que todas as 50 threads dispararam simultaneamente. A latência média de 505ms reflete o custo real da operação: validação do usuário no DynamoDB + gravação do pagamento + envio para SQS — três chamadas a serviços AWS em sequência.

---

### Plano B — Consultas simultâneas (`GET /payments/{id}`)

**Configuração:** 50 threads, 20 loops por thread, ramp-up de 5s → **1.000 requisições totais**

| Métrica | Valor |
|---------|-------|
| Total de requisições | 1.000 |
| Throughput | 73,7 req/s |
| Latência média | 431 ms |
| Latência mínima | 398 ms |
| Latência máxima | 556 ms |
| Taxa de erro | 0,00% |
| Duração total | ~14s |

**Observações:** Leituras foram consistentemente mais rápidas e estáveis que escritas — spread de apenas 158ms entre mínimo e máximo, contra 1.162ms no Plano A. Isso é esperado: `GET /payments/{id}` faz uma única leitura por chave primária no DynamoDB (`GetItem`), sem passar pela SQS. A estabilidade da latência indica que o DynamoDB não sofreu throttling e operou dentro da capacidade provisionada.

---

### Plano C — Fluxo misto sustentado (criação + consulta)

**Configuração:** 30 threads criando pagamentos + 20 threads consultando, por 3 minutos, ramp-up de 15s

| Métrica | Valor |
|---------|-------|
| Total de requisições | 7.621 |
| Throughput | 42,2 req/s |
| Latência média | 470 ms |
| Latência mínima | 395 ms |
| Latência máxima | 922 ms |
| Taxa de erro | 0,00% |
| Duração total | ~3min |

**Observações:** Com carga sustentada por 3 minutos e 50 threads simultâneas (mistas), a latência média ficou em 470ms — entre os valores dos planos A e B, o que é coerente com o mix de operações. A latência se manteve estável ao longo de toda a execução (sem degradação progressiva), indicando que a arquitetura serverless escala adequadamente sem acúmulo de filas ou esgotamento de conexões. O pico de 922ms ocorreu isoladamente, sem impacto na média geral.

---

## Análise consolidada

### Comportamento geral

A plataforma sustentou os três cenários sem nenhum erro (taxa de erro = 0% em 9.621 requisições totais). A ausência de erros sob rajada e carga sustentada valida a robustez da arquitetura para o volume testado.

### Latência

A latência ficou consistentemente na faixa de **400–500ms** para todos os cenários, com picos pontuais abaixo de 1.700ms. Para uma API serverless sem cache, esse número é aceitável — cada requisição envolve inicialização da Lambda (quando necessário), acesso ao DynamoDB e, no caso de criação, envio à SQS.

A diferença entre escrita (505ms) e leitura (431ms) confirma o overhead das operações adicionais no fluxo de criação: validação de usuário + PutItem + SendMessage.

### Throughput

| Cenário | req/s |
|---------|-------|
| Escrita pura (rajada) | 50,4 |
| Leitura pura | 73,7 |
| Misto sustentado | 42,2 |

A leitura atingiu throughput ~46% maior que a escrita, o que é esperado dado que envolve menos operações por requisição.

### Fila SQS sob carga

O Plano A criou 1.000 mensagens na fila em ~20 segundos. O worker Lambda consome a fila de forma assíncrona — durante o teste, a fila acumulou mensagens temporariamente e foi drenada pelo worker após o término da rajada. Esse comportamento é o esperado e demonstra o desacoplamento correto entre API e processamento.

### Gargalos identificados

**1. Cold start da Lambda**
O pico de 1.604ms no Plano A ocorreu no início, quando todas as threads dispararam ao mesmo tempo após o ramp-up. Cold starts da Lambda em Python adicionam ~300–800ms na primeira invocação. Sob carga sustentada (Plano C), esse efeito se dilui e a latência se estabiliza.

**2. Operações encadeadas na escrita**
O `POST /payments` encadeia três chamadas síncronas: `GetItem` (validar usuário) + `PutItem` (gravar pagamento) + `SendMessage` (enfileirar). Qualquer lentidão em uma delas afeta a latência total. Isso explica a latência média ~74ms maior na escrita em relação à leitura.

**3. Scan na listagem de usuários**
O handler `GET /users` usa `scan` na tabela Users sem paginação. Sob volume maior de usuários, esse endpoint degradaria progressivamente. Não foi testado diretamente neste sprint, mas é um ponto de atenção para escala futura.

### Pontos positivos

- **Zero erros** em todos os cenários — idempotência e validações funcionaram corretamente sob concorrência
- **Estabilidade sustentada** — sem degradação de latência ao longo dos 3 minutos do Plano C
- **Escalabilidade automática** — Lambda e DynamoDB (on-demand) absorveram os picos sem intervenção manual
- **Desacoplamento via SQS** — a API respondeu 202 imediatamente sem aguardar o processamento do worker

---

## Conclusão

A arquitetura se comportou dentro do esperado para um MVP sob carga moderada. Os principais limitadores para escala futura são o cold start da Lambda e as operações encadeadas na escrita — ambos endereçáveis com Provisioned Concurrency e otimização do fluxo de validação. A Sprint 5.5 irá tratar esses pontos com intervenções concretas e re-execução dos planos para comparação antes/depois.
