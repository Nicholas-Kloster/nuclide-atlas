import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import {
  Background,
  Controls,
  ReactFlow,
  ReactFlowProvider,
  type Edge,
  type Node,
  type NodeMouseHandler,
} from '@xyflow/react';
import '@xyflow/react/dist/style.css';

import {
  fetchGraph,
  fetchProbe,
  fetchRisk,
  fetchSources,
  type ProbeResult,
  type RiskFinding,
  type RiskReport,
} from './lib/api';
import { buildNodesAndEdges, nodeId, type AtlasNodeData } from './lib/graphBuild';
import { agentClosure } from './lib/traverse';
import { traceFromAgent } from './lib/queryFlow';
import type { AnyEntity, EntityType, Graph } from './lib/types';
import { AtlasNode } from './components/AtlasNode';
import { DetailPanel } from './components/DetailPanel';
import { FilterPanel } from './components/FilterPanel';
import { SearchFilter } from './components/SearchFilter';
import { EmptyState } from './components/EmptyState';
import { AddSourceModal } from './components/AddSourceModal';

const ALL_LAYERS: EntityType[] = [
  'endpoint',
  'deployment',
  'model',
  'ragPipeline',
  'vectorIndex',
  'tool',
  'agent',
  'safetyPolicy',
];

const nodeTypes = { atlas: AtlasNode };

const NO_FINDINGS: RiskFinding[] = [];

