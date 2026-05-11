# EVEmu Crucible Restoration State

## RESTORATION SLICE RESULT (latest)

**Slice:** Courier corp completion — collateral + **reward** to persisted **`acceptorCorpID`** / division; session guard

**Status:** PARTIAL — server wired; **live smoke** (corp issuer debit, corp acceptor collateral + reward credit, fail path, **corp-hop blocked**) batched for end-of-sprint PASS

**Evidence:**
- Migration **`sql/migrations/20260510120000-ctrcontracts_acceptor_corp.sql`** adds **`ctrContracts.acceptorCorpID`** (default **0**).
- **`CreateContract`:** persists **`issuerWalletKey`** (**`GetCorpAccountKey()`** when **`forCorp`**, else **0**) on **`ctrContracts`** insert so issuer division matches listing-time corp wallet.
- **`AcceptContract` (item exchange):** loads **`issuerWalletKey`**; issuer corp reward balance check and **`TransferFunds`** use **`issuerMoneyKey`** derived from row (**`0` → Cash** for legacy rows).
- **`AcceptContract` (courier):** persists **`acceptorCorpID`** next to **`acceptorWalletKey`** when **`acceptorForCorp`**, else **0**.
- **`CompleteContract`:** SELECT loads **`acceptorCorpID`**; corp-collateral ledger legs (**`acceptorWalletKey != 0`**) use **`acceptorCorpID`** from the row (never session corp). **`ValidateCorpCourierAcceptSession`** enforces **`acceptorCorpID != 0`**, **`IsPlayerCorp`**, and **`call.client->GetCorporationID() == acceptorCorpID`** when wallet key is set for corp-backed flow.
- **`ContractUtils`** contract payload SELECT includes **`acceptorCorpID`** for listings/detail parity.
- Courier **reward** on success: **`acceptorCorpID != 0 && acceptorWalletKey != 0`** → **`TransferFunds(issuerWalletID → acceptorCorpID, issuerMoneyKey → persisted division)`**; else personal courier → **`TransferFunds(issuer → courier character, … → Cash)`**.

**Files changed:** `src/eve-server/contract/ContractProxy.cpp`, `src/eve-server/contract/ContractUtils.cpp`, `sql/migrations/20260510120000-ctrcontracts_acceptor_corp.sql` (plus follow-up commits on same branch: corp courier reward credit, **`issuerWalletKey`** create/accept).

**Commands run:** `docker compose build server` (PASS — May 10, 2026; re-run after corp-reward + **`issuerWalletKey`** create/accept edits)

**Temporary diagnostics removed:** N/A (no new noisy logs)

**Client task required:** YES — baseline corp courier smoke **plus** accept-for-corp then change corporation before complete/fail → expect **blocked** with notify (session corp ≠ persisted **`acceptorCorpID`**).

**Remaining risk:** Legacy rows with **`acceptorWalletKey != 0`** and **`acceptorCorpID == 0`** (accepted before migration) are **rejected** at completion with a migration/recreate message; plastic wrap / cargo ownership stays **character** (courier pilot).

**Next slice:** Batched **live smoke** on this branch (contracts). **Optional later code:** courier **`CreateContract`** reward pre-pay for **`forCorp`** issuers (still character-only). **Matrix backlog** (PvP, mining, industry, corp market smoke) — separate restoration slices, not part of this contract branch.

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
| Courier corp collateral + `acceptorWalletKey` + `acceptorCorpID` + `CompleteContract` routing | PARTIAL (this slice) |
| Paper doll: `UpdateExistingCharacter*` DB persistence + `GetPaperDollData` full KeyVal parity | CODE PASS / **live observer refresh unverified** |

---

## Paper doll / character appearance (May 2026)

**Server (branch `restoration/contract-accept-corp`):**

- `paperDollServer.UpdateExistingCharacterFull` / `UpdateExistingCharacterLimited` persist body + portrait after clearing prior rows (`CharacterDB::ClearPaperDollAppearanceData`, `ClearChrPortraitData`; `CharacterAppearance::Build`, `CharacterPortrait::Build`).
- `GetPaperDollData` returns the same **`util.KeyVal`** shape as `GetMyPaperDollData` (`colors`, `modifiers`, `appearance`, `sculpts`) for the requested `characterID`.

**Live verification:** PARTIAL — confirm re-customization writes DB rows and that **your** client refreshes portrait / show-info / full-body fetch as expected.

