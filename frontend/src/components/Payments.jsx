import { useState } from 'react';
import { api } from '../api';

function StatusBadge({ status }) {
  const cls = { PENDING: 'pending', APPROVED: 'approved', REJECTED: 'rejected' }[status] || 'pending';
  return <span className={`badge badge-${cls}`}>{status}</span>;
}

export default function Payments() {
  const [paymentId, setPaymentId] = useState('');
  const [userId, setUserId] = useState('');
  const [singleResult, setSingleResult] = useState(null);
  const [listResult, setListResult] = useState(null);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  async function handleGetOne(e) {
    e.preventDefault();
    setError(''); setSingleResult(null); setListResult(null); setLoading(true);
    try {
      setSingleResult(await api.getPayment(paymentId.trim()));
    } catch (err) {
      setError(`${err.status}: ${err.message}`);
    } finally {
      setLoading(false);
    }
  }

  async function handleList(e) {
    e.preventDefault();
    setError(''); setSingleResult(null); setListResult(null); setLoading(true);
    try {
      setListResult(await api.listPayments(userId.trim()));
    } catch (err) {
      setError(`${err.status}: ${err.message}`);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div>
      <div className="section-header">
        <h2>Consultar Pagamentos</h2>
        <p>Busque por ID ou liste todos os pagamentos de um usuário.</p>
      </div>

      <div className="card">
        <div className="card-title">Por Payment ID</div>
        <form onSubmit={handleGetOne}>
          <label>Payment ID
            <input value={paymentId} onChange={e => setPaymentId(e.target.value)} placeholder="pay_xxxxxxxx" required />
          </label>
          <div className="form-actions">
            <button type="submit" className="btn btn-primary" disabled={loading}>
              {loading ? 'Buscando…' : 'Buscar'}
            </button>
          </div>
        </form>
      </div>

      <div className="card">
        <div className="card-title">Por usuário</div>
        <form onSubmit={handleList}>
          <label>User ID
            <input value={userId} onChange={e => setUserId(e.target.value)} placeholder="usr_xxxxxxxx" required />
          </label>
          <div className="form-actions">
            <button type="submit" className="btn btn-primary" disabled={loading}>
              {loading ? 'Listando…' : 'Listar pagamentos'}
            </button>
          </div>
        </form>
      </div>

      {error && <div className="alert error">{error}</div>}

      {singleResult && (
        <div className="card">
          <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 14 }}>
            <span style={{ fontWeight: 600, fontSize: '0.9rem', color: 'var(--text-h)' }}>
              {singleResult.paymentId}
            </span>
            <StatusBadge status={singleResult.status} />
          </div>
          <div className="result-block">
            <div className="result-block-header">Detalhes</div>
            <pre>{JSON.stringify(singleResult, null, 2)}</pre>
          </div>
        </div>
      )}

      {listResult && (
        <div className="card">
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 14 }}>
            <span style={{ fontWeight: 600, fontSize: '0.9rem', color: 'var(--text-h)' }}>
              Pagamentos encontrados
            </span>
            <span className="badge badge-pending" style={{ fontSize: '0.75rem' }}>
              {listResult.count} {listResult.count === 1 ? 'resultado' : 'resultados'}
            </span>
          </div>

          {listResult.count === 0 ? (
            <div className="empty-state">Nenhum pagamento encontrado para este usuário.</div>
          ) : (
            <div className="table-wrap">
              <table>
                <thead>
                  <tr>
                    <th>Payment ID</th>
                    <th>Valor</th>
                    <th>Descrição</th>
                    <th>Status</th>
                    <th>Criado em</th>
                  </tr>
                </thead>
                <tbody>
                  {listResult.items.map(p => (
                    <tr key={p.paymentId}>
                      <td><code style={{ fontSize: '0.8rem' }}>{p.paymentId}</code></td>
                      <td>{Number(p.amount).toLocaleString('pt-BR', { style: 'currency', currency: p.currency })}</td>
                      <td className="text-muted">{p.description || '—'}</td>
                      <td><StatusBadge status={p.status} /></td>
                      <td className="text-muted">{new Date(p.createdAt).toLocaleString('pt-BR')}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
