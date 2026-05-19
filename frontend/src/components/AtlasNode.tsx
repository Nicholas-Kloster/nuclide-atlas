import { Handle, Position, type NodeProps } from '@xyflow/react';
import type { AtlasNodeData } from '../lib/graphBuild';
import type { AnyEntity } from '../lib/types';

const COLOR: Record<AnyEntity['_type'], string> = {
  model: 'var(--node-model)',
  deployment: 'var(--node-deployment)',
  endpoint: 'var(--node-endpoint)',
  ragPipeline: 'var(--node-rag)',
  vectorIndex: 'var(--node-vector)',
  tool: 'var(--node-tool)',
  agent: 'var(--node-agent)',
  safetyPolicy: 'var(--node-safety)',
};

export function AtlasNode({ data }: NodeProps) {
  const d = data as AtlasNodeData;
  const t = d.entity._type;
  return (
    <div style={{ borderLeft: `4px solid ${COLOR[t]}`, paddingLeft: 6 }}>
      <Handle type="target" position={Position.Left} style={{ background: 'transparent', border: 0 }} />
      <div className="node-title">{d.label}</div>
      <div className="node-sub">{d.sub}</div>
      <Handle type="source" position={Position.Right} style={{ background: 'transparent', border: 0 }} />
    </div>
  );
}
