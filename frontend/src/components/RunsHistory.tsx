import React, { useEffect, useState } from 'react';
import { apiClient } from '../api/client';
import { RunStatusResponse } from '../api/types';

interface RunsHistoryProps {
  onSelectRunLeads: (runId: string) => void;
}

export const RunsHistory: React.FC<RunsHistoryProps> = ({ onSelectRunLeads }) => {
  const [runs, setRuns] = useState<RunStatusResponse[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  const fetchRuns = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await apiClient.getRuns();
      setRuns(data);
    } catch (err: any) {
      setError(err.message || 'Failed to load run history.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchRuns();
  }, []);

  const getBadgeClass = (status: string) => {
    switch (status) {
      case 'COMPLETED':
        return 'badge-success';
      case 'EXHAUSTED':
        return 'badge-warning';
      case 'FAILED':
        return 'badge-danger';
      default:
        return 'badge-active';
    }
  };

  return (
    <div className="runs-history-page">
      <div className="page-header">
        <div>
          <h2 className="page-title">Autonomous Execution History</h2>
          <p className="page-subtitle">
            Audit history of all previous and active venture discovery runs.
          </p>
        </div>
        <button className="btn btn-secondary" onClick={fetchRuns}>
          🔄 Refresh Runs
        </button>
      </div>

      {loading && (
        <div className="card loading-card">
          <span className="spinner"></span> Loading run history...
        </div>
      )}

      {!loading && error && (
        <div className="card error-card">
          <h3>Error Loading Runs</h3>
          <p>{error}</p>
          <button className="btn btn-primary" onClick={fetchRuns}>
            Retry Request
          </button>
        </div>
      )}

      {!loading && !error && runs.length === 0 && (
        <div className="card empty-card">
          <div className="empty-state">
            <div className="empty-icon">📜</div>
            <h3>No Execution History</h3>
            <p>Start a new autonomous run on the Dashboard to view metrics and history here.</p>
          </div>
        </div>
      )}

      {!loading && !error && runs.length > 0 && (
        <div className="card table-card">
          <div className="table-responsive">
            <table className="runs-table">
              <thead>
                <tr>
                  <th>Run ID</th>
                  <th>Status</th>
                  <th>Stop Reason</th>
                  <th>Goal Target</th>
                  <th>Qualified Leads</th>
                  <th>Discovered / Researched</th>
                  <th>Started At</th>
                  <th>Action</th>
                </tr>
              </thead>
              <tbody>
                {runs.map((r) => (
                  <tr key={r.run_id} className="run-row">
                    <td>
                      <code>{r.run_id}</code>
                    </td>
                    <td>
                      <span className={`badge ${getBadgeClass(r.status)}`}>
                        {r.status}
                      </span>
                    </td>
                    <td>
                      <span className="stop-reason-text">{r.stop_reason || 'IN_PROGRESS'}</span>
                    </td>
                    <td>{r.target_qualified_leads}</td>
                    <td>
                      <strong style={{ color: '#34d399' }}>{r.qualified_leads_count}</strong>
                    </td>
                    <td>
                      {r.total_discovered} disc / {r.total_researched} res
                    </td>
                    <td>{new Date(r.started_at).toLocaleString()}</td>
                    <td>
                      <button
                        className="btn btn-sm btn-primary"
                        onClick={() => onSelectRunLeads(r.run_id)}
                      >
                        View Qualified Leads →
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
};