**Remaining risk (not fixed server-side):** **Already-present observers** may keep stale in-scene meshes until relog or another client-driven refresh. The codebase does not expose an obvious, payload-complete appearance broadcast: `ShipSE::MakeSlimItem` has no paper-doll fields, and blindly adding `SendNotification` names would be speculative.

**Next step if refresh fails in testing:** trace the **Crucible client** by surface (pick one):

1. **Station interior** — other characters’ body meshes.
2. **Space (pod / ship)** — in-bubble entity visuals.
3. **Show-info / portrait only** — profile-style UI (often satisfied by RPC refetch alone).

Document observed RPCs, notifications, and destiny updates during a re-customize; only then mirror the real pattern on the server.

**Client trace procedure (when Crucible + capture are available):**

1. **Baseline:** two clients (A = editor, B = observer), same bubble/station as needed; note ship item IDs / char IDs.
2. **Capture:** log **service calls** (`paperDollServer.*`, `charMgr`, `config`, etc.), **marshaled notifications** (`On*`, channel + id key), and **destiny** traffic (`OnSlimItemChange`, `DoDestinyUpdate`, ball ops) from **save** through a few seconds after A exits the editor.
3. **Order:** start with **show-info / portrait** (smallest traffic cone); only then **station**; only then **space** if you need pod/hull refresh proof.
4. **Success criteria for a server change:** you can name the **exact** tuple/notification/destiny shape the retail client handles after save, and reproduce it from `PaperDollService` or the owning system with the same id keys — not a new guessed name.

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

## Strict sprint checklist (branch `restoration/contract-accept-corp`)

Ordered work — **do not skip ahead** without recording evidence in this file and pushing from a real clone.

1. **Contracts — live smoke (now / top priority).** Run the full **create → accept → complete** batch until PASS or a filed defect: corp issuer debit, corp acceptor collateral, corp reward credit, fail-path routing, **corp-hop blocked** (accept-for-corp then change corporation before complete/fail → blocked with notify). Until that trace is green, the courier/corp slice stays **PARTIAL**, not PASS.
2. **Corporation market — live smoke (next).** Code path is **CODE PASS**; remaining work is **validation only** (`PlaceCharOrder` / modify / cancel corp paths). Promote to PASS only with live evidence.
3. **One new gameplay slice (then).** Pick **one** unchecked matrix row and verify only that slice. After (1) and (2), prefer **PvP** or **mining** (per backlog framing: separate slices, one proven slice at a time). Industry and exploration remain until explicitly chosen.
4. **Smoke tooling — required baseline.** Before each live-smoke session: **Tier A** (`pwsh .\scripts\smoke\docker-smoke.ps1` or `bash scripts/smoke/docker-smoke.sh`, or CI **Docker smoke (Tier A)**). After client steps: **Tier B** SQL under `scripts/smoke/sql/` (contracts, paper doll, **corp `mktOrders`**) or **`pwsh .\scripts\live-smoke\run-post-client-evidence.ps1`**. Read **`scripts/live-smoke/README.md`** for what automation **cannot** substitute (marshaled RPC / session). Tier A/B **do not replace** gameplay testing.
5. **Contract code freeze.** Do **not** add contract implementation unless live smoke proves a **concrete** defect. Courier **`CreateContract`** reward pre-pay for **`forCorp`** issuers remains **optional later code**, not a blocker for closing this branch’s contract slice.
6. **Paper doll.** Treat as **code-complete** for save/load and **`GetPaperDollData`** shape. **Observer refresh** is **investigation-only** (client trace first; reproduce only an observed packet/notification — not a default next implementation sprint).
7. **Exit criterion per slice.** After each **PASS** or validated **PARTIAL** phase: update this file with evidence, **`git commit`**, **`git push`** (`restoration/contract-accept-corp` or successor branch).

**Estimate context:** ~**97%** core playable / ~**94%** fully verified matrix — remaining effort is mostly **proof and protocol discovery**, not missing broad systems.

