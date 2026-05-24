const { test } = require('node:test');
const assert = require('node:assert/strict');
const { lint, summarize } = require('../src/index.js');

test('clean agent passes all rules', () => {
  const agent = {
    language: 'en-US',
    conversationFlow: {
      is_transfer_cf: false, start_node_id: 'n1',
      nodes: [{ id: 'n1', type: 'start' }, { id: 'n2', type: 'function', tool_id: 'check' }],
      edges: [{ id: 'e1', source_node_id: 'n1', destination_node_id: 'n2' }],
    },
    tools: [{ name: 'check', url: 'https://api.example.com/check',
              parameters: { type: 'object', required: ['date'],
                            properties: { date: { type: 'string', description: 'ISO date' } } } }],
  };
  const f = lint(agent);
  assert.equal(f.length, 0);
  assert.equal(summarize(f).verdict, 'OK');
});

test('detects RTL-001 (missing is_transfer_cf)', () => {
  const f = lint({ conversationFlow: { start_node_id: 'n1', nodes: [{ id: 'n1', type: 'start' }] } });
  assert.equal(f.some(x => x.rule === 'RTL-001'), true);
});

test('detects RTL-002 (empty parameters.required)', () => {
  const f = lint({ conversationFlow: { is_transfer_cf: false, start_node_id: 'n1', nodes: [{ id: 'n1', type: 'start' }] },
                   tools: [{ name: 'x', url: 'https://x', parameters: { type: 'object', required: [],
                              properties: { a: { type: 'string', description: 'a' } } } }] });
  assert.equal(f.some(x => x.rule === 'RTL-002'), true);
});

test('detects RTL-003 (unknown tool_id)', () => {
  const f = lint({ conversationFlow: { is_transfer_cf: false, start_node_id: 'n1',
                     nodes: [{ id: 'n1', type: 'start' }, { id: 'n2', type: 'function', tool_id: 'ghost' }] } });
  assert.equal(f.some(x => x.rule === 'RTL-003'), true);
});

test('detects RTL-004 (unresolved destination_node_id)', () => {
  const f = lint({ conversationFlow: { is_transfer_cf: false, start_node_id: 'n1',
                     nodes: [{ id: 'n1', type: 'start' }],
                     edges: [{ id: 'e1', destination_node_id: 'missing' }] } });
  assert.equal(f.some(x => x.rule === 'RTL-004'), true);
});

test('detects RTL-008 (non-BCP-47 language)', () => {
  const f = lint({ language: 'english',
                   conversationFlow: { is_transfer_cf: false, start_node_id: 'n1', nodes: [{ id: 'n1', type: 'start' }] } });
  assert.equal(f.some(x => x.rule === 'RTL-008'), true);
});

test('detects RTL-016 (ngrok URL) but accepts <<PLACEHOLDER>>', () => {
  const bad = lint({ conversationFlow: { is_transfer_cf: false, start_node_id: 'n1', nodes: [{ id: 'n1', type: 'start' }] },
                     tools: [{ name: 't', url: 'https://abc.ngrok.io/x',
                                parameters: { type: 'object', required: ['a'],
                                  properties: { a: { type: 'string', description: 'a' } } } }] });
  assert.equal(bad.some(x => x.rule === 'RTL-016'), true);

  const ok = lint({ conversationFlow: { is_transfer_cf: false, start_node_id: 'n1', nodes: [{ id: 'n1', type: 'start' }] },
                    tools: [{ name: 't', url: '<<TOOL_URL>>',
                               parameters: { type: 'object', required: ['a'],
                                 properties: { a: { type: 'string', description: 'a' } } } }] });
  assert.equal(ok.some(x => x.rule === 'RTL-016'), false);
});

test('summarize gives BLOCK DEPLOY when any ERROR is present', () => {
  const f = lint({ language: 'english',
                   conversationFlow: { is_transfer_cf: false, start_node_id: 'n1', nodes: [{ id: 'n1', type: 'start' }] } });
  const s = summarize(f);
  assert.equal(s.verdict, 'BLOCK DEPLOY');
  assert.ok(s.errors >= 1);
});
