import test from 'node:test';
import assert from 'node:assert/strict';
import { mergeRoomEvents, RoomEventSchema } from './research';

test('room replay deduplicates history, reconnect and live delivery by durable event id', () => {
  const first = RoomEventSchema.parse({ id: 'a', room_id: 'r', seq: 1, kind: 'message', agent: 'analyst', at: '2026-11-01T00:00:00Z', data: { text: 'quoted' } });
  const second = { ...first, id: 'b', seq: 2, agent: 'skeptic' };
  assert.deepEqual(mergeRoomEvents([second], [first, second, first]), [first, second]);
  assert.throws(() => RoomEventSchema.parse({ ...first, seq: 'invented' }));
});
