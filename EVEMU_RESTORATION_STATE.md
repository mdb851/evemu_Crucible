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

## Tier A CI + compile-first probe log (May 11, 2026)

**Tier A (`docker-smoke` on `restoration/contract-accept-corp`):** **PASS** — GitHub Actions run **`25682646510`** (~**5m42s**), head at **`008d6fee`**.

- **Diagnosis:** `mariadb` CLI parsed **`-ueva`** as user **`eva`** instead of **`-u evemu`** + password; readiness loop never saw a clean DB session.
- **Fix (smallest):** use **`mariadb -u evemu -pevemu evemu`** in Tier A smoke scripts (**`008d6fee`**). Earlier **`4f06d63e`** raised **`MAX_WAIT`** to **600** and added timeout dumps (**`docker compose ps -a`**, **`docker compose logs db --tail 200`**) for classification only.

**Permanent `eve-server-testlib` baseline (when `EVEMU_BUILD_TESTS=ON`):** **`contract/ContractUtils.cpp`**, **`account/AccountDB.cpp`**, **`services/Callable.cpp`**, **`Profiler.cpp`**, **`EVEServerConfig.cpp`**. **`ServerLinkSmokeTest`** in **`src/eve-test`** links **`eve-server-testlib`** with **`--whole-archive`** so a few server TUs resolve without pulling **`libeve-server`**.

**Second compile-first probe (temporary; not in committed tree):** Added **`contract/ContractProxy.cpp`** and **`account/AccountService.cpp`** to **`eve-server-testlib`**, rebuilt **`eve-test`**. **First linker failure cluster** was entirely from **`AccountService.cpp.o`**: missing **`Character::balance`**, **`Character::AlterBalance`**, **`ClientSession::GetCurrentInt`**, **`EntityList::FindClientByCharID`**, **`EntityList::CorpNotify`**, **`EntityList`** ctor/dtor, **`CorporationDB::GetCorpName`**, **`GetDivisionName`**, **`CharacterDB::GetCorpTaxRate`**, **`GetCorpID`**, **`StaticDataMgr::GetCorpName`**, **`StaticDataMgr::~StaticDataMgr`**, and related **`EntityList`** / cold-path dtors. **Probe sources reverted** after capture; **`EVEMU_BUILD_TESTS`** baseline unchanged for merge.

**Third compile-first probe (temporary; not in committed tree):** Added **`contract/ContractProxy.cpp`**, **`account/AccountService.cpp`**, **`character/Character.cpp`**, **`ClientSession.cpp`** on top of the **5-file baseline** (did **not** add **`EntityList.cpp`**, **`CorporationDB.cpp`**, **`CharacterDB.cpp`**, **`StaticDataMgr.cpp`**, **`Client.cpp`**). **`cmake --build build-test --target eve-test`**: **link** failure (compile OK). **First `undefined reference` cluster** was from **`ContractProxy.cpp.o`**: **`ItemFactory::GetItemRef`**, **`ItemFactory::GetStationRef`**, **`ItemFactory::GetSolarSystemRef`**, **`ItemFactory::GetCharacterRef`**, **`ItemFactory::SpawnItem`**, **`ItemFactory::ItemFactory()`**, **`Inventory::GetByID`**, **`Inventory::GetItemsByFlag`**, **`InventoryItem::ChangeOwner`**, **`InventoryItem::Move`**, **`InventoryItem::SetAttribute`**, **`InventoryItem::SaveItem`**, **`ItemData::ItemData(...)`**, **`Client::SendNotifyMsg`**. Later in the same link: large **`Character.cpp.o`** surface (**`CharacterDB`**, **`StaticDataMgr`**, **`EntityList`**, **`Client`**, **`InventoryItem`** vtables, **`ItemDB`**, **`CertificateMgrDB`**, etc.) and a short **`ClientSession.cpp.o`** tail (**`EntityList::RegisterSID`**, **`RemoveSID`**, ctor/dtor). **Probe reverted** after capture; baseline unchanged.

**Fourth compile-first probe (temporary; reverted):** Same as third plus **`inventory/Inventory.cpp`**, **`inventory/InventoryItem.cpp`**, **`inventory/ItemFactory.cpp`**. **Compile OK, link failed.** First **`undefined reference`** cluster: **`ContractProxy.cpp.o`** — mostly **`Client::SendNotifyMsg`**, one **`ItemData::ItemData(...)`**, then **`StaticDataMgr::IsStation`**, **`StaticDataMgr::StaticDataMgr()`**, **`GetStationSystem`**, **`GetStationRegion`**, **`~StaticDataMgr`**, **`AttributeMap::GetAttribute`**. **Reverted** to 5-TU baseline.

**Fifth compile-first probe (temporary; reverted):** Probe four’s seven TU adds plus **`Client.cpp`**, **`StaticDataMgr.cpp`**. **Compile OK, link failed.** First **`undefined reference`** cluster: **`ContractProxy.cpp.o`** — **`ItemData::ItemData(...)`** (`AcceptContract`), **`AttributeMap::GetAttribute`** (`CreateContract`); next in the same link, **`AccountService.cpp.o`** — **`EntityList::CorpNotify`**, **`EntityList`** ctor/dtor, **`CorporationDB::GetCorpName`**, **`GetDivisionName`**, **`EntityList::FindClientByCharID`**, **`CharacterDB::GetCorpTaxRate`**, **`GetCorpID`**. Probe four’s **`Client::SendNotifyMsg`** / **StaticDataMgr** first-wave symbols no longer head this tail. **Reverted** to 5-TU baseline.

**Sixth compile-first probe (temporary; reverted):** Full **probe-five** set plus **`inventory/AttributeMap.cpp`**, **`inventory/ItemType.cpp`**. **Compile OK, link failed.** **`ItemData::ItemData(...)`** / **`AttributeMap::GetAttribute`** no longer appear at the head of the tail — probe six **collapsed** that wall. **First `undefined reference`** cluster (after a **`Client.cpp.o`** relocation warning): **`AccountService.cpp.o`** — **`EntityList::CorpNotify`**, **`EntityList`** ctor/dtor, **`CorporationDB::GetCorpName`**, **`GetDivisionName`**, **`EntityList::FindClientByCharID`**, **`CharacterDB::GetCorpTaxRate`**, **`GetCorpID`**. **Reverted** to 5-TU baseline.

