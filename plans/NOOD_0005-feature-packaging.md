# Plan — Self-Contained Feature Packages (NOOD_0005)

**Status:** plan → not yet implemented.
**Goal:** each app-under-test's folder under `features/` (e.g.
`features/web/busterblock`) becomes a self-contained package — its own env,
secrets, config, and resources live inside it, so an agent (or a human) can
add a new app-under-test without touching shared/root files, and without
risking collisions with other suites.

## Is this viable? Yes — and it's mostly already built

Three of the four things the user asked to package are **already
per-folder**, not global:

- `resources/` (payloads, CSVs) — resolved relative to the feature's own
  folder (`noodle/orchestrator/runner.py:225`).
- `scripts/*.py` — same (`noodle/orchestrator/script_runner.py`).
- `pageobjects/*_pom.yaml` + local `pom.yaml` — `noodle/agents/web/pom.py`
  already does a local → global cascade, set per-feature via
  `pom_module.set_context()` in `before_feature`.
- `environments.yaml` (base URLs) is *half* built: `noodle/hooks.py:_load_environments`
  already globs `features/**/resources/environments.yaml` as a suite-level
  override on top of the root file — nobody uses this path today, but the
  mechanism exists.

**The actual gap:** `.env` (config) and `secrets.env` (credentials) are
loaded exactly once, from the repo root, in `before_all`
(`noodle/hooks.py:81-83`). There is no per-package config/secrets file. This
is the only new mechanism this plan needs to add — everything else is
"formalize and document a convention that mostly already exists."

