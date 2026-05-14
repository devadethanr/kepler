import { useEffect, useMemo, useRef, useState } from 'react';
import ForceGraph3D from 'react-force-graph-3d';
import { Bar, BarChart, Cell, ResponsiveContainer } from 'recharts';
import { AnimatePresence, motion } from 'motion/react';
import {
  useKnowledgeGraph,
  useKnowledgeIndex,
  useStockKnowledge,
} from '@/hooks/useDashboardData';
import type { KnowledgeGraphEdge, KnowledgeGraphNode, KnowledgeIndexStock } from '@/lib/schemas';
import { cn } from '@/lib/utils';

type GraphNode = {
  id: string;
  name: string;
  type: string;
  val: number;
  color: string;
  summary: string;
  metadata: Record<string, unknown>;
  ticker: string | null;
  raw: KnowledgeGraphNode;
};

type GraphLink = {
  source: string | GraphNode;
  target: string | GraphNode;
  label: string;
  weight: number;
  metadata: Record<string, unknown>;
  raw: KnowledgeGraphEdge;
};

type GraphState = 'loading' | 'available' | 'degraded' | 'unavailable';

const NODE_COLORS: Record<string, string> = {
  Stock: '#42e09a',
  Sector: '#93ccff',
  Index: '#f7c948',
  Regime: '#93ccff',
  RegimeSnapshot: '#93ccff',
  ResearchRun: '#7dd3fc',
  ResearchCandidate: '#c4b5fd',
  NewsArticle: '#fb7185',
  SignalSnapshot: '#60a5fa',
  TechnicalSnapshot: '#38bdf8',
  FundamentalSnapshot: '#a3e635',
  SentimentSnapshot: '#f472b6',
  Trade: '#f1afff',
  TradeMemory: '#f1afff',
  Observation: '#fdba74',
  Lesson: '#e480ff',
  FailurePattern: '#ffb4ab',
  Incident: '#ffb4ab',
  SkillVersion: '#d8b4fe',
};

const FALLBACK_COLORS = ['#7dd3fc', '#42e09a', '#f7c948', '#f472b6', '#fdba74', '#c4b5fd'];

const STATE_STYLES: Record<GraphState, string> = {
  loading: 'border-outline-variant/40 bg-surface-container/60 text-on-surface-variant',
  available: 'border-secondary/40 bg-secondary/10 text-secondary',
  degraded: 'border-tertiary/40 bg-tertiary/10 text-tertiary',
  unavailable: 'border-error/40 bg-error/10 text-error',
};

function displayValue(value: unknown): string | null {
  if (typeof value === 'string' && value.trim()) return value;
  if (typeof value === 'number' && Number.isFinite(value)) return String(value);
  if (typeof value === 'boolean') return value ? 'true' : 'false';
  return null;
}

function pickValue(source: Record<string, unknown> | undefined, keys: string[]): string | null {
  if (!source) return null;
  for (const key of keys) {
    const value = displayValue(source[key]);
    if (value) return value;
  }
  return null;
}

function titleCase(value: string): string {
  const cleaned = value.replace(/[_:-]+/g, ' ').trim();
  if (!cleaned) return 'Unknown';
  return cleaned
    .split(/\s+/)
    .map((part) => `${part.charAt(0).toUpperCase()}${part.slice(1)}`)
    .join(' ');
}

function normalizeType(value: string): string {
  const normalized = titleCase(value);
  return normalized === 'Unknown' ? 'Unknown' : normalized.replace(/\s+/g, '');
}

function normalizeSize(value: unknown, fallback: number): number {
  const numeric = typeof value === 'number' ? value : Number(value);
  if (!Number.isFinite(numeric)) return fallback;
  return Math.max(2, Math.min(14, numeric));
}

