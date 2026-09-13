import React, { useState } from 'react';

interface RunConfigurationProps {
  onStartRun: (targetLeads: number) => Promise<void>;
  isStarting: boolean;
  disabled: boolean;
}

export const RunConfiguration: React.FC<RunConfigurationProps> = ({
  onStartRun,
  isStarting,
  disabled,
}) => {
  const [targetLeadsInput, setTargetLeadsInput] = useState<string>('15');
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setErrorMsg(null);

    const parsed = parseInt(targetLeadsInput.trim(), 10);
    if (isNaN(parsed) || parsed < 1 || parsed > 100) {
      setErrorMsg('Target qualified leads must be an integer between 1 and 100.');
      return;
    }

    try {
      await onStartRun(parsed);
    } catch (err: any) {
      setErrorMsg(err.message || 'Failed to trigger agent run.');
    }
  };

  return (
    <div className="card config-card">
      <div className="card-header">
        <h2 className="card-title">Autonomous Agent Controller</h2>
        <p className="card-description">
          Configure resource constraints and launch the autonomous lead discovery pipeline.
        </p>
      </div>

      <form onSubmit={handleSubmit} className="config-form">
        <div className="form-group">
          <label htmlFor="targetLeadsInput" className="form-label">
            Target Qualified Leads
          </label>
          <div className="input-row">
            <input
              id="targetLeadsInput"
              type="number"
              min={1}
              max={100}
              step={1}
              value={targetLeadsInput}
              onChange={(e) => {
                setTargetLeadsInput(e.target.value);
                setErrorMsg(null);
              }}
              disabled={isStarting || disabled}
              className={`form-input ${errorMsg ? 'input-error' : ''}`}
            />
            <button
              type="submit"
              disabled={isStarting || disabled}
              className="btn btn-primary"
            >
              {isStarting ? (
                <>
                  <span className="spinner"></span> Starting Agent...
                </>
              ) : (
                'Start Agent Run'
              )}
            </button>
          </div>
          {errorMsg && <p className="error-text">{errorMsg}</p>}
          <span className="help-text">
            Valid range: 1 – 100 leads. Execution runs asynchronously in the background.
          </span>
        </div>
      </form>
    </div>
  );
};
