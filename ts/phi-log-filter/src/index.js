// phi-log-filter — Node reference implementation (zero deps).
//
// Exports:
//   scrubString(s)            → string with regex PHI replaced
//   scrubObject(o, allowlist) → deep-cloned object with PHI scrubbed
//   pinoCensor(allowlist)     → drop-in for pino's `redact.censor`
//   winstonFormat(allowlist)  → drop-in for winston's `format.combine`

'use strict';

const PHI_KEYS = new Set([
  'name','first_name','last_name','middle_name','maiden_name','patient_name',
  'full_name','given_name','family_name','doctor','doctor_name','provider',
  'provider_name','dob','birth_date','date_of_birth','birthdate','ssn',
  'social_security','mrn','chart_id','medical_record_number','phone',
  'telephone','cell','mobile','fax','email','email_address','address',
  'street','line1','line2','city','zip','zip_code','account','account_no',
  'account_number','member_id','policy_no','policy_number','subscriber_id',
  'ip','ip_address',
]);

const PATTERNS = [
  ['SSN',   /\b\d{3}-\d{2}-\d{4}\b/g],
  ['EMAIL', /\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b/g],
  ['PHONE', /\b(?:\+?1[-.\s]?)?\(?[2-9]\d{2}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b/g],
  ['DOB',   /\b(?:19|20)\d{2}-(?:0[1-9]|1[0-2])-(?:0[1-9]|[12]\d|3[01])\b/g],
  ['MRN',   /\bMRN[:\s#]*[A-Z]?\d{6,10}\b/gi],
];

const YEAR_RE = /(?:19|20)\d{2}/;

function placeholder(kind, original) {
  if (kind === 'DOB') {
    const m = original.match(YEAR_RE);
    return m ? `[PHI:DOB:year=${m[0]}]` : '[PHI:DOB]';
  }
  return `[PHI:${kind}]`;
}

function keyKind(key) {
  const k = String(key).toLowerCase();
  if (k.includes('name'))    return 'NAME';
  if (k.includes('dob') || k.includes('birth')) return 'DOB';
  if (k.includes('ssn'))     return 'SSN';
  if (k.includes('mrn'))     return 'MRN';
  if (k.includes('phone') || k.includes('fax') || k.includes('cell') || k.includes('mobile')) return 'PHONE';
  if (k.includes('email'))   return 'EMAIL';
  if (k.includes('zip'))     return 'ZIP';
  if (k.includes('address') || k.includes('street') || k.includes('line') || k.includes('city')) return 'ADDRESS';
  if (k.includes('account') || k.includes('member') || k.includes('policy') || k.includes('subscriber')) return 'ACCT';
  if (k.includes('ip'))      return 'IP';
  return 'REDACTED';
}

function scrubString(s) {
  if (typeof s !== 'string') return s;
  let out = s;
  for (const [kind, pat] of PATTERNS) {
    out = out.replace(pat, (m) => placeholder(kind, m));
  }
  return out;
}

function scrubObject(obj, allowlist = new Set()) {
  if (obj === null || obj === undefined) return obj;
  if (typeof obj === 'string') return scrubString(obj);
  if (Array.isArray(obj)) return obj.map((v) => scrubObject(v, allowlist));
  if (typeof obj !== 'object') return obj;
  const out = {};
  for (const [k, v] of Object.entries(obj)) {
    if (allowlist.has(k)) {
      out[k] = v;
    } else if (PHI_KEYS.has(String(k).toLowerCase()) && (typeof v === 'string' || typeof v === 'number')) {
      out[k] = placeholder(keyKind(k), String(v));
    } else {
      out[k] = scrubObject(v, allowlist);
    }
  }
  return out;
}

function pinoCensor(allowlist = []) {
  const allow = new Set(['event','level','timestamp','logger',...allowlist]);
  return function censor(value, path) {
    // pino calls censor for each matched redact path AND for whole-object scrub
    const last = path && path.length ? path[path.length - 1] : '';
    if (allow.has(last)) return value;
    if (typeof value === 'string') return scrubString(value);
    if (typeof value === 'object') return scrubObject(value, allow);
    return value;
  };
}

function winstonFormat(allowlist = []) {
  const allow = new Set(['event','level','timestamp','message','logger',...allowlist]);
  return {
    transform(info) {
      return scrubObject(info, allow);
    },
  };
}

module.exports = { scrubString, scrubObject, pinoCensor, winstonFormat, PHI_KEYS };
