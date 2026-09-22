import React, { useState, useEffect, useCallback } from 'react';
import { useAuth } from '../AuthContext';
import ProductChecklist from './ProductChecklist';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api';

function useProductList() {
  const [products, setProducts] = useState([]);
  useEffect(() => {
    fetch(`${API_BASE_URL}/catalog/products`)
      .then((res) => (res.ok ? res.json() : []))
      .then((data) => setProducts(Array.isArray(data) ? data : []))
      .catch(() => setProducts([]));
  }, []);
  return products;
}

function ProfileCard({ user }) {
  return (
    <div className="dash-card">
      <h2 className="dash-card-title">Your Account</h2>
      <div className="dash-profile-row"><span>Name</span><strong>{user.name}</strong></div>
      <div className="dash-profile-row"><span>Email</span><strong>{user.email}</strong></div>
      <div className="dash-profile-row"><span>Role</span><strong className="dash-role-pill">{user.role}</strong></div>
    </div>
  );
}

function StartChecklistCard({ products, onPick }) {
  const [query, setQuery] = useState('');
  const filtered = query.trim()
    ? products.filter((p) => p.canonical_name?.toLowerCase().includes(query.toLowerCase()))
    : products;

  return (
    <div className="dash-card">
      <h2 className="dash-card-title">Start a Compliance Checklist</h2>
      <p className="dash-card-subtitle">Pick a product to see what you need for BIS compliance.</p>
      <input
        type="text"
        className="auth-input"
        placeholder="Search products…"
        value={query}
        onChange={(e) => setQuery(e.target.value)}
      />
      <div className="dash-product-pick-list">
        {filtered.slice(0, 8).map((p) => (
          <button key={p.product_id} type="button" className="dash-product-pick-btn" onClick={() => onPick(p.product_id)}>
            {p.canonical_name}
          </button>
        ))}
        {filtered.length === 0 && <p className="dash-empty-hint">No matching products.</p>}
      </div>
    </div>
  );
}

function SavedChecklistsCard({ savedChecklists, isLoading, onOpen }) {
  return (
    <div className="dash-card">
      <h2 className="dash-card-title">My Checklists</h2>
      {isLoading && <p>Loading…</p>}
      {!isLoading && savedChecklists.length === 0 && (
        <p className="dash-empty-hint">You haven't started a checklist yet.</p>
      )}
      <ul className="dash-saved-list">
        {savedChecklists.map((c) => (
          <li key={c.product_id}>
            <button type="button" className="dash-saved-link" onClick={() => onOpen(c.product_id)}>
              {c.product_id}
            </button>
            <span className="dash-saved-meta">{(c.completed_step_ids || []).length} steps checked</span>
          </li>
        ))}
      </ul>
    </div>
  );
}

function HallmarkingStub() {
  return (
    <div className="dash-card dash-card-stub">
      <h2 className="dash-card-title">Hallmarking Guidance</h2>
      <p className="dash-empty-hint">
        Coming soon - hallmarking checklists need jeweller/hallmarking data we haven't added to the
        knowledge base yet.
      </p>
    </div>
  );
}

function RecentChatsStub() {
  return (
    <div className="dash-card dash-card-stub">
      <h2 className="dash-card-title">Recent Chats</h2>
      <p className="dash-empty-hint">Your conversations will show up here.</p>
    </div>
  );
}

function AdminQuickLink({ onGoToAdmin }) {
  return (
    <div className="dash-card">
      <h2 className="dash-card-title">Admin</h2>
      <button type="button" className="auth-submit-btn" onClick={onGoToAdmin}>Open Admin Dashboard</button>
    </div>
  );
}