**Seventh compile-first probe (temporary; reverted):** Full **probe-six** set plus **`EntityList.cpp`**. **Compile OK, link failed.** After the same **`Client.cpp.o`** relocation **warning** (not the first hard failure), **first `undefined reference`** cluster: **`AccountService.cpp.o`** — **`CorporationDB::GetCorpName`**, **`GetDivisionName`**, **`CharacterDB::GetCorpTaxRate`**, **`GetCorpID`** — probe seven **removed `EntityList::*` from the head** of the tail vs probe six. **Reverted** to 5-TU baseline.

**Eighth compile-first probe (temporary; reverted):** Full **probe-seven** set plus **`corporation/CorporationDB.cpp`**, **`character/CharacterDB.cpp`**. **Compile OK, link failed.** **`CorporationDB::*`** / **`CharacterDB::*`** from **`AccountService`** no longer head the tail — probe eight **cleared the corp/character DB ring** at the front. **First `undefined reference`** cluster (same **`Client.cpp.o`** **`ShipSE`** relocation **warning** first): **`Character.cpp.o`** — **`Skill::SkillPrereqsComplete`**, **`Skill::VerifyAttribs`**, **`StandingDB::GetStanding`**, **`StandingDB::SetStanding`**, **`StatisticMgr::Add`**, **`StatisticMgr::StatisticMgr()`**, **`Skill::GetSPForLevel`**, **`Skill::GetCurrentSP`**, then **`CertificateMgrDB`**, **`FleetService`**, **`FxDataMgr`**, **`ItemDB`**, etc. **Reverted** to 5-TU baseline.

**Ninth compile-first probe (temporary; reverted):** Full **probe-eight** set plus **`character/Skill.cpp`**. **Compile OK, link failed.** **`Skill::SkillPrereqsComplete`**, **`Skill::VerifyAttribs`**, **`Skill::GetSPForLevel`**, **`Skill::GetCurrentSP`**, etc., no longer head the tail — probe nine **cleared the Skill TU gap** at the front. **First `undefined reference`** cluster (same **`ShipSE`** relocation **warning** first): **`Character.cpp.o`** — **`StandingDB::GetStanding`**, **`StandingDB::SetStanding`**, **`StatisticMgr::Add`**, **`StatisticMgr::StatisticMgr()`**, then **`CertificateMgrDB`**, **`FleetService`**, **`FxDataMgr`**, **`ItemDB`**, … **Reverted** to 5-TU baseline.

**Tenth compile-first probe (temporary; reverted):** Full **probe-nine** set plus **`standing/StandingDB.cpp`**. **Compile OK, link failed.** **`StandingDB::GetStanding`** / **`SetStanding`** no longer head the tail — probe ten **cleared the standing DB slice** at the front. **First `undefined reference`** cluster (same **`ShipSE`** relocation **warning** first): **`Character.cpp.o`** — **`StatisticMgr::Add`**, **`StatisticMgr::StatisticMgr()`** (`PayBounty`), then **`CertificateMgrDB`**, **`FleetService`**, **`ConsoleCommand`**, **`FxDataMgr`**, **`FxProc`**, **`ItemDB`**, … **Reverted** to 5-TU baseline.

**Eleventh compile-first probe (temporary; reverted):** Full **probe-ten** set plus **`StatisticMgr.cpp`** (repo root). **Compile OK, link failed.** **`StatisticMgr::Add`** / **`StatisticMgr::StatisticMgr()`** no longer head the tail — probe eleven **cleared the statistics slice** at the front. **First `undefined reference`** cluster (same **`ShipSE`** relocation **warning** first): **`Character.cpp.o`** — **`CertificateMgrDB::LoadCertificates`**, then **`FleetService::LeaveFleet`**, **`ConsoleCommand::ConsoleCommand()`**, **`FleetService::FleetService()`**, **`CertificateMgrDB::SaveCertificates`**, **`FxDataMgr::*`**, **`FxProc::ParseExpression`** / **`ApplyEffects`**, **`ItemDB::GetItemData`**, … **Reverted** to 5-TU baseline.

**Twelfth compile-first probe (temporary; reverted):** Full **probe-eleven** set plus **`character/CertificateMgrDB.cpp`**. **Compile OK, link failed.** **`CertificateMgrDB::LoadCertificates`** / **`SaveCertificates`** (and related cert symbols) no longer head the tail — probe twelve **cleared the certificate DB slice** at the front. **First `undefined reference`** cluster (same **`ShipSE`** relocation **warning** first): **`Character.cpp.o`** — **`FleetService::LeaveFleet`**, **`ConsoleCommand::ConsoleCommand()`**, **`FleetService::FleetService()`**, then **`FxDataMgr::*`**, **`FxProc::ParseExpression`** / **`ApplyEffects`**, **`ItemDB::GetItemData`**; shortly after, **`EntityList.cpp.o`** pulls **`ServiceDB::SetClientSeed`**, **`SystemManager`**, **`TargetManager`**, **`CivilianMgr`**, **`BubbleManager`**, … **Reverted** to 5-TU baseline.

**Thirteenth compile-first probe (temporary; reverted):** Full **probe-twelve** set plus **`fleet/FleetService.cpp`**. **Compile OK, link failed.** **`FleetService::LeaveFleet`** / **`FleetService::FleetService()`** no longer head the tail — probe thirteen **cleared the fleet TU slice** at the front. **First `undefined reference`** cluster (same **`ShipSE`** relocation **warning** first): **`Character.cpp.o`** — **`ConsoleCommand::ConsoleCommand()`** (`LogOut`), then **`FxDataMgr::*`**, **`FxProc::ParseExpression`** / **`ApplyEffects`**, **`ItemDB::GetItemData`**; **`EntityList.cpp.o`** follow-on (**`ServiceDB`**, **`SystemManager`**, …) remains **behind** that front block. **Reverted** to 5-TU baseline.

