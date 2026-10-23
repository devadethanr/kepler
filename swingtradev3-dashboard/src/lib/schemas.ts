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

export const PolicyOverlaySchema = z
  .object({
    overlay_id: z.string(),
    key: z.string(),
    value: z.unknown(),
    status: z.string(),
    reason: z.string().default(''),
    proposer: z.string().default(''),
    approver: z.string().nullable().optional(),
    expires_at: z.string().nullable().optional(),
    rollback_handle: z.string().default(''),
    payload: z.record(z.string(), z.unknown()).default({}),
  })
  .passthrough();

export const EffectivePolicySchema = z
  .object({
    min_score_threshold: z.number(),
    max_position_size_pct: z.number(),
    new_entries_enabled: z.boolean(),
    max_same_sector_positions: z.number(),
    trail_stop_at_pct: z.number(),
    trail_to_pct: z.number(),
    debate_top_n: z.number(),
    base: z.record(z.string(), z.unknown()).default({}),
    sources: z.record(z.string(), z.string()).default({}),
    applied_overlays: z.array(z.record(z.string(), z.unknown())).default([]),
    ignored_overlays: z.array(z.record(z.string(), z.unknown())).default([]),
    operator_controls: z.record(z.string(), z.unknown()).default({}),
    resolved_at_ist: z.string(),
  })
  .passthrough();

export const PolicyDashboardSchema = z
  .object({
    effective: EffectivePolicySchema,
    overlays: z.array(PolicyOverlaySchema).default([]),
    active_overlays: z.array(PolicyOverlaySchema).default([]),
  })
  .passthrough();

const KnowledgeMetadataSchema = z.record(z.string(), z.unknown()).default({});

export const KnowledgeGraphNodeSchema = z
  .object({
    id: z.string(),
    label: z.string().nullable().optional(),
    name: z.string().nullable().optional(),
    type: z.string().default('unknown'),
    size: z.number().nullable().optional(),
    val: z.number().nullable().optional(),
    color: z.string().nullable().optional(),
    summary: z.string().nullable().optional(),
    metadata: KnowledgeMetadataSchema,
  })
  .passthrough();

export const KnowledgeGraphEdgeSchema = z
  .object({
    source: z.string(),
    target: z.string(),
    label: z.string().nullable().optional(),
    relationship: z.string().nullable().optional(),
    weight: z.number().default(1),
    metadata: KnowledgeMetadataSchema,
  })
  .passthrough();

export const KnowledgeGraphSchema = z
  .object({
    status: z.string().default('available'),
    phase: z.string().nullable().optional(),
    message: z.string().nullable().optional(),
    nodes: z.array(KnowledgeGraphNodeSchema).default([]),
    edges: z.array(KnowledgeGraphEdgeSchema).default([]),
    last_updated: z.string().nullable().optional(),
    counts: z.record(z.string(), z.number()).default({}),
    degraded_reason: z.string().nullable().optional(),
    last_error: z.string().nullable().optional(),
  })
  .passthrough();

export const KnowledgeIndexStockSchema = z
  .object({
    ticker: z.string(),
    note_path: z.string().nullable().optional(),
    scan_count: z.number().default(0),
    avg_score: z.number().default(0),
    last_scanned: z.string().nullable().optional(),
    sector: z.string().nullable().optional(),
    tags: z.array(z.string()).default([]),
  })
  .passthrough();

export const KnowledgeIndexSchema = z
  .object({
    status: z.string().default('available'),
    message: z.string().nullable().optional(),
    stocks: z
      .union([
        z.record(z.string(), KnowledgeIndexStockSchema),
        z.array(KnowledgeIndexStockSchema),
      ])
      .default({}),
    last_updated: z.string().nullable().optional(),
    counts: z.record(z.string(), z.number()).default({}),
    degraded_reason: z.string().nullable().optional(),
    last_error: z.string().nullable().optional(),
  })
  .passthrough();

export const StockKnowledgeSchema = z
  .object({
    status: z.string().default('available'),
    ticker: z.string(),
    summary: z.string().nullable().optional(),
    evidence: z.array(z.record(z.string(), z.unknown())).default([]),
    connections: z.array(z.union([z.string(), z.record(z.string(), z.unknown())])).default([]),
    has_history: z.boolean().optional(),
    last_updated: z.string().nullable().optional(),
    message: z.string().nullable().optional(),
    degraded_reason: z.string().nullable().optional(),
    last_error: z.string().nullable().optional(),
  })
  .passthrough();

