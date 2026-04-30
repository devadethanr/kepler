import { useEffect, useRef, useState } from 'react';
import { SystemTelemetryFlow } from '@/components/SystemTelemetryFlow';
import { useLiveEvents, useTelemetry } from '@/hooks/useDashboardData';
import { cn } from '@/lib/utils';

export function TelemetryScreen() {
  const telemetryQuery = useTelemetry();
  const live = useLiveEvents();
  const [logsExpanded, setLogsExpanded] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);
  const events = live.events.length ? live.events : telemetryQuery.data?.events ?? [];

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
            System Telemetry Map
          </h1>
          <p className="text-[12px] font-mono text-on-surface-variant">
            Durable execution-event stream. SSE status: {live.status}; cursor: {live.cursor ?? '-'}.
          </p>
        </div>

        <div className="flex-1 relative border border-outline-variant/20 rounded-xl bg-surface-container-low/40 backdrop-blur-xl overflow-hidden shadow-2xl z-10">
          <SystemTelemetryFlow />
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
          {logsExpanded ? "HIDE EXECUTION EVENTS" : "EXPAND EXECUTION EVENTS"}
        </button>

        <div className={cn("flex-1 overflow-hidden flex flex-col opacity-0 transition-opacity duration-300", logsExpanded && "opacity-100")}>
          <div className="h-10 bg-[#0a0b0f] flex items-center px-4 justify-between shrink-0 border-b border-[#1c1e26]">
            <div className="flex items-center gap-4">
              <span className="flex gap-4 text-[10px] font-mono uppercase font-bold tracking-widest text-[#89929c]">
                <span className="text-[#3bb0ff]">All</span>
                <span>Events: {events.length}</span>
                <span>Types: {Object.keys(telemetryQuery.data?.event_type_counts ?? {}).length}</span>
              </span>
            </div>
          </div>
          <div ref={scrollRef} className="flex-1 overflow-auto p-4 font-mono text-[11px] leading-relaxed selection:bg-[#3bb0ff] selection:text-[#000000] no-scrollbar">
            {events.map((event) => {
              const isError = event.event_type.includes('fail') || event.event_type.includes('incident');
              return (
                <div key={event.event_id} className="flex gap-3 hover:bg-[#1a1b20]/50 px-1 rounded whitespace-pre-wrap transition-colors duration-100">
                  <span className="text-[#3f4851] w-22 shrink-0">{event.created_at ? new Date(event.created_at).toLocaleTimeString('en-IN', { hour12: false }) : '--:--:--'}</span>
                  <span className={cn("w-36 shrink-0 font-bold", isError ? 'text-[#ffb4ab]' : 'text-[#3bb0ff]')}>
                    [{event.event_type}]
                  </span>
                  <span className="w-24 shrink-0 text-secondary">{event.source}</span>
                  <span className={cn("flex-1", isError ? 'text-[#ffb4ab]' : 'text-[#bec7d3]')}>
                    {event.entity_type}:{event.entity_id}
                  </span>
                </div>
              );
            })}
            {!events.length && <div className="text-[#89929c]">No execution events recorded.</div>}
          </div>
        </div>
      </div>
    </div>
  );
}
