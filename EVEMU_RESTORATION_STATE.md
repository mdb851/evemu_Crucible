# EVEmu Crucible Restoration State

## RESTORATION SLICE RESULT (latest)

**Slice:** Courier **`CompleteContract`** — issuer corp wallet + reward accounting + courier authorization

**Status:** PARTIAL — logic corrected in server; **live courier corp issuer / reward debit still needs smoke**

**Evidence:**
- **`CompleteContract`** SELECT now loads **`issuerCorpID`**, **`acceptorID`**, **`issuerWalletKey`** ( **`acceptorWalletKey`** omitted until corp-courier acceptance persists it ).
- **Issuer ISK sink:** reward no longer uses **`AddBalance(reward)`** only (which credited courier without debiting issuer). Reward is **`TransferFunds(issuerWalletID → courier character, issuerMoneyKey → Cash)`**.
- **Delivered goods:** **`ChangeOwner(issuerWalletID)`** with **`issuerWalletID = issuerForCorp ? issuerCorpID : issuerID`** (fixes corp issuer receiving corporation-owned cargo).
- **Fail collateral:** **`TransferFunds(courier → issuerWalletID, …, issuerMoneyKey)`** instead of raw **`issuerID`** only.
- **Authorization:** completion/fail reject when **`acceptorID`** is set and **`call.client`** is not that courier.
- Removed unconditional **`sLog.White`** from **`CompleteContract`** entry.

**Files changed:** `src/eve-server/contract/ContractProxy.cpp`

**Commands run:** `docker compose build server`; `docker compose up -d server`

**Temporary diagnostics removed:** YES (removed noisy White log line)

**Client task required:** YES — complete courier contract with **corp issuer** (`forCorp`, **`issuerCorpID`**) + reward; verify issuer corp wallet debits and courier credits; fail path with collateral.

**Remaining risk:** Courier **`AcceptContract`** still escrows collateral on **character** **`AddBalance`** only — corp courier acceptance + **`acceptorWalletKey`** persistence not implemented; **`issuerWalletKey`** relies on **`ctrContracts`** / **`CreateContract`** population (defaults **0** → division **Cash**).

**Next slice:** Corp-courier **`AcceptContract`** (collateral + **`acceptorWalletKey`**), or backlog PvP / mining.

---

### Suggested Git commit (copy/paste)

**Title:**
```text
restoration: harden corp contract accept path and restore RUN_GDB compose
```

**Body:**
```text
restoration: harden corp contract accept path and restore RUN_GDB compose

- restore docker-compose RUN_WITH_GDB=${RUN_GDB:-FALSE}
- restrict corp request-stack lookup to active corp wallet division
- require matching HangarCanTake role for selected division
- make acceptorForCorp optional PyBool handling null-safe
- use active corp account key for acceptor balance/reward/price flows
- courier CompleteContract: issuer corp wallet, reward TransferFunds, acceptor check
- update restoration state notes for validated fixes and remaining gaps

Known remaining gaps:
- issuer corp wallet division still inferred when issuerWalletKey is 0 on ctrContracts
- corp courier AcceptContract (corp collateral / acceptorWalletKey) still needs a slice
```

*(Amend the body bullet list if this commit only contains the courier slice vs the earlier accept-path/docker edits.)*

---

### Completed slices archive (this sprint)

| Slice | Status |
|-------|--------|
| Insurance purchase (`InsureShip` RPC + tiers) | PASS |
| Insurance payout (code review) | PASS |
| Market sell / modify / cancel (personal) | PASS (matrix — no change this session) |
| Corporation market (`PlaceCharOrder` / modify / cancel corp paths) | PARTIAL (live smoke pending) |
| Contracts `SearchContracts` byname safety | PARTIAL (code; matrix unchanged) |
| External review: corp accept hardening + `RUN_WITH_GDB` | PARTIAL |
| Courier `CompleteContract` corp / reward parity | PARTIAL (this slice) |

---

## Current completion estimate
- Core playable restoration: ~97%
- Full verified restoration matrix: ~94% (insurance slice promoted after live PASS)

