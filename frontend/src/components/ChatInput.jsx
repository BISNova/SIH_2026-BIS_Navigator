import React, { useState, useRef } from 'react';

const PROMPT_SUGGESTIONS = [
  { label: 'What is BIS?', query: 'What is Bureau of Indian Standards (BIS)?' },
  { label: 'Explain ISI mark', query: 'Explain the ISI mark certification scheme' },
  { label: 'How to start a BIS certification?', query: 'How do I start a new BIS certification on Manakonline?' },
  { label: 'Find a lab near me', query: 'Find recognized testing laboratories near me' }
];

export default function ChatInput({ onSendMessage, onTypingChange, onSelectSuggestion }) {
  const [inputText, setInputText] = useState('');
  const [attachedFile, setAttachedFile] = useState(null);
  const fileInputRef = useRef(null);
  const typingTimeoutRef = useRef(null);

  function handleInputChange(e) {
    const val = e.target.value;
    setInputText(val);

    if (val.trim().length > 0) {
      onTypingChange(true);
      if (typingTimeoutRef.current) clearTimeout(typingTimeoutRef.current);
      typingTimeoutRef.current = setTimeout(() => {
        onTypingChange(false);
      }, 1500);
    } else {
      onTypingChange(false);
    }
  }

  function handleFileChange(e) {
    if (e.target.files && e.target.files[0]) {
      setAttachedFile(e.target.files[0]);
    }
  }

  function handleRemoveFile() {
    setAttachedFile(null);
    if (fileInputRef.current) fileInputRef.current.value = '';
  }

  function handleSubmit(e) {
    if (e) e.preventDefault();
    const trimmed = inputText.trim();
    if (!trimmed && !attachedFile) return;

    onSendMessage(trimmed, attachedFile);
    setInputText('');
    setAttachedFile(null);
    if (fileInputRef.current) fileInputRef.current.value = '';
    onTypingChange(false);
  }

  function handleKeyDown(e) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  }

  return (
    <footer className="chat-bottom-dock">
      {/* Attached file badge */}
      {attachedFile && (
        <div className="attached-file-pill">
          <span>📎 {attachedFile.name}</span>
          <button
            type="button"
            className="remove-file-x-btn"
            onClick={handleRemoveFile}
            title="Remove file"
          >
            ✕
          </button>
        </div>
      )}

      {/* Floating Pill Input Bar */}
      <form className="chat-pill-input-box" onSubmit={handleSubmit}>
        <input
          type="file"
          ref={fileInputRef}
          onChange={handleFileChange}
          style={{ display: 'none' }}
          accept=".pdf,.doc,.docx,.png,.jpg,.jpeg"
        />

        <button
          type="button"
          className="chat-clip-btn"
          onClick={() => fileInputRef.current?.click()}
          title="Attach document or product specification"
          aria-label="Attach File"
        >
          <span className="clip-icon">📎</span>
        </button>

        <input
          type="text"
          className="chat-main-text-input"
          value={inputText}
          onChange={handleInputChange}
          onKeyDown={handleKeyDown}
          onFocus={() => {
            if (inputText.trim().length > 0) onTypingChange(true);
          }}
          onBlur={() => onTypingChange(false)}
          placeholder="Ask BISNova anything..."
          autoComplete="off"
          aria-label="Ask BISNova anything"
        />

        <button
          type="submit"
          className="chat-submit-plane-btn"
          title="Send message"
          aria-label="Send message"
          disabled={!inputText.trim() && !attachedFile}
        >
          <svg viewBox="0 0 24 24" fill="currentColor">
            <path d="M2.01 21L23 12 2.01 3 2 10l15 2-15 2z" />
          </svg>
        </button>
      </form>

      {/* Bottom Row: Quick Suggestion Chips + AI Disclaimer */}
      <div className="chat-dock-footer-row">
        <div className="dock-suggestions-list" aria-label="Suggested questions">
          {PROMPT_SUGGESTIONS.map((sug, sIdx) => (
            <button
              key={sIdx}
              type="button"
              className="dock-suggestion-chip"
              onClick={() => onSelectSuggestion(sug.query)}
            >
              {sug.label}
            </button>
          ))}
        </div>

        <div className="ai-disclaimer-note">
          <span>✨ BISNova can make mistakes. Please verify with official sources.</span>
        </div>
      </div>
    </footer>
  );
}
