import { z } from 'zod';

export const RoomSchema = z.object({
  id: z.string(), status: z.string(), question: z.string(), target: z.string(), seq: z.number(), worker_state: z.string().optional(),
  counts: z.object({ model: z.number(), tool: z.number(), reserved_tokens: z.number(),
    input_tokens: z.number(), output_tokens: z.number(), unknown_usage_calls: z.number() }),
}).passthrough();
export const RoomEventSchema = z.object({
  id: z.string(), room_id: z.string(), seq: z.number(), kind: z.string(), agent: z.string(),
  at: z.string(), data: z.record(z.string(), z.unknown()),
});
export type Room = z.infer<typeof RoomSchema>;
export type RoomEvent = z.infer<typeof RoomEventSchema>;

export const terminalStatuses = new Set(['conclusion', 'disagreement', 'abstention', 'cancelled', 'interrupted', 'failed']);

/** UUID v4 using browser cryptographic randomness, including on HTTP LAN origins. */
export function newRequestId(cryptoApi: Crypto = globalThis.crypto): string {
  if (typeof cryptoApi?.randomUUID === 'function') return cryptoApi.randomUUID();
  if (typeof cryptoApi?.getRandomValues !== 'function') throw new Error('Secure random numbers are unavailable');
  const bytes = cryptoApi.getRandomValues(new Uint8Array(16));
  bytes[6] = (bytes[6] & 0x0f) | 0x40;
  bytes[8] = (bytes[8] & 0x3f) | 0x80;
  const hex = Array.from(bytes, byte => byte.toString(16).padStart(2, '0')).join('');
  return `${hex.slice(0, 8)}-${hex.slice(8, 12)}-${hex.slice(12, 16)}-${hex.slice(16, 20)}-${hex.slice(20)}`;
}

export function shouldStreamRoom(room: Room, events: RoomEvent[]): boolean {
  return !terminalStatuses.has(room.status) && !events.some(event => event.kind === 'room.finished');
}

export function mergeRoomEvents(current: RoomEvent[], incoming: RoomEvent[]): RoomEvent[] {
  const byId = new Map(current.map((event) => [event.id, event]));
  for (const event of incoming) byId.set(event.id, event);
  return [...byId.values()].sort((a, b) => a.seq - b.seq);
}

async function request(path: string, body?: unknown) {
  const response = await fetch(`/api/research${path}`, {
    method: body === undefined ? 'GET' : 'POST',
    headers: body === undefined ? undefined : { 'Content-Type': 'application/json' },
    body: body === undefined ? undefined : JSON.stringify(body),
  });
  if (!response.ok) throw new Error(`Research API ${response.status}: ${await response.text()}`);
  return response.json();
}
export const research = {
  health: async () => z.object({ status: z.string(), models: z.record(z.string(), z.object({ model: z.string(), status: z.string() })) }).parse(await request('/health')),
  list: async () => z.object({ rooms: RoomSchema.array() }).parse(await request('/rooms')).rooms,
  get: async (id: string) => RoomSchema.parse(await request(`/rooms/${encodeURIComponent(id)}`)),
  create: async (target: string, question: string, requestId: string) => RoomSchema.parse(
    await request('/rooms', { target, question, request_id: requestId })),
  retry: async (id: string, requestId: string) => RoomSchema.parse(await request(`/rooms/${encodeURIComponent(id)}/retry`, { request_id: requestId })),
  cancel: async (id: string) => RoomSchema.parse(await request(`/rooms/${encodeURIComponent(id)}/cancel`, {})),
  events: async (id: string, after = 0) => z.object({ events: RoomEventSchema.array(), cursor: z.number() })
    .parse(await request(`/rooms/${encodeURIComponent(id)}/events?after=${after}`)),
};
