import { useState } from 'react';
import { api } from '../api';

export default function Users() {
  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [emailSearch, setEmailSearch] = useState('');
  const [emailResult, setEmailResult] = useState(null);
  const [emailNotFound, setEmailNotFound] = useState(false);
  const [search, setSearch] = useState('');
  const [result, setResult] = useState(null);
  const [userList, setUserList] = useState(null);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const [listLoading, setListLoading] = useState(false);

  async function handleCreate(e) {
    e.preventDefault();
    setError(''); setResult(null); setLoading(true);
    try {
      setResult(await api.createUser({ name, email }));
      setName(''); setEmail('');
      if (userList) {
        const updated = await api.listUsers();
        setUserList(updated);
      }
    } catch (err) {
      setError(`${err.status}: ${err.message}`);
    } finally {
      setLoading(false);
    }
  }

  async function handleSearchByEmail(e) {
    e.preventDefault();
    setError(''); setEmailResult(null); setEmailNotFound(false); setLoading(true);
    try {
      const all = await api.listUsers();
      const found = all.items.find(u => u.email.toLowerCase() === emailSearch.trim().toLowerCase());
      if (found) {
        setEmailResult(found);
      } else {
        setEmailNotFound(true);
      }
    } catch (err) {
      setError(`${err.status}: ${err.message}`);
    } finally {
      setLoading(false);
    }
  }

  async function handleListUsers() {
    setError(''); setListLoading(true);
    try {
      setUserList(await api.listUsers());
    } catch (err) {
      setError(`${err.status}: ${err.message}`);
    } finally {
      setListLoading(false);
    }
  }

  const filteredUsers = userList
    ? userList.items.filter(u =>
        u.name.toLowerCase().includes(search.toLowerCase()) ||
        u.email.toLowerCase().includes(search.toLowerCase())
      )
    : null;

  return (
    <div>
      <div className="section-header">
        <h2>Usuários</h2>
        <p>Cadastre novos usuários ou consulte os existentes.</p>
      </div>

      <div className="card">
        <div className="card-title">Cadastrar usuário</div>
        <form onSubmit={handleCreate}>
          <div className="form-grid">
            <label>Nome
              <input value={name} onChange={e => setName(e.target.value)} placeholder="João Silva" required />
            </label>
            <label>E-mail
              <input type="email" value={email} onChange={e => setEmail(e.target.value)} placeholder="joao@email.com" required />
            </label>
          </div>
          <div className="form-actions">
            <button type="submit" className="btn btn-primary" disabled={loading}>
              {loading ? 'Cadastrando…' : 'Cadastrar'}
            </button>
          </div>
        </form>
      </div>

      <div className="card">
        <div className="card-title">Consultar por e-mail</div>
        <form onSubmit={handleSearchByEmail}>
          <label>E-mail
            <input type="email" value={emailSearch} onChange={e => setEmailSearch(e.target.value)} placeholder="joao@email.com" required />
          </label>
          <div className="form-actions">
            <button type="submit" className="btn btn-primary" disabled={loading}>
              {loading ? 'Buscando…' : 'Buscar'}
            </button>
          </div>
        </form>
        {emailNotFound && <div className="alert error" style={{ marginTop: 12 }}>Nenhum usuário encontrado com este e-mail.</div>}
        {emailResult && (
          <div className="result-block" style={{ marginTop: 12 }}>
            <div className="result-block-header">Usuário encontrado</div>
            <pre>{JSON.stringify(emailResult, null, 2)}</pre>
          </div>
        )}
      </div>

      {error && <div className="alert error">{error}</div>}

      {result && (
        <div className="result-block" style={{ marginBottom: 16 }}>
          <div className="result-block-header">Resposta</div>
          <pre>{JSON.stringify(result, null, 2)}</pre>
        </div>
      )}

      <div className="card">
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: userList ? 14 : 0 }}>
          <div className="card-title" style={{ margin: 0 }}>Todos os usuários</div>
          <button className="btn btn-primary" style={{ padding: '6px 14px', fontSize: '0.8rem' }} onClick={handleListUsers} disabled={listLoading}>
            {listLoading ? 'Carregando…' : userList ? 'Atualizar' : 'Carregar'}
          </button>
        </div>

        {userList && (
          <>
            <input
              value={search}
              onChange={e => setSearch(e.target.value)}
              placeholder="Filtrar por nome ou e-mail…"
              style={{ marginBottom: 12 }}
            />
            {filteredUsers.length === 0 ? (
              <div className="empty-state">Nenhum usuário encontrado.</div>
            ) : (
              <div className="table-wrap">
                <table>
                  <thead>
                    <tr>
                      <th>User ID</th>
                      <th>Nome</th>
                      <th>E-mail</th>
                      <th>Criado em</th>
                    </tr>
                  </thead>
                  <tbody>
                    {filteredUsers.map(u => (
                      <tr key={u.userId}>
                        <td><code style={{ fontSize: '0.8rem' }}>{u.userId}</code></td>
                        <td>{u.name}</td>
                        <td className="text-muted">{u.email}</td>
                        <td className="text-muted">{new Date(u.createdAt).toLocaleString('pt-BR')}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
}
