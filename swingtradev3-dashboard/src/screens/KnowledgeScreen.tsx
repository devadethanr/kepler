import { useEffect, useMemo, useRef, useState } from 'react';
import ForceGraph3D from 'react-force-graph-3d';
import { Bar, BarChart, Cell, ResponsiveContainer } from 'recharts';
import { AnimatePresence, motion } from 'motion/react';
import { cn } from '@/lib/utils';

type Node = {
  id: string;
  name: string;
  type: 'Regime' | 'Stock' | 'Trade' | 'Lesson' | 'Incident';
  val: number;
  color: string;
  summary: string;
};

const nodes: Node[] = [
  { id: 'regime:range', name: 'Range Expansion', type: 'Regime', val: 8, color: '#93ccff', summary: 'Mock regime context used only to exercise the Phase 8 graph UI.' },
  { id: 'stock:RELIANCE', name: 'RELIANCE', type: 'Stock', val: 9, color: '#42e09a', summary: 'Representative high-liquidity candidate node.' },
  { id: 'stock:TCS', name: 'TCS', type: 'Stock', val: 7, color: '#42e09a', summary: 'Representative technology-sector candidate node.' },
  { id: 'trade:001', name: 'Breakout Trade', type: 'Trade', val: 6, color: '#f1afff', summary: 'Mock trade memory node connected to one setup lesson.' },
  { id: 'lesson:trail', name: 'Trail After Confirmation', type: 'Lesson', val: 5, color: '#e480ff', summary: 'Mock lesson demonstrating future memory retrieval.' },
  { id: 'incident:gtt', name: 'GTT Recovery', type: 'Incident', val: 4, color: '#ffb4ab', summary: 'Mock incident node for future operator graph workflows.' },
];

const links = [
  { source: 'regime:range', target: 'stock:RELIANCE', label: 'supports' },
  { source: 'regime:range', target: 'stock:TCS', label: 'constrains' },
  { source: 'stock:RELIANCE', target: 'trade:001', label: 'generated' },
  { source: 'trade:001', target: 'lesson:trail', label: 'taught' },
  { source: 'incident:gtt', target: 'lesson:trail', label: 'reinforced' },
  { source: 'stock:TCS', target: 'incident:gtt', label: 'monitored_by' },
];

const timelineData = [
  { day: 'D-13', nodesCreated: 4 },
  { day: 'D-12', nodesCreated: 7 },
  { day: 'D-11', nodesCreated: 3 },
  { day: 'D-10', nodesCreated: 8 },
  { day: 'D-9', nodesCreated: 5 },
  { day: 'D-8', nodesCreated: 6 },
  { day: 'D-7', nodesCreated: 9 },
  { day: 'D-6', nodesCreated: 4 },
  { day: 'D-5', nodesCreated: 6 },
  { day: 'D-4', nodesCreated: 10 },
  { day: 'D-3', nodesCreated: 8 },
  { day: 'D-2', nodesCreated: 7 },
  { day: 'D-1', nodesCreated: 5 },
  { day: 'D-0', nodesCreated: 6 },
];

const nodeTypes: Node['type'][] = ['Regime', 'Stock', 'Trade', 'Lesson', 'Incident'];

