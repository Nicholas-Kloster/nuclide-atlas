import type { EntityType, Graph, MetricsSnapshot } from './types';

const BASE = ''; // relative; vite dev proxy + same-origin in prod compose

export async function fetchGraph(): Promise<Graph> {
  const r = await fetch(`${BASE}/api/graph`);
  if (!r.ok) throw new Error(`graph: ${r.status}`);
  return r.json();
}

export async function fetchMetrics(
  entityType: EntityType,
  entityId: string,
): Promise<MetricsSnapshot> {
  const r = await fetch(`${BASE}/api/metrics/${entityType}/${entityId}`);
  if (!r.ok) throw new Error(`metrics: ${r.status}`);
  return r.json();
}
