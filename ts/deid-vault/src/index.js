// deid-vault — Node reference (zero deps; built-in node:crypto).
//
// Deterministic, keyed HMAC-SHA256 pseudonyms with an in-memory vault
// (production should swap for Postgres + field-level encryption).
//
// Exports:
//   makeVault({ key, store }) → { pseudonym, remember, deidentifyBundle, reidentify }
//   scanForPhiLeaks(originals, output) → string[] of leaked values
//
// The bundle walker mirrors the Python pipeline in fhir-mcp / phi-redact.

'use strict';

const crypto = require('node:crypto');

// PHI-bearing FHIR paths to scrub on each resource type
// Note: `id` is handled in Pass 1 below (so cross-resource references can be
// rewritten consistently). PHI_PATHS only enumerates non-id fields.
const PHI_PATHS = {
  Patient: [
    ['identifier[*].value', 'MRN'],
    ['name[*].family', 'name.family'],
    ['name[*].given[*]', 'name.given'],
    ['name[*].text', 'name.text'],
    ['telecom[*].value', 'telecom'],
    ['address[*].line[*]', 'address.line'],
    ['address[*].city', 'address.city'],
    ['address[*].postalCode', 'address.zip'],
  ],
  Practitioner: [
    ['name[*].family', 'name.family'],
    ['name[*].given[*]', 'name.given'],
    ['telecom[*].value', 'telecom'],
  ],
  RelatedPerson: [
    ['name[*].family', 'name.family'],
    ['name[*].given[*]', 'name.given'],
  ],
};


function makeVault({ key, store }) {
  if (!key) throw new Error('deid-vault: key is required');
  const keyBuf = Buffer.from(String(key));
  const entries = store || new Map(); // pseudonym → { original, kind, createdAt }
  const reverseIndex = new Map();      // `${kind}\x00${original}` → pseudonym

  function pseudonym(kind, original) {
    const msg = Buffer.concat([Buffer.from(`${kind}\x00`), Buffer.from(String(original))]);
    const digest = crypto.createHmac('sha256', keyBuf).update(msg).digest();
    const b32 = base32(digest).slice(0, 12).toLowerCase();
    return `PT_${b32}`;
  }

  function remember(kind, original) {
    const key = `${kind}\x00${original}`;
    if (reverseIndex.has(key)) return reverseIndex.get(key);
    const ps = pseudonym(kind, original);
    entries.set(ps, { original: String(original), kind, createdAt: Date.now() });
    reverseIndex.set(key, ps);
    return ps;
  }

  function reidentify(ps, { reason, actor = 'unknown' } = {}) {
    if (process.env.DEID_ENABLE_REID !== 'true') {
      throw new Error('re-identification disabled (DEID_ENABLE_REID != true)');
    }
    if (!reason) throw new Error('re-identification requires a reason');
    const row = entries.get(ps);
    return row ? row.original : null;
  }

  function deidentifyBundle(bundle) {
    if (!bundle || !Array.isArray(bundle.entry)) return bundle;
    // Pass 1 — pseudonymise IDs, build the rewrite map
    const idMap = new Map();  // `Patient/123` → `Patient/PT_xxx`
    for (const e of bundle.entry) {
      const r = e.resource || {};
      const paths = PHI_PATHS[r.resourceType];
      if (paths && r.id) {
        const newId = remember(`${r.resourceType}.id`, r.id);
        idMap.set(`${r.resourceType}/${r.id}`, `${r.resourceType}/${newId}`);
        r.id = newId;
      }
    }
    // Pass 2 — scrub PHI fields per resource + rewrite cross-resource refs + generalise birthDate
    for (const e of bundle.entry) {
      const r = e.resource || {};
      const paths = PHI_PATHS[r.resourceType];
      if (paths) scrubResource(r, paths, remember);
      rewriteRefs(r, idMap);
      if (r.resourceType === 'Patient' && typeof r.birthDate === 'string') {
        r.birthDate = r.birthDate.slice(0, 4);
      }
    }
    return bundle;
  }

  return { pseudonym, remember, reidentify, deidentifyBundle, _entries: entries };
}


// ── path resolver (FHIRPath-lite: a.b[*].c) ────────────────────────────

function resolvePath(node, path) {
  const out = [];
  const parts = path.split('.');
  let stack = [node];
  for (let i = 0; i < parts.length; i++) {
    const part = parts[i];
    const isLast = i === parts.length - 1;
    const next = [];
    for (const cur of stack) {
      if (cur == null) continue;
      if (part.endsWith('[*]')) {
        const k = part.slice(0, -3);
        const v = cur[k];
        if (Array.isArray(v)) {
          for (const item of v) {
            if (isLast) out.push([cur, k]);
            else next.push(item);
          }
        }
      } else {
        if (isLast) out.push([cur, part]);
        else if (cur[part] != null) next.push(cur[part]);
      }
    }
    stack = next;
  }
  return out;
}

function scrubResource(res, paths, remember) {
  for (const [path, kind] of paths) {
    for (const [parent, key] of resolvePath(res, path)) {
      const val = parent[key];
      if (typeof val === 'string' && val) {
        parent[key] = remember(kind, val);
      } else if (Array.isArray(val)) {
        for (let i = 0; i < val.length; i++) {
          if (typeof val[i] === 'string' && val[i]) val[i] = remember(kind, val[i]);
        }
      }
    }
  }
}

function rewriteRefs(node, idMap) {
  if (!node || typeof node !== 'object') return;
  if (Array.isArray(node)) {
    for (const v of node) rewriteRefs(v, idMap);
    return;
  }
  if (typeof node.reference === 'string' && idMap.has(node.reference)) {
    node.reference = idMap.get(node.reference);
  }
  for (const k of Object.keys(node)) rewriteRefs(node[k], idMap);
}


// ── leak scanner ──────────────────────────────────────────────────────

function scanForPhiLeaks(originals, output) {
  const text = typeof output === 'string' ? output : JSON.stringify(output);
  const leaked = [];
  for (const o of originals) {
    if (typeof o !== 'string' || !o) continue;
    if (text.includes(o)) leaked.push(o);
  }
  return leaked;
}


// ── base32 (RFC 4648, no padding) ─────────────────────────────────────

const B32 = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ234567';

function base32(buf) {
  let bits = 0;
  let value = 0;
  let out = '';
  for (const byte of buf) {
    value = (value << 8) | byte;
    bits += 8;
    while (bits >= 5) {
      out += B32[(value >>> (bits - 5)) & 0x1f];
      bits -= 5;
    }
  }
  if (bits > 0) out += B32[(value << (5 - bits)) & 0x1f];
  return out;
}


module.exports = { makeVault, scanForPhiLeaks };
