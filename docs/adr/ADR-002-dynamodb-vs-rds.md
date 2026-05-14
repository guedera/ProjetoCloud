# ADR-002 — DynamoDB vs RDS

**Data:** 2026-05-14  
**Status:** Aceito

## Contexto

O sistema precisa persistir dois tipos de dado: usuários e pagamentos. Precisamos escolher entre um banco relacional gerenciado (RDS) e um banco NoSQL de chave-valor (DynamoDB).

## Decisão

Escolhemos **DynamoDB**.

## Justificativa

1. **Sem servidor para gerenciar:** DynamoDB é totalmente serverless — sem instância EC2, sem patching, sem configuração de VPC obrigatória. Isso se alinha com a arquitetura Lambda do projeto, onde não queremos gerenciar infraestrutura.

2. **Modelo de acesso simples:** os padrões de acesso do MVP são diretos — buscar usuário por `userId`, buscar pagamento por `paymentId`, listar pagamentos por `userId`. DynamoDB atende todos com chave primária e um GSI, sem necessidade de JOINs.

3. **Escalabilidade automática:** no modo on-demand, DynamoDB escala automaticamente com o tráfego sem configuração de capacidade. Em testes de carga, isso evita throttling sem intervenção manual.

4. **Integração nativa com Lambda:** boto3 + DynamoDB é o padrão da AWS para funções Lambda. Sem necessidade de gerenciar connection pool (problema comum com RDS + Lambda, que pode esgotar conexões sob carga).

5. **Custo no MVP:** no nível gratuito da AWS, DynamoDB oferece 25 GB de armazenamento e 25 unidades de capacidade gratuitas por mês. RDS exige uma instância rodando continuamente, com custo mesmo sem tráfego.

## Consequências

- Sem suporte a transações complexas entre tabelas (ex.: débito de saldo + criação de pagamento em uma única transação ACID). Para o MVP isso não é requisito.
- Queries flexíveis (ex.: filtros arbitrários, agregações) não são suportadas nativamente — requerem GSI ou scan completo. Se surgir necessidade de relatórios complexos, seria necessário exportar para S3 + Athena.
- Se no futuro o modelo de dados crescer com muitos relacionamentos entre entidades, uma migração para RDS (Aurora Serverless) seria considerada.
