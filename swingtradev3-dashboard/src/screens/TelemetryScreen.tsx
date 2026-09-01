import { useEffect, useRef, useState } from 'react';
import {
  type LiveEventsState,
  useAgentActivity,
  useCognitionRuns,
  useExceptionRuns,
  useSessionPlan,
  useTelemetry,
} from '@/hooks/useDashboardData';
import type { DashboardEvent } from '@/lib/schemas';
import { formatIstDateTime, formatIstTime } from '@/lib/time';
import { cn } from '@/lib/utils';

function asText(value: unknown, fallback = '-') {
  if (value === null || value === undefined || value === '') return fallback;
  return String(value);
}

function statusClass(status: string) {
  const normalized = status.toLowerCase();
  if (normalized.includes('error') || normalized.includes('fail')) return 'text-error border-error/40 bg-error/10';
  if (normalized.includes('running') || normalized.includes('live')) return 'text-secondary border-secondary/40 bg-secondary/10';
  if (normalized.includes('completed') || normalized.includes('observed')) return 'text-primary border-primary/40 bg-primary/10';
  return 'text-on-surface-variant border-outline-variant/30 bg-surface-high';
}

function eventSeverity(event: DashboardEvent) {
  const text = `${event.event_type} ${event.entity_type}`.toLowerCase();
  if (text.includes('fail') || text.includes('incident') || text.includes('error')) return 'text-error';
  if (text.includes('order') || text.includes('fill') || text.includes('broker')) return 'text-secondary';
  return 'text-primary';
}

function compactPayload(payload: Record<string, unknown>) {
  const keys = Object.keys(payload);
  if (!keys.length) return '-';
  return keys.slice(0, 4).map((key) => `${key}=${JSON.stringify(payload[key])}`).join(' ');
}

function asRecord(value: unknown): Record<string, unknown> {
  return value && typeof value === 'object' && !Array.isArray(value)
    ? value as Record<string, unknown>
    : {};
}

function asArray(value: unknown): unknown[] {
  return Array.isArray(value) ? value : [];
}

function asCount(value: unknown) {
  if (typeof value === 'number' && Number.isFinite(value)) return value;
  if (typeof value === 'string' && value.trim() !== '') return Number(value) || 0;
  return 0;
}

function unwrapSessionPlan(plan: unknown): Record<string, unknown> {
  const record = asRecord(plan);
  const payload = asRecord(record.payload);
  return Object.keys(payload).length ? payload : record;
}

