import { motion } from 'motion/react';
import { useExecutionDashboard, useSafety } from '@/hooks/useDashboardData';
import { cn } from '@/lib/utils';

export function IncidentsScreen() {
  const executionQuery = useExecutionDashboard();
  const safetyQuery = useSafety();
  const incidents = executionQuery.data?.incidents ?? [];
  const safety = safetyQuery.data;
  const block = safety?.block_new_entries as { active?: boolean; reasons?: string[] } | undefined;

  return (
    <div className="flex-1 p-4 md:p-6 bg-surface overflow-y-auto">
      <div className="flex flex-col md:flex-row justify-between items-start md:items-end mb-8 gap-4">
        <div>
          <h1 className="flex items-center gap-3 text-2xl font-headline font-bold text-on-surface tracking-wider uppercase">
            <span className="material-symbols-outlined text-[28px] text-error">emergency</span>
            Incident Response
          </h1>
          <p className="text-[12px] font-mono text-on-surface-variant mt-1">Failure incidents and kill-switch state from Postgres.</p>
        </div>
        <div className={cn("px-4 py-2 rounded border text-[11px] font-bold tracking-widest uppercase", block?.active ? "bg-error/20 text-error border-error/50" : "bg-secondary/10 text-secondary border-secondary/40")}>
          {block?.active ? 'Entries Blocked' : 'No Entry Block'}
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        <div className="lg:col-span-5 flex flex-col gap-3">
          <h2 className="text-[12px] font-mono text-on-surface-variant mb-2">Active Tracker</h2>
          {incidents.map((incident, i) => {
            const payload = incident.payload as Record<string, unknown> | undefined;
            const status = String(incident.status || payload?.status || 'open');
            const severity = String(incident.severity || payload?.severity || 'warning');
            return (
              <motion.div
                initial={{ x: -20, opacity: 0 }}
                animate={{ x: 0, opacity: 1 }}
                transition={{ delay: i * 0.05 }}
                key={String(incident.incident_id || i)}
                className={cn(
                  "p-4 rounded border hover:bg-surface-high transition-colors",
                  status === 'open' && severity === 'critical'
                    ? 'bg-error/10 border-error/50'
                    : status === 'open'
                      ? 'bg-surface-container-low border-tertiary/30'
                      : 'bg-surface-lowest border-outline-variant/20 opacity-70',
                )}
              >
                <div className="flex justify-between items-center mb-2 text-[10px] font-mono">
                  <span className={cn("px-2 py-0.5 rounded text-surface-lowest uppercase font-bold", severity === 'critical' ? 'bg-error' : 'bg-tertiary text-surface-lowest')}>{severity}</span>
                  <span className="text-on-surface-variant">{String(incident.incident_id || '-')}</span>
                </div>
                <h3 className={cn("text-[13px] font-headline font-bold mb-3", status === 'open' ? 'text-white' : 'text-on-surface-variant')}>
                  {String(payload?.reason || payload?.detail || payload?.summary || 'Execution incident')}
                </h3>
                <div className="flex justify-between items-center text-[11px] font-mono">
                  <span className="text-on-surface-variant">Source: {String(payload?.source || '-')}</span>
                  <span className={status === 'open' ? 'text-error' : 'text-secondary'}>{status.toUpperCase()}</span>
                </div>
              </motion.div>
            );
          })}
          {!incidents.length && <div className="p-8 text-center text-[12px] font-mono text-on-surface-variant border border-outline-variant/15 rounded">No incidents recorded.</div>}
        </div>

        <div className="lg:col-span-7 bg-surface-container-low border border-outline-variant/15 rounded flex flex-col overflow-hidden min-h-[400px]">
          <div className="bg-error/10 border-b border-error/20 p-4">
            <span className="text-error text-[10px] font-mono font-bold tracking-widest uppercase mb-1 block">Kill Switch Reasons</span>
            <h2 className="text-xl font-headline font-bold text-white mb-2">{block?.active ? 'New entries are blocked' : 'No active block'}</h2>
            <p className="text-[12px] font-mono text-on-surface-variant">{block?.reasons?.join(', ') || 'The worker has not persisted an active block reason.'}</p>
          </div>
          <div className="p-4 flex-1 overflow-y-auto font-mono text-[11px] space-y-4">
            {Object.entries((safety?.kill_switches as Record<string, unknown> | undefined) ?? {}).map(([name, value]) => {
              const item = value as { active?: boolean };
              return (
                <div key={name} className="flex gap-4">
                  <div className={item.active ? 'w-20 text-error' : 'w-20 text-secondary'}>{item.active ? 'ACTIVE' : 'OK'}</div>
                  <div className="flex-1 text-white border-l border-outline-variant/30 pl-4">{name}</div>
                </div>
              );
            })}
          </div>
        </div>
      </div>
    </div>
  );
}
