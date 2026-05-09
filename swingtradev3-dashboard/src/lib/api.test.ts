import assert from 'node:assert/strict';
import { afterEach, test } from 'node:test';
import { ZodError } from 'zod';

import { api } from './api';

type FetchCall = {
  input: RequestInfo | URL;
  init?: RequestInit;
};

const originalFetch = globalThis.fetch;

function jsonResponse(payload: unknown, init: ResponseInit = {}) {
  return new Response(JSON.stringify(payload), {
    status: 200,
    headers: { 'Content-Type': 'application/json' },
    ...init,
  });
}

function installFetch(handler: (call: FetchCall) => Response | Promise<Response>) {
  const calls: FetchCall[] = [];
  globalThis.fetch = (async (input: RequestInfo | URL, init?: RequestInit) => {
    const call = { input, init };
    calls.push(call);
    return handler(call);
  }) as typeof fetch;
  return calls;
}

afterEach(() => {
  globalThis.fetch = originalFetch;
});

test('api client sends same-origin GET requests through the /api proxy', async () => {
  const calls = installFetch(() =>
    jsonResponse({ status: 'ok', mode: 'paper', services: { app: 'running' } }),
  );
  const controller = new AbortController();

  const health = await api.health(controller.signal);

  assert.deepEqual(health, {
    status: 'ok',
    mode: 'paper',
    services: { app: 'running' },
  });
  assert.equal(calls.length, 1);
  assert.equal(calls[0]?.input, '/api/health');
  assert.equal(calls[0]?.init?.method, 'GET');
  assert.equal(calls[0]?.init?.signal, controller.signal);
  assert.equal(calls[0]?.init?.headers, undefined);
  assert.equal(calls[0]?.init?.body, undefined);
});

test('api client serializes command bodies with JSON request headers', async () => {
  const calls = installFetch(() => jsonResponse({ ok: true }));

  await api.updateMode({ reason: 'unit-test', trading_enabled: false });

  assert.equal(calls.length, 1);
  assert.equal(calls[0]?.input, '/api/ops/mode');
  assert.equal(calls[0]?.init?.method, 'POST');
  assert.deepEqual(calls[0]?.init?.headers, { 'Content-Type': 'application/json' });
  assert.equal(
    calls[0]?.init?.body,
    JSON.stringify({ reason: 'unit-test', trading_enabled: false }),
  );
});

test('api client builds durable event cursor query parameters', async () => {
  const calls = installFetch(() => jsonResponse([]));

  const events = await api.events(25, 1234);

  assert.deepEqual(events, []);
  assert.equal(calls.length, 1);
  assert.equal(calls[0]?.input, '/api/dashboard/events?limit=25&after_id=1234');
});

test('api client fetches news dashboard payloads', async () => {
  const calls = installFetch(() =>
    jsonResponse({
      items: [
        {
          provider: 'nse_corporate_announcements_rss',
          source_type: 'official_filing',
          title: 'Reliance board meeting',
          url: 'https://nseindia.com/a',
          tickers: ['RELIANCE'],
          category: 'corporate_action',
          confidence: 0.95,
        },
      ],
      provider_health: {
        nse_corporate_announcements_rss: {
          provider: 'nse_corporate_announcements_rss',
          enabled: true,
          status: 'healthy',
          items_seen: 1,
          items_emitted: 1,
        },
      },
      source_counts: { nse_corporate_announcements_rss: 1 },
      source_type_counts: { official_filing: 1 },
      category_counts: { corporate_action: 1 },
      item_count: 1,
    }),
  );

  const news = await api.newsDashboard(25);

  assert.equal(calls.length, 1);
  assert.equal(calls[0]?.input, '/api/dashboard/news?limit=25');
  assert.equal(news.items[0]?.tickers[0], 'RELIANCE');
  assert.equal(news.provider_health.nse_corporate_announcements_rss.items_emitted, 1);
});

test('api client rejects payloads that fail Zod validation', async () => {
  installFetch(() => jsonResponse({ status: 200, services: {} }));

  await assert.rejects(api.health(), ZodError);
});

test('api client includes response text in non-2xx errors', async () => {
  installFetch(() => new Response('forbidden', { status: 403 }));

  await assert.rejects(api.health(), /GET \/health failed: 403 forbidden/);
});
