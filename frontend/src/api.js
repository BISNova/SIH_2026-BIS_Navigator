/**
 * BISNova backend API client.
 *
 * Base URL is configurable via VITE_API_BASE_URL (create a .env file
 * with VITE_API_BASE_URL=http://your-backend-host:8000/api for anything
 * other than local development). Defaults to the FastAPI dev server.
 */

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api';

export class BISNovaAPIError extends Error {}

/**
 * Sends a query to the chat endpoint and returns the parsed response.
 * Throws BISNovaAPIError on network failure or non-2xx response, so
 * callers can show a graceful fallback message instead of crashing.
 *
 * sessionId: the current chat's own id, doubling as the backend's
 * conversation-memory key (see backend/session_store.py) - so a
 * follow-up like "what tests are needed" resolves against whatever
 * product was matched earlier in THIS chat, not some other chat.
 */
export async function sendChatMessage(query, sessionId = null) {
  let response;
  try {
    response = await fetch(`${API_BASE_URL}/chat`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ query, session_id: sessionId }),
    });
  } catch (err) {
    throw new BISNovaAPIError('Could not reach the BISNova server. Please check your connection and try again.');
  }

  if (!response.ok) {
    throw new BISNovaAPIError(`BISNova server returned an error (${response.status}).`);
  }

  return response.json();
}

/**
 * Sends a 👍/👎 rating for a given answer.
 */
export async function sendFeedback({ query, answer, rating, sessionId = null, comment = null }) {
  let response;
  try {
    response = await fetch(`${API_BASE_URL}/feedback`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ query, answer, rating, session_id: sessionId, comment }),
    });
  } catch (err) {
    throw new BISNovaAPIError('Could not reach the BISNova server. Please check your connection and try again.');
  }
  if (!response.ok) {
    throw new BISNovaAPIError(`BISNova server returned an error (${response.status}).`);
  }
  return response.json();
}

/**
 * Fetches every standard in the knowledge base, for the Explore
 * Standards page. Grows automatically as the knowledge base grows -
 * no frontend change needed when more standards are added.
 */
export async function fetchCatalogStandards() {
  let response;
  try {
    response = await fetch(`${API_BASE_URL}/catalog/standards`);
  } catch (err) {
    throw new BISNovaAPIError('Could not reach the BISNova server. Please check your connection and try again.');
  }
  if (!response.ok) {
    throw new BISNovaAPIError(`BISNova server returned an error (${response.status}).`);
  }
  return response.json();
}

/**
 * Fetches every active testing lab in the knowledge base, for the
 * "Testing and Labs" section.
 */
export async function fetchCatalogLabs() {
  let response;
  try {
    response = await fetch(`${API_BASE_URL}/catalog/labs`);
  } catch (err) {
    throw new BISNovaAPIError('Could not reach the BISNova server. Please check your connection and try again.');
  }
  if (!response.ok) {
    throw new BISNovaAPIError(`BISNova server returned an error (${response.status}).`);
  }
  return response.json();
}
