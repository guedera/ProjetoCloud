# Contrato de API

Base URL: `https://<api-id>.execute-api.us-east-1.amazonaws.com/dev`

---

## Usuários

### POST /users
Cadastra um novo usuário.

**Request:**
```json
{
  "name": "Guilherme",
  "email": "gui@teste.com"
}
```

**Response 201:**
```json
{
  "userId": "usr_8e5dd28b",
  "name": "Guilherme",
  "email": "gui@teste.com",
  "createdAt": "2026-05-16T17:45:37.667748+00:00"
}
```

**Erros:**
- `400` — campo obrigatório ausente (`name` ou `email`)
- `409` — email já cadastrado

---

### GET /users
Lista todos os usuários cadastrados, ordenados por data de criação.

**Response 200:**
```json
{
  "items": [
    {
      "userId": "usr_8e5dd28b",
      "name": "Guilherme",
      "email": "gui@teste.com",
      "createdAt": "2026-05-16T17:45:37.667748+00:00"
    }
  ],
  "count": 1
}
```

---

### GET /users/{id}
Retorna um usuário pelo ID.

**Response 200:**
```json
{
  "userId": "usr_8e5dd28b",
  "name": "Guilherme",
  "email": "gui@teste.com",
  "createdAt": "2026-05-16T17:45:37.667748+00:00"
}
```

**Erros:**
- `400` — id ausente
- `404` — usuário não encontrado

---

## Pagamentos

### POST /payments
Cria um novo pagamento e o envia para processamento assíncrono.

**Headers opcionais:**
- `Idempotency-Key: <string>` — garante que retries não criem pagamentos duplicados

**Request:**
```json
{
  "userId": "usr_8e5dd28b",
  "amount": 100,
  "currency": "BRL",
  "description": "descrição opcional"
}
```

**Response 202:**
```json
{
  "paymentId": "pay_22f05652",
  "userId": "usr_8e5dd28b",
  "amount": "100",
  "currency": "BRL",
  "description": "descrição opcional",
  "status": "PENDING",
  "createdAt": "2026-05-16T17:45:52.507377+00:00"
}
```

**Erros:**
- `400` — campo obrigatório ausente (`userId`, `amount` ou `currency`)
- `404` — usuário não encontrado
- `409` — pagamento duplicado (idempotency-key já usada)

---

### GET /payments/{id}
Retorna um pagamento pelo ID, incluindo o status atual.

**Response 200:**
```json
{
  "paymentId": "pay_22f05652",
  "userId": "usr_8e5dd28b",
  "amount": "100",
  "currency": "BRL",
  "description": "teste",
  "status": "APPROVED",
  "createdAt": "2026-05-16T17:45:52.507377+00:00",
  "updatedAt": "2026-05-16T17:45:53.435394+00:00"
}
```

**Status possíveis:** `PENDING` | `APPROVED` | `REJECTED`

**Erros:**
- `400` — id ausente
- `404` — pagamento não encontrado

---

### GET /payments?userId={userId}
Lista todos os pagamentos de um usuário.

**Query params:**
- `userId` (obrigatório)

**Response 200:**
```json
{
  "items": [
    {
      "paymentId": "pay_22f05652",
      "userId": "usr_8e5dd28b",
      "amount": "100",
      "currency": "BRL",
      "description": "teste",
      "status": "APPROVED",
      "createdAt": "2026-05-16T17:45:52.507377+00:00",
      "updatedAt": "2026-05-16T17:45:53.435394+00:00"
    }
  ],
  "count": 1
}
```

**Erros:**
- `400` — userId ausente