**Fourteenth compile-first probe (temporary; reverted):** Full **probe-thirteen** set plus **`ConsoleCommands.cpp`**. **Compile OK, link failed.** **`ConsoleCommand::ConsoleCommand()`** no longer heads the tail — probe fourteen **cleared the console slice** at the front. **First `undefined reference`** cluster (same **`ShipSE`** relocation **warning** first): **`Character.cpp.o`** (in **`Character::ProcessEffects`**) — **`FxDataMgr::GetTypeEffect`**, **`GetExpression`**, **`GetEffect`**, **`FxDataMgr::FxDataMgr()`**, **`FxProc::ParseExpression`**, **`FxProc::ApplyEffects`**, then **`ItemDB::GetItemData`**; **`EntityList.cpp.o`** subsystem pulls remain **downstream**. **Reverted** to 5-TU baseline.

**Fifteenth compile-first probe (temporary; reverted):** Full **probe-fourteen** set plus **`effects/EffectsDataMgr.cpp`**. **Compile OK, link failed.** **`FxDataMgr::*`** symbols no longer head the tail — probe fifteen **cleared the FxDataMgr TU slice** at the front. **First `undefined reference`** cluster (same **`ShipSE`** relocation **warning** first): **`Character.cpp.o`** (in **`Character::ProcessEffects`**) — **`FxProc::ParseExpression`**, **`FxProc::ApplyEffects`**, then **`ItemDB::GetItemData`**; **`EntityList.cpp.o`** pulls remain **downstream**. **Reverted** to 5-TU baseline.

**Sixteenth compile-first probe (temporary; reverted):** Full **probe-fifteen** set plus **`effects/EffectsProcessor.cpp`**. **Compile OK, link failed.** **`FxProc::ParseExpression`** / **`ApplyEffects`** no longer head the tail — probe sixteen **cleared the effects processor TU slice** at the front. **First `undefined reference`** cluster (same **`ShipSE`** relocation **warning** first): **`ItemDB::GetItemData`** from **`Character::Load`**, **`InventoryItem::Load<Character>`**, **`InventoryItem::Load<Skill>`**; **`EntityList.cpp.o`** (**`ServiceDB`**, **`SystemManager`**, …) remains **downstream**. **Reverted** to 5-TU baseline.

**Seventeenth compile-first probe (temporary; reverted):** Full **probe-sixteen** set plus **`inventory/ItemDB.cpp`**. **Compile OK, link failed.** **`ItemDB::GetItemData`** from **`Character::Load`** / **`InventoryItem::Load<Character>`** / **`Load<Skill>`** no longer heads the tail — probe seventeen **cleared the ItemDB slice** at the front. **First `undefined reference`** cluster (same **`ShipSE`** relocation **warning** first): **`EntityList.cpp.o`** — **`ServiceDB::SetClientSeed()`** (**`EntityList::Initialize`**), then **`SystemManager::*`**, **`TargetManager::Process`**, **`CivilianMgr`**, **`BubbleManager`**, **`MissionDataMgr`**, **`MapDB`**, **`MarketMgr`**, **`WormholeMgr`**, **`MarketBotMgr`**, … **Reverted** to 5-TU baseline.

**Eighteenth compile-first probe (temporary; reverted):** Full **probe-seventeen** set plus **`ServiceDB.cpp`** (repo root). **Compile OK, link failed.** **`ServiceDB::SetClientSeed()`** no longer heads the tail — probe eighteen **cleared the small ServiceDB hook** at the front of the **`EntityList`** companion wall. **First `undefined reference`** cluster (same **`ShipSE`** relocation **warning** first): **`EntityList.cpp.o`** — **`SystemManager::UnloadSystem`**, **`SystemManager::~SystemManager()`** (**`EntityList::Close`**), **`TargetManager::Process`**, **`SystemManager::ProcessTic`**, **`CivilianMgr::Process`**, **`BubbleManager::Process`**, then **`MissionDataMgr`**, **`MapDB`**, **`MarketMgr`**, **`WormholeMgr`**, **`MarketBotMgr`**, … **Reverted** to 5-TU baseline.

**Nineteenth compile-first probe (temporary; reverted):** Full **probe-eighteen** set plus **`system/SystemManager.cpp`**. **Compile OK, link failed.** Before the first **`undefined reference`**, **`ld`** emitted a **`SystemManager.cpp.o`** relocation **warning** against **`StructureSE`** (same “not the first hard blocker” class as the recurring **`Client.cpp.o`** / **`ShipSE`** warning). **First `undefined reference`** cluster: **`EntityList.cpp.o`** in **`EntityList::Process()`** — **`TargetManager::Process()`**, **`CivilianMgr::Process()`**, **`BubbleManager::Process()`**, **`MissionDataMgr::Process()`**, **`MapDB::ManipulateTimeData()`**, **`MarketMgr::Process()`**, **`CivilianMgr::CivilianMgr()`**, **`BubbleManager::BubbleManager()`**, **`WormholeMgr::Process()`**, **`MarketBotMgr::Process(bool)`**, **`MissionDataMgr::MissionDataMgr()`**, **`MarketMgr::MarketMgr()`**, **`MarketBotMgr::MarketBotMgr()`**, **`WormholeMgr::WormholeMgr()`**. Probe nineteen **resolved** the prior head’s **`SystemManager::UnloadSystem`**, **`~SystemManager`**, and **`SystemManager::ProcessTic`** pulls from **`EntityList`** (those symbols now live in **`libeve-server-testlib.a`**). **Reverted** to 5-TU baseline.

**Twentieth compile-first probe (temporary; reverted):** Full **probe-nineteen** set plus **`system/TargetManager.cpp`**. **Compile OK, link failed.** Same leading **`SystemManager.cpp.o`** / **`StructureSE`** relocation **warning** (still not the first hard blocker). **First `undefined reference`** cluster: **`EntityList.cpp.o`** in **`EntityList::Process()`** — **`CivilianMgr::Process()`** ( **`TargetManager::Process()`** no longer appears at the head of this block), then **`BubbleManager::Process()`**, **`MissionDataMgr::Process()`**, **`MapDB::ManipulateTimeData()`**, **`MarketMgr::Process()`**, matching **ctors** / **`WormholeMgr`**, **`MarketBotMgr`**, … **Reverted** to 5-TU baseline.

