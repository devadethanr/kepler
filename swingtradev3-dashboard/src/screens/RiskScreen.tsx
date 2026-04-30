import { useDashboardSnapshot, useSafety } from '@/hooks/useDashboardData';
import { cn } from '@/lib/utils';

const inr = new Intl.NumberFormat('en-IN', {
  style: 'currency',
  currency: 'INR',
  maximumFractionDigits: 0,
});

function ringOffset(pct: number) {
  return 314 - (Math.max(0, Math.min(pct, 100)) / 100) * 314;
}

export function RiskScreen() {
  const snapshotQuery = useDashboardSnapshot();
  const safetyQuery = useSafety();
  const portfolio = snapshotQuery.data?.portfolio;
  const exposure = portfolio?.total_invested ?? 0;
  const cash = portfolio?.cash_inr ?? 0;
  const grossPct = cash + exposure > 0 ? (exposure / (cash + exposure)) * 100 : 0;
  const drawdownPct = Math.abs(portfolio?.drawdown_pct ?? 0) * 100;
  const weeklyLossPct = Math.abs(portfolio?.weekly_loss_pct ?? 0) * 100;
  const killSwitches = safetyQuery.data?.kill_switches as Record<string, { active?: boolean }> | undefined;
  const activeSwitches = Object.values(killSwitches ?? {}).filter((value) => value?.active).length;
  const sectors = Object.entries(portfolio?.sector_exposure ?? {}).sort((a, b) => b[1] - a[1]);

  return (
    <div className="flex-1 p-4 md:p-6 bg-surface overflow-y-auto">
      <div className="mb-6 border-b border-outline-variant/15 pb-4 flex justify-between items-end">
        <div>
          <h1 className="text-2xl font-headline font-bold text-on-surface tracking-wider uppercase text-error">Global Risk Dashboard</h1>
          <p className="text-[12px] font-mono text-on-surface-variant mt-1">Exposure, drawdown, loss controls, and kill-switch state.</p>
        </div>
        <div className="text-right">
          <div className="text-[10px] font-mono text-on-surface-variant">Total Exposure</div>
          <div className="text-2xl font-mono text-error font-bold">{inr.format(exposure)}</div>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-6">
        {[
          { label: 'Gross Exp.', pct: grossPct, detail: 'Capital deployed', color: 'text-error' },
          { label: 'Drawdown', pct: drawdownPct, detail: 'Account drawdown', color: 'text-primary' },
          { label: 'Weekly Loss', pct: weeklyLossPct, detail: `${activeSwitches} switches active`, color: activeSwitches ? 'text-error' : 'text-secondary' },
        ].map((metric) => (
          <div key={metric.label} className="bg-surface-container-low border border-outline-variant/20 rounded p-5 flex flex-col items-center justify-center relative overflow-hidden">
            <span className="text-[10px] font-headline font-bold text-on-surface-variant uppercase tracking-widest mb-4 absolute top-4 left-4">{metric.label}</span>
            <div className="relative w-32 h-32 flex items-center justify-center">
              <svg className="w-full h-full transform -rotate-90">
                <circle cx="64" cy="64" r="50" fill="none" stroke="currentColor" strokeWidth="8" className="text-surface-highest" />
                <circle cx="64" cy="64" r="50" fill="none" stroke="currentColor" strokeWidth="8" strokeDasharray="314" strokeDashoffset={ringOffset(metric.pct)} className={metric.color} />
              </svg>
              <span className="absolute text-xl font-mono select-none text-white font-bold">{metric.pct.toFixed(0)}%</span>
            </div>
            <span className={cn("text-[11px] font-mono mt-4", metric.color)}>{metric.detail}</span>
          </div>
        ))}
      </div>

      <div className="bg-surface-container-low border border-outline-variant/20 rounded p-5">
        <h2 className="text-[12px] font-headline font-bold text-on-surface uppercase tracking-wider mb-6">Sector Exposure</h2>
        <div className="space-y-4">
          {sectors.map(([name, value]) => {
            const pct = exposure > 0 ? (value / exposure) * 100 : 0;
            return (
              <div key={name}>
                <div className="flex justify-between text-[11px] font-mono mb-1.5">
                  <span className="text-on-surface text-white">{name}</span>
                  <span className="text-on-surface-variant">{inr.format(value)}</span>
                </div>
                <div className="w-full bg-surface-highest h-2 rounded-full overflow-hidden">
                  <div className="h-full rounded-full bg-primary transition-all duration-1000" style={{ width: `${pct}%` }}></div>
                </div>
              </div>
            );
          })}
          {!sectors.length && <div className="text-[12px] font-mono text-on-surface-variant">No sector exposure recorded.</div>}
        </div>
      </div>
    </div>
  );
}
