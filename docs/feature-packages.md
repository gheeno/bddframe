# Feature Packages

Each app-under-test gets its own self-contained folder under `features/` —
its env, secrets, base URLs, page objects, test data and scripts all live
inside that one folder. Nothing about an app leaks into another app's
folder, and nothing about an app needs to touch the shared root files.

This works the same whether `features/` sits inside the `noodle` repo or in
a separate workspace you run `noodle` against — see
[Two topologies](#two-topologies) below.

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

`environment/` holds anything that must never mix between apps (credentials,
base URLs, feature flags). `resources/` holds everything else a scenario
needs to run (test data, seed scripts). A package is just "whatever folder
directly contains the `.feature` files" — there's no registry to update,
`features/web/busterblock/` and `features/api/` are both packages, nesting
depth doesn't matter.

Worked example: [`features/web/busterblock/`](../features/web/busterblock)
has `BB_USER`/`BB_PASS` in `environment/secrets.env.example` and its base URL
in `environment/environments.yaml`.

## Resolution algorithm — which file wins

For the `.feature` file currently loading, `feature_dir` is its own package
folder and `workspace` is the run's working directory (the repo root, or
whatever `--workspace` points at):

| File type | Order (first found / first-set wins) |
|---|---|
| `[VAR]` secrets & config | 1. real process env vars (CI-injected, always wins) → 2. `workspace/.env` → 3. `workspace/secrets.env` → 4. `feature_dir/environment/.env` → 5. `feature_dir/environment/secrets.env` |
| `[VAR]` base URLs | 1. `workspace/environments.yaml` → 2. `feature_dir/environment/environments.yaml` |
| Page objects | 1. `feature_dir/pageobjects/*_pom.yaml` → 2. `feature_dir/pom.yaml` → 3. nearest ancestor `pom.yaml`/`features/pom.yaml` found by walking up from `feature_dir` |
| Test data / fixtures | `feature_dir/resources/**` only — no cascade |
| Scripts | `feature_dir/scripts/**` only — no cascade |

"First wins" comes straight from `load_dotenv()`'s own behaviour (it only
sets a key that isn't already in `os.environ`) — there's no separate merge
step to reason about.

### The collision rule

`os.environ` is one flat namespace per process. Two packages must not reuse
a generic key name (`USERNAME`, `PASSWORD`) — whichever package's feature
file runs first in that process "claims" the key, and the second package
silently gets the first one's value. Prefix package-specific keys with the
app name (`BB_USER`, `SAUCE_USERNAME`) exactly like the existing root
`secrets.env.example` already does. There's no automatic collision
detection — the naming convention is the guard.

## Two topologies

- **In-repo (default):** `noodle/` (the framework) and `features/` live in
  the same repo. `noodle run` with no `--workspace` resolves `features/`
  relative to the repo root.
- **External workspace:** `noodle` is installed as a dependency
  (`pip install noodle`) into a separate directory that holds its own
  `noodle.yaml`, `.env`, and `features/`:
  ```
  /path/to/workspace/features/canadiantire/
  /path/to/workspace/features/busterblock/
  ```
  Scaffold one with `noodle init`, then run with
  `noodle run --workspace /path/to/workspace`.

No code branches on which topology you're in. Every path above is resolved
from `Path.cwd()` or from the feature file's own folder — never from where
`noodle` itself is installed — and the CLI always runs `behave` with
`cwd` set to the workspace. A `features/busterblock/environment/secrets.env`
resolves identically either way.

## Adding a new app package

1. Create `features/<category>/<app>/` (or `features/<app>/` in a
   single-category workspace) with your `.feature` files.
2. Add `environment/secrets.env.example` for any credentials the scenarios
   need, prefixed with the app name. Copy it to `environment/secrets.env`
   locally (gitignored) and fill in real values.
3. Add `environment/environments.yaml` if the app has its own base URL.
4. Add `resources/`, `pageobjects/`, `scripts/` as needed — same rules as
   any existing suite.

`noodle agent`'s `create test for ... at ...` does steps 1 and part of 4 for
you automatically, deriving the app folder from the URL's host.
