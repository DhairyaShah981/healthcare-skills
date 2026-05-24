# TypeScript reference implementations

The skills in this directory have Python reference impls in `skills/<name>/scripts/`. This directory contains the Node / TypeScript equivalents for skills where TS is the more common ecosystem.

| Skill | TS impl | Stack |
|---|---|---|
| phi-log-filter | [`ts/phi-log-filter/`](./phi-log-filter/) | pino + winston redactors |
| webhook-verify | [`ts/webhook-verify/`](./webhook-verify/) | crypto.timingSafeEqual, all 7 providers |
| audit-trail | [`ts/audit-trail/`](./audit-trail/) | Express middleware + Knex / Prisma sketch |
| consent-gate | [`ts/consent-gate/`](./consent-gate/) | Express middleware, SMART scope handling |

## Layout per skill

```
ts/<skill>/
├── package.json
├── src/
│   └── index.ts            # the implementation
└── test/
    └── smoke.test.js        # Node assert-based smoke (zero deps)
```

The smoke tests use `node --test` (Node 18+, zero dependencies) so they run in the validate-skills CI workflow without an npm install.

## Running a smoke locally

```bash
cd ts/webhook-verify
node --test test/smoke.test.js
```
