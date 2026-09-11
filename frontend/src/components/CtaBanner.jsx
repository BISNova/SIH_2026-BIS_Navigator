import React from 'react';

export default function CtaBanner({ onOpenChatbot }) {
  return (
    <section className="cta-banner-section">
      <div className="cta-banner-card">
        {/* Left: Mascot with quote */}
        <div className="cta-mascot-col">
          <div className="cta-mascot-bubble" aria-hidden="true">
            <span>Still have questions?</span>
          </div>
          <img
            src="/assets/mascot.png"
            alt="BISNova Mascot"
            className="cta-mascot-img"
          />
        </div>

        {/* Center: Headline and Description */}
        <div className="cta-text-col">
          <h2 className="cta-heading">
            Ask <span className="cta-brand-red">BISNova</span>.
          </h2>
          <p className="cta-desc">
            From finding the right standard to understanding what comes next,
            start with a question.
          </p>
        </div>

        {/* Right: Action Button */}
        <div className="cta-btn-col">
          <button
            type="button"
            className="cta-start-conv-btn"
            onClick={onOpenChatbot}
            title="Start a conversation with BISNova"
          >
            <span>Start a Conversation</span>
            <span className="btn-arrow">→</span>
          </button>
        </div>
      </div>
    </section>
  );
}
