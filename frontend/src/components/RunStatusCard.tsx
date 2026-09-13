import React from 'react';
import { RunStatusResponse } from '../api/types';
import { MetricCard } from './MetricCard';

interface RunStatusCardProps {
  run: RunStatusResponse | null;
  pollingError: string | null;
  onViewLeads?: () => void;
}

export const RunStatusCard: React.FC<RunStatusCardProps> = ({ run, pollingError, onViewLeads }) => {
  if (!run) {
    return (
      <div className="card empty-card">
        <div className="empty-state">
          <div className="empty-icon">⚡</div>
          <h3>No Active Run</h3>
          <p>
            Configure your target qualified lead goal above and click <strong>Start Agent Run</strong> to initiate autonomous discovery and deterministic qualification.
          </p>
        </div>
      </div>
    );
  }

  const isTerminal = [
    'COMPLETED',
    'EXHAUSTED',
    'FAILED',
  ].includes(run.status);

  const getBadgeClass = (status: string) => {
    switch (status) {
      case 'COMPLETED':
      case 'QUALIFIED':
        return 'badge-success';
      case 'DISCOVERING':
      case 'RESEARCHING':
      case 'VALIDATING':
      case 'CONTACT_RESEARCH':
      case 'EMAIL_VERIFICATION':
      case 'ITERATING':
        return 'badge-active';
      case 'EXHAUSTED':
        return 'badge-warning';
      case 'FAILED':
      case 'REJECTED':
        return 'badge-danger';
      default:
        return 'badge-neutral';
    }
  };

  return (
    <div className="card run-card">
      <div className="run-card-header">
        <div>
          <div className="run-title-row">
            <h2 className="card-title">Run Telemetry</h2>
            <span className={`badge ${getBadgeClass(run.status)}`}>
              {!isTerminal && <span className="dot pulse">●</span>}
              {run.status}
            </span>
          </div>
          <span className="run-id-tag">Run ID: <code>{run.run_id}</code></span>
        </div>

        <div style={{ display: 'flex', gap: '12px', alignItems: 'center' }}>
          {onViewLeads && run.qualified_leads_count > 0 && (
            <button className="btn btn-sm btn-primary" onClick={onViewLeads}>
              View Leads ({run.qualified_leads_count}) →
            </button>
          )}

          {run.stop_reason && (
            <div className="stop-reason-box">
              <span className="stop-reason-label">Stop Reason</span>
              <span className="stop-reason-value">{run.stop_reason}</span>
            </div>
          )}
        </div>
      </div>

      {pollingError && (
        <div className="alert alert-warning">
          ⚠️ Polling warning: {pollingError}. Telemetry will update on next interval.
        </div>
      )}

      <div className="metrics-grid">
        <MetricCard
          label="Target Leads Goal"
          value={run.target_qualified_leads}
          variant="accent"
        />
        <MetricCard
          label="Qualified Leads"
          value={run.qualified_leads_count}
          sublabel={`${((run.qualified_leads_count / Math.max(1, run.target_qualified_leads)) * 100).toFixed(0)}% reached`}
          variant="success"
        />
        <MetricCard
          label="Discovered"
          value={run.total_discovered}
        />
        <MetricCard
          label="Researched"
          value={run.total_researched}
        />
        <MetricCard
          label="Rejected"
          value={run.total_rejected}
          variant="warning"
        />
        <MetricCard
          label="Email Verification Attempts"
          value={run.total_email_attempts}
        />
        <MetricCard
          label="Iterations Completed"
          value={run.iterations_completed}
        />
      </div>

      {run.errors && run.errors.length > 0 && (
        <div className="log-section log-errors">
          <h4 className="log-title">Execution Errors ({run.errors.length})</h4>
          <ul className="log-list">
            {run.errors.map((err, idx) => (
              <li key={idx}>{err}</li>
            ))}
          </ul>
        </div>
      )}

      {run.warnings && run.warnings.length > 0 && (
        <div className="log-section log-warnings">
          <h4 className="log-title">Warnings ({run.warnings.length})</h4>
          <ul className="log-list">
            {run.warnings.map((warn, idx) => (
              <li key={idx}>{warn}</li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
};
