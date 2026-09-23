import React, { useState, useEffect, useCallback } from 'react';
import { useAuth } from '../AuthContext';
import { useLabChat } from '../useLabChat';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api';

export default function LabInbox({ onBack }) {
  const { user, token } = useAuth();
  const [conversations, setConversations] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [activeConversationId, setActiveConversationId] = useState(null);

  const loadConversations = useCallback(async () => {
    setIsLoading(true);
    try {
      const res = await fetch(`${API_BASE_URL}/lab-chat/conversations`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      setConversations(res.ok ? await res.json() : []);
    } catch {
      setConversations([]);
    } finally {
      setIsLoading(false);
    }
  }, [token]);

  useEffect(() => { loadConversations(); }, [loadConversations]);

  const chat = useLabChat({ conversationId: activeConversationId, token });

  const activeConversation = conversations.find((c) => c.conversation_id === activeConversationId);

  if (!user || user.role !== 'lab') {
    return (
      <div className="auth-page">
        <div className="auth-card">
          <h1 className="auth-title">Access Denied</h1>
          <p className="auth-subtitle">This page is only for lab accounts.</p>
          <button type="button" className="auth-submit-btn" onClick={onBack}>Back to app</button>
        </div>
      </div>
    );
  }

  return (
    <div className="lab-inbox-page">
      <div className="lab-inbox-sidebar">
        <div className="lab-inbox-sidebar-header">
          <button type="button" className="auth-back-link" onClick={onBack}>← Back</button>
          <h2>Messages</h2>
        </div>

        {isLoading && <p className="dash-empty-hint">Loading…</p>}
        {!isLoading && conversations.length === 0 && (
          <p className="dash-empty-hint">No conversations yet.</p>
        )}

        <div className="lab-inbox-conversation-list">
          {conversations.map((c) => (
            <button
              key={c.conversation_id}
              type="button"
              className={`lab-inbox-conversation-item${activeConversationId === c.conversation_id ? ' active' : ''}`}
              onClick={() => setActiveConversationId(c.conversation_id)}
            >
              <span className="lab-inbox-avatar">{c.other_party_name?.[0]?.toUpperCase() || '?'}</span>
              <span className="lab-inbox-name">{c.other_party_name}</span>
            </button>
          ))}
        </div>
      </div>

      <div className="lab-inbox-thread">
        {!activeConversationId && (
          <div className="lab-inbox-empty-state">Select a conversation to view messages.</div>
        )}

        {activeConversationId && (
          <>
            <div className="lab-inbox-thread-header">
              <strong>{activeConversation?.other_party_name}</strong>
              <span className={`lab-inbox-status-dot${chat.isConnected ? ' online' : ''}`} title={chat.isConnected ? 'Live' : 'Reconnecting…'} />
            </div>

            <div className="lab-inbox-thread-messages">
              {chat.messages.map((m) => (
                <div
                  key={m.id}
                  className={`mini-chat-bubble ${m.sender_user_id === user.id ? 'mine' : 'theirs'}`}
                >
                  {m.content}
                </div>
              ))}
            </div>

            <LabInboxComposer onSend={(text) => chat.sendMessage(text, activeConversationId)} />
          </>
        )}
      </div>
    </div>
  );
}

function LabInboxComposer({ onSend }) {
  const [text, setText] = useState('');

  function handleSubmit(e) {
    e.preventDefault();
    if (!text.trim()) return;
    onSend(text.trim());
    setText('');
  }

  return (
    <form className="lab-inbox-composer" onSubmit={handleSubmit}>
      <input
        type="text"
        className="auth-input"
        placeholder="Type a message…"
        value={text}
        onChange={(e) => setText(e.target.value)}
      />
      <button type="submit" className="auth-submit-btn" disabled={!text.trim()}>Send</button>
    </form>
  );
}
