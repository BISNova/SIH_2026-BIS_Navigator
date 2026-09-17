import React, { useEffect, useMemo, useState } from 'react';
import { fetchCatalogStandards, BISNovaAPIError } from '../api';

/**
 * A real, browsable catalog of every standard in the knowledge base -
 * grows automatically as the knowledge base grows, no code change needed.
 */
export default function ExploreStandardsPage({ onAskAboutStandard }) {
  const [standards, setStandards] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [searchTerm, setSearchTerm] = useState('');
  const [activeCategory, setActiveCategory] = useState('All Categories');

  useEffect(() => {
    let cancelled = false;

    fetchCatalogStandards()
      .then(data => {
        if (!cancelled) {
          setStandards(data);
          setLoading(false);
        }
      })
      .catch(err => {
        if (!cancelled) {
          setError(
            err instanceof BISNovaAPIError
              ? err.message
              : 'Something went wrong loading standards.'
          );
          setLoading(false);
        }
      });

    return () => { cancelled = true; };
  }, []);

  const categories = useMemo(() => {
    const set = new Set(standards.map(s => s.product_category).filter(Boolean));
    return ['All Categories', ...Array.from(set).sort()];
  }, [standards]);

  const filteredStandards = useMemo(() => {
    return standards.filter(std => {
      const matchesCategory =
        activeCategory === 'All Categories' || std.product_category === activeCategory;

      const term = searchTerm.trim().toLowerCase();
      const matchesSearch =
        term === '' ||
        std.title.toLowerCase().includes(term) ||
        std.is_number.toLowerCase().includes(term) ||
        (std.product_category || '').toLowerCase().includes(term);

      return matchesCategory && matchesSearch;
    });
  }, [standards, searchTerm, activeCategory]);

  return (
    <main className="explore-standards-page">
      <section className="explore-standards-hero">
        <span className="explore-kicker">Knowledge Base</span>
        <h1 className="explore-hero-title">Explore Standards</h1>
        <p className="explore-hero-description">
          Every Indian Standard currently in BISNova's curated knowledge base.
          Search by name, category, or IS number - click any standard to ask
          BISNova about it directly.
        </p>

        <div className="explore-search-wrapper">
          <svg className="explore-search-icon" width="18" height="18" viewBox="0 0 24 24" fill="none">
            <circle cx="11" cy="11" r="7" stroke="currentColor" strokeWidth="2" />
            <line x1="21" y1="21" x2="16.65" y2="16.65" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
          </svg>
          <input
            type="text"
            placeholder="Search standards by name, IS number, or category..."
            value={searchTerm}
            onChange={e => setSearchTerm(e.target.value)}
            className="explore-search-input"
          />
          {searchTerm && (
            <button className="explore-clear-search" onClick={() => setSearchTerm('')}>
              ✕
            </button>
          )}
        </div>
      </section>

      <section className="explore-standards-content">
        {!loading && !error && (
          <div className="explore-category-pills">
            {categories.map(cat => (
              <button
                key={cat}
                className={`explore-pill ${activeCategory === cat ? 'active' : ''}`}
                onClick={() => setActiveCategory(cat)}
              >
                {cat}
              </button>
            ))}
          </div>
        )}

        {loading && (
          <div className="explore-state-message">Loading standards…</div>
        )}

        {error && (
          <div className="explore-state-message explore-state-error">
            {error}
          </div>
        )}

        {!loading && !error && filteredStandards.length === 0 && (
          <div className="explore-state-message">
            No standards match your search. Try a different term or category.
          </div>
        )}

        {!loading && !error && filteredStandards.length > 0 && (
          <div className="explore-standards-grid">
            {filteredStandards.map(std => (
              <article key={std.standard_id} className="explore-standard-card">
                <div className="explore-card-top">
                  <span className="explore-card-is-number">{std.is_number}</span>
                  <div className="explore-card-badges">
                    {std.is_mandatory === true && (
                      <span className="explore-badge explore-badge-mandatory">MANDATORY</span>
                    )}
                    {std.status === 'withdrawn' && (
                      <span className="explore-badge explore-badge-withdrawn">WITHDRAWN</span>
                    )}
                  </div>
                </div>

                <h3 className="explore-card-title">{std.title}</h3>

                {std.product_category && (
                  <span className="explore-card-category">{std.product_category}</span>
                )}

                {std.scope_summary && (
                  <p className="explore-card-scope">{std.scope_summary}</p>
                )}

                <div className="explore-card-actions">
                  <button
                    className="explore-card-ask-btn"
                    onClick={() => onAskAboutStandard(std.ask_query)}
                  >
                    Ask BISNova →
                  </button>
                  {std.source_url && (
                    <a
                      href={std.source_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="explore-card-source-link"
                    >
                      Source
                    </a>
                  )}
                </div>
              </article>
            ))}
          </div>
        )}
      </section>
    </main>
  );
}
