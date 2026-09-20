import React from 'react';

export default function Navbar({
  onOpenChatbot,
  onNavigateSection,
  viewMode,
  user,
  isAdmin,
  onLogout,
  onGoToLogin,
  onGoToRegister,
  onGoToAdmin,
}) {
  const navClass = (section) => `nav-link${viewMode === section ? ' active' : ''}`;

  return (
    <header className="landing-navbar">
      <div className="navbar-container">
        {/* Logo */}
        <a
          href="#"
          className="navbar-logo-wrap"
          onClick={(e) => { e.preventDefault(); onNavigateSection('hero'); }}
        >
          <img
            src="/assets/bisnova_logo.png"
            alt="BISNova Logo"
            className="navbar-logo"
          />
        </a>

        {/* Center Nav Links */}
        <nav className="navbar-links" aria-label="Main navigation">
          <a
            href="#home"
            className={navClass('landing')}
            onClick={(e) => { e.preventDefault(); onNavigateSection('hero'); }}
          >
            Home
          </a>
          <a
            href="#standards"
            className={navClass('explore-standards')}
            onClick={(e) => { e.preventDefault(); onNavigateSection('explore-standards'); }}
          >
            Standards
          </a>
          <a
            href="#testing-labs"
            className={navClass('testing-labs')}
            onClick={(e) => {
              e.preventDefault();
              onNavigateSection('testing-labs');
            }}
          >
            Testing &amp; Labs
          </a>
          <a
            href="#faqs"
            className={navClass('faq')}
            onClick={(e) => {
              e.preventDefault();
              onNavigateSection('faq-page');
            }}
          >
            FAQs
          </a>
          <a
            href="#dashboard"
            className="nav-link"
            onClick={(e) => { e.preventDefault(); onOpenChatbot(); }}
          >
            Dashboard
          </a>
        </nav>

        {/* Right CTA: Chat with BISNova pill button */}
        <div className="navbar-actions">
          <button
            type="button"
            className="nav-chatbot-btn"
            onClick={onOpenChatbot}
            title="Open BISNova Chatbot"
          >
            <span className="btn-chat-icon">💬</span> Chat with BISNova
          </button>

          <div className="navbar-auth">
            {user ? (
              <>
                {isAdmin && (
                  <button
                    type="button"
                    className="navbar-auth-btn navbar-auth-register-btn"
                    onClick={onGoToAdmin}
                  >
                    Admin Dashboard
                  </button>
                )}
                <span className="navbar-user-chip">
                  {user.name}
                  <span className="navbar-user-role">
                    ({user.role})
                  </span>
                </span>
                <button
                  type="button"
                  className="navbar-auth-btn"
                  onClick={onLogout}
                >
                  Logout
                </button>
              </>
            ) : (
              <>
                <button
                  type="button"
                  className="navbar-auth-btn"
                  onClick={onGoToLogin}
                >
                  Log In
                </button>
                <button
                  type="button"
                  className="navbar-auth-btn"
                  onClick={onGoToRegister}
                >
                  Register
                </button>
              </>
            )}
          </div>
        </div>
      </div>
    </header>
  );
}
