import React, { useEffect, useRef, useState } from 'react';
import { mergeRoomEvents, newRequestId, research, RoomEventSchema, shouldStreamRoom, terminalStatuses, type Room, type RoomEvent } from '../lib/research';

const terminal = terminalStatuses;
const text = (value: unknown) => typeof value === 'string' ? value : '';

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
        {claim.metadata_policy != null && <p className="text-slate-400">Metadata policy: {typeof claim.metadata_policy === 'string' ? claim.metadata_policy : JSON.stringify(claim.metadata_policy)}</p>}
      </div>)}
      <p className="text-xs text-slate-400">{text(data.validation)} · {new Date(event.at).toLocaleTimeString()}</p>
    </article>;
  }
  return <details className="rounded border border-slate-800 p-2 text-sm text-slate-400">
    <summary>{event.agent} · {event.kind}{data.name ? ` · ${text(data.name)}` : ''}</summary>
    <pre className="max-h-72 overflow-auto whitespace-pre-wrap p-2 text-xs">{JSON.stringify(data, null, 2)}</pre>
  </details>;
}

export function ResearchDeskScreen() {
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
  const retryInFlight = useRef(false);
  const retryIds = useRef(new Map<string, string>());
  const [models, setModels] = useState('Checking local model services');
  const [requestId, setRequestId] = useState(() => newRequestId());

  useEffect(() => {
    let live = true;
    const refresh = () => research.list().then(value => { if (live) { setRooms(value); setRoomsLoading(false); setError(previous => previous.startsWith('Saved rooms unavailable:') ? '' : previous); } })
      .catch(err => { if (live) { setRoomsLoading(false); setError(`Saved rooms unavailable: ${String(err)}`); } });
    const health = () => research.health().then(value => { if (live) setModels(
      Object.entries(value.models).map(([role, model]) => `${role}: ${model.model} · ${model.status}`).join(' / ') || value.status,
    ); }).catch(() => { if (live) setModels('Local model health unavailable'); });
    void refresh(); void health();
    const timer = setInterval(() => { void refresh(); void health(); }, 5000);
    return () => { live = false; clearInterval(timer); };
  }, []);
  useEffect(() => {
    if (!selected) return;
    let live = true;
    let source: EventSource | undefined;
    let initialized = false;
    let initializing = false;
    let terminalSynced = false;
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
    const refresh = () => research.get(selected).then(value => {
      if (!live) return;
      setRoom(value);
      setError(previous => previous.startsWith('Room unavailable:') ? '' : previous);
      if (terminal.has(value.status)) syncTerminal();
    }).catch(err => { if (live) setError(`Room unavailable: ${String(err)}`); });
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
  return <main className="flex-1 overflow-auto p-5 text-slate-200">
    <h1 className="text-2xl font-semibold">Research Desk</h1>
    <p className="my-2 text-sm text-slate-400">Analyst and skeptic · read-only research · live entries require your approval</p>
    <p className="text-xs text-slate-400" role="status">{models}. A running research worker processes queued rooms.</p>
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
    <p className="text-xs text-slate-400">{roomsLoading ? 'Loading saved rooms…' : rooms.length ? 'Showing recent rooms. Open older rooms by ID.' : 'No saved rooms shown.'}</p>
    {room && <section className="my-4" aria-label="Room status">
      <div className="flex flex-wrap items-center gap-3"><h2 className="font-semibold">{room.target}: {room.question}</h2>
        <span role="status">{room.status} · {room.worker_state === 'stale' ? 'Worker lease expired; awaiting recovery' : connection}</span>
        {terminal.has(room.status) && <button disabled={retryBusy} className="rounded border border-slate-600 px-3 py-1 disabled:opacity-50" onClick={() => { void retry(room.id); }}>Retry as new room</button>}
        {!terminal.has(room.status) && <button className="rounded border border-red-700 px-3 py-1" onClick={() => {
          research.cancel(room.id).then(setRoom).catch(err => setError(String(err)));
        }}>Cancel research</button>}
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
