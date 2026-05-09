import { z } from 'zod';

export const HealthSchema = z.object({
  status: z.string(),
  mode: z.string().optional(),
  services: z.record(z.string(), z.string()).default({}),
});

export const PortfolioSummarySchema = z.object({
  cash_inr: z.number().default(0),
  realized_pnl: z.number().default(0),
  unrealized_pnl: z.number().default(0),
  total_pnl: z.number().default(0),
  open_positions_count: z.number().default(0),
  sector_exposure: z.record(z.string(), z.number()).default({}),
  total_invested: z.number().default(0),
  drawdown_pct: z.number().optional(),
  weekly_loss_pct: z.number().optional(),
  consecutive_losses: z.number().optional(),
});

export const PositionSchema = z
  .object({
    ticker: z.string(),
    quantity: z.number(),
    entry_price: z.number(),
    current_price: z.number().nullable().optional(),
    stop_price: z.number(),
    target_price: z.number(),
    opened_at: z.string(),
    entry_order_id: z.string().nullable().optional(),
    product: z.string().optional(),
    oco_gtt_id: z.string().nullable().optional(),
    lifecycle_state: z.string().default('open'),
    thesis_score: z.number().nullable().optional(),
    sector: z.string().nullable().optional(),
  })
  .passthrough();

export const ApprovalSchema = z
  .object({
    ticker: z.string(),
    score: z.number(),
    setup_type: z.string(),
    entry_zone: z.object({ low: z.number(), high: z.number() }).passthrough(),
    stop_price: z.number(),
    target_price: z.number(),
    confidence_reasoning: z.string(),
    risk_flags: z.array(z.string()).default([]),
    sector: z.string().nullable().optional(),
    approved: z.boolean().nullable().optional(),
    approval_id: z.string(),
    entry_intent_id: z.string().nullable().optional(),
    order_intent_id: z.string().nullable().optional(),
    execution_requested: z.boolean().default(false),
    execution_request_id: z.string().nullable().optional(),
    status: z.string().nullable().optional(),
    expires_at: z.string(),
  })
  .passthrough();

export const TradeSchema = z
  .object({
    trade_id: z.string(),
    ticker: z.string(),
    quantity: z.number(),
    entry_price: z.number(),
    exit_price: z.number(),
    opened_at: z.string(),
    closed_at: z.string(),
    exit_reason: z.string(),
    pnl_abs: z.number(),
    pnl_pct: z.number(),
  })
  .passthrough();

export const DashboardEventSchema = z
  .object({
    event_id: z.number(),
    event_type: z.string(),
    entity_type: z.string(),
    entity_id: z.string(),
    source: z.string(),
    payload: z.record(z.string(), z.unknown()).default({}),
    created_at: z.string().nullable().optional(),
  })
  .passthrough();

const CountMapSchema = z.record(z.string(), z.number()).default({});

export const SessionSegmentSchema = z
  .object({
    key: z.string(),
    label: z.string(),
    start: z.string(),
    end: z.string(),
    duration_minutes: z.number(),
    width_pct: z.number(),
    active: z.boolean(),
    elapsed_pct: z.number(),
  })
  .passthrough();

export const SessionSchema = z
  .object({
    timezone: z.string(),
    current_time: z.string(),
    trading_day: z.boolean(),
    holiday: z.string().nullable().optional(),
    market_status: z.string(),
    current_phase: z.string(),
    wallclock_phase: z.string(),
    phase_label: z.string(),
    day_label: z.string(),
    segments: z.array(SessionSegmentSchema),
  })
  .passthrough();

export const DashboardSnapshotSchema = z
  .object({
    portfolio: PortfolioSummarySchema,
    account: z.record(z.string(), z.unknown()).default({}),
    counts: z.record(z.string(), z.number()).default({}),
    status_counts: z.record(z.string(), CountMapSchema).default({}),
    positions: z.array(PositionSchema).default([]),
    approvals: z.array(ApprovalSchema).default([]),
    recent_trades: z.array(TradeSchema).default([]),
    open_incidents: z.array(z.record(z.string(), z.unknown())).default([]),
    worker_status: z.record(z.string(), z.unknown()).default({}),
    latest_event_id: z.number().nullable().optional(),
    session: SessionSchema.optional(),
  })
  .passthrough();

export const ExecutionSchema = z
  .object({
    positions: z.array(z.record(z.string(), z.unknown())).default([]),
    entry_intents: z.array(z.record(z.string(), z.unknown())).default([]),
    order_intents: z.array(z.record(z.string(), z.unknown())).default([]),
    broker_orders: z.array(z.record(z.string(), z.unknown())).default([]),
    broker_fills: z.array(z.record(z.string(), z.unknown())).default([]),
    protective_triggers: z.array(z.record(z.string(), z.unknown())).default([]),
    reconciliation_runs: z.array(z.record(z.string(), z.unknown())).default([]),
    incidents: z.array(z.record(z.string(), z.unknown())).default([]),
    status_counts: z.record(z.string(), CountMapSchema).default({}),
  })
  .passthrough();

