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
