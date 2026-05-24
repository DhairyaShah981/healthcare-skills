const { test } = require('node:test');
const assert = require('node:assert/strict');
const { audited, AuditStore } = require('../src/index.js');

test('records a success row, hashes PHI args, returns result', async () => {
  const store = new AuditStore();
  const getPatient = audited({
    action: 'patient.read',
    phiArgs: ['patient_id'],
    resourceArg: 'patient_id',
    resourceType: 'Patient',
    getActor: () => ({ id: 'user:42', type: 'user' }),
    getTraceId: () => '01HF7T...',
    store,
  })(async ({ patient_id }) => ({ id: patient_id, name: '[REDACTED]' }));

  const out = await getPatient({ patient_id: 'P-9981' });
  assert.equal(out.id, 'P-9981');
  assert.equal(store.rows.length, 1);
  const r = store.rows[0];
  assert.equal(r.actor_id, 'user:42');
  assert.equal(r.action, 'patient.read');
  assert.equal(r.resource_type, 'Patient');
  assert.equal(r.resource_id, 'P-9981');
  assert.match(r.args_hash, /^sha256:[a-f0-9]{64}$/);
  assert.equal(r.outcome, 'success');
  assert.equal(r.trace_id, '01HF7T...');
});

test('records a failure row when the wrapped fn throws', async () => {
  const store = new AuditStore();
  const explode = audited({
    action: 'patient.read',
    phiArgs: ['patient_id'],
    store,
  })(async () => { throw new Error('not found'); });

  await assert.rejects(() => explode({ patient_id: 'P-X' }), /not found/);
  assert.equal(store.rows.length, 1);
  assert.equal(store.rows[0].outcome, 'failure');
  assert.match(store.rows[0].error, /not found/);
});

test('NEVER stores raw PHI values', async () => {
  const store = new AuditStore();
  const wrapped = audited({
    action: 'patient.read',
    phiArgs: ['patient_name', 'dob'],
    store,
  })(async () => ({}));
  await wrapped({ patient_name: 'Maria Hernandez', dob: '1962-04-11' });
  const serialized = JSON.stringify(store.rows[0]);
  assert.doesNotMatch(serialized, /Maria Hernandez/);
  assert.doesNotMatch(serialized, /1962-04-11/);
});
