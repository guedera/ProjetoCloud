# Painel Administrativo — Frontend

## Acesso

O painel está hospedado publicamente no S3:

**http://pagamentos-frontend.s3-website-us-east-1.amazonaws.com/**

---

## Stack

- React 19 + Vite
- JavaScript puro (sem TypeScript)
- CSS customizado (sem framework de UI)

---

## Telas

### Usuários
- Cadastro de novo usuário (`POST /users`)
- Consulta de usuário por ID (`GET /users/{id}`)
- Listagem de todos os usuários com filtro por nome ou e-mail (`GET /users`)

### Criar Pagamento
- Formulário para criação de pagamento (`POST /payments`)
- Exibe o resultado com status inicial `PENDING`

### Consultar Pagamentos
- Consulta de pagamento por ID (`GET /payments/{id}`) com badge de status
- Listagem de pagamentos por User ID (`GET /payments?userId=...`) com tabela completa
- Seção de últimos 5 pagamentos ordenados por data

---

## Rodar localmente

**Pré-requisitos:** Node.js 18+

```bash
cd frontend
npm install
npm run dev
```

O painel abre em `http://localhost:5173` apontando para a API real na AWS.

A URL da API é configurada em `frontend/.env`:
```
VITE_API_URL=https://zll9wu9brj.execute-api.us-east-1.amazonaws.com/dev
```

---

## Gerar build e atualizar o S3

```bash
cd frontend
npm run build
```

Os arquivos gerados ficam em `frontend/dist/`. Para atualizar o S3, faça upload manual pelo console AWS:

1. Acesse o bucket do frontend no S3 → aba **Objects**
2. Delete os arquivos antigos
3. Faça upload do `index.html` e da pasta `assets/` de dentro de `dist/`

Ou, se tiver o AWS CLI configurado (substitua `<nome-do-bucket>` pelo nome real):
```bash
aws s3 sync dist/ s3://<nome-do-bucket> --delete
```

---

## Estrutura

```
frontend/
├── src/
│   ├── App.jsx              ← shell com navegação por abas
│   ├── App.css              ← estilos globais
│   ├── api.js               ← funções de chamada à API
│   ├── assets/
│   │   └── card.svg         ← logo do header
│   └── components/
│       ├── Users.jsx        ← tela de usuários
│       ├── CreatePayment.jsx ← tela de criação de pagamento
│       └── Payments.jsx     ← tela de consulta de pagamentos
├── .env                     ← URL da API (não versionado em produção)
└── vite.config.js
```