export function TelemetryScreen({ live }: { live: LiveEventsState }) {
  const telemetryQuery = useTelemetry();
  const activityQuery = useAgentActivity();
  const cognitionQuery = useCognitionRuns(10);
  const exceptionQuery = useExceptionRuns(10);
  const sessionPlanQuery = useSessionPlan();
  const [logsExpanded, setLogsExpanded] = useState(false);
  const [selectedEventId, setSelectedEventId] = useState<number | null>(null);
  const scrollRef = useRef<HTMLDivElement>(null);
  const auditEvents = [
    ...(activityQuery.data?.recent_events ?? telemetryQuery.data?.events ?? []),
    ...live.events,
  ]
    .filter((event, index, events) => events.findIndex((item) => item.event_id === event.event_id) === index)
    .sort((a, b) => a.event_id - b.event_id);
  const events = auditEvents.length ? auditEvents : telemetryQuery.data?.events ?? [];
  const selectedEvent = events.find((event) => event.event_id === selectedEventId) ?? null;
  const agents = activityQuery.data?.agents ?? [];
  const observedSources = activityQuery.data?.observed_sources ?? [];
  const scanStatus = activityQuery.data?.scan_status;
  const workerStatus = activityQuery.data?.worker_status ?? telemetryQuery.data?.worker_status ?? {};
  const session = activityQuery.data?.session;
  const latestRun = cognitionQuery.data?.runs[0] ?? null;
  const latestRunPayload = asRecord(latestRun?.payload);
  const latestRunDiagnostics = asRecord(latestRunPayload.diagnostics);
  const latestRunDecisions = asArray(latestRunPayload.decisions);
  const latestRunApprovalCount = asCount(latestRunDiagnostics.approval_candidates);
  const latestException = exceptionQuery.data?.runs[0] ?? null;
  const latestExceptionPayload = asRecord(latestException?.payload);
  const latestAdvice = asRecord(latestExceptionPayload.advice);
  const sessionPlan = unwrapSessionPlan(sessionPlanQuery.data?.plan);
  const sessionPlanItems = asArray(sessionPlan.items);
  const sessionPlanBlocks = asArray(sessionPlan.blocked_reasons);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [events]);

  return (
    <div className="flex-1 flex flex-col overflow-hidden bg-[#050505]">
      <div className="flex-1 overflow-hidden flex flex-col p-4 md:p-6 pb-0">
        <div className="flex flex-col gap-2 mb-4 shrink-0">
          <h1 className="text-2xl font-headline font-bold text-white tracking-wider uppercase flex items-center gap-3">
            <span className="material-symbols-outlined text-[28px] text-tertiary">account_tree</span>
            Agent Activity & Audit Trail
          </h1>
          <p className="text-[12px] font-mono text-on-surface-variant">
            SSE {live.status}; cursor {live.cursor ?? '-'}; phase {session?.phase_label ?? asText(workerStatus.current_phase)}.
          </p>
        </div>

        <div className="flex-1 grid grid-cols-1 xl:grid-cols-12 gap-4 overflow-hidden">
          <section className="xl:col-span-7 border border-outline-variant/20 rounded-md bg-surface-container-low/60 overflow-hidden flex flex-col min-h-[320px]">
            <div className="h-11 px-4 border-b border-outline-variant/15 bg-surface-lowest flex items-center justify-between">
              <h2 className="text-[12px] font-headline font-bold uppercase tracking-wide text-white">Overnight / Slow Brain Agents</h2>
              <span className={cn('px-2 py-1 rounded border text-[10px] font-mono uppercase', statusClass(asText(scanStatus?.status, 'unknown')))}>
                {asText(scanStatus?.status, activityQuery.isLoading ? 'loading' : 'unknown')}
              </span>
            </div>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3 p-3 overflow-auto">
              {(agents.length ? agents : []).map((agent) => (
                <div key={agent.agent_name} className="bg-surface-lowest border border-outline-variant/15 rounded p-3 min-h-[112px]">
                  <div className="flex items-start justify-between gap-3 mb-2">
                    <div>
                      <div className="text-[12px] font-mono font-bold text-white">{agent.agent_name}</div>
                      <div className="text-[10px] font-mono text-on-surface-variant">{formatIstDateTime(agent.started_at)}</div>
                    </div>
                    <span className={cn('px-2 py-0.5 rounded border text-[10px] font-mono uppercase', statusClass(agent.status))}>
                      {agent.status}
                    </span>
                  </div>
                  <div className="text-[12px] text-on-surface leading-relaxed line-clamp-3">
                    {agent.current_task ?? agent.progress ?? agent.last_error ?? 'No active task recorded.'}
                  </div>
                  <div className="mt-3 text-[10px] font-mono text-on-surface-variant flex justify-between">
                    <span>{agent.progress ?? '-'}</span>
                    <span>{agent.completed_at ? formatIstTime(agent.completed_at) : 'open'}</span>
                  </div>
                </div>
              ))}
              {!agents.length && (
                <div className="md:col-span-2 text-[12px] font-mono text-on-surface-variant border border-dashed border-outline-variant/25 rounded p-6 text-center">
                  {activityQuery.isLoading ? 'Loading agent activity...' : 'No active agent activity snapshot recorded.'}
                </div>
              )}
            </div>
          </section>

          <section className="xl:col-span-5 border border-outline-variant/20 rounded-md bg-surface-container-low/60 overflow-hidden flex flex-col min-h-[320px]">
            <div className="h-11 px-4 border-b border-outline-variant/15 bg-surface-lowest flex items-center justify-between">
              <h2 className="text-[12px] font-headline font-bold uppercase tracking-wide text-white">Runtime Sources</h2>
              <span className="text-[10px] font-mono text-on-surface-variant">
                {observedSources.length} sources
              </span>
            </div>
            <div className="p-3 grid grid-cols-1 sm:grid-cols-2 gap-3 border-b border-outline-variant/15">
              <div className="bg-surface-lowest border border-outline-variant/15 rounded p-3">
                <div className="text-[10px] uppercase font-mono text-on-surface-variant">Scheduler</div>
                <div className="text-[13px] font-mono font-bold text-white mt-1">{asText(workerStatus.current_phase)}</div>
                <div className="text-[10px] font-mono text-on-surface-variant mt-1">{asText(workerStatus.next_task)}</div>
              </div>
              <div className="bg-surface-lowest border border-outline-variant/15 rounded p-3">
                <div className="text-[10px] uppercase font-mono text-on-surface-variant">Research Scan</div>
                <div className="text-[13px] font-mono font-bold text-white mt-1">{asText(scanStatus?.status)}</div>
                <div className="text-[10px] font-mono text-on-surface-variant mt-1">{formatIstTime(scanStatus?.completed_at)}</div>
              </div>
              <div className="bg-surface-lowest border border-outline-variant/15 rounded p-3">
                <div className="text-[10px] uppercase font-mono text-on-surface-variant">Slow Brain Run</div>
                <div className="flex items-center justify-between gap-2 mt-1">
                  <div className="text-[13px] font-mono font-bold text-white truncate">
                    {asText(latestRun?.status, cognitionQuery.isLoading ? 'loading' : 'none')}
                  </div>
                  <span className={cn('px-2 py-0.5 rounded border text-[9px] font-mono uppercase shrink-0', statusClass(asText(latestRun?.status)))}>
                    {latestRun?.phase ?? 'phase_13'}
                  </span>
                </div>
                <div className="text-[10px] font-mono text-on-surface-variant mt-1 truncate">
                  {latestRun ? `${latestRunDecisions.length} decisions / ${latestRunApprovalCount} approvals` : 'No cognition run stored yet.'}
                </div>
                <div className="text-[10px] font-mono text-on-surface-variant mt-1 truncate">
                  {latestRun?.completed_at ? formatIstDateTime(latestRun.completed_at) : asText(latestRun?.run_id)}
                </div>
              </div>
              <div className="bg-surface-lowest border border-outline-variant/15 rounded p-3">
                <div className="text-[10px] uppercase font-mono text-on-surface-variant">Session Plan</div>
                <div className="flex items-center justify-between gap-2 mt-1">
                  <div className="text-[13px] font-mono font-bold text-white truncate">
                    {asText(sessionPlan.status, sessionPlanQuery.isLoading ? 'loading' : 'none')}
                  </div>
                  <span className={cn('px-2 py-0.5 rounded border text-[9px] font-mono uppercase shrink-0', statusClass(asText(sessionPlan.status)))}>
                    {sessionPlanItems.length} items
                  </span>
                </div>
                <div className="text-[10px] font-mono text-on-surface-variant mt-1 truncate">
                  {sessionPlanBlocks.length ? sessionPlanBlocks.join(', ') : 'No session blocks recorded.'}
                </div>
                <div className="text-[10px] font-mono text-on-surface-variant mt-1 truncate">
                  {asText(sessionPlan.trading_date)}
                </div>
              </div>
              <div className="bg-surface-lowest border border-outline-variant/15 rounded p-3 sm:col-span-2">
                <div className="text-[10px] uppercase font-mono text-on-surface-variant">Intraday Exception Analyst</div>
                <div className="flex items-center justify-between gap-2 mt-1">
                  <div className="text-[13px] font-mono font-bold text-white truncate">
                    {asText(latestAdvice.advisory_action, exceptionQuery.isLoading ? 'loading' : 'no anomaly')}
                  </div>
                  <span className={cn('px-2 py-0.5 rounded border text-[9px] font-mono uppercase shrink-0', statusClass(asText(latestException?.status)))}>
                    advisory only
                  </span>
                </div>
                <div className="text-[10px] font-mono text-on-surface-variant mt-1 truncate">
                  {asText(latestAdvice.kind ?? latestExceptionPayload.kind, 'No bounded exception report stored.')}
                </div>
                <div className="text-[10px] font-mono text-on-surface-variant mt-1 truncate">
                  {latestException?.completed_at ? formatIstDateTime(latestException.completed_at) : asText(latestException?.run_id)}
                </div>
              </div>
            </div>
            <div className="overflow-auto p-2 space-y-1">
              {latestRun && (
                <div className="bg-surface-lowest/70 border border-tertiary/20 rounded px-3 py-2">
                  <div className="flex items-center justify-between gap-3">
                    <span className="text-[12px] font-mono font-bold text-white truncate">
                      {latestRun.run_id}
                    </span>
                    <span className="text-[10px] font-mono text-tertiary shrink-0">
                      {latestRunDecisions.length} decisions
                    </span>
                  </div>
                  <div className="text-[10px] font-mono text-on-surface-variant mt-1 truncate">
                    scan={asText(latestRunDiagnostics.scan_candidates)} funnel={asText(latestRunDiagnostics.funnel_candidates)} approvals={asText(latestRunDiagnostics.approval_candidates)}
                  </div>
                </div>
              )}
              {observedSources.map((source) => (
                <div key={source.agent_name} className="bg-surface-lowest/70 border border-outline-variant/10 rounded px-3 py-2">
                  <div className="flex items-center justify-between gap-3">
                    <span className="text-[12px] font-mono font-bold text-white truncate">{source.agent_name}</span>
                    <span className={cn('px-2 py-0.5 rounded border text-[10px] font-mono uppercase shrink-0', statusClass(source.status))}>
                      {source.status}
                    </span>
                  </div>
                  <div className="text-[10px] font-mono text-on-surface-variant mt-1 flex justify-between gap-3">
                    <span className="truncate">{source.last_event ?? '-'}</span>
                    <span>{source.event_count} events</span>
                  </div>
                </div>
              ))}
              {!observedSources.length && (
                <div className="text-[12px] font-mono text-on-surface-variant p-6 text-center">No durable sources observed.</div>
              )}
            </div>
          </section>
        </div>
      </div>

      <div className={cn(
        "flex-none bg-[#020202] border-t border-outline-variant/30 flex flex-col transition-all duration-500 ease-in-out relative z-20 shadow-[0_-10px_30px_rgba(0,0,0,0.5)] mt-4",
        logsExpanded ? "h-[350px]" : "h-10"
      )}>
        <button
          onClick={() => setLogsExpanded(!logsExpanded)}
          className="h-10 w-full flex items-center justify-center gap-2 text-[11px] font-mono hover:bg-white/5 transition-colors text-white border-b border-outline-variant/10 cursor-pointer shrink-0 group"
        >
          <span className="material-symbols-outlined text-[16px] text-primary group-hover:text-secondary transition-colors">
            {logsExpanded ? "keyboard_double_arrow_down" : "keyboard_double_arrow_up"}
          </span>
          {logsExpanded ? "HIDE AUDIT TRAIL" : "EXPAND AUDIT TRAIL"}
        </button>

        <div className={cn("flex-1 overflow-hidden flex flex-col opacity-0 transition-opacity duration-300", logsExpanded && "opacity-100")}>
          <div className="h-10 bg-[#0a0b0f] flex items-center px-4 justify-between shrink-0 border-b border-[#1c1e26]">
            <div className="flex items-center gap-4">
              <span className="flex gap-4 text-[10px] font-mono uppercase font-bold tracking-widest text-[#89929c]">
                <span className="text-[#3bb0ff]">All</span>
                <span>Events: {events.length}</span>
                <span>Types: {Object.keys(telemetryQuery.data?.event_type_counts ?? {}).length}</span>
                <span>Audit Count: {activityQuery.data?.event_count ?? '-'}</span>
              </span>
            </div>
          </div>
          <div ref={scrollRef} className="flex-1 overflow-auto p-4 font-mono text-[11px] leading-relaxed selection:bg-[#3bb0ff] selection:text-[#000000] no-scrollbar">
            {events.map((event) => {
              const selected = selectedEventId === event.event_id;
              return (
                <div key={event.event_id} className={cn("rounded transition-colors duration-100", selected ? "bg-[#1a1b20]" : "hover:bg-[#1a1b20]/50")}>
                  <button
                    onClick={() => setSelectedEventId(selected ? null : event.event_id)}
                    className="w-full flex gap-3 px-1 py-1 text-left whitespace-pre-wrap"
                  >
                    <span className="text-[#3f4851] w-20 shrink-0">{formatIstTime(event.created_at)}</span>
                    <span className="text-[#3f4851] w-16 shrink-0">#{event.event_id}</span>
                    <span className={cn("w-40 shrink-0 font-bold", eventSeverity(event))}>[{event.event_type}]</span>
                    <span className="w-32 shrink-0 text-secondary">{event.source}</span>
                    <span className="w-56 shrink-0 text-[#bec7d3]">{event.entity_type}:{event.entity_id}</span>
                    <span className="flex-1 text-[#89929c] truncate">{compactPayload(event.payload)}</span>
                  </button>
                  {selected && (
                    <pre className="mx-1 mb-2 max-h-52 overflow-auto rounded bg-black/50 border border-outline-variant/20 p-3 text-[10px] text-[#bec7d3]">
                      {JSON.stringify(event.payload, null, 2)}
                    </pre>
                  )}
                </div>
              );
            })}
            {!events.length && <div className="text-[#89929c]">No audit events recorded.</div>}
          </div>
        </div>
      </div>
    </div>
  );
}
