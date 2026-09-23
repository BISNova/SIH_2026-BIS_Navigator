import { useState, useEffect, useRef, useCallback } from 'react';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api';
const WS_BASE_URL = API_BASE_URL.replace(/^http/, 'ws').replace(/\/api$/, '/api');

const POLL_INTERVAL_MS = 4000;
const RETRY_INTERVAL_MS = 3000;

/**
 * conversationId can be null initially (BookingModal case, where the
 * conversation doesn't exist until the first message is sent) or known
 * up front (LabInbox case, selecting from an existing list).
 *
 * Design: every message is POSTed to Supabase via REST first - that's
 * the only thing that actually counts as "sent." The WebSocket message
 * is just a hint to refetch sooner; if the socket never connects or
 * drops (Render free tier sleeping, for example), polling still
 * delivers messages, just a few seconds slower. Nothing is ever lost
 * either way.
 */
export function useLabChat({ conversationId, token }) {
  const [messages, setMessages] = useState([]);
  const [isConnected, setIsConnected] = useState(false);
  const wsRef = useRef(null);
  const retryQueueRef = useRef([]); // [{ content, conversationId }]
  const retryTimerRef = useRef(null);

  const loadMessages = useCallback(async (convId) => {
    if (!convId) return;
    try {
      const res = await fetch(`${API_BASE_URL}/lab-chat/conversations/${convId}/messages`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (res.ok) {
        setMessages(await res.json());
      }
    } catch {
      // Polling will just try again next interval - no need to surface
      // a transient fetch failure as an error to the user.
    }
  }, [token]);

  // Polling - always runs, regardless of WebSocket state. The safety
  // net, not the fallback-only path.
  useEffect(() => {
    if (!conversationId) return;
    loadMessages(conversationId);
    const interval = setInterval(() => loadMessages(conversationId), POLL_INTERVAL_MS);
    return () => clearInterval(interval);
  }, [conversationId, loadMessages]);

  // WebSocket - connects once per token, independent of which
  // conversation is currently open, since a lab user needs to hear
  // about new messages across ALL their conversations, not just the
  // one currently selected.
  useEffect(() => {
    if (!token) return;

    const ws = new WebSocket(`${WS_BASE_URL}/lab-chat/ws?token=${encodeURIComponent(token)}`);
    wsRef.current = ws;

    ws.onopen = () => setIsConnected(true);
    ws.onclose = () => setIsConnected(false);
    ws.onerror = () => setIsConnected(false);

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        if (data.type === 'new_message' && data.conversation_id === conversationId) {
          loadMessages(conversationId);
        }
      } catch {
        // Ignore malformed push payloads - polling will catch up regardless.
      }
    };

    return () => ws.close();
  }, [token, conversationId, loadMessages]);

  // Retry queue - anything that failed to send gets retried on a timer
  // until it succeeds. Covers a brief network hiccup, not a long
  // offline period (see the scoped-down decision on this feature).
  const flushRetryQueue = useCallback(async () => {
    if (retryQueueRef.current.length === 0) return;
    const [next, ...rest] = retryQueueRef.current;
    try {
      const res = await fetch(`${API_BASE_URL}/lab-chat/conversations/${next.conversationId}/messages`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
        body: JSON.stringify({ content: next.content }),
      });
      if (res.ok) {
        retryQueueRef.current = rest;
        loadMessages(next.conversationId);
      }
      // If it failed, leave it at the front of the queue and try again
      // next tick - don't drop it.
    } catch {
      // Same - stays queued, network is likely still down.
    }
  }, [token, loadMessages]);

  useEffect(() => {
    retryTimerRef.current = setInterval(flushRetryQueue, RETRY_INTERVAL_MS);
    return () => clearInterval(retryTimerRef.current);
  }, [flushRetryQueue]);

  const startConversation = useCallback(async (labUserId) => {
    const res = await fetch(`${API_BASE_URL}/lab-chat/conversations`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
      body: JSON.stringify({ lab_user_id: labUserId }),
    });
    if (!res.ok) throw new Error('Could not start a conversation with this lab.');
    const data = await res.json();
    return data.conversation_id;
  }, [token]);

  const sendMessage = useCallback(async (content, convId) => {
    const targetId = convId || conversationId;
    if (!targetId) return;

    try {
      const res = await fetch(`${API_BASE_URL}/lab-chat/conversations/${targetId}/messages`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
        body: JSON.stringify({ content }),
      });
      if (!res.ok) throw new Error('send failed');
      loadMessages(targetId);
    } catch {
      // Queue it - flushRetryQueue will keep trying every few seconds.
      retryQueueRef.current = [...retryQueueRef.current, { content, conversationId: targetId }];
    }
  }, [conversationId, token, loadMessages]);

  return { messages, isConnected, sendMessage, startConversation, refetch: () => loadMessages(conversationId) };
}
