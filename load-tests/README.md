# Testes de Carga — JMeter

## Pré-requisitos

- Apache JMeter 5.6+ instalado
- Java 11+

## Planos disponíveis

| Arquivo | Descrição | Threads | Requisições |
|---------|-----------|---------|-------------|
| `plano-a-rajada-payments.jmx` | Rajada de `POST /payments` | 50 | 1000 |
| `plano-b-consultas-payments.jmx` | Consultas simultâneas `GET /payments/{id}` | 50 | 1000 |
| `plano-c-fluxo-misto.jmx` | Criação + consulta sustentados por 3 min | 50 (30+20) | contínuo |

Todos os planos criam o usuário de teste automaticamente no Setup antes de iniciar a carga.

## Como rodar (linha de comando)

```bash
# Plano A
jmeter -n -t load-tests/plano-a-rajada-payments.jmx \
  -l load-tests/resultados/plano-a.csv \
  -e -o load-tests/resultados/relatorio-a/

# Plano B
jmeter -n -t load-tests/plano-b-consultas-payments.jmx \
  -l load-tests/resultados/plano-b.csv \
  -e -o load-tests/resultados/relatorio-b/

# Plano C
jmeter -n -t load-tests/plano-c-fluxo-misto.jmx \
  -l load-tests/resultados/plano-c.csv \
  -e -o load-tests/resultados/relatorio-c/
```

A flag `-e -o <dir>` gera o relatório HTML automaticamente.

## Estrutura de resultados

```
resultados/
├── plano-a.csv          ← dados brutos (latência, status, etc.)
├── plano-b.csv
├── plano-c.csv
├── plano-c-lista.csv
├── relatorio-a/         ← relatório HTML (gerado pelo JMeter)
├── relatorio-b/
└── relatorio-c/
```

> Os arquivos `.csv` e pastas de relatório HTML estão no `.gitignore`. Commite apenas os `.jmx`.