function inferTicker(
  id: string,
  name: string,
  type: string,
  metadata: Record<string, unknown>,
  raw: Record<string, unknown>,
): string | null {
  const explicit = pickValue(metadata, ['ticker', 'symbol']) ?? pickValue(raw, ['ticker', 'symbol']);
  if (explicit) return explicit.toUpperCase();

  const idParts = id.split(':');
  if (idParts[0]?.toLowerCase().includes('stock') && idParts.length > 1) {
    return String(idParts[idParts.length - 1]).toUpperCase();
  }
  if (type.toLowerCase() === 'stock') return name.toUpperCase();
  return null;
}

function normalizeNode(node: KnowledgeGraphNode, index: number): GraphNode {
  const raw = node as Record<string, unknown>;
  const metadata = (node.metadata ?? raw.properties ?? {}) as Record<string, unknown>;
  const type = normalizeType(node.type);
  const name =
    displayValue(node.name) ??
    displayValue(node.label) ??
    pickValue(metadata, ['title', 'name', 'ticker', 'source_id']) ??
    node.id.split(':').at(-1) ??
    node.id;
  const summary =
    displayValue(node.summary) ??
    pickValue(metadata, ['summary', 'description', 'thesis', 'reason', 'note']) ??
    `${type} node from graph memory.`;
  const color =
    displayValue(node.color) ??
    NODE_COLORS[type] ??
    FALLBACK_COLORS[index % FALLBACK_COLORS.length];
  const sizeCandidate =
    node.val ?? node.size ?? metadata.score ?? metadata.confidence ?? metadata.weight ?? null;

  return {
    id: node.id,
    name,
    type,
    val: normalizeSize(sizeCandidate, 4 + Math.min(index % 5, 3)),
    color,
    summary,
    metadata,
    ticker: inferTicker(node.id, name, type, metadata, raw),
    raw: node,
  };
}

function normalizeLink(edge: KnowledgeGraphEdge): GraphLink {
  const raw = edge as Record<string, unknown>;
  const metadata = (edge.metadata ?? raw.properties ?? {}) as Record<string, unknown>;
  return {
    source: edge.source,
    target: edge.target,
    label: displayValue(edge.label) ?? displayValue(edge.relationship) ?? 'RELATED_TO',
    weight: normalizeSize(edge.weight, 1),
    metadata,
    raw: edge,
  };
}

function endpointId(endpoint: string | GraphNode): string {
  return typeof endpoint === 'string' ? endpoint : endpoint.id;
}

function normalizeIndexStocks(
  stocks: Record<string, KnowledgeIndexStock> | KnowledgeIndexStock[] | undefined,
): KnowledgeIndexStock[] {
  if (!stocks) return [];
  return Array.isArray(stocks) ? stocks : Object.values(stocks);
}

function backendMessage(value: string | null | undefined): string | null {
  if (!value) return null;
  const lower = value.toLowerCase();
  if (lower.includes('phase') && lower.includes('14')) return null;
  return value;
}

function errorMessage(error: unknown): string | null {
  return error instanceof Error ? error.message : null;
}

function evidenceLabel(evidence: Record<string, unknown>): string {
  return (
    pickValue(evidence, ['title', 'summary', 'source', 'relationship', 'kind', 'type']) ??
    JSON.stringify(evidence)
  );
}

function connectionLabel(connection: string | Record<string, unknown>): string {
  if (typeof connection === 'string') return connection;
  return (
    pickValue(connection, ['label', 'name', 'ticker', 'id', 'relationship', 'type']) ??
    JSON.stringify(connection)
  );
}

