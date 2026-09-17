import React, { useEffect, useState } from 'react';
import { fetchCatalogLabs, BISNovaAPIError } from '../api';

export default function StandardsAndLabs({ onOpenChatbotWithQuery, onExploreStandards }) {
  const [searchCity, setSearchCity] = useState('');
  const [labs, setLabs] = useState([]);
  const [labsLoading, setLabsLoading] = useState(true);
  const [labsError, setLabsError] = useState(null);

  useEffect(() => {
    let cancelled = false;

    fetchCatalogLabs()
      .then(data => {
        if (!cancelled) {
          setLabs(data);
          setLabsLoading(false);
        }
      })
      .catch(err => {
        if (!cancelled) {
          setLabsError(
            err instanceof BISNovaAPIError
              ? err.message
              : 'Could not load laboratories right now.'
          );
          setLabsLoading(false);
        }
      });

    return () => { cancelled = true; };
  }, []);

  const term = searchCity.trim().toLowerCase();
  const filteredLabs = term === ''
    ? labs
    : labs.filter(lab =>
        (lab.city || '').toLowerCase().includes(term) ||
        (lab.state || '').toLowerCase().includes(term) ||
        (lab.district || '').toLowerCase().includes(term) ||
        lab.lab_name.toLowerCase().includes(term) ||
        (lab.lab_type || '').toLowerCase().includes(term)
      );

  return (
    <section className="standards-labs-section" id="standards-labs">
      <div className="standards-labs-grid">
        {/* Left Card: Knowledge Base Showcase */}
        <div className="knowledge-card">
          <span className="card-kicker">EXPLORE THE KNOWLEDGE BASE</span>
          <h3 className="card-heading">Find the standard you need.</h3>
          <p className="card-description">
            Search and explore Indian Standards from our curated knowledge base.
            Discover product standards, related standards and technical information in one place.
          </p>

          <button
            type="button"
            className="explore-standards-cta"
            onClick={onExploreStandards}
          >
            Explore Standards →
          </button>

          {/* Document Graphic Illustration */}
          <div className="standards-doc-graphic-wrap">
            <div className="doc-paper stack-back"></div>
            <div className="doc-paper stack-mid"></div>
            <div className="doc-paper stack-front">
              <div className="doc-seal">IS</div>
              <div className="doc-title-text">Indian Standard</div>
              <div className="doc-lines">
                <span className="doc-line l1"></span>
                <span className="doc-line l2"></span>
                <span className="doc-line l3"></span>
              </div>
            </div>
          </div>

          {/* Category Chips */}
          <div className="standards-chips-row">
            <button
              type="button"
              className="std-chip"
              onClick={() => onOpenChatbotWithQuery('Show mandatory product standards')}
            >
              📄 Product Standards
            </button>
            <button
              type="button"
              className="std-chip"
              onClick={() => onOpenChatbotWithQuery('Show related standards')}
            >
              📚 Related Standards
            </button>
            <button
              type="button"
              className="std-chip"
              onClick={() => onOpenChatbotWithQuery('Explain technical testing specifications')}
            >
              ℹ️ Technical Details
            </button>
          </div>
        </div>

        {/* Right Card: Lab Locator */}
        <div className="lab-locator-card">
          <span className="card-kicker">TESTING MADE EASIER</span>
          <h3 className="card-heading">Find a recognized laboratory near you.</h3>
          <p className="card-description">
            Looking for somewhere to test your product? Discover laboratories matching your testing requirements and location.
          </p>

          {/* Interactive Search Bar */}
          <div className="lab-search-input-wrap">
            <span className="pin-icon">📍</span>
            <input
              type="text"
              className="lab-search-input"
              placeholder="Search by city, state, or lab name..."
              value={searchCity}
              onChange={(e) => setSearchCity(e.target.value)}
            />
            {searchCity && (
              <button
                type="button"
                className="lab-search-submit-btn"
                onClick={() => setSearchCity('')}
                title="Clear search"
              >
                ✕
              </button>
            )}
          </div>

          {/* Laboratory List */}
          <div className="lab-results-header">
            <span className="lab-results-title">
              {labsLoading ? 'Loading laboratories…' : `${filteredLabs.length} recognized laboratories`}
            </span>
            {searchCity && (
              <button
                type="button"
                className="view-all-labs-btn"
                onClick={() => setSearchCity('')}
              >
                View all
              </button>
            )}
          </div>

          {labsError && (
            <div className="lab-slogan-note">
              <span>{labsError}</span>
            </div>
          )}

          {!labsLoading && !labsError && (
            <div className="lab-items-list">
              {filteredLabs.slice(0, 6).map((lab) => (
                <div
                  key={lab.lab_id}
                  className="lab-item-row"
                  onClick={() => onOpenChatbotWithQuery(
                    `Give details and contact information for ${lab.lab_name} in ${lab.city || lab.state || 'India'}`
                  )}
                >
                  <div className="lab-item-icon">📍</div>
                  <div className="lab-item-info">
                    <strong>{lab.lab_name}</strong>
                    <span className="lab-location-scope">
                      {[lab.city, lab.state].filter(Boolean).join(', ')}
                      {lab.lab_type ? ` • ${lab.lab_type}` : ''}
                    </span>
                  </div>
                </div>
              ))}
              {filteredLabs.length === 0 && (
                <div className="lab-slogan-note">
                  <span>No laboratories match "{searchCity}" - try a different city or state.</span>
                </div>
              )}
            </div>
          )}

          {/* Slogan Note */}
          <div className="lab-slogan-note">
            <span>Trusted labs for a safer India. ⤴</span>
          </div>
        </div>
      </div>
    </section>
  );
}
