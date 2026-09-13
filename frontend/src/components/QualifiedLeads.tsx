import React, { useEffect, useMemo, useState } from 'react';
import { apiClient } from '../api/client';
import { LeadSummary } from '../api/types';

interface QualifiedLeadsProps {
  selectedRunId?: string | null;
  onClearRunFilter?: () => void;
  onSelectLead: (leadId: string) => void;
}

export const QualifiedLeads: React.FC<QualifiedLeadsProps> = ({
  selectedRunId,
  onClearRunFilter,
  onSelectLead,
}) => {
  const [leads, setLeads] = useState<LeadSummary[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  const [searchTerm, setSearchTerm] = useState<string>('');
  const [industryFilter, setIndustryFilter] = useState<string>('ALL');

  const fetchLeads = async () => {
    setLoading(true);
    setError(null);
    try {
      let data: LeadSummary[] = [];
      if (selectedRunId) {
        data = await apiClient.getRunLeads(selectedRunId);
      } else {
        data = await apiClient.getLeads();
      }
      setLeads(data);
    } catch (err: any) {
      setError(err.message || 'Failed to load qualified leads.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchLeads();
  }, [selectedRunId]);

  // Available industry sectors for filtering
  const availableIndustries = useMemo(() => {
    const set = new Set<string>();
    leads.forEach((l) => {
      if (l.industry_sector) {
        set.add(l.industry_sector);
      }
    });
    return Array.from(set).sort();
  }, [leads]);

  // Client-side search and filtering
  const filteredLeads = useMemo(() => {
    return leads.filter((l) => {
      // Industry filter
      if (industryFilter !== 'ALL' && l.industry_sector !== industryFilter) {
        return false;
      }
      // Search filter
      if (!searchTerm.trim()) return true;
      const term = searchTerm.toLowerCase();
      return (
        l.company_name.toLowerCase().includes(term) ||
        l.domain.toLowerCase().includes(term) ||
        (l.industry_sector && l.industry_sector.toLowerCase().includes(term)) ||
        (l.executive_name && l.executive_name.toLowerCase().includes(term)) ||
        (l.verified_executive_email && l.verified_executive_email.toLowerCase().includes(term))
      );
    });
  }, [leads, searchTerm, industryFilter]);

  return (
    <div className="leads-page">
      <div className="page-header">
        <div>
          <h2 className="page-title">
            {selectedRunId ? `Qualified Leads for Run: ${selectedRunId}` : 'All Qualified Leads'}
          </h2>
          <p className="page-subtitle">
            Deduplicated, deterministically qualified enterprise SaaS candidates with verified contacts.
          </p>
        </div>

        {selectedRunId && onClearRunFilter && (
          <button className="btn btn-secondary" onClick={onClearRunFilter}>
            ✕ Clear Run Filter
          </button>
        )}
      </div>

      {/* Filter and Search Toolbar */}
      <div className="card toolbar-card">
        <div className="toolbar-row">
          <div className="search-box">
            <span className="search-icon">🔍</span>
            <input
              type="text"
              placeholder="Search company, domain, executive, or email..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="form-input search-input"
            />
            {searchTerm && (
              <button className="btn-clear" onClick={() => setSearchTerm('')}>
                ✕
              </button>
            )}
          </div>

          <div className="filter-box">
            <label htmlFor="industryFilter" className="filter-label">Industry:</label>
            <select
              id="industryFilter"
              value={industryFilter}
              onChange={(e) => setIndustryFilter(e.target.value)}
              className="form-select"
            >
              <option value="ALL">All Sectors ({leads.length})</option>
              {availableIndustries.map((ind) => (
                <option key={ind} value={ind}>
                  {ind}
                </option>
              ))}
            </select>
          </div>
        </div>
      </div>

      {/* Main Content Area */}
      {loading && (
        <div className="card loading-card">
          <span className="spinner"></span> Loading qualified leads...
        </div>
      )}

      {!loading && error && (
        <div className="card error-card">
          <h3>Error Loading Leads</h3>
          <p>{error}</p>
          <button className="btn btn-primary" onClick={fetchLeads}>
            Retry Request
          </button>
        </div>
      )}

      {!loading && !error && filteredLeads.length === 0 && (
        <div className="card empty-card">
          <div className="empty-state">
            <div className="empty-icon">📂</div>
            <h3>{leads.length === 0 ? 'No Qualified Leads Yet' : 'No Matching Leads Found'}</h3>
            <p>
              {leads.length === 0
                ? 'Start an autonomous discovery run on the Dashboard to find candidates matching TVB criteria.'
                : 'Try adjusting your search query or industry filter.'}
            </p>
          </div>
        </div>
      )}

      {!loading && !error && filteredLeads.length > 0 && (
        <div className="card table-card">
          <div className="table-header-summary">
            Showing {filteredLeads.length} of {leads.length} leads
          </div>

          <div className="table-responsive">
            <table className="leads-table">
              <thead>
                <tr>
                  <th>Company Name</th>
                  <th>Domain</th>
                  <th>Industry / Sector</th>
                  <th>Executive Contact</th>
                  <th>Verified Email</th>
                  <th>Status</th>
                  <th>Action</th>
                </tr>
              </thead>
              <tbody>
                {filteredLeads.map((lead) => (
                  <tr key={lead.id} className="lead-row" onClick={() => onSelectLead(lead.id)}>
                    <td className="company-cell">
                      <span className="company-name">{lead.company_name}</span>
                      {lead.description && <span className="company-desc">{lead.description}</span>}
                    </td>
                    <td>
                      <code className="domain-code">{lead.domain}</code>
                    </td>
                    <td>{lead.industry_sector || 'B2B Software'}</td>
                    <td>
                      {lead.executive_name ? (
                        <div className="exec-info">
                          <span className="exec-name">{lead.executive_name}</span>
                          <span className="exec-role">{lead.executive_role || 'CEO / Founder'}</span>
                        </div>
                      ) : (
                        <span className="text-muted">—</span>
                      )}
                    </td>
                    <td>
                      {lead.verified_executive_email ? (
                        <span className="email-verified-tag">
                          ✓ {lead.verified_executive_email}
                        </span>
                      ) : (
                        <span className="text-muted">Unverified</span>
                      )}
                    </td>
                    <td>
                      <span className={`badge ${lead.qualification_status === 'QUALIFIED' ? 'badge-success' : 'badge-warning'}`}>
                        {lead.qualification_status}
                      </span>
                    </td>
                    <td>
                      <button
                        className="btn btn-sm btn-primary"
                        onClick={(e) => {
                          e.stopPropagation();
                          onSelectLead(lead.id);
                        }}
                      >
                        View Audit →
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
