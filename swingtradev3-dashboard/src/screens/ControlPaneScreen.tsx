import { useState } from 'react';
import { api } from '@/lib/api';
import { useControlActions, useSafety, useScanStatus } from '@/hooks/useDashboardData';
import { cn } from '@/lib/utils';

function ToggleRow({
  label,
  enabled,
  onClick,
  disabled,
}: {
  label: string;
  enabled: boolean;
  onClick: () => void;
  disabled?: boolean;
}) {
  return (
    <div className="flex justify-between items-center bg-[#1a1c23] p-3 rounded border border-outline-variant/20">
      <span className="text-[13px] font-bold text-white">{label}</span>
      <button
        disabled={disabled}
        onClick={onClick}
        className={cn(
          "w-10 h-5 rounded-full relative flex items-center transition-colors disabled:opacity-50",
          enabled ? "bg-secondary/30" : "bg-surface-highest border border-outline-variant/50",
        )}
      >
        <span className={cn("w-4 h-4 rounded-full absolute transition-all", enabled ? "bg-secondary right-0.5 shadow-[0_0_10px_#42e09a]" : "bg-outline left-0.5")}></span>
      </button>
    </div>
  );
}

export function ControlPaneScreen() {
  const safetyQuery = useSafety();
  const scanStatusQuery = useScanStatus();
  const actions = useControlActions();
  const [flattenConfirm, setFlattenConfirm] = useState('');
  const [reason, setReason] = useState('operator dashboard update');
  const safety = safetyQuery.data;
  const controls = safety?.operator_controls as
    | {
        trading_enabled?: { enabled?: boolean };
        new_entries_enabled?: { enabled?: boolean };
        exit_only_mode?: { enabled?: boolean };
        flatten_requested?: unknown;
      }
    | undefined;
  const tradingEnabled = controls?.trading_enabled?.enabled ?? false;
  const entriesEnabled = controls?.new_entries_enabled?.enabled ?? false;
  const exitOnly = controls?.exit_only_mode?.enabled ?? false;
  const block = safety?.block_new_entries as { active?: boolean; reasons?: string[] } | undefined;
  const controlsReady = safetyQuery.isSuccess && Boolean(controls) && reason.trim().length > 0;

  return (
    <div className="flex-1 p-4 md:p-6 bg-surface overflow-y-auto w-full text-on-surface">
      <div className="mb-6 border-b border-outline-variant/15 pb-4">
        <h1 className="text-2xl font-headline font-bold text-white tracking-wider uppercase flex items-center gap-3">
          <span className="material-symbols-outlined text-[28px] text-primary">tune</span>
          Control Pane
        </h1>
        <p className="text-[12px] font-mono text-on-surface-variant mt-1">Operator writes are queued through control flags; the dashboard never places broker orders directly.</p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        <div className="lg:col-span-4 flex flex-col gap-6">
          <section className="bg-surface-container-low border border-error/20 rounded-md p-5 flex flex-col gap-4 relative overflow-hidden">
            <div className="absolute top-0 left-0 w-full h-1 bg-error"></div>
            <h2 className="text-[14px] font-headline font-bold text-error tracking-widest uppercase flex items-center gap-2">
              <span className="material-symbols-outlined">warning</span> Intervention
            </h2>
            <input
              value={reason}
              onChange={(event) => setReason(event.target.value)}
              className="bg-surface border border-outline-variant/30 rounded px-3 py-2 text-[12px] font-mono text-white placeholder-on-surface-variant/50 focus:outline-none focus:border-primary"
              placeholder="Reason"
            />
            <div className="flex flex-col gap-3">
              <ToggleRow
                label="Trading Enabled"
                enabled={tradingEnabled}
                disabled={!controlsReady || actions.updateMode.isPending}
                onClick={() => actions.updateMode.mutate({ reason, trading_enabled: !tradingEnabled })}
              />
              <ToggleRow
                label="New Entries Enabled"
                enabled={entriesEnabled}
                disabled={!controlsReady || actions.updateMode.isPending}
                onClick={() => actions.updateMode.mutate({ reason, new_entries_enabled: !entriesEnabled })}
              />
              <ToggleRow
                label="Exit-Only Mode"
                enabled={exitOnly}
                disabled={!controlsReady || actions.updateMode.isPending}
                onClick={() => actions.updateMode.mutate({ reason, exit_only_mode: !exitOnly })}
              />
            </div>

            <div className="mt-2 pt-4 border-t border-error/20 z-10 space-y-3">
              <input
                value={flattenConfirm}
                onChange={(event) => setFlattenConfirm(event.target.value)}
                className="w-full bg-surface border border-outline-variant/30 rounded px-3 py-2 text-[12px] font-mono text-white placeholder-on-surface-variant/50 focus:outline-none focus:border-error"
                placeholder="Type FLATTEN to queue flatten-all"
              />
              <button
                disabled={flattenConfirm !== 'FLATTEN' || !controlsReady || actions.flatten.isPending}
                onClick={() => actions.flatten.mutate({ reason })}
                className="w-full bg-[#121317] border border-error text-error py-3 rounded font-bold text-[13px] tracking-widest hover:bg-error-container hover:text-on-error-container transition-colors disabled:opacity-40"
              >
                FLATTEN ALL
              </button>
            </div>
          </section>
        </div>

        <div className="lg:col-span-8 flex flex-col gap-6">
          <section className="bg-surface-container-low border border-outline-variant/15 rounded-md overflow-hidden">
            <div className="p-5 border-b border-outline-variant/15 bg-surface-highest/50 flex justify-between items-center">
              <div className="flex flex-col">
                <h2 className="text-[14px] font-headline font-bold text-tertiary tracking-widest uppercase flex items-center gap-2">
                  <span className="material-symbols-outlined">security</span> Safety State
                </h2>
                <span className="text-[11px] font-mono text-on-surface-variant mt-1">
                  {safetyQuery.isLoading
                    ? 'Loading safety state'
                    : safetyQuery.isError
                      ? 'Safety state unavailable'
                      : block?.active
                        ? block.reasons?.join(', ')
                        : 'No block-new-entries flag active'}
                </span>
              </div>
              <button
                disabled={!block?.active || actions.clearBlock.isPending}
                onClick={() => actions.clearBlock.mutate({ reason, source: 'dashboard' })}
                className="bg-surface border border-outline-variant/30 hover:bg-surface-high transition-colors px-3 py-1.5 rounded text-[11px] font-mono text-white disabled:opacity-40"
              >
                CLEAR BLOCK
              </button>
            </div>
            <div className="p-5 grid grid-cols-1 md:grid-cols-2 gap-4 font-mono text-[12px]">
              {Object.entries((safety?.kill_switches as Record<string, { active?: boolean }> | undefined) ?? {}).map(([key, value]) => (
                <div key={key} className="flex items-center justify-between bg-surface p-3 rounded border border-outline-variant/20">
                  <span>{key}</span>
                  <span className={value.active ? 'text-error' : 'text-secondary'}>{value.active ? 'ACTIVE' : 'OK'}</span>
                </div>
              ))}
            </div>
          </section>

          <section className="bg-surface-container-low border border-outline-variant/15 rounded-md overflow-hidden">
            <div className="p-5 border-b border-outline-variant/15 bg-surface-highest/50 flex justify-between items-center">
              <div>
                <h2 className="text-[14px] font-headline font-bold text-primary tracking-widest uppercase">Research Scan</h2>
                <span className="text-[11px] font-mono text-on-surface-variant mt-1 block">Current status: {scanStatusQuery.data?.status ?? 'unknown'}</span>
              </div>
              <button
                disabled={scanStatusQuery.data?.status === 'running'}
                onClick={() => void api.triggerScan().then(() => scanStatusQuery.refetch())}
                className="bg-primary/10 text-primary border border-primary/30 px-3 py-1.5 rounded text-[11px] font-bold tracking-wider hover:bg-primary/20 transition-colors disabled:opacity-40"
              >
                START SCAN
              </button>
            </div>
            <div className="p-5 font-mono text-[12px] text-on-surface-variant">
              Started: {scanStatusQuery.data?.started_at ?? '-'}<br />
              Completed: {scanStatusQuery.data?.completed_at ?? '-'}
            </div>
          </section>
        </div>
      </div>
    </div>
  );
}
