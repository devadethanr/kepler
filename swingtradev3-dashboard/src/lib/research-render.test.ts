import test from 'node:test';
import assert from 'node:assert/strict';
import React from 'react';
import { renderToStaticMarkup } from 'react-dom/server';
import { DiscussionEvent, ResearchDeskScreen } from '../screens/ResearchDeskScreen';
import { RoomEventSchema } from './research';

test('desk renders on a LAN origin with only getRandomValues', () => {
  const original = Object.getOwnPropertyDescriptor(globalThis, 'crypto');
  Object.defineProperty(globalThis, 'crypto', { configurable: true, value: {
    getRandomValues: (bytes: Uint8Array) => { bytes.fill(1); return bytes; },
  } });
  try {
    const html = renderToStaticMarkup(React.createElement(ResearchDeskScreen));
    assert.match(html, /Start research/);
    assert.match(html, /Loading saved rooms/);
  } finally {
    if (original) Object.defineProperty(globalThis, 'crypto', original);
    else Reflect.deleteProperty(globalThis, 'crypto');
  }
});

test('claim rendering distinguishes model assessment and exact quotation', () => {
  const event = RoomEventSchema.parse({ id: 'e', room_id: 'r', seq: 1, kind: 'message', agent: 'analyst', at: '2026-11-01', data: {
    text: 'Interpretation', claims: [{ id: 'c', text: 'A claim', kind: 'inference', support_assessment: 'supported', quote: 'A real quote', evidence_id: 'source' }],
  } });
  const html = renderToStaticMarkup(React.createElement(DiscussionEvent, { event }));
  assert.match(html, /narrative unassessed/);
  assert.match(html, /Model support proposal: supported/);
  assert.match(html, /Excerpt verified/);
});

test('source evidence distinguishes publication precision, retrieval and identity', async () => {
  const { SourceEvidence, SourceStatus } = await import('../screens/ResearchDeskScreen');
  const html = renderToStaticMarkup(React.createElement(SourceEvidence, { packet: {
    source_snapshot: { coverage: 'partial', requested_cutoff: '2026-11-01T00:00:00Z' },
    content: { sources: [{ source_id: 'sebi', source_type: 'regulator', version_id: 'v1',
      published_raw: '01 Nov 2026', precision: 'date', timezone_basis: 'Asia/Kolkata',
      first_seen_at: '2026-11-02T00:00:00Z', fetched_at: '2026-11-02T01:00:00Z',
      identity_basis: 'text mention', availability: 'unknown', completeness: 'partial',
      canonical_url: 'https://example.org/item' }] },
    quote_spans: [{ id: 'q:1', text: 'Actual excerpt', start: 0, end: 14 }],
  } }));
  for (const expected of ['partial', 'sebi', 'v1', '01 Nov 2026', 'Precision: date', 'Asia/Kolkata', 'First seen:', 'Fetched:', 'text mention', 'Actual excerpt', 'offsets 0–14']) assert.ok(html.includes(expected), expected);
  const status = renderToStaticMarkup(React.createElement(SourceStatus, { value: { sources: [{ source_id: 'rbi', status: 'empty', entry_count: 0 }], coverage: 'incomplete' }, error: '' }));
  assert.match(status, /incomplete/);
  assert.match(status, /empty/);
  assert.match(status, /Entries: 0/);
});

test('market context labels instrument, provenance and unknown data without inventing a quote', async () => {
  const { MarketContextStatus, SourceEvidence } = await import('../screens/ResearchDeskScreen');
  const unavailable = { snapshot_id: 's1', symbol: 'GIFT', instrument_kind: 'future', status: 'unavailable', quote_value: 123, reference_value: 456, delay_seconds: null, quality_reasons: ['no entitlement'], market_state: 'closed', market_state_at_cutoff: 'open', contract_specification: 'historical specification', source_document_sha256: 'abc' };
  const html = renderToStaticMarkup(React.createElement(MarketContextStatus, { value: { observations: [unavailable], coverage: 'partial', limits: ['no history'] }, error: '' }));
  for (const expected of ['Future', 'Quote unavailable', 'Reference: unavailable', 'Delay: unknown', 'no entitlement', 'no history', 'Snapshot ID: s1', 'Market state at observation: closed', 'Market state at cutoff: open', 'historical specification', 'Source document SHA-256: abc']) assert.ok(html.includes(expected), expected);
  assert.doesNotMatch(html, /Quote: 123/);
  assert.doesNotMatch(html, /Reference: 456/);
  const saved = renderToStaticMarkup(React.createElement(SourceEvidence, { packet: { market_snapshot: { ...unavailable, symbol: 'STI proxy', instrument_kind: 'proxy', status: 'ok', quote_value: 12, quote_unit: 'points', delay_seconds: 900, exchange_asof: '2026-11-02T00:00:00Z' } } }));
  for (const expected of ['Saved market evidence', 'Proxy', 'Quote: 12 points', '900 seconds', 'UTC', 'IST', 'Singapore']) assert.ok(saved.includes(expected), expected);
  assert.match(renderToStaticMarkup(React.createElement(MarketContextStatus, { value: null, error: 'network' })), /Market context unavailable/);
});

test('stale market quotes retain their status and unknown identity fields', async () => {
  const { MarketObservation } = await import('../screens/ResearchDeskScreen');
  const html = renderToStaticMarkup(React.createElement(MarketObservation, { item: {
    symbol: 'STI', instrument_kind: 'cash_index', status: 'stale', market_state: null,
    quote_value: 1234, quote_unit: null, contract: null, delay_seconds: null,
    exchange_asof: '2026-11-02T00:00:00', quality_reasons: ['old observation'],
  } }));
  for (const expected of ['Cash index', 'Status: stale', 'Market state at observation: unknown', 'Market state at cutoff: unknown', 'Quote: 1234 unknown', 'Contract: unknown', 'Delay: unknown', 'timezone unknown', 'old observation']) assert.ok(html.includes(expected), expected);
});
