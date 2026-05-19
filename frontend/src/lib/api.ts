import type { EntityType, Graph, MetricsSnapshot } from './types';

const BASE = '';

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

export interface ProbeResult {
  endpoint_id: string;
  reachable: boolean;
  status_code: number | null;
  latency_ms: number | null;
  inferred_operations: string[];
  inferred_provider: string | null;
  error: string | null;
  raw_excerpt: string | null;
}

export async function fetchProbe(): Promise<Record<string, ProbeResult>> {
  const r = await fetch(`${BASE}/api/probe`);
  if (!r.ok) throw new Error(`probe: ${r.status}`);
  const data = await r.json();
  return data.results as Record<string, ProbeResult>;
}

export interface RiskFinding {
  ruleId: string;
  severity: 'info' | 'warn' | 'high';
  message: string;
}

export interface RiskReport {
  findings: Array<RiskFinding & { entityType: EntityType; entityId: string }>;
  byEntity: Record<string, RiskFinding[]>;
  count: number;
}

export async function fetchRisk(): Promise<RiskReport> {
  const r = await fetch(`${BASE}/api/risk`);
  if (!r.ok) throw new Error(`risk: ${r.status}`);
  return r.json();
}

export interface DiscoverResponse {
  wrote: string;
  sources_run: string[];
  counts: Record<string, number>;
  graph_summary: string;
  models: number;
  deployments: number;
  endpoints: number;
}

export async function postDiscover(opts?: {
  include_env?: boolean;
  include_local?: boolean;
  include_docker?: boolean;
  include_k8s?: boolean;
  extra_hosts?: string[];
  k8s_namespace?: string | null;
}): Promise<DiscoverResponse> {
  const r = await fetch(`${BASE}/api/discover`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(opts ?? {}),
  });
  if (!r.ok) throw new Error(`discover: ${r.status}`);
  return r.json();
}

export interface ImportUrlResponse {
  added: { endpoints: unknown[]; vectors: unknown[]; observability: unknown[] };
  wrote: string;
  graph_summary: string;
}

export async function postImportUrl(url: string): Promise<ImportUrlResponse> {
  const r = await fetch(`${BASE}/api/import-url`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ url }),
  });
  if (!r.ok) {
    const detail = await r.text();
    throw new Error(detail || `import-url: ${r.status}`);
  }
  return r.json();
}

export async function fetchSources(): Promise<{ path: string; name: string; exists: boolean }> {
  const r = await fetch(`${BASE}/api/sources`);
  if (!r.ok) throw new Error(`sources: ${r.status}`);
  return r.json();
}
