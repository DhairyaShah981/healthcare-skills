// audit-trail — Node reference (zero deps).
//
// Exports:
//   AuditStore                — pluggable persistence (default: in-memory)
//   audited(opts)             — wrap any async function; emits an audit row
//   auditExpress(opts)        — Express middleware: emits a row per route hit
//
// Audit rows carry NO PHI: phi-tagged args are hashed (SHA-256), never stored raw.

'use strict';

const crypto = require('node:crypto');

function uuidv4Like() {
  const b = crypto.randomBytes(16);
  b[6] = (b[6] & 0x0f) | 0x40;
  b[8] = (b[8] & 0x3f) | 0x80;
  const h = b.toString('hex');
  return `${h.slice(0,8)}-${h.slice(8,12)}-${h.slice(12,16)}-${h.slice(16,20)}-${h.slice(20)}`;
}

function nowIso() {
  return new Date().toISOString();
}

function hashArgs(map, salt = process.env.AUDIT_ARG_HASH_SALT || '') {
  const serial = JSON.stringify(map, Object.keys(map).sort());
  const h = crypto.createHash('sha256').update(salt).update(serial).digest('hex');
  return `sha256:${h}`;
}

class AuditStore {
  constructor() { this.rows = []; }
  async write(row) { this.rows.push(row); }
}

const defaultStore = new AuditStore();

function audited({ action, phiArgs = [], resourceArg = null, resourceType = null,
                   getActor = () => ({ id: 'anonymous', type: 'system' }),
                   getTraceId = () => null,
                   store = defaultStore }) {
  return function wrap(fn) {
    return async function audit_wrapper(...args) {
      const started = process.hrtime.bigint();
      const actor = await getActor();
      const traceId = await getTraceId();

      const namedArgs = args[0] && typeof args[0] === 'object' ? args[0] : {};
      const phiMap = {};
      for (const k of phiArgs) {
        if (k in namedArgs) phiMap[k] = namedArgs[k];
      }
      const resourceId = resourceArg && namedArgs[resourceArg] != null
        ? String(namedArgs[resourceArg]) : null;

      const baseRow = {
        id: uuidv4Like(),
        ts: nowIso(),
        actor_id: actor.id,
        actor_type: actor.type,
        action,
        resource_type: resourceType,
        resource_id: resourceId,
        args_hash: Object.keys(phiMap).length ? hashArgs(phiMap) : null,
        trace_id: traceId,
      };

      try {
        const result = await fn(...args);
        const ms = Number((process.hrtime.bigint() - started) / 1_000_000n);
        await store.write({ ...baseRow, outcome: 'success', duration_ms: ms, error: null });
        return result;
      } catch (err) {
        const ms = Number((process.hrtime.bigint() - started) / 1_000_000n);
        await store.write({ ...baseRow, outcome: 'failure', duration_ms: ms,
                            error: `${err.name}: ${err.message}` });
        throw err;
      }
    };
  };
}

function auditExpress({ action, phiArgs = [], resourceArg = null, resourceType = null,
                        getActor = (req) => req.user || { id: 'anonymous', type: 'system' },
                        store = defaultStore }) {
  return async function (req, res, next) {
    const started = process.hrtime.bigint();
    const actor = await getActor(req);
    const traceId = req.headers['x-trace-id'] || req.headers['traceparent'] || null;

    const params = { ...req.params, ...req.query };
    const phiMap = {};
    for (const k of phiArgs) if (k in params) phiMap[k] = params[k];

    res.on('finish', async () => {
      const ms = Number((process.hrtime.bigint() - started) / 1_000_000n);
      const outcome = res.statusCode >= 200 && res.statusCode < 400 ? 'success' : 'failure';
      await store.write({
        id: uuidv4Like(),
        ts: nowIso(),
        actor_id: actor.id,
        actor_type: actor.type,
        action,
        resource_type: resourceType,
        resource_id: resourceArg && params[resourceArg] != null ? String(params[resourceArg]) : null,
        args_hash: Object.keys(phiMap).length ? hashArgs(phiMap) : null,
        trace_id: traceId,
        outcome,
        duration_ms: ms,
        http_status: res.statusCode,
        ip: req.ip,
        user_agent: req.headers['user-agent'],
      });
    });

    next();
  };
}

module.exports = { audited, auditExpress, AuditStore, defaultStore };
