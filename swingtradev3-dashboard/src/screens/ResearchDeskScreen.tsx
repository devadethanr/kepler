import React, { useEffect, useRef, useState } from 'react';
import { mergeRoomEvents, newRequestId, research, RoomEventSchema, shouldStreamRoom, terminalStatuses, type Room, type RoomEvent, type SourceCoverage, type MarketContext } from '../lib/research';

const terminal = terminalStatuses;
const text = (value: unknown) => typeof value === 'string' ? value : '';
const object = (value: unknown): Record<string, unknown> => value && typeof value === 'object' && !Array.isArray(value) ? value as Record<string, unknown> : {};
const display = (value: unknown): string => value == null || value === '' ? 'unknown' : typeof value === 'string' ? value : JSON.stringify(value);
const ist = (value: unknown): string => {
  if (typeof value !== 'string' || !value) return 'unknown';
  if (/^\d{4}-\d{2}-\d{2}$/.test(value)) return value;
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? value : `${value} (${date.toLocaleString('en-IN', { timeZone: 'Asia/Kolkata', timeZoneName: 'short' })})`;
};

const marketTime = (value: unknown): string => {
  if (typeof value !== 'string' || !value) return 'unknown';
  // An unzoned timestamp is not silently interpreted in the browser timezone.
  if (!/(?:Z|[+-]\d{2}:?\d{2})$/i.test(value)) return `${value} (timezone unknown)`;
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return `${value} (invalid timestamp)`;
  const format = (zone: string) => date.toLocaleString('en-GB', { timeZone: zone, timeZoneName: 'short' });
  return `${date.toISOString()} UTC · ${format('Asia/Kolkata')} IST · ${format('Asia/Singapore')} SGT (Singapore)`;
};

export function MarketObservation({ item }: { item: Record<string, unknown> }) {
  const kind = item.instrument_kind === 'future' ? 'Future' : item.instrument_kind === 'cash_index' ? 'Cash index' : item.instrument_kind === 'proxy' ? 'Proxy' : 'Instrument type unknown';
  const usable = ['ok', 'partial', 'stale'].includes(text(item.status));
  const hasQuote = usable && typeof item.quote_value === 'number' && Number.isFinite(item.quote_value) && item.quote_value > 0;
  return <article className="rounded border border-slate-700 bg-slate-900 p-3 text-xs text-slate-300">
    <h3 className="font-semibold text-sm text-cyan-300">{display(item.symbol ?? item.underlying)} · {kind}</h3>
    <p>Status: {display(item.status)} · Market state at observation: {display(item.market_state)} · Market state at cutoff: {display(item.market_state_at_cutoff)} · Session at observation: {display(item.session_id)} · Market date: {display(item.market_date)}</p>
    <p className="my-1 text-sm">{hasQuote ? `Quote: ${display(item.quote_value)} ${display(item.quote_unit)}` : 'Quote unavailable'} · Delay: {typeof item.delay_seconds === 'number' ? `${item.delay_seconds} seconds` : 'unknown'}</p>
    <p>Instrument ID: {display(item.instrument_id)} · Underlying: {display(item.underlying)} · Exchange: {display(item.exchange)} · Contract: {display(item.contract)} · Expiry: {display(item.expiry)} · Settlement currency: {display(item.settlement_currency)}</p>
    <p>Provider: {display(item.provider)} · Source: {display(item.source)}</p>
    <p>Exchange as of: {marketTime(item.exchange_asof)}</p>
    <p>Provider as of: {marketTime(item.provider_asof)}</p>
    <p>Received: {marketTime(item.received_at)} · First seen: {marketTime(item.first_seen_at)}</p>
    <p>Reference: {usable ? display(item.reference_value) : 'unavailable'} · Reference as of: {marketTime(item.reference_asof)} · Basis: {display(item.basis)}</p>
    <p>Quality reasons: {Array.isArray(item.quality_reasons) && item.quality_reasons.length ? item.quality_reasons.map(display).join('; ') : 'none reported'}</p>
    <details className="mt-1"><summary>Snapshot provenance</summary>
      <p>Contract specification: {display(item.contract_specification)} · Multiplier (USD per point): {display(item.contract_multiplier_usd_per_point)} · Expiry rule source: {display(item.expiry_rule_source)}</p>
      <p>Snapshot ID: {display(item.snapshot_id)} · Schema: {display(item.schema_version)} · Source version: {display(item.source_version)} · Config version: {display(item.config_version)} · Calendar version: {display(item.calendar_version)}</p>
      <p>Source document SHA-256: {display(item.source_document_sha256)} · Expiry rule document SHA-256: {display(item.expiry_rule_document_sha256)} · Raw observation hash: {display(item.raw_observation_hash)}</p>
      <p>Saved status: {display(item.saved_status)} · Assessment: {display(item.assessment_basis)} · Observation age: {typeof item.observation_age_seconds === 'number' ? `${item.observation_age_seconds} seconds` : 'unknown'}</p>
    </details>
  </article>;
}

