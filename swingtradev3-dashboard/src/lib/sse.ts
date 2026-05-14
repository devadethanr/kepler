import { fetchEventSource, type FetchEventSourceInit } from '@microsoft/fetch-event-source';
import { DashboardEventSchema, type DashboardEvent } from './schemas';

export type LiveEvent =
  | { type: 'ready'; cursor: number | null }
  | { type: 'heartbeat'; cursor: number | null }
  | { type: 'execution_event'; event: DashboardEvent };

type FetchEventSourceClient = (
  input: RequestInfo,
  init: FetchEventSourceInit,
) => Promise<void>;

export function connectLiveEvents(options: {
  afterId?: number | null;
  retryDelayMs?: number;
  signal?: AbortSignal;
  onEvent: (event: LiveEvent) => void;
  onError?: (error: unknown) => void;
}, eventSource: FetchEventSourceClient = fetchEventSource) {
  const params = new URLSearchParams();
  if (options.afterId !== undefined && options.afterId !== null) {
    params.set('after_id', String(options.afterId));
  }
  const url = `/api/sse/live${params.toString() ? `?${params.toString()}` : ''}`;

  return eventSource(url, {
    signal: options.signal,
    openWhenHidden: true,
    onmessage(message) {
      const parsed = JSON.parse(message.data);
      if (message.event === 'ready') {
        options.onEvent({ type: 'ready', cursor: parsed.cursor ?? null });
        return;
      }
      if (message.event === 'heartbeat') {
        options.onEvent({ type: 'heartbeat', cursor: parsed.cursor ?? null });
        return;
      }
      options.onEvent({
        type: 'execution_event',
        event: DashboardEventSchema.parse(parsed.data),
      });
    },
    onerror(error) {
      options.onError?.(error);
      return options.retryDelayMs;
    },
  });
}
