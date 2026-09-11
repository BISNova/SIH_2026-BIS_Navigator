import React, { useMemo, useState } from 'react';

const FAQ_CATEGORIES = [
  'All Questions',
  'General Information',
  'Finding Standards',
  'Certification & ISI Mark',
  'Testing & Laboratories',
  'BIS Schemes & Services',
  'Consumers'
];

const FAQS = [
  // =========================================================================
  // GENERAL INFORMATION
  // =========================================================================

  {
    category: 'General Information',
    question: 'What is BIS?',
    answer:
      'The Bureau of Indian Standards (BIS) is India’s national standards body. It develops and publishes Indian Standards and provides services related to conformity assessment, product certification, testing, hallmarking, training and other areas connected with standards and quality.'
  },
  {
    category: 'General Information',
    question: 'What are Indian Standards?',
    answer:
      'Indian Standards are documented requirements, specifications, guidelines or methods developed for products, processes, services and other areas. They help establish consistent expectations for quality, safety, performance and reliability.'
  },
  {
    category: 'General Information',
    question: 'Why are Indian Standards important?',
    answer:
      'Standards provide a common technical reference for manufacturers, testing laboratories, regulators and consumers. Depending on the product and applicable requirements, following the relevant standard can help demonstrate conformity, improve quality and support safer products.'
  },
  {
    category: 'General Information',
    question: 'What can BISNova help me with?',
    answer:
      'BISNova is designed to help users understand BIS information through a conversational interface. You can ask about applicable Indian Standards, certification requirements, testing requirements, recognized laboratories, BIS schemes and consumer-related questions.'
  },

  // =========================================================================
  // FINDING STANDARDS
  // =========================================================================

  {
    category: 'Finding Standards',
    question: 'How do I find the Indian Standard applicable to my product?',
    answer:
      'Describe your product in plain language, including details such as what it is, what it is made of, how it is used and who it is intended for. BISNova can use that description to identify potentially relevant standards and explain why they may apply.'
  },
  {
    category: 'Finding Standards',
    question: 'I do not know my product’s IS number. Can BISNova still help?',
    answer:
      'Yes. You do not need to know the standard number to start. Describe the product and its intended use in your own words. BISNova is designed to work from product descriptions and guide you toward potentially relevant standards.'
  },
  {
    category: 'Finding Standards',
    question: 'What if more than one standard could apply to my product?',
    answer:
      'Some products may relate to more than one standard depending on their material, intended use, specifications or category. BISNova can present potential matches and, where the information provided is insufficient, ask clarifying questions instead of making an unsupported choice.'
  },
  {
    category: 'Finding Standards',
    question: 'Can BISNova explain why a particular standard matches my product?',
    answer:
      'Yes. The intended workflow is not simply to display a standard number. BISNova can explain the basis for a potential match and provide the relevant supporting information and sources so that you can understand why the standard is being suggested.'
  },

  // =========================================================================
  // CERTIFICATION & ISI MARK
  // =========================================================================

  {
    category: 'Certification & ISI Mark',
    question: 'Is BIS certification mandatory for every product?',
    answer:
      'No. BIS certification requirements depend on the product, applicable regulations and the relevant BIS scheme or legal requirement. Some products may be subject to mandatory requirements, while certification for others may operate under different arrangements.'
  },
  {
    category: 'Certification & ISI Mark',
    question: 'What is the ISI Mark?',
    answer:
      'The ISI Mark is associated with BIS product certification for products covered by the applicable certification scheme. It indicates that the certified product is covered by the relevant BIS conformity assessment requirements.'
  },
  {
    category: 'Certification & ISI Mark',
    question: 'How does the BIS certification process generally work?',
    answer:
      'The exact process depends on the applicable product and certification scheme. In general, it involves identifying the relevant requirements, meeting the applicable product and testing conditions, submitting the required information and going through the prescribed conformity assessment process.'
  },
  {
    category: 'Certification & ISI Mark',
    question: 'What information do I need before starting a certification process?',
    answer:
      'You should first establish which product category and Indian Standard apply, whether certification is required, what testing requirements exist and which documents or other information the applicable scheme requires. BISNova can help you work through these questions in sequence.'
  },

  // =========================================================================
  // TESTING & LABORATORIES
  // =========================================================================

  {
    category: 'Testing & Laboratories',
    question: 'Why does product testing matter for BIS requirements?',
    answer:
      'Testing helps determine whether a product meets the technical requirements specified by the applicable standard or conformity assessment process. The required tests depend on the product and the relevant standard.'
  },
  {
    category: 'Testing & Laboratories',
    question: 'How do I know which tests my product needs?',
    answer:
      'The required tests depend on the applicable Indian Standard and the characteristics of the product. Once the relevant standard is identified, BISNova can help present the associated testing information available in its knowledge base.'
  },
  {
    category: 'Testing & Laboratories',
    question: 'Where can I get my product tested?',
    answer:
      'Testing should be carried out through laboratories relevant to the applicable testing requirements. BISNova is designed to help users identify suitable recognized laboratories based on the product, testing scope and available location information.'
  },
  {
    category: 'Testing & Laboratories',
    question: 'Can BISNova help me find a laboratory near me?',
    answer:
      'Yes. The laboratory-finder workflow can be used to identify relevant laboratories based on location and testing requirements. You can also ask BISNova for help finding laboratories associated with a particular product or testing requirement.'
  },

  // =========================================================================
  // BIS SCHEMES & SERVICES
  // =========================================================================

  {
    category: 'BIS Schemes & Services',
    question: 'What services does BIS provide besides product certification?',
    answer:
      'BIS provides a range of services and activities including standards development and publication, product certification, hallmarking, laboratory recognition, training, conformity assessment and consumer-related initiatives.'
  },
  {
    category: 'BIS Schemes & Services',
    question: 'What is BIS hallmarking?',
    answer:
      'Hallmarking is a conformity-related system used for precious metal articles. It provides information associated with the purity or fineness of the article through the applicable hallmarking framework and processes.'
  },
  {
    category: 'BIS Schemes & Services',
    question: 'What are BIS Standards Clubs?',
    answer:
      'BIS Standards Clubs are initiatives intended to create awareness and understanding of standardization and quality among students and educational communities. They provide opportunities to engage with concepts related to standards and quality.'
  },
  {
    category: 'BIS Schemes & Services',
    question: 'Where can I learn more about BIS training and conformity assessment services?',
    answer:
      'BIS provides information about its training programmes, conformity assessment activities and other services through its official information channels. BISNova can help you identify the relevant BIS service or topic and point you toward the supporting information available to the assistant.'
  },

  // =========================================================================
  // CONSUMERS
  // =========================================================================

  {
    category: 'Consumers',
    question: 'How can I check whether a product has BIS certification?',
    answer:
      'The method for checking certification depends on the type of product and the applicable BIS certification mechanism. BISNova can help explain what information to look for and guide you toward the relevant BIS verification process.'
  },
  {
    category: 'Consumers',
    question: 'What should I look for when buying a BIS-certified product?',
    answer:
      'Look for the applicable BIS certification or marking information and check whether the product details correspond to the certification information. When in doubt, use the relevant official BIS verification mechanism rather than relying only on a visual mark.'
  },
  {
    category: 'Consumers',
    question: 'What should I do if I suspect a product is not meeting BIS requirements?',
    answer:
      'First, collect relevant information about the product, manufacturer, markings and purchase. You should then use the appropriate official BIS consumer or complaint channel for reporting or verification. BISNova can help you understand which type of BIS information or service is relevant to your question.'
  },
  {
    category: 'Consumers',
    question: 'Can consumers ask BISNova questions about product standards?',
    answer:
      'Yes. Consumers can ask questions in ordinary language, such as what a particular BIS mark means, what standard may apply to a product, what a requirement means or where to find relevant BIS information. BISNova is designed to make standards-related information easier to understand.'
  }
];