export function App() {
  const [graph, setGraph] = useState<Graph | null>(null);
  const [loadErr, setLoadErr] = useState<string | null>(null);
  const [selected, setSelected] = useState<AnyEntity | null>(null);
  const [visible, setVisible] = useState<Set<EntityType>>(new Set(ALL_LAYERS));
  const [highlightAgentId, setHighlightAgentId] = useState<string | null>(null);
  const [search, setSearch] = useState('');
  const [showAddSource, setShowAddSource] = useState(false);
  const [probes, setProbes] = useState<Record<string, ProbeResult> | null>(null);
  const [risk, setRisk] = useState<RiskReport | null>(null);
  const [sourcePath, setSourcePath] = useState<string | null>(null);
  const [livePulse, setLivePulse] = useState(false);
  const [pulsedAt, setPulsedAt] = useState<number | null>(null);
  const [traceIds, setTraceIds] = useState<Set<string> | null>(null);
  const traceTimers = useRef<number[]>([]);

  const reloadAll = useCallback(async () => {
    setLoadErr(null);
    try {
      const [g, src, r] = await Promise.all([
        fetchGraph(),
        fetchSources().catch(() => ({ path: '', name: '', exists: false })),
        fetchRisk().catch(() => null),
      ]);
      setGraph(g);
      setSourcePath(src.name || src.path);
      if (r) setRisk(r);
    } catch (e) {
      setLoadErr((e as Error).message);
    }
  }, []);

  useEffect(() => {
    void reloadAll();
  }, [reloadAll]);

  // Live pulse: fire /api/probe every 15s when enabled, and once immediately
  // on toggle so the user sees an effect.
  useEffect(() => {
    if (!livePulse) return;
    let cancelled = false;
    const fire = async () => {
      try {
        const p = await fetchProbe();
        if (!cancelled) {
          setProbes(p);
          setPulsedAt(Date.now());
        }
      } catch {
        /* swallow: pulse is best-effort */
      }
    };
    void fire();
    const id = window.setInterval(fire, 15000);
    return () => {
      cancelled = true;
      window.clearInterval(id);
    };
  }, [livePulse]);

  const built = useMemo(() => (graph ? buildNodesAndEdges(graph) : null), [graph]);

  const closureSet: Set<string> | null = useMemo(() => {
    if (!graph || !highlightAgentId) return null;
    const a = graph.agents.find((x) => x.id === highlightAgentId);
    return a ? agentClosure(graph, a) : null;
  }, [graph, highlightAgentId]);

  const searchMatches: Set<string> = useMemo(() => {
    if (!built || !search.trim()) return new Set();
    const needle = search.toLowerCase();
    const ids = new Set<string>();
    for (const n of built.nodes) {
      const e = n.data.entity as AnyEntity;
      const hay =
        ('name' in e ? (e.name || '') : '') +
        '|' +
        ('url' in e ? (e.url || '') : '') +
        '|' +
        e.id +
        '|' +
        e._type;
      if (hay.toLowerCase().includes(needle)) ids.add(n.id);
    }
    return ids;
  }, [built, search]);

  const probeStatus: Map<string, 'ok' | 'auth' | 'err'> = useMemo(() => {
    const out = new Map<string, 'ok' | 'auth' | 'err'>();
    if (!probes || !graph) return out;
    for (const ep of graph.endpoints) {
      const r = probes[ep.id];
      if (!r) continue;
      if (r.reachable && r.status_code && r.status_code < 400) out.set(nodeId('endpoint', ep.id), 'ok');
      else if (r.status_code === 401 || r.status_code === 403) out.set(nodeId('endpoint', ep.id), 'auth');
      else out.set(nodeId('endpoint', ep.id), 'err');
    }
    return out;
  }, [probes, graph]);

  const { nodes, edges } = useMemo(() => {
    if (!built) return { nodes: [] as Node<AtlasNodeData>[], edges: [] as Edge[] };

    // Layer-visibility filter first.
    const visibleNodes = built.nodes.filter((n) =>
      visible.has((n.data.entity as AnyEntity)._type),
    );
    const visibleIds = new Set(visibleNodes.map((n) => n.id));
    const visibleEdges = built.edges.filter(
      (e) => visibleIds.has(e.source) && visibleIds.has(e.target),
    );

    const decoratedNodes = visibleNodes.map((n) => {
      const classes: string[] = [];

      // Agent closure dim/highlight.
      if (closureSet) {
        classes.push(closureSet.has(n.id) ? 'path-on' : 'path-off');
      }

      // Search match dim/highlight wins over closure for clarity.
      if (search.trim()) {
        classes.push(searchMatches.has(n.id) ? 'search-hit' : 'search-miss');
      }

      // Trace currently-pulsing nodes.
      if (traceIds?.has(n.id)) classes.push('trace-on');

      // Probe status badge on endpoint nodes.
      const ps = probeStatus.get(n.id);
      if (ps) classes.push(`probe-${ps}`);

      // Risk severity badge on entity.
      const r = risk?.byEntity[`${(n.data.entity as AnyEntity)._type}:${(n.data.entity as AnyEntity).id}`];
      if (r?.some((x) => x.severity === 'high')) classes.push('risk-high');
      else if (r?.some((x) => x.severity === 'warn')) classes.push('risk-warn');

      return { ...n, className: classes.join(' ') };
    });

    const decoratedEdges = visibleEdges.map((e) => {
      const classes: string[] = [];
      if (closureSet) {
        classes.push(closureSet.has(e.source) && closureSet.has(e.target) ? 'path-on' : 'path-off');
      }
      if (traceIds?.has(e.source) && traceIds?.has(e.target)) classes.push('trace-on');
      return { ...e, className: classes.join(' ') };
    });

    return { nodes: decoratedNodes, edges: decoratedEdges };
  }, [built, visible, closureSet, search, searchMatches, probeStatus, risk, traceIds]);

  const onNodeClick: NodeMouseHandler = (_, node) => {
    setSelected((node.data as AtlasNodeData).entity);
  };

  const toggleLayer = (k: EntityType) => {
    setVisible((prev) => {
      const next = new Set(prev);
      if (next.has(k)) next.delete(k);
      else next.add(k);
      return next;
    });
  };

  const toggleHighlight = () => {
    if (!selected || selected._type !== 'agent') return;
    setHighlightAgentId((cur) => (cur === selected.id ? null : selected.id));
  };

  const traceQuery = () => {
    if (!graph || !selected || selected._type !== 'agent') return;
    const path = traceFromAgent(graph, selected);
    if (path.length === 0) return;

    // Clear any in-flight trace.
    traceTimers.current.forEach((t) => window.clearTimeout(t));
    traceTimers.current = [];

    const accumulated = new Set<string>();
    path.forEach((id, i) => {
      const tid = window.setTimeout(() => {
        accumulated.add(id);
        setTraceIds(new Set(accumulated));
      }, i * 450);
      traceTimers.current.push(tid);
    });
    // Auto-clear after the path finishes pulsing.
    const clearTid = window.setTimeout(
      () => setTraceIds(null),
      path.length * 450 + 1500,
    );
    traceTimers.current.push(clearTid);
  };

  const selectedRisk: RiskFinding[] =
    risk && selected ? risk.byEntity[`${selected._type}:${selected.id}`] ?? NO_FINDINGS : NO_FINDINGS;

  const stackEmpty =
    graph && graph.models.length === 0 && graph.endpoints.length === 0 && graph.agents.length === 0;

  return (
    <div className="atlas-shell">
      <header className="atlas-header">
        <h1>Nuclide Atlas</h1>
        <span className="muted">
          {graph
            ? `${graph.models.length} models · ${graph.deployments.length} deployments · ${graph.endpoints.length} endpoints · ${graph.agents.length} agents`
            : loadErr
              ? `load error: ${loadErr}`
              : 'loading…'}
        </span>
        {sourcePath && <span className="muted hide-on-narrow">{sourcePath}</span>}
        {risk && risk.count > 0 && (
          <span className="muted risk-pill" title="rule-based findings">
            {risk.count} finding{risk.count === 1 ? '' : 's'}
          </span>
        )}
        {closureSet && (
          <span className="muted">path: {closureSet.size} nodes</span>
        )}
        <span className="header-spacer" />
        <button
          className="header-action"
          onClick={() => setShowAddSource(true)}
        >
          + Add source
        </button>
        <button
          className={`header-action ${livePulse ? 'on' : ''}`}
          onClick={() => setLivePulse((v) => !v)}
          title="Re-probe every 15s and color endpoints by liveness"
        >
          {livePulse ? '● Live' : '○ Live'}
        </button>
      </header>

      <div className="atlas-body">
        <FilterPanel
          visible={visible}
          onToggle={toggleLayer}
          onClearHighlight={() => setHighlightAgentId(null)}
          hasHighlight={highlightAgentId != null}
          search={
            <SearchFilter
              value={search}
              onChange={setSearch}
              matchCount={searchMatches.size}
            />
          }
          pulsedAt={pulsedAt}
        />

        <main className="atlas-canvas">
          {stackEmpty ? (
            <EmptyState onAddSource={() => setShowAddSource(true)} />
          ) : (
            <ReactFlowProvider>
              <ReactFlow
                nodes={nodes}
                edges={edges}
                nodeTypes={nodeTypes}
                onNodeClick={onNodeClick}
                fitView
                minZoom={0.2}
                maxZoom={2}
                proOptions={{ hideAttribution: true }}
              >
                <Background gap={24} color="#1c232c" />
                <Controls position="bottom-right" showInteractive={false} />
              </ReactFlow>
            </ReactFlowProvider>
          )}
        </main>

        <DetailPanel
          entity={selected}
          isAgentHighlighted={
            selected?._type === 'agent' && highlightAgentId === selected.id
          }
          onToggleHighlight={toggleHighlight}
          onTraceQuery={traceQuery}
          isTracing={traceIds !== null}
          risk={selectedRisk}
        />
      </div>

      {showAddSource && (
        <AddSourceModal
          onClose={() => setShowAddSource(false)}
          onChanged={() => void reloadAll()}
        />
      )}
    </div>
  );
}