## Recent permanent patches (summary)
- **ContractProxy.cpp / ContractUtils.cpp / migration `20260510120000`:** **CreateContract** persists **`issuerWalletKey`** for **`forCorp`**; **AcceptContract** optional **`forCorp`** + **`SearchContracts`** guards + **`PyLong`** contract type; corp accept uses **pilot wallet division hangar + HangarCanTakeN**, **`acceptorMoneyKey`** / persisted **`issuerMoneyKey`** on ISK legs; **courier** corp collateral **`corp → corpSCC`** + persisted **`acceptorWalletKey`** / **`acceptorCorpID`**; **courier `CompleteContract`** routes corp collateral + **reward** via persisted corp + division when accept-for-corp; session guard + **acceptorID** gate.
- **docker-compose.yml:** **`RUN_WITH_GDB=${RUN_GDB:-FALSE}`** restores GDB toggle via **`RUN_GDB`**.
- **InsuranceService.cpp:** hull-sized premium → platinum coverage; nearest-tier matching for nominal ratios; **`InsureShip`** overloads for **`PyInt`** / **`PyLong`** premium amounts (same logic as **`PyFloat`**).
- **ShipDB / Ship.cpp / Damage.cpp:** insurance settlement from DB `ownerID`; abandoned-hull destruction path pays out.
- **ShipService.cpp:** Eject/Board/SelfDestruct velocity gate; **SelfDestruct** flexible RPC args + fatal kill; Board cyno message corrected.
- **MarketProxyService:** ModifyCharOrder `bid` PyBool (Crucible); corp market unblocked + corp-aware modify/cancel + corp sell ownership gate.
- **PaperDollService.cpp / CharacterDB:** appearance re-customize persists to `avatars` / `avatar_*` / `chrPortraitData`; `GetPaperDollData` returns full paper-doll KeyVal (commits through `41183ce4` on `restoration/contract-accept-corp`).
- **`scripts/smoke/`:** Tier A **`docker-smoke.ps1`** / **`docker-smoke.sh`** (compose build/up, DB ready, server log line, `ctrContracts` column smoke) + Tier B SQL templates for courier + paper doll; see **`scripts/smoke/README.md`**. CI: **`.github/workflows/docker-smoke.yml`** (Tier A on `master` / `staging` / `restoration/**`).

## Insurance test fixture (historical)
- Bantam typeID=582; Caldari Frigate skill gate resolved for boarding.

## Known code gaps (not PASS until tested)
- **ContractProxy.cpp:** item-exchange **acceptance** uses division hangar + wallet keys; **`issuerWalletKey`** now persisted on create and honored on accept (**legacy `0` → Cash**). **Courier `CreateContract`** reward pre-pay still debits **character** only (corp-issuer courier create + escrow parity not done). **still UNCHECKED** live for full corp issuer ↔ corp acceptor matrix.
- **Courier (corp accept):** **`acceptorCorpID`** + **`acceptorWalletKey`** persisted; **`CompleteContract`** uses row corp id for SCC/corp collateral + **issuer → persisted corp division** reward when accept-for-corp; corp-hop blocked — **still UNCHECKED** live; personal courier reward still **character Cash**.
- **Contracts surface:** `contractProxy` registers **CreateContract**, **AcceptContract**, **CompleteContract**, **SearchContracts**, listings, etc.; schema under `sql/migrations/*contract*.sql`. Treat as **PARTIAL implementation** until a full create→accept→complete live trace is green.
- **Industry:** `RamProxyService` + related RAM pipeline present (`src/eve-server/manufacturing/`); **UNCHECKED** live job completion vs Crucible client expectations.
- Large surface areas above remain **verification-dependent** — no substitute for targeted live tests.

## Automated verification log (agent-run — May 10, 2026)

Executed **without** the Crucible game client (RPC-level contract flows still require client or a dedicated harness):

| Check | Result |
|-------|--------|
| `docker compose build server` | PASS |
| **`pwsh .\scripts\smoke\docker-smoke.ps1 -SkipBuild -SkipUp`** (after stack already up) | Tier A baseline — run locally when Docker available |
| **`bash scripts/smoke/docker-smoke.sh`** (or **`.github/workflows/docker-smoke.yml`** on `restoration/**` / `master` / `staging`) | Same Tier A checks on Linux / CI |
| `docker compose config`: default **`RUN_WITH_GDB`** | **`"FALSE"`** |
| Same with **`$env:RUN_GDB='TRUE'`** (PowerShell) then **`docker compose config`** | **`"TRUE"`** |
| **`SHOW COLUMNS FROM ctrContracts`** incl. **`issuerCorpID`**, **`acceptorID`**, **`issuerWalletKey`**, **`acceptorCorpID`** (after **`20260510120000`** migrate) | PASS once migrated |
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
