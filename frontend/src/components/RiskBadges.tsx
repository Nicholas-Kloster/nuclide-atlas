import type { RiskFinding } from '../lib/api';

interface Props {
  findings: RiskFinding[];
}

const COLOR: Record<RiskFinding['severity'], string> = {
  info: '#5a8db8',
  warn: '#d0a035',
  high: '#d04d6a',
};

export function RiskBadges({ findings }: Props) {
  if (!findings.length) return null;
  return (
    <div className="risk-badges">
      {findings.map((f, i) => (
        <span
          key={i}
          className="risk-badge"
          style={{ background: COLOR[f.severity] }}
          title={`${f.ruleId} — ${f.message}`}
        >
          {f.severity === 'high' ? '!' : f.severity === 'warn' ? '~' : 'i'}{' '}
          {f.message}
        </span>
      ))}
    </div>
  );
}
