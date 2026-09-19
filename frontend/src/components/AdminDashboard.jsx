import React, { useState, useEffect, useCallback } from 'react';
import { useAuth } from '../AuthContext';

// NOTE: the exact shape of a "staged change" object wasn't specified by
// the backend - this renders defensively (falls back to raw JSON for
// anything it doesn't recognize) so it won't break once you confirm the
// real fields. Update the card below once you know them for real.
function StagedChangeCard({ change, onReview, isSubmitting }) {
  const [note, setNote] = useState('');
  const documentId = change.document_id || change.id;

  return (
    <div className="admin-card">
      <div className="admin-card-header">
        <span className="admin-card-id">{documentId}</span>
        {change.status && <span className="admin-card-status">{change.status}</span>}
      </div>

      {change.title && <h3 className="admin-card-title">{change.title}</h3>}
      {change.summary && <p className="admin-card-summary">{change.summary}</p>}

      {!change.title && !change.summary && (
        <pre className="admin-card-raw">{JSON.stringify(change, null, 2)}</pre>
      )}

      <textarea
        className="admin-note-input"
        placeholder="Optional note/comment..."
        value={note}
        onChange={(e) => setNote(e.target.value)}
      />

      <div className="admin-card-actions">
        <button
          type="button"
          className="admin-approve-btn"
          disabled={isSubmitting}
          onClick={() => onReview(documentId, true, note)}
        >
          Approve
        </button>
        <button
          type="button"
          className="admin-reject-btn"
          disabled={isSubmitting}
          onClick={() => onReview(documentId, false, note)}
        >
          Reject
        </button>
      </div>
    </div>
  );
}

export default function AdminDashboard({ onBack }) {
  const { isAdmin, getStagedChanges, submitReview } = useAuth();
  const [changes, setChanges] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);
  const [reviewingId, setReviewingId] = useState(null);

  const loadChanges = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const result = await getStagedChanges();
      // Defensive: accept either a bare array or { items: [...] } / { changes: [...] }
      const list = Array.isArray(result)
        ? result
        : result?.items || result?.changes || [];
      setChanges(list);
    } catch (err) {
      setError(err.message || 'Could not load staged changes.');
    } finally {
      setIsLoading(false);
    }
  }, [getStagedChanges]);

  useEffect(() => {
    if (isAdmin) {
      loadChanges();
    }
  }, [isAdmin, loadChanges]);

  async function handleReview(documentId, approve, note) {
    setReviewingId(documentId);
    try {
      await submitReview({ document_id: documentId, approve, note });
      // Remove it from the list optimistically rather than a full
      // reload - keeps the dashboard responsive.
      setChanges((prev) =>
        prev.filter((c) => (c.document_id || c.id) !== documentId)
      );
    } catch (err) {
      setError(err.message || 'Could not submit review.');
    } finally {
      setReviewingId(null);
    }
  }

  // Defense in depth - App.jsx should already prevent a non-admin from
  // reaching this view, but this guarantees it regardless of how it's
  // reached.
  if (!isAdmin) {
    return (
      <div className="auth-page">
        <div className="auth-card">
          <h1 className="auth-title">Access Denied</h1>
          <p className="auth-subtitle">You don't have permission to view this page.</p>
          <button type="button" className="auth-submit-btn" onClick={onBack}>
            Back to app
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="admin-page">
      <div className="admin-page-header">
        <button type="button" className="auth-back-link" onClick={onBack}>
          ← Back
        </button>
        <h1 className="auth-title">Admin Dashboard</h1>
        <button type="button" className="admin-refresh-btn" onClick={loadChanges}>
          Refresh
        </button>
      </div>

      {error && <div className="auth-error">{error}</div>}

      {isLoading && <p>Loading staged changes…</p>}

      {!isLoading && changes.length === 0 && !error && (
        <p className="admin-empty-state">No staged changes waiting for review.</p>
      )}

      <div className="admin-card-list">
        {changes.map((change) => (
          <StagedChangeCard
            key={change.document_id || change.id}
            change={change}
            onReview={handleReview}
            isSubmitting={reviewingId === (change.document_id || change.id)}
          />
        ))}
      </div>
    </div>
  );
}