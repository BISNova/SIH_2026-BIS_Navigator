import React, { useEffect, useRef } from 'react';

export default function MessageList({ messages, isThinking, onChipClick, onFeedback }) {
  const messagesEndRef = useRef(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, isThinking]);

  return (
    <section className="chat-stream-viewport" aria-label="Chat Conversation">
      {/* Decorative motivational note on right (matching Image 1)
      <div className="chat-floating-slogan" aria-hidden="true">
        <span>Same Standards.<br /><em>Brighter Possibilities!</em></span>
        <div className="slogan-curve-line"></div>
      </div> */}

      <div className="chat-messages-inner">
        {messages.length === 0 && !isThinking && (
          <div className="chat-empty-state">
            <img src="/assets/bisnova_logo.png" alt="BISNova" className="chat-empty-logo" />
            <h2>Namaste! I'm BISNova 👋</h2>
            <p>
              Ask me anything about Indian Standards, BIS certification, testing
              requirements, or hallmarking — I'll find the applicable standard and
              cite my sources.
            </p>
          </div>
        )}

        {messages.map((msg, index) => {
          const isBot = msg.sender === 'bot';

          return (
            <div
              key={index}
              className={`message-bubble-row ${isBot ? 'bot-row' : 'user-row'} ${msg.isNew ? 'pop-in' : ''}`}
            >
              {/* Bot Avatar on Left */}
              {isBot && (
                <div className="msg-avatar-col bot-avatar">
                  <img src="/assets/logo.png" alt="BISNova" className="msg-avatar-img" />
                </div>
              )}

              {/* Bubble Body */}
              <div className="msg-bubble-card">
                {/* File Attachment if any */}
                {msg.file && (
                  <div className="msg-attached-file-badge">
                    <span>📎</span> <strong>{msg.file.name}</strong>
                  </div>
                )}

                {/* Message Text */}
                <div className="msg-text-content">
                  {msg.text.split('\n').map((line, lIdx) => (
                    <p key={lIdx}>{line}</p>
                  ))}
                </div>

                {/* Rich Standard Card (if present) - singular, kept for
                    backward compatibility with pre-seeded demo chats */}
                {msg.standardCard && (
                  <div className="msg-standard-feature-card">
                    <div className="std-doc-icon">📄</div>
                    <div className="std-doc-text">
                      <strong className="std-doc-code">{msg.standardCard.code}</strong>
                      <span className="std-doc-title">{msg.standardCard.title}</span>
                    </div>
                  </div>
                )}

                {/* Multiple Standard Cards (real backend responses - a
                    product can have more than one applicable standard,
                    e.g. a mandatory safety standard + a secondary one) */}
                 {/* {msg.standardCards && msg.standardCards.length > 0 && (
                  <div className="msg-standard-cards-group">
                    {msg.standardCards.map((std, sIdx) => (
                      <div key={sIdx} className="msg-standard-feature-card">
                        <div className="std-doc-icon">📄</div>
                        <div className="std-doc-text">
                          <strong className="std-doc-code">
                            {std.code}
                            {std.mandatory === true && (
                              <span className="std-mandatory-badge"> · MANDATORY</span>
                            )}
                            {std.relationship_type === 'secondary' && (
                              <span className="std-secondary-badge"> · related</span>
                            )}
                          </strong>
                          <span className="std-doc-title">{std.title}</span>
                          {std.lastVerified && (
                            <span className="std-last-verified">Data as of: {std.lastVerified}</span>
                          )}
                        </div>
                      </div>
                    ))}
                  </div>
                )}  */}
                {msg.standardCards && msg.standardCards.length > 0 && (
                  <div className="msg-citation-pills-row">
                    {msg.standardCards.map((std, sIdx) => {
                      const Tag = std.sourceUrl ? 'a' : 'span';
                      const linkProps = std.sourceUrl
                        ? { href: std.sourceUrl, target: '_blank', rel: 'noopener noreferrer' }
                        : {};
                      return (
                        <Tag
                          key={sIdx}
                          className={`std-citation-pill${std.sourceUrl ? '' : ' no-link'}`}
                          title={std.title}
                          {...linkProps}
                        >
                          <span className="std-pill-icon">📄</span>
                          <span className="std-pill-code">{std.code}</span>
                          {std.mandatory === true && <span className="std-pill-tag mandatory">Mandatory</span>}
                          {std.relationship_type === 'secondary' && <span className="std-pill-tag related">Related</span>}
                        </Tag>
                      );
                    })}
                  </div>
                )}


                {/* Confidence badge - judges' feedback: "answer confidence
                    score shown in UI" */}
                {/* {isBot && msg.confidenceLabel && (
                  <div className={`msg-confidence-badge confidence-${msg.confidenceLabel}`}>
                    Confidence: {msg.confidenceLabel}
                  </div>
                )} */}

                {/* Attached Quick Action Chips (matching Image 1) */}
                {isBot && msg.actionChips && (
                  <div className="msg-attached-chips-row">
                    {msg.actionChips.map((chip, cIdx) => (
                      <button
                        key={cIdx}
                        type="button"
                        className="msg-action-chip"
                        onClick={() => onChipClick(chip.query)}
                      >
                        <span className="chip-icon">{chip.icon}</span>
                        <span>{chip.label}</span>
                      </button>
                    ))}
                  </div>
                )}

                {/* Footer: Timestamp & Read Status */}
                <div className="msg-meta-row">
                  <span className="msg-timestamp">{msg.time || '10:24 AM'}</span>
                  {!isBot && <span className="read-receipt-ticks">✓✓</span>}
                  {isBot && msg.feedbackQuery && (
                    <div className="msg-feedback-buttons">
                      <button
                        type="button"
                        className={`feedback-btn ${msg.feedbackGiven === 'up' ? 'active' : ''}`}
                        onClick={() => onFeedback(index, 'up')}
                        disabled={!!msg.feedbackGiven}
                        title="This answer was helpful"
                      >
                        👍
                      </button>
                      <button
                        type="button"
                        className={`feedback-btn ${msg.feedbackGiven === 'down' ? 'active' : ''}`}
                        onClick={() => onFeedback(index, 'down')}
                        disabled={!!msg.feedbackGiven}
                        title="This answer was not helpful"
                      >
                        👎
                      </button>
                      {msg.feedbackGiven && <span className="feedback-thanks">Thanks for the feedback!</span>}
                    </div>
                  )}
                </div>
              </div>

              {/* User Avatar on Right */}
              {!isBot && (
                <div className="msg-avatar-col user-avatar">
                  <span className="user-initial">A</span>
                </div>
              )}
            </div>
          );
        })}

        {/* Thinking Indicator */}
        {isThinking && (
          <div className="message-bubble-row bot-row pop-in">
            <div className="msg-avatar-col bot-avatar">
              <img src="/assets/logo.png" alt="BISNova" className="msg-avatar-img" />
            </div>

            <div className="msg-bubble-card typing-bubble">
              <div className="typing-dots-group">
                <span className="dot d1"></span>
                <span className="dot d2"></span>
                <span className="dot d3"></span>
              </div>
              <span className="typing-label">BISNova is finding verified standards...</span>
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>
    </section>
  );
}