**Twenty-first compile-first probe (temporary; reverted):** Full **probe-twenty** set plus **`system/cosmicMgrs/CivilianMgr.cpp`**. **Compile OK, link failed.** Same leading **`SystemManager.cpp.o`** / **`StructureSE`** relocation **warning**. **`CivilianMgr.cpp.o`** linked with **no** new **`undefined reference`** entries before **`EntityList`**. **First `undefined reference`** cluster: **`EntityList.cpp.o`** in **`EntityList::Process()`** — **`BubbleManager::Process()`** (**`CivilianMgr::Process()`** and **`CivilianMgr::CivilianMgr()`** no longer head this block), then **`MissionDataMgr::Process()`**, **`MapDB::ManipulateTimeData()`**, **`MarketMgr::Process()`**, **`BubbleManager::BubbleManager()`**, **`WormholeMgr`**, **`MarketBotMgr`**, matching **ctors**, … **Reverted** to 5-TU baseline.

**Twenty-second compile-first probe (temporary; reverted):** Full **probe-twenty-one** set plus **`system/BubbleManager.cpp`**. **Compile OK, link failed.** Same leading **`SystemManager.cpp.o`** / **`StructureSE`** relocation **warning**. **First `undefined reference`** cluster (immediately after the link line, same ordering convention as prior probes): **`EntityList.cpp.o`** in **`EntityList::Process()`** — **`MissionDataMgr::Process()`** at the head (**`BubbleManager::Process()`**, **`BubbleManager::BubbleManager()`**, and **`BubbleManager::~BubbleManager()`** no longer appear in this **`EntityList`** block), then **`MapDB::ManipulateTimeData()`**, **`MarketMgr::Process()`**, **`WormholeMgr`**, **`MarketBotMgr`**, matching **ctors**, … **Later in the same `ld` pass** (after other TU blocks in the log): **`BubbleManager.cpp.o`** still pulls a large companion wall — mostly **`SystemBubble::*`**, plus **`MapData::*`**, **`DestinyManager::SetPosition`**, … (expected next widening toward bubble internals / destiny / map data, not the deferred mission/map/market mgr TUs yet). **Reverted** to 5-TU baseline.

**Twenty-third compile-first probe (temporary; reverted):** Full **probe-twenty-two** set plus **`missions/MissionDataMgr.cpp`**. **Compile OK, link failed.** Same leading **`SystemManager.cpp.o`** / **`StructureSE`** relocation **warning**. **First `undefined reference`** cluster: **`EntityList.cpp.o`** in **`EntityList::Process()`** — **`MapDB::ManipulateTimeData()`** at the head (**`MissionDataMgr::Process()`**, **`MissionDataMgr::MissionDataMgr()`**, and **`MissionDataMgr::~MissionDataMgr()`** no longer appear in this **`EntityList`** block), then **`MarketMgr::Process()`**, **`WormholeMgr::Process()`**, **`MarketBotMgr::Process(bool)`**, **`MarketMgr::MarketMgr()`**, **`MarketBotMgr::MarketBotMgr()`**, **`WormholeMgr::WormholeMgr()`**, … **Later in the same `ld` pass** (not the first cluster by ordering rule): **`MissionDataMgr.cpp.o`** pulls **`Agent::*`** and **`MissionDB::*`** — noted for a future slice; **do not** pivot probe twenty-four away from the **`EntityList`**-front chain. **Reverted** to 5-TU baseline.

**Twenty-fourth compile-first probe (temporary; reverted):** Full **probe-twenty-three** set plus **`map/MapDB.cpp`**. **Compile OK, link failed.** Same leading **`SystemManager.cpp.o`** / **`StructureSE`** relocation **warning**. **First `undefined reference`** cluster: **`EntityList.cpp.o`** in **`EntityList::Process()`** — **`MarketMgr::Process()`** at the head (**`MapDB::ManipulateTimeData()`** no longer appears in this **`EntityList`** block), then **`WormholeMgr::Process()`**, **`MarketBotMgr::Process(bool)`**, **`MarketMgr::MarketMgr()`**, **`MarketBotMgr::MarketBotMgr()`**, **`WormholeMgr::WormholeMgr()`**, … **`MapDB.cpp.o`** did not surface its own **`undefined reference`** block before other TU tails in this link log. **Reverted** to 5-TU baseline.

**Twenty-fifth compile-first probe (temporary; reverted):** Full **probe-twenty-four** set plus **`market/MarketMgr.cpp`**. **Compile OK, link failed.** Same leading **`SystemManager.cpp.o`** / **`StructureSE`** relocation **warning**. **First `undefined reference`** cluster: **`EntityList.cpp.o`** in **`EntityList::Process()`** — **`WormholeMgr::Process()`** at the head (**`MarketMgr::Process()`** and **`MarketMgr::MarketMgr()`** no longer appear in this **`EntityList`** block), then **`MarketBotMgr::Process(bool)`**, **`MarketBotMgr::MarketBotMgr()`**, **`WormholeMgr::WormholeMgr()`**, … **Later in the same `ld` pass** (not the first cluster by ordering rule): **`MarketMgr.cpp.o`** pulls a large companion wall (market DB / cache / order execution helpers, etc.) — **do not** pivot probe twenty-six away from the **`EntityList`**-front chain. **Reverted** to 5-TU baseline.

