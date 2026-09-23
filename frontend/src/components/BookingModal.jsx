import React, { useState } from 'react';
import { useAuth } from '../AuthContext';
import { useLabChat } from '../useLabChat';

export default function BookingModal({ lab, currentUser, onClose }) {
  const { token } = useAuth();
  const [conversationId, setConversationId] = useState(null);
  const [isStarting, setIsStarting] = useState(false);
  const [startError, setStartError] = useState(null);

  const chat = useLabChat({ conversationId, token });

  async function handleFirstMessage(text) {
    if (!conversationId) {
      setIsStarting(true);
      setStartError(null);
      try {
        const id = await chat.startConversation(lab.lab_user_id);
        setConversationId(id);
        // Send once the conversation exists - queued if this fails,
        // per the retry-queue behavior in useLabChat.
        chat.sendMessage(text, id);
      } catch (err) {
        setStartError(err.message || 'Could not start the conversation.');
      } finally {
        setIsStarting(false);
      }
    } else {
      chat.sendMessage(text, conversationId);
    }
  }

  if (!currentUser) {
    return (
      <div className="booking-modal-overlay" onClick={onClose}>
        <div className="booking-modal" onClick={(e) => e.stopPropagation()}>
          <button type="button" className="booking-modal-close" onClick={onClose}>✕</button>
          <p>Please log in to message this lab.</p>
        </div>
      </div>
    );
  }

  return (
    <div className="booking-modal-overlay" onClick={onClose}>
      <div className="booking-modal" onClick={(e) => e.stopPropagation()}>
        <div className="booking-modal-header">
          <h3>{lab.lab_name}</h3>
          {lab.contact && (
            <a href={`tel:${lab.contact}`} className="booking-call-btn" title="Call this lab">
              📞 Call
            </a>
          )}
          <button type="button" className="booking-modal-close" onClick={onClose}>✕</button>
        </div>

        {(lab.opening_time || lab.closing_time) && (
          <p className="booking-modal-hours">
            Hours: {lab.opening_time || '?'} – {lab.closing_time || '?'}
          </p>
        )}

        <p className="booking-modal-disclaimer">
          Calls are between you and the lab directly - please keep it professional.
        </p>

        {startError && <div className="auth-error">{startError}</div>}

        <MiniChatBox
          messages={chat.messages}
          onSend={handleFirstMessage}
          disabled={isStarting}
          currentUserId={currentUser.id}
        />
      </div>
    </div>
  );
}

function MiniChatBox({ messages, onSend, disabled, currentUserId }) {
  const [text, setText] = useState('');

  function handleSubmit(e) {
    e.preventDefault();
    if (!text.trim()) return;
    onSend(text.trim());
    setText('');
  }

  return (
    <div className="mini-chat-box">
      <div className="mini-chat-messages">
        {messages.length === 0 && (
          <p className="dash-empty-hint">Send a message to start the conversation.</p>
        )}
        {messages.map((m) => (
          <div
            key={m.id}
            className={`mini-chat-bubble ${m.sender_user_id === currentUserId ? 'mine' : 'theirs'}`}
          >
            {m.content}
          </div>
        ))}
      </div>
      <form className="mini-chat-input-row" onSubmit={handleSubmit}>
        <input
          type="text"
          className="auth-input"
          placeholder="Type a message…"
          value={text}
          onChange={(e) => setText(e.target.value)}
          disabled={disabled}
        />
        <button type="submit" className="auth-submit-btn" disabled={disabled || !text.trim()}>
          Send
        </button>
      </form>
    </div>
  );
}
