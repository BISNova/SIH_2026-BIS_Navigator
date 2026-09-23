const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL ||
  'http://localhost:8000/api';


export class BISNovaAPIError extends Error {
  constructor(message, status = null) {
    super(message);
    this.name = 'BISNovaAPIError';
    this.status = status;
  }
}


async function handleResponse(response) {
  if (response.status === 401) {
    throw new BISNovaAPIError(
      'Your session has expired. Please log in again.',
      401
    );
  }

  if (!response.ok) {
    let detail = '';

    try {
      const data = await response.json();

      if (typeof data?.detail === 'string') {
        detail = data.detail;
      }
    } catch {
      // Ignore JSON parsing errors.
    }

    throw new BISNovaAPIError(
      detail ||
        `BISNova server returned an error (${response.status}).`,
      response.status
    );
  }

  // DELETE endpoints may return 204 No Content.
  if (response.status === 204) {
    return null;
  }

  return response.json();
}


function authHeaders(token) {
  return token
    ? {
        Authorization: `Bearer ${token}`,
      }
    : {};
}


/**
 * Send a chat message.
 *
 * JWT is required by the protected /api/chat endpoint.
 */
export async function sendChatMessage(
  query,
  sessionId = null,
  token = null
) {
  let response;

  try {
    response = await fetch(
      `${API_BASE_URL}/chat`,
      {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...authHeaders(token),
        },
        body: JSON.stringify({
          query,
          session_id: sessionId,
        }),
      }
    );
  } catch {
    throw new BISNovaAPIError(
      'Could not reach the BISNova server. Please check your connection and try again.'
    );
  }

  return handleResponse(response);
}


/**
 * Save feedback.
 */
export async function sendFeedback(
  query,
  answer,
  rating,
  sessionId = null,
  comment = null
) {
  let response;

  try {
    response = await fetch(
      `${API_BASE_URL}/feedback`,
      {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          query,
          answer,
          rating,
          session_id: sessionId,
          comment,
        }),
      }
    );
  } catch {
    throw new BISNovaAPIError(
      'Could not reach the BISNova server. Please check your connection and try again.'
    );
  }

  return handleResponse(response);
}


/**
 * Fetch one conversation's saved history.
 *
 * The backend identifies the user from the JWT.
 * The frontend never sends user_id.
 */
export async function fetchChatHistory(
  sessionId,
  token
) {
  if (!sessionId) {
    return [];
  }

  let response;

  try {
    response = await fetch(
      `${API_BASE_URL}/chat/history/${sessionId}`,
      {
        method: 'GET',
        headers: {
          ...authHeaders(token),
        },
      }
    );
  } catch {
    throw new BISNovaAPIError(
      'Could not reach the BISNova server. Please check your connection and try again.'
    );
  }

  return handleResponse(response);
}


/**
 * Fetch all chat sessions belonging to the logged-in user.
 *
 * The backend identifies the user from the JWT.
 * The frontend never sends user_id.
 */
export async function fetchChatSessions(token) {
  let response;

  try {
    response = await fetch(
      `${API_BASE_URL}/chat/sessions`,
      {
        method: 'GET',
        headers: {
          ...authHeaders(token),
        },
      }
    );
  } catch {
    throw new BISNovaAPIError(
      'Could not reach the BISNova server. Please check your connection and try again.'
    );
  }

  return handleResponse(response);
}


/**
 * Delete all messages belonging to one chat session.
 *
 * The backend identifies the user from the JWT.
 * The frontend never sends user_id.
 */
export async function deleteChatHistory(
  sessionId,
  token
) {
  if (!sessionId) {
    return;
  }

  let response;

  try {
    response = await fetch(
      `${API_BASE_URL}/chat/history/${sessionId}`,
      {
        method: 'DELETE',
        headers: {
          ...authHeaders(token),
        },
      }
    );
  } catch {
    throw new BISNovaAPIError(
      'Could not reach the BISNova server. Please check your connection and try again.'
    );
  }

  return handleResponse(response);
}


/**
 * Fetch catalog standards.
 */
export async function fetchCatalogStandards() {
  let response;

  try {
    response = await fetch(
      `${API_BASE_URL}/catalog/standards`
    );
  } catch {
    throw new BISNovaAPIError(
      'Could not reach the BISNova server. Please check your connection and try again.'
    );
  }

  return handleResponse(response);
}


/**
 * Fetch catalog laboratories.
 */
export async function fetchCatalogLabs() {
  let response;

  try {
    response = await fetch(
      `${API_BASE_URL}/catalog/labs`
    );
  } catch {
    throw new BISNovaAPIError(
      'Could not reach the BISNova server. Please check your connection and try again.'
    );
  }

  return handleResponse(response);
}


/**
 * Fetch BIS hallmarking centres.
 *
 * Hallmarking centres are fetched separately from laboratories
 * because the backend exposes them through a dedicated catalog
 * endpoint.
 */
export async function fetchHallmarkingCentres() {
  let response;

  try {
    response = await fetch(
      `${API_BASE_URL}/catalog/hallmarking-centres`
    );
  } catch {
    throw new BISNovaAPIError(
      'Could not reach the BISNova server. Please check your connection and try again.'
    );
  }

  return handleResponse(response);
}

/**
 * Save a newly-registered lab's contact number + hours. Public - the
 * lab can't log in yet while pending, so this is called right after
 * registration using the id the register response returns.
 */
export async function submitLabProfile({ userId, contactNumber, openingTime, closingTime }) {
  let response;

  try {
    response = await fetch(
      `${API_BASE_URL}/labs/profile`,
      {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          user_id: userId,
          contact_number: contactNumber,
          opening_time: openingTime,
          closing_time: closingTime,
        }),
      }
    );
  } catch {
    throw new BISNovaAPIError(
      'Could not reach the BISNova server. Please check your connection and try again.'
    );
  }

  return handleResponse(response);
}


/**
 * Fetch approved platform-registered labs (brand-new labs, not the
 * original scraped BIS catalog) to merge into the Testing & Labs page.
 */
export async function fetchPlatformLabs() {
  let response;

  try {
    response = await fetch(
      `${API_BASE_URL}/labs/platform-registered`
    );
  } catch {
    throw new BISNovaAPIError(
      'Could not reach the BISNova server. Please check your connection and try again.'
    );
  }

  return handleResponse(response);
}
