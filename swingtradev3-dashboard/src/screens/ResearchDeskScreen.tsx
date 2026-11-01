import React, { useEffect, useState } from 'react';
import { mergeRoomEvents, research, RoomEventSchema, type Room, type RoomEvent } from '../lib/research';

const terminal = new Set(['conclusion', 'disagreement', 'abstention', 'cancelled', 'interrupted', 'failed']);
const text = (value: unknown) => typeof value === 'string' ? value : '';

function DiscussionEvent({ event }: { event: RoomEvent }) {
  const data = event.data;
  if (event.kind === 'message') {
    const claims = Array.isArray(data.claims) ? data.claims as Record<string, unknown>[] : [];
    return <article className="rounded border border-slate-700 bg-slate-900 p-4" aria-label={`${event.agent} message`}>
      <div className="text-sm text-cyan-300">{event.agent} → {text(data.recipient)} · {text(data.kind)} · {text(data.stance)}</div>
      <p className="mt-2 text-xs text-slate-400">Agent interpretation · excerpts are verified separately below</p>
      <p className="my-3 whitespace-pre-wrap text-slate-100">{text(data.text)}</p>
      {claims.map((claim, i) => <blockquote key={i} className="my-2 border-l-2 border-cyan-600 pl-3 text-sm">
        <p>{text(claim.quote)}</p>
        <p className="text-slate-400">{text(claim.evidence_id)} · {text(claim.source)} · freshness: {text(claim.freshness)}</p>
      </blockquote>)}
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
  const [room, setRoom] = useState<Room | null>(null);
  const [events, setEvents] = useState<RoomEvent[]>([]);
  const [target, setTarget] = useState('');
  const [question, setQuestion] = useState('');
  const [error, setError] = useState('');
  const [connection, setConnection] = useState('Disconnected');
  const [busy, setBusy] = useState(false);
  const [models, setModels] = useState('Checking local model services');
  const [requestId, setRequestId] = useState(() => crypto.randomUUID());

  useEffect(() => {
    let live = true;
    const refresh = () => research.list().then(value => { if (live) setRooms(value); })
      .catch(err => { if (live) setError(String(err)); });
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
    setEvents([]); setRoom(null); setConnection('Connecting');
    const refresh = () => research.get(selected).then(value => {
      if (!live) return;
      setRoom(value);
    }).catch(err => { if (live) setError(String(err)); });
    void refresh();
    research.events(selected).then(history => {
      if (!live) return;
      setEvents(history.events);
      source = new EventSource(`/api/research/rooms/${encodeURIComponent(selected)}/stream?after=${history.cursor}`);
      source.onopen = () => { if (live) { setConnection('Live'); setError(''); } };
      source.onerror = () => { if (live) setConnection('Reconnecting — showing saved discussion'); };
      source.addEventListener('room', raw => {
        try {
          const event = RoomEventSchema.parse(JSON.parse((raw as MessageEvent).data));
          if (!live) return;
          setEvents(previous => mergeRoomEvents(previous, [event]));
          void refresh();
          if (event.kind === 'room.finished') { source?.close(); setConnection('Saved discussion'); }
        } catch (err) { if (live) setError(`Invalid room event: ${String(err)}`); }
      });
      if (history.events.some(event => event.kind === 'room.finished')) {
        source.close(); setConnection('Saved discussion');
      }
    }).catch(err => { if (live) setError(String(err)); });
    const timer = setInterval(refresh, 2000);
    return () => { live = false; source?.close(); clearInterval(timer); };
  }, [selected]);

  async function start(event: React.FormEvent) {
    event.preventDefault(); setBusy(true); setError('');
    try {
      const result = await research.create(target, question, requestId);
      setSelected(result.id); setRequestId(crypto.randomUUID());
    } catch (err) { setError(String(err)); }
    finally { setBusy(false); }
  }
  return <main className="flex-1 overflow-auto p-5 text-slate-200">
    <h1 className="text-2xl font-semibold">Research Desk</h1>
    <p className="my-2 text-sm text-slate-400">Analyst and skeptic · read-only research · live entries require your approval</p>
    <p className="text-xs text-slate-400" role="status">{models}. A running research worker processes queued rooms.</p>
    <form onSubmit={start} className="my-4 flex flex-wrap gap-3">
      <label className="flex flex-col text-sm">Target
        <input required maxLength={64} value={target} onChange={e => { setTarget(e.target.value); setRequestId(crypto.randomUUID()); }}
          className="rounded border border-slate-600 bg-slate-900 p-2" placeholder="RELIANCE" />
      </label>
      <label className="flex min-w-64 flex-1 flex-col text-sm">Research question
        <textarea required minLength={8} maxLength={3000} value={question}
          onChange={e => { setQuestion(e.target.value); setRequestId(crypto.randomUUID()); }}
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
    {room && <section className="my-4" aria-label="Room status">
      <div className="flex flex-wrap items-center gap-3"><h2 className="font-semibold">{room.target}: {room.question}</h2>
        <span role="status">{room.status} · {room.worker_state === 'stale' ? 'Worker lease expired; awaiting recovery' : connection}</span>
        {terminal.has(room.status) && <button className="rounded border border-slate-600 px-3 py-1" onClick={() => {
          research.retry(room.id).then(value => setSelected(value.id)).catch(err => setError(String(err)));
        }}>Retry as new room</button>}
        {!terminal.has(room.status) && <button className="rounded border border-red-700 px-3 py-1" onClick={() => {
          research.cancel(room.id).then(setRoom).catch(err => setError(String(err)));
        }}>Cancel research</button>}
      </div>
      <p className="my-2 text-xs text-slate-400">Model calls {room.counts.model} · Tools {room.counts.tool} · Actual tokens {room.counts.input_tokens + room.counts.output_tokens} · Unknown-usage calls {room.counts.unknown_usage_calls} · Reserved context tokens {room.counts.reserved_tokens}</p>
    </section>}
    <section aria-label="Research discussion" aria-live="polite" className="space-y-3">
      {events.map(event => <DiscussionEvent key={event.id} event={event} />)}
      {selected && !events.length && <p>No committed discussion events yet.</p>}
    </section>
  </main>;
}
