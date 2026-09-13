# interview-ai-agent — backend

FastAPI backend for the mock interview agent. This document is a backend
developer walkthrough — tech stack, structure, how to run it, how to test
it.

## Tech stack

| Concern | Choice |
|---|---|
| Web framework | FastAPI (`app/main.py`) |
| ASGI server | Uvicorn |
| Database | Postgres (Neon, free tier) |
| ORM / driver | SQLAlchemy (async) + `asyncpg` |
| Migrations | Alembic |
| Vector search (RAG) | `pgvector` on Postgres |
| LLM provider | Google Gemini (`google-genai` — chat, native audio STT) |
| Voice TTS | ElevenLabs |
| Resume parsing | `pypdf` |
| Code execution (coding challenge) | Judge0 CE via RapidAPI (plain REST, no SDK) |
| External REST calls (GitHub, LeetCode unofficial API, Judge0) | `httpx` |
| Config | `pydantic-settings`, env vars in `.env` (see `.env.example`) |
| Testing | `pytest`, `pytest-cov`, `pytest-asyncio`, `pytest-mock`, `httpx` (`TestClient`) |
| Linting / security | `ruff`, `bandit`, `pre-commit` (`requirements-dev.txt`) |

Every endpoint is versioned under `/api/v1`, including the docs — Swagger
UI lives at `/api/v1/docs`, not `/docs`.

## Project structure

```
backend/
├── app/
│   ├── main.py                   # FastAPI app instance, router + exception handler wiring
│   ├── constants/                 # shared constants, grouped by domain (not one flat file)
│   │   ├── app.py                 #   API_V1_PREFIX, SERVICE_NAME, DEFAULT_USER_ID
│   │   ├── health.py              #   HEALTH_STATUS_HEALTHY / _UNHEALTHY
│   │   ├── responses.py           #   RESPONSE_STATUS_OK / _ERROR (envelope's "status" field)
│   │   └── interview.py           #   INTERVIEW_PHASES
│   ├── core/
│   │   ├── config.py              # Settings (pydantic-settings) — loads .env, e.g. DATABASE_URL
│   │   ├── db.py                  # async SQLAlchemy engine/session (get_engine, get_db)
│   │   ├── responses.py           # success_response() / error_response() — the envelope builders
│   │   └── exception_handlers.py  # wraps HTTPException / validation / 500s in the same envelope
│   ├── models/                    # SQLAlchemy ORM models (candidate_profile, job_description)
│   ├── schemas/
│   │   └── response.py            # APIResponse / ErrorDetail Pydantic models
│   ├── routes/
│   │   └── health.py              # /health
│   ├── services/                  # business logic
│   └── utils/                     # generic, framework-agnostic helpers
├── migrations/                      # Alembic migrations — env.py reads DATABASE_URL via app.core.config
├── tests/                         # mirrors app/'s structure 1:1 — see Testing below
│   ├── conftest.py                # shared fixtures (TestClient, ...)
│   ├── core/
│   ├── models/
│   ├── constants/
│   └── routes/
├── requirements.txt                # runtime + test deps (pinned)
├── requirements-dev.txt            # lint/security tooling only (ruff, bandit, pre-commit)
├── pyproject.toml                  # ruff, bandit, and pytest/coverage config
└── .env.example                    # required env vars, no real secrets
```

## Standard API response envelope

Every endpoint returns the same envelope shape, success or failure — except
the `error` key, which is never present on a success response (it doesn't
apply there), while `data` is always present, `null` or not:

```json
// success
{
  "success": true,
  "status": "ok",
  "status_code": 200,
  "data": { "...": "..." }
}

// failure (raised HTTPException, validation error, or unhandled exception)
{
  "success": false,
  "status": "error",
  "status_code": 404,
  "data": null,
  "error": { "message": "Candidate not found" }
}
```

Build it with `success_response(data, status_code)` / `error_response(message, status_code, data)`
from `app/core/responses.py` — don't hand-roll the dict in a route. Anything
you `raise HTTPException(...)` gets wrapped in this same shape automatically
via `app/core/exception_handlers.py`, so you only need to call `error_response`
directly for cases that aren't a plain raised exception.

## Running locally

```bash
cd backend
source .venv/bin/activate        # venv is managed with uv
uvicorn app.main:app --reload
```

Swagger UI: http://127.0.0.1:8000/api/v1/docs

