import { useEffect, useState } from 'react';
import { useExecutionDashboard, useQuotes } from '@/hooks/useDashboardData';
import { formatIstTime } from '@/lib/time';
import { cn } from '@/lib/utils';

function payloadValue(row: Record<string, unknown>, key: string) {
  const payload = row.payload as Record<string, unknown> | undefined;
  return payload?.[key] ?? row[key] ?? '-';
}

function statusClass(status: unknown) {
  const value = String(status || '').toLowerCase();
  if (['open', 'armed', 'filled', 'completed', 'sync'].includes(value)) return 'text-secondary';
  if (['rejected', 'failed', 'error', 'reconcile_required'].includes(value)) return 'text-error';
  if (['submitted', 'queued', 'pending_arm', 'pending'].includes(value)) return 'text-primary';
  return 'text-on-surface-variant';
}

export function ExecutionScreen() {
  const executionQuery = useExecutionDashboard();
  const quotesQuery = useQuotes();
  const [now, setNow] = useState(new Date());
  const execution = executionQuery.data;
  const triggers = execution?.protective_triggers ?? [];
  const orders = execution?.broker_orders ?? [];
  const runs = execution?.reconciliation_runs ?? [];
  const quotes = quotesQuery.data?.quotes ?? [];

  useEffect(() => {
    const timer = setInterval(() => setNow(new Date()), 1000);
    return () => clearInterval(timer);
  }, []);

  return (
    <div className="flex-1 flex flex-col h-full overflow-hidden bg-surface relative">
      <div className="hidden md:flex h-12 bg-surface-container-low border-b border-surface-container/20 items-center justify-between px-6 shrink-0">
        <div className="flex items-center gap-4 text-[11px] font-mono tabular-nums text-slate-400">
          <span className="px-2 py-1 bg-surface rounded border border-outline-variant/20">
            IST {formatIstTime(now)}
          </span>
          <span className="px-2 py-1 bg-surface rounded border border-outline-variant/20 text-secondary">
            {executionQuery.isFetching ? 'SYNCING' : 'DB READY'}
          </span>
          <span className="px-2 py-1 bg-surface rounded border border-outline-variant/20">
            {orders.length} ORDERS
          </span>
          <span className="px-2 py-1 bg-surface-highest rounded text-primary border border-primary/30">
            {triggers.length} GTT
          </span>
        </div>
      </div>

      <div className="flex-1 p-4 overflow-hidden flex flex-col lg:flex-row gap-4">
        <div className="w-full lg:w-[65%] flex flex-col gap-4 overflow-hidden">
          <section className="flex-1 bg-surface-container-low rounded-md border border-outline-variant/15 flex flex-col overflow-hidden min-h-[300px]">
            <div className="h-10 border-b border-outline-variant/15 bg-surface-container flex items-center justify-between px-4 shrink-0">
              <h2 className="text-[12px] font-headline font-bold tracking-tight text-on-surface uppercase pr-4">Protection Board</h2>
              <span className="text-[10px] font-mono text-primary bg-primary/10 px-2 py-1 rounded border border-primary/20">{triggers.length} TRIGGERS</span>
            </div>
            <div className="flex-1 overflow-auto no-scrollbar p-2">
              <table className="w-full text-left border-collapse">
                <thead>
                  <tr className="text-[10px] font-headline text-on-surface-variant uppercase tracking-wider border-b border-outline-variant/10">
                    <th className="pb-2.5 pt-1 pl-3 font-semibold">Ticker</th>
                    <th className="pb-2.5 pt-1 font-semibold">Position</th>
                    <th className="pb-2.5 pt-1 font-semibold">Broker Status</th>
                    <th className="pb-2.5 pt-1 text-right pr-3 font-semibold">Trigger</th>
                  </tr>
                </thead>
                <tbody className="text-[11px] font-mono">
                  {triggers.map((trigger, index) => (
                    <tr key={String(trigger.protective_trigger_id || index)} className="border-b border-surface-lowest hover:bg-surface-highest/50 transition-colors">
                      <td className="py-2.5 pl-3 text-primary font-bold">{String(trigger.ticker || '-')}</td>
                      <td className="py-2.5 text-on-surface-variant">{String(trigger.position_id || '-')}</td>
                      <td className="py-2.5">
                        <span className={cn("flex items-center gap-1.5", statusClass(trigger.status))}>
                          <span className="w-1.5 h-1.5 rounded-full bg-current"></span>
                          {String(trigger.status || 'unknown').toUpperCase()}
                        </span>
                      </td>
                      <td className="py-2.5 text-right pr-3 text-on-surface-variant">
                        {String(payloadValue(trigger, 'gtt_id'))}
                      </td>
                    </tr>
                  ))}
                  {!triggers.length && (
	                    <tr><td colSpan={4} className="py-8 text-center text-on-surface-variant">{executionQuery.isLoading ? 'Loading protective triggers...' : executionQuery.isError ? 'Protective triggers unavailable.' : 'No protective triggers recorded.'}</td></tr>
                  )}
                </tbody>
              </table>
            </div>
          </section>

          <section className="flex-1 bg-surface-container-low rounded-md border border-outline-variant/15 flex flex-col overflow-hidden min-h-[250px]">
            <div className="h-10 border-b border-outline-variant/15 bg-surface-container flex items-center justify-between px-4 shrink-0">
              <h2 className="text-[12px] font-headline font-bold tracking-tight text-on-surface uppercase">Broker Order Ledger</h2>
              <span className="text-[10px] font-mono text-on-surface-variant">{orders.length} rows</span>
            </div>
            <div className="flex-1 overflow-auto no-scrollbar p-2 bg-surface">
              <div className="flex flex-col gap-[2px]">
                {orders.map((order, index) => (
                  <div key={String(order.broker_order_id || index)} className="grid grid-cols-6 text-[11px] font-mono py-1.5 px-3 hover:bg-surface-highest/30 rounded border border-transparent hover:border-outline-variant/20 transition-colors">
                    <span className="text-on-surface-variant">{String(order.broker_order_id || '-')}</span>
                    <span className="text-primary font-bold">{String(order.ticker || '-')}</span>
                    <span>{String(order.order_intent_id || '-')}</span>
                    <span className={statusClass(order.status)}>{String(order.status || '-').toUpperCase()}</span>
                    <span>{String(order.broker_tag || '-')}</span>
                    <span className="text-right">{String(order.source || 'broker')}</span>
                  </div>
                ))}
                {!orders.length && (
	                  <div className="p-8 text-center text-[12px] font-mono text-on-surface-variant">{executionQuery.isLoading ? 'Loading broker orders...' : executionQuery.isError ? 'Broker orders unavailable.' : 'No broker orders recorded.'}</div>
                )}
              </div>
            </div>
          </section>
        </div>

        <div className="w-full lg:w-[35%] flex flex-col gap-4 overflow-hidden">
          <section className="bg-surface-container-low rounded-md border border-outline-variant/15 flex flex-col overflow-hidden h-[300px] shrink-0">
            <div className="h-10 border-b border-outline-variant/15 bg-surface-container flex items-center justify-between px-4 shrink-0">
              <h2 className="text-[12px] font-headline font-bold tracking-tight text-on-surface uppercase">Quote Freshness</h2>
              <span className="text-[10px] font-mono text-on-surface-variant">{quotes.length} tracked</span>
            </div>
            <div className="flex-1 p-3 bg-surface overflow-auto flex flex-wrap content-start gap-1.5">
              {quotes.map((quote, index) => {
                const stale = Boolean(quote.stale);
                return (
                  <div key={String(quote.ticker || index)} className={cn("min-w-[64px] h-8 text-[10px] font-mono flex items-center justify-center rounded-sm font-bold shadow-sm", stale ? "bg-error text-[#690005]" : "bg-secondary text-[#00472c]")}>
                    {String(quote.ticker || '-')}
                  </div>
                );
              })}
	              {!quotes.length && <span className="text-[12px] font-mono text-on-surface-variant">{quotesQuery.isLoading ? 'Loading quotes...' : quotesQuery.isError ? 'Quotes unavailable.' : 'No quote-derived positions.'}</span>}
            </div>
          </section>

          <section className="flex-1 bg-surface-container-low rounded-md border border-outline-variant/15 flex flex-col overflow-hidden">
            <div className="h-10 border-b border-outline-variant/15 bg-surface-container flex items-center justify-between px-4 shrink-0">
              <h2 className="text-[12px] font-headline font-bold tracking-tight text-on-surface uppercase pr-4">Recon Stream</h2>
            </div>
            <div className="flex-1 overflow-auto no-scrollbar p-3 bg-surface">
              <div className="flex flex-col gap-2">
                {runs.map((run, index) => (
                  <div key={String(run.reconciliation_run_id || index)} className="flex text-[10px] font-mono p-2 bg-surface-highest/20 border border-outline-variant/10 rounded items-center gap-2.5">
                    <span className={cn("material-symbols-outlined text-[16px]", statusClass(run.status))}>sync</span>
                    <span className="w-24 text-on-surface-variant font-medium">{String(run.reconciliation_run_id || '-')}</span>
                    <span className="flex-1 text-on-surface opacity-90">{String((run.payload as Record<string, unknown> | undefined)?.summary || 'broker reconciliation')}</span>
                    <span className={cn("font-bold tracking-wider", statusClass(run.status))}>{String(run.status || '-').toUpperCase()}</span>
                  </div>
                ))}
	                {!runs.length && <div className="text-[12px] font-mono text-on-surface-variant">{executionQuery.isLoading ? 'Loading reconciliation runs...' : executionQuery.isError ? 'Reconciliation runs unavailable.' : 'No reconciliation runs recorded.'}</div>}
              </div>
            </div>
          </section>
        </div>
      </div>
    </div>
  );
}