Recommendation: **extend the existing local/global cascade pattern**
(same shape as `pom.py`'s local-then-global chain) rather than designing a
new packaging system. Reuse `load_dotenv()`'s own semantics (first value
wins, doesn't override an already-set key) — that's the same "root wins,
suite can only add" rule `_load_environments` already documents.

## Two supported topologies — both must keep working

The framework already has a workspace abstraction for this; the plan adopts
it rather than inventing a second one:

- **In-repo (route A, current default):** `noodle/` (the framework) and
  `features/` live in the same repo. `noodle run` with no `--workspace`
  defaults to `workspace="."` (`noodle/cli.py:37`), so `features/` is
  resolved relative to the repo root.
- **External workspace (route B, the future layout in this request):**
  ```
  /path/to/workspace/noodle/                # pip-installed dependency, not a sibling copy of the repo
  /path/to/workspace/features/canadiantire/
  /path/to/workspace/features/busterblock/
  ```
  `noodle` is installed as a package (`pyproject.toml` already ships
  `[project.scripts] noodle = "noodle.cli:app"`, so this works today via
  `pip install`/`pip install -e`, no packaging change needed). The workspace
  itself is scaffolded by `noodle init` (`noodle.yaml`, `.env`,
  `features/environment.py`, `features/steps/z_catch_all.py`) and driven with
  `noodle run --workspace /path/to/workspace`. `noodle/config.py:load()` reads
  `noodle.yaml` from that workspace; `cli.py`'s `run()` sets `cwd = workspace`
  before shelling out to `behave` (`cli.py:91,105`).

**Why the per-package design needs no topology branch:** every path in
`hooks.py` and `pom.py` is resolved from `Path.cwd()` or from
`Path(feature.filename).parent` (the feature's own folder) — never from
`noodle`'s install location. Since the CLI always runs `behave` with
`cwd=workspace`, `Path.cwd()` is the repo root in route A and the external
workspace root in route B, automatically. The package contract below (and
the Phase 2 loader) therefore work unmodified in either topology — a
`features/busterblock/environment/secrets.env` resolves the same way whether
`features/` sits inside the noodle repo or two directories away from it in
someone's own workspace.

## Resolution algorithm — which .env / pom / yaml / config wins

For the `.feature` file currently loading, let `feature_dir` =
`Path(feature.filename).parent` (its own package folder) and `workspace` =
`Path.cwd()` (repo root in route A, `--workspace` dir in route B):

| File type | Order (first found / first-set wins) |
|---|---|
| `[VAR]` secrets & config | 1. real process env vars (CI-injected, always wins) → 2. `workspace/.env` → 3. `workspace/secrets.env` → 4. `feature_dir/environment/.env` → 5. `feature_dir/environment/secrets.env` |
| `[VAR]` base URLs | 1. `workspace/environments.yaml` → 2. `feature_dir/environment/environments.yaml` |
| Page objects | 1. `feature_dir/pageobjects/*_pom.yaml` → 2. `feature_dir/pom.yaml` → 3. nearest ancestor `pom.yaml`/`features/pom.yaml` found by walking up from `feature_dir` (`pom.py:_global_pom_path`) |
| Test data / fixtures | `feature_dir/resources/**` only — no cascade, no fallback (package-local by design) |
| Scripts | `feature_dir/scripts/**` only — same |

Steps 2-3 in the env/config row are what `before_all` already does
(`load_dotenv()` then `load_dotenv("secrets.env")`, both cwd-relative); steps
4-5 are what Phase 2 below adds, called once per package from
`before_feature`. `load_dotenv()`'s own default (set a key only if not
already in `os.environ`) is what enforces "first wins" — no new merge logic
needed, just more calls in the same shape as the existing ones.

## The package contract

```
features/<category>/<app>/
  *.feature
  environment/
    .env                    # committed, no secrets — package config overrides
    secrets.env             # gitignored — package credentials
    secrets.env.example     # committed template for the above
    environments.yaml       # optional — base URL(s) for this app
  resources/
    payloads/...
    *.csv
  pageobjects/
    *_pom.yaml
  pom.yaml                  # local element overrides
  scripts/
    *.py
```

`environment/` holds anything the agent must never mix between apps
(credentials, base URLs, feature flags). `resources/` holds everything else
a scenario needs to run (test data, seed scripts, page objects). This maps
directly onto the busterblock/canadiantire examples in the user story —
`environment/environments.yaml` replaces the currently-unused
`resources/environments.yaml` path (nothing adopts that path yet, so moving
it costs nothing).

## The collision risk (must be documented, not "solved")

`os.environ` is one flat namespace per process, and a behave worker runs all
of a suite's features sequentially in that same process — so package env
files load into the same global dict everything else reads from. This is
already true of `environments.yaml` today (root wins, suites can only add
new keys, never override). Package `.env`/`secrets.env` will follow the
identical rule: **first load wins.**

Consequence: two packages must not reuse a generic key name (`USERNAME`,
`PASSWORD`) or the second package silently gets the first package's value.
The existing root `secrets.env.example` already avoids this by convention
(`BB_USER`/`BB_PASS`, `SAUCE_USERNAME`/`SAUCE_PASSWORD`) — the plan is to
write that convention down as a rule, not to build env-sandboxing per
scenario. Automatic collision detection is explicitly deferred (see Out of
scope) — add it only if a real collision happens.

## Phases

### Phase 1 — Docs (this branch)
This plan doc + a `docs/feature-packages.md` describing the contract above,
linked from the README's "Configuration" section and from the agent-facing
instructions, so an agent creating a new app-under-test knows to scaffold
`environment/` + `resources/` inside the app's own folder instead of adding
keys to root `.env`/`secrets.env`.

### Phase 2 — Loader
In `noodle/hooks.py`:
- `before_feature` gains a call alongside the existing
  `pom_module.set_context(...)` line: `load_dotenv(feature_dir / "environment" / ".env")`
  and `load_dotenv(feature_dir / "environment" / "secrets.env")`, same
  non-override semantics as the root loads in `before_all`.
- `_load_environments()`'s glob changes from
  `features/**/resources/environments.yaml` to
  `features/**/environment/environments.yaml` (unused path today — free
  rename).
- Track visited package dirs in a module-level set so repeat `before_feature`
  calls for feature files in the same package don't re-glob/re-parse.

### Phase 2b — Align the scaffolding tools with the per-app shape
Found while checking route B: `noodle init` and `noodle/agent/generate.py`
predate the per-app-package convention and are flat/single-app today —
`_NOODLE_YAML` (`cli.py:208`) scaffolds one workspace-wide
`pageobjects_dir: features/pageobjects`, and `generate()`/`generate_llm()`
(`generate.py:92,109`) write every generated `.feature`/POM straight into
`features_dir`/`pageobjects_dir`, with no app subfolder. Left alone, a
workspace with two apps-under-test would still get one shared
`pageobjects/`, defeating the whole point of packaging. Fix: both need an
`--app <name>` (or description-derived) folder segment so generated files
land at `<features_dir>/<app>/{*.feature, pageobjects/, environment/, resources/}`,
matching what `pom.py`/`runner.py` already resolve at runtime.

Also drop `pageobjects_dir` from `noodle.yaml`/`config.py`'s `DEFAULTS` once
`generate.py` is fixed — it's already dead as far as the *runtime* engine is
concerned (`pom.py` never reads it; it hardcodes `<feature_dir>/pageobjects`)
and keeping it around as a workspace-level config key implies a single flat
pageobjects dir that contradicts the per-package model. One source of truth,
not two.

### Phase 3 — Gitignore + example files
- `.gitignore`: add `features/**/environment/secrets.env` alongside the
  existing root `secrets.env` rule.
- Add `environment/secrets.env.example` to one package as the worked
  reference (see Phase 4).

### Phase 4 — Migrate one package as the worked example
Move BusterBlock's keys (`BB_USER`, `BB_PASS`) out of root `secrets.env` into
`features/web/busterblock/environment/secrets.env`, with a matching
`.example` file. Other suites (saucedemo, canadiantire, api) stay on root
`secrets.env` — migration is opt-in per package since root-first load order
means nothing breaks for suites that don't move.

### Phase 5 — Test + docs
- One `unit_tests/test_package_env.py` self-check: a folder with
  `environment/.env` gets its keys into `os.environ`, and an already-set root
  key is not clobbered.
- README "Configuration" section gets a "per-package config" subsection
  pointing at `docs/feature-packages.md`.

## Out of scope

- A second "which topology am I in" mechanism — `--workspace` / `noodle.yaml`
  / `config.load()` already exist and already make every path `Path.cwd()`-
  or `feature_dir`-relative; this plan reuses that, it doesn't add a
  parallel concept.
- A multi-app registry inside `noodle.yaml` (e.g. listing every app under a
  workspace) — the package boundary stays implicit ("any folder directly
  under `features_dir` holding `.feature` files"), same as today's PoM/
  resources resolution. Add a registry only if some tool actually needs to
  enumerate apps up front.
- Azure Key Vault packaging (`noodle/secrets_akv.py` stays root-only) — no
  per-package AKV paths.
- Automatic cross-package key-collision linting — revisit only if a real
  collision happens; the naming convention is the guard for now.
- Forcing existing suites (saucedemo, canadiantire, api) to migrate off root
  `secrets.env` — opt-in, not a mass rewrite.
- Per-scenario env sandboxing/unloading — `os.environ` stays a single
  process-wide namespace; not needed unless packages collide in practice.