export function KnowledgeScreen() {
  const containerRef = useRef<HTMLDivElement>(null);
  const fgRef = useRef<any>(null);
  const graphQuery = useKnowledgeGraph();
  const indexQuery = useKnowledgeIndex();
  const [dimensions, setDimensions] = useState({ width: 800, height: 600 });
  const [selectedNode, setSelectedNode] = useState<GraphNode | null>(null);
  const [activeFilters, setActiveFilters] = useState<string[]>([]);
  const selectedTicker = selectedNode?.ticker ?? null;
  const stockQuery = useStockKnowledge(selectedTicker);

  useEffect(() => {
    const updateDim = () => {
      if (containerRef.current) {
        setDimensions({
          width: containerRef.current.offsetWidth,
          height: containerRef.current.offsetHeight,
        });
      }
    };
    updateDim();
    window.addEventListener('resize', updateDim);
    return () => window.removeEventListener('resize', updateDim);
  }, []);

  const graphStatus = graphQuery.data?.status.toLowerCase() ?? '';
  const graphPhase = graphQuery.data?.phase?.toLowerCase() ?? '';
  const graphUnavailable =
    graphQuery.isError ||
    ['unavailable', 'disabled', 'deferred', 'error'].some((status) =>
      graphStatus.includes(status),
    ) ||
    (graphPhase.includes('phase') && graphPhase.includes('14'));
  const graphDegraded =
    !graphUnavailable &&
    ['degraded', 'partial', 'fallback'].some((status) => graphStatus.includes(status));
  const graphState: GraphState = graphQuery.isLoading
    ? 'loading'
    : graphUnavailable
      ? 'unavailable'
      : graphDegraded
        ? 'degraded'
        : 'available';
  const statusLabel =
    graphState === 'available'
      ? 'Live'
      : graphState === 'degraded'
        ? 'Degraded'
        : graphState === 'loading'
          ? 'Loading'
          : 'Unavailable';
  const graphMessage =
    backendMessage(graphQuery.data?.last_error) ??
    backendMessage(graphQuery.data?.degraded_reason) ??
    backendMessage(graphQuery.data?.message) ??
    errorMessage(graphQuery.error) ??
    (graphState === 'unavailable'
      ? 'Context graph memory is not available from the backend.'
      : null);

  const graphNodes = useMemo(() => {
    if (graphUnavailable) return [];
    return graphQuery.data?.nodes.map(normalizeNode) ?? [];
  }, [graphQuery.data?.nodes, graphUnavailable]);

  const graphLinks = useMemo(() => {
    if (graphUnavailable) return [];
    return graphQuery.data?.edges.map(normalizeLink) ?? [];
  }, [graphQuery.data?.edges, graphUnavailable]);

  const nodeTypes = useMemo(
    () => Array.from(new Set(graphNodes.map((node) => node.type))).sort(),
    [graphNodes],
  );
  const nodeTypesKey = nodeTypes.join('|');

  useEffect(() => {
    setActiveFilters((current) => {
      if (!nodeTypes.length) return [];
      if (!current.length) return nodeTypes;
      const next = current.filter((type) => nodeTypes.includes(type));
      return next.length ? next : nodeTypes;
    });
  }, [nodeTypesKey]);

  useEffect(() => {
    if (selectedNode && !graphNodes.some((node) => node.id === selectedNode.id)) {
      setSelectedNode(null);
    }
  }, [graphNodes, selectedNode]);

  const filteredData = useMemo(() => {
    const visibleNodes = graphNodes.filter((node) => activeFilters.includes(node.type));
    const ids = new Set(visibleNodes.map((node) => node.id));
    return {
      nodes: visibleNodes,
      links: graphLinks.filter(
        (link) => ids.has(endpointId(link.source)) && ids.has(endpointId(link.target)),
      ),
    };
  }, [activeFilters, graphLinks, graphNodes]);

  const typeDensity = useMemo(
    () =>
      nodeTypes.map((type) => ({
        type,
        count: graphNodes.filter((node) => node.type === type).length,
        color: graphNodes.find((node) => node.type === type)?.color ?? '#3f4851',
      })),
    [graphNodes, nodeTypes],
  );

  const indexStocks = normalizeIndexStocks(indexQuery.data?.stocks);
  const graphStockCount = graphNodes.filter((node) => node.type === 'Stock').length;
  const stockCount =
    graphQuery.data?.counts.stocks ??
    graphQuery.data?.counts.Stock ??
    (indexStocks.length || graphStockCount);
  const selectedLinkCount = selectedNode
    ? graphLinks.filter(
        (link) =>
          endpointId(link.source) === selectedNode.id || endpointId(link.target) === selectedNode.id,
      ).length
    : 0;
  const stockKnowledge = stockQuery.data;
  const stockStatus = stockKnowledge?.status.toLowerCase() ?? '';
  const stockUnavailable =
    stockQuery.isError ||
    ['unavailable', 'disabled', 'deferred', 'error'].some((status) =>
      stockStatus.includes(status),
    );
  const stockDegraded =
    !stockUnavailable &&
    ['degraded', 'partial', 'fallback'].some((status) => stockStatus.includes(status));
  const stockMessage =
    backendMessage(stockKnowledge?.last_error) ??
    backendMessage(stockKnowledge?.degraded_reason) ??
    backendMessage(stockKnowledge?.message) ??
    errorMessage(stockQuery.error);

  return (
    <div className="flex-1 h-full bg-[#050505] relative overflow-hidden" ref={containerRef}>
      <div className="absolute top-6 left-6 z-10 flex flex-col gap-4 pointer-events-none">
        <div className="flex items-center gap-3">
          <h1 className="text-2xl md:text-3xl font-headline font-black text-white tracking-tight uppercase">
            Context Graph
          </h1>
          <span
            className={cn(
              'px-2 py-1 rounded-sm border text-[10px] font-mono font-bold uppercase',
              STATE_STYLES[graphState],
            )}
          >
            {statusLabel}
          </span>
        </div>
        <div className="max-w-xl text-[12px] font-mono text-on-surface-variant leading-relaxed">
          <span>{graphNodes.length} nodes</span>
          <span className="mx-2 text-outline-variant">/</span>
          <span>{graphLinks.length} edges</span>
          <span className="mx-2 text-outline-variant">/</span>
          <span>{stockCount} indexed stocks</span>
          {graphQuery.data?.last_updated && (
            <>
              <span className="mx-2 text-outline-variant">/</span>
              <span>Updated {graphQuery.data.last_updated}</span>
            </>
          )}
        </div>
      </div>

      <div className="absolute top-28 left-6 z-10 bg-surface-container-low/80 backdrop-blur-md border border-outline-variant/30 rounded-md p-3 pointer-events-auto">
        <div className="text-[10px] font-mono text-on-surface-variant uppercase tracking-widest mb-3">
          Node Filters
        </div>
        <div className="flex flex-col gap-2 min-w-32">
          {nodeTypes.length ? (
            nodeTypes.map((type) => {
              const active = activeFilters.includes(type);
              const sample = graphNodes.find((node) => node.type === type);
              return (
                <label key={type} className="flex items-center gap-2 cursor-pointer group">
                  <input
                    type="checkbox"
                    checked={active}
                    onChange={() => {
                      setActiveFilters((current) =>
                        current.includes(type)
                          ? current.filter((item) => item !== type)
                          : [...current, type],
                      );
                    }}
                    className="hidden"
                  />
                  <div
                    className={cn(
                      'w-3 h-3 rounded-sm border flex items-center justify-center',
                      active
                        ? 'bg-surface-high border-outline-variant/50'
                        : 'bg-surface-lowest border-outline-variant/20',
                    )}
                  >
                    {active && (
                      <span
                        className="w-1.5 h-1.5 rounded-full"
                        style={{ backgroundColor: sample?.color }}
                      ></span>
                    )}
                  </div>
                  <span
                    className={cn(
                      'text-[11px] font-mono transition-colors',
                      active ? 'text-white' : 'text-on-surface-variant group-hover:text-white/70',
                    )}
                  >
                    {type}
                  </span>
                </label>
              );
            })
          ) : (
            <span className="text-[11px] font-mono text-on-surface-variant">
              {graphQuery.isLoading ? 'Loading node types...' : 'No node types returned.'}
            </span>
          )}
        </div>
      </div>

      <ForceGraph3D
        ref={fgRef}
        graphData={filteredData}
        width={dimensions.width}
        height={dimensions.height}
        backgroundColor="#050505"
        nodeLabel={(node: any) => `${node.name} (${node.type})`}
        nodeColor={(node: any) => node.color}
        nodeVal={(node: any) => node.val}
        linkLabel={(link: any) => link.label}
        linkWidth={(link: any) => Math.max(0.5, Math.min(3, Number(link.weight) || 1))}
        linkColor={() => (graphState === 'degraded' ? 'rgba(250,204,21,0.5)' : 'rgba(168,85,247,0.5)')}
        linkDirectionalParticles={graphState === 'unavailable' ? 0 : 2}
        linkDirectionalParticleSpeed={0.006}
        linkDirectionalParticleWidth={2.5}
        linkDirectionalParticleColor={() => (graphState === 'degraded' ? 'rgba(250,204,21,0.9)' : 'rgba(124,58,237,0.9)')}
        linkDirectionalArrowLength={4}
        linkDirectionalArrowRelPos={0.95}
        onNodeClick={(node: any) => setSelectedNode(node)}
      />

      {(graphState === 'loading' || graphState === 'unavailable' || !graphNodes.length) && (
        <div className="absolute inset-0 z-0 flex items-center justify-center pointer-events-none">
          <div className="w-[min(420px,calc(100vw-48px))] bg-surface-container-low/90 backdrop-blur-md border border-outline-variant/30 rounded-md p-5 text-center shadow-xl">
            <div
              className={cn(
                'text-[10px] font-mono font-bold uppercase tracking-widest mb-2',
                graphState === 'unavailable' ? 'text-error' : 'text-on-surface-variant',
              )}
            >
              {graphState === 'loading'
                ? 'Loading Graph'
                : graphState === 'unavailable'
                  ? 'Graph Unavailable'
                  : 'Graph Empty'}
            </div>
            <p className="text-[12px] font-mono text-on-surface-variant leading-relaxed">
              {graphState === 'loading'
                ? 'Loading context graph from the dashboard API.'
                : graphMessage ?? 'The backend returned no graph nodes.'}
            </p>
          </div>
        </div>
      )}

      {graphState === 'degraded' && (
        <div className="absolute top-6 right-6 z-10 w-80 bg-surface-container-low/90 backdrop-blur-md border border-tertiary/30 rounded-md p-3 shadow-xl pointer-events-none">
          <div className="text-[10px] font-mono font-bold uppercase tracking-widest text-tertiary mb-1">
            Degraded Context
          </div>
          <p className="text-[11px] font-mono text-on-surface-variant leading-relaxed">
            {graphMessage ?? 'The backend is serving partial graph context.'}
          </p>
        </div>
      )}

      <div className="absolute bottom-6 left-1/2 transform -translate-x-1/2 z-10 w-[min(600px,calc(100vw-48px))] bg-surface-container-low/80 backdrop-blur-md border border-outline-variant/30 rounded-md p-3 flex flex-col gap-2 shadow-xl pointer-events-auto">
        <div className="flex justify-between items-center text-[10px] font-mono text-on-surface-variant uppercase tracking-widest pl-2">
          <span>Node Distribution</span>
          <button className="hover:text-white transition-colors" onClick={() => fgRef.current?.zoomToFit(1000)}>
            Reset Camera
          </button>
        </div>
        <div className="h-10 w-full px-2">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={typeDensity}>
              <Bar dataKey="count" radius={[2, 2, 0, 0]}>
                {typeDensity.map((entry, index) => (
                  <Cell
                    cursor="pointer"
                    fill={entry.color}
                    key={`${entry.type}-${index}`}
                    className="opacity-70 hover:opacity-100 transition-all"
                  />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>

      <AnimatePresence>
        {selectedNode && (
          <motion.div
            initial={{ x: 20, opacity: 0 }}
            animate={{ x: 0, opacity: 1 }}
            exit={{ x: 20, opacity: 0 }}
            className="absolute top-6 right-6 bottom-6 w-80 bg-surface-container-low/90 backdrop-blur-xl border border-outline-variant/30 rounded-md flex flex-col shadow-2xl z-20 pointer-events-auto"
          >
            <div className="p-4 border-b border-outline-variant/20 flex justify-between items-start">
              <div className="flex flex-col">
                <span
                  className="text-[10px] font-mono px-2 py-0.5 rounded border mb-2 w-max uppercase tracking-wider"
                  style={{
                    color: selectedNode.color,
                    borderColor: `${selectedNode.color}40`,
                    backgroundColor: `${selectedNode.color}10`,
                  }}
                >
                  {selectedNode.type} Node
                </span>
                <h3 className="text-lg font-headline font-bold text-white">{selectedNode.name}</h3>
                <span className="text-[10px] font-mono text-on-surface-variant mt-1">
                  ID: {selectedNode.id}
                </span>
              </div>
              <button onClick={() => setSelectedNode(null)} className="text-on-surface-variant hover:text-white mt-1">
                <span className="material-symbols-outlined text-[20px]">close</span>
              </button>
            </div>

            <div className="flex-1 overflow-y-auto p-4 flex flex-col gap-5 text-[11px] font-mono">
              <div>
                <span className="block text-on-surface-variant text-[10px] uppercase mb-1">
                  Metadata
                </span>
                <div className="grid grid-cols-2 gap-2 bg-surface-lowest p-2 border border-outline-variant/10 rounded">
                  <div className="flex flex-col">
                    <span className="text-on-surface-variant opacity-70">Type</span>
                    <span className="text-white">{selectedNode.type}</span>
                  </div>
                  <div className="flex flex-col">
                    <span className="text-on-surface-variant opacity-70">Rank</span>
                    <span className="text-white">{selectedNode.val}</span>
                  </div>
                  <div className="flex flex-col">
                    <span className="text-on-surface-variant opacity-70">Links</span>
                    <span className="text-white">{selectedLinkCount}</span>
                  </div>
                  <div className="flex flex-col">
                    <span className="text-on-surface-variant opacity-70">Ticker</span>
                    <span className="text-white">{selectedNode.ticker ?? 'n/a'}</span>
                  </div>
                </div>
              </div>

              {selectedNode.ticker && (
                <div>
                  <div className="flex items-center justify-between text-[10px] uppercase mb-1">
                    <span className="text-on-surface-variant">Stock Context</span>
                    {(stockDegraded || stockUnavailable) && (
                      <span className={stockUnavailable ? 'text-error' : 'text-tertiary'}>
                        {stockUnavailable ? 'Unavailable' : 'Degraded'}
                      </span>
                    )}
                  </div>
                  <div className="bg-surface-lowest p-2 border border-outline-variant/10 rounded leading-relaxed text-on-surface-variant">
                    {stockQuery.isLoading
                      ? 'Loading stock context...'
                      : stockMessage ??
                        stockKnowledge?.summary ??
                        'No stock-specific context returned.'}
                  </div>
                </div>
              )}

              <div>
                <span className="block text-on-surface-variant text-[10px] uppercase mb-1">
                  Summary
                </span>
                <div className="bg-surface-highest p-3 rounded border border-outline-variant/20 leading-relaxed text-on-surface shadow-[inset_0_0_10px_rgba(0,0,0,0.2)]">
                  {stockKnowledge?.summary ?? selectedNode.summary}
                </div>
              </div>

              {!!stockKnowledge?.evidence.length && (
                <div>
                  <span className="block text-on-surface-variant text-[10px] uppercase mb-1">
                    Evidence
                  </span>
                  <div className="flex flex-col gap-2">
                    {stockKnowledge.evidence.slice(0, 4).map((evidence, index) => (
                      <div
                        key={index}
                        className="bg-surface-lowest p-2 border border-outline-variant/10 rounded text-on-surface-variant leading-relaxed"
                      >
                        {evidenceLabel(evidence)}
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {!!stockKnowledge?.connections.length && (
                <div>
                  <span className="block text-on-surface-variant text-[10px] uppercase mb-1">
                    Connections
                  </span>
                  <div className="flex flex-wrap gap-2">
                    {stockKnowledge.connections.slice(0, 8).map((connection, index) => (
                      <span
                        key={index}
                        className="px-2 py-1 rounded-sm bg-surface-lowest border border-outline-variant/10 text-on-surface-variant"
                      >
                        {connectionLabel(connection)}
                      </span>
                    ))}
                  </div>
                </div>
              )}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
