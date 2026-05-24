// tenant-rls-guard — Node reference (zero-dep regex linter).
//
// Detects tenant-scoped queries in TS / JS source that LACK an explicit
// `clientId`/`tenantId`/`orgId` predicate. Catches:
//   - Drizzle: db.select().from(patient).where(eq(patient.id, ...))    (missing clientId)
//   - Prisma:  prisma.patient.findMany({ where: { id } })              (no clientId)
//   - Raw SQL: `SELECT * FROM patient WHERE id = '...'`                (no client_id)
//
// Treats files containing `tenant-rls-guard: bypass` as exempt.
// Configurable via { tenantColumns: ['clientId','tenantId','orgId'], scopedTables: [...] }.

'use strict';

const DEFAULT_TENANT_COLS = ['clientId', 'tenantId', 'orgId', 'client_id', 'tenant_id', 'org_id'];
const DEFAULT_SCOPED = [
  'patient', 'encounter', 'observation', 'condition', 'appointment',
  'medicationRequest', 'auditEvent', 'priorAuth', 'clinicUser',
  // snake_case raw-SQL variants
  'medication_request', 'audit_event', 'prior_auth', 'clinic_user',
];


function lintFile({ path = '<input>', text, tenantColumns = DEFAULT_TENANT_COLS,
                    scopedTables = DEFAULT_SCOPED } = {}) {
  if (text == null) throw new Error('lintFile requires text');
  if (/tenant-rls-guard:\s*bypass/.test(text)) return [];

  const lines = text.split('\n');
  const findings = [];
  const tenantCol = '(?:' + tenantColumns.map(escapeReg).join('|') + ')';
  const tables = '(?:' + scopedTables.map(escapeReg).join('|') + ')';

  // Drizzle: db.select().from(<table>)... where(...) chains
  // Prisma:  prisma.<table>.findMany|findUnique|findFirst({ where: { ... } })
  // Raw SQL: SELECT/UPDATE/DELETE FROM <table> WHERE ...
  const reDrizzle = new RegExp(`\\.from\\(\\s*${tables}\\b`, 'g');
  const rePrisma  = new RegExp(`(?:prisma|db|client)\\.${tables}\\.(?:findMany|findUnique|findFirst|deleteMany|updateMany)\\b`, 'g');
  const reRawSql  = new RegExp(`(?:SELECT|UPDATE|DELETE FROM)\\s+\\*?\\s*FROM?\\s+${tables}\\b`, 'gi');
  const reTenant  = new RegExp(`\\b${tenantCol}\\b`);

  // Walk forward through the file; for each match, look at a "near" window
  // (current line + next 6 lines) for a tenant predicate.
  for (const re of [reDrizzle, rePrisma, reRawSql]) {
    let m;
    while ((m = re.exec(text)) !== null) {
      const upto = text.slice(0, m.index);
      const lineNo = upto.split('\n').length;
      const startLine = lineNo - 1;
      const windowText = lines.slice(startLine, startLine + 7).join('\n');
      if (!reTenant.test(windowText)) {
        findings.push({
          rule: 'RLS-001', severity: 'ERROR', line: lineNo, path,
          message: `query on scoped table lacks ${tenantColumns[0]} predicate: ${lines[startLine].trim().slice(0, 120)}`,
        });
      }
    }
  }
  return findings;
}


function escapeReg(s) {
  return s.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
}


module.exports = { lintFile, DEFAULT_TENANT_COLS, DEFAULT_SCOPED };
