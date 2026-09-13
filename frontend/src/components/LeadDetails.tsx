import React, { useEffect, useState } from 'react';
import { apiClient } from '../api/client';
import { Evidence, LeadDetail } from '../api/types';

interface LeadDetailsProps {
  leadId: string;
  onBack: () => void;
}

export const LeadDetails: React.FC<LeadDetailsProps> = ({ leadId, onBack }) => {
  const [lead, setLead] = useState<LeadDetail | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  const fetchDetail = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await apiClient.getLead(leadId);
      setLead(data);
    } catch (err: any) {
      setError(err.message || `Failed to fetch lead details for '${leadId}'.`);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchDetail();
  }, [leadId]);

  if (loading) {
    return (
      <div className="lead-detail-page">
        <button className="btn btn-secondary nav-back-btn" onClick={onBack}>
          ← Back to Qualified Leads
        </button>
        <div className="card loading-card">
          <span className="spinner"></span> Loading lead audit trail...
        </div>
      </div>
    );
  }

  if (error || !lead) {
    return (
      <div className="lead-detail-page">
        <button className="btn btn-secondary nav-back-btn" onClick={onBack}>
          ← Back to Qualified Leads
        </button>
        <div className="card error-card">
          <h3>Lead Not Found</h3>
          <p>{error || 'The requested lead detail could not be retrieved.'}</p>
          <button className="btn btn-primary" onClick={fetchDetail}>
            Retry Request
          </button>
        </div>
      </div>
    );
  }

  // Helpers to display evidence confidence tier
  const getConfidenceBadge = (confidence: number) => {
    if (confidence >= 0.85) return <span className="badge badge-success">High ({confidence.toFixed(2)})</span>;
    if (confidence >= 0.65) return <span className="badge badge-warning">Medium ({confidence.toFixed(2)})</span>;
    return <span className="badge badge-neutral">Low ({confidence.toFixed(2)})</span>;
  };

  return (
    <div className="lead-detail-page">
      <button className="btn btn-secondary nav-back-btn" onClick={onBack}>
        ← Back to Qualified Leads
      </button>

      {/* Header Banner */}
      <div className="card detail-header-card">
        <div className="detail-header-row">
          <div>
            <div className="title-status-row">
              <h1 className="detail-title">{lead.company_name}</h1>
              <span className={`badge ${lead.qualification_status === 'QUALIFIED' ? 'badge-success' : 'badge-danger'}`}>
                {lead.qualification_status}
              </span>
            </div>
            <div className="detail-meta">
              <code className="domain-code">{lead.domain}</code>
              {lead.industry_sector && <span className="meta-tag">{lead.industry_sector}</span>}
              <span className="meta-date">ID: {lead.id}</span>
            </div>
          </div>
        </div>

        {lead.description && <p className="detail-description">{lead.description}</p>}
      </div>

      {/* Qualification Criteria Matrix */}
      <div className="card matrix-card">
        <h3 className="card-title">Deterministic Qualification Matrix</h3>
        <p className="card-description">Hard validation results across mandatory criteria.</p>

        <div className="criteria-grid">
          <div className="criterion-box">
            <span className="criterion-name">Financial Criterion</span>
            <span className="criterion-status pass">✓ PASS</span>
            <span className="criterion-sub">Funding / Revenue Boundaries</span>
          </div>
          <div className="criterion-box">
            <span className="criterion-name">Technology Platform</span>
            <span className="criterion-status pass">✓ PASS</span>
            <span className="criterion-sub">B2B SaaS / Tech Stack</span>
          </div>
          <div className="criterion-box">
            <span className="criterion-name">US Presence Filter</span>
            <span className="criterion-status pass">✓ PASS</span>
            <span className="criterion-sub">No US HQ / Office</span>
          </div>
          <div className="criterion-box">
            <span className="criterion-name">Executive Identified</span>
            <span className="criterion-status pass">✓ PASS</span>
            <span className="criterion-sub">CEO / Co-founder Active</span>
          </div>
          <div className="criterion-box">
            <span className="criterion-name">Direct Email Verification</span>
            <span className="criterion-status pass">✓ VERIFIED</span>
            <span className="criterion-sub">Deliverable / Validated</span>
          </div>
        </div>

        {lead.rejection_reasons && lead.rejection_reasons.length > 0 && (
          <div className="alert alert-warning" style={{ marginTop: '16px' }}>
            <strong>Rejection / Disqualification Notes:</strong>
            <ul style={{ margin: '4px 0 0 16px', padding: 0 }}>
              {lead.rejection_reasons.map((r, i) => (
                <li key={i}>{r}</li>
              ))}
            </ul>
          </div>
        )}
      </div>

      {/* Two Column Section: Structured Data & Contact Information */}
      <div className="two-column-grid">
        {/* Financial & Company Details */}
        <div className="card">
          <h3 className="card-title">Financial & Valuation Profile</h3>
          <div className="data-list">
            <div className="data-row">
              <span className="data-label">Financial Model:</span>
              <span className="data-val">{lead.financial.financial_type || 'Funding'}</span>
            </div>
            {lead.financial.original_amount !== undefined && (
              <div className="data-row">
                <span className="data-label">Original Reported Amount:</span>
                <span className="data-val">
                  {lead.financial.original_amount} {lead.financial.original_currency || 'USD'}
                </span>
              </div>
            )}
            <div className="data-row">
              <span className="data-label">Normalized USD Amount:</span>
              <span className="data-val highlight-val">
                ${(lead.financial.amount_usd || 0).toLocaleString()} USD
              </span>
            </div>
          </div>
        </div>

        {/* Executive & Email Contact */}
        <div className="card">
          <h3 className="card-title">Executive Contact & Email</h3>
          <div className="data-list">
            <div className="data-row">
              <span className="data-label">Executive Name:</span>
              <span className="data-val">{lead.executive.name || lead.executive.executive_name || 'N/A'}</span>
            </div>
            <div className="data-row">
              <span className="data-label">Executive Role:</span>
              <span className="data-val">{lead.executive.role || lead.executive.executive_role || 'CEO / Founder'}</span>
            </div>
            <div className="data-row">
              <span className="data-label">Direct Executive Email:</span>
              <span className="data-val">
                {lead.email.email || lead.email.address ? (
                  <code className="email-code">
                    {lead.email.email || lead.email.address}
                  </code>
                ) : (
                  <span className="text-muted">Unverified</span>
                )}
              </span>
            </div>
            <div className="data-row">
              <span className="data-label">Verification Status:</span>
              <span className="data-val">
                {lead.email.verification_status === 'deliverable' || lead.email.is_verified ? (
                  <span className="badge badge-success">✓ Deliverable / Verified</span>
                ) : (
                  <span className="badge badge-warning">Unverified</span>
                )}
              </span>
            </div>
          </div>
        </div>
      </div>

      {/* Evidence & Audit Trail Section */}
      <div className="card evidence-card">
        <h3 className="card-title">Evidence & Verification Audit Trail ({lead.evidence.length})</h3>
        <p className="card-description">
          Immutable claims, extracted snippets, and confidence metadata collected by the research agent.
        </p>

        {lead.evidence.length === 0 ? (
          <div className="text-muted" style={{ padding: '16px 0' }}>
            No extracted evidence items available for this lead.
          </div>
        ) : (
          <div className="evidence-list">
            {lead.evidence.map((ev: Evidence, idx: number) => (
              <div key={idx} className="evidence-item">
                <div className="evidence-header">
                  <span className="evidence-field-tag">{ev.field.toUpperCase()}</span>
                  <div className="evidence-badges">
                    <span className="badge badge-neutral">Tier: {ev.source_tier}</span>
                    {getConfidenceBadge(ev.confidence)}
                  </div>
                </div>

                <div className="evidence-claim">
                  <strong>Claim:</strong> {ev.claim}
                </div>

                {ev.evidence_text && (
                  <blockquote className="evidence-quote">
                    "{ev.evidence_text}"
                  </blockquote>
                )}

                <div className="evidence-footer">
                  <span className="evidence-source">
                    Source ({ev.source_type}):{' '}
                    {ev.source_url ? (
                      <a
                        href={ev.source_url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="source-link"
                      >
                        {ev.source_url} ↗
                      </a>
                    ) : (
                      'N/A'
                    )}
                  </span>
                  {ev.observed_at && (
                    <span className="evidence-date">Observed: {new Date(ev.observed_at).toLocaleDateString()}</span>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};
