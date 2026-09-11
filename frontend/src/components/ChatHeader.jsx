import React from 'react';

export default function ChatHeader({
  onToggleSidebar,
  onGoHome,
  onClearChat,
  onGlobalSearch
}) {
  return (
    <header className="chat-top-navbar">

      {/* Main Chat Sub-Header */}
      <div className="chat-sub-header">
        <div className="chat-agent-info">
          <img src="/assets/logo.png" alt="BISNova" className="agent-avatar-img" />
          <div className="agent-text-col">
            <div className="agent-name-row">
              <h1 className="agent-name">BISNova</h1>
              <span className="agent-status-dot" title="Online"></span>
            </div>
            <span className="agent-status-text">Always here to help</span>
          </div>
        </div>

        <div className="chat-header-actions">
          {/* Clear Chat Button matching reference */}
          <button
            type="button"
            className="clear-chat-pill-btn"
            onClick={onClearChat}
            title="Clear active conversation"
          >
            <span className="trash-icon">🗑️</span>
            <span>Clear Chat</span>
          </button>

          {/* Home Icon Button - returns to Landing page */}
          <button
            type="button"
            className="home-nav-pill-btn"
            onClick={onGoHome}
            title="Back to Landing Page"
          >
            <span>Home ⌂</span>
          </button>
        </div>
      </div>
    </header>
  );
}