export const CognitionRunSchema = z
  .object({
    run_id: z.string(),
    phase: z.string().default('phase_13'),
    status: z.string().default('unknown'),
    started_at: z.string().nullable().optional(),
    completed_at: z.string().nullable().optional(),
    payload: z.record(z.string(), z.unknown()).default({}),
    created_at: z.string().nullable().optional(),
    updated_at: z.string().nullable().optional(),
  })
  .passthrough();

export const CognitionReportSchema = z
  .object({
    report_id: z.string(),
    run_id: z.string(),
    ticker: z.string().nullable().optional(),
    agent_name: z.string(),
    schema_version: z.string().default('unknown'),
    status: z.string().default('unknown'),
    payload: z.record(z.string(), z.unknown()).default({}),
    created_at: z.string().nullable().optional(),
    updated_at: z.string().nullable().optional(),
  })
  .passthrough();

export const CognitionRunsSchema = z
  .object({
    runs: z.array(CognitionRunSchema).default([]),
    count: z.number().default(0),
  })
  .passthrough();

export const CognitionRunDetailSchema = z
  .object({
    run: CognitionRunSchema.nullable().optional(),
    reports: z.array(CognitionReportSchema).default([]),
    count: z.number().default(0),
  })
  .passthrough();

export const CognitionTickerReportsSchema = z
  .object({
    ticker: z.string(),
    reports: z.array(CognitionReportSchema).default([]),
    count: z.number().default(0),
  })
  .passthrough();

export const SessionPlanItemSchema = z
  .object({
    entry_intent_id: z.string().nullable().optional(),
    approval_id: z.string().nullable().optional(),
    order_intent_id: z.string().nullable().optional(),
    ticker: z.string(),
    action: z.string().default('defer'),
    reason: z.string().default(''),
    payload: z.record(z.string(), z.unknown()).default({}),
  })
  .passthrough();

export const SessionPlanPayloadSchema = z
  .object({
    plan_id: z.string().default(''),
    trading_date: z.string().default(''),
    status: z.string().default('unknown'),
    generated_at: z.string().nullable().optional(),
    items: z.array(SessionPlanItemSchema).default([]),
    blocked_reasons: z.array(z.string()).default([]),
    session_readiness: z.record(z.string(), z.unknown()).default({}),
  })
  .passthrough();

export const SessionPlanRecordSchema = z
  .object({
    plan_id: z.string(),
    trading_date: z.string(),
    status: z.string().default('unknown'),
    payload: SessionPlanPayloadSchema.optional(),
    created_at: z.string().nullable().optional(),
    updated_at: z.string().nullable().optional(),
  })
  .passthrough();

export const SessionPlanResponseSchema = z
  .object({
    plan: z.union([SessionPlanPayloadSchema, SessionPlanRecordSchema]).nullable().optional(),
    generated: z.boolean().default(false),
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
export type EffectivePolicy = z.infer<typeof EffectivePolicySchema>;
export type PolicyDashboard = z.infer<typeof PolicyDashboardSchema>;
export type PolicyOverlay = z.infer<typeof PolicyOverlaySchema>;
export type KnowledgeGraph = z.infer<typeof KnowledgeGraphSchema>;
export type KnowledgeGraphNode = z.infer<typeof KnowledgeGraphNodeSchema>;
export type KnowledgeGraphEdge = z.infer<typeof KnowledgeGraphEdgeSchema>;
export type KnowledgeIndex = z.infer<typeof KnowledgeIndexSchema>;
export type KnowledgeIndexStock = z.infer<typeof KnowledgeIndexStockSchema>;
export type StockKnowledge = z.infer<typeof StockKnowledgeSchema>;
export type CognitionRun = z.infer<typeof CognitionRunSchema>;
export type CognitionReport = z.infer<typeof CognitionReportSchema>;
export type CognitionRuns = z.infer<typeof CognitionRunsSchema>;
export type CognitionRunDetail = z.infer<typeof CognitionRunDetailSchema>;
export type CognitionTickerReports = z.infer<typeof CognitionTickerReportsSchema>;
export type SessionPlanItem = z.infer<typeof SessionPlanItemSchema>;
export type SessionPlanPayload = z.infer<typeof SessionPlanPayloadSchema>;
export type SessionPlanRecord = z.infer<typeof SessionPlanRecordSchema>;
export type SessionPlanResponse = z.infer<typeof SessionPlanResponseSchema>;
