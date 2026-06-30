# Phase Plan — Test Preconditions & Teardowns (BusterBlock)

**Status:** plan → implemented in this branch.
**Goal:** mimic the Java/JDBC pattern where you *seed data before a test and clean
up after*. In Java you open a JDBC connection and run SQL in `@Before`/`@After`.
BusterBlock has **no SQL database** — its state lives in in-memory `Map`s inside
`server.js` (`carts`, `orders`) plus `movies.json` loaded at startup. So the
"database" we manipulate is that in-memory store, reached over a small test-only
HTTP surface.

## Decisions (locked)

1. **DB seam:** add test-only `/api/test/*` endpoints to the app. The in-memory
   `Map` *is* the database; these endpoints are the manipulation surface
   (`reset`, set `stock`, `seed-cart`). Gated behind `BB_TEST_API` (on by default
   for this test app, set `BB_TEST_API=0` to disable).
2. **Mechanism:** tag-driven YAML fixtures. A scenario tagged
   `@precondition:NAME` runs `NAME`'s `setup:` HTTP calls in `before_scenario`
   and its `teardown:` calls in `after_scenario`. This is the direct analog of
   JUnit `@Before`/`@After` SQL fixtures and is the only option that cleanly
   covers **teardown** (Gherkin `Background:` has no teardown counterpart).

## Why not the alternatives

- **Gherkin `Background:` + `api_call` steps** already work for *setup* (the
  resolver has `api_call`/`load_data`), but `Background` runs only *before* a
  scenario — there is no native teardown, which the requirement demands.
- **A real SQLite DB** would be a truer JDBC analog but is a large rewrite of the
  test app for no test-coverage gain; the in-memory store already models the
  domain.

## Phases

### Phase 1 — Rename test app
`git mv vhs-vault test-app`; update `package.json` name. URL
(`http://localhost:3333`) and the `[BUSTERBLOCK]` env key are unchanged.

### Phase 2 — Test seam in `server.js`
Snapshot original stock at startup, then (behind `BB_TEST_API`):
- `POST /api/test/reset` — clear carts + orders, restore every movie's stock to
  its startup value. The universal teardown.
- `PATCH /api/test/stock` — `{movieId, stock}`; force a movie's stock (e.g. 0 to
  test the out-of-stock path).
- `POST /api/test/seed-cart` — `{username, items:[{movieId, qty}]}`; pre-fill a
  user's cart without driving the UI.

### Phase 3 — Framework precondition runner
New module `bddframe/preconditions.py`:
- Reads `preconditions.yaml` from the **feature's own folder**.
- For each `@precondition:NAME` tag, runs that fixture's `setup:` / `teardown:`
  list of `METHOD URL [JSON]` lines.
- `[VAR]` substitution reuses `orchestrator.runner.substitute`, so
  `[BUSTERBLOCK]` resolves from `environments.yaml`.
- HTTP via **stdlib `urllib`** — no new dependency.

Wire into `bddframe/hooks.py`:
- `before_scenario` → `preconditions.run(scenario, "setup")`.
- `after_scenario` → `preconditions.run(scenario, "teardown")`, run early and
  guarded so it **always fires, even when the scenario failed** (the whole point
  of teardown).

### Phase 4 — Fixtures + example feature
- `features/busterblock/preconditions.yaml` — two fixtures
  (`jaws_out_of_stock`, `cart_preseeded`).
- `features/busterblock/preconditions.feature` — a documented `.feature` showing
  both: one asserts a *seeded-empty-stock* precondition in the UI, one asserts a
  *pre-seeded cart*. Each carries its `teardown:` reset.

### Phase 5 — Test + docs
- One `unit_tests/test_preconditions.py` self-check for the `METHOD URL JSON`
  parser (the only non-trivial logic).
- README: a "Run the test app" section + a "Preconditions & teardowns" section.

## Teardown guarantees

- `teardown:` runs in `after_scenario` regardless of pass/fail.
- Every fixture's teardown is `POST /api/test/reset`, so state never leaks between
  scenarios even if a setup half-completed.
- `before_all` already wipes per-run artifacts; preconditions add per-scenario
  data isolation on top.

## Out of scope

- Auth on `/api/test/*` (test app, gated by env — `ponytail:` flag, not a
  security boundary).
- Parallel-shard DB isolation: each shard runs its own app instance, so resets
  don't collide. Revisit only if shards ever share one app.
