import { z, type ZodType } from 'zod';
import {
  AgentActivityDashboardSchema,
  ApprovalSchema,
  BrokerSchema,
  DashboardEventSchema,
  DashboardSnapshotSchema,
  ExecutionSchema,
  HealthSchema,
  PortfolioSummarySchema,
  PositionSchema,
  QuotesSchema,
  SafetySchema,
  ScanStatusSchema,
  SessionSchema,
  TelemetrySchema,
  TradeSchema,
} from './schemas';

const CommandResponseSchema = z.record(z.string(), z.unknown());
const ApprovalResponseSchema = z
  .object({
    approval_id: z.string(),
    decision: z.string(),
    ticker: z.string(),
    message: z.string().nullable().optional(),
  })
  .passthrough();

type RequestOptions = {
  body?: unknown;
  signal?: AbortSignal;
};

async function request<T>(
  path: string,
  schema: ZodType<T>,
  method = 'GET',
  options: RequestOptions = {},
): Promise<T> {
  const response = await fetch(`/api${path}`, {
    method,
    signal: options.signal,
    headers: options.body === undefined ? undefined : { 'Content-Type': 'application/json' },
    body: options.body === undefined ? undefined : JSON.stringify(options.body),
  });

  if (!response.ok) {
    const message = await response.text();
    throw new Error(`${method} ${path} failed: ${response.status} ${message}`);
  }

  const payload = await response.json();
  return schema.parse(payload);
}

export const api = {
  health: (signal?: AbortSignal) => request('/health', HealthSchema, 'GET', { signal }),
  safety: (signal?: AbortSignal) => request('/ops/safety', SafetySchema, 'GET', { signal }),
  snapshot: (signal?: AbortSignal) =>
    request('/dashboard/snapshot', DashboardSnapshotSchema, 'GET', { signal }),
  events: (limit = 50, afterId?: number, signal?: AbortSignal) => {
    const params = new URLSearchParams({ limit: String(limit) });
    if (afterId !== undefined) {
      params.set('after_id', String(afterId));
    }
    return request(
      `/dashboard/events?${params.toString()}`,
      DashboardEventSchema.array(),
      'GET',
      { signal },
    );
  },
  execution: (signal?: AbortSignal) =>
    request('/dashboard/execution', ExecutionSchema, 'GET', { signal }),
  quotes: (signal?: AbortSignal) =>
    request('/dashboard/quotes', QuotesSchema, 'GET', { signal }),
  broker: (signal?: AbortSignal) =>
    request('/dashboard/broker', BrokerSchema, 'GET', { signal }),
  telemetry: (signal?: AbortSignal) =>
    request('/dashboard/telemetry', TelemetrySchema, 'GET', { signal }),
  activity: (signal?: AbortSignal) =>
    request('/dashboard/activity', AgentActivityDashboardSchema, 'GET', { signal }),
  session: (signal?: AbortSignal) =>
    request('/dashboard/session', SessionSchema, 'GET', { signal }),
  approvals: (signal?: AbortSignal) =>
    request('/approvals', ApprovalSchema.array(), 'GET', { signal }),
  approve: (approvalId: string) =>
    request(
      `/approvals/${encodeURIComponent(approvalId)}/yes`,
      ApprovalResponseSchema,
      'POST',
    ),
  reject: (approvalId: string) =>
    request(
      `/approvals/${encodeURIComponent(approvalId)}/no`,
      ApprovalResponseSchema,
      'POST',
    ),
  positions: (signal?: AbortSignal) =>
    request('/positions', PositionSchema.array(), 'GET', { signal }),
  trades: (signal?: AbortSignal) => request('/trades', TradeSchema.array(), 'GET', { signal }),
  portfolioSummary: (signal?: AbortSignal) =>
    request('/portfolio/summary', PortfolioSummarySchema, 'GET', { signal }),
  scanStatus: (signal?: AbortSignal) =>
    request('/scan/status', ScanStatusSchema, 'GET', { signal }),
  triggerScan: () => request('/scan', ScanStatusSchema.passthrough(), 'POST'),
  updateMode: (body: {
    reason: string;
    trading_enabled?: boolean;
    new_entries_enabled?: boolean;
    exit_only_mode?: boolean;
  }) => request('/ops/mode', CommandResponseSchema, 'POST', { body }),
  flatten: (body: { reason: string; tickers?: string[] }) =>
    request('/ops/flatten', CommandResponseSchema, 'POST', { body }),
  clearFlatten: () => request('/ops/flatten', CommandResponseSchema, 'DELETE'),
  clearBlock: (body: { reason?: string; source?: string }) =>
    request('/ops/block/clear', CommandResponseSchema, 'POST', { body }),
};
