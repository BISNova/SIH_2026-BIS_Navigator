/**
 * BISNova auth API client. Mirrors the style of api.js on purpose - same
 * base URL env var, same try/catch-and-wrap-in-a-typed-error shape - so
 * this doesn't feel like a bolted-on second system.
 *
 * Base URL is the SAME backend as chat/catalog (confirmed: auth, admin,
 * chat, catalog, feedback are all on one Render deployment). Uses the
 * same VITE_API_BASE_URL env var as api.js - no new env var needed.
 */

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api';

export class AuthAPIError extends Error {
  constructor(message, status = null, detail = null) {
    super(message);
    this.status = status;   // 401 | 403 | 409 | null (network failure)
    this.detail = detail;   // raw backend "detail" string, if any
  }
}

async function request(path, { method = 'GET', body = null, token = null } = {}) {
  const headers = { 'Content-Type': 'application/json' };
  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }

  let response;
  try {
    response = await fetch(`${API_BASE_URL}${path}`, {
      method,
      headers,
      body: body ? JSON.stringify(body) : undefined,
    });
  } catch (err) {
    throw new AuthAPIError(
      'Could not reach the BISNova server. Please check your connection and try again.'
    );
  }

  let payload = null;
  try {
    payload = await response.json();
  } catch {
    // No JSON body (e.g. a plain 500) - fine, payload stays null.
  }

  if (!response.ok) {
    const detail = payload?.detail || null;
    throw new AuthAPIError(
      detail || `Request failed (${response.status}).`,
      response.status,
      detail
    );
  }

  return payload;
}

// --- Auth ---

export function registerUser({ name, email, password, role }) {
  return request('/auth/register', { method: 'POST', body: { name, email, password, role } });
}

export function loginUser({ email, password }) {
  return request('/auth/login', { method: 'POST', body: { email, password } });
}

export function fetchCurrentUser(token) {
  return request('/auth/me', { token });
}

// --- Admin ---

export function fetchStagedChanges(token) {
  return request('/admin/staged-changes', { token });
}

/**
 * decision: { document_id, approve: boolean, note?: string }
 * Confirmed exact body shape with backend - approve:true = approve,
 * approve:false = reject, note is optional.
 */
export function reviewStagedChange(token, { document_id, approve, note }) {
  return request('/admin/review', {
    method: 'POST',
    token,
    body: { document_id, approve, note: note || undefined },
  });
}