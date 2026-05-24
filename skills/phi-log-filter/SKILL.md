---
name: phi-log-filter
description: |
  Install a structlog / loguru / Python logging / winston / pino processor that
  redacts PHI continuously at the logging boundary — every log call gets the
  scrub, no opt-in needed. Different from `phi-redact` (one-shot scrubbing of
  text/files); this is the always-on logger middleware. Use when the user sets
  up logging in a healthcare service or asks "how do I make sure PHI never
  hits the log sink?".
when_to_use: |
  Activate when the user:
  - Sets up logging in a FastAPI / Flask / Django / Express / Fastify service
  - Asks "how do I prevent PHI from getting into logs?"
  - Uses structlog, loguru, Python logging, winston, or pino
  - Configures a log sink (Datadog, Cloud Logging, Sentry, LogRocket)
  - Has a logging review finding about possible PHI exposure
allowed-tools: [Read, Write, Edit, Bash]
license: MIT
tags: [hipaa, phi, logging, security, healthcare]
incident: |
  Even when engineers know "don't log PHI", they reach for `logger.info(f"loaded
  patient {patient}")` under deadline pressure. The fix isn't more discipline;
  it's a logger middleware that scrubs every record before it leaves the
  process, plus a redact-keys allowlist so deliberate diagnostic logging
  surfaces only safe fields. This skill installs the processor once.
---

# phi-log-filter

> Logger middleware that scrubs PHI on every record. Defense at the boundary.

## When to use

- The user sets up logging in a healthcare service (any language).
- The user mentions structlog / loguru / Python logging / winston / pino.
- The user is wiring logs to Datadog / Sentry / Cloud Logging / LogRocket and a BAA situation is unclear.
- A security review flagged "logger.info(f'{patient}')" or similar.

## How it works

1. **Choose the layer.** The processor sits between the logger and the sink. Install at the lowest level the framework allows:
   - **structlog** → add to `processors=[...]`
   - **Python logging** → a `logging.Filter` on every handler
   - **loguru** → `logger.add(..., filter=phi_filter)`
   - **winston** → a custom format (`format.combine(phiScrub(), ...)`)
   - **pino** → `redact: { paths: [...] , censor: scrub }`

2. **Two-pass scrub.** Run both on every record:
   - **Key-based** — keys matching `name|first_name|...|mrn|dob|...` get their values replaced wholesale with `[PHI:<kind>]`. (Same key list as `phi-redact`.)
   - **Value-based regex** — apply the regex catalog (`phi-redact/references/regex-patterns.md`) to every string value, swap matches with placeholders.

3. **Allowlist deliberate diagnostic fields.** `patient_id` (an opaque internal ID), `trace_id`, `tenant_id` are *not* PHI by themselves. The processor's allowlist keeps them visible.

4. **Fail closed.** If the processor throws, drop the record (or replace it with `{"error": "phi-filter-failure"}`), don't emit the raw one. Wire a metric so a broken processor surfaces.

5. **Test it.** A unit test that constructs a record with every shape of PHI and asserts the output is clean. Run on every PR.

6. **Don't replace `phi-redact`.** `phi-log-filter` is the continuous boundary at the logger; `phi-redact` is for cleaning files / pastes / fixtures. Compose both.

## Example — structlog (Python)

```python
# app/logging_setup.py
import structlog
from healthcare_skills.phi_log_filter import phi_processor

structlog.configure(
    processors=[
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        phi_processor(allowlist={"patient_id", "trace_id", "tenant_id",
                                  "request_id", "user_id", "encounter_id"}),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.JSONRenderer(),
    ],
)

log = structlog.get_logger()
log.info("patient_loaded", patient_id="P9981", patient_name="Maria Hernandez",
         dob="1962-04-11")
```

Output:
```json
{"event": "patient_loaded", "patient_id": "P9981",
 "patient_name": "[PHI:NAME]", "dob": "[PHI:DOB:year=1962]",
 "timestamp": "2026-05-24T08:14:22Z", "level": "info"}
```

## Example — Python stdlib logging

```python
# app/logging_setup.py
import logging
from healthcare_skills.phi_log_filter import PhiFilter

ALLOWLIST = {"patient_id", "trace_id", "tenant_id", "request_id"}

handler = logging.StreamHandler()
handler.addFilter(PhiFilter(allowlist=ALLOWLIST))
logging.basicConfig(level=logging.INFO, handlers=[handler])
```

`PhiFilter.filter(record)` rewrites `record.msg` and `record.args` (and any `extra=` dict) before emission.

## Example — pino (Node)

```js
const pino = require('pino')
const { phiCensor } = require('healthcare-skills/phi-log-filter')

const log = pino({
  redact: {
    paths: [
      '*.name', '*.first_name', '*.last_name', '*.dob', '*.date_of_birth',
      '*.ssn', '*.mrn', '*.phone', '*.email', '*.address.*'
    ],
    censor: phiCensor   // also runs the regex scrub on string values
  }
})
```

## Edge cases

- **Logged exception messages.** Stack traces sometimes carry PHI in repr strings ("KeyError: 'Maria Hernandez'"). The processor must rewrite `record.exc_info` too.
- **Bound contextvars.** `structlog.contextvars.bind_contextvars(patient_name=...)` leaks into every subsequent log. Bind only allowlisted keys.
- **Repr of model objects.** A `Patient.__repr__` that includes name leaks into logs. Override `__repr__` on PHI-bearing models to print only the ID.
- **Custom formatters.** Format strings (`"loaded %s"`) get assembled by the logger; scrub *after* formatting so the final emitted string is what's checked.
- **Performance.** The processor is on every log call. Cache compiled regexes; skip records below INFO when possible; benchmark with `pyperf`.
- **Don't scrub config / startup logs.** Connection strings, port numbers, feature flags — these aren't PHI and breaking them confuses ops. The allowlist handles this.
- **Sinks with their own redaction.** Datadog has `@redact` patterns; don't rely on them alone — scrub before the record leaves the process.
- **Sentry breadcrumbs.** Sentry collects breadcrumbs separately; install the processor on Sentry's `before_send` too.

## References

- HIPAA Breach Notification Rule §164.404 — PHI in vendor logs without a BAA is reportable
- structlog processors: <https://www.structlog.org/en/stable/processors.html>
- Python `logging.Filter`: <https://docs.python.org/3/library/logging.html#filter-objects>
- pino redact: <https://github.com/pinojs/pino/blob/master/docs/redaction.md>
- winston formats: <https://github.com/winstonjs/winston#formats>
- [`scripts/phi_log_filter.py`](./scripts/phi_log_filter.py) — Python (structlog + stdlib)
- [`examples/structlog_setup.py`](./examples/structlog_setup.py)
- Compose with: `phi-redact` (one-shot scrub), `audit-trail` (separate, PHI-free audit table)
