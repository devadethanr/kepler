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
  retry: async (id: string) => RoomSchema.parse(await request(`/rooms/${encodeURIComponent(id)}/retry`, { request_id: crypto.randomUUID() })),
  cancel: async (id: string) => RoomSchema.parse(await request(`/rooms/${encodeURIComponent(id)}/cancel`, {})),
  events: async (id: string, after = 0) => z.object({ events: RoomEventSchema.array(), cursor: z.number() })
    .parse(await request(`/rooms/${encodeURIComponent(id)}/events?after=${after}`)),
};