## PASS matrix (verified / retained)
- movement / docking / station basics
- inventory / hangar / fitting basics
- chat / local
- combat flow
- NPC spawn / attack / kill
- missions / agents end-to-end
- market browse
- seeded sell visibility
- market buy execution
- bookmarks:
  - station bookmark persistence / visibility / warp-to-bookmark PASS
  - open-space coordinate bookmark persistence / visibility / warp-to-bookmark PASS
- market sell-side personal order management:
  - sell order creation PASS
  - mktOrders insert PASS
  - full-stack item removal PASS
  - full-stack cancel restore PASS
  - partial-stack quantity reduction PASS
  - partial-stack cancel restore as new row PASS
  - active order visibility PASS
  - regional market visibility PASS
  - price modification PASS
  - order cancellation PASS
- **corporation market (code restoration May 2026 — live smoke pending):**
  - `PlaceCharOrder` corp flag enabled (removed blanket deny)
  - corp buy/sell paths reuse existing broker fee + escrow logic
  - `ModifyCharOrder` / `CancelCharOrder` honor `isCorp` + `accountKey` / `ownerID`
  - corp sell requires item `ownerID` == pilot corporation
- **insurance (live PASS — MeganSoft restoration May 2026):**
  - purchase: tier selection (hull-quote + nearest-ratio), wallet debit, `shipInsurance` row
  - **eject** from hull in space (velocity-based gate; Crucible-safe)
  - **self-destruct** completes and destroys hull (`ShipBound::SelfDestruct` RPC accepts Crucible tuple/int/long shapes)
  - payout: `shipInsurance.ownerID` + `payOutAmount`; row deleted after pay
  - **abandoned hull** (pilot ejected): insurance still settles on destruction
  - no spurious payout when uninsured (removed flat 15k placeholder)
- hull transfer consistency:
  - **Board** uses same velocity/warp gate as **Eject** / **SelfDestruct** (replaces bogus `GetSpeed() > 20` checks)

## Current active target
Rotate to **next verification slice** (pick one — still needs live proof before PASS):

| Priority | Slice | Status |
|----------|--------|--------|
| High | PvP aggression → damage → kill → cleanup | UNCHECKED live |
| High | Mining cycle → ore to hold / persistence | UNCHECKED live |
| High | Contracts create → accept → complete → ISK/items | **SearchContracts hardened**; remainder UNCHECKED live |
| Medium | Industry / manufacturing jobs | UNCHECKED live |
| Medium | Exploration / scanning | UNCHECKED live |
| Medium | **Corporation** market | CODE PASS / **live smoke pending** |

No blocker on insurance.

## Recent permanent patches (summary)
- **ContractProxy.cpp:** **AcceptContract** optional **`forCorp`** + **`SearchContracts`** guards + **`PyLong`** contract type; corp accept uses **pilot wallet division hangar + HangarCanTakeN**, **`acceptorMoneyKey`** on ISK legs, safe optional **`PyBool`** handling; **courier `CompleteContract`** issuer corp + **`TransferFunds`** reward + **acceptorID** gate.
- **docker-compose.yml:** **`RUN_WITH_GDB=${RUN_GDB:-FALSE}`** restores GDB toggle via **`RUN_GDB`**.
- **InsuranceService.cpp:** hull-sized premium → platinum coverage; nearest-tier matching for nominal ratios; **`InsureShip`** overloads for **`PyInt`** / **`PyLong`** premium amounts (same logic as **`PyFloat`**).
- **ShipDB / Ship.cpp / Damage.cpp:** insurance settlement from DB `ownerID`; abandoned-hull destruction path pays out.
- **ShipService.cpp:** Eject/Board/SelfDestruct velocity gate; **SelfDestruct** flexible RPC args + fatal kill; Board cyno message corrected.
- **MarketProxyService:** ModifyCharOrder `bid` PyBool (Crucible); corp market unblocked + corp-aware modify/cancel + corp sell ownership gate.

## Insurance test fixture (historical)
- Bantam typeID=582; Caldari Frigate skill gate resolved for boarding.

