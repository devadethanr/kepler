import assert from 'node:assert/strict';
import { test } from 'node:test';
import type { FetchEventSourceInit } from '@microsoft/fetch-event-source';
import type { EventSourceMessage } from '@microsoft/fetch-event-source/lib/esm/parse';

import { connectLiveEvents, type LiveEvent } from './sse';

type CapturedCall = {
  input: RequestInfo;
  init: FetchEventSourceInit;
};

function message(event: string, data: unknown): EventSourceMessage {
  return {
    id: '',
    event,
    data: JSON.stringify(data),
  };
}

function dashboardEvent(eventId: number) {
  return {
    event_id: eventId,
    event_type: 'order_submitted',
    entity_type: 'order_intent',
    entity_id: `order-${eventId}`,
    source: 'unit-test',
    payload: { ticker: 'RELIANCE' },
    created_at: '2026-05-04T09:15:00+05:30',
  };
}

test('connectLiveEvents resumes SSE from the supplied cursor', async () => {
  let captured: CapturedCall | undefined;
  const controller = new AbortController();

  await connectLiveEvents(
    {
      afterId: 42,
      signal: controller.signal,
      onEvent() {},
    },
    async (input, init) => {
      captured = { input, init };
    },
  );

  assert.equal(captured?.input, '/api/sse/live?after_id=42');
  assert.equal(captured?.init.signal, controller.signal);
  assert.equal(captured?.init.openWhenHidden, true);
});

test('connectLiveEvents emits ready, heartbeat, and execution events in stream order', async () => {
  const received: LiveEvent[] = [];

  await connectLiveEvents(
    {
      onEvent(event) {
        received.push(event);
      },
    },
    async (_input, init) => {
      init.onmessage?.(message('ready', { cursor: 10 }));
      init.onmessage?.(message('heartbeat', { cursor: 11 }));
      init.onmessage?.(message('execution_event', { data: dashboardEvent(12) }));
      init.onmessage?.(message('execution_event', { data: dashboardEvent(13) }));
    },
  );

  assert.deepEqual(received.map((event) => event.type), [
    'ready',
    'heartbeat',
    'execution_event',
    'execution_event',
  ]);
  assert.equal(received[0]?.type === 'ready' ? received[0].cursor : null, 10);
  assert.equal(received[1]?.type === 'heartbeat' ? received[1].cursor : null, 11);
  assert.equal(
    received[2]?.type === 'execution_event' ? received[2].event.event_id : null,
    12,
  );
  assert.equal(
    received[3]?.type === 'execution_event' ? received[3].event.event_id : null,
    13,
  );
});

test('connectLiveEvents lets fetch-event-source retry after errors', async () => {
  const streamError = new Error('stream dropped');
  let observedError: unknown;
  let retryDelay: number | null | undefined | void;

  await connectLiveEvents(
    {
      retryDelayMs: 1500,
      onEvent() {},
      onError(error) {
        observedError = error;
      },
    },
    async (_input, init) => {
      retryDelay = init.onerror?.(streamError);
    },
  );

  assert.equal(observedError, streamError);
  assert.equal(retryDelay, 1500);
});
