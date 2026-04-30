import React, { useState, useEffect } from 'react';
import { cn } from '@/lib/utils';

// Live Mock State Generator
function useTelemetrySimulation() {
  const [ticks, setTicks] = useState(0);

  useEffect(() => {
    const timer = setInterval(() => setTicks(t => t + 1), 1500);
    return () => clearInterval(timer);
  }, []);

  const parseActivity = (phaseOffset: number, activeMsgs: string[], idleMsgs: string[]) => {
    const isActive = (ticks + phaseOffset) % 5 < 3; 
    const msg = isActive 
        ? activeMsgs[Math.floor(Math.random() * activeMsgs.length)] 
        : idleMsgs[Math.floor(Math.random() * idleMsgs.length)];
    return { active: isActive, msg };
  };

  return { ticks, parseActivity };
}

export function SystemTelemetryFlow() {
  const { parseActivity } = useTelemetrySimulation();

  // Ingress
  const kiteStream = parseActivity(0, ['Parsing tick quotes', 'Order update Rx', 'WS Ping OK (12ms)'], ['WS Listening', 'Idle (Heartbeat)']);
  const newsAgg = parseActivity(2, ['Tavily Search: Index', 'DDGS Scanning'], ['Aggregator Idle']);
  const opControl = parseActivity(4, ['Telegram Polling', 'REST API Serviced'], ['Awaiting Commands']);

  // Slow Brain
  const regimeScanner = parseActivity(1, ['Scanning Nifty 200', 'Regime Update'], ['Awaiting Next Run']);
  const thesisAgent = parseActivity(3, ['Deliberating Setup', 'Evidence Assembly'], ['Staging Intents']);
  const skepticAgent = parseActivity(0, ['Critiquing Trade', 'Sizing Too Large!'], ['Awaiting Thesis']);
  const sessionPlanner = parseActivity(2, ['Building Plan', 'Capital Lock'], ['Plan Ready']);

  // Fast Brain
  const execCoord = parseActivity(2, ['Routing orders', 'Reducing Streams'], ['Coordinator Idle']);
  const reconciler = parseActivity(1, ['Syncing Positions', 'Detecting Drift'], ['Reconciliation OK']);
  const exceptionAnalyst = parseActivity(4, ['Validating Bounds', 'Margin Check'], ['No Incidents']);
  const riskGuard = parseActivity(0, ['Enforcing D-Limit', 'P&L Verify'], ['Bounds OK']);

  // Memory
  const kgStore = parseActivity(3, ['Embeddings Updated', 'Markdown Built'], ['Vector Index OK']);
  const pgDb = parseActivity(0, ['Writing exec_event', 'Updating projection'], ['DB Sync (4ms)']);
  const sessionDb = parseActivity(4, ['Flushing Context', 'Reading Ticket'], ['Cache Clear']);

  // Policy / Learning
  const reviewer = parseActivity(4, ['Generating lessons', 'Trade eval'], ['Awaiting Close']);
  const policyGov = parseActivity(2, ['Bound Overlays', 'trading_enabled=1'], ['Policy Enforced']);

  // Optimized Edge Networking without tangles
  const edges = [
    // Ingress bounds
    { x1: 50, y1: 12, x2: 70, y2: 38, active: kiteStream.active || execCoord.active, color: "text-secondary" }, // Kite -> Exec
    { x1: 50, y1: 12, x2: 85, y2: 38, active: kiteStream.active || reconciler.active, color: "text-secondary" }, // Kite -> Recon
    { x1: 15, y1: 12, x2: 15, y2: 38, active: newsAgg.active, color: "text-tertiary" }, // News -> Regime
    { x1: 85, y1: 12, x2: 65, y2: 85, active: opControl.active, color: "text-error", curveVertical: true }, // Auth -> Policy

    // Slow Brain connections
    { x1: 15, y1: 38, x2: 30, y2: 38, active: regimeScanner.active, color: "text-primary" }, // Regime -> Thesis
    { x1: 30, y1: 62, x2: 30, y2: 38, active: skepticAgent.active, color: "text-primary", straight: true }, // Skeptic -> Thesis
    { x1: 30, y1: 38, x2: 50, y2: 38, active: thesisAgent.active, color: "text-primary" }, // Thesis -> KG
    { x1: 30, y1: 38, x2: 15, y2: 62, active: thesisAgent.active, color: "text-primary" }, // Thesis -> Planner
    { x1: 15, y1: 62, x2: 50, y2: 62, active: sessionPlanner.active, color: "text-primary" }, // Planner -> DB
    { x1: 15, y1: 62, x2: 50, y2: 85, active: sessionPlanner.active, color: "text-primary" }, // Planner -> Session

    // Fast Brain connections
    { x1: 70, y1: 38, x2: 85, y2: 62, active: execCoord.active, color: "text-secondary" }, // Exec -> RiskGuard
    { x1: 70, y1: 62, x2: 70, y2: 38, active: exceptionAnalyst.active, color: "text-secondary", straight: true }, // Exception -> Exec
    { x1: 70, y1: 62, x2: 65, y2: 85, active: exceptionAnalyst.active, color: "text-secondary" }, // Exception -> Policy
    { x1: 85, y1: 38, x2: 50, y2: 62, active: reconciler.active, color: "text-secondary" }, // Recon -> Postgres
    
    // Core DB interactions
    { x1: 50, y1: 62, x2: 70, y2: 38, active: pgDb.active, color: "text-white" }, // Postgres -> ExecCoord
    { x1: 50, y1: 62, x2: 35, y2: 85, active: pgDb.active, color: "text-white" }, // Postgres -> Reviewer
    { x1: 35, y1: 85, x2: 50, y2: 38, active: reviewer.active, color: "text-tertiary" }, // Reviewer -> KG
    { x1: 65, y1: 85, x2: 50, y2: 62, active: policyGov.active, color: "text-error" }, // Policy -> Postgres
  ];

  return (
    <div className="w-full h-full relative overflow-auto no-scrollbar">
      {/* Container ensures grid min-width for panning if viewport is small */}
      <div className="w-[1200px] h-[750px] relative mx-auto mt-4 mb-4 select-none">
         
         {/* Background Connectors */}
         <svg className="absolute inset-0 w-full h-full pointer-events-none z-0" viewBox="0 0 100 100" preserveAspectRatio="none">
           {edges.map((edge, i) => (
             <FlowEdge key={i} {...edge} />
           ))}
         </svg>

         {/* --- Layer A: Ingress --- */}
         <Node top={12} left={15} label="News & Macro" type="ingress" icon="rss_feed" color="text-tertiary" activity={newsAgg} />
         <Node top={12} left={50} label="Kite Stream" type="ingress" icon="language" color="text-secondary" activity={kiteStream} />
         <Node top={12} left={85} label="Operator Auth" type="ingress" icon="admin_panel_settings" color="text-error" activity={opControl} />

         {/* --- Layer C: Slow Brain --- */}
         <Node top={38} left={15} label="Regime Scanner" type="worker" icon="radar" color="text-primary" activity={regimeScanner} />
         <Node top={38} left={30} label="ThesisAgent" type="agent" icon="psychology" color="text-primary" activity={thesisAgent} />
         <Node top={62} left={30} label="SkepticAgent" type="agent" icon="policy" color="text-primary" activity={skepticAgent} />
         <Node top={62} left={15} label="Session Planner" type="worker" icon="edit_document" color="text-primary" activity={sessionPlanner} />

         {/* --- Layer B: Memory Core --- */}
         <Node top={38} left={50} label="Knowledge Graph" type="db" icon="hub" color="text-white" activity={kgStore} />
         <Node top={62} left={50} label="PostgreSQL Core" type="db" icon="database" color="text-white" activity={pgDb} />
         <Node top={85} left={50} label="Session Mem" type="db" icon="memory" color="text-on-surface-variant" activity={sessionDb} />

         {/* --- Layer D: Fast Brain --- */}
         <Node top={38} left={70} label="Exec Coordinator" type="worker" icon="bolt" color="text-secondary" activity={execCoord} />
         <Node top={38} left={85} label="Reconciler" type="worker" icon="sync_alt" color="text-secondary" activity={reconciler} />
         <Node top={62} left={70} label="Exception Analyst" type="agent" icon="health_and_safety" color="text-secondary" activity={exceptionAnalyst} />
         <Node top={62} left={85} label="Risk Guard" type="worker" icon="shield" color="text-secondary" activity={riskGuard} />

         {/* --- Layer E/F: Bounds & Learning --- */}
         <Node top={85} left={35} label="Post-Trade Review" type="worker" icon="school" color="text-tertiary" activity={reviewer} />
         <Node top={85} left={65} label="Policy Governor" type="worker" icon="gavel" color="text-error" activity={policyGov} />

         {/* Context Layer Labels */}
         <div className="absolute top-[2%] left-[46%] text-[9px] font-mono text-on-surface-variant/40 uppercase tracking-[0.4em] pointer-events-none">Phase A: Ingress</div>
         <div className="absolute top-[20%] left-[17%] text-[9px] font-mono text-primary/30 uppercase tracking-[0.4em] pointer-events-none">Phase C: Slow Brain</div>
         <div className="absolute top-[20%] left-[70%] text-[9px] font-mono text-secondary/30 uppercase tracking-[0.4em] pointer-events-none">Phase D: Fast Brain</div>
         <div className="absolute top-[96%] left-[43%] text-[9px] font-mono text-white/20 uppercase tracking-[0.4em] pointer-events-none">Phase E/F: Logic & Policy</div>
      </div>
    </div>
  );
}

