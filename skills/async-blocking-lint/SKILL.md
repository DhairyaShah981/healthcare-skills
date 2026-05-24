---
name: async-blocking-lint
description: |
  Detect synchronous network / IO calls (requests, urllib, httpx (sync mode),
  time.sleep, smtplib, paramiko) inside `async def` functions or coroutines.
  These calls block the event loop and cause request pile-ups under load.
  Use when the user writes an async route handler, reviews an async service,
  or asks why their server is "slow under load."
when_to_use: |
  Activate when the user:
  - Writes an `async def` route handler or service method
  - Reviews FastAPI / Starlette / Litestar / aiohttp code
  - Mentions slow response times under load, server stalls, or "event loop blocked"
  - Asks about `asgi`, `async`, `await`, or coroutines in a server context
  - Uses `requests`, `urllib`, `httpx.Client` (sync), `time.sleep` in async code
allowed-tools: [Read, Grep, Edit, Bash]
license: MIT
tags: [linter, async, performance, healthcare]
incident: |
  An async FastAPI service blocked the event loop with a `requests.post()`
  inside an `async def` handler. Under burst load (incoming voice calls
  triggering webhooks) the event loop stalled and the entire process queued
  up requests, eventually timing out. Replacing one synchronous call with
  `httpx.AsyncClient` cut p95 latency by an order of magnitude. This linter
  catches the pattern before it ships.
---

# async-blocking-lint

> Sync IO in async code blocks the event loop. Lint catches it before prod.

## When to use

- The user is writing async FastAPI / Starlette / Litestar / aiohttp / asyncio code.
- The user reports slow latency under load or "server hangs after a few requests".
- The user mentions blocking calls, sync vs async, or event-loop stalls.

## How it works

1. **Walk every Python file under `app/`** (or the configured root).
2. **Parse to AST**, find every `AsyncFunctionDef` node.
3. **Inside each async function body**, look for calls to known-synchronous functions:

| Blocking call | Async replacement |
|---|---|
| `requests.get/post/...` | `httpx.AsyncClient().get(...)` |
| `urllib.request.urlopen` | `httpx.AsyncClient().get(...)` |
| `urllib3.PoolManager().request` | `httpx.AsyncClient(...)` |
| `httpx.get/post/...` (module-level, not AsyncClient) | `httpx.AsyncClient().get(...)` |
| `time.sleep` | `await asyncio.sleep(...)` |
| `subprocess.run/check_call/Popen.wait` | `asyncio.create_subprocess_exec(...)` |
| `socket.recv/send/...` | `asyncio.open_connection(...)` |
| `smtplib.SMTP/...` | `aiosmtplib` |
| `paramiko.SSHClient` | `asyncssh` |
| `psycopg2.connect/...` | `asyncpg` or `psycopg.AsyncConnection` |
| `redis.Redis(...)` (sync client) | `redis.asyncio.Redis(...)` |
| `boto3.client(...).<sync>` | `aioboto3` |
| `open(...).read()` of large files | `aiofiles.open(...)` |

4. **Report findings** with the line number, the blocking call, and the suggested replacement.

5. **Exempt run-in-threadpool calls.** `await loop.run_in_executor(None, requests.get, url)` is acceptable (the sync call runs in a thread); the linter detects this pattern and skips.

## Rules

| ID | Severity | Rule |
|---|---|---|
| ASB-001 | ERROR | `requests.*` inside `async def` |
| ASB-002 | ERROR | `urllib.*` inside `async def` |
| ASB-003 | ERROR | `time.sleep` inside `async def` (use `asyncio.sleep`) |
| ASB-004 | ERROR | Sync DB client (`psycopg2`, `redis.Redis` sync) inside `async def` |
| ASB-005 | ERROR | Synchronous file `open()` on potentially large files inside `async def` |
| ASB-006 | ERROR | `subprocess.run/check_call` inside `async def` (use `asyncio.create_subprocess_exec`) |
| ASB-007 | WARN | A coroutine is defined but never `await`ed (suggests sync misuse) |

## Example

**Bad:**
```python
import requests, time

@app.get("/patients/{id}")
async def get_patient(id: str):
    time.sleep(0.1)                            # ASB-003
    res = requests.get(f"https://ehr.example/Patient/{id}").json()    # ASB-001
    return res
```

**Output:**
```
async-blocking-lint — app/routes/patients.py:5
  ASB-003  ERROR  time.sleep(...) blocks event loop
     → await asyncio.sleep(0.1)
  ASB-001  ERROR  requests.get(...) blocks event loop
     → use httpx.AsyncClient or run in executor:
       async with httpx.AsyncClient() as client:
           res = (await client.get(...)).json()
```

**Good:**
```python
import asyncio, httpx

@app.get("/patients/{id}")
async def get_patient(id: str):
    await asyncio.sleep(0.1)
    async with httpx.AsyncClient() as client:
        res = (await client.get(f"https://ehr.example/Patient/{id}")).json()
    return res
```

## Edge cases

- **Sync code called via threadpool is OK.** `await loop.run_in_executor(None, requests.get, url)` runs the sync call off the event loop. The linter detects `run_in_executor` and `asyncio.to_thread` and exempts the wrapped call.
- **Library functions that are async-aware.** Some libraries (e.g. `httpx`) provide both sync and async APIs from the same module. `httpx.get` is sync; `httpx.AsyncClient().get` is async. The linter checks which is in use.
- **Constructors aren't always blocking.** `redis.Redis(...)` just builds an object; the blocking call is when you `.get()`. The linter checks for the *method* call, not the constructor.
- **Tests are exempt.** Files under `tests/` aren't linted (sync calls in tests are fine).
- **Sync calls in library code.** Some libraries you depend on may make sync calls under the hood; you can't fix those from your codebase. Document and move on.
- **Don't auto-fix.** The right replacement depends on context (use `httpx`? `aiohttp`? threadpool?). Suggest, don't replace.

## References

- Starlette docs on threadpool: <https://www.starlette.io/threadpool/>
- FastAPI async/await guide: <https://fastapi.tiangolo.com/async/>
- `asyncio.to_thread` (Python 3.9+) — easiest way to offload sync calls
- [`scripts/check_async_blocking.py`](./scripts/check_async_blocking.py) — runnable linter
- [`examples/bad_async.py`](./examples/bad_async.py) / [`examples/good_async.py`](./examples/good_async.py)
