import { useState } from 'react';
import { api } from '../api';

export default function CreatePayment() {
  const [userId, setUserId] = useState('');
  const [amount, setAmount] = useState('');
  const [currency, setCurrency] = useState('BRL');
  const [description, setDescription] = useState('');
  const [result, setResult] = useState(null);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e) {
    e.preventDefault();
    setError(''); setResult(null); setLoading(true);
    try {
      const payment = await api.createPayment(
        { userId, amount: Number(amount), currency, description },
      );
      setResult(payment);
    } catch (err) {
      setError(`${err.status}: ${err.message}`);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div>
      <div className="section-header">
        <h2>Criar Pagamento</h2>
        <p>Submete um novo pagamento para processamento assíncrono.</p>
      </div>

      <div className="card">
        <div className="card-title">Novo pagamento</div>
        <form onSubmit={handleSubmit}>
          <div className="form-grid">
            <label className="span-2">User ID
              <input value={userId} onChange={e => setUserId(e.target.value)} placeholder="usr_xxxxxxxx" required />
            </label>
            <label>Valor
              <input type="number" min="0.01" step="0.01" value={amount} onChange={e => setAmount(e.target.value)} placeholder="0.00" required />
            </label>
            <label>Moeda
              <select value={currency} onChange={e => setCurrency(e.target.value)}>
                <option>BRL</option>
                <option>USD</option>
                <option>EUR</option>
              </select>
            </label>
            <label className="span-2">Descrição <span className="text-muted">(opcional)</span>
              <input value={description} onChange={e => setDescription(e.target.value)} placeholder="Ex: assinatura mensal" />
            </label>
          </div>
          <div className="form-actions">
            <button type="submit" className="btn btn-primary" disabled={loading}>
              {loading ? 'Enviando…' : 'Enviar pagamento'}
            </button>
          </div>
        </form>
      </div>

      {error && <div className="alert error">{error}</div>}
      {result && (
        <div className="result-block">
          <div className="result-block-header">Pagamento criado — status inicial</div>
          <pre>{JSON.stringify(result, null, 2)}</pre>
        </div>
      )}
    </div>
  );
}
