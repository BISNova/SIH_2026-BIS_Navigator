import React, { useEffect, useRef } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

export default function MessageList({
  messages,
  isThinking,
  onChipClick
}) {
  const messagesEndRef = useRef(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({
      behavior: 'smooth'
    });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, isThinking]);

  return (
    <section
      className="chat-stream-viewport"
      aria-label="Chat Conversation"
    >
      {/* Decorative motivational note on right
      <div className="chat-floating-slogan" aria-hidden="true">
        <span>
          Same Standards.<br />
          <em>Brighter Possibilities!</em>
        </span>
        <div className="slogan-curve-line"></div>
      </div>
      */}

      <div className="chat-messages-inner">

        {messages.map((msg, index) => {
          const isBot = msg.sender === 'bot';

          return (
            <div
              key={index}
              className={`message-bubble-row ${
                isBot ? 'bot-row' : 'user-row'
              } ${msg.isNew ? 'pop-in' : ''}`}
            >

              {/* ==========================================================
                  BOT AVATAR
                  ========================================================== */}

              {isBot && (
                <div className="msg-avatar-col bot-avatar">
                  <img
                    src="/assets/logo.png"
                    alt="BISNova"
                    className="msg-avatar-img"
                  />
                </div>
              )}


              {/* ==========================================================
                  MESSAGE BUBBLE
                  ========================================================== */}

              <div className="msg-bubble-card">

                {/* --------------------------------------------------------
                    FILE ATTACHMENT
                    -------------------------------------------------------- */}

                {msg.file && (
                  <div className="msg-attached-file-badge">
                    <span>📎</span>
                    <strong>{msg.file.name}</strong>
                  </div>
                )}


                {/* --------------------------------------------------------
                    MESSAGE TEXT

                    IMPORTANT:
                    ReactMarkdown converts the Markdown returned by
                    the BISNova backend into proper HTML elements.
                    -------------------------------------------------------- */}

                <div className="msg-text-content markdown-content">

                  <ReactMarkdown
                    remarkPlugins={[remarkGfm]}
                    components={{

                      /* Headings */

                      h1: ({ children }) => (
                        <h1>{children}</h1>
                      ),

                      h2: ({ children }) => (
                        <h2>{children}</h2>
                      ),

                      h3: ({ children }) => (
                        <h3>{children}</h3>
                      ),

                      h4: ({ children }) => (
                        <h4>{children}</h4>
                      ),


                      /* Paragraph */

                      p: ({ children }) => (
                        <p>{children}</p>
                      ),


                      /* Bold */

                      strong: ({ children }) => (
                        <strong>{children}</strong>
                      ),


                      /* Italic */

                      em: ({ children }) => (
                        <em>{children}</em>
                      ),


                      /* Unordered list */

                      ul: ({ children }) => (
                        <ul>{children}</ul>
                      ),


                      /* Ordered list */

                      ol: ({ children }) => (
                        <ol>{children}</ol>
                      ),


                      /* List item */

                      li: ({ children }) => (
                        <li>{children}</li>
                      ),


                      /* Links */

                      a: ({ href, children }) => (
                        <a
                          href={href}
                          target="_blank"
                          rel="noopener noreferrer"
                        >
                          {children}
                        </a>
                      ),


                      /* Blockquote */

                      blockquote: ({ children }) => (
                        <blockquote>{children}</blockquote>
                      ),


                      /* Inline / block code */

                      code: ({ className, children }) => {
                        const isBlock =
                          className?.startsWith('language-');

                        if (isBlock) {
                          return (
                            <pre>
                              <code className={className}>
                                {children}
                              </code>
                            </pre>
                          );
                        }

                        return (
                          <code className={className}>
                            {children}
                          </code>
                        );
                      },


                      /* Code block wrapper */

                      pre: ({ children }) => (
                        <pre>{children}</pre>
                      ),


                      /* Horizontal rule */

                      hr: () => (
                        <hr />
                      ),


                      /* Tables */

                      table: ({ children }) => (
                        <div className="markdown-table-wrapper">
                          <table>{children}</table>
                        </div>
                      ),

                      thead: ({ children }) => (
                        <thead>{children}</thead>
                      ),

                      tbody: ({ children }) => (
                        <tbody>{children}</tbody>
                      ),

                      tr: ({ children }) => (
                        <tr>{children}</tr>
                      ),

                      th: ({ children }) => (
                        <th>{children}</th>
                      ),

                      td: ({ children }) => (
                        <td>{children}</td>
                      )
                    }}
                  >
                    {msg.text || ''}
                  </ReactMarkdown>

                </div>


                {/* ========================================================
                    SINGLE STANDARD CARD
                    ======================================================== */}

                {msg.standardCard && (
                  <div className="msg-standard-feature-card">

                    <div className="std-doc-icon">
                      📄
                    </div>

                    <div className="std-doc-text">

                      <strong className="std-doc-code">
                        {msg.standardCard.code}
                      </strong>

                      <span className="std-doc-title">
                        {msg.standardCard.title}
                      </span>

                    </div>

                  </div>
                )}


                {/* ========================================================
                    MULTIPLE STANDARD CARDS
                    ======================================================== */}

                {msg.standardCards &&
                  msg.standardCards.length > 0 && (

                    <div className="msg-standard-cards-group">

                      {msg.standardCards.map(
                        (std, sIdx) => (

                          <div
                            key={sIdx}
                            className="msg-standard-feature-card"
                          >

                            <div className="std-doc-icon">
                              📄
                            </div>

                            <div className="std-doc-text">

                              <strong className="std-doc-code">

                                {std.code}

                                {std.mandatory === true && (
                                  <span className="std-mandatory-badge">
                                    {' · MANDATORY'}
                                  </span>
                                )}

                                {std.relationship_type ===
                                  'secondary' && (
                                  <span className="std-secondary-badge">
                                    {' · related'}
                                  </span>
                                )}

                              </strong>

                              <span className="std-doc-title">
                                {std.title}
                              </span>

                            </div>

                          </div>

                        )
                      )}

                    </div>

                  )}


                {/* ========================================================
                    ACTION CHIPS
                    ======================================================== */}

                {isBot &&
                  msg.actionChips &&
                  msg.actionChips.length > 0 && (

                    <div className="msg-attached-chips-row">

                      {msg.actionChips.map(
                        (chip, cIdx) => (

                          <button
                            key={cIdx}
                            type="button"
                            className="msg-action-chip"
                            onClick={() =>
                              onChipClick(chip.query)
                            }
                          >

                            <span className="chip-icon">
                              {chip.icon}
                            </span>

                            <span>
                              {chip.label}
                            </span>

                          </button>

                        )
                      )}

                    </div>

                  )}


                {/* ========================================================
                    MESSAGE FOOTER
                    ======================================================== */}

                <div className="msg-meta-row">

                  <span className="msg-timestamp">
                    {msg.time || '10:24 AM'}
                  </span>

                  {!isBot && (
                    <span className="read-receipt-ticks">
                      ✓✓
                    </span>
                  )}

                </div>

              </div>


              {/* ==========================================================
                  USER AVATAR
                  ========================================================== */}

              {!isBot && (
                <div className="msg-avatar-col user-avatar">
                  <span className="user-initial">
                    A
                  </span>
                </div>
              )}

            </div>
          );
        })}


        {/* ================================================================
            THINKING INDICATOR
            ================================================================ */}

        {isThinking && (

          <div className="message-bubble-row bot-row pop-in">

            <div className="msg-avatar-col bot-avatar">

              <img
                src="/assets/logo.png"
                alt="BISNova"
                className="msg-avatar-img"
              />

            </div>


            <div className="msg-bubble-card typing-bubble">

              <div className="typing-dots-group">

                <span className="dot d1"></span>
                <span className="dot d2"></span>
                <span className="dot d3"></span>

              </div>

              <span className="typing-label">
                BISNova is finding verified standards...
              </span>

            </div>

          </div>

        )}


        {/* Scroll anchor */}

        <div ref={messagesEndRef} />

      </div>
    </section>
  );
}