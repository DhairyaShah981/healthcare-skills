const { test } = require('node:test');
const assert = require('node:assert/strict');
const crypto = require('node:crypto');
const { verify } = require('../src/index.js');

const body = Buffer.from('{"event":"call.completed","call_id":"abc"}');
const secret = 'shh-very-secret';

function hmacHex(b, s) {
  return crypto.createHmac('sha256', s).update(b).digest('hex');
}

test('retell — valid signature accepted', () => {
  const sig = hmacHex(body, secret);
  assert.equal(true, verify('retell', body, { 'X-Retell-Signature': sig }, { secrets: [secret] }));
});

test('retell — wrong signature rejected', () => {
  assert.equal(false, verify('retell', body,
    { 'X-Retell-Signature': 'deadbeef'.repeat(8) }, { secrets: [secret] }));
});

test('retell — body tamper detected', () => {
  const sig = hmacHex(body, secret);
  const tampered = Buffer.from('{"event":"call.completed","call_id":"EVIL"}');
  assert.equal(false, verify('retell', tampered, { 'X-Retell-Signature': sig }, { secrets: [secret] }));
});

test('retell — secret rotation: second secret matches', () => {
  const sig = hmacHex(body, secret);
  assert.equal(true, verify('retell', body, { 'X-Retell-Signature': sig },
    { secrets: ['old-secret', secret] }));
});

test('github — sha256= prefix accepted', () => {
  const sig = 'sha256=' + hmacHex(body, secret);
  assert.equal(true, verify('github', body, { 'X-Hub-Signature-256': sig }, { secrets: [secret] }));
});

test('stripe — fresh timestamp + valid v1', () => {
  const ts = Math.floor(Date.now() / 1000).toString();
  const signed = Buffer.concat([Buffer.from(`${ts}.`), body]);
  const v1 = crypto.createHmac('sha256', secret).update(signed).digest('hex');
  assert.equal(true, verify('stripe', body,
    { 'Stripe-Signature': `t=${ts},v1=${v1}` }, { secrets: [secret] }));
});

test('stripe — replay rejected after window', () => {
  const ts = String(Math.floor(Date.now() / 1000) - 10_000); // 10000s old
  const signed = Buffer.concat([Buffer.from(`${ts}.`), body]);
  const v1 = crypto.createHmac('sha256', secret).update(signed).digest('hex');
  assert.equal(false, verify('stripe', body,
    { 'Stripe-Signature': `t=${ts},v1=${v1}` }, { secrets: [secret] }));
});

test('slack — valid v0= signature', () => {
  const ts = Math.floor(Date.now() / 1000).toString();
  const base = Buffer.concat([Buffer.from(`v0:${ts}:`), body]);
  const sig = 'v0=' + crypto.createHmac('sha256', secret).update(base).digest('hex');
  assert.equal(true, verify('slack', body, {
    'X-Slack-Signature': sig, 'X-Slack-Request-Timestamp': ts,
  }, { secrets: [secret] }));
});

test('twilio — url + sorted form params', () => {
  const url = 'https://example.com/twilio';
  const form = { To: '+14155550173', From: '+14155550174', Body: 'hi' };
  let base = url;
  for (const k of Object.keys(form).sort()) base += k + form[k];
  const sig = crypto.createHmac('sha1', secret).update(base).digest('base64');
  assert.equal(true, verify('twilio', body, { 'X-Twilio-Signature': sig },
    { secrets: [secret], url, formParams: form }));
});
