import React from 'react';

export type NavigationTab = 'dashboard' | 'runs' | 'leads';

interface NavbarProps {
  currentTab: NavigationTab;
  onTabChange: (tab: NavigationTab) => void;
  qualifiedCount?: number;
}

export const Navbar: React.FC<NavbarProps> = ({ currentTab, onTabChange, qualifiedCount }) => {
  return (
    <nav className="navbar">
      <button
        className={`nav-link ${currentTab === 'dashboard' ? 'active' : ''}`}
        onClick={() => onTabChange('dashboard')}
      >
        <span className="nav-icon">📊</span> Dashboard
      </button>

      <button
        className={`nav-link ${currentTab === 'runs' ? 'active' : ''}`}
        onClick={() => onTabChange('runs')}
      >
        <span className="nav-icon">🔄</span> Runs History
      </button>

      <button
        className={`nav-link ${currentTab === 'leads' ? 'active' : ''}`}
        onClick={() => onTabChange('leads')}
      >
        <span className="nav-icon">🎯</span> Qualified Leads
        {typeof qualifiedCount === 'number' && qualifiedCount > 0 && (
          <span className="nav-count-badge">{qualifiedCount}</span>
        )}
      </button>
    </nav>
  );
};
