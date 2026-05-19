// Turn a backend Graph into React Flow nodes/edges with dagre-laid-out
// positions. The visual columns the spec asks for (Clients/Endpoints,
// Deployments/Models, RAG/Vector/Tools/Agents) map onto dagre's rank
// ordering by typing each node into a `column` rank we sort on.

import type { Edge, Node } from '@xyflow/react';
import dagre from 'dagre';
import type {
  AnyEntity,
  EntityType,
  Graph,
} from './types';

export const NODE_W = 170;
export const NODE_H = 56;

export interface AtlasNodeData extends Record<string, unknown> {
  entity: AnyEntity;
  label: string;
  sub?: string;
}

const COLUMN: Record<EntityType, number> = {
  endpoint: 0,
  deployment: 1,
  model: 2,
  ragPipeline: 3,
  vectorIndex: 4,
  tool: 3,
  agent: 5,
  safetyPolicy: 5,
};

export function buildNodesAndEdges(g: Graph): {
  nodes: Node<AtlasNodeData>[];
  edges: Edge[];
} {
  const nodes: Node<AtlasNodeData>[] = [];
  const edges: Edge[] = [];

  const push = (type: EntityType, id: string, label: string, sub: string, entity: AnyEntity) => {
    nodes.push({
      id: nodeId(type, id),
      type: 'atlas',
      position: { x: 0, y: 0 }, // dagre fills below
      data: { entity, label, sub },
    });
  };

  g.endpoints.forEach((e) =>
    push('endpoint', e.id, e.url, `${e.protocol.toUpperCase()} · ${e.type}`,
      { ...e, _type: 'endpoint' }),
  );
  g.deployments.forEach((d) =>
    push('deployment', d.id, d.id, `${d.inferenceFramework} · ${d.environment}`,
      { ...d, _type: 'deployment' }),
  );
  g.models.forEach((m) =>
    push('model', m.id, m.name, m.providerType, { ...m, _type: 'model' }),
  );
  g.ragPipelines.forEach((r) =>
    push('ragPipeline', r.id, r.name, 'RAG pipeline',
      { ...r, _type: 'ragPipeline' }),
  );
  g.vectorIndexes.forEach((v) =>
    push('vectorIndex', v.id, v.name, `${v.dbType} · dim ${v.embeddingDim}`,
      { ...v, _type: 'vectorIndex' }),
  );
  g.tools.forEach((t) =>
    push('tool', t.id, t.name, t.backingService ?? 'tool', { ...t, _type: 'tool' }),
  );
  g.agents.forEach((a) =>
    push('agent', a.id, a.name, a.role ?? 'agent', { ...a, _type: 'agent' }),
  );
  g.safetyPolicies.forEach((p) =>
    push('safetyPolicy', p.id, p.name, 'safety policy',
      { ...p, _type: 'safetyPolicy' }),
  );

  // Edges per spec:
  //  Endpoint  → Deployment → Model
  //  RagPipeline → Model (embedding) and → VectorIndex
  //  Agent     → Model (primary), Tools, RagPipelines, SafetyPolicy
  g.endpoints.forEach((e) =>
    edges.push(edge('e-d', e.id, e.deploymentId, 'endpoint', 'deployment')),
  );
  g.deployments.forEach((d) =>
    edges.push(edge('d-m', d.id, d.modelId, 'deployment', 'model')),
  );
  g.ragPipelines.forEach((r) => {
    edges.push(edge('r-m', r.id, r.embeddingModelId, 'ragPipeline', 'model'));
    edges.push(edge('r-v', r.id, r.vectorIndexId, 'ragPipeline', 'vectorIndex'));
  });
  g.agents.forEach((a) => {
    edges.push(edge('a-m', a.id, a.primaryModelId, 'agent', 'model'));
    a.toolsUsed.forEach((t) =>
      edges.push(edge('a-t', a.id, t, 'agent', 'tool')),
    );
    a.ragPipelinesUsed.forEach((r) =>
      edges.push(edge('a-r', a.id, r, 'agent', 'ragPipeline')),
    );
    if (a.safetyPolicyId)
      edges.push(edge('a-p', a.id, a.safetyPolicyId, 'agent', 'safetyPolicy'));
  });

  // Dagre layout: LR with ranks bucketed by COLUMN.
  const dg = new dagre.graphlib.Graph().setDefaultEdgeLabel(() => ({}));
  dg.setGraph({ rankdir: 'LR', nodesep: 18, ranksep: 70, marginx: 16, marginy: 16 });
  nodes.forEach((n) =>
    dg.setNode(n.id, {
      width: NODE_W,
      height: NODE_H,
      rank: COLUMN[(n.data.entity as AnyEntity)._type],
    }),
  );
  edges.forEach((e) => dg.setEdge(e.source, e.target));
  dagre.layout(dg);

  return {
    nodes: nodes.map((n) => {
      const p = dg.node(n.id);
      return {
        ...n,
        position: { x: p.x - NODE_W / 2, y: p.y - NODE_H / 2 },
      };
    }),
    edges,
  };
}

export function nodeId(type: EntityType, id: string): string {
  return `${type}:${id}`;
}

function edge(
  kind: string,
  fromId: string,
  toId: string,
  fromT: EntityType,
  toT: EntityType,
): Edge {
  return {
    id: `${kind}|${fromId}->${toId}`,
    source: nodeId(fromT, fromId),
    target: nodeId(toT, toId),
    type: 'default',
    animated: false,
  };
}
