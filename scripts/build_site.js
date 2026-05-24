#!/usr/bin/env node
/**
 * build_site.js — generate docs/site/skills.json from skills/* SKILL.md frontmatter.
 *
 * The static site (docs/site/index.html) fetches skills.json client-side and
 * renders the searchable / filterable directory. Re-run on every PR via CI.
 */
'use strict';

const fs = require('node:fs');
const path = require('node:path');

const REPO = path.resolve(__dirname, '..');
const SKILLS_DIR = path.join(REPO, 'skills');
const OUT = path.join(REPO, 'docs', 'site', 'skills.json');

function parseFrontmatter(md) {
  if (!md.startsWith('---\n')) return {};
  const end = md.indexOf('\n---\n', 4);
  if (end < 0) return {};
  const block = md.slice(4, end);
  const out = {};
  let currentKey = null;
  let buf = [];
  for (const line of block.split('\n')) {
    const m = line.match(/^([A-Za-z0-9_-]+):\s*(.*)$/);
    if (m && !line.startsWith(' ') && !line.startsWith('\t')) {
      if (currentKey) out[currentKey] = buf.join('\n').trim();
      currentKey = m[1];
      buf = [m[2]];
    } else {
      buf.push(line.replace(/^  /, ''));
    }
  }
  if (currentKey) out[currentKey] = buf.join('\n').trim();
  for (const k of Object.keys(out)) {
    let v = out[k];
    if (v.startsWith('|')) v = v.slice(1).trim();
    if (v.startsWith('[') && v.endsWith(']')) {
      try { v = JSON.parse(v.replace(/(\w[\w-]*)/g, '"$1"').replace(/""/g, '"')); }
      catch { /* leave as string */ }
    }
    out[k] = v;
  }
  return out;
}

function tier(name, tags) {
  const tier0 = ['phi-redact', 'fhir-bundle', 'hipaa-review'];
  const tier1 = ['clinical-eval', 'audit-trail', 'consent-gate', 'deid-vault',
                  'hl7-transform', 'cds-hook', 'icd-snomed-map'];
  const tier2 = ['voice-agent-lint', 'alembic-guard', 'jsonb-pydantic-pair',
                  'tenant-rls-guard', 'async-blocking-lint', 'secrets-placeholder',
                  'synthea-fixture'];
  const tier3 = ['smart-oauth-scaffold', 'prior-auth-fhir', 'route-fatness',
                  'clinic-config-extract', 'migration-bisect', 'webhook-verify',
                  'phi-log-filter', 'specialty-scaffold',
                  'epic-sandbox-bootstrap', 'cds-hook-tester'];
  if (tier0.includes(name)) return 0;
  if (tier1.includes(name)) return 1;
  if (tier2.includes(name)) return 2;
  if (tier3.includes(name)) return 3;
  return 9;
}

function whenTrigger(fm) {
  const wt = fm.when_to_use || '';
  if (!wt) return [];
  // Pull bullet lines beginning with "- "
  return wt.split('\n')
    .map(s => s.trim())
    .filter(s => s.startsWith('- '))
    .map(s => s.slice(2).trim());
}

const skills = [];
for (const name of fs.readdirSync(SKILLS_DIR).sort()) {
  if (name.startsWith('_')) continue;
  const md = path.join(SKILLS_DIR, name, 'SKILL.md');
  if (!fs.existsSync(md)) continue;
  const text = fs.readFileSync(md, 'utf8');
  const fm = parseFrontmatter(text);
  const incidentFull = fm.incident ? oneLine(fm.incident) : '';
  skills.push({
    name,
    description: oneLine(fm.description),
    tags: Array.isArray(fm.tags) ? fm.tags : (fm.tags ? [String(fm.tags)] : []),
    incident: incidentFull.slice(0, 240) + (incidentFull.length > 240 ? '…' : ''),
    incident_full: incidentFull,
    when_to_use: whenTrigger(fm),
    license: fm.license || 'MIT',
    tier: tier(name, fm.tags),
    has_script: fs.existsSync(path.join(SKILLS_DIR, name, 'scripts')) &&
                 fs.readdirSync(path.join(SKILLS_DIR, name, 'scripts')).length > 0,
    has_typescript: fs.existsSync(path.join(REPO, 'ts', name)),
    github_url: `https://github.com/DhairyaShah981/healthcare-skills/blob/main/skills/${name}/SKILL.md`,
    incident_page: `incident.html?skill=${encodeURIComponent(name)}`,
  });
}

function oneLine(s) {
  if (!s) return '';
  return String(s).replace(/\n+/g, ' ').replace(/\s+/g, ' ').trim();
}

// Pull version from package.json so site, CLI, and tarball stay aligned.
const pkgVersion = JSON.parse(fs.readFileSync(path.join(REPO, 'package.json'), 'utf8')).version;

fs.mkdirSync(path.dirname(OUT), { recursive: true });
fs.writeFileSync(OUT, JSON.stringify({
  version: pkgVersion,
  generated_at: new Date().toISOString(),
  skills,
}, null, 2));

console.log(`build_site: wrote ${skills.length} skills to ${path.relative(REPO, OUT)}`);
