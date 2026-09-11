import React, { useState, useEffect, useRef } from 'react';
import Mascot from './Mascot';

export default function Sidebar({
  isOpen,
  onToggle,
  onCloseMobile,
  chats,
  activeChatId,
  onSelectChat,
  onNewChat,
  onPinChat,
  onRenameChat,
  onDeleteChat,
  onNavClick,
  activeNav,
  mascotState,
  onMascotClick
}) {
  const [isRecentDropdownOpen, setIsRecentDropdownOpen] = useState(true);
  const [activeMenuChatId, setActiveMenuChatId] = useState(null);
  const [editingChatId, setEditingChatId] = useState(null);
  const [editTitle, setEditTitle] = useState('');

  const menuRef = useRef(null);
  const renameInputRef = useRef(null);

  useEffect(() => {
    function handleClickOutside(event) {
      if (menuRef.current && !menuRef.current.contains(event.target)) {
        setActiveMenuChatId(null);
      }
    }
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  useEffect(() => {
    if (editingChatId && renameInputRef.current) {
      renameInputRef.current.focus();
      renameInputRef.current.select();
    }
  }, [editingChatId]);

  function handleStartRename(chat, e) {
    e.stopPropagation();
    setEditingChatId(chat.id);
    setEditTitle(chat.title);
    setActiveMenuChatId(null);
  }

  function handleSaveRename(chatId) {
    if (editTitle.trim()) {
      onRenameChat(chatId, editTitle.trim());
    }
    setEditingChatId(null);
  }

  function handleRenameKeyDown(e, chatId) {
    if (e.key === 'Enter') {
      e.preventDefault();
      handleSaveRename(chatId);
    } else if (e.key === 'Escape') {
      setEditingChatId(null);
    }
  }

  const sortedChats = [...chats].sort((a, b) => {
    if (a.pinned && !b.pinned) return -1;
    if (!a.pinned && b.pinned) return 1;
    return 0;
  });

  return (
    <aside className={`sidebar ${isOpen ? 'expanded' : 'collapsed'}`}>
      {/* Sidebar Header with new BISNova logo */}
      <div className="sidebar-header">
        {isOpen && (
          <a href="#" className="sidebar-logo-wrap" title="BISNova Home">
            <img src="/assets/bisnova_logo.png" alt="BISNova Logo" className="sidebar-logo-bisnova" />
          </a>
        )}
        <button
          type="button"
          className="sidebar-toggle-btn"
          onClick={onToggle}
          title={isOpen ? 'Collapse Sidebar' : 'Expand Sidebar'}
          aria-label={isOpen ? 'Collapse Sidebar' : 'Expand Sidebar'}
        >
          <div className="toggle-icon-rect"></div>
        </button>
      </div>

      {/* Main Navigation */}
      <nav className="sidebar-nav" aria-label="Main Navigation">
        {/* + New Chat with coral pill highlight */}
        <button
          className={`nav-item new-chat-pill ${activeNav === 'new-chat' ? 'active' : ''}`}
          onClick={onNewChat}
          title="Start a New Chat"
        >
          <div className="nav-icon-wrap red-icon">
            <svg viewBox="0 0 24 24">
              <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm5 11h-4v4h-2v-4H7v-2h4V7h2v4h4v2z" />
            </svg>
          </div>
          {isOpen && <span className="new-chat-label">+ New Chat</span>}
        </button>

        <button
          className={`nav-item ${activeNav === 'Dashboard' ? 'active' : ''}`}
          onClick={() => onNavClick('Dashboard')}
          title="Dashboard"
        >
          <div className="nav-icon-wrap">
            <svg viewBox="0 0 24 24">
              <rect x="3" y="3" width="7.5" height="7.5" rx="2.5" />
              <rect x="13.5" y="3" width="7.5" height="7.5" rx="2.5" />
              <rect x="3" y="13.5" width="7.5" height="7.5" rx="2.5" />
              <rect x="13.5" y="13.5" width="7.5" height="7.5" rx="2.5" />
            </svg>
          </div>
          {isOpen && <span>Dashboard</span>}
        </button>

        <button
          className={`nav-item ${activeNav === 'Explore Standards' ? 'active' : ''}`}
          onClick={() => onNavClick('Explore Standards')}
          title="Explore Standards"
        >
          <div className="nav-icon-wrap">
            <svg viewBox="0 0 24 24">
              <path d="M18 2H6c-1.1 0-2 .9-2 2v16c0 1.1.9 2 2 2h12c1.1 0 2-.9 2-2V4c0-1.1-.9-2-2-2zM6 4h5v8l-2.5-1.5L6 12V4z" />
            </svg>
          </div>
          {isOpen && <span>Explore Standards</span>}
        </button>

        <button
          className={`nav-item ${activeNav === 'Testing and Labs' ? 'active' : ''}`}
          onClick={() => onNavClick('Testing and Labs')}
          title="Testing and Labs"
        >
          <div className="nav-icon-wrap">
            <svg viewBox="0 0 24 24">
              <path d="M19 19L14.5 12V6h1V4H8.5v2h1v6L5 19a2 2 0 0 0 1.7 3h10.6a2 2 0 0 0 1.7-3zM8.8 17l2.2-3.5h2l2.2 3.5H8.8z" />
            </svg>
          </div>
          {isOpen && <span>Testing and Labs</span>}
        </button>

        <button
          className={`nav-item ${activeNav === 'Other Queries / FAQs' ? 'active' : ''}`}
          onClick={() => onNavClick('Other Queries / FAQs')}
          title="Other Queries / FAQs"
        >
          <div className="nav-icon-wrap">
            <svg viewBox="0 0 24 24">
              <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm1 16h-2v-2h2v2zm1.07-7.75l-.9.92C12.45 11.9 12 12.5 12 14h-2v-.5c0-1.1.45-2.1 1.17-2.83l1.24-1.26c.37-.36.59-.86.59-1.41 0-1.1-.9-2-2-2s-2 .9-2 2H7c0-2.76 2.24-5 5-5s5 2.24 5 5c0 1.04-.42 1.99-1.07 2.75z" />
            </svg>
          </div>
          {isOpen && <span>Other Queries / FAQs</span>}
        </button>
      </nav>

      {/* Divider */}
      {isOpen && <hr className="sidebar-divider" />}

      {/* Recent Chats */}
      {isOpen && (
        <div className="recent-chats-section">
          <div className="recent-chats-header">
            <div className="recent-header-left">
              <div className="recent-icon-wrap">
                <svg viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2.3" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
              </div>
              <span>Recent Chats</span>
            </div>

            <button
              className={`recent-dropdown-btn ${!isRecentDropdownOpen ? 'collapsed' : ''}`}
              onClick={() => setIsRecentDropdownOpen(!isRecentDropdownOpen)}
              title={isRecentDropdownOpen ? 'Collapse Recent Chats' : 'Expand Recent Chats'}
              aria-label="Toggle Recent Chats Dropdown"
            >
              <svg width="18" height="18" viewBox="0 0 24 24" fill="currentColor">
                <path d="M7.41 8.59L12 13.17l4.59-4.58L18 10l-6 6-6-6 1.41-1.41z" />
              </svg>
            </button>
          </div>

          {isRecentDropdownOpen && (
            <div className="recent-chats-list">
              {sortedChats.map(chat => (
                <div
                  key={chat.id}
                  className={`recent-chat-item ${activeChatId === chat.id ? 'active' : ''}`}
                  onClick={() => onSelectChat(chat.id)}
                >
                  <div className="recent-chat-left">
                    <div className="recent-chat-icon">
                      <svg viewBox="0 0 24 24">
                        <path d="M20 2H4c-1.1 0-2 .9-2 2v18l4-4h14c1.1 0 2-.9 2-2V4c0-1.1-.9-2-2-2z" />
                      </svg>
                    </div>

                    {editingChatId === chat.id ? (
                      <input
                        ref={renameInputRef}
                        type="text"
                        className="chat-rename-input"
                        value={editTitle}
                        onChange={(e) => setEditTitle(e.target.value)}
                        onBlur={() => handleSaveRename(chat.id)}
                        onKeyDown={(e) => handleRenameKeyDown(e, chat.id)}
                        onClick={(e) => e.stopPropagation()}
                      />
                    ) : (
                      <span className="recent-chat-title">
                        {chat.title}
                        {chat.pinned && <span className="pin-badge" title="Pinned">📌</span>}
                      </span>
                    )}
                  </div>

                  <button
                    className={`chat-menu-trigger-btn ${activeMenuChatId === chat.id ? 'active' : ''}`}
                    onClick={(e) => {
                      e.stopPropagation();
                      setActiveMenuChatId(activeMenuChatId === chat.id ? null : chat.id);
                    }}
                    title="Chat options"
                    aria-label="Chat options"
                  >
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor">
                      <circle cx="12" cy="5" r="2" />
                      <circle cx="12" cy="12" r="2" />
                      <circle cx="12" cy="19" r="2" />
                    </svg>
                  </button>

                  {activeMenuChatId === chat.id && (
                    <div className="chat-action-menu" ref={menuRef} onClick={(e) => e.stopPropagation()}>
                      <button
                        className="menu-action-item"
                        onClick={() => {
                          onPinChat(chat.id);
                          setActiveMenuChatId(null);
                        }}
                      >
                        <span>{chat.pinned ? '📍 Unpin' : '📌 Pin to top'}</span>
                      </button>

                      <button
                        className="menu-action-item"
                        onClick={(e) => handleStartRename(chat, e)}
                      >
                        <span>✏️ Rename</span>
                      </button>

                      <button
                        className="menu-action-item delete-action"
                        onClick={() => {
                          onDeleteChat(chat.id);
                          setActiveMenuChatId(null);
                        }}
                      >
                        <span>🗑️ Delete</span>
                      </button>
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Mascot at Bottom with Quote Slogan (matching Image 1) */}
      <div className="sidebar-mascot-footer-wrap">
        {/* {isOpen && (
          <div className="sidebar-mascot-quote-note">
            <span>Curiosity today.<br /><em>A safer tomorrow.</em></span>
          </div>
        )} */}
        <Mascot mascotState={mascotState} onMascotClick={onMascotClick} isCollapsed={!isOpen} />
      </div>
    </aside>
  );
}
