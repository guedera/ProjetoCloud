import { useState } from 'react';
import Users from './components/Users';
import CreatePayment from './components/CreatePayment';
import Payments from './components/Payments';
import logo from './assets/card.svg';
import './App.css';

const TABS = [
  { id: 'users', label: 'Usuários' },
  { id: 'create-payment', label: 'Criar Pagamento' },
  { id: 'payments', label: 'Consultar Pagamentos' },
];

export default function App() {
  const [tab, setTab] = useState('users');

  return (
    <div className="app">
      <header>
        <img src={logo} alt="logo" style={{ height: 28, width: 28 }} />
        <h1>Painel de Pagamentos</h1>
        <nav>
          {TABS.map(t => (
            <button
              key={t.id}
              className={tab === t.id ? 'active' : ''}
              onClick={() => setTab(t.id)}
            >
              {t.label}
            </button>
          ))}
        </nav>
      </header>
      <main>
        {tab === 'users' && <Users />}
        {tab === 'create-payment' && <CreatePayment />}
        {tab === 'payments' && <Payments />}
      </main>
    </div>
  );
}
