// consent-gate — Node reference (zero deps).
//
// Two middlewares:
//   requireSmartScope(scope) — enforce a SMART-on-FHIR scope on the access token
//   requireConsent({ scope, getConsent }) — enforce a FHIR Consent row
//
// Both fail with HTTP 403 + { error, scope } body when the check fails.

'use strict';

// ── SMART scope inheritance ───────────────────────────────────────────────

function scopeCovers(granted, required) {
  if (granted.has(required)) return true;
  const slash = required.indexOf('/');
  if (slash < 0) return false;
  const ctx = required.slice(0, slash);
  const op = required.slice(slash + 1);
  const dot = op.lastIndexOf('.');
  if (dot < 0) return false;
  const resource = op.slice(0, dot);
  const verb = op.slice(dot + 1);
  const candidates = new Set([
    `${ctx}/*.${verb}`,
    `${ctx}/*.*`,
    `${ctx}/${resource}.*`,
    'user/*.*',
    `user/${resource}.${verb}`,
    `user/${resource}.*`,
    `user/*.${verb}`,
  ]);
  for (const c of candidates) if (granted.has(c)) return true;
  return false;
}

function requireSmartScope(scope, { getTokenClaims = (req) => req.tokenClaims || {} } = {}) {
  return function (req, res, next) {
    const claims = getTokenClaims(req);
    const granted = new Set(String(claims.scope || '').split(/\s+/).filter(Boolean));
    if (scopeCovers(granted, scope)) return next();
    res.status(403).json({ error: 'insufficient_scope', required: scope });
  };
}

// ── FHIR Consent row check ───────────────────────────────────────────────

function requireConsent({ scope, getConsent, getCallerApp = (req) => req.app_principal || {} }) {
  return async function (req, res, next) {
    const patientId = req.params.patient_id || req.params.patientId || req.body?.patient_id;
    if (!patientId) {
      return res.status(400).json({ error: 'patient_id required for consent check' });
    }
    const app = await getCallerApp(req);
    const now = new Date();
    let consent;
    try {
      consent = await getConsent({ patientId, recipient: app.id, scope, now });
    } catch (err) {
      return res.status(500).json({ error: 'consent_check_failed' });
    }
    if (!consent || consent.status !== 'active' || !Array.isArray(consent.scopes) ||
        !consent.scopes.includes(scope)) {
      return res.status(403).json({
        error: 'consent_required', scope, app: app.id || null,
      });
    }
    if (consent.period_end && new Date(consent.period_end) < now) {
      return res.status(403).json({ error: 'consent_expired', scope });
    }
    req.consent = consent;
    next();
  };
}

module.exports = { scopeCovers, requireSmartScope, requireConsent };
