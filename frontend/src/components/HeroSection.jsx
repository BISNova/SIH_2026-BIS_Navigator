import React from 'react';

export default function HeroSection({ onOpenChatbot, onExploreStandards }) {
  return (
    <section className="hero-section" id="hero">
      {/* Background with India Gate landscape */}
      <div className="hero-bg-container" aria-hidden="true">
        <img
          src="/assets/landing_bg.png"
          alt="India Gate Sunrise"
          className="hero-bg-image"
        />
        <div className="hero-bg-overlay"></div>
      </div>

      <div className="hero-content-container">
        {/* Left Column: Headlines, CTAs, Trust Badges */}
        <div className="hero-left-column">
          <span className="hero-pre-kicker">YOUR GUIDE TO INDIAN STANDARDS</span>

          <div className="hero-title-group">
            <h1 className="hero-headline">
              Hi, I’m <span className="bisnova-brand-text">BISNova</span>.
            </h1>
            <h2 className="hero-tagline">
              Your guide to Indian Standards.
            </h2>
          </div>

          <p className="hero-description">
            From finding the right standard to understanding certification and testing,
            get clear, source-backed answers in one conversation.
          </p>

          <div className="hero-buttons-row">
            <button
              type="button"
              className="hero-btn-primary"
              onClick={onOpenChatbot}
              title="Start chatting with BISNova"
            >
              <span>Talk to BISNova</span>
              <span className="btn-arrow">→</span>
            </button>

            <button
              type="button"
              className="hero-btn-secondary"
              onClick={onExploreStandards}
              title="Explore Indian Standards catalog"
            >
              <span>Explore Standards</span>
            </button>
          </div>

          {/* Trust badges underneath buttons */}
          <div className="hero-trust-badges">
            <div className="trust-badge-item">
              <span className="trust-icon">🛡️</span>
              <div className="trust-text">
                <strong>Source-backed</strong>
                <span>answers</span>
              </div>
            </div>
            <div className="trust-badge-item">
              <span className="trust-icon">👥</span>
              <div className="trust-text">
                <strong>For industry</strong>
                <span>& consumers</span>
              </div>
            </div>
            <div className="trust-badge-item">
              <span className="trust-icon">🌐</span>
              <div className="trust-text">
                <strong>English & Hindi</strong>
                <span>supported</span>
              </div>
            </div>
          </div>
        </div>

        {/* Right Column: 3D Perspective Laptop Mockup (overflows frame for 3D depth) */}
        <div className="hero-right-column">
          <div className="hero-laptop-wrap">
            <img
              src="/assets/laptop_mockup.png"
              alt="BISNova Chatbot Interface running on laptop"
              className="hero-laptop-img"
              onClick={onOpenChatbot}
              title="Click to launch interactive Chatbot"
            />
            {/* Playful callout badge */}
            <div className="hero-laptop-callout" aria-hidden="true">
              <span>Standards today.<br /><em>A brighter tomorrow.</em></span>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
