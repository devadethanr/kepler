import test from 'node:test';
import assert from 'node:assert/strict';
import React from 'react';
import { renderToStaticMarkup } from 'react-dom/server';
import { ResearchOffice, officeLayout } from '../components/research-office/ResearchOffice';
import { projectOffice } from './research-office';

test('unselected office presents both configured agents and unknown room state', () => {
  const scene = projectOffice({ room: null, events: [], connection: 'saved', models: {
    analyst: { model: 'analyst-model', status: 'healthy' },
    skeptic: { model: 'skeptic-model', status: 'unavailable' },
  } });
  const html = renderToStaticMarkup(React.createElement(ResearchOffice, {
    scene, onSelectAgent: () => {}, onSelectMessage: () => {},
  }));
  for (const text of ['Research office', 'No room selected', 'analyst-model: healthy', 'skeptic-model: unavailable', 'Open analyst details, unknown', 'Open skeptic details, unknown']) assert.ok(html.includes(text), text);
  assert.doesNotMatch(html, /Open analyst message/);
});

test('real messages have accessible controls and matching discussion positions', () => {
  const scene = projectOffice({ room: null, events: [], connection: 'saved' });
  scene.agents.analyst.state = 'speaking';
  scene.agents.analyst.messages.push({ eventId: 'event-1', seq: 1, agent: 'analyst', text: 'Evidence needs review', recipient: 'skeptic', replyTo: null });
  const layout = officeLayout(scene);
  assert.equal(layout.analyst.character.x, 390);
  assert.equal(layout.skeptic.character.x, 733);
  const html = renderToStaticMarkup(React.createElement(ResearchOffice, {
    scene, onSelectAgent: () => {}, onSelectMessage: () => {},
  }));
  assert.match(html, /Open analyst message: Evidence needs review/);
  assert.match(html, /analyst → skeptic/);
  assert.match(html, /Message: Evidence needs review/);
  assert.doesNotMatch(html, /Open skeptic message/);
  scene.agents.analyst.messages[0].recipient = null;
  const noRecipient = renderToStaticMarkup(React.createElement(ResearchOffice, { scene, onSelectAgent: () => {}, onSelectMessage: () => {} }));
  assert.doesNotMatch(noRecipient, /→/);
});
