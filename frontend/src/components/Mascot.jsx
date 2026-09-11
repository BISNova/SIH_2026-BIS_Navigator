import React from 'react';

export default function Mascot({ mascotState = 'idle', onMascotClick, isCollapsed = false }) {
  // mascotState: 'idle' | 'reading' | 'thinking' | 'smiling'
  const stateClass = `mascot-${mascotState}`;
  const collapsedClass = isCollapsed ? 'collapsed-mascot' : '';

  return (
    <div className={`sidebar-mascot-container ${collapsedClass}`}>
      {/* Full Body Cartoon Mascot - Gentle Micro-Animations */}
      <img
        src="/assets/mascot.png"
        alt="BISNova Mascot"
        className={`sidebar-mascot-img ${stateClass}`}
        title="BISNova Mascot"
        onClick={onMascotClick}
      />
    </div>
  );
}