function SubscriptionCard({ products, token }) {
  const [subscriptions, setSubscriptions] = useState([]);
  const [selectedProductId, setSelectedProductId] = useState('');
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);

  const load = useCallback(async () => {
    setIsLoading(true);
    try {
      const res = await fetch(`${API_BASE_URL}/subscriptions`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      setSubscriptions(res.ok ? await res.json() : []);
    } catch {
      setSubscriptions([]);
    } finally {
      setIsLoading(false);
    }
  }, [token]);

  useEffect(() => { load(); }, [load]);

  async function handleSubscribe() {
    if (!selectedProductId) return;
    setError(null);
    try {
      const checklistRes = await fetch(`${API_BASE_URL}/catalog/checklist/${selectedProductId}`);
      const checklistData = checklistRes.ok ? await checklistRes.json() : { standards: [] };
      const standardIds = (checklistData.standards || []).map((s) => s.standard_id).filter(Boolean);

      const res = await fetch(`${API_BASE_URL}/subscriptions`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
        body: JSON.stringify({ product_id: selectedProductId, standard_ids: standardIds }),
      });
      if (!res.ok) throw new Error('Could not subscribe.');
      setSelectedProductId('');
      load();
    } catch (err) {
      setError(err.message);
    }
  }

  async function handleUnsubscribe(productId) {
    await fetch(`${API_BASE_URL}/subscriptions/${productId}`, {
      method: 'DELETE',
      headers: { Authorization: `Bearer ${token}` },
    });
    load();
  }

  return (
    <div className="dash-card">
      <h2 className="dash-card-title">Standard Update Subscriptions</h2>
      <p className="dash-card-subtitle">
        Subscribe to a product's standards to be notified if they change.
        <br />
        <em>Notification emails are on the roadmap - subscribing saves your preference now.</em>
      </p>

      {error && <div className="auth-error">{error}</div>}

      <div className="dash-subscribe-row">
        <select
          className="auth-input"
          value={selectedProductId}
          onChange={(e) => setSelectedProductId(e.target.value)}
        >
          <option value="">Select a product…</option>
          {products.map((p) => (
            <option key={p.product_id} value={p.product_id}>{p.canonical_name}</option>
          ))}
        </select>
        <button type="button" className="auth-submit-btn" onClick={handleSubscribe} disabled={!selectedProductId}>
          Subscribe
        </button>
      </div>

      {isLoading && <p>Loading…</p>}
      <ul className="dash-saved-list">
        {subscriptions.map((s) => (
          <li key={s.product_id}>
            <span>{s.product_id}</span>
            <button type="button" className="navbar-auth-btn" onClick={() => handleUnsubscribe(s.product_id)}>
              Unsubscribe
            </button>
          </li>
        ))}
      </ul>
    </div>
  );
}

export default function UserDashboard({ onBack, onGoToAdmin, onGoToLogin }) {
  const { user, isAdmin, token } = useAuth();
  const [activeProductId, setActiveProductId] = useState(null);
  const [savedChecklists, setSavedChecklists] = useState([]);
  const [isLoadingSaved, setIsLoadingSaved] = useState(true);
  const products = useProductList();

  const loadSavedChecklists = useCallback(async () => {
    setIsLoadingSaved(true);
    try {
      const res = await fetch(`${API_BASE_URL}/checklist/progress`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      setSavedChecklists(res.ok ? await res.json() : []);
    } catch {
      setSavedChecklists([]);
    } finally {
      setIsLoadingSaved(false);
    }
  }, [token]);

  useEffect(() => { loadSavedChecklists(); }, [loadSavedChecklists]);

  if (activeProductId) {
    return (
      <ProductChecklist
        productId={activeProductId}
        onGoToLogin={onGoToLogin}
        onBack={() => { setActiveProductId(null); loadSavedChecklists(); }}
      />
    );
  }

  return (
    <div className="dash-page">
      <div className="dash-page-header">
        <button type="button" className="auth-back-link" onClick={onBack}>← Back</button>
        <h1 className="auth-title">Dashboard</h1>
      </div>

      <div className="dash-grid">
        <ProfileCard user={user} />
        <StartChecklistCard products={products} onPick={setActiveProductId} />
        <SavedChecklistsCard savedChecklists={savedChecklists} isLoading={isLoadingSaved} onOpen={setActiveProductId} />
        <HallmarkingStub />
        {user.role === 'msme' && <SubscriptionCard products={products} token={token} />}
        <RecentChatsStub />
        {isAdmin && <AdminQuickLink onGoToAdmin={onGoToAdmin} />}
      </div>
    </div>
  );
}
