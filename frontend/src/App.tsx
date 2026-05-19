import { useEffect, useMemo, useState } from 'react';
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

import { fetchGraph } from './lib/api';
import { buildNodesAndEdges, type AtlasNodeData } from './lib/graphBuild';
import { agentClosure } from './lib/traverse';
import type { AnyEntity, EntityType, Graph } from './lib/types';
import { AtlasNode } from './components/AtlasNode';
import { DetailPanel } from './components/DetailPanel';
import { FilterPanel } from './components/FilterPanel';

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

export function App() {
  const [graph, setGraph] = useState<Graph | null>(null);
  const [loadErr, setLoadErr] = useState<string | null>(null);
  const [selected, setSelected] = useState<AnyEntity | null>(null);
  const [visible, setVisible] = useState<Set<EntityType>>(new Set(ALL_LAYERS));
  const [highlightAgentId, setHighlightAgentId] = useState<string | null>(null);

  useEffect(() => {
    fetchGraph()
      .then(setGraph)
      .catch((e: Error) => setLoadErr(e.message));
  }, []);

  const built = useMemo(() => (graph ? buildNodesAndEdges(graph) : null), [graph]);

  const highlightSet: Set<string> | null = useMemo(() => {
    if (!graph || !highlightAgentId) return null;
    const a = graph.agents.find((x) => x.id === highlightAgentId);
    return a ? agentClosure(graph, a) : null;
  }, [graph, highlightAgentId]);

  const { nodes, edges } = useMemo(() => {
    if (!built) return { nodes: [] as Node<AtlasNodeData>[], edges: [] as Edge[] };
    const filteredNodes = built.nodes.filter((n) =>
      visible.has((n.data.entity as AnyEntity)._type),
    );
    const visibleIds = new Set(filteredNodes.map((n) => n.id));
    const filteredEdges = built.edges.filter(
      (e) => visibleIds.has(e.source) && visibleIds.has(e.target),
    );

    if (!highlightSet) {
      return {
        nodes: filteredNodes.map((n) => ({ ...n, className: '' })),
        edges: filteredEdges.map((e) => ({ ...e, className: '' })),
      };
    }
    return {
      nodes: filteredNodes.map((n) => ({
        ...n,
        className: highlightSet.has(n.id) ? 'path-on' : 'path-off',
      })),
      edges: filteredEdges.map((e) => ({
        ...e,
        className:
          highlightSet.has(e.source) && highlightSet.has(e.target)
            ? 'path-on'
            : 'path-off',
      })),
    };
  }, [built, visible, highlightSet]);

  const onNodeClick: NodeMouseHandler = (_, node) => {
    const entity = (node.data as AtlasNodeData).entity;
    setSelected(entity);
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
        {highlightSet && (
          <span className="muted">
            path: {highlightSet.size} nodes
          </span>
        )}
      </header>

      <div className="atlas-body">
        <FilterPanel
          visible={visible}
          onToggle={toggleLayer}
          onClearHighlight={() => setHighlightAgentId(null)}
          hasHighlight={highlightAgentId != null}
        />

        <main className="atlas-canvas">
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
        </main>

        <DetailPanel
          entity={selected}
          isAgentHighlighted={
            selected?._type === 'agent' && highlightAgentId === selected.id
          }
          onToggleHighlight={toggleHighlight}
        />
      </div>
    </div>
  );
}
