# Smoke Pipeline for Agents

**Quick index:** what automation can and cannot do.

## Tier A — Fully Automatable

CI / agents can run without the game client:

```powershell
pwsh .\scripts\smoke\docker-smoke.ps1
```

```bash
bash scripts/smoke/docker-smoke.sh
```

**What it checks:**
- Docker / compose build and startup
- MariaDB readiness
- Server log boot marker (`TCP Server started on port`)
- Schema columns: `ctrContracts.acceptorCorpID`, `issuerWalletKey`, `acceptorWalletKey`

**Exit code `0` = infrastructure OK.** (Does not exercise gameplay.)

See: `scripts/smoke/README.md`

## Tier B — Evidence Collection (After Manual Client Session)

Agents can collect DB evidence after a human runs a gameplay slice:

```powershell
pwsh .\scripts\live-smoke\run-post-client-evidence.ps1 -Target all
```

Or run individual SQL files:
- `scripts/smoke/sql/contracts_courier_assertions.sql`
- `scripts/smoke/sql/corp_market_assertions.sql`
- `scripts/smoke/sql/paper_doll_assertions.sql`

**What it does:** queries DB for evidence that client operations persisted (contract rows, market orders, character appearance).

**Exit code indicates SQL execution only, not gameplay correctness.**

See: `scripts/smoke/README.md`, `scripts/live-smoke/README.md`

## Tier C — RPC Gameplay (Not Automated Here)

**Cannot** run from CI or SQL alone:

- `CreateContract` / `AcceptContract` / `CompleteContract` (wallet transfers, hangar checks, session guards)
- `PlaceCharOrder` / `ModifyCharOrder` / `CancelCharOrder` with corp flag (ownership routing, collateral ledger)

**Why:** `contractProxy` and `marketProxy` marshal through the game client session and execute C++ logic that SQL cannot invoke.

**Current workaround:** manual client session → collect Tier B evidence.

**Future automation:** in-process tests (wire `eve-test` to eve-server; see `src/eve-test/`), or record/replay after a captured session.

---

## Setup Validation

Verify smoke infrastructure is intact:

```bash
bash scripts/smoke/validate-setup.sh
```

---

## Next Automation Leverage

Real regression coverage for contracts and corp market requires **in-process testing**, not SQL simulation.

See: `src/eve-test/` (currently linked to `eve-core` only). Wiring it to `eve-server` contracts and market logic is the path to repeatable, version-controlled Tier C automation.
