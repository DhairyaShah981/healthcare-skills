const { test } = require('node:test');
const assert = require('node:assert/strict');
const { makeVault, scanForPhiLeaks } = require('../src/index.js');

test('pseudonym is deterministic per (kind, original) under the same key', () => {
  const v = makeVault({ key: 'k1' });
  assert.equal(v.pseudonym('MRN', 'M-001'), v.pseudonym('MRN', 'M-001'));
  assert.notEqual(v.pseudonym('MRN', 'M-001'), v.pseudonym('MRN', 'M-002'));
  assert.notEqual(v.pseudonym('MRN', 'M-001'), v.pseudonym('name', 'M-001')); // kind matters
});

test('different keys produce different pseudonyms', () => {
  const a = makeVault({ key: 'k1' });
  const b = makeVault({ key: 'k2' });
  assert.notEqual(a.pseudonym('MRN', 'M-001'), b.pseudonym('MRN', 'M-001'));
});

test('deidentifyBundle scrubs PHI on Patient and rewrites references', () => {
  const v = makeVault({ key: 'staging-key' });
  const bundle = {
    resourceType: 'Bundle', type: 'collection',
    entry: [
      { resource: {
        resourceType: 'Patient', id: 'p-123',
        identifier: [{ value: 'MRN-8829340' }],
        name: [{ family: 'Hernandez', given: ['Maria'] }],
        telecom: [{ system: 'phone', value: '415-555-0173' }],
        birthDate: '1962-04-11',
      } },
      { resource: {
        resourceType: 'Observation', id: 'o-1',
        code: { coding: [{ system: 'http://loinc.org', code: '4548-4' }] },
        subject: { reference: 'Patient/p-123' },
      } },
    ],
  };
  const out = v.deidentifyBundle(bundle);
  const pt = out.entry[0].resource;
  const obs = out.entry[1].resource;
  assert.match(pt.id, /^PT_[a-z0-9]{12}$/);
  assert.equal(pt.identifier[0].value.startsWith('PT_'), true);
  assert.equal(pt.name[0].family.startsWith('PT_'), true);
  assert.equal(pt.name[0].given[0].startsWith('PT_'), true);
  assert.equal(pt.telecom[0].value.startsWith('PT_'), true);
  assert.equal(pt.birthDate, '1962');                  // year-only generalisation
  assert.equal(obs.subject.reference, `Patient/${pt.id}`);  // cross-resource ref rewritten
});

test('re-identification gated by DEID_ENABLE_REID', () => {
  const v = makeVault({ key: 'k1' });
  const ps = v.remember('name.family', 'Hernandez');
  delete process.env.DEID_ENABLE_REID;
  assert.throws(() => v.reidentify(ps, { reason: 'support' }), /disabled/);
  process.env.DEID_ENABLE_REID = 'true';
  assert.throws(() => v.reidentify(ps, { reason: '' }), /reason/);
  assert.equal(v.reidentify(ps, { reason: 'support ticket #4421' }), 'Hernandez');
  delete process.env.DEID_ENABLE_REID;
});

test('scanForPhiLeaks finds verbatim survivors', () => {
  const out = '{"note":"Patient Hernandez confirmed at 415-555-0173"}';
  const leaks = scanForPhiLeaks(['Hernandez', '415-555-0173', 'NotPresent'], out);
  assert.deepEqual(leaks.sort(), ['415-555-0173', 'Hernandez']);
});

test('deidentified bundle has no original verbatim PHI', () => {
  const v = makeVault({ key: 'k1' });
  const bundle = {
    resourceType: 'Bundle', type: 'collection',
    entry: [{ resource: {
      resourceType: 'Patient', id: 'p-X',
      identifier: [{ value: 'MRN-X' }],
      name: [{ family: 'Smith', given: ['John'] }],
      birthDate: '1960-01-01',
    } }],
  };
  const originals = ['Smith', 'John', 'MRN-X', '1960-01-01'];
  v.deidentifyBundle(bundle);
  const text = JSON.stringify(bundle);
  const leaks = scanForPhiLeaks(originals, text);
  // 1960 (year) is allowed to remain after generalisation; the full date should not be present
  assert.equal(leaks.includes('Smith'), false);
  assert.equal(leaks.includes('John'), false);
  assert.equal(leaks.includes('MRN-X'), false);
  assert.equal(leaks.includes('1960-01-01'), false);
});