export default function FAQPage({ onOpenChatbot }) {
  const [activeCategory, setActiveCategory] = useState('All Questions');
  const [openIndex, setOpenIndex] = useState(null);
  const [searchQuery, setSearchQuery] = useState('');

  const filteredFAQs = useMemo(() => {
    const query = searchQuery.trim().toLowerCase();

    return FAQS.filter((faq) => {
      const categoryMatch =
        activeCategory === 'All Questions' ||
        faq.category === activeCategory;

      const searchMatch =
        !query ||
        faq.question.toLowerCase().includes(query) ||
        faq.answer.toLowerCase().includes(query) ||
        faq.category.toLowerCase().includes(query);

      return categoryMatch && searchMatch;
    });
  }, [activeCategory, searchQuery]);

  function handleCategoryChange(category) {
    setActiveCategory(category);
    setOpenIndex(null);
  }

  function handleSearchChange(event) {
    setSearchQuery(event.target.value);
    setOpenIndex(null);
  }

  function handleOpenQuestion(index) {
    setOpenIndex((currentIndex) =>
      currentIndex === index ? null : index
    );
  }

  return (
    <main className="faq-page">

      {/* =====================================================================
          FAQ HERO
          ===================================================================== */}

      <section className="faq-hero">
        <div className="faq-hero-bg" aria-hidden="true">
          <img
            src="/assets/landing_bg.png"
            alt=""
            className="faq-hero-bg-image"
          />

          <div className="faq-hero-overlay"></div>
        </div>

        <div className="faq-hero-content">

          <div className="faq-hero-copy">
            <span className="faq-kicker">
              FREQUENTLY ASKED QUESTIONS
            </span>

            <h1 className="faq-hero-title">
              We're here to <span>help.</span>
            </h1>

            <p className="faq-hero-description">
              Find clear answers about Indian Standards, BIS
              certification, testing, laboratories and BIS services.
              If your question is more specific, just ask BISNova.
            </p>

            <button
              type="button"
              className="faq-hero-chat-btn"
              onClick={onOpenChatbot}
            >
              Ask BISNova →
            </button>
          </div>

          <div className="faq-hero-mascot">

            <div className="faq-mascot-speech">
              Questions?
              <br />
              I've got answers!
            </div>

            <img
              src="/assets/mascot.png"
              alt="BISNova mascot"
              className="faq-mascot-image"
            />

          </div>

        </div>
      </section>

      {/* =====================================================================
          SEARCH + FAQ CONTENT
          ===================================================================== */}

      <section className="faq-content-section">

        <div className="faq-search-wrapper">

          <span
            className="faq-search-icon"
            aria-hidden="true"
          >
            <svg viewBox="0 0 24 24" fill="none">
              <circle
                cx="11"
                cy="11"
                r="6.5"
                stroke="currentColor"
                strokeWidth="2"
              />

              <path
                d="M16 16L21 21"
                stroke="currentColor"
                strokeWidth="2"
                strokeLinecap="round"
              />
            </svg>
          </span>

          <input
            type="search"
            value={searchQuery}
            onChange={handleSearchChange}
            placeholder="Search FAQs..."
            aria-label="Search frequently asked questions"
          />

          {searchQuery && (
            <button
              type="button"
              className="faq-clear-search"
              onClick={() => {
                setSearchQuery('');
                setOpenIndex(null);
              }}
              aria-label="Clear FAQ search"
            >
              ×
            </button>
          )}

        </div>

        <div className="faq-layout">

          {/* =================================================================
              CATEGORY SIDEBAR
              ================================================================= */}

          <aside className="faq-sidebar">

            <div className="faq-sidebar-title">
              Browse by topic
            </div>

            <div className="faq-category-list">

              {FAQ_CATEGORIES.map((category) => (
                <button
                  key={category}
                  type="button"
                  className={`faq-category-btn ${
                    activeCategory === category ? 'active' : ''
                  }`}
                  onClick={() => handleCategoryChange(category)}
                >
                  <span>{category}</span>

                  {activeCategory === category && (
                    <span
                      className="faq-category-arrow"
                      aria-hidden="true"
                    >
                      ›
                    </span>
                  )}
                </button>
              ))}

            </div>

            {/* Sidebar BISNova CTA */}

            <div className="faq-sidebar-cta">

              <span className="faq-sidebar-cta-kicker">
                CAN'T FIND IT?
              </span>

              <h3>
                Ask BISNova instead.
              </h3>

              <p>
                Describe your question in your own words and
                continue the conversation with the BIS assistant.
              </p>

              <button
                type="button"
                onClick={onOpenChatbot}
              >
                Chat with BISNova →
              </button>

              <img
                src="/assets/mascot.png"
                alt=""
                className="faq-sidebar-mascot"
              />

            </div>

          </aside>

          {/* =================================================================
              FAQ QUESTIONS
              ================================================================= */}

          <section className="faq-list-panel">

            <div className="faq-list-header">

              <div>
                <span className="faq-list-kicker">
                  {activeCategory === 'All Questions'
                    ? 'ALL QUESTIONS'
                    : activeCategory.toUpperCase()}
                </span>

                <h2>
                  Frequently asked questions
                </h2>
              </div>

              <span className="faq-count">
                {filteredFAQs.length}{' '}
                {filteredFAQs.length === 1
                  ? 'question'
                  : 'questions'}
              </span>

            </div>

            <div className="faq-accordion">

              {filteredFAQs.length > 0 ? (

                filteredFAQs.map((faq, index) => {
                  const isOpen = openIndex === index;

                  return (
                    <article
                      key={`${faq.category}-${faq.question}`}
                      className={`faq-item ${
                        isOpen ? 'open' : ''
                      }`}
                    >

                      <button
                        type="button"
                        className="faq-question"
                        onClick={() => handleOpenQuestion(index)}
                        aria-expanded={isOpen}
                      >

                        <span>
                          {faq.question}
                        </span>

                        <span
                          className="faq-chevron"
                          aria-hidden="true"
                        >
                          +
                        </span>

                      </button>

                      {isOpen && (
                        <div className="faq-answer">

                          <p>
                            {faq.answer}
                          </p>

                          <button
                            type="button"
                            className="faq-answer-chat-btn"
                            onClick={onOpenChatbot}
                          >
                            Need more help? Ask BISNova →
                          </button>

                        </div>
                      )}

                    </article>
                  );
                })

              ) : (

                <div className="faq-empty-state">

                  <div
                    className="faq-empty-icon"
                    aria-hidden="true"
                  >
                    ?
                  </div>

                  <h3>
                    We couldn't find that question.
                  </h3>

                  <p>
                    Try a different search, browse another category,
                    or ask BISNova directly.
                  </p>

                  <button
                    type="button"
                    onClick={onOpenChatbot}
                  >
                    Ask BISNova →
                  </button>

                </div>

              )}

            </div>

          </section>

        </div>

      </section>

      {/* =====================================================================
          BOTTOM CTA
          ===================================================================== */}

      <section className="faq-bottom-cta">

        <div className="faq-bottom-cta-content">

          <span className="faq-bottom-kicker">
            STILL HAVE A QUESTION?
          </span>

          <h2>
            Ask <span>BISNova.</span>
          </h2>

          <p>
            Get clear, source-backed guidance in a conversation
            instead of searching through pages of information.
          </p>

          <button
            type="button"
            onClick={onOpenChatbot}
          >
            Start a Conversation →
          </button>

        </div>

        <div className="faq-bottom-mascot-wrap">

          <div className="faq-bottom-speech">
            No question is too specific.
          </div>

          <img
            src="/assets/mascot.png"
            alt="BISNova mascot"
            className="faq-bottom-mascot"
          />

        </div>

      </section>

    </main>
  );
}