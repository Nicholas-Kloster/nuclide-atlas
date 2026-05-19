import type { ReactNode } from 'react';
import type { EntityType } from '../lib/types';

const LAYERS: { key: EntityType; label: string; color: string }[] = [
  { key: 'endpoint', label: 'Endpoints', color: 'var(--node-endpoint)' },
  { key: 'deployment', label: 'Deployments', color: 'var(--node-deployment)' },
  { key: 'model', label: 'Models', color: 'var(--node-model)' },
  { key: 'ragPipeline', label: 'RAG Pipelines', color: 'var(--node-rag)' },
  { key: 'vectorIndex', label: 'Vector Indexes', color: 'var(--node-vector)' },
  { key: 'tool', label: 'Tools', color: 'var(--node-tool)' },
  { key: 'agent', label: 'Agents', color: 'var(--node-agent)' },
  { key: 'safetyPolicy', label: 'Safety Policies', color: 'var(--node-safety)' },
];

interface Props {
  visible: Set<EntityType>;
  onToggle: (key: EntityType) => void;
  onClearHighlight: () => void;
  hasHighlight: boolean;
  search?: ReactNode;
  pulsedAt: number | null;
}

export function FilterPanel({
  visible,
  onToggle,
  onClearHighlight,
  hasHighlight,
  search,
  pulsedAt,
}: Props) {
  return (
    <nav className="atlas-filters">
      {search && <div className="filter-section">{search}</div>}

      <h3>Layers</h3>
      {LAYERS.map(({ key, label, color }) => (
        <label key={key}>
          <input
            type="checkbox"
            checked={visible.has(key)}
            onChange={() => onToggle(key)}
          />
          <span className="dot" style={{ background: color }} />
          {label}
        </label>
      ))}

      <h3 style={{ marginTop: 18 }}>Highlight</h3>
      {hasHighlight ? (
        <button className="action" onClick={onClearHighlight}>
          Clear agent path
        </button>
      ) : (
        <div style={{ fontSize: 11, color: 'var(--fg-mute)' }}>
          Click an Agent node, then "Highlight path" to trace everything it touches.
        </div>
      )}

      <h3 style={{ marginTop: 18 }}>Live status</h3>
      <div style={{ fontSize: 11, color: 'var(--fg-mute)' }}>
        {pulsedAt
          ? `last probe: ${new Date(pulsedAt).toLocaleTimeString()}`
          : 'click ○ Live in the header to start probing endpoints.'}
      </div>

      <div className="legend" style={{ marginTop: 14 }}>
        <h3>Legend</h3>
        <div className="legend-row"><span className="dot probe-ok" /> reachable</div>
        <div className="legend-row"><span className="dot probe-auth" /> auth required</div>
        <div className="legend-row"><span className="dot probe-err" /> unreachable</div>
        <div className="legend-row"><span className="dot risk-warn" /> finding (warn)</div>
        <div className="legend-row"><span className="dot risk-high" /> finding (high)</div>
      </div>
    </nav>
  );
}
