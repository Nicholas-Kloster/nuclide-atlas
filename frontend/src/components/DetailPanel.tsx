import { useEffect, useState } from 'react';
import { fetchMetrics } from '../lib/api';
import type { AnyEntity, EntityType, MetricsSnapshot } from '../lib/types';

const METRIC_TYPES: ReadonlySet<EntityType> = new Set([
  'model',
  'deployment',
  'endpoint',
]);

const KIND_LABEL: Record<AnyEntity['_type'], string> = {
  model: 'Model',
  deployment: 'Deployment',
  endpoint: 'Endpoint',
  ragPipeline: 'RAG Pipeline',
  vectorIndex: 'Vector Index',
  tool: 'Tool',
  agent: 'Agent',
  safetyPolicy: 'Safety Policy',
};

interface Props {
  entity: AnyEntity | null;
  isAgentHighlighted: boolean;
  onToggleHighlight: () => void;
}

export function DetailPanel({ entity, isAgentHighlighted, onToggleHighlight }: Props) {
  if (!entity) {
    return (
      <aside className="atlas-detail">
        <div className="atlas-empty">
          Click a node to inspect it.
          <br />
          <br />
          Click an Agent twice to highlight everything it touches.
        </div>
      </aside>
    );
  }

  return (
    <aside className="atlas-detail">
      <div className="kind">{KIND_LABEL[entity._type]}</div>
      <h2>{titleFor(entity)}</h2>
      <div>
        <span className="atlas-pill">id: {entity.id}</span>
      </div>

      {entity._type === 'agent' && (
        <p style={{ margin: '10px 0' }}>
          <button className="action" onClick={onToggleHighlight}>
            {isAgentHighlighted ? 'Clear path' : 'Highlight path'}
          </button>
        </p>
      )}

      {METRIC_TYPES.has(entity._type) && (
        <MetricsCard entityType={entity._type} entityId={entity.id} />
      )}

      <h3 style={{ fontSize: 12, color: 'var(--fg-mute)', marginTop: 16 }}>RAW</h3>
      <pre>{JSON.stringify(stripType(entity), null, 2)}</pre>
    </aside>
  );
}

function MetricsCard({ entityType, entityId }: { entityType: EntityType; entityId: string }) {
  const [m, setM] = useState<MetricsSnapshot | null>(null);
  const [err, setErr] = useState<string | null>(null);
  useEffect(() => {
    let live = true;
    setM(null);
    setErr(null);
    fetchMetrics(entityType, entityId)
      .then((res) => live && setM(res))
      .catch((e: Error) => live && setErr(e.message));
    return () => {
      live = false;
    };
  }, [entityType, entityId]);

  if (err) return <div className="metric-card">metrics unavailable: {err}</div>;
  if (!m) return <div className="metric-card">loading metrics…</div>;
  return (
    <div className="metric-card">
      <div className="metric-row">
        <span>Latency p50</span>
        <span>{m.latencyP50.toFixed(1)} ms</span>
      </div>
      <div className="metric-row">
        <span>Latency p95</span>
        <span>{m.latencyP95.toFixed(1)} ms</span>
      </div>
      {m.tokensPerSecond != null && (
        <div className="metric-row">
          <span>Tokens / sec</span>
          <span>{m.tokensPerSecond.toFixed(1)}</span>
        </div>
      )}
      {m.gpuUtilization != null && (
        <div className="metric-row">
          <span>GPU util</span>
          <span>{(m.gpuUtilization * 100).toFixed(0)}%</span>
        </div>
      )}
      <div className="metric-row">
        <span>Error rate</span>
        <span>{(m.errorRate * 100).toFixed(2)}%</span>
      </div>
      <div className="metric-row" style={{ marginTop: 4 }}>
        <span>Window</span>
        <span>last {m.timeRange}</span>
      </div>
    </div>
  );
}

function titleFor(entity: AnyEntity): string {
  switch (entity._type) {
    case 'endpoint':
      return entity.url;
    case 'deployment':
      return entity.id;
    case 'model':
    case 'ragPipeline':
    case 'vectorIndex':
    case 'tool':
    case 'agent':
    case 'safetyPolicy':
      return entity.name;
  }
}

function stripType(entity: AnyEntity) {
  const { _type, ...rest } = entity;
  void _type;
  return rest;
}
