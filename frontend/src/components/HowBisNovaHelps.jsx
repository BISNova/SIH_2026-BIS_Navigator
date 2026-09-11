import React from 'react';

export default function HowBisNovaHelps({ onOpenChatbotWithQuery }) {
  return (
    <section className="how-bisnova-helps-section" id="how-bisnova-helps">
      <div className="section-header-wrap">
        <div className="header-text-block">
          <span className="section-kicker">HOW BISNOVA HELPS</span>
          <h2 className="section-main-heading">
            Just ask. <span className="brand-accent">BISNova</span> takes it from there.
          </h2>
          <p className="section-sub-heading">
            No need to know the right standard, scheme or technical terms.
            Start with what you know, and let BISNova help you figure out what you need.
          </p>
        </div>

        <div className="header-handwriting-note" aria-hidden="true">
          <span>You ask.<br />BISNova finds the answers.</span>
          <svg className="curved-arrow" width="36" height="36" viewBox="0 0 40 40" fill="none">
            <path d="M 10 10 Q 25 15 28 30 M 20 28 L 28 30 L 30 20" stroke="#E66A3A" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
        </div>
      </div>

      {/* 3 Step Interactive Workflow Cards */}
      <div className="steps-container">
        {/* Step 01 */}
        <div className="step-card">
          <div className="step-card-top">
            <span className="step-number">01</span>
            <div className="step-title-block">
              <h3 className="step-title">Tell BISNova what you need</h3>
              <p className="step-desc">
                Describe your product, process or ask any question — in your own words.
              </p>
            </div>
          </div>

          <div className="step-preview-box">
            <div className="user-query-pill">
              <span className="user-avatar-circle">👤</span>
              <p>I manufacture stainless-steel bottles. Which BIS standard applies to me?</p>
            </div>

            <div className="step-mascot-row">
              <img src="/assets/mascot.png" alt="Mascot" className="step-mini-mascot" />
              <div className="step-mascot-speech">
                <span>Any question is the right question!</span>
              </div>
            </div>
          </div>
        </div>

        {/* Step 02 */}
        <div className="step-card">
          <div className="step-card-top">
            <span className="step-number">02</span>
            <div className="step-title-block">
              <h3 className="step-title">Get a clear answer</h3>
              <p className="step-desc">
                BISNova finds what applies to your situation, explains it in simple language, and shows sources.
              </p>
            </div>
          </div>

          <div className="step-preview-box step-answer-box">
            <div className="bot-answer-snippet">
              <div className="bot-snippet-header">
                <img src="/assets/logo.png" alt="BISNova" className="bot-icon-small" />
                <span>For stainless-steel bottles, the applicable standard is:</span>
              </div>

              <div className="standard-highlight-badge">
                <strong>IS 17526:2021</strong> – Stainless Steel Vacuum Insulated Bottles.
              </div>

              <p className="standard-snippet-text">
                This standard specifies requirements for materials, construction, performance and testing methods.
              </p>

              <div className="source-link-row">
                <span className="source-tag">📄 Source: BIS IS 17526:2021</span>
                <span className="source-action">View Source →</span>
              </div>
            </div>

            <div className="snippet-quick-actions">
              <button
                type="button"
                className="snippet-pill"
                onClick={() => onOpenChatbotWithQuery('Explain IS 17526 in simpler terms')}
              >
                Explain in simpler terms
              </button>
              <button
                type="button"
                className="snippet-pill"
                onClick={() => onOpenChatbotWithQuery('Show full standard IS 17526')}
              >
                Show full standard
              </button>
            </div>
          </div>
        </div>

        {/* Step 03 */}
        <div className="step-card">
          <div className="step-card-top">
            <span className="step-number">03</span>
            <div className="step-title-block">
              <h3 className="step-title">Know what to do next</h3>
              <p className="step-desc">
                Get the relevant requirements, certification or testing information, and recognized laboratories.
              </p>
            </div>
          </div>

          <div className="step-preview-box next-actions-box">
            <div className="next-actions-header">
              <img src="/assets/logo.png" alt="BISNova" className="bot-icon-small" />
              <span>Here's what you can do next:</span>
            </div>

            <div className="next-actions-list">
              <div
                className="action-nav-item"
                onClick={() => onOpenChatbotWithQuery('Tell me about the Certification Process for stainless steel bottles')}
              >
                <div className="action-nav-icon red">📄</div>
                <div className="action-nav-text">
                  <strong>Certification Process</strong>
                  <span>Steps, documents and requirements</span>
                </div>
                <span className="action-chevron">›</span>
              </div>

              <div
                className="action-nav-item"
                onClick={() => onOpenChatbotWithQuery('What are the Testing Requirements for IS 17526?')}
              >
                <div className="action-nav-icon orange">🧪</div>
                <div className="action-nav-text">
                  <strong>Testing Requirements</strong>
                  <span>Tests, methods and parameters</span>
                </div>
                <span className="action-chevron">›</span>
              </div>

              <div
                className="action-nav-item"
                onClick={() => onOpenChatbotWithQuery('Find recognized testing laboratories near me')}
              >
                <div className="action-nav-icon blue">📍</div>
                <div className="action-nav-text">
                  <strong>Find Recognized Laboratories</strong>
                  <span>Labs near you with relevant scope</span>
                </div>
                <span className="action-chevron">›</span>
              </div>

              <div
                className="action-nav-item"
                onClick={() => onOpenChatbotWithQuery('Show related standards for bottles and food contact')}
              >
                <div className="action-nav-icon green">📖</div>
                <div className="action-nav-text">
                  <strong>Related Standards</strong>
                  <span>Other applicable and complementary standards</span>
                </div>
                <span className="action-chevron">›</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
