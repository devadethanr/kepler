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
