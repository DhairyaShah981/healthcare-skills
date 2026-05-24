const { test } = require('node:test');
const assert = require('node:assert/strict');
const { scrubString, scrubObject } = require('../src/index.js');

test('scrubs SSN, email, phone, DOB, MRN from a free-text string', () => {
  const input = "Maria's SSN is 123-45-6789, phone 415-555-0173, " +
                "email m@example.com, MRN8829340, DOB 1962-04-11.";
  const out = scrubString(input);
  assert.match(out, /\[PHI:SSN\]/);
  assert.match(out, /\[PHI:EMAIL\]/);
  assert.match(out, /\[PHI:PHONE\]/);
  assert.match(out, /\[PHI:MRN\]/);
  assert.match(out, /\[PHI:DOB:year=1962\]/);
  assert.doesNotMatch(out, /123-45-6789/);
  assert.doesNotMatch(out, /1962-04-11/);
});

test('scrubObject replaces PHI keys but preserves allowlist', () => {
  const input = {
    event: 'patient_loaded',
    patient_id: 'P9981',
    patient_name: 'Maria Hernandez',
    dob: '1962-04-11',
    phone: '415-555-0173',
    note: "Called daughter at j@example.com, MRN8829340 confirmed.",
  };
  const out = scrubObject(input, new Set(['event', 'patient_id']));
  assert.equal(out.event, 'patient_loaded');
  assert.equal(out.patient_id, 'P9981');
  assert.equal(out.patient_name, '[PHI:NAME]');
  assert.equal(out.dob, '[PHI:DOB:year=1962]');
  assert.equal(out.phone, '[PHI:PHONE]');
  assert.match(out.note, /\[PHI:EMAIL\]/);
  assert.match(out.note, /\[PHI:MRN\]/);
});

test('scrubObject handles nested objects + arrays', () => {
  const input = {
    request_id: 'r1',
    patient: { name: 'Jane Doe', dob: '1980-01-01', tags: ['urgent', 'mrn 4421337'] },
  };
  const out = scrubObject(input, new Set(['request_id']));
  assert.equal(out.request_id, 'r1');
  assert.equal(out.patient.name, '[PHI:NAME]');
  assert.equal(out.patient.dob, '[PHI:DOB:year=1980]');
  assert.ok(Array.isArray(out.patient.tags));
  assert.equal(out.patient.tags[0], 'urgent');
});

test('returns input unchanged when no PHI present', () => {
  assert.equal(scrubString('hello world'), 'hello world');
  const o = { trace_id: 'abc', count: 5, ok: true };
  assert.deepEqual(scrubObject(o, new Set()), o);
});
