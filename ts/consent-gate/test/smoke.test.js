const { test } = require('node:test');
const assert = require('node:assert/strict');
const { scopeCovers, requireSmartScope, requireConsent } = require('../src/index.js');

// ── scopeCovers unit tests ────────────────────────────────────────────────

test('exact scope match', () => {
  assert.equal(true, scopeCovers(new Set(['patient/Observation.read']), 'patient/Observation.read'));
});

test('patient/*.read covers patient/Observation.read', () => {
  assert.equal(true, scopeCovers(new Set(['patient/*.read']), 'patient/Observation.read'));
});

test('user/*.* covers patient/Observation.read', () => {
  assert.equal(true, scopeCovers(new Set(['user/*.*']), 'patient/Observation.read'));
});

test('mismatched verb is rejected', () => {
  assert.equal(false, scopeCovers(new Set(['patient/Observation.read']), 'patient/Observation.write'));
});

test('only Condition scope does not cover Observation', () => {
  assert.equal(false, scopeCovers(new Set(['patient/Condition.read']), 'patient/Observation.read'));
});

// ── middleware tests via mock req/res ─────────────────────────────────────

function mockResponse() {
  return {
    statusCode: 200, body: null,
    status(c) { this.statusCode = c; return this; },
    json(b) { this.body = b; return this; },
  };
}

test('requireSmartScope passes when scope granted', async () => {
  const mw = requireSmartScope('patient/Observation.read');
  const req = { tokenClaims: { scope: 'patient/*.read launch openid' } };
  const res = mockResponse();
  let nextCalled = false;
  await mw(req, res, () => { nextCalled = true; });
  assert.equal(nextCalled, true);
});

test('requireSmartScope fails with 403 when scope missing', async () => {
  const mw = requireSmartScope('patient/Condition.read');
  const req = { tokenClaims: { scope: 'patient/Observation.read' } };
  const res = mockResponse();
  await mw(req, res, () => { throw new Error('next should not be called'); });
  assert.equal(res.statusCode, 403);
  assert.equal(res.body.error, 'insufficient_scope');
  assert.equal(res.body.required, 'patient/Condition.read');
});

test('requireConsent passes with active consent', async () => {
  const mw = requireConsent({
    scope: 'patient/Observation.read',
    getConsent: async () => ({
      status: 'active',
      scopes: ['patient/Observation.read'],
      period_end: null,
    }),
    getCallerApp: () => ({ id: 'app-1' }),
  });
  const req = { params: { patient_id: 'P-1' }, body: {} };
  const res = mockResponse();
  let next = false;
  await mw(req, res, () => { next = true; });
  assert.equal(next, true);
});

test('requireConsent fails 403 when no consent', async () => {
  const mw = requireConsent({
    scope: 'patient/Observation.read',
    getConsent: async () => null,
    getCallerApp: () => ({ id: 'app-1' }),
  });
  const req = { params: { patient_id: 'P-1' }, body: {} };
  const res = mockResponse();
  await mw(req, res, () => { throw new Error('next should not be called'); });
  assert.equal(res.statusCode, 403);
  assert.equal(res.body.error, 'consent_required');
});

test('requireConsent fails 403 when consent expired', async () => {
  const mw = requireConsent({
    scope: 'patient/Observation.read',
    getConsent: async () => ({
      status: 'active',
      scopes: ['patient/Observation.read'],
      period_end: '2020-01-01T00:00:00Z',
    }),
    getCallerApp: () => ({ id: 'app-1' }),
  });
  const req = { params: { patient_id: 'P-1' }, body: {} };
  const res = mockResponse();
  await mw(req, res, () => { throw new Error('next should not be called'); });
  assert.equal(res.statusCode, 403);
  assert.equal(res.body.error, 'consent_expired');
});