Dependencies are managed with [`uv`](https://github.com/astral-sh/uv):

```bash
uv pip install --python .venv/bin/python -r requirements.txt
uv pip install --python .venv/bin/python -r requirements-dev.txt   # lint/security tools
```

Copy `.env.example` to `.env` and fill in real values before running
anything that touches Postgres/Gemini/ElevenLabs/Judge0/GitHub.

## Database

Postgres via Neon. Models live in `app/models/`; migrations are Alembic,
configured (`migrations/env.py`) to read `DATABASE_URL` from `.env` via
`app.core.config` — not from `alembic.ini` — so there's one source of
truth for the connection string, same as the running app uses.

```bash
alembic upgrade head                                    # apply migrations
alembic revision --autogenerate -m "add some_table"       # after changing a model
alembic current                                          # what revision the DB is on
```

**Gotcha:** Neon's connection string includes `sslmode=require` and
`channel_binding=require` — these are `libpq`/`psycopg` query parameters.
SQLAlchemy's asyncpg dialect passes URL query params straight through as
Python keyword arguments to `asyncpg.connect()`, which doesn't have a
`sslmode` or `channel_binding` parameter at all (only `ssl`) — so using
Neon's URL as-is raises `TypeError: connect() got an unexpected keyword
argument 'sslmode'`. Fixed in `app/core/db.py`'s `to_asyncpg_url()`: it
strips those query params and TLS is enabled instead via
`connect_args={"ssl": True}` on `create_async_engine`.

## Logging

`structlog`, configured once at startup (`app/core/logging.py`,
`configure_logging()` called from `app/main.py`) and routed through
stdlib `logging` via `ProcessorFormatter`, so **every** log line — this
app's own, and library log lines still using stdlib `logging` (Uvicorn,
SQLAlchemy, ...) — goes through the same pipeline, with file name, line
number, and function name attached automatically.

**Output format depends on whether stdout is a real terminal**
(`sys.stdout.isatty()`), decided automatically, no config needed:
- **Local dev (running `uvicorn` directly in a terminal):** colored,
  human-readable console output (`structlog.dev.ConsoleRenderer`).
- **Anywhere else** (output piped/redirected to a file, running under a
  process manager on Render, etc.): flat JSON — what a log aggregator
  actually wants to parse:

```json
{"method": "GET", "path": "/api/v1/health", "status_code": 200, "duration_ms": 3.7, "event": "request handled", "request_id": "d07afca9-...", "level": "info", "timestamp": "2026-09-08T15:09:10.233082Z", "func_name": "dispatch", "filename": "request_logging.py", "lineno": 33}
```

**Using it in a route/service — one-time setup, then trivial per call:**

```python
import structlog

logger = structlog.get_logger(__name__)

logger.info("resume parsed", candidate_id=candidate.id)
logger.warning("github_url missing", candidate_id=candidate.id)
```

Structured fields (`candidate_id=...`) come out as real JSON fields, not
text glued into a sentence. Nothing else needs configuring per file —
`configure_logging()` is called exactly once, at process startup.

**Request correlation:** `app/core/request_logging.py`'s
`RequestLoggingMiddleware` binds a `request_id` (reused from an incoming
`X-Request-ID` header if present, otherwise a generated UUID) once per
request via `structlog.contextvars`. Every log line emitted anywhere
while handling that request — this middleware's own "request handled"
line, any route/service code, even Uvicorn's own access log line —
automatically carries the same `request_id`, with nothing passed around
manually. The response also gets an `X-Request-ID` header back.

**Testing logging behavior:** use `structlog.testing.capture_logs()`
rather than parsing stdout. It disables the configured processor
pipeline for its duration, so if a test needs `request_id` (or anything
else from `structlog.contextvars`) to show up, pass it back in explicitly:

```python
with structlog.testing.capture_logs(
    processors=[structlog.contextvars.merge_contextvars]
) as captured:
    response = client.get("/api/v1/health")
```

### Changing the console theme or colors

Both live in `app/core/logging.py`, inside the `if sys.stdout.isatty():`
branch (the local-dev console path — the JSON path has no theme/color
concept, it's plain data).

**Exception traceback theme** — currently `monokai`
(`RichTracebackFormatter(theme="monokai")`). This is a [Pygments](https://pygments.org/styles/)
syntax-highlighting theme name; any installed Pygments style works.

All 50 theme names actually installed in this environment (verified via
the command below, not just documented — rerun it after a dependency
bump in case Pygments adds/removes styles):

```bash
.venv/bin/python -c "from pygments.styles import get_all_styles; print(sorted(get_all_styles()))"
```

```
abap, algol, algol_nu, arduino, autumn, borland, bw, coffee, colorful,
default, dracula, emacs, friendly, friendly_grayscale, fruity,
github-dark, gruvbox-dark, gruvbox-light, igor, inkpot, lightbulb,
lilypond, lovelace, manni, material, monokai, murphy, native, night-owl,
nord, nord-darker, one-dark, paraiso-dark, paraiso-light, pastie,
perldoc, rainbow_dash, rrt, sas, solarized-dark, solarized-light,
staroffice, stata-dark, stata-light, tango, trac, vim, vs, xcode, zenburn
```

Popular choices for a dark terminal: `monokai`, `dracula`, `one-dark`,
`nord`, `gruvbox-dark`, `solarized-dark`, `night-owl`, `github-dark`.
Switch it by editing the one string:

```python
structlog.dev.RichTracebackFormatter(theme="dracula")
```

**Level colors** (the color of the `info`/`warning`/`error` label
itself) — currently the library defaults, which use the same green for
both `debug` and `info`. Override with `level_styles` on
`ConsoleRenderer`:

```python
structlog.dev.ConsoleRenderer(
    level_styles={
        "debug": "\x1b[90m",  # gray
        "info": "\x1b[36m",  # cyan
        "warning": "\x1b[33m",  # yellow (library default)
        "error": "\x1b[31m",  # red (library default)
        "critical": "\x1b[35m",  # magenta
        "exception": "\x1b[35m",
        "notset": "\x1b[41m",
    },
    exception_formatter=structlog.dev.RichTracebackFormatter(theme="monokai"),
)
```

See the current defaults for any styles you don't want to override:

```bash
.venv/bin/python -c "import structlog.dev; print(structlog.dev.ConsoleRenderer.get_default_level_styles())"
```

Any ANSI escape code works as a `level_styles` value — `structlog.dev`
exports these as named constants (all verified against the installed
version), which is clearer than typing raw escape sequences:

| Constant | Value | Color |
|---|---|---|
| `structlog.dev.RED` | `\x1b[31m` | red |
| `structlog.dev.GREEN` | `\x1b[32m` | green |
| `structlog.dev.YELLOW` | `\x1b[33m` | yellow |
| `structlog.dev.BLUE` | `\x1b[34m` | blue |
| `structlog.dev.MAGENTA` | `\x1b[35m` | magenta |
| `structlog.dev.CYAN` | `\x1b[36m` | cyan |
| `structlog.dev.RED_BACK` | `\x1b[41m` | red background |
| `structlog.dev.BRIGHT` | `\x1b[1m` | bold/bright modifier |
| `structlog.dev.DIM` | `\x1b[2m` | dim modifier |
| `structlog.dev.RESET_ALL` | `\x1b[0m` | reset |

That's a small, fixed named set (8 base colors' worth — no named gray,
for instance). For anything outside it — gray (`\x1b[90m`), any 256-color
code, or a truecolor RGB code (`\x1b[38;2;R;G;Bm`) — just use the raw
ANSI escape string directly, exactly like the `"debug": "\x1b[90m"`
example above.

To disable color entirely (e.g. a terminal that mangles ANSI codes),
pass `colors=False` to `ConsoleRenderer` — this has no effect on the
JSON path, which was never colored to begin with.

## Linting & formatting

```bash
.venv/bin/ruff check .            # lint
.venv/bin/ruff check --fix .      # lint, auto-fixing what's safely fixable
.venv/bin/ruff format .           # reformat
.venv/bin/ruff format --check .   # verify formatting without changing files
.venv/bin/bandit -c pyproject.toml -r app   # security scan
```

Or run everything at once, exactly as the pre-commit hook does
(`.pre-commit-config.yaml` at the repo root):

```bash
.venv/bin/pre-commit run --all-files
```

## Testing

**Tests are written alongside each task, not batched at the end.**
Retrofitting tests after several tasks are already built is expensive
(re-deriving edge cases for code you no longer remember) and risky (bugs
compound into later work before anything catches them). A task isn't done
until its tests exist and pass.

Run the full suite (this is the command — also runs coverage automatically):

```bash
cd backend
.venv/bin/pytest
```

or, with the venv activated:

```bash
pytest
```

Useful variants:

```bash
pytest -v                              # verbose, one line per test
pytest tests/routes/test_health.py     # just one file
pytest -k "health"                     # just tests matching a keyword
pytest --cov=app --cov-report=html     # HTML coverage report → htmlcov/index.html
```

Note: the coverage % printed only reflects whatever files/tests you pointed
`pytest` at — `pytest tests/routes/test_health.py` shows a lower % than the
real project number because it never runs the tests that exercise
`app/core/exception_handlers.py`. Run bare `pytest` (no path) for the true,
whole-project number.

Coverage is enforced, not just reported: `pyproject.toml` sets
`--cov-fail-under=85` and `branch = true`, so `pytest` **fails the run** if
statement+branch coverage on `app/` drops below 85% — branch coverage
specifically catches an `if/else` where only one side was ever tested. If
you add code that drops coverage below that, the fix is to add tests, not
to lower the threshold.

### Nicer output (`pytest-sugar`)

**What it does:** replaces pytest's default output (a flat line of dots —
`....F..` — followed by a separate failure summary at the end) with a live,
color-coded, per-file progress display, and reformats failures/tracebacks
to be easier to scan.

**How it works:** it's a pytest plugin, registered via a standard pytest
entry point. Once it's installed in the environment, pytest auto-discovers
and loads it — there's no import to add, no config to write, and no way to
invoke it separately from pytest itself. You can confirm it's active from
the `plugins:` line pytest prints at the top of a run:

```
plugins: asyncio-0.24.0, cov-5.0.0, anyio-4.14.2, sugar-1.1.1, mock-3.14.0
```

**Command to run:** none — there's no `pytest-sugar` command. It activates
automatically on the same command you already use:

```bash
pytest
```

**What it covers:** purely the terminal presentation of results pytest
already produced — pass/fail counts, a progress bar, which file is
currently running, colorized tracebacks on failure.

**What it does *not* cover:** anything about test *quality*. It doesn't
run coverage, doesn't check branches, doesn't verify assertions are
meaningful, and can't tell you a test is weak or missing — it only makes
the existing pass/fail output easier to read. It has no relationship to
`pytest-cov`'s coverage % or to what `mutmut` checks below; they run
independently and `pytest-sugar` just decorates whichever one's output
reaches the terminal.

**Useful when:** running the suite locally and scanning output by eye —
which file is slow, which test just failed, at a glance. Marginal value in
CI logs (which are usually read after the fact, non-interactively, where
plain dots are just as readable and sometimes parse more easily).

**Not useful for:** anything you'd point automation at — don't parse
`pytest-sugar`'s output programmatically; use `pytest`'s own machine-
readable outputs (exit code, `--junitxml`, `-q`) for that instead.

### Mutation testing (`mutmut`)

Coverage answers "did this line run?" — it doesn't answer "would a test
actually have caught a bug here?" A line can be "covered" by a test with a
weak or missing assertion. `mutmut` checks that directly: it automatically
rewrites small pieces of `app/` (flips a `<` to `<=`, `True` to `False`,
etc.) and reruns the test suite against each rewrite ("mutant"). A mutant
the tests **kill** (catch, i.e. some test now fails) means that logic is
genuinely verified. A mutant that **survives** (all tests still pass) means
that piece of logic isn't really being tested, whatever the coverage number
says.

```bash
mutmut run                              # generate mutants of app/, test each one
mutmut results                          # list every mutant and its outcome
mutmut show <mutant-id>                 # see the exact diff for one mutant
```

It's configured in `pyproject.toml`'s `[tool.mutmut]` to mutate `app/` and
to run pytest with `--no-cov` — mutation runs need coverage collection
turned off, otherwise the `--cov-fail-under` gate (which measures something
different here — mutated code, not your real code) fails the run for
unrelated reasons.

This is slower than a normal test run and most useful in bursts (after
adding real business logic, not after every small change) — it's not part
of the day-to-day `pytest` command.

Conventions:
- Test layout mirrors `app/` 1:1 — `app/core/responses.py` →
  `tests/core/test_responses.py`.
- Use the `client` fixture (`tests/conftest.py`, a FastAPI `TestClient`)
  for anything hitting an endpoint.
- Async code gets a plain `async def test_...` — `asyncio_mode = "auto"`
  in `pyproject.toml` means no `@pytest.mark.asyncio` decorator needed.
- Test files and fixtures are committed to git like any other source —
  they are not scratch/disposable.
