import React, { useState, useEffect, useCallback } from 'react';
import { useAuth } from '../AuthContext';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api';

function groupTitle(key) {
  return {
    certification_steps: 'Certification Steps',
    tests: 'Required Tests',
    inspection_requirements: 'Inspection Requirements',
  }[key] || key;
}

export default function ProductChecklist({ productId, onBack, onGoToLogin }) {
  const { user, token } = useAuth();
  const isLoggedIn = !!user;

  const [data, setData] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);
  const [checked, setChecked] = useState({});
  const [isSaving, setIsSaving] = useState(false);

  const loadChecklist = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const res = await fetch(`${API_BASE_URL}/catalog/checklist/${productId}`);
      if (!res.ok) throw new Error(`Could not load checklist (${res.status})`);
      setData(await res.json());
    } catch (err) {
      setError(err.message || 'Could not load this checklist.');
    } finally {
      setIsLoading(false);
    }
  }, [productId]);

  const loadSavedProgress = useCallback(async () => {
    if (!isLoggedIn) return;
    try {
      const res = await fetch(`${API_BASE_URL}/checklist/progress?product_id=${productId}`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!res.ok) return;
      const payload = await res.json();
      const ids = payload?.completed_step_ids || [];
      const map = {};
      ids.forEach((id) => { map[id] = true; });
      setChecked(map);
    } catch {
      // Silent - a failed restore shouldn't block viewing the checklist.
    }
  }, [productId, isLoggedIn, token]);

  useEffect(() => {
    loadChecklist();
    loadSavedProgress();
  }, [loadChecklist, loadSavedProgress]);

  async function persistProgress(nextChecked) {
    if (!isLoggedIn) return;
    setIsSaving(true);
    try {
      await fetch(`${API_BASE_URL}/checklist/progress`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
        body: JSON.stringify({
          product_id: productId,
          completed_step_ids: Object.keys(nextChecked).filter((k) => nextChecked[k]),
        }),
      });
    } catch {
      // Best-effort - a failed save shouldn't undo the user's checkbox click.
    } finally {
      setIsSaving(false);
    }
  }

  function toggleItem(itemId) {
    const next = { ...checked, [itemId]: !checked[itemId] };
    setChecked(next);
    persistProgress(next);
  }

  if (isLoading) return <div className="checklist-page"><p>Loading checklist…</p></div>;
  if (error) return <div className="checklist-page"><div className="auth-error">{error}</div></div>;
  if (!data) return null;

  const itemGroups = ['certification_steps', 'tests', 'inspection_requirements'];
  const totalItems = itemGroups.reduce((sum, g) => sum + (data[g]?.length || 0), 0);
  const completedCount = Object.values(checked).filter(Boolean).length;

  return (
    <div className="checklist-page">
      <div className="checklist-header no-print">
        <button type="button" className="auth-back-link" onClick={onBack}>← Back</button>

        {isLoggedIn ? (
          <button type="button" className="checklist-download-btn" onClick={() => window.print()}>
            ⬇ Download PDF
          </button>
        ) : (
          <button type="button" className="checklist-download-btn" onClick={onGoToLogin}>
            Log In to Download & Save
          </button>
        )}
      </div>

      <div className="checklist-print-header">
        <h1 className="checklist-title">{data.product?.canonical_name || 'Compliance Checklist'}</h1>
        {data.standards?.length > 0 && (
          <p className="checklist-subtitle">{data.standards.map((s) => s.is_number).join(', ')}</p>
        )}
        <p className="checklist-progress-line">
          {completedCount} / {totalItems} steps completed
          {!isLoggedIn && ' · log in to save your progress and download'}
          {isSaving && ' · saving…'}
        </p>
      </div>

      {/* 1. Certification Scheme Guidance - explanatory, no checkboxes */}
      {(data.schemes?.length > 0 || data.conformity_routes?.length > 0) && (
        <div className="checklist-group">
          <h2 className="checklist-group-title">Certification Scheme Guidance</h2>
          {data.schemes?.map((scheme, idx) => (
            <div key={idx} className="checklist-scheme-card">
              <div className="checklist-scheme-name">
                {scheme.name || scheme.scheme_name}
                {scheme.standard_mark && <span className="checklist-scheme-mark">{scheme.standard_mark}</span>}
              </div>
              {scheme.description && <p className="checklist-scheme-desc">{scheme.description}</p>}
              {scheme.application_route && (
                <p className="checklist-scheme-route"><strong>How to apply:</strong> {scheme.application_route}</p>
              )}
            </div>
          ))}
          {data.conformity_routes?.map((route, idx) => (
            <p key={idx} className="checklist-mandatory-note">
              {route.mandatory
                ? `Mandatory${route.mandatory_reason ? ` — ${route.mandatory_reason}` : ''}`
                : 'Voluntary certification'}
            </p>
          ))}
        </div>
      )}

      {/* 2. Compliance Checklist Generation - the actionable part */}
      {itemGroups.map((groupKey) => {
        const items = data[groupKey] || [];
        if (items.length === 0) return null;
        return (
          <div key={groupKey} className="checklist-group">
            <h2 className="checklist-group-title">{groupTitle(groupKey)}</h2>
            <ul className="checklist-item-list">
              {items.map((item, idx) => {
                const itemId = item.id || item.test_id || item.step_id || `${groupKey}-${idx}`;
                const label = item.description || item.test_name || item.requirement || item.title || JSON.stringify(item);
                return (
                  <li key={itemId} className="checklist-item">
                    <label className="checklist-item-label">
                      <input
                        type="checkbox"
                        checked={!!checked[itemId]}
                        onChange={() => toggleItem(itemId)}
                        className="no-print"
                      />
                      <span className={checked[itemId] ? 'checklist-item-done' : ''}>{label}</span>
                    </label>
                  </li>
                );
              })}
            </ul>
          </div>
        );
      })}

      {/* 3. Cost Information - hides gracefully if cost_estimates.json isn't wired yet */}
      {data.cost_info?.length > 0 && (
        <div className="checklist-group">
          <h2 className="checklist-group-title">Cost Information</h2>
          <ul className="checklist-item-list">
            {data.cost_info.map((c, idx) => (
              <li key={idx} className="checklist-cost-row">
                <span>{c.label || c.item}</span>
                <strong>{c.amount || c.fee_range}</strong>
              </li>
            ))}
          </ul>
          <p className="checklist-cost-caveat">Indicative only — confirm current fees on Manak Online.</p>
        </div>
      )}

      <p className="checklist-disclaimer no-print">
        Informational guidance only — not a substitute for official BIS certification advice.
      </p>
    </div>
  );
}
