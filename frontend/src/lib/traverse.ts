// Agent path highlight.
//
// Closure rule (locked, do not loosen without updating the comment):
//   Agent → { primaryModelId, toolsUsed[], ragPipelinesUsed[], safetyPolicyId }
//   RagPipeline → { embeddingModelId, vectorIndexId }
//   SafetyPolicy → { safetyModelId }
//   For every Model in the closure: include all Deployments referencing it
//     and every Endpoint pointing at those Deployments.
//
// Without the Deployment+Endpoint inclusion, a Model lights up but its
// serving path stays dark, which makes the highlight visually broken.

import type { Agent, Graph } from './types';
import { nodeId } from './graphBuild';

export function agentClosure(g: Graph, agent: Agent): Set<string> {
  const ids = new Set<string>();
  const modelIds = new Set<string>();

  ids.add(nodeId('agent', agent.id));
  ids.add(nodeId('model', agent.primaryModelId));
  modelIds.add(agent.primaryModelId);

  agent.toolsUsed.forEach((t) => ids.add(nodeId('tool', t)));
  if (agent.safetyPolicyId) {
    ids.add(nodeId('safetyPolicy', agent.safetyPolicyId));
    const p = g.safetyPolicies.find((s) => s.id === agent.safetyPolicyId);
    if (p?.safetyModelId) {
      ids.add(nodeId('model', p.safetyModelId));
      modelIds.add(p.safetyModelId);
    }
  }

  agent.ragPipelinesUsed.forEach((rid) => {
    ids.add(nodeId('ragPipeline', rid));
    const r = g.ragPipelines.find((x) => x.id === rid);
    if (!r) return;
    ids.add(nodeId('model', r.embeddingModelId));
    ids.add(nodeId('vectorIndex', r.vectorIndexId));
    modelIds.add(r.embeddingModelId);
  });

  // Pull serving path for every Model in the closure.
  g.deployments.forEach((d) => {
    if (!modelIds.has(d.modelId)) return;
    ids.add(nodeId('deployment', d.id));
    g.endpoints
      .filter((e) => e.deploymentId === d.id)
      .forEach((e) => ids.add(nodeId('endpoint', e.id)));
  });

  return ids;
}