**Twenty-sixth compile-first probe (temporary; reverted):** Full **probe-twenty-five** set plus **`system/cosmicMgrs/WormholeMgr.cpp`**. **Compile OK, link failed.** Same leading **`SystemManager.cpp.o`** / **`StructureSE`** relocation **warning**. **First `undefined reference`** cluster: **`EntityList.cpp.o`** in **`EntityList::Process()`** — **`MarketBotMgr::Process(bool)`** at the head (**`WormholeMgr::Process()`**, **`WormholeMgr::WormholeMgr()`**, and **`WormholeMgr::~WormholeMgr()`** no longer appear in this **`EntityList`** block), then **`MarketBotMgr::MarketBotMgr()`**; the next **`EntityList`** symbols in the same pass are **`StationItem::GetGuestList`**, **`Agent::Agent`**, **`Agent::Load`**, … **Later in the same `ld` pass** (not the first cluster): **`WormholeMgr.cpp.o`** may pull companion symbols — not used to choose probe twenty-seven. **Reverted** to 5-TU baseline.

**Twenty-seventh compile-first probe (temporary; reverted):** Full **probe-twenty-six** set plus **`market/MarketBotMgr.cpp`**. **Compile OK, link failed.** Same leading **`SystemManager.cpp.o`** / **`StructureSE`** relocation **warning**. **`EntityList::Process()`** no longer emits **`undefined reference`** lines in this link — the **EntityList** runtime ring at **`Process()`** is **closed** for this carried set. **First `undefined reference`** cluster: **`EntityList.cpp.o`** in **`EntityList::Multicast`** / **`GetStationGuestList`** — **`StationItem::GetGuestList(...)`** at the head, then **`Agent::Agent(unsigned int)`**, **`Agent::Load()`** in **`EntityList::GetAgent`**. **Reverted** to 5-TU baseline.

**Twenty-eighth compile-first probe (temporary; reverted):** Full **probe-twenty-seven** set plus **`station/Station.cpp`**. **Compile OK, link failed.** Before the first **`undefined reference`**, **`ld`** emitted a **`Station.cpp.o`** relocation **warning** against **`SystemEntity`** (same non-blocker class as other vtable relocations). **`StationItem::GetGuestList`** and **`Multicast`**-path **`EntityList`** guest-list symbols no longer appear — probe twenty-eight **cleared the station guest-list head** from **`EntityList`**. **First `undefined reference`** cluster: **`EntityList.cpp.o`** in **`EntityList::GetAgent`** — **`Agent::Agent(unsigned int)`**, **`Agent::Load()`** at the head; the next block in the same pass is **`Inventory.cpp.o`** (**`InventoryDB::GetItemContents`**, …). **Later in the same `ld` pass** (not the first cluster): **`Station.cpp.o`** pulls **`StationDataMgr`**, **`CelestialObject`**, **`SystemEntity`**, **`SystemDB`**, … — companion wall; next probe still follows the **`EntityList`** front. **Reverted** to 5-TU baseline.

Next compile-first probe (twenty-ninth): keep the **full probe-twenty-eight** TU set; add **`agents/Agent.cpp`** only first — owns **`Agent::Agent`**, **`Agent::Load()`** (first symbol family in the new head cluster).

**Twenty-ninth compile-first probe (temporary; reverted):** Full **probe-twenty-eight** set plus **`agents/Agent.cpp`**. **Compile OK, link failed.** Same leading **`Station.cpp.o`** / **`SystemEntity`** relocation **warning** (non-blocker). **`EntityList::GetAgent`** no longer emits **`Agent::Agent`** / **`Agent::Load`** — probe twenty-nine **cleared the agent head** from **`EntityList`**. **First `undefined reference`** cluster: **`Inventory.cpp.o`** in **`Inventory::GetItems`** — **`InventoryDB::GetItemContents(...)`** at the head, then **`SovereigntyDataMgr::GetSovereigntyData`**, **`SovereigntyDataMgr::SovereigntyDataMgr()`**, more **`InventoryDB::GetItemContents`**, **`StationDB::LoadOffices`**, **`SovereigntyDataMgr::~SovereigntyDataMgr()`**, … **Reverted** to 5-TU baseline.

Next compile-first probe (thirtieth): keep the **full probe-twenty-nine** TU set; add **`inventory/InventoryDB.cpp`** only first — owns **`InventoryDB::GetItemContents`** (first symbol at the new head).

**Thirtieth compile-first probe (temporary; reverted):** Full **probe-twenty-nine** set plus **`inventory/InventoryDB.cpp`**. **Compile OK, link failed.** Same leading **`Station.cpp.o`** / **`SystemEntity`** relocation **warning** (non-blocker). **`InventoryDB::GetItemContents`** / related **`InventoryDB::*`** from **`Inventory::GetItems`** / **`LoadContents`** no longer head the tail — probe thirty **cleared the InventoryDB slice** at the front of **`Inventory.cpp.o`**. **First `undefined reference`** cluster: **`Inventory.cpp.o`** in **`Inventory::ValidateIHubUpgrade`** — **`SovereigntyDataMgr::GetSovereigntyData(unsigned int)`** at the head, then **`SovereigntyDataMgr::SovereigntyDataMgr()`**, then **`StationDB::LoadOffices(...)`** in **`Inventory::LoadContents`**, **`SovereigntyDataMgr::~SovereigntyDataMgr()`**, … **Reverted** to 5-TU baseline.

**Thirty-first compile-first probe (temporary; reverted):** Full **probe-thirty** set plus **`system/sov/SovereigntyDataMgr.cpp`**. **Compile OK, link failed.** Same leading **`Station.cpp.o`** / **`SystemEntity`** relocation **warning** (non-blocker). **`SovereigntyDataMgr::GetSovereigntyData`**, ctor, and dtor no longer appear from **`Inventory.cpp.o`** in the first cluster — probe thirty-one **cleared the sovereignty data head** from **`Inventory`**. **First `undefined reference`** cluster: **`Inventory.cpp.o`** in **`Inventory::LoadContents()`** — **`StationDB::LoadOffices(OwnerData&, …)`** at the head; next block is **`InventoryItem.cpp.o`** (**`CargoContainer::SpawnTemp`**, **`ShipItem::Spawn`**, …). **Later in the same `ld` pass** (not the first cluster): **`SovereigntyDataMgr.cpp.o`** pulls **`SovereigntyDB::*`** — companion wall for a later probe. **Reverted** to 5-TU baseline.

