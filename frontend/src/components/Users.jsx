import { useState } from 'react';
import { api } from '../api';

export default function Users() {
  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [lookupId, setLookupId] = useState('');
  const [result, setResult] = useState(null);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  async function handleCreate(e) {
    e.preventDefault();
    setError(''); setResult(null); setLoading(true);
    try {
      setResult(await api.createUser({ name, email }));
      setName(''); setEmail('');
    } catch (err) {
      setError(`${err.status}: ${err.message}`);
    } finally {
      setLoading(false);
    }
  }

  async function handleGet(e) {
    e.preventDefault();
    setError(''); setResult(null); setLoading(true);
    try {
      setResult(await api.getUser(lookupId.trim()));
    } catch (err) {
      setError(`${err.status}: ${err.message}`);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div>
      <div className="section-header">
        <h2>Usuários</h2>
        <p>Cadastre novos usuários ou consulte os existentes pelo ID.</p>
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
        <div className="card-title">Consultar usuário</div>
        <form onSubmit={handleGet}>
          <label>User ID
            <input value={lookupId} onChange={e => setLookupId(e.target.value)} placeholder="usr_xxxxxxxx" required />
          </label>
          <div className="form-actions">
            <button type="submit" className="btn btn-primary" disabled={loading}>
              {loading ? 'Buscando…' : 'Buscar'}
            </button>
          </div>
        </form>
      </div>

      {error && <div className="alert error">{error}</div>}
      {result && (
        <div className="result-block">
          <div className="result-block-header">Resposta</div>
          <pre>{JSON.stringify(result, null, 2)}</pre>
        </div>
      )}
    </div>
  );
}
