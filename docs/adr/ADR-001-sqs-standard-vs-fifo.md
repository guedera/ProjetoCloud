# ADR-001 — SQS Standard vs FIFO

**Data:** 2026-05-14  
**Status:** Aceito

## Contexto

O sistema de pagamentos precisa de uma fila para desacoplar a criação do pagamento (API síncrona) do seu processamento (worker assíncrono). A AWS oferece dois tipos de fila SQS:

- **Standard:** entrega pelo menos uma vez, sem garantia de ordem, throughput ilimitado.
- **FIFO:** entrega exatamente uma vez, ordem garantida, limitado a 3.000 mensagens/segundo.

## Decisão

Escolhemos **SQS Standard**.

## Justificativa

1. **Idempotência no worker é suficiente:** a entrega "pelo menos uma vez" do Standard significa que uma mensagem pode ser processada mais de uma vez em casos raros. Isso é aceitável porque implementamos idempotência no lado da API (`ConditionExpression` no DynamoDB) — um `paymentId` duplicado simplesmente não será gravado duas vezes.

2. **Ordem não é requisito:** pagamentos são independentes entre si. Não há motivo para que o pagamento A precise ser processado antes do pagamento B.

3. **Throughput:** Standard suporta volume praticamente ilimitado. FIFO teria um teto de 3.000 msg/s que poderia ser um gargalo em testes de carga futuros.

4. **Custo:** Standard é mais barato que FIFO.

## Consequências

- O worker deve ser idempotente (já é, via `UpdateItem` no DynamoDB — atualizar o status de um pagamento já processado não causa dano).
- A DLQ (`payments-dlq`) captura mensagens que falharam 5 vezes consecutivas, permitindo análise e reprocessamento manual.
- Se no futuro surgir requisito de ordem estrita (ex.: pagamentos de um mesmo usuário devem ser processados em sequência), seria necessário migrar para FIFO com `MessageGroupId` por `userId`.
