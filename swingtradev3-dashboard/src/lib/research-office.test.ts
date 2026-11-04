import test from 'node:test';
import assert from 'node:assert/strict';
import { projectOffice } from './research-office';
import type { Room, RoomEvent } from './research';

// Explicit offline fixtures; no runtime or model access.
const room: Room = { id: 'r', status: 'abstention', question: 'Q', target: 'T', seq: 8,
  counts: { model: 0, tool: 0, reserved_tokens: 0, input_tokens: 0, output_tokens: 0, unknown_usage_calls: 0 } };
const event = (seq: number, kind: string, agent = 'manager', data: Record<string, unknown> = {}): RoomEvent =>
  ({ id: `e${seq}`, room_id: 'r', seq, kind, agent, data, at: '2026-11-03T00:00:00Z' });
const records = [event(1, 'room.created'), event(2, 'room.started'),
  event(3, 'turn.started', 'analyst'), event(4, 'budget.admitted', 'manager', { kind: 'model' }),
  event(5, 'tool.started', 'analyst', { name: 'market_context', call_id: 'c' }),
  event(6, 'tool.result', 'analyst', { name: 'market_context', call_id: 'c', output: { evidence: [] } }),
  event(7, 'message', 'analyst', { text: 'Observed source limits.', recipient: 'skeptic', claims: [] }),
  event(8, 'room.finished', 'manager', { status: 'abstention' })];

test('no selection remains unknown with separate model health', () => {
  const state = projectOffice({ room: null, events: records, connection: 'connected', models: { analyst: { model: 'm', status: 'ready' } } });
  assert.equal(state.agents.analyst.state, 'unknown');
  assert.equal(state.agents.skeptic.state, 'unknown');
  assert.equal(state.agents.analyst.model?.status, 'ready');
  assert.deepEqual(state.events, []);
});

test('replay uses sequence cursor, durable IDs and selected room only', () => {
  const state = projectOffice({ room, events: [...records].reverse().concat(records[4], { ...records[2], id: 'other', room_id: 'other' }), connection: 'saved', cursor: 5 });
  assert.deepEqual(state.events.map(e => e.seq), [1, 2, 3, 4, 5]);
  assert.equal(state.agents.analyst.state, 'tool');
  assert.equal(state.agents.skeptic.state, 'waiting');
  assert.equal(state.messages.length, 0);
});

test('public text drives handoffs and tools retain event references', () => {
  const state = projectOffice({ room, events: [...records, event(7.1, 'message', 'skeptic', { recipient: 'analyst' })], connection: 'saved', cursor: 7.1 });
  assert.equal(state.agents.analyst.state, 'speaking');
  assert.deepEqual(state.handoffs.map(m => [m.eventId, m.text, m.recipient]), [['e7', 'Observed source limits.', 'skeptic']]);
  assert.deepEqual(state.agents.analyst.tools.map(e => e.id), ['e5', 'e6']);
  assert.deepEqual(state.agents.analyst.evidenceEvents.map(e => e.id), ['e6', 'e7']);
});

test('terminal overrides stale observations without leaking into earlier replay', () => {
  const replay = projectOffice({ room, events: records, connection: 'disconnected', cursor: 5 });
  assert.equal(replay.agents.analyst.observedState, 'tool');
  assert.equal(replay.agents.analyst.state, 'unknown');
  const done = projectOffice({ room, events: records, connection: 'stale' });
  assert.equal(done.agents.analyst.state, 'finished');
  assert.equal(done.agents.skeptic.state, 'finished');
  const cancelled = projectOffice({ room: { ...room, status: 'cancelled' }, events: [event(8, 'room.finished', 'manager', { status: 'cancelled' })], connection: 'disconnected' });
  assert.equal(cancelled.agents.analyst.state, 'cancelled');
});

test('turn completion and manager budget do not fabricate agent activity', () => {
  const running = { ...room, status: 'running', seq: 20 };
  const sequence = [event(1, 'room.created'), event(2, 'room.started'), event(3, 'turn.started', 'skeptic'), event(4, 'tool.started', 'skeptic'), event(5, 'tool.result', 'skeptic'), event(6, 'budget.released', 'manager', { kind: 'tool' }), event(7, 'turn.finished', 'skeptic', { status: 'interrupted', published: true })];
  assert.equal(projectOffice({ room: running, events: sequence, connection: 'connected', cursor: 5 }).agents.skeptic.state, 'researching');
  const done = projectOffice({ room: running, events: sequence, connection: 'connected' });
  assert.equal(done.agents.skeptic.state, 'waiting');
  assert.equal(done.agents.analyst.state, 'waiting');
});

test('unknown worker activity suppresses current motion, but does not rewrite replay', () => {
  const uncertain = { ...room, status: 'running', seq: 20, activity_state: 'unknown' };
  const state = projectOffice({ room: uncertain, events: records.slice(0, 5), connection: 'connected' });
  assert.equal(state.agents.analyst.observedState, 'tool');
  assert.equal(state.agents.analyst.state, 'unknown');
  const replay = projectOffice({ room: uncertain, events: records, connection: 'saved', cursor: 5 });
  assert.equal(replay.agents.analyst.state, 'tool');
  const stale = projectOffice({ room: { ...uncertain, activity_state: 'active', worker_state: 'stale' }, events: records.slice(0, 5), connection: 'connected' });
  assert.equal(stale.agents.analyst.state, 'unknown');
});

test('cancellation request and unknown terminal outcome never claim a completed result', () => {
  const running = { ...room, status: 'running', seq: 20 };
  const cancel = projectOffice({ room: running, events: [...records.slice(0, 5), event(6, 'room.cancel_requested')], connection: 'connected' });
  assert.equal(cancel.agents.analyst.observedState, 'tool');
  assert.equal(cancel.agents.analyst.state, 'unknown');
  const unknown = projectOffice({ room: running, events: [...records.slice(0, 5), event(6, 'room.finished', 'manager', { status: 'new_status' })], connection: 'connected' });
  assert.equal(unknown.agents.analyst.state, 'unknown');
});
