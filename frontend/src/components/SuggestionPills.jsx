import React from 'react';

const SUGGESTIONS = [
  'Certification Process',
  'Show Documents',
  'Related Standards'
];

export default function SuggestionPills({ onSelectSuggestion }) {
  return (
    <div className="suggestions-wrapper" aria-label="Suggested Queries">
      {SUGGESTIONS.map((text, idx) => (
        <button
          key={idx}
          type="button"
          className="suggestion-pill"
          onClick={() => onSelectSuggestion(text)}
        >
          {text}
        </button>
      ))}
    </div>
  );
}
