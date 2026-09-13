# interview-ai-agent — frontend

**Status: tooling scaffolded, features not built.** Per the root
[`CLAUDE.md`](../CLAUDE.md)'s backend-first build order, no frontend
*feature* code is written until Build Stage 7 — every backend endpoint
(Stages 1–6) gets built and verified via Swagger UI first, so the API
contract is stable before real UI is built against it.

**Exception, done ahead of schedule at the user's explicit request:** the
tooling below — TypeScript, Tailwind, TanStack Query, React Router,
Vitest, oxlint/Prettier — is installed, configured, and verified
end-to-end (`npm run typecheck`, `lint`, `test`, `build` all pass; a real
browser load shows the health-check page correctly). The `features/`
folder skeleton exists with one route per Interview Phase group, but
every page except `health-check/` is still an inert placeholder — this is
setup, not the interview UI. The rest of this document is still a **spec
to build against** for the actual feature logic: when each backend
stage's endpoints land, that placeholder page gets replaced with the real
thing. If a decision here turns out wrong once that happens, update this
file in the same commit, don't just silently diverge from it.

## Tech stack

| Concern | Choice | Why |
|---|---|---|
| Framework | React 19 (already scaffolded) | |
| Build tool | Vite (already scaffolded) | |
| Language | **TypeScript** | Type-checks the frontend against the backend's response envelope (`{success, status, status_code, data, error}` — see `backend/README.md`) at compile time instead of finding contract drift as a runtime bug in the browser. |
| Styling | **Tailwind CSS** | Utility classes colocated with markup — no separate `.css`/`.module.css` file per component to keep in sync as the UI grows across 6+ distinct pages (upload, chat, coding editor, report, ...). |
| Server state / data fetching | **TanStack Query** | Handles caching, loading/error state, and polling in one hook each — this project genuinely needs caching (report data), polling (coding-challenge Judge0 result isn't instant), and one-shot mutations (resume upload), not just simple one-off fetches. See the comparison below for why this beat plain `fetch` and Redux Toolkit. |
| Routing | **React Router** | Standard for a multi-page SPA (upload → chat → coding challenge → report). Not deeply debated — this project's routing needs (a handful of top-level pages, no nested-loader complexity) don't call for TanStack Router's extra data-loading machinery. |
| HTTP client | Native `fetch`, wrapped in one thin `lib/api.ts` client | No axios — same "minimal dependency count" principle the backend follows with plain `httpx` instead of provider SDKs. `fetch` + a small wrapper that unwraps the envelope and throws on `error` is all `TanStack Query`'s `queryFn`/`mutationFn` need. |
| Streaming (chat replies) | `fetch` + `ReadableStream`, or `EventSource` (SSE) | Matches the backend's streaming Gateway (`backend/README.md`'s LLM Gateway) — the Interviewer's replies arrive token-by-token, same as `curl`-verified in Stage 2. |
| Code editor (Stage 7 coding challenge only) | `@monaco-editor/react` | Not installed yet — only needed once the coding-challenge page is actually built. |
| Testing | **Vitest** + **React Testing Library** + `@testing-library/user-event` + `jsdom` | Vitest is Vite's native test runner (same config, same transform pipeline — no separate Jest/Babel setup to maintain). Mirrors the backend's `pytest` discipline: tests alongside each component, not batched at the end. |
| Linting | `oxlint` (already scaffolded) | Rust-based, near-instant, already configured for `react`/`oxc` rules in `.oxlintrc.json`. |
| Formatting | Prettier | `oxlint` is lint-only (no stable formatter yet as of this writing) — same split the backend doesn't need (`ruff` does both), so Prettier fills the formatting half here. |

### Why TanStack Query over the alternatives

Three real options were compared against this project's actual pages, not
in the abstract:

- **Plain `fetch` + custom hooks:** zero dependencies, but the
  loading/error/cancel-on-unmount plumbing gets hand-written on every
  page that fetches something (resume upload, chat, submission polling,
  report — four times), and there's no shared cache if two components
  need the same data.
