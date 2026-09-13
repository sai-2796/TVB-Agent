import React, { useCallback, useEffect, useRef, useState } from 'react';
import { apiClient } from './api/client';
import { HealthResponse, RunStatusResponse } from './api/types';
import { Header } from './components/Header';
import { Navbar, NavigationTab } from './components/Navbar';
import { RunConfiguration } from './components/RunConfiguration';
import { RunStatusCard } from './components/RunStatusCard';
import { QualifiedLeads } from './components/QualifiedLeads';
import { LeadDetails } from './components/LeadDetails';
import { RunsHistory } from './components/RunsHistory';

const POLLING_INTERVAL_MS = 2500;
const TERMINAL_STATES: Set<string> = new Set(['COMPLETED', 'EXHAUSTED', 'FAILED']);

export const App: React.FC = () => {
  const [currentTab, setCurrentTab] = useState<NavigationTab>('dashboard');
  const [selectedLeadId, setSelectedLeadId] = useState<string | null>(null);
  const [runFilterId, setRunFilterId] = useState<string | null>(null);

  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [healthLoading, setHealthLoading] = useState<boolean>(true);
  const [healthError, setHealthError] = useState<string | null>(null);

  const [activeRunId, setActiveRunId] = useState<string | null>(null);
  const [activeRun, setActiveRun] = useState<RunStatusResponse | null>(null);
  const [isStartingRun, setIsStartingRun] = useState<boolean>(false);
  const [pollingError, setPollingError] = useState<string | null>(null);
  const [globalLeadsCount, setGlobalLeadsCount] = useState<number>(0);

  const pollTimerRef = useRef<number | null>(null);

  // Initial Health & Leads Count Check
  const checkHealth = useCallback(async () => {
    try {
      setHealthLoading(true);
      const res = await apiClient.getHealth();
      setHealth(res);
      setHealthError(null);
    } catch (err: any) {
      setHealthError(err.message || 'Unable to reach backend API.');
      setHealth(null);
    } finally {
      setHealthLoading(false);
    }
  }, []);

  const refreshLeadsCount = useCallback(async () => {
    try {
      const leads = await apiClient.getLeads();
      setGlobalLeadsCount(leads.length);
    } catch {
      // Ignore background refresh errors
    }
  }, []);

  useEffect(() => {
    checkHealth();
    refreshLeadsCount();
  }, [checkHealth, refreshLeadsCount]);

  // Polling management
  const stopPolling = useCallback(() => {
    if (pollTimerRef.current !== null) {
      window.clearInterval(pollTimerRef.current);
      pollTimerRef.current = null;
    }
  }, []);

  const fetchRunStatus = useCallback(async (runId: string) => {
    try {
      const data = await apiClient.getRun(runId);
      setActiveRun(data);
      setPollingError(null);
      refreshLeadsCount();

      if (TERMINAL_STATES.has(data.status)) {
        stopPolling();
      }
    } catch (err: any) {
      setPollingError(err.message || 'Error fetching run telemetry.');
    }
  }, [stopPolling, refreshLeadsCount]);

  useEffect(() => {
    if (!activeRunId) {
      stopPolling();
      return;
    }

    fetchRunStatus(activeRunId);

    stopPolling();
    pollTimerRef.current = window.setInterval(() => {
      fetchRunStatus(activeRunId);
    }, POLLING_INTERVAL_MS);

    return () => {
      stopPolling();
    };
  }, [activeRunId, fetchRunStatus, stopPolling]);

  // Actions
  const handleStartRun = async (targetLeads: number) => {
    setIsStartingRun(true);
    setPollingError(null);
    try {
      const res = await apiClient.createRun({ target_qualified_leads: targetLeads });
      setActiveRunId(res.run_id);
      setActiveRun({
        run_id: res.run_id,
        status: res.status,
        target_qualified_leads: res.target_qualified_leads,
        qualified_leads_count: 0,
        total_discovered: 0,
        total_researched: 0,
        total_rejected: 0,
        total_email_attempts: 0,
        iterations_completed: 0,
        errors: [],
        warnings: [],
        started_at: res.started_at,
      });
    } finally {
      setIsStartingRun(false);
    }
  };

  const handleNavigateToRunLeads = (runId: string) => {
    setRunFilterId(runId);
    setSelectedLeadId(null);
    setCurrentTab('leads');
  };

  const handleSelectLead = (leadId: string) => {
    setSelectedLeadId(leadId);
  };

  return (
    <div className="app-container">
      <Header
        health={health}
        healthLoading={healthLoading}
        healthError={healthError}
      />

      <Navbar
        currentTab={currentTab}
        onTabChange={(tab) => {
          setCurrentTab(tab);
          setSelectedLeadId(null);
        }}
        qualifiedCount={globalLeadsCount}
      />

      <main className="dashboard-main">
        {selectedLeadId ? (
          <LeadDetails
            leadId={selectedLeadId}
            onBack={() => setSelectedLeadId(null)}
          />
        ) : (
          <>
            {currentTab === 'dashboard' && (
              <>
                <RunConfiguration
                  onStartRun={handleStartRun}
                  isStarting={isStartingRun}
                  disabled={healthLoading || !!healthError}
                />

                <RunStatusCard
                  run={activeRun}
                  pollingError={pollingError}
                  onViewLeads={() => {
                    if (activeRun) {
                      handleNavigateToRunLeads(activeRun.run_id);
                    }
                  }}
                />
              </>
            )}

            {currentTab === 'runs' && (
              <RunsHistory
                onSelectRunLeads={handleNavigateToRunLeads}
              />
            )}

            {currentTab === 'leads' && (
              <QualifiedLeads
                selectedRunId={runFilterId}
                onClearRunFilter={() => setRunFilterId(null)}
                onSelectLead={handleSelectLead}
              />
            )}
          </>
        )}
      </main>
    </div>
  );
};

export default App;