export const SafetySchema = z.record(z.string(), z.unknown());

export const QuotesSchema = z
  .object({
    quotes: z.array(z.record(z.string(), z.unknown())).default([]),
    count: z.number().default(0),
  })
  .passthrough();

export const BrokerSchema = z
  .object({
    auth_session: z.record(z.string(), z.unknown()).default({}),
    broker_orders: z.array(z.record(z.string(), z.unknown())).default([]),
    broker_fills: z.array(z.record(z.string(), z.unknown())).default([]),
    status_counts: z.record(z.string(), CountMapSchema).default({}),
  })
  .passthrough();

export const TelemetrySchema = z
  .object({
    worker_status: z.record(z.string(), z.unknown()).default({}),
    events: z.array(DashboardEventSchema).default([]),
    operator_controls: z.array(z.record(z.string(), z.unknown())).default([]),
    event_type_counts: CountMapSchema,
    source_counts: CountMapSchema,
  })
  .passthrough();

export const AgentActivitySchema = z
  .object({
    agent_name: z.string(),
    status: z.string().default('unknown'),
    current_task: z.string().nullable().optional(),
    started_at: z.string().nullable().optional(),
    completed_at: z.string().nullable().optional(),
    progress: z.string().nullable().optional(),
    last_error: z.string().nullable().optional(),
    metadata: z.record(z.string(), z.unknown()).default({}),
  })
  .passthrough();

export const ObservedSourceSchema = z
  .object({
    agent_name: z.string(),
    status: z.string().default('observed'),
    event_count: z.number().default(0),
    last_event: z.string().nullable().optional(),
    updated_at: z.string().nullable().optional(),
  })
  .passthrough();

export const ScanStatusSchema = z
  .object({
    status: z.string(),
    started_at: z.string().nullable().optional(),
    completed_at: z.string().nullable().optional(),
    progress: z.string().nullable().optional(),
    result: z.unknown().nullable().optional(),
  })
  .passthrough();

export const AgentActivityDashboardSchema = z
  .object({
    agents: z.array(AgentActivitySchema).default([]),
    observed_sources: z.array(ObservedSourceSchema).default([]),
    scheduler_phase: z.string().default('unknown'),
    last_updated: z.string().nullable().optional(),
    worker_status: z.record(z.string(), z.unknown()).default({}),
    scan_status: ScanStatusSchema,
    session: SessionSchema,
    recent_events: z.array(DashboardEventSchema).default([]),
    event_count: z.number().default(0),
  })
  .passthrough();

export const NewsItemSchema = z
  .object({
    provider: z.string().default('unknown'),
    source_type: z.string().default('unknown'),
    title: z.string(),
    url: z.string().nullable().optional(),
    canonical_url: z.string().nullable().optional(),
    summary: z.string().nullable().optional(),
    published_at_ist: z.string().nullable().optional(),
    fetched_at_ist: z.string().nullable().optional(),
    tickers: z.array(z.string()).default([]),
    category: z.string().default('unknown'),
    confidence: z.number().default(0),
  })
  .passthrough();

export const NewsProviderHealthSchema = z
  .object({
    provider: z.string(),
    enabled: z.boolean().default(true),
    status: z.string().optional(),
    last_success_at_ist: z.string().nullable().optional(),
    last_failure_at_ist: z.string().nullable().optional(),
    last_error: z.string().nullable().optional(),
    items_seen: z.number().default(0),
    items_emitted: z.number().default(0),
    dedupe_drops: z.number().default(0),
    empty_extractions: z.number().default(0),
    latency_ms: z.number().default(0),
  })
  .passthrough();

export const NewsDashboardSchema = z
  .object({
    items: z.array(NewsItemSchema).default([]),
    provider_health: z.record(z.string(), NewsProviderHealthSchema).default({}),
    source_counts: CountMapSchema,
    source_type_counts: CountMapSchema,
    category_counts: CountMapSchema,
    item_count: z.number().default(0),
    last_updated_at_ist: z.string().nullable().optional(),
  })
  .passthrough();

export type DashboardSnapshot = z.infer<typeof DashboardSnapshotSchema>;
export type DashboardEvent = z.infer<typeof DashboardEventSchema>;
export type ExecutionDashboard = z.infer<typeof ExecutionSchema>;
export type Health = z.infer<typeof HealthSchema>;
export type Safety = z.infer<typeof SafetySchema>;
export type Approval = z.infer<typeof ApprovalSchema>;
export type Position = z.infer<typeof PositionSchema>;
export type Trade = z.infer<typeof TradeSchema>;
export type Session = z.infer<typeof SessionSchema>;
export type AgentActivity = z.infer<typeof AgentActivitySchema>;
export type AgentActivityDashboard = z.infer<typeof AgentActivityDashboardSchema>;
export type NewsDashboard = z.infer<typeof NewsDashboardSchema>;
export type NewsItem = z.infer<typeof NewsItemSchema>;
export type NewsProviderHealth = z.infer<typeof NewsProviderHealthSchema>;
