import React from 'react';

export default function Navbar({
  onOpenChatbot,
  onNavigateSection,
  activeSection
}) {

  // ============================================================
  // NAVIGATION HANDLER
  // ============================================================

  const navigate = (event, destination) => {
    event.preventDefault();

    if (onNavigateSection) {
      onNavigateSection(destination);
    }
  };


  // ============================================================
  // HOME
  // ============================================================

  const handleHome = (event) => {
    navigate(event, 'home');
  };


  // ============================================================
  // STANDARDS
  // ============================================================

  const handleStandards = (event) => {
    navigate(event, 'standards');
  };


  // ============================================================
  // FAQ
  // ============================================================

  const handleFAQs = (event) => {
    navigate(event, 'faq');
  };


  // ============================================================
  // DASHBOARD / CHATBOT
  // ============================================================

  const handleDashboard = (event) => {
    event.preventDefault();

    if (onOpenChatbot) {
      onOpenChatbot();
    }
  };


  return (
    <header className="landing-navbar">

      <div className="navbar-container">

        {/* ======================================================
            LOGO
            ====================================================== */}

        <a
          href="#home"
          className="navbar-logo-wrap"
          onClick={handleHome}
          aria-label="BISNova Home"
        >
          <img
            src="/assets/bisnova_logo.png"
            alt="BISNova Logo"
            className="navbar-logo"
          />
        </a>


        {/* ======================================================
            CENTER NAVIGATION
            ====================================================== */}

        <nav
          className="navbar-links"
          aria-label="Main navigation"
        >

          {/* ----------------------------------------------------
              HOME
              ---------------------------------------------------- */}

          <a
            href="#home"
            className={`nav-link ${
              activeSection === 'home' ||
              activeSection === 'hero'
                ? 'active'
                : ''
            }`}
            onClick={handleHome}
          >
            Home
          </a>


          {/* ----------------------------------------------------
              STANDARDS
              ---------------------------------------------------- */}

          <a
            href="#standards"
            className={`nav-link ${
              activeSection === 'standards' ||
              activeSection === 'how-bisnova-helps'
                ? 'active'
                : ''
            }`}
            onClick={handleStandards}
          >
            Standards
          </a>


          {/* ----------------------------------------------------
              FAQs
              ---------------------------------------------------- */}

          <a
            href="#faqs"
            className={`nav-link ${
              activeSection === 'faq' ||
              activeSection === 'faq-page'
                ? 'active'
                : ''
            }`}
            onClick={handleFAQs}
          >
            FAQs
          </a>


          {/* ----------------------------------------------------
              DASHBOARD
              ---------------------------------------------------- */}

          <a
            href="#dashboard"
            className={`nav-link ${
              activeSection === 'dashboard'
                ? 'active'
                : ''
            }`}
            onClick={handleDashboard}
          >
            Dashboard
          </a>

        </nav>


        {/* ======================================================
            CHATBOT CTA
            ====================================================== */}

        <div className="navbar-actions">

          <button
            type="button"
            className="nav-chatbot-btn"
            onClick={handleDashboard}
            title="Open BISNova Chatbot"
          >
            <span className="btn-chat-icon">
              💬
            </span>

            Chat with BISNova
          </button>

        </div>

      </div>

    </header>
  );
}