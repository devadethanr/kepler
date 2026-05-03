import React from 'react';
import { cn } from '@/lib/utils';
import { motion } from 'motion/react';
import { useDashboardEvents, useDashboardSnapshot } from '@/hooks/useDashboardData';
import { formatIstTime } from '@/lib/time';

const inr = new Intl.NumberFormat('en-IN', {
  style: 'currency',
  currency: 'INR',
  maximumFractionDigits: 0,
});

export function DashboardScreen() {
  const snapshotQuery = useDashboardSnapshot();
  const eventsQuery = useDashboardEvents(40);
  const snapshot = snapshotQuery.data;
  const portfolio = snapshot?.portfolio;
  const counts = snapshot?.counts ?? {};
  const events = eventsQuery.data ?? [];
  const pnl = portfolio?.total_pnl ?? 0;
  const pnlPct = portfolio?.total_invested ? (pnl / portfolio.total_invested) * 100 : 0;
  const session = snapshot?.session;
  const queuedApprovals = snapshot?.status_counts.approvals?.queued ?? 0;
  const approvalCount = counts.approvals ?? 0;
  const queuedPct = approvalCount > 0 ? (queuedApprovals / approvalCount) * 100 : 0;
  const eventRows = events.slice(-12).reverse().map((event) => ({
    time: formatIstTime(event.created_at),
    type: event.event_type.split('_')[0]?.toUpperCase() || 'EVT',
    color:
      event.event_type.includes('incident') || event.event_type.includes('fail')
        ? 'text-error'
        : event.event_type.includes('order') || event.event_type.includes('fill')
          ? 'text-secondary'
          : 'text-primary',
    msg: `${event.event_type} ${event.entity_type}:${event.entity_id}`,
    meta: event.source,
    bg: '',
  }));

  const containerVars: any = {
    hidden: { opacity: 0 },
    show: {
      opacity: 1,
      transition: { staggerChildren: 0.1 }
    }
  };

  const itemVars: any = {
    hidden: { opacity: 0, y: 10 },
    show: { opacity: 1, y: 0, transition: { type: 'spring', stiffness: 300, damping: 24 } }
  };

  return (
    <div className="flex-1 overflow-y-auto p-4 md:p-6 bg-surface">
      {/* Hero Tiles Grid */}
      <motion.div 
        variants={containerVars} initial="hidden" animate="show"
        className="grid grid-cols-1 xl:grid-cols-4 gap-4 mb-6"
      >
        
        {/* Live P&L */}
        <motion.div variants={itemVars} className="bg-surface-container-low p-4 rounded-md border border-outline-variant/15 relative overflow-hidden group hover:bg-surface-container transition-colors duration-300 flex flex-col justify-between min-h-[100px]">
          <div className="flex justify-between items-start mb-2">
            <span className="text-[11px] font-headline font-bold text-on-surface-variant uppercase tracking-wider">Live P&L</span>
            <span className="material-symbols-outlined text-secondary text-[16px]">trending_up</span>
          </div>
          <div className="flex items-baseline gap-2 z-10">
            <span className="text-2xl font-mono text-white">{inr.format(pnl)}</span>
            <span className={cn("text-[12px] font-mono flex items-center", pnl >= 0 ? "text-secondary" : "text-error")}>
              {pnl >= 0 ? '▲' : '▼'} {Math.abs(pnlPct).toFixed(2)}%
            </span>
          </div>
          <div className="absolute bottom-0 left-0 w-full h-8 opacity-30">
            <svg className="w-full h-full" preserveAspectRatio="none" viewBox="0 0 100 20">
              <path d="M0,20 L10,15 L20,18 L30,10 L40,12 L50,5 L60,8 L70,2 L80,6 L90,1 L100,5" fill="none" stroke="#42e09a" strokeWidth="2" vectorEffect="non-scaling-stroke"></path>
            </svg>
          </div>
        </motion.div>

        {/* Open Positions */}
        <motion.div variants={itemVars} className="bg-surface-container-low p-4 rounded-md border border-outline-variant/15 relative group hover:bg-surface-container transition-colors duration-300 flex flex-col justify-between min-h-[100px]">
          <div className="flex justify-between items-start mb-2">
            <span className="text-[11px] font-headline font-bold text-on-surface-variant uppercase tracking-wider">Open Positions</span>
            <span className="material-symbols-outlined text-primary text-[16px]">workspaces</span>
          </div>
          <div className="flex items-end justify-between">
            <div>
              <span className="text-2xl font-mono text-white">{counts.positions ?? 0}</span>
              <span className="block text-[11px] font-mono text-on-surface-variant mt-1">Exp: {inr.format(portfolio?.total_invested ?? 0)}</span>
            </div>
            <div className="w-8 h-8 rounded-full border-4 border-surface-highest border-t-primary border-r-secondary border-b-tertiary border-l-primary-container transform rotate-45"></div>
          </div>
        </motion.div>

        {/* Pending Approvals */}
        <motion.div variants={itemVars} className="bg-surface-container-low p-4 rounded-md border border-outline-variant/15 relative group hover:bg-surface-container transition-colors duration-300 flex flex-col justify-between min-h-[100px]">
          <div className="flex justify-between items-start mb-2">
            <span className="text-[11px] font-headline font-bold text-on-surface-variant uppercase tracking-wider">Pending Approvals</span>
            <span className="material-symbols-outlined text-tertiary text-[16px]">pending_actions</span>
          </div>
          <div className="flex items-end justify-between">
            <span className="text-2xl font-mono text-white">{counts.approvals ?? 0}</span>
            <div className="flex flex-col items-end">
              <span className="text-[11px] font-mono text-error">Queued: {queuedApprovals}</span>
              <div className="w-16 h-1 flex bg-surface-highest mt-1 rounded-full overflow-hidden">
                <div className="h-full bg-error" style={{ width: `${queuedPct}%` }}></div>
              </div>
            </div>
          </div>
        </motion.div>

        {/* Incidents */}
        <motion.div variants={itemVars} className="bg-surface-high p-4 rounded-md border-l-2 border-error shadow-[0_0_15px_rgba(255,180,171,0.05)] relative group hover:bg-surface-highest transition-colors duration-300 flex flex-col justify-between min-h-[100px]">
          <div className="flex justify-between items-start mb-2">
            <span className="text-[11px] font-headline font-bold text-error uppercase tracking-wider">Incidents</span>
            <span className="material-symbols-outlined text-error text-[16px]">warning</span>
          </div>
          <div className="flex items-center gap-3">
            <span className="text-2xl font-mono text-error">{counts.open_incidents ?? 0}</span>
            <div className="flex gap-1">
              <span className="px-1.5 py-0.5 bg-error-container text-on-error-container text-[10px] font-mono rounded uppercase">Open</span>
              <span className="px-1.5 py-0.5 bg-surface-lowest text-on-surface-variant text-[10px] font-mono rounded uppercase">DB: {snapshot?.latest_event_id ?? 0}</span>
            </div>
          </div>
        </motion.div>
        
      </motion.div>

      <motion.div 
        variants={containerVars} initial="hidden" animate="show"
        className="grid grid-cols-1 lg:grid-cols-12 gap-6"
      >
        
        {/* Main Data Matrix */}
        <motion.div variants={itemVars} className="lg:col-span-8 flex flex-col gap-6">
          
          {/* Session Phase Strip */}
          <section className="bg-surface-container-low rounded-md border border-outline-variant/15 p-4 flex flex-col">
            <div className="flex justify-between items-center mb-4">
              <h2 className="text-[12px] font-headline font-bold text-on-surface tracking-wide uppercase">Session Phase</h2>
              <div className="flex items-center gap-2 text-[11px] font-mono">
                <span className={session?.trading_day === false ? 'text-error' : 'text-primary'}>
                  {session?.day_label ?? '...'}
                </span>
                <span className="text-on-surface-variant">{session?.phase_label ?? 'Loading'}</span>
              </div>
            </div>
            <div className="relative w-full h-8 bg-surface-lowest rounded overflow-hidden flex border border-outline-variant/10">
              {(session?.segments ?? []).map((segment) => {
                const marketClosed =
                  segment.key === 'market_hours' && session?.market_status === 'closed';
                const label =
                  segment.active && segment.key === 'market_hours'
                    ? marketClosed
                      ? 'Market (Closed)'
                      : 'Market (Active)'
                    : segment.label;
                return (
                  <div
                    key={segment.key}
                    className={cn(
                      "h-full flex items-center justify-center border-r border-surface relative min-w-[34px]",
                      segment.active ? "bg-primary/10" : "bg-surface-high",
                      !session?.trading_day && segment.active ? "bg-error/10" : "",
                    )}
                    style={{ width: `${segment.width_pct}%` }}
                  >
                    <span
                      className={cn(
                        "text-[9px] md:text-[10px] font-mono truncate px-1",
                        segment.active
                          ? session?.trading_day === false
                            ? "text-error font-bold"
                            : "text-primary font-bold"
                          : "text-on-surface-variant",
                      )}
                    >
                      {label}
                    </span>
                    {segment.active && (
                      <>
                        <div
                          className="absolute top-0 w-0.5 h-full bg-secondary shadow-[0_0_8px_#42e09a]"
                          style={{ left: `${segment.elapsed_pct}%` }}
                        ></div>
                        <div
                          className="absolute -top-1 transform -translate-x-1/2 w-2 h-2 rounded-full bg-secondary"
                          style={{ left: `${segment.elapsed_pct}%` }}
                        ></div>
                      </>
                    )}
                  </div>
                );
              })}
            </div>
            {session?.holiday && (
              <div className="mt-2 text-[10px] font-mono text-error">{session.holiday}</div>
            )}
          </section>

          {/* Live Event Ticker */}
          <section className="bg-surface-container-low rounded-md border border-outline-variant/15 flex-1 flex flex-col overflow-hidden min-h-[300px]">
            <div className="flex justify-between items-center p-3 border-b border-outline-variant/15 bg-surface-lowest">
              <div className="flex items-center gap-2">
                <div className="w-2 h-2 rounded-full bg-secondary animate-pulse"></div>
                <h2 className="text-[12px] font-headline font-bold text-on-surface tracking-wide uppercase">Execution Ticker</h2>
              </div>
              <div className="flex gap-2">
                <button className="text-[10px] font-mono px-2 py-1 rounded border border-outline-variant/30 text-on-surface-variant hover:text-white transition-colors">Filter</button>
                <button className="text-[10px] font-mono px-2 py-1 rounded border border-outline-variant/30 text-on-surface-variant hover:text-white transition-colors">Pause</button>
              </div>
            </div>
            
            <div className="p-2 space-y-0.5 overflow-y-auto flex-1 font-mono text-[11px]">
              {(eventRows.length ? eventRows : [
	                { time: '--:--:--', type: 'SYS', color: 'text-on-surface-variant', msg: eventsQuery.isLoading ? 'Loading execution events' : eventsQuery.isError ? 'Execution events unavailable' : 'No execution events recorded', meta: 'DB', bg: '' },
              ]).map((log, i) => (
                <div key={i} className={cn("flex items-center gap-3 p-1.5 hover:bg-surface-container transition-colors rounded", log.bg)}>
                  <span className="text-on-surface-variant w-16 opacity-70">{log.time}</span>
                  <span className={cn("w-12", log.color)}>[{log.type}]</span>
                  <span className="flex-1 text-white">{log.msg}</span>
                  <span className="text-on-surface-variant">{log.meta}</span>
                </div>
              ))}
            </div>
          </section>

        </motion.div>

        {/* Action Rail */}
        <motion.div variants={itemVars} className="lg:col-span-4 flex flex-col gap-6">
          


          {/* System Status Card */}
          <section className="bg-surface-container-low rounded-md border border-outline-variant/15 p-4 flex-1">
            <h2 className="text-[12px] font-headline font-bold text-on-surface tracking-wide uppercase mb-4">Infrastructure</h2>
            <div className="space-y-4 font-mono text-[11px]">
              
              <div>
                <div className="flex justify-between items-center mb-1.5">
                  <span className="text-on-surface-variant">API Gateway</span>
                  <span className="text-secondary">99.9%</span>
                </div>
                <div className="w-full h-1 bg-surface-highest rounded-full overflow-hidden">
                  <div className="w-full h-full bg-secondary"></div>
                </div>
              </div>

              <div>
                <div className="flex justify-between items-center mb-1.5">
                  <span className="text-on-surface-variant">Matching Engine</span>
                  <span className="text-primary">1.2ms avg</span>
                </div>
                <div className="w-full h-1 bg-surface-highest rounded-full overflow-hidden">
                  <div className="w-[30%] h-full bg-primary"></div>
                </div>
              </div>

              <div>
                <div className="flex justify-between items-center mb-1.5">
                  <span className="text-on-surface-variant">DB Master Replicas</span>
                  <span className="text-white">Syncing...</span>
                </div>
                <div className="w-full h-1 bg-surface-highest rounded-full overflow-hidden">
                  <div className="w-[85%] h-full bg-tertiary"></div>
                </div>
              </div>

            </div>
          </section>

        </motion.div>
      </motion.div>
    </div>
  );
}
