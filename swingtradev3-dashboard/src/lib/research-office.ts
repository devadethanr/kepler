import { terminalStatuses, type Room, type RoomEvent } from './research';

export type OfficeAgentId = 'analyst' | 'skeptic';
export type OfficeAgentState = 'unknown' | 'queued' | 'researching' | 'tool' | 'waiting' | 'speaking' | 'finished' | 'failed' | 'cancelled';
export type OfficeConnection = 'connected' | 'disconnected' | 'stale' | 'saved';
export type OfficeModel = { model: string; status: string };
export type OfficeMessage = {
  eventId: string; seq: number; agent: OfficeAgentId; text: string;
  recipient: OfficeAgentId | null; replyTo: string | null;
};
export type OfficeAgent = {
  id: OfficeAgentId; state: OfficeAgentState; observedState: OfficeAgentState;
  model: OfficeModel | null; messages: OfficeMessage[]; tools: RoomEvent[]; evidenceEvents: RoomEvent[];
};
export type OfficeState = {
  roomId: string | null; agents: Record<OfficeAgentId, OfficeAgent>; events: RoomEvent[];
  messages: OfficeMessage[]; handoffs: OfficeMessage[]; cursor: number;
  connection: OfficeConnection; asOf: string | null;
};
export type OfficeInput = {
  room: Room | null; events: RoomEvent[]; connection: OfficeConnection;
  asOf?: string | null; cursor?: number | null;
  models?: Partial<Record<OfficeAgentId, OfficeModel>>;
};

const ids: OfficeAgentId[] = ['analyst', 'skeptic'];
const isAgent = (value: unknown): value is OfficeAgentId => value === 'analyst' || value === 'skeptic';
const terminalState = (status: unknown): OfficeAgentState | null => {
  if (status === 'cancelled') return 'cancelled';
  if (status === 'failed' || status === 'interrupted') return 'failed';
  if (typeof status === 'string' && terminalStatuses.has(status)) return 'finished';
  return null;
};

/** Project only durable room records; current model health is separate metadata. */
export function projectOffice(input: OfficeInput): OfficeState {
  const { room, connection } = input;
  const agents = Object.fromEntries(ids.map(id => [id, {
    id, state: 'unknown', observedState: 'unknown', model: input.models?.[id] ?? null,
    messages: [], tools: [], evidenceEvents: [],
  }])) as Record<OfficeAgentId, OfficeAgent>;
  const byId = new Map<string, RoomEvent>();
  // Filtering before deduplication prevents another room's record from shadowing this room.
  const candidates = input.events.filter(e => room && e.room_id === room.id &&
    (input.cursor == null || e.seq <= input.cursor));
  // Pick a stable representative even if malformed duplicate IDs disagree.
  candidates.sort((a, b) => a.seq - b.seq || a.id.localeCompare(b.id) ||
    JSON.stringify(a).localeCompare(JSON.stringify(b)));
  for (const event of candidates) if (!byId.has(event.id)) byId.set(event.id, event);
  const events = [...byId.values()];
  const messages: OfficeMessage[] = [];
  const activeTurns = new Set<OfficeAgentId>();
  let terminal: OfficeAgentState | null = null;
  let cancelRequested = false;
  for (const event of events) {
    if (event.kind === 'room.created') {
      for (const id of ids) agents[id].observedState = 'queued';
    } else if (event.kind === 'room.started') {
      for (const id of ids) if (agents[id].observedState === 'queued') agents[id].observedState = 'waiting';
    } else if (event.kind === 'room.finished') {
      terminal = terminalState(event.data.status) ?? 'unknown';
    } else if (event.kind === 'room.cancel_requested') {
      cancelRequested = true;
    }
    if (!isAgent(event.agent)) continue;
    const agent = agents[event.agent];
    switch (event.kind) {
      case 'thread.started':
        agent.observedState = 'waiting';
        break;
      case 'turn.started':
        activeTurns.add(event.agent);
        agent.observedState = 'researching';
        break;
      case 'turn.finished':
      case 'turn.completed':
        activeTurns.delete(event.agent);
        agent.observedState = event.data.status === 'failed' || event.data.error ? 'failed' : 'waiting';
        break;
      case 'tool.started':
        agent.tools.push(event);
        agent.observedState = 'tool';
        break;
      case 'tool.result':
      case 'tool.rejected':
        agent.tools.push(event);
        if (event.kind === 'tool.result') agent.evidenceEvents.push(event);
        agent.observedState = activeTurns.has(event.agent) ? 'researching' : 'waiting';
        break;
      case 'message': {
        if (typeof event.data.text !== 'string' || !event.data.text.trim()) break;
        const message: OfficeMessage = {
          eventId: event.id, seq: event.seq, agent: event.agent, text: event.data.text,
          recipient: isAgent(event.data.recipient) ? event.data.recipient : null,
          replyTo: typeof event.data.reply_to === 'string' ? event.data.reply_to : null,
        };
        messages.push(message);
        agent.messages.push(message);
        agent.evidenceEvents.push(event);
        agent.observedState = 'speaking';
        break;
      }
    }
  }
  // The room snapshot is current, so it cannot describe an earlier replay position.
  if (!terminal && room && (input.cursor == null || input.cursor >= room.seq)) {
    terminal = terminalState(room.status);
  }
  for (const id of ids) {
    if (terminal) agents[id].observedState = terminal;
    const observed = agents[id].observedState;
    const currentActivityUnknown = input.cursor == null &&
      (room?.activity_state === 'unknown' || room?.worker_state === 'stale');
    agents[id].state = !terminal && (cancelRequested || currentActivityUnknown || connection === 'stale' || connection === 'disconnected') &&
      ['queued', 'researching', 'tool', 'waiting', 'speaking'].includes(observed) ? 'unknown' : observed;
  }
  return {
    roomId: room?.id ?? null, agents, events, messages,
    handoffs: messages.filter(message => message.recipient !== null && message.recipient !== message.agent),
    cursor: input.cursor ?? events.at(-1)?.seq ?? 0, connection, asOf: input.asOf ?? null,
  };
}
