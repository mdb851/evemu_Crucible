# Smoke baseline (Tier A + Tier B)

Narrow, repeatable checks for **infrastructure** and **optional post-client DB evidence**. This does **not** automate the Crucible client or login.

## Tier A — PowerShell or Bash

From the **repository root** (where `docker-compose.yml` lives).

**Windows (recommended):**

```powershell
pwsh .\scripts\smoke\docker-smoke.ps1
```

**Linux / macOS / GitHub Actions:**

```bash
bash scripts/smoke/docker-smoke.sh
```

Optional: extend the wait window for slow hosts or CI:

```bash
MAX_WAIT=300 bash scripts/smoke/docker-smoke.sh
```

PowerShell honors the same variable if set **before** invocation (it overrides `-MaxWaitSeconds`):

```powershell
$env:MAX_WAIT = '300'
pwsh .\scripts\smoke\docker-smoke.ps1
```

CI: `.github/workflows/docker-smoke.yml` runs **`docker-smoke.sh`** on pushes and PRs to **`master`**, **`staging`**, and **`restoration/**`** (plus **workflow_dispatch**), with **`permissions: contents: read`** and **`MAX_WAIT=300`**.

### Live-smoke without re-running Tier A

After a **manual client** session, collect DB evidence only:

```powershell
pwsh .\scripts\live-smoke\run-post-client-evidence.ps1 -Target all
```

See **`scripts/live-smoke/README.md`** for why the **game client** is still required for the RPC portion of contracts / corp market smoke.

### Troubleshooting (Actions / forks)

- Ensure **GitHub Actions** is enabled for the repository (forks may default to off until approved).
- First-time contributors: some orgs require **workflow approval** for PRs from forks; check the **Actions** tab for a pending run.
- If the job times out during `docker compose build`, increase **`MAX_WAIT`** in the workflow env or split caching (future work).

Optional:

| Flag | Meaning |
|------|---------|
| `-SkipBuild` | `docker compose up -d` only (image already built). |
| `-SkipUp` | Assume containers already running; only wait + checks. |
| `-PostClientAssertions contracts` | After Tier A, pipe `sql/contracts_courier_assertions.sql` into MariaDB (informational output). |
| `-PostClientAssertions paper` | Same for `sql/paper_doll_assertions.sql`. |
| `-PostClientAssertions corpmarket` | Same for `sql/corp_market_assertions.sql` (corp `mktOrders`). |
| `-PostClientAssertions all` | Run contracts, paper doll, and corp market SQL files. |

**Tier A steps:**

1. `docker compose build server` (unless `-SkipBuild`).
2. `docker compose up -d` (unless `-SkipUp`).
3. Wait until MariaDB accepts `SELECT 1` as user `evemu` / database `evemu`.
4. Wait until server logs contain **`TCP Server started on port`** (see `eve-server.cpp`).
5. Schema: `ctrContracts` must define **`acceptorCorpID`**, **`issuerWalletKey`**, and **`acceptorWalletKey`** (via `information_schema.columns`).
6. Optional: `Test-NetConnection` to **localhost:26000** (best-effort; not all environments expose the port to the host).

Exit code **0** means Tier A passed. **Post-client SQL does not change the exit code** in the first version; inspect the printed result sets manually.

## Tier B — SQL only (after manual client steps)

1. Run a client scenario (e.g. corp courier accept, or paper-doll save).
2. From repo root:

```powershell
pwsh .\scripts\smoke\docker-smoke.ps1 -SkipBuild -SkipUp -PostClientAssertions all
```

Or run SQL directly:

```powershell
Get-Content .\scripts\smoke\sql\contracts_courier_assertions.sql -Raw |
  docker compose exec -T db mariadb -ueva -pevemu evemu
```

## Tier C — observer / bubble work

Use **two clients**, **Wireshark** on `26000`/`26001`, and server logs. Do **not** try to automate Tier C until you have archived captures; see `EVEMU_RESTORATION_STATE.md` (paper doll section).

## Requirements

- Docker / Docker Compose v2
- PowerShell **7+** (`pwsh`) recommended; Windows PowerShell 5.1 may work if `docker` is on `PATH`.
