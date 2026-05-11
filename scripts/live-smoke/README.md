# Live smoke: contracts & corporation market

## What “live smoke” means here

**`contractProxy`** and **`marketProxy`** RPCs are reached only through the **modified Crucible client** (marshaled login, bound services, session state). The server has **no** HTTP or console shortcut that replays **`CreateContract`**, **`AcceptContract`**, **`CompleteContract`**, or **`PlaceCharOrder`** end-to-end.

So:

| Goal | Can CI / this repo run it without the game client? |
|------|------------------------------------------------------|
| Tier A (build, DB up, server log, `ctrContracts` schema) | **Yes** — `scripts/smoke/docker-smoke.ps1` / `.sh` and GitHub **Docker smoke (Tier A)** |
| Tier B (DB evidence **after** you used the client) | **Yes** — `scripts/smoke/sql/*.sql` or `scripts/live-smoke/run-post-client-evidence.ps1` |
| Full **create → accept → complete** contracts or corp **PlaceCharOrder** flows | **No** — requires **you** (or a future headless harness) driving the client against a running stack |

Trying to fake that from SQL alone would **not** exercise wallet transfers, hangar rules, or session guards in `ContractProxy.cpp` / `MarketProxyService.cpp`.

## What you *can* run “from here” (agent / automation)

1. **Tier A** before a session: `pwsh .\scripts\smoke\docker-smoke.ps1` or `bash scripts/smoke/docker-smoke.sh`.
2. **Manual client** session on the same stack (corp courier batch, corp market batch).
3. **Tier B / evidence** immediately after:
   ```powershell
   pwsh .\scripts\live-smoke\run-post-client-evidence.ps1 -Target all
   ```
   Or run individual files under `scripts/smoke/sql/` with `docker compose exec -T db mariadb …` (see `scripts/smoke/README.md`).

## Paths to true headless “live” runs (not implemented)

These are **larger** than this folder; track them as separate restoration tasks if you need them:

1. **In-process tests** linking **`eve-server`** (or a thin `contract_smoke` target) with a synthetic **`Client`** / **`PyCallArgs`** — high setup cost; today **`eve-test`** only links **`eve-common`** and is not wired in the root `CMakeLists.txt`.
2. **Record / replay** of marshaled calls after one successful client capture (see paper-doll “trace procedure” in `EVEMU_RESTORATION_STATE.md`).
3. **Self-hosted runner** with the real client installed — operational, not a code substitute.

Until one of those exists, treat **Tier A + client + Tier B** as the authoritative live-smoke pipeline for this branch.