- **Redux Toolkit + RTK Query:** this project's state is almost entirely
  *server* state (candidate profile, transcript, submission result,
  report) — exactly what RTK Query already covers, making the Redux
  store/slice/`Provider` boilerplate around it dead weight nothing here
  needs.
- **TanStack Query (chosen):** `refetchInterval` gives the coding-challenge
  polling loop in one line; `queryKey`-based caching gives the report page
  its cache for free; no global store to configure for state that isn't
  global to begin with.

Client-only UI state (a form field, a modal's open/closed flag) stays
plain `useState`/`useContext` — don't reach for a global state library for
that; there's nothing here that needs one.

## Planned project structure

Feature-based (a.k.a. "feature-sliced"), not type-based — this is the
current (2026) standard over the older `components/`, `hooks/`, `api/`
top-level split, because a feature usually changes as one unit (a page's
component, its hooks, and its API calls all move together) and should be
deletable as one unit:

```
frontend/                            # ✓ = real, built and verified; everything else is a placeholder
├── src/
│   ├── main.tsx                   # ✓ entry point — QueryClientProvider + RootErrorBoundary + App
│   ├── App.tsx                    # ✓ React Router route table
│   ├── app/
│   │   └── queryClient.ts         # ✓ one shared TanStack QueryClient instance
│   ├── features/
│   │   ├── health-check/          # ✓ REAL — proves the whole chain end-to-end, not a placeholder
│   │   │   ├── HealthStatus.tsx       #   renders GET /health via useHealthCheck
│   │   │   ├── useHealthCheck.ts      #   TanStack Query wrapping api.get('/health')
│   │   │   └── HealthStatus.test.tsx
│   │   ├── resume-upload/         # placeholder — Interview setup: resume PDF + JD input
│   │   │   └── ResumeUploadPage.tsx   #   real useUploadResume.ts mutation lands with Stage 1's
│   │   │                              #   POST /candidates/resume endpoint
│   │   ├── interview-chat/        # placeholder — Phases 1,2,3,5,6,7, one continuous view
│   │   │   └── InterviewChatPage.tsx  #   real useChatStream.ts (ReadableStream/SSE) lands with
│   │   │                              #   Stage 2's chat-turn endpoints
│   │   ├── coding-challenge/      # placeholder — Phase 4, Monaco editor + timer
│   │   │   └── CodingChallengePage.tsx #  real useSubmission.ts (mutation + polling useQuery)
│   │   │                              #   lands with Stage 4's orchestrator
│   │   └── report/                # placeholder — final evidence-backed report view
│   │       └── ReportPage.tsx         #   real useReport.ts (cached useQuery) lands with
│   │                                  #   Stage 5's report endpoint
│   ├── components/
│   │   └── RootErrorBoundary.tsx  # ✓ root-level render-crash fallback (see Error handling below)
│   ├── lib/
│   │   └── api.ts                 # ✓ fetch wrapper: unwraps {success, data, error}, throws on error
│   ├── types/
│   │   └── api.ts                 # ✓ TS types mirroring backend/app/schemas/response.py
│   ├── test/
│   │   └── setup.ts               # ✓ vitest setup — @testing-library/jest-dom matchers
│   └── index.css                  # ✓ `@import "tailwindcss"` — no hand-written global CSS beyond this
├── public/
├── .env.example                    # ✓ VITE_-prefixed vars only (see Env vars below)
├── package.json
                                     #   (no package-lock.json — gitignored, see below)
├── vite.config.ts                  # ✓ react + tailwindcss plugins, dev proxy, vitest config (merged)
├── tsconfig.json                   # ✓ project-reference root (→ tsconfig.app.json / tsconfig.node.json)
├── tsconfig.app.json               # ✓ src/ — strict, react-jsx, vite/client + vitest/globals types
├── tsconfig.node.json               # ✓ vite.config.ts itself
├── .prettierrc.json / .prettierignore  # ✓
└── .oxlintrc.json                  # ✓ react, oxc, typescript, vitest plugins
```

Note: no `tailwind.config.*` — Tailwind v4's `@tailwindcss/vite` plugin
needs no separate config file for this project's needs; theme
customization (once there's an actual design to encode) happens via
`@theme` in `index.css` itself, not a JS config object.

There's also no top-level `tests/` — colocated `*.test.tsx` next to each
component instead (`HealthStatus.test.tsx` sits right next to
`HealthStatus.tsx`), per the colocation rule below.

Rules that keep this from rotting back into a tangle as pages are added:

- **Colocation:** a hook or helper used by only one feature lives inside
  that feature's folder, not in a shared `utils/`. It only moves to
  `lib/`/`components/` once a *second* feature needs it.
- **No cross-feature imports.** `coding-challenge/` never imports from
  `interview-chat/`. If two features need to share something, that thing
  is promoted to `components/`/`lib/`, and both features import it from
  there — never from each other.
- **No barrel files** (`features/interview-chat/index.ts` re-exporting
  everything). They defeat Vite's tree-shaking and add an indirection
  layer with no real benefit here — import each file directly.

## Consuming the backend's response envelope

Every backend endpoint returns the same shape (see `backend/README.md`).
The frontend should unwrap it in exactly one place — `lib/api.ts` — so
every feature's `queryFn`/`mutationFn` just gets the real `data`, or a
thrown error `TanStack Query` already knows how to surface:

```ts
// lib/api.ts
type ApiEnvelope<T> =
  | { success: true; data: T }
  | { success: false; data: null; error: { message: string } }

export async function apiGet<T>(path: string): Promise<T> {
  const res = await fetch(`/api/v1${path}`)
  const body: ApiEnvelope<T> = await res.json()
  if (!body.success) throw new Error(body.error.message)
  return body.data
}
```

```ts
// features/report/useReport.ts
export function useReport(sessionId: string) {
  return useQuery({
    queryKey: ['report', sessionId],
    queryFn: () => apiGet<Report>(`/sessions/${sessionId}/report`),
  })
}
```

## Env vars

Vite only exposes env vars prefixed `VITE_` to client code (via
`import.meta.env.VITE_...`) — anything without that prefix is a build-time
Node var, invisible to the browser bundle, which is also why secrets never
belong here: **nothing** in `frontend/.env` should be a real API key
(OpenAI/ElevenLabs/Judge0 keys stay server-side in `backend/.env`, never
shipped to the browser). Realistically this file will only ever need
something like `VITE_API_BASE_URL`. Mirror the backend's pattern once
real vars exist: commit a `.env.example` with placeholder values, gitignore
the real `.env`.

## Error handling & logging (no direct backend-logger equivalent)

The backend's `structlog` setup (`backend/README.md`'s Logging section)
has **no direct frontend equivalent** — there's no server process here to
attach a request-correlated logger to, and no Postgres table nearby to
write structured lines into. The right analog for a frontend is a
different pair of tools, solving a different problem (a component crash
loses the whole app instantly if unhandled — the interviewer voice-first
UX has no room for a white screen mid-interview):

- **React Error Boundaries** — catch render-time crashes in their child
  tree and show a fallback UI instead of a blank page. Placed at multiple
  levels, not one boundary around the whole `<App/>`:
  - **Root boundary** — last resort, generic "something went wrong,
    reload" fallback.
  - **Per-feature boundary** — e.g. one around `interview-chat/`, so if
    a rendering bug crashes the chat view mid-interview, the candidate
    sees a scoped error in that panel, not a full-page wipe of an
    in-progress session.
  - **What they don't catch:** errors in event handlers, `async`
    callbacks, or the boundary component itself — those still need plain
    `try/catch` at the call site (e.g. around the `fetch` in
    `useChatStream.ts`), same as any JS error handling.
- **Client-side logging stays console-only by default** — `console.debug`
  during `npm run dev`, gated off in production builds (Vite strips
  `console.*` calls in prod via `esbuild`'s `drop` option if configured,
  or gate manually behind `import.meta.env.DEV`). Unlike the backend, a
  frontend console log never reaches you unless a user opens devtools and
  pastes it — there's nothing to aggregate on its own.
- **Actual production visibility needs an error-tracking service**
  (Sentry is the standard 2026 default; Datadog RUM/LogRocket are
  alternatives) — this is what actually ships browser errors somewhere
  you can see them, the closest real equivalent to the backend's logging
  table. **Not needed now** — this is a `Pre-Deployment Checklist`-shaped
  concern (root `CLAUDE.md`), i.e. fine to add at Stage 8 once this is
  exposed beyond local testing, not a Stage 7 blocker.

## Testing

Same discipline as the backend's `pytest` — tests written alongside each
component, not batched at the end (see root `CLAUDE.md`'s Testing
Discipline section, which applies project-wide, not just to `backend/`).
`health-check/HealthStatus.test.tsx` is the first real example of this —
every placeholder page picks up its own colocated test once it gets real
logic.

```bash
npm run test          # vitest run
npm run test:watch    # vitest (watch mode)
npm run test:coverage # vitest run --coverage
```

- Test files live next to what they test (`ResumeUploadPage.tsx` →
  `ResumeUploadPage.test.tsx`), not in a mirrored `tests/` tree — colocation
  applies to tests too, for the same reason it applies to hooks/helpers.
- `@testing-library/react` + `@testing-library/user-event` for
  component tests — assert on what the user sees/does (rendered text,
  clicks, typed input), not on internal component state.
- Mock the network boundary (`lib/api.ts`), not `TanStack Query` itself —
  tests should exercise the real query/mutation hooks against a fake
  server response, the same way backend tests hit a real `TestClient`
  rather than mocking the router.

## Linting & formatting

```bash
npm run lint            # oxlint
npm run format          # prettier --write
npm run format:check    # verify formatting without changing files
```

## Running locally

```bash
cd frontend
npm install
npm run dev         # http://localhost:5173 — proxies /api/* to the
                     #   backend on :8000 (vite.config.ts), so start the
                     #   backend too (see backend/README.md) to see the
                     #   health-check on the home page turn green
npm run typecheck   # tsc -b --noEmit
npm run test         # vitest run
npm run build        # tsc -b && vite build → dist/
npm run preview      # serve the production build locally
```

## `package-lock.json` is gitignored

Not committed, on `.gitignore` — a deliberate call for this project,
against the more common default (an application normally *does* commit
its lockfile, unlike a published library). Worth knowing what that
trades away:

- `package.json` pins ranges, not exact versions (`"react": "^19.2.8"`
  allows any `19.x.x` ≥ `19.2.8`). Without a committed lockfile, `npm
  install` run on different machines — or days apart — can resolve
  *different* actual versions, including of nested dependencies nobody
  listed directly. Each environment (your machine, CI, Render's build)
  regenerates its own resolution independently.
- Practical effect right now: low risk, single-developer project, no CI
  pinning a specific lockfile yet. Revisit committing it once that
  changes (a collaborator, or a CI/deploy step that should be
  byte-for-byte reproducible).

## Pages (mapped to Interview Phases, per root `CLAUDE.md`)

| Route | Feature folder | Interview Phase(s) |
|---|---|---|
| `/setup` | `resume-upload/` | Resume + JD intake (Stage 1 backend) |
| `/interview/:sessionId` | `interview-chat/` | 1, 2, 3, 5, 6, 7 (all dialogue phases, one continuous view — matches the single persistent Interviewer agent, no page break per phase) |
| `/interview/:sessionId/coding` | `coding-challenge/` | 4 (only rendered if the JD implied a coding assessment) |
| `/interview/:sessionId/report` | `report/` | Final evidence-backed report |

The chat UI staying **one page across phases 1–7** (not one route per
phase) matches a decision already made on the backend: the Conversational
Interviewer is one continuous agent/thread, not phase-per-agent, to avoid
a jarring tone shift at phase transitions on a voice-first UX (see root
`CLAUDE.md`'s Agent Architecture). The frontend shouldn't reintroduce that
seam with a route change per phase.