**Thirty-second compile-first probe (temporary; reverted):** Full **probe-thirty-one** set plus **`station/StationDB.cpp`**. **Compile OK, link failed.** Before the first **`undefined reference`**, **`ld`** emitted a **`Station.cpp.o`** relocation **warning** against **`SystemEntity`** (same non-blocker class as prior probes). **`StationDB::LoadOffices`** no longer appears from **`Inventory.cpp.o`** in the first cluster — probe thirty-two **cleared the station DB office-load head** from **`Inventory::LoadContents`**. **First `undefined reference`** cluster: **`InventoryItem.cpp.o`** in **`InventoryItem::SpawnTemp` / `Spawn`** — **`CargoContainer::SpawnTemp(ItemData&)`** at the head, then **`ShipItem::Spawn`**, **`ModuleItem::Spawn`**, **`Blueprint::Spawn`**, **`CargoContainer::Spawn`**, **`StructureItem::Spawn`**, **`ProbeItem::Spawn`**, **`CelestialObject::Spawn`**, **`WreckContainer::Spawn`**, … **Reverted** to 5-TU baseline.

**Thirty-third compile-first probe (temporary; reverted):** Full **probe-thirty-two** set plus **`system/Container.cpp`**. **Compile OK, link failed.** Same leading **`Station.cpp.o`** / **`SystemEntity`** relocation **warning** (non-blocker). **`CargoContainer::SpawnTemp`** no longer appears from **`InventoryItem.cpp.o`** in the first cluster — probe thirty-three **cleared the cargo temp-spawn head** from **`InventoryItem::SpawnTemp`**. **First `undefined reference`** cluster: **`InventoryItem.cpp.o`** in **`InventoryItem::Spawn(ItemData&)`** — **`ShipItem::Spawn(ItemData&)`** at the head, then **`ModuleItem::Spawn`**, **`Blueprint::Spawn`**, **`StructureItem::Spawn`**, **`ProbeItem::Spawn`**, **`CelestialObject::Spawn`**, … **Reverted** to 5-TU baseline.

**Thirty-fourth compile-first probe (temporary; reverted):** Full **probe-thirty-three** set plus **`ship/Ship.cpp`**. **Compile OK, link failed.** Same leading **`Station.cpp.o`** / **`SystemEntity`** relocation **warning** (non-blocker). **`ShipItem::Spawn(ItemData&)`** no longer appears from **`InventoryItem.cpp.o`** in the first cluster — probe thirty-four **cleared the ship spawn head** from **`InventoryItem::Spawn`**. **First `undefined reference`** cluster: **`InventoryItem.cpp.o`** in **`InventoryItem::Spawn(ItemData&)`** — **`ModuleItem::Spawn(ItemData&)`** at the head, then **`Blueprint::Spawn`**, **`StructureItem::Spawn`**, **`ProbeItem::Spawn`**, **`CelestialObject::Spawn`**, … **Reverted** to 5-TU baseline.

**Thirty-fifth compile-first probe (temporary; reverted):** Full **probe-thirty-four** set plus **`ship/modules/ModuleItem.cpp`**. **Compile OK, link failed.** Same leading **`Station.cpp.o`** / **`SystemEntity`** relocation **warning** (non-blocker). **`ModuleItem::Spawn(ItemData&)`** no longer appears from **`InventoryItem.cpp.o`** in the first cluster — probe thirty-five **cleared the module spawn head** from **`InventoryItem::Spawn`**. **First `undefined reference`** cluster: **`InventoryItem.cpp.o`** in **`InventoryItem::Spawn(ItemData&)`** — **`Blueprint::Spawn(ItemData&, EvERam::bpData&)`** at the head, then **`StructureItem::Spawn`**, **`ProbeItem::Spawn`**, **`CelestialObject::Spawn`**, … **Reverted** to 5-TU baseline.

**Thirty-sixth compile-first probe (temporary; reverted):** Full **probe-thirty-five** set plus **`manufacturing/Blueprint.cpp`**. **Compile OK, link failed.** Same leading **`Station.cpp.o`** / **`SystemEntity`** relocation **warning** (non-blocker). **`Blueprint::Spawn(ItemData&, EvERam::bpData&)`** no longer appears from **`InventoryItem.cpp.o`** in the first cluster — probe thirty-six **cleared the blueprint spawn head** from **`InventoryItem::Spawn`**. **First `undefined reference`** cluster: **`InventoryItem.cpp.o`** in **`InventoryItem::Spawn(ItemData&)`** — **`StructureItem::Spawn(ItemData&)`** at the head, then **`ProbeItem::Spawn`**, **`CelestialObject::Spawn`**, … **Reverted** to 5-TU baseline.

**Thirty-seventh compile-first probe (temporary; reverted):** Full **probe-thirty-six** set plus **`pos/Structure.cpp`**. **Compile OK, link failed.** Same leading **`Station.cpp.o`** / **`SystemEntity`** relocation **warning** (non-blocker). **`StructureItem::Spawn(ItemData&)`** no longer appears from **`InventoryItem.cpp.o`** in the first cluster — probe thirty-seven **cleared the structure spawn head** from **`InventoryItem::Spawn`**. **First `undefined reference`** cluster: **`InventoryItem.cpp.o`** in **`InventoryItem::Spawn(ItemData&)`** — **`ProbeItem::Spawn(ItemData&)`** at the head, then **`CelestialObject::Spawn(ItemData&)`**, … **Reverted** to 5-TU baseline.

**Thirty-eighth compile-first probe (temporary; reverted):** Full **probe-thirty-seven** set plus **`exploration/Probes.cpp`**. **Compile OK, link failed.** Same leading **`Station.cpp.o`** / **`SystemEntity`** relocation **warning** (non-blocker). **`ProbeItem::Spawn(ItemData&)`** no longer appears from **`InventoryItem.cpp.o`** in the first cluster — probe thirty-eight **cleared the probe spawn head** from **`InventoryItem::Spawn`**. **First `undefined reference`** cluster: **`InventoryItem.cpp.o`** in **`InventoryItem::Spawn(ItemData&)`** — **`CelestialObject::Spawn(ItemData&)`** at the head, … **Reverted** to 5-TU baseline.