export function KnowledgeScreen() {
  const containerRef = useRef<HTMLDivElement>(null);
  const fgRef = useRef<any>(null);
  const [dimensions, setDimensions] = useState({ width: 800, height: 600 });
  const [selectedNode, setSelectedNode] = useState<Node | null>(null);
  const [activeFilters, setActiveFilters] = useState<Node['type'][]>(nodeTypes);

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

  const filteredData = useMemo(() => {
    const visibleNodes = nodes.filter((node) => activeFilters.includes(node.type));
    const ids = new Set(visibleNodes.map((node) => node.id));
    return {
      nodes: visibleNodes,
      links: links.filter((link) => ids.has(String(link.source)) && ids.has(String(link.target))),
    };
  }, [activeFilters]);

  return (
    <div className="flex-1 h-full bg-[#050505] relative overflow-hidden" ref={containerRef}>
      <div className="absolute top-6 left-6 z-10 flex flex-col gap-4 pointer-events-none">
        <div className="flex items-center gap-3">
          <h1 className="text-2xl md:text-3xl font-headline font-black text-white tracking-tight uppercase">Context Graph</h1>
          <span className="px-2 py-1 rounded-sm border border-tertiary/40 bg-tertiary/10 text-tertiary text-[10px] font-mono font-bold uppercase">
            Phase 14 Mock
          </span>
        </div>
        <p className="max-w-md text-[12px] font-mono text-on-surface-variant leading-relaxed">
          Deterministic local graph preview. Real Postgres and Memgraph memory is intentionally deferred.
        </p>
      </div>

      <div className="absolute top-24 left-6 z-10 bg-surface-container-low/80 backdrop-blur-md border border-outline-variant/30 rounded-md p-3 pointer-events-auto">
        <div className="text-[10px] font-mono text-on-surface-variant uppercase tracking-widest mb-3">Node Filters</div>
        <div className="flex flex-col gap-2">
          {nodeTypes.map((type) => {
            const active = activeFilters.includes(type);
            const sample = nodes.find((node) => node.type === type);
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
                <div className={cn("w-3 h-3 rounded-sm border flex items-center justify-center", active ? "bg-surface-high border-outline-variant/50" : "bg-surface-lowest border-outline-variant/20")}>
                  {active && <span className="w-1.5 h-1.5 rounded-full" style={{ backgroundColor: sample?.color }}></span>}
                </div>
                <span className={cn("text-[11px] font-mono transition-colors", active ? "text-white" : "text-on-surface-variant group-hover:text-white/70")}>{type}</span>
              </label>
            );
          })}
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
        linkColor={() => 'rgba(147,204,255,0.35)'}
        linkDirectionalParticles={1}
        linkDirectionalParticleSpeed={0.003}
        onNodeClick={(node: any) => setSelectedNode(node)}
      />

      <div className="absolute bottom-6 left-1/2 transform -translate-x-1/2 z-10 w-[min(600px,calc(100vw-48px))] bg-surface-container-low/80 backdrop-blur-md border border-outline-variant/30 rounded-md p-3 flex flex-col gap-2 shadow-xl pointer-events-auto">
        <div className="flex justify-between items-center text-[10px] font-mono text-on-surface-variant uppercase tracking-widest pl-2">
          <span>Mock Memory Density</span>
          <button className="hover:text-white transition-colors" onClick={() => fgRef.current?.zoomToFit(1000)}>Reset Camera</button>
        </div>
        <div className="h-10 w-full px-2">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={timelineData}>
              <Bar dataKey="nodesCreated" radius={[2, 2, 0, 0]}>
                {timelineData.map((entry, index) => (
                  <Cell cursor="pointer" fill="#3f4851" key={`${entry.day}-${index}`} className="hover:fill-primary transition-all" />
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
                  style={{ color: selectedNode.color, borderColor: `${selectedNode.color}40`, backgroundColor: `${selectedNode.color}10` }}
                >
                  {selectedNode.type} Node
                </span>
                <h3 className="text-lg font-headline font-bold text-white">{selectedNode.name}</h3>
                <span className="text-[10px] font-mono text-on-surface-variant mt-1">ID: {selectedNode.id}</span>
              </div>
              <button onClick={() => setSelectedNode(null)} className="text-on-surface-variant hover:text-white mt-1">
                <span className="material-symbols-outlined text-[20px]">close</span>
              </button>
            </div>

            <div className="flex-1 overflow-y-auto p-4 flex flex-col gap-5 text-[11px] font-mono">
              <div>
                <span className="block text-on-surface-variant text-[10px] uppercase mb-1">Metadata</span>
                <div className="grid grid-cols-2 gap-2 bg-surface-lowest p-2 border border-outline-variant/10 rounded">
                  <div className="flex flex-col"><span className="text-on-surface-variant opacity-70">Phase</span> <span className="text-white">14 Mock</span></div>
                  <div className="flex flex-col"><span className="text-on-surface-variant opacity-70">Rank</span> <span className="text-white">{selectedNode.val}</span></div>
                  <div className="flex flex-col"><span className="text-on-surface-variant opacity-70">Type</span> <span className="text-white">{selectedNode.type}</span></div>
                  <div className="flex flex-col"><span className="text-on-surface-variant opacity-70">Links</span> <span className="text-white">{links.filter((link) => link.source === selectedNode.id || link.target === selectedNode.id).length}</span></div>
                </div>
              </div>

              <div>
                <span className="block text-on-surface-variant text-[10px] uppercase mb-1">Preview Summary</span>
                <div className="bg-surface-highest p-3 rounded border border-outline-variant/20 leading-relaxed text-on-surface shadow-[inset_0_0_10px_rgba(0,0,0,0.2)]">
                  {selectedNode.summary}
                </div>
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
