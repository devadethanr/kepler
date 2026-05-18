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
    jsonResponse({
      status: 'ok',
      mode: 'paper',
      services: {
        app: 'running',
        postgres_memory_views: 'healthy',
        memgraph_context_graph: 'degraded',
        toolbox: 'healthy',
        local_llm: 'disabled',
      },
    }),
  );
  const controller = new AbortController();

  const health = await api.health(controller.signal);

  assert.deepEqual(health, {
    status: 'ok',
    mode: 'paper',
    services: {
      app: 'running',
      postgres_memory_views: 'healthy',
      memgraph_context_graph: 'degraded',
      toolbox: 'healthy',
      local_llm: 'disabled',
    },
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

test('api client fetches policy dashboard payloads', async () => {
  const calls = installFetch(() =>
    jsonResponse({
      effective: {
        min_score_threshold: 7,
        max_position_size_pct: 40,
        new_entries_enabled: true,
        max_same_sector_positions: 2,
        trail_stop_at_pct: 5,
        trail_to_pct: 10,
        debate_top_n: 3,
        base: {},
        sources: {},
        applied_overlays: [],
        ignored_overlays: [],
        operator_controls: {},
        resolved_at_ist: '2026-05-09T09:15:00+05:30',
      },
      overlays: [],
      active_overlays: [],
    }),
  );

  const policy = await api.policyDashboard();

  assert.equal(calls.length, 1);
  assert.equal(calls[0]?.input, '/api/dashboard/policy');
  assert.equal(policy.effective.max_position_size_pct, 40);
});

test('api client fetches knowledge graph payloads', async () => {
  const calls = installFetch(() =>
    jsonResponse({
      status: 'available',
      nodes: [
        {
          id: 'stock:RELIANCE',
          label: 'RELIANCE',
          type: 'Stock',
          size: 4,
          metadata: { sector: 'Energy' },
        },
      ],
      edges: [
        {
          source: 'stock:RELIANCE',
          target: 'sector:Energy',
          relationship: 'BELONGS_TO_SECTOR',
          weight: 0.9,
        },
      ],
      last_updated: '2026-05-10T09:15:00+05:30',
    }),
  );

  const graph = await api.knowledgeGraph();

  assert.equal(calls.length, 1);
  assert.equal(calls[0]?.input, '/api/dashboard/knowledge/graph');
  assert.equal(graph.nodes[0]?.metadata.sector, 'Energy');
  assert.equal(graph.edges[0]?.relationship, 'BELONGS_TO_SECTOR');
});

test('api client fetches knowledge index payloads', async () => {
  const calls = installFetch(() =>
    jsonResponse({
      status: 'degraded',
      message: 'Memgraph fallback is serving a partial index.',
      stocks: {
        RELIANCE: {
          ticker: 'RELIANCE',
          sector: 'Energy',
          scan_count: 3,
          avg_score: 7.5,
        },
      },
    }),
  );

  const index = await api.knowledgeIndex();

  assert.equal(calls.length, 1);
  assert.equal(calls[0]?.input, '/api/dashboard/knowledge/index');
  assert.equal(index.status, 'degraded');
  assert.equal(Array.isArray(index.stocks), false);
});

test('api client fetches stock knowledge payloads with encoded ticker', async () => {
  const calls = installFetch(() =>
    jsonResponse({
      status: 'available',
      ticker: 'M&M',
      summary: 'Autos candidate with recurring setup history.',
      evidence: [{ source: 'ResearchRun', confidence: 0.8 }],
      connections: ['sector:Auto'],
      has_history: true,
    }),
  );

  const stock = await api.stockKnowledge('M&M');

  assert.equal(calls.length, 1);
  assert.equal(calls[0]?.input, '/api/dashboard/knowledge/stock/M%26M');
  assert.equal(stock.ticker, 'M&M');
  assert.equal(stock.evidence.length, 1);
});

test('api client fetches Phase 13 cognition runs and reports', async () => {
  const calls = installFetch((call) => {
    if (String(call.input).includes('/dashboard/cognition/runs/phase13%3Arun')) {
      return jsonResponse({
        run: {
          run_id: 'phase13:run',
          phase: 'phase_13',
          status: 'completed',
          started_at: '2026-05-17T08:45:00+05:30',
          payload: {
            diagnostics: { approval_candidates: 1 },
          },
        },
        reports: [
          {
            report_id: 'phase13:run:SBIN:final',
            run_id: 'phase13:run',
            ticker: 'SBIN',
            agent_name: 'final_intent_judge',
            status: 'proposed',
            payload: { decision: 'BUY_ONLY_ABOVE_TRIGGER' },
          },
        ],
        count: 1,
      });
    }
    return jsonResponse({
      runs: [
        {
          run_id: 'phase13:run',
          phase: 'phase_13',
          status: 'completed',
          started_at: '2026-05-17T08:45:00+05:30',
          payload: {
            diagnostics: { scan_candidates: 4, approval_candidates: 1 },
          },
        },
      ],
      count: 1,
    });
  });

  const runs = await api.cognitionRuns(5);
  const run = await api.cognitionRun('phase13:run');

  assert.equal(calls[0]?.input, '/api/dashboard/cognition/runs?limit=5');
  assert.equal(calls[1]?.input, '/api/dashboard/cognition/runs/phase13%3Arun');
  assert.deepEqual(runs.runs[0]?.payload.diagnostics, {
    scan_candidates: 4,
    approval_candidates: 1,
  });
  assert.equal(run.reports[0]?.agent_name, 'final_intent_judge');
});

test('api client fetches Phase 13 ticker reports and session plan payloads', async () => {
  const calls = installFetch((call) => {
    if (String(call.input).includes('/dashboard/session-plan')) {
      return jsonResponse({
        generated: false,
        plan: {
          plan_id: 'session-plan:2026-05-17:084500',
          trading_date: '2026-05-17',
          status: 'ready',
          payload: {
            plan_id: 'session-plan:2026-05-17:084500',
            status: 'ready',
          },
        },
      });
    }
    return jsonResponse({
      ticker: 'M&M',
      reports: [
        {
          report_id: 'phase13:run:MM:thesis',
          run_id: 'phase13:run',
          ticker: 'M&M',
          agent_name: 'thesis_agent',
          status: 'ok',
          payload: { confidence_score: 7 },
        },
      ],
      count: 1,
    });
  });

  const reports = await api.cognitionReports('M&M', 25);
  const plan = await api.sessionPlan('2026-05-17');

  assert.equal(calls[0]?.input, '/api/dashboard/cognition/reports/M%26M?limit=25');
  assert.equal(calls[1]?.input, '/api/dashboard/session-plan?trading_date=2026-05-17');
  assert.equal(reports.reports[0]?.ticker, 'M&M');
  assert.equal(plan.plan?.status, 'ready');
});

test('api client rejects payloads that fail Zod validation', async () => {
  installFetch(() => jsonResponse({ status: 200, services: {} }));

  await assert.rejects(api.health(), ZodError);
});

test('api client includes response text in non-2xx errors', async () => {
  installFetch(() => new Response('forbidden', { status: 403 }));

  await assert.rejects(api.health(), /GET \/health failed: 403 forbidden/);
});