**Thirty-ninth compile-first probe (temporary; reverted):** Full **probe-thirty-eight** set plus **`system/Celestial.cpp`**. **Compile OK, link failed.** Same leading **`Station.cpp.o`** / **`SystemEntity`** relocation **warning** (non-blocker). **`CelestialObject::Spawn(ItemData&)`** no longer appears from **`InventoryItem.cpp.o`** in the first cluster — probe thirty-nine **cleared the celestial spawn head** from **`InventoryItem::Spawn`**. The **`InventoryItem::Spawn`** link slice is **closed** for this carried set. **First `undefined reference`** cluster: **`InventoryItem.cpp.o`** in **`InventoryItem::Rename(...)`** — **`SystemBubble::BubblecastSendNotification(...)`** at the head, then **`SystemDB::GetCelestialObjectData`**, **`ManagerDB::GetAsteroidData`**, **`FactoryDB::GetBlueprintData`**, **`AsteroidItem::AsteroidItem`**, **`StationOffice::StationOffice`**, **`SolarSystem::SolarSystem`**, … **Reverted** to 5-TU baseline.

**Fortieth compile-first probe (temporary; reverted):** Full **probe-thirty-nine** set plus **`system/SystemBubble.cpp`**. **Compile OK, link failed.** Same leading **`Station.cpp.o`** / **`SystemEntity`** relocation **warning** (non-blocker). **`SystemBubble::BubblecastSendNotification`** no longer appears from **`InventoryItem.cpp.o`** in the first cluster — probe forty **cleared the rename/bubblecast head** from **`InventoryItem::Rename`**. **First `undefined reference`** cluster: **`InventoryItem.cpp.o`** in **`CelestialObject::_LoadItem<CelestialObject>`** / **`InventoryItem::_LoadItem<InventoryItem>`** — **`SystemDB::GetCelestialObjectData(unsigned int, CelestialObjectData&)`** at the head, then **`ManagerDB::GetAsteroidData`**, **`FactoryDB::GetBlueprintData`**, **`AsteroidItem::AsteroidItem`**, **`StationOffice::StationOffice`**, **`SolarSystem::SolarSystem`**, … **Reverted** to 5-TU baseline.

**Forty-first compile-first probe (temporary; reverted):** Full **probe-forty** set plus **`system/SystemDB.cpp`**. **Compile OK, link failed.** Same leading **`Station.cpp.o`** / **`SystemEntity`** relocation **warning** (non-blocker). **`SystemDB::GetCelestialObjectData`** no longer appears from **`InventoryItem.cpp.o`** in the first cluster — probe forty-one **cleared the celestial DB load head** from **`CelestialObject::_LoadItem`** / **`InventoryItem::_LoadItem`**. **First `undefined reference`** cluster: **`InventoryItem.cpp.o`** in **`InventoryItem::_LoadItem<InventoryItem>`** — **`ManagerDB::GetAsteroidData(unsigned int, AsteroidData&)`** at the head, then **`FactoryDB::GetBlueprintData`**, **`AsteroidItem::AsteroidItem`**, **`StationOffice::StationOffice`**, **`SolarSystem::SolarSystem`**, … **Reverted** to 5-TU baseline.

**Forty-second compile-first probe (temporary; reverted):** Full **probe-forty-one** set plus **`system/cosmicMgrs/ManagerDB.cpp`**. **Compile OK, link failed.** Same leading **`Station.cpp.o`** / **`SystemEntity`** relocation **warning** (non-blocker). **`ManagerDB::GetAsteroidData`** no longer appears from **`InventoryItem.cpp.o`** in the first cluster — probe forty-two **cleared the manager DB asteroid head** from **`InventoryItem::_LoadItem<InventoryItem>`**. **`ItemFactory::Initialize`** no longer emits **`ManagerDB::DeleteSpawnedRats`** as the first hard symbol in this pass. **First `undefined reference`** cluster: **`InventoryItem.cpp.o`** in **`InventoryItem::_LoadItem<InventoryItem>`** — **`FactoryDB::GetBlueprintData(unsigned int, EvERam::bpData&)`** at the head, then **`AsteroidItem::AsteroidItem`**, **`StationOffice::StationOffice`**, **`SolarSystem::SolarSystem`**, … **Reverted** to 5-TU baseline.

**Forty-third compile-first probe (temporary; reverted):** Full **probe-forty-two** set plus **`manufacturing/FactoryDB.cpp`**. **Compile OK, link failed.** Same leading **`Station.cpp.o`** / **`SystemEntity`** relocation **warning** (non-blocker). **`FactoryDB::GetBlueprintData`** no longer appears from **`InventoryItem.cpp.o`** in the first cluster — probe forty-three **cleared the factory DB blueprint head** from **`InventoryItem::_LoadItem<InventoryItem>`**. **First `undefined reference`** cluster: **`InventoryItem.cpp.o`** in **`InventoryItem::_LoadItem<InventoryItem>`** — **`AsteroidItem::AsteroidItem(...)`** at the head, then **`StationOffice::StationOffice`**, **`SolarSystem::SolarSystem`**, … **Reverted** to 5-TU baseline.

**Forty-fourth compile-first probe (temporary; reverted):** Full **probe-forty-three** set plus **`system/Asteroid.cpp`**. **Compile OK, link failed.** Same leading **`Station.cpp.o`** / **`SystemEntity`** relocation **warning** (non-blocker). **`AsteroidItem::AsteroidItem(...)`** no longer appears from **`InventoryItem.cpp.o`** in the first cluster — probe forty-four **cleared the asteroid item ctor head** from **`InventoryItem::_LoadItem<InventoryItem>`**. **First `undefined reference`** cluster: **`InventoryItem.cpp.o`** in **`InventoryItem::_LoadItem<InventoryItem>`** — **`StationOffice::StationOffice(...)`** at the head, then **`SolarSystem::SolarSystem(...)`**, … **Reverted** to 5-TU baseline.

