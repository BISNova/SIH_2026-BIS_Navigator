import React from 'react';

export default function Footer({ onOpenChatbot }) {
  return (
    <footer className="landing-footer">
      <div className="footer-container">
        {/* Brand Col */}
        <div className="footer-brand-col">
          <div className="footer-logo-row">
            <img src="/assets/bisnova_logo.png" alt="BISNova" className="footer-logo" />
          </div>
          <p className="footer-tagline">
            Your guide to Indian Standards. Smarter navigation through BIS compliance.
          </p>
        </div>

        {/* Explore Links */}
        <div className="footer-links-col">
          <h4 className="footer-col-title">Explore</h4>
          <ul className="footer-nav-list">
            <li><a href="#hero">Home</a></li>
            <li><a href="#standards-labs">Standards</a></li>
            <li><a href="#how-bisnova-helps">FAQs</a></li>
            <li><a href="#" onClick={(e) => { e.preventDefault(); onOpenChatbot(); }}>Dashboard</a></li>
          </ul>
        </div>

        {/* About Links */}
        <div className="footer-links-col">
          <h4 className="footer-col-title">About</h4>
          <ul className="footer-nav-list">
            <li><a href="#about">About</a></li>
            <li><a href="#contact">Contact</a></li>
            <li><a href="#privacy">Privacy Policy</a></li>
            <li><a href="#terms">Terms & Disclaimer</a></li>
          </ul>
        </div>

        {/* Official Resources */}
        <div className="footer-links-col">
          <h4 className="footer-col-title">Official</h4>
          <ul className="footer-nav-list">
            <li>
              <a href="https://www.bis.gov.in" target="_blank" rel="noopener noreferrer">
                BIS Website
              </a>
            </li>
            <li>
              <a href="https://www.services.bis.gov.in" target="_blank" rel="noopener noreferrer">
                Relevant BIS resources
              </a>
            </li>
          </ul>
        </div>
      </div>

      <div className="footer-bottom-bar">
        <div className="footer-bottom-inner">
          <div className="footer-social-icons">
            <a href="https://linkedin.com" target="_blank" rel="noopener noreferrer" aria-label="LinkedIn">in</a>
            <a href="https://youtube.com" target="_blank" rel="noopener noreferrer" aria-label="YouTube">▶</a>
            <a href="https://x.com" target="_blank" rel="noopener noreferrer" aria-label="X">𝕏</a>
          </div>
          <p className="sih-credit-text">
            Built for SIH26107 • Not an official BIS website
          </p>
        </div>
      </div>
    </footer>
  );
}
