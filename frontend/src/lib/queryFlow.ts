// Query Flow — animate a hypothetical user query traversing the graph.
//
// Starting from an Agent, the trace visits, in order:
//   1. Agent's safety policy (pre-prompt filter step)
//   2. Each RAG pipeline → its vector index → its embedding model
//   3. Tools available to the agent
//   4. The agent's primary model
//   5. The deployments serving that model and their endpoints
//   6. Back to the safety policy (post-response filter step) — by visiting
//      its id again, the pulse animation lights it twice, which reads as
//      "pre- and post- pass," same way a real request would flow.
//
// The path is an ordered list of node ids — the App accumulates them on
// a timer, so each id lights up in sequence.

import { nodeId } from './graphBuild';
import type { Agent, Graph } from './types';

export function traceFromAgent(g: Graph, agent: Agent): string[] {
  const path: string[] = [nodeId('agent', agent.id)];

  if (agent.safetyPolicyId) {
    path.push(nodeId('safetyPolicy', agent.safetyPolicyId));
  }

  for (const rid of agent.ragPipelinesUsed) {
    path.push(nodeId('ragPipeline', rid));
    const r = g.ragPipelines.find((x) => x.id === rid);
    if (!r) continue;
    path.push(nodeId('vectorIndex', r.vectorIndexId));
    path.push(nodeId('model', r.embeddingModelId));
  }

  for (const tid of agent.toolsUsed) {
    path.push(nodeId('tool', tid));
  }

  path.push(nodeId('model', agent.primaryModelId));

  for (const d of g.deployments) {
    if (d.modelId !== agent.primaryModelId) continue;
    path.push(nodeId('deployment', d.id));
    for (const e of g.endpoints) {
      if (e.deploymentId === d.id) path.push(nodeId('endpoint', e.id));
    }
  }

  if (agent.safetyPolicyId) {
    path.push(nodeId('safetyPolicy', agent.safetyPolicyId));
  }

  return path;
}
