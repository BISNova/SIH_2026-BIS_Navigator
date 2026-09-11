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
 */
export async function sendChatMessage(query) {
  let response;
  try {
    response = await fetch(`${API_BASE_URL}/chat`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ query }),
    });
  } catch (err) {
    throw new BISNovaAPIError('Could not reach the BISNova server. Please check your connection and try again.');
  }

  if (!response.ok) {
    throw new BISNovaAPIError(`BISNova server returned an error (${response.status}).`);
  }

  return response.json();
}
