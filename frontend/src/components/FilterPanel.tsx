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
}

export function FilterPanel({ visible, onToggle, onClearHighlight, hasHighlight }: Props) {
  return (
    <nav className="atlas-filters">
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
    </nav>
  );
}
