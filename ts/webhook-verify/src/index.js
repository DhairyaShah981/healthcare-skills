// webhook-verify — Node reference (zero deps; uses built-in crypto).
//
// All verifiers:
//   - operate on raw body bytes (verify BEFORE parsing JSON)
//   - use crypto.timingSafeEqual for constant-time comparison
//   - accept a list of secrets to support rotation

'use strict';

const crypto = require('node:crypto');

function timingSafeEqualString(a, b) {
  const ab = Buffer.from(a, 'utf8');
  const bb = Buffer.from(b, 'utf8');
  if (ab.length !== bb.length) return false;
  return crypto.timingSafeEqual(ab, bb);
}

// ── generic HMAC-SHA256, hex-encoded ──────────────────────────────────────

function verifyHmacSha256Hex(body, headers, secret, { headerName = 'x-signature' } = {}) {
  const sig = lower(headers)[headerName.toLowerCase()];
  if (!sig) return false;
  const expected = crypto.createHmac('sha256', secret).update(body).digest('hex');
  return timingSafeEqualString(sig.toLowerCase(), expected.toLowerCase());
}

// ── GitHub X-Hub-Signature-256 ────────────────────────────────────────────

function verifyGithub(body, headers, secret) {
  const sig = lower(headers)['x-hub-signature-256'];
  if (!sig || !sig.startsWith('sha256=')) return false;
  const expected = 'sha256=' + crypto.createHmac('sha256', secret).update(body).digest('hex');
  return timingSafeEqualString(sig, expected);
}

// ── Stripe ────────────────────────────────────────────────────────────────

function verifyStripe(body, headers, secret, { maxAgeSeconds = 300 } = {}) {
  const header = lower(headers)['stripe-signature'];
  if (!header) return false;
  const parts = Object.fromEntries(
    header.split(',').map((p) => p.split('=')).filter((kv) => kv.length === 2)
  );
  const ts = parts.t;
  const v1 = parts.v1;
  if (!ts || !v1) return false;
  if (Math.abs(Date.now() / 1000 - Number(ts)) > maxAgeSeconds) return false;
  const signed = Buffer.concat([Buffer.from(`${ts}.`), Buffer.from(body)]);
  const expected = crypto.createHmac('sha256', secret).update(signed).digest('hex');
  return timingSafeEqualString(v1, expected);
}

// ── Slack ─────────────────────────────────────────────────────────────────

function verifySlack(body, headers, secret, { maxAgeSeconds = 300 } = {}) {
  const h = lower(headers);
  const sig = h['x-slack-signature'];
  const ts = h['x-slack-request-timestamp'];
  if (!sig || !ts) return false;
  if (Math.abs(Date.now() / 1000 - Number(ts)) > maxAgeSeconds) return false;
  const base = Buffer.concat([Buffer.from(`v0:${ts}:`), Buffer.from(body)]);
  const expected = 'v0=' + crypto.createHmac('sha256', secret).update(base).digest('hex');
  return timingSafeEqualString(sig, expected);
}

// ── Twilio (SHA-1, base64) ────────────────────────────────────────────────

function verifyTwilio(body, headers, secret, { url, formParams } = {}) {
  const sig = lower(headers)['x-twilio-signature'];
  if (!sig || !url) return false;
  let base = url;
  if (formParams) {
    for (const k of Object.keys(formParams).sort()) {
      base += k + formParams[k];
    }
  }
  const expected = crypto.createHmac('sha1', secret).update(base).digest('base64');
  return timingSafeEqualString(sig, expected);
}

// ── dispatcher ────────────────────────────────────────────────────────────

const HEADER_BY_PROVIDER = {
  retell:  'x-retell-signature',
  vapi:    'x-vapi-signature',
  segment: 'x-signature',
  generic: 'x-signature',
};

function verify(provider, body, headers, { secrets, ...opts } = {}) {
  const list = (secrets || []).filter(Boolean);
  if (!list.length) return false;
  for (const secret of list) {
    if (callVerifier(provider, body, headers, secret, opts)) return true;
  }
  return false;
}

function callVerifier(provider, body, headers, secret, opts) {
  switch (provider) {
    case 'retell':
    case 'vapi':
    case 'segment':
    case 'generic':
      return verifyHmacSha256Hex(body, headers, secret, { headerName: HEADER_BY_PROVIDER[provider] });
    case 'github': return verifyGithub(body, headers, secret);
    case 'stripe': return verifyStripe(body, headers, secret);
    case 'slack':  return verifySlack(body, headers, secret);
    case 'twilio': return verifyTwilio(body, headers, secret, opts);
    default: throw new Error(`unsupported provider: ${provider}`);
  }
}

function lower(headers) {
  const out = {};
  for (const [k, v] of Object.entries(headers || {})) {
    out[String(k).toLowerCase()] = Array.isArray(v) ? v[0] : v;
  }
  return out;
}

module.exports = {
  verify,
  verifyHmacSha256Hex,
  verifyGithub,
  verifyStripe,
  verifySlack,
  verifyTwilio,
};
