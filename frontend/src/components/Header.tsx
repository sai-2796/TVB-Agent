import React from 'react';
import { HealthResponse } from '../api/types';

interface HeaderProps {
  health: HealthResponse | null;
  healthLoading: boolean;
  healthError: string | null;
}

export const Header: React.FC<HeaderProps> = ({ health, healthLoading, healthError }) => {
  return (
    <header className="header-container">
      <div className="header-brand">
        <div className="header-logo-badge">TVB</div>
        <div>
          <h1 className="header-title">Venture Intelligence</h1>
          <p className="header-subtitle">Autonomous Venture Discovery & Lead Qualification System</p>
        </div>
      </div>

      <div className="header-status">
        {healthLoading && (
          <div className="status-indicator status-loading">
            <span className="dot pulse">●</span> Checking Backend...
          </div>
        )}
        {!healthLoading && health && (
          <div className="status-indicator status-connected">
            <span className="dot">●</span> Backend Connected
            <span className="version-tag">v{health.version}</span>
          </div>
        )}
        {!healthLoading && healthError && (
          <div className="status-indicator status-error" title={healthError}>
            <span className="dot">●</span> Backend Unavailable
          </div>
        )}
      </div>
    </header>
  );
};