**Forty-fifth compile-first probe (temporary; reverted):** Full **probe-forty-four** set plus **`station/StationOffice.cpp`**. **Compile OK, link failed.** Same leading **`Station.cpp.o`** / **`SystemEntity`** relocation **warning** (non-blocker). **`StationOffice::StationOffice(...)`** no longer appears from **`InventoryItem.cpp.o`** in the first cluster — probe forty-five **cleared the station office ctor head** from **`InventoryItem::_LoadItem<InventoryItem>`**. **First `undefined reference`** cluster: **`InventoryItem.cpp.o`** in **`InventoryItem::_LoadItem<InventoryItem>`** — **`SolarSystem::SolarSystem(...)`** at the head, then **`SolarSystem::Load`** from **`ItemFactory::GetSolarSystemRef`**, … **Reverted** to 5-TU baseline.

**Forty-sixth compile-first probe (temporary; reverted):** Full **probe-forty-five** set plus **`system/SolarSystem.cpp`**. **Compile OK, link failed.** Same leading **`Station.cpp.o`** / **`SystemEntity`** relocation **warning** (non-blocker). **`SolarSystem::SolarSystem(...)`** and **`SolarSystem::Load`** no longer appear from **`InventoryItem.cpp.o`** / **`ItemFactory.cpp.o`** in the first cluster — probe forty-six **closed the solar-system item load/ctor slice** for this carried set. **First `undefined reference`** cluster: **`Client.cpp.o`** in **`Client::Client`** — **`EVEServiceManager::Lookup(std::string const&)`** at the head, then **`DynamicSystemEntity::~DynamicSystemEntity`**, **`DestinyManager::*`**, **`MapData::*`**, … **Reverted** to 5-TU baseline.

**Forty-seventh compile-first probe (temporary; reverted):** Full **probe-forty-six** set plus **`services/ServiceManager.cpp`**. **Compile OK, link failed.** Same leading **`Station.cpp.o`** / **`SystemEntity`** relocation **warning** (non-blocker). **`EVEServiceManager::Lookup`** no longer appears from **`Client.cpp.o`** in the first cluster — probe forty-seven **cleared the service manager lookup head** from **`Client::Client`**. **First `undefined reference`** cluster: **`Client.cpp.o`** in **`Client::DestroyShipSE`** — **`DynamicSystemEntity::~DynamicSystemEntity()`** at the head, then **`DestinyManager::*`**, **`ModuleManager::CharacterLeavingShip`**, **`MapData::*`**, … **Reverted** to 5-TU baseline.

**Forty-eighth compile-first probe (temporary; reverted):** Full **probe-forty-seven** set plus **`system/SystemEntity.cpp`**. **Compile OK, link failed.** No **`Station.cpp.o`** relocation **warning** before the first **`undefined reference`** in this link log (first hard output is directly from **`Client.cpp.o`**). **`DynamicSystemEntity::~DynamicSystemEntity()`** no longer appears from **`Client.cpp.o`** in the first cluster — probe forty-eight **cleared the dynamic system entity dtor head** from **`Client::DestroyShipSE`**. **First `undefined reference`** cluster: **`Client.cpp.o`** in **`Client::SetCloakTimer`** — **`DestinyManager::UnCloak()`** at the head, then **`DestinyManager::SendJumpInEffect`**, **`SendJumpOutEffect`**, **`ModuleManager::CharacterLeavingShip`**, **`DestinyManager::UpdateNewShip`**, **`SetPosition`**, **`MapData::GetRandPointOnPlanet`**, **`MapData::MapData()`**, … **Reverted** to 5-TU baseline.

Next compile-first probe (forty-ninth): keep the **full probe-forty-eight** TU set; add **`system/DestinyManager.cpp`** only first — defines **`DestinyManager::UnCloak`** and the adjacent **`DestinyManager::*`** symbols at the new head.

**Forty-ninth compile-first probe (temporary; reverted):** Full **probe-forty-eight** set plus **`system/DestinyManager.cpp`**. **Compile OK, link failed.** **`DestinyManager::UnCloak`**, **`SendJumpInEffect`**, **`SendJumpOutEffect`**, **`DestinyManager::UpdateNewShip`**, **`SetPosition`**, and related **`DestinyManager::*`** from **`Client::SetCloakTimer`** / **`SetDestiny`** no longer head the tail — probe forty-nine **cleared the destiny-manager head** from **`Client`**. **First `undefined reference`** cluster: **`Client.cpp.o`** in **`Client::BoardShip`** — **`ModuleManager::CharacterLeavingShip()`** at the head, then **`MapData::GetRandPointOnPlanet`**, **`MapData::MapData()`**, **`LiveUpdateDB::GenerateUpdates`**, **`LSCChannel::*`**, **`TradeService::CancelTrade`**, **`StationDataMgr::*`**, **`Scan::ProcessScan`**, **`ModuleManager::UpdateChargeQty`**, **`LSCService::*`**, **`ImageServer::*`**, … **Reverted** to 5-TU baseline.

Next compile-first probe (fiftieth): keep the **full probe-forty-nine** TU set; add **`ship/modules/ModuleManager.cpp`** only first — owns **`ModuleManager::CharacterLeavingShip`**, **`UpdateChargeQty`**, and the **`ModuleManager::*`** symbols pulled from **`EffectsProcessor`** in the same link pass.

**Autopilot session (May 11–12, 2026):** Ran probes **26–49** in **`evemu_Crucible_github_work`** (Docker image **`evemu_app_build:latest`**: **`cmake -S . -B build-test -DEVEMU_BUILD_TESTS=ON -DCMAKE_BUILD_TYPE=Release`** + **`cmake --build build-test --parallel 4 --target eve-test`**). **`EVEMU_RESTORATION_STATE.md`** updated per probe; **`CMakeLists.txt`** remains the **5-TU** committed testlib after each revert. **`eve-test`** did **not** link successfully — **no `ctest`** run. Full link logs (untracked): **`_probe32_link_full.log`** … **`_probe49_link_full.log`**.

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
