// Controlled offline probe of the actual selected-room effect and event projector.
// No browser, database, provider, broker or model operation occurs.
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { createRequire } from 'node:module';
import { resolve } from 'node:path';
import { pathToFileURL } from 'node:url';

const root = process.cwd();
const require = createRequire(resolve(root, 'swingtradev3-dashboard/package.json'));
const ts = require('typescript');
const { projectOffice } = await import(pathToFileURL(resolve(root,
  'swingtradev3-dashboard/src/lib/research-office.ts')).href);
const { mergeRoomEvents, shouldStreamRoom, RoomEventSchema, terminalStatuses } =
  await import(pathToFileURL(resolve(root, 'swingtradev3-dashboard/src/lib/research.ts')).href);
const filename = resolve(root, 'swingtradev3-dashboard/src/screens/ResearchDeskScreen.tsx');
const text = readFileSync(filename, 'utf8');
const ast = ts.createSourceFile(filename, text, ts.ScriptTarget.Latest, true, ts.ScriptKind.TSX);
let effect;
function find(node) {
  if (ts.isCallExpression(node) && node.expression.getText(ast) === 'useEffect' &&
      node.arguments[0]?.getText(ast).includes('let terminalSynced = false')) effect = node.arguments[0];
  ts.forEachChild(node, find);
}
find(ast);
assert.ok(effect, 'Locate the actual selected-room effect, without reimplementing it');
let now = 1_000_000, seq = 2, historyReads = 0, poll;
const state = { room: null, events: [], lastSync: 0, connection: '', error: '' };
const update = key => value => { state[key] = typeof value === 'function' ? value(state[key]) : value; };
const event = (n, kind, data = {}) => ({ id: `offline-${n}`, room_id: 'offline-room',
  seq: n, kind, agent: 'analyst', at: '2026-11-04T00:00:00Z', data });
const initial = [event(1, 'turn.started'), event(2, 'tool.started', { name: 'fixture-only' })];
class OpenSilentSource {
  static OPEN = 1;
  static instance;
  readyState = 1;
  constructor() { OpenSilentSource.instance = this; }
  close() { this.readyState = 2; }
  addEventListener() { /* Intentionally deliver no subsequent events. */ }
}
const dependencies = {
  selected: 'offline-room',
  research: {
    get: async () => ({ id: 'offline-room', seq, status: 'running', activity_state: 'active',
      worker_state: 'alive', question: 'Offline transport probe', target: 'fixture', counts: {} }),
    events: async () => { historyReads++; return { events: initial, cursor: 2 }; },
  },
  EventSource: OpenSilentSource, terminal: terminalStatuses, mergeRoomEvents,
  shouldStreamRoom, RoomEventSchema,
  Date: { now: () => now }, setInterval: fn => { poll = fn; return 1; }, clearInterval: () => {},
  setRoom: update('room'), setEvents: update('events'), setLastSync: update('lastSync'),
  setConnection: update('connection'), setError: update('error'),
};
const compiled = ts.transpileModule(`const runEffect = ${effect.getText(ast)};`, {
  compilerOptions: { target: ts.ScriptTarget.ES2022, module: ts.ModuleKind.None },
}).outputText;
const cleanup = new Function(...Object.keys(dependencies), compiled + '\nreturn runEffect();')
  (...Object.values(dependencies));
const flush = () => new Promise(resolve => setImmediate(resolve));
await flush();
OpenSilentSource.instance.onopen();
for (let n = 0; n < 10; n++) {
  now += 2000; seq++;
  await poll(); await flush();
}
const transportStale = state.connection === 'Unavailable' || state.connection.startsWith('Reconnecting') ||
  (state.lastSync > 0 && now - state.lastSync > 12000);
const scene = projectOffice({ room: state.room, events: state.events,
  connection: transportStale ? 'disconnected' : state.connection === 'Live' ? 'connected' : 'saved' });
assert.equal(state.connection, 'Live');
assert.equal(state.events.at(-1).seq, 2);
assert.equal(state.room.seq, 12);
assert.equal(scene.agents.analyst.state, 'tool');
assert.equal(historyReads, 1);
const broadcast = projectOffice({ room: state.room,
  events: [event(3, 'message', { text: 'Offline broadcast', recipient: 'room' })], connection: 'saved' });
assert.equal(broadcast.messages[0].recipient, null);
console.log(JSON.stringify({
  type: 'offline_actual_effect_probe', source_commit: '5b3db54',
  delivered_event_seq: 2, polled_snapshot_seq: state.room.seq, elapsed_ms: 20000,
  history_reads: historyReads, connection: state.connection,
  current_agent_state: scene.agents.analyst.state, milliseconds_since_last_sync: now - state.lastSync,
  bug: 'Successful snapshot polling masks a missing event history; working motion remains enabled.',
  broadcast_input_recipient: 'room', broadcast_projected_recipient: broadcast.messages[0].recipient,
  model_calls: 0, tool_admissions: 0, provider_requests: 0,
}, null, 2));
cleanup();
