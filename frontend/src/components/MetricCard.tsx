import React from 'react';

interface MetricCardProps {
  label: string;
  value: number | string;
  sublabel?: string;
  variant?: 'default' | 'success' | 'warning' | 'error' | 'accent';
}

export const MetricCard: React.FC<MetricCardProps> = ({
  label,
  value,
  sublabel,
  variant = 'default',
}) => {
  return (
    <div className={`metric-card metric-${variant}`}>
      <span className="metric-label">{label}</span>
      <span className="metric-value">{value}</span>
      {sublabel && <span className="metric-sublabel">{sublabel}</span>}
    </div>
  );
};
