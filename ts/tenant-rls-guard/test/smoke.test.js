const { test } = require('node:test');
const assert = require('node:assert/strict');
const { lintFile } = require('../src/index.js');

test('flags a Drizzle query that omits clientId', () => {
  const src = `
    export async function listObs(patientId) {
      return db.select().from(observation).where(eq(observation.patientId, patientId));
    }
  `;
  const findings = lintFile({ path: 'app/observations.ts', text: src });
  assert.equal(findings.length, 1);
  assert.equal(findings[0].rule, 'RLS-001');
});

test('passes a Drizzle query with clientId predicate', () => {
  const src = `
    export async function listObs(patientId, clientId) {
      return db.select().from(observation).where(and(eq(observation.clientId, clientId), eq(observation.patientId, patientId)));
    }
  `;
  const findings = lintFile({ path: 'ok.ts', text: src });
  assert.equal(findings.length, 0);
});

test('flags a Prisma findMany without clientId', () => {
  const src = `
    const rows = await prisma.patient.findMany({ where: { lastName: 'Smith' } });
  `;
  const findings = lintFile({ path: 'p.ts', text: src });
  assert.equal(findings.length, 1);
});

test('passes a Prisma findMany with clientId in where', () => {
  const src = `
    const rows = await prisma.patient.findMany({
      where: { clientId, lastName: 'Smith' },
    });
  `;
  const findings = lintFile({ path: 'p.ts', text: src });
  assert.equal(findings.length, 0);
});

test('flags raw SQL without client_id', () => {
  const src = `
    const rows = await db.execute(sql\`SELECT * FROM patient WHERE id = \${id}\`);
  `;
  const findings = lintFile({ path: 'raw.ts', text: src });
  assert.equal(findings.length, 1);
});

test('passes raw SQL with client_id', () => {
  const src = `
    const rows = await db.execute(sql\`SELECT * FROM patient WHERE client_id = \${clientId} AND id = \${id}\`);
  `;
  const findings = lintFile({ path: 'raw.ts', text: src });
  assert.equal(findings.length, 0);
});

test('respects bypass comment', () => {
  const src = `
    // tenant-rls-guard: bypass=analytics
    const rows = await db.select().from(patient);
  `;
  const findings = lintFile({ path: 'analytics.ts', text: src });
  assert.equal(findings.length, 0);
});

test('handles custom tenant column and scoped table list', () => {
  const src = `await db.select().from(my_table).where(eq(my_table.organizationId, orgId));`;
  const bad = lintFile({ path: 'x.ts', text: src, tenantColumns: ['orgId'], scopedTables: ['my_table'] });
  assert.equal(bad.length, 0);
  const bad2 = lintFile({ path: 'x.ts', text: `await db.select().from(my_table);`,
                          tenantColumns: ['orgId'], scopedTables: ['my_table'] });
  assert.equal(bad2.length, 1);
});