// ------ Styled Custom Shapes & Edges ------ //

function FlowEdge({ x1, y1, x2, y2, active, color, straight, curveVertical }: any) {
  let pathData = '';
  
  if (straight) {
    pathData = `M ${x1} ${y1} L ${x2} ${y2}`;
  } else if (curveVertical) {
    // S-curve favoring vertical travel
    const mx1 = x1;
    const my1 = y1 + (y2 - y1) * 0.5;
    const mx2 = x2;
    const my2 = y1 + (y2 - y1) * 0.5;
    pathData = `M ${x1} ${y1} C ${mx1} ${my1}, ${mx2} ${my2}, ${x2} ${y2}`;
  } else {
    // S-curve favoring horizontal travel
    const mx1 = x1 + (x2 - x1) * 0.5;
    const my1 = y1;
    const mx2 = x1 + (x2 - x1) * 0.5;
    const my2 = y2;
    pathData = `M ${x1} ${y1} C ${mx1} ${my1}, ${mx2} ${my2}, ${x2} ${y2}`;
  }

  // Lookup internal color for stroke
  const strokeColorMap: any = {
    'text-primary': '147, 204, 255',
    'text-secondary': '66, 224, 154',
    'text-tertiary': '241, 175, 255',
    'text-error': '255, 180, 171',
    'text-white': '255, 255, 255'
  };
  const rgb = strokeColorMap[color] || '255, 255, 255';

  return (
    <>
       <path d={pathData} stroke="var(--color-outline-variant)" strokeOpacity="0.15" fill="none" strokeWidth="0.15" />
       {active && (
         <path 
           d={pathData} 
           stroke={`rgba(${rgb}, 0.8)`}
           fill="none" 
           strokeWidth="0.3"
           className="animate-data-flow"
           style={{ filter: `drop-shadow(0 0 1px rgba(${rgb}, 0.6))` }}
         />
       )}
    </>
  );
}

