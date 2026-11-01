import test from 'node:test';
import assert from 'node:assert/strict';
import { mergeRoomEvents, newRequestId, research, RoomEventSchema, RoomSchema, shouldStreamRoom } from './research';

test('room replay deduplicates history, reconnect and live delivery by durable event id', () => {
  const first = RoomEventSchema.parse({ id: 'a', room_id: 'r', seq: 1, kind: 'message', agent: 'analyst', at: '2026-11-01T00:00:00Z', data: { text: 'quoted' } });
  const second = { ...first, id: 'b', seq: 2, agent: 'skeptic' };
  assert.deepEqual(mergeRoomEvents([second], [first, second, first]), [first, second]);
  assert.throws(() => RoomEventSchema.parse({ ...first, seq: 'invented' }));
});


test('request IDs remain UUID v4 when randomUUID is unavailable on an HTTP LAN origin', () => {
  const api = { getRandomValues: (bytes: Uint8Array) => { bytes.fill(255); return bytes; } } as unknown as Crypto;
  assert.equal(newRequestId(api), 'ffffffff-ffff-4fff-bfff-ffffffffffff');
  assert.throws(() => newRequestId({} as Crypto), /Secure random/);
});

test('terminal room state and terminal history suppress the event stream', () => {
  const room = RoomSchema.parse({ id: 'r', status: 'cancelled', question: 'q', target: 't', seq: 0,
    counts: { model: 0, tool: 0, reserved_tokens: 0, input_tokens: 0, output_tokens: 0, unknown_usage_calls: 0 } });
  const finish = RoomEventSchema.parse({ id: 'e', room_id: 'r', seq: 1, kind: 'room.finished', agent: 'system', at: '2026-11-01', data: {} });
  assert.equal(shouldStreamRoom(room, []), false);
  assert.equal(shouldStreamRoom({ ...room, status: 'running' }, [finish]), false);
  assert.equal(shouldStreamRoom({ ...room, status: 'running' }, []), true);
});


test('retry sends the caller’s same request ID after a lost response', async () => {
  const original = globalThis.fetch;
  const bodies: unknown[] = [];
  const room = { id: 'child', status: 'queued', question: 'question', target: 't', seq: 0,
    counts: { model: 0, tool: 0, reserved_tokens: 0, input_tokens: 0, output_tokens: 0, unknown_usage_calls: 0 } };
  globalThis.fetch = async (_input, init) => {
    bodies.push(JSON.parse(String(init?.body)));
    if (bodies.length === 1) throw new TypeError('connection lost');
    return new Response(JSON.stringify(room), { status: 200 });
  };
  try {
    await assert.rejects(research.retry('parent', 'same-request-id'), /connection lost/);
    assert.equal((await research.retry('parent', 'same-request-id')).id, 'child');
    assert.deepEqual(bodies, [{ request_id: 'same-request-id' }, { request_id: 'same-request-id' }]);
  } finally { globalThis.fetch = original; }
});