export function MarketContextStatus({ value, error }: { value: MarketContext | null; error: string }) {
  return <section aria-label="Market context" className="my-4 rounded border border-slate-700 p-3 text-sm">
    <h2 className="font-semibold">Market context</h2>
    {error ? <p role="status">Market context unavailable: {error}</p> : !value ? <p>Loading market context…</p> : <>
      <p className="text-xs text-slate-400">As of: {marketTime(value.as_of)} · Cutoff: {marketTime(value.cutoff)} · Coverage: {display(value.coverage)}</p>
      {value.limits != null && <p className="text-xs text-slate-400">Limits: {display(value.limits)}</p>}
      {!value.observations.length && <p>No market observations available.</p>}
      <div className="mt-2 grid gap-2 lg:grid-cols-2">{value.observations.map((item, index) => <MarketObservation key={`${text(item.snapshot_id)}-${index}`} item={item} />)}</div>
    </>}
  </section>;
}

export function SourceEvidence({ packet }: { packet: Record<string, unknown> }) {
  const marketSnapshot = object(packet.market_snapshot);
  const snapshot = object(packet.source_snapshot);
  const content = object(packet.content);
  const retrieval = object(packet.retrieval);
  const sources = Array.isArray(content.sources) ? content.sources.map(object) : [];
  const records = sources.length ? sources : Object.keys(snapshot).length ? [snapshot] : [];
  if (Object.keys(marketSnapshot).length) return <section aria-label="Saved market evidence" className="mt-2"><h4 className="text-xs font-semibold">Saved market evidence</h4><MarketObservation item={marketSnapshot} /></section>;
  if (!records.length && !Object.keys(snapshot).length) return null;
  return <section aria-label="Source evidence" className="mt-2 space-y-2 rounded border border-slate-700 p-3 text-xs text-slate-300">
    <h4 className="font-semibold text-cyan-300">Source evidence</h4>
    {Object.keys(snapshot).length > 0 && <p>Snapshot coverage: {display(snapshot.coverage ?? snapshot.completeness)} · Cutoff: {ist(snapshot.requested_cutoff ?? snapshot.cutoff)}</p>}
    {records.map((item, index) => <div key={`${text(item.version_id)}-${index}`} className="border-t border-slate-700 pt-2">
      <p>Source: {display(item.source_id ?? item.provider)} · Type: {display(item.source_type)} · Revision: {display(item.version_id)} · Supersedes: {display(item.supersedes_version_id ?? item.supersedes)}</p>
      <p>Published: {display(item.published_raw ?? item.published_date ?? item.published_at_utc ?? item.published_at_or_date ?? item.published_at)} · Precision: {display(item.publication_precision ?? item.precision)} · Timezone basis: {display(item.timezone_basis)}</p>
      <p>Event: {ist(item.event_at)} · First seen: {ist(item.first_seen_at)} · Fetched: {ist(item.fetched_at)}</p>
      <p>Identity basis: {display(item.identity_basis)} · Availability: {display(item.availability)} · Cutoff: {ist(item.requested_cutoff ?? item.cutoff)}</p>
      <p>Retrieval completeness: {display(item.retrieval_completeness ?? item.completeness ?? item.retrieval_scope ?? retrieval.completeness)}</p>
      {text(item.canonical_url) && /^https?:\/\//i.test(text(item.canonical_url)) && <a href={text(item.canonical_url)} target="_blank" rel="noreferrer" className="text-cyan-300 underline">Original source</a>}
      {text(item.excerpt) && <blockquote className="mt-1 whitespace-pre-wrap">Excerpt: “{text(item.excerpt)}”</blockquote>}
    </div>)}
    {Array.isArray(packet.quote_spans) && packet.quote_spans.map((raw, index) => { const span = object(raw); return <blockquote key={text(span.id) || index} className="whitespace-pre-wrap">{display(span.id)}: “{text(span.text)}” {span.start != null || span.end != null ? `(offsets ${display(span.start)}–${display(span.end)})` : ''}</blockquote>; })}
  </section>;
}

export function SourceStatus({ value, error }: { value: SourceCoverage | null; error: string }) {
  return <section aria-label="Source coverage" className="my-4 rounded border border-slate-700 p-3 text-sm">
    <h2 className="font-semibold">Source coverage</h2>
    {error ? <p role="status">Source status unavailable: {error}</p> : !value ? <p>Loading source status…</p> : <>
      <p>{display(value.coverage)}</p>
      {!value.sources.length && <p>No source status records available.</p>}
      {value.sources.map(source => <p key={source.source_id}>{source.source_id} · {display(source.source_type)} · {display(source.status)} · Entries: {display(source.entry_count)} · Freshness: {display(source.freshness)} · Fetched: {ist(source.fetched_at)} · Coverage: {display(source.coverage)}</p>)}
    </>}
  </section>;
}


export function DiscussionEvent({ event }: { event: RoomEvent }) {
  const data = event.data;
  if (event.kind === 'message') {
    const claims = Array.isArray(data.claims) ? data.claims as Record<string, unknown>[] : [];
    return <article className="rounded border border-slate-700 bg-slate-900 p-4" aria-label={`${event.agent} message`}>
      <div className="text-sm text-cyan-300">{event.agent} → {text(data.recipient)} · {text(data.kind)} · {text(data.stance)}</div>
      <p className="mt-2 text-xs text-slate-400">Agent interpretation · excerpts are verified separately below</p>
      <p className="my-3 whitespace-pre-wrap text-slate-100">{text(data.text)}</p>
      {claims.map((claim, i) => <div key={text(claim.id) || i} className="my-2 border-l-2 border-cyan-600 pl-3 text-sm">
        {text(claim.text) && <p>{text(claim.text)}</p>}
        {text(claim.kind) && <p className="text-slate-400">{text(claim.kind)} · narrative unassessed</p>}
        {text(claim.support_assessment) && <p className="text-slate-400">Model support proposal: {text(claim.support_assessment)} · not a truth check</p>}
        {text(claim.quote) && <blockquote>Excerpt verified: “{text(claim.quote)}”</blockquote>}
        {(text(claim.evidence_id) || text(claim.source) || text(claim.freshness)) &&
          <p className="text-slate-400">{text(claim.evidence_id)} · {text(claim.source)} · freshness: {text(claim.freshness) || 'unknown'}</p>}
        {Array.isArray(claim.evidence_refs) && <p className="text-slate-400">Evidence references: {claim.evidence_refs.map(ref => {
          if (!ref || typeof ref !== 'object') return '';
          const item = ref as Record<string, unknown>;
          return `${text(item.evidence_id)} / ${text(item.quote_id)}`;
        }).filter(Boolean).join(', ') || 'none'}</p>}
        {(text(claim.target_entity) || text(claim.event_id)) && <p className="text-slate-400">Entity: {text(claim.target_entity) || 'unknown'} · Event: {text(claim.event_id) || 'unknown'}</p>}
        {claim.source_metadata != null && <p className="text-slate-400">Source provenance: {display(claim.source_metadata)}</p>}
        {claim.metadata_policy != null && <p className="text-slate-400">Metadata policy: {typeof claim.metadata_policy === 'string' ? claim.metadata_policy : JSON.stringify(claim.metadata_policy)}</p>}
      </div>)}
      <p className="text-xs text-slate-400">{text(data.validation)} · {new Date(event.at).toLocaleTimeString()}</p>
    </article>;
  }
  const output = object(data.output);
  const evidence = Array.isArray(output.evidence) ? output.evidence.map(object) : [];
  return <details className="rounded border border-slate-800 p-2 text-sm text-slate-400">
    <summary>{event.agent} · {event.kind}{data.name ? ` · ${text(data.name)}` : ''}</summary>
    {evidence.map((packet, index) => <SourceEvidence key={text(packet.id) || index} packet={packet} />)}
    <SourceEvidence packet={output} />
    <pre className="max-h-72 overflow-auto whitespace-pre-wrap p-2 text-xs">{JSON.stringify(data, null, 2)}</pre>
  </details>;
}

export function ResearchDeskScreen() {
  const [marketContext, setMarketContext] = useState<MarketContext | null>(null);
  const [marketError, setMarketError] = useState('');
  const [sourceStatus, setSourceStatus] = useState<SourceCoverage | null>(null);
  const [sourceError, setSourceError] = useState('');
  const [rooms, setRooms] = useState<Room[]>([]);
  const [selected, setSelected] = useState('');
  const [roomId, setRoomId] = useState('');
  const [roomsLoading, setRoomsLoading] = useState(true);
  const [room, setRoom] = useState<Room | null>(null);
  const [events, setEvents] = useState<RoomEvent[]>([]);
  const [target, setTarget] = useState('');
  const [question, setQuestion] = useState('');
  const [error, setError] = useState('');
  const [connection, setConnection] = useState('Disconnected');
  const [busy, setBusy] = useState(false);
  const [retryBusy, setRetryBusy] = useState(false);
  const [cancelBusy, setCancelBusy] = useState(false);
  const cancelInFlight = useRef(false);
  const retryInFlight = useRef(false);
  const retryIds = useRef(new Map<string, string>());
  const [models, setModels] = useState('Checking local model services');
  const [requestId, setRequestId] = useState(() => newRequestId());

  useEffect(() => {
    let live = true;
    let sourceRequest = 0;
    let marketRequest = 0;
    const refresh = () => research.list().then(value => { if (live) { setRooms(value); setRoomsLoading(false); setError(previous => previous.startsWith('Saved rooms unavailable:') ? '' : previous); } })
      .catch(err => { if (live) { setRoomsLoading(false); setError(`Saved rooms unavailable: ${String(err)}`); } });
    const health = () => research.health().then(value => { if (live) setModels(
      Object.entries(value.models).map(([role, model]) => `${role}: ${model.model} · ${model.status}`).join(' / ') || value.status,
    ); }).catch(() => { if (live) setModels('Local model health unavailable'); });
    const sources = () => {
      const request = ++sourceRequest;
      return research.sources().then(value => { if (live && request === sourceRequest) { setSourceStatus(value); setSourceError(''); } }).catch(err => { if (live && request === sourceRequest) setSourceError(String(err)); });
    };
    const market = () => {
      const request = ++marketRequest;
      return research.marketContext().then(value => { if (live && request === marketRequest) { setMarketContext(value); setMarketError(''); } }).catch(err => { if (live && request === marketRequest) setMarketError(String(err)); });
    };
    void refresh(); void health(); void sources(); void market();
    const timer = setInterval(() => { void refresh(); void health(); void sources(); }, 5000);
    const marketTimer = setInterval(() => { void market(); }, 30000);
    return () => { live = false; clearInterval(timer); clearInterval(marketTimer); };
  }, []);
  useEffect(() => {
    if (!selected) return;
    let live = true;
    let source: EventSource | undefined;
    let initialized = false;
    let initializing = false;
    let terminalSynced = false;
    let refreshInFlight = false;
    const syncTerminal = () => {
      source?.close();
      setConnection('Saved discussion');
      if (terminalSynced) return;
      terminalSynced = true;
      research.events(selected).then(history => {
        if (live) { setEvents(previous => mergeRoomEvents(previous, history.events)); setError(previous => previous.startsWith('Room history unavailable:') ? '' : previous); }
      }).catch(err => {
        terminalSynced = false;
        if (live) setError(`Room history unavailable: ${String(err)}`);
      });
    };
    setEvents([]); setRoom(null); setConnection('Connecting');
    const refresh = () => {
      if (refreshInFlight) return;
      refreshInFlight = true;
      return research.get(selected).then(value => {
      if (!live) return;
      setRoom(previous => previous?.id === value.id && (previous.seq > value.seq || (terminal.has(previous.status) && !terminal.has(value.status))) ? previous : value);
      setError(previous => previous.startsWith('Room unavailable:') ? '' : previous);
      if (terminal.has(value.status)) syncTerminal();
    }).catch(err => { if (live) setError(`Room unavailable: ${String(err)}`); }).finally(() => { refreshInFlight = false; });
    };
    const initialize = () => {
      if (initializing || initialized) return;
      initializing = true;
      Promise.all([research.get(selected), research.events(selected)]).then(([value, history]) => {
      if (!live) return;
      initialized = true;
      setError(previous => previous.startsWith('Room unavailable:') ? '' : previous);
      setRoom(value); setEvents(history.events);
      if (!shouldStreamRoom(value, history.events)) { syncTerminal(); return; }
      source = new EventSource(`/api/research/rooms/${encodeURIComponent(selected)}/stream?after=${history.cursor}`);
      source.onopen = () => { if (live) setConnection('Live'); };
      source.onerror = () => { if (live) { setConnection('Reconnecting — showing saved discussion'); void refresh(); } };
      source.addEventListener('room', raw => {
        try {
          const event = RoomEventSchema.parse(JSON.parse((raw as MessageEvent).data));
          if (!live) return;
          setEvents(previous => mergeRoomEvents(previous, [event]));
          if (event.kind === 'room.finished') { terminalSynced = true; source?.close(); setConnection('Saved discussion'); }
          void refresh();
        } catch (err) { if (live) setError(`Invalid room event: ${String(err)}`); }
      });
      }).catch(err => { if (live) { setConnection('Unavailable'); setError(`Room unavailable: ${String(err)}`); } })
        .finally(() => { initializing = false; });
    };
    initialize();
    const timer = setInterval(() => { if (initialized) void refresh(); else initialize(); }, 2000);
    return () => { live = false; source?.close(); clearInterval(timer); };
  }, [selected]);

  async function start(event: React.FormEvent) {
    event.preventDefault(); setBusy(true); setError('');
    try {
      const result = await research.create(target, question, requestId);
      setSelected(result.id); setRequestId(newRequestId());
    } catch (err) { setError(String(err)); }
    finally { setBusy(false); }
  }
  async function retry(parentId: string) {
    if (retryInFlight.current) return;
    retryInFlight.current = true; setRetryBusy(true); setError('');
    try {
      let requestId = retryIds.current.get(parentId);
      if (!requestId) { requestId = newRequestId(); retryIds.current.set(parentId, requestId); }
      const result = await research.retry(parentId, requestId);
      retryIds.current.delete(parentId);
      setSelected(result.id);
    } catch (err) { setError(String(err)); }
    finally { retryInFlight.current = false; setRetryBusy(false); }
  }
  async function cancel(id: string) {
    if (cancelInFlight.current) return;
    cancelInFlight.current = true; setCancelBusy(true);
    try {
      const result = await research.cancel(id);
      setRoom(previous => previous?.id === id ? result : previous);
    } catch (err) { setError(String(err)); }
    finally { cancelInFlight.current = false; setCancelBusy(false); }
  }
  return <main className="flex-1 overflow-auto p-5 text-slate-200">
    <h1 className="text-2xl font-semibold">Research Desk</h1>
    <p className="my-2 text-sm text-slate-400">Analyst and skeptic · read-only research · live entries require your approval</p>
    <p className="text-xs text-slate-400" role="status">{models}. A running research worker processes queued rooms.</p>
    <SourceStatus value={sourceStatus} error={sourceError} />
    <MarketContextStatus value={marketContext} error={marketError} />
    <form onSubmit={start} className="my-4 flex flex-wrap gap-3">
      <label className="flex flex-col text-sm">Target
        <input required maxLength={64} value={target} onChange={e => { setTarget(e.target.value); setRequestId(newRequestId()); }}
          className="rounded border border-slate-600 bg-slate-900 p-2" placeholder="RELIANCE" />
      </label>
      <label className="flex min-w-64 flex-1 flex-col text-sm">Research question
        <textarea required minLength={8} maxLength={3000} value={question}
          onChange={e => { setQuestion(e.target.value); setRequestId(newRequestId()); }}
          className="rounded border border-slate-600 bg-slate-900 p-2" placeholder="What does the available evidence support, and what is missing?" />
      </label>
      <button disabled={busy} className="self-end rounded bg-cyan-800 px-4 py-2 disabled:opacity-50">Start research</button>
    </form>
    {error && <p role="alert" className="my-3 text-red-300">{error}</p>}
    <label className="text-sm">Saved rooms <select value={selected} onChange={e => setSelected(e.target.value)} className="m-2 rounded bg-slate-900 p-2">
      <option value="">Choose a room</option>
      {rooms.map(item => <option key={item.id} value={item.id}>{item.target} · {item.status} · {item.question.slice(0, 70)}</option>)}
      {selected && !rooms.some(item => item.id === selected) && <option value={selected}>{selected}</option>}
    </select></label>
    <form className="my-2 flex flex-wrap items-end gap-2" onSubmit={event => {
      event.preventDefault(); setError(''); setSelected(roomId.trim());
    }}>
      <label className="text-sm">Open saved room by ID
        <input required value={roomId} onChange={event => setRoomId(event.target.value)}
          className="ml-2 rounded border border-slate-600 bg-slate-900 p-2" placeholder="Room ID" />
      </label>
      <button className="rounded border border-slate-600 px-3 py-2">Open room</button>
    </form>
    <p className="text-xs text-slate-400">{roomsLoading ? 'Loading saved rooms…' : error.startsWith('Saved rooms unavailable:') ? 'Saved rooms could not be loaded.' : rooms.length ? 'Showing recent rooms. Open older rooms by ID.' : 'No saved rooms shown.'}</p>
    {room && <section className="my-4" aria-label="Room status">
      <div className="flex flex-wrap items-center gap-3"><h2 className="font-semibold">{room.target}: {room.question}</h2>
        <span role="status">{room.status} · {room.worker_state === 'stale' ? 'Worker lease expired; awaiting recovery' : connection}</span>
        {terminal.has(room.status) && <button disabled={retryBusy} className="rounded border border-slate-600 px-3 py-1 disabled:opacity-50" onClick={() => { void retry(room.id); }}>Retry as new room</button>}
        {!terminal.has(room.status) && <button disabled={cancelBusy} className="rounded border border-red-700 px-3 py-1 disabled:opacity-50" onClick={() => { void cancel(room.id); }}>Cancel research</button>}
      </div>
      {text(room.termination_reason) && <p className="my-2 text-xs text-slate-400">Termination reason: {text(room.termination_reason)}</p>}
      {room.activity_state === 'unknown' && <p className="my-2 text-xs text-amber-300">In-flight activity is unknown after interruption or lease expiry.</p>}
      <p className="my-2 text-xs text-slate-400">Model calls {room.counts.model} · Tools {room.counts.tool} · Actual tokens {room.counts.input_tokens + room.counts.output_tokens} · Unknown-usage calls {room.counts.unknown_usage_calls} · Reserved context tokens {room.counts.reserved_tokens}</p>
    </section>}
    <section aria-label="Research discussion" aria-live="polite" className="space-y-3">
      {events.map(event => <DiscussionEvent key={event.id} event={event} />)}
      {selected && !events.length && <p>No committed discussion events yet.</p>}
    </section>
  </main>;
}