function Node({ top, left, label, icon, color, activity, type }: any) {
  const { active, msg } = activity;

  // Icon Housing Shapes based on Architecture Layer
  const shapeClass = 
    type === 'agent' ? "rounded-full" : 
    type === 'worker' ? "rounded-tl-[12px] rounded-br-[12px]" : 
    type === 'db' ? "rounded-b-[16px] rounded-t-[4px] border-b-4 border-t" : 
    "rounded-[8px]"; // ingress

  // Map to safely implement specific border and background colors
  const colorMap: any = {
    'text-primary': { bg: 'bg-[#93ccff]', border: 'border-[#93ccff]' },
    'text-secondary': { bg: 'bg-[#42e09a]', border: 'border-[#42e09a]' },
    'text-tertiary': { bg: 'bg-[#f1afff]', border: 'border-[#f1afff]' },
    'text-error': { bg: 'bg-[#ffb4ab]', border: 'border-[#ffb4ab]' },
    'text-white': { bg: 'bg-white', border: 'border-white/50' },
    'text-on-surface-variant': { bg: 'bg-[#bec7d3]', border: 'border-[#bec7d3]/50' },
  };
  
  const c = colorMap[color] || colorMap['text-white'];
  const isActiveStyle = active ? `${c.border}` : "border-white/5";

  return (
    <div 
       className="absolute z-10 w-[140px] group" 
       style={{ top: `${top}%`, left: `${left}%`, transform: 'translate(-50%, -50%)' }}
    >
      <div className={cn(
        "flex flex-col items-center bg-[#121317]/95 backdrop-blur-xl border overflow-hidden p-3 transition-colors duration-500 rounded-xl",
        isActiveStyle,
        active ? "shadow-[0_0_20px_rgba(0,0,0,0.8)] bg-[#1a1c24]/95" : "shadow-lg border-outline-variant/15"
      )}>
        
        {/* Isolated Icon Container corresponding to component Type */}
        <div className={cn(
          "w-9 h-9 mb-2.5 flex items-center justify-center border bg-[#0a0b0f] transition-all duration-300 z-10", 
          shapeClass, 
          isActiveStyle
        )}>
          <span className={cn(
            "material-symbols-outlined text-[18px] transition-all", 
            color, 
            active ? "animate-pulse drop-shadow-md opacity-100" : "opacity-50"
          )}>{icon}</span>
        </div>

        {/* Node Label */}
        <span className={cn(
            "text-[10px] uppercase font-bold tracking-wider text-center leading-[12px] mb-3 h-[24px] flex items-center justify-center z-10",
            active ? "text-white" : "text-white/70"
        )}>
          {label}
        </span>

        {/* Diagnostic Activity Track */}
        <div className={cn(
            "w-full rounded-[4px] px-2 py-1.5 flex items-center gap-1.5 transition-all duration-300 z-10",
            active ? "bg-[#050505] border border-outline-variant/30" : "bg-black/30 border border-transparent"
        )}>
          <div className={cn(
              "w-1.5 h-1.5 shrink-0 rounded-full transition-all duration-300", 
              active ? `${c.bg} animate-pulse shadow-sm` : "bg-outline-variant/30"
          )} />
          <span className={cn(
              "text-[8px] font-mono truncate transition-all",
              active ? "text-white" : "text-outline-variant opacity-60"
          )}>{msg}</span>
        </div>
        
        {/* Subtle internal atmospheric glow if active */}
        {active && (
          <div className="absolute inset-0 bg-gradient-to-b from-white/5 to-transparent pointer-events-none rounded-xl" />
        )}

      </div>
    </div>
  );
}
