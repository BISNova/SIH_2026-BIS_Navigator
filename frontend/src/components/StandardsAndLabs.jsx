import React, { useState } from 'react';

export default function StandardsAndLabs({ onOpenChatbotWithQuery }) {
  const [searchCity, setSearchCity] = useState('');

  const laboratories = [
    {
      name: 'BIS Central Laboratory',
      location: 'New Delhi, Delhi',
      scope: 'Metals, Mechanical, General Engineering',
      distance: '2.3 km'
    },
    {
      name: 'NABL Accredited Lab',
      location: 'Noida, UP',
      scope: 'Chemical, Polymer, Packaging',
      distance: '12.6 km'
    },
    {
      name: 'BIS Recognized Lab',
      location: 'Gurugram, Haryana',
      scope: 'Electrical, Electronics, IT Equipment',
      distance: '28.4 km'
    }
  ];

  const filteredLabs = laboratories.filter(lab =>
    lab.location.toLowerCase().includes(searchCity.toLowerCase()) ||
    lab.name.toLowerCase().includes(searchCity.toLowerCase()) ||
    lab.scope.toLowerCase().includes(searchCity.toLowerCase())
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
            onClick={() => onOpenChatbotWithQuery('Search all Indian Standards by product category')}
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
              placeholder="Enter your city or allow location access..."
              value={searchCity}
              onChange={(e) => setSearchCity(e.target.value)}
            />
            <button
              type="button"
              className="lab-search-submit-btn"
              onClick={() => onOpenChatbotWithQuery(`Find testing laboratories in ${searchCity || 'Delhi NCR'}`)}
              title="Search Laboratories"
            >
              🔍
            </button>
          </div>

          {/* Laboratory List */}
          <div className="lab-results-header">
            <span className="lab-results-title">Recognized laboratories near you</span>
            <button
              type="button"
              className="view-all-labs-btn"
              onClick={() => onOpenChatbotWithQuery('List all BIS recognized testing laboratories in India')}
            >
              View all
            </button>
          </div>

          <div className="lab-items-list">
            {filteredLabs.map((lab, idx) => (
              <div
                key={idx}
                className="lab-item-row"
                onClick={() => onOpenChatbotWithQuery(`Give details and contact for ${lab.name} in ${lab.location}`)}
              >
                <div className="lab-item-icon">📍</div>
                <div className="lab-item-info">
                  <strong>{lab.name}</strong>
                  <span className="lab-location-scope">{lab.location} • {lab.scope}</span>
                </div>
                <span className="lab-distance-badge">{lab.distance}</span>
              </div>
            ))}
          </div>

          {/* Slogan Note */}
          <div className="lab-slogan-note">
            <span>Trusted labs for a safer India. ⤴</span>
          </div>
        </div>
      </div>
    </section>
  );
}
