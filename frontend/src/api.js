const BASE_URL = import.meta.env.VITE_API_URL || '';

async function request(method, path, body, headers = {}) {
  let res;
  try {
    res = await fetch(`${BASE_URL}${path}`, {
      method,
      headers: { 'Content-Type': 'application/json', ...headers },
      body: body ? JSON.stringify(body) : undefined,
    });
  } catch (e) {
    throw { status: 0, message: `Falha de rede: ${e.message}` };
  }
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw { status: res.status, message: data.message || data.error || 'Erro desconhecido' };
  return data;
}

export const api = {
  createUser: (payload) => request('POST', '/users', payload),
  getUser: (id) => request('GET', `/users/${id}`),
  listUsers: () => request('GET', '/users'),

  createPayment: (payload) => request('POST', '/payments', payload),
  getPayment: (id) => request('GET', `/payments/${id}`),
  listPayments: (userId) => request('GET', `/payments?userId=${userId}`),
};
