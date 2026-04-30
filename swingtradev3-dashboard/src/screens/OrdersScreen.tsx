import { useApprovalActions, useApprovals } from '@/hooks/useDashboardData';
import { cn } from '@/lib/utils';

function confidence(score: number) {
  if (score >= 8) return { label: 'HIGH', className: 'text-secondary border-secondary/20 bg-secondary/10' };
  if (score >= 6) return { label: 'MID', className: 'text-primary border-primary/20 bg-primary/10' };
  return { label: 'LOW', className: 'text-error border-error/20 bg-error/10' };
}

export function OrdersScreen() {
  const approvalsQuery = useApprovals();
  const { approve, reject } = useApprovalActions();
  const approvals = approvalsQuery.data ?? [];

  return (
    <div className="flex-1 overflow-y-auto p-4 lg:p-6 bg-surface relative">
      <div className="max-w-7xl mx-auto space-y-6">
        <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4 border-b border-outline-variant/15 pb-4">
          <div>
            <h1 className="text-2xl font-headline font-bold tracking-tight text-on-surface">Approval Queue</h1>
            <p className="text-[12px] font-mono text-on-surface-variant mt-1">
              {approvals.length} intents from Postgres execution memory
            </p>
          </div>
          <div className="text-[11px] font-mono text-on-surface-variant">
            {approvalsQuery.isFetching ? 'Refreshing' : 'Broker-truth read model'}
          </div>
        </div>

        <div className="bg-surface-container-low rounded-md flex flex-col overflow-hidden shadow-lg border border-outline-variant/15">
          <div className="grid grid-cols-12 gap-2 px-4 py-3 border-b border-outline-variant/15 text-[11px] font-headline font-bold text-on-surface-variant uppercase tracking-wider bg-surface-container">
            <div className="col-span-2">Ticker</div>
            <div className="col-span-1 text-right">Score</div>
            <div className="col-span-2 text-center">Confidence</div>
            <div className="col-span-3 text-right">Entry / Stop / Target</div>
            <div className="col-span-1 text-center">Sector</div>
            <div className="col-span-1 text-center">Status</div>
            <div className="col-span-2 text-right">Actions</div>
          </div>

          <div className="flex flex-col">
            {approvals.map((approval) => {
              const conf = confidence(approval.score);
              const disabled = approve.isPending || reject.isPending || approval.status === 'rejected';
              return (
                <div key={approval.approval_id} className="grid grid-cols-12 gap-2 px-4 py-3 border-b border-outline-variant/5 text-[12px] hover:bg-surface-highest/50 transition-colors">
                  <div className="col-span-2 flex items-center gap-2">
                    <span className="font-mono text-primary font-bold">{approval.ticker}</span>
                  </div>
                  <div className="col-span-1 flex items-center justify-end font-mono tabular-nums text-secondary font-bold">
                    {approval.score.toFixed(1)}
                  </div>
                  <div className="col-span-2 flex items-center justify-center">
                    <span className={cn("px-2 py-0.5 rounded-sm border text-[10px] font-mono tracking-wider font-semibold", conf.className)}>
                      {conf.label}
                    </span>
                  </div>
                  <div className="col-span-3 flex items-center justify-end font-mono tabular-nums text-on-surface-variant">
                    {approval.entry_zone.low.toFixed(2)}
                    <span className="opacity-40 mx-1.5">/</span>
                    {approval.stop_price.toFixed(2)}
                    <span className="opacity-40 mx-1.5">/</span>
                    <span className="text-secondary">{approval.target_price.toFixed(2)}</span>
                  </div>
                  <div className="col-span-1 flex items-center justify-center font-mono text-[11px] text-on-surface-variant opacity-80">
                    {approval.sector || 'UNK'}
                  </div>
                  <div className="col-span-1 flex items-center justify-center font-mono text-[11px] text-on-surface-variant">
                    {approval.status || 'pending'}
                  </div>
                  <div className="col-span-2 flex items-center justify-end gap-2">
                    <button
                      disabled={disabled}
                      onClick={() => reject.mutate(approval.approval_id)}
                      className="px-3 py-1 rounded border border-outline-variant/30 text-on-surface-variant hover:text-error hover:border-error/50 disabled:opacity-40 text-[11px] font-mono"
                    >
                      Reject
                    </button>
                    <button
                      disabled={disabled}
                      onClick={() => approve.mutate(approval.approval_id)}
                      className="px-3 py-1 rounded bg-primary text-on-primary-container hover:opacity-90 disabled:opacity-40 text-[11px] font-bold"
                    >
                      Approve
                    </button>
                  </div>
                  <div className="col-span-12 text-[11px] font-mono text-on-surface-variant pl-0 md:pl-0">
                    {approval.confidence_reasoning}
                  </div>
                </div>
              );
            })}

            {!approvals.length && (
              <div className="p-8 text-center text-[12px] font-mono text-on-surface-variant">
                {approvalsQuery.isLoading ? 'Loading approvals from Postgres...' : 'No approval intents are pending.'}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