## Known code gaps (not PASS until tested)
- **ContractProxy.cpp:** item-exchange **acceptance** uses division hangar + wallet keys as above; issuer corp wallet division still assumes **`Cash` (1000)** pending schema; **still UNCHECKED** live for corp issuer ↔ corp acceptor paths.
- **Courier `CompleteContract`:** issuer corp **`issuerWalletID` / `issuerMoneyKey`**, reward **`TransferFunds`**, fail collateral to issuer corp, **acceptorID** gate — **still UNCHECKED** live; corp-courier **accept** (corp collateral / **`acceptorWalletKey`**) still absent.
- **Contracts surface:** `contractProxy` registers **CreateContract**, **AcceptContract**, **CompleteContract**, **SearchContracts**, listings, etc.; schema under `sql/migrations/*contract*.sql`. Treat as **PARTIAL implementation** until a full create→accept→complete live trace is green.
- **Industry:** `RamProxyService` + related RAM pipeline present (`src/eve-server/manufacturing/`); **UNCHECKED** live job completion vs Crucible client expectations.
- Large surface areas above remain **verification-dependent** — no substitute for targeted live tests.

## Automated verification log (agent-run — May 11, 2026)

Executed **without** the Crucible game client (RPC-level contract flows still require client or a dedicated harness):

| Check | Result |
|-------|--------|
| `docker compose build server` | PASS |
| `docker compose config`: default **`RUN_WITH_GDB`** | **`"FALSE"`** |
| Same with **`$env:RUN_GDB='TRUE'`** (PowerShell) then **`docker compose config`** | **`"TRUE"`** |
| **`SHOW COLUMNS FROM ctrContracts`** incl. **`issuerCorpID`**, **`acceptorID`**, **`issuerWalletKey`** | PASS |
| **`CompleteContract` SELECT** (full column list as in server code) vs MariaDB | Executes OK (empty set for nonexistent id) |
| **`ctrContracts` / `ctrItems` row counts** | **0** — no pre-seeded contracts to drive **`CompleteContract`** without inserting a full station/item/courier fixture |
| **`ctest --output-on-failure`** in **`docker build --target app-build`** image | **No tests found** — **`src/eve-test`** is **not** wired into root **`CMakeLists.txt`** `ADD_SUBDIRECTORY`, so **`eve-test`** is not built/installed in default Docker pipeline |
| **`docker logs server`** after startup | Clean init / online |

**Boundary:** **`contractProxy.CompleteContract`** / **`AcceptContract`** semantics (wallet mutations, hangar moves) were **not** executed end-to-end here — that needs either live client testing or adding **`eve-test`** (or similar) to CMake + Docker and scripting DB fixtures.

## Hard project rules
- Restoration first
- No solo customization during restoration
- No invented content
- No custom missions
- No market seeding as gameplay customization during restoration
- No convenience/admin gameplay shortcuts as substitutes for broken features
- Temporary test fixtures allowed only when strictly needed to validate a restoration feature
- Temporary diagnostic logs removed after the issue is resolved

## Rebuild rules
- Rebuild only after a real source/config change
- Use only:
  - `docker compose build server`
  - `docker compose up -d server`
- Do not use prune / no-cache unless evidence proves it necessary

## Git commit & push (mandatory after each proven phase)

Work only inside a normal **`git clone`** of your authoritative fork with **`origin`** already set and **`git`** available on your PATH. Do **not** rely on unpacked ZIP-only trees for pushes (they have no history or remote).

When a restoration slice is **proven** (PASS or validated PARTIAL with evidence recorded above), run from the repo root:

```text
git status
git add EVEMU_RESTORATION_STATE.md
git add path/to/changed/sources...
git commit -m "restoration: <short slice topic>"
git push origin HEAD
```

Conventions:

- One logical slice per commit when practical (easier bisect).
- If Git reports **“Author identity unknown”**, set identity once per clone:  
  `git config user.name "..."` and `git config user.email "..."` (omit **`--global`** to scope this repo only).

The restoration agent completes **commit + push** after each proven phase **when** Git credentials and a configured **`remote`** exist on the machine running the agent. If automation cannot access Git or the remote (missing `.git`, no PATH to Git, or no credentials), finish steps **1–4** locally in your IDE terminal before starting the next slice.

## Deferred post-restoration policy
Solo Crucible Preservation Build is deferred until the restoration matrix is green.

## Next approved step (operations)
1. Choose **one** backlog slice from the table above.
2. Run smallest live scenario; capture client result + DB/logs as appropriate.
3. If failure is reproducible, open a **single-slice** fix request with evidence.
