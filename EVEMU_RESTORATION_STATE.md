# EVEmu Crucible Restoration State

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
| High | Contracts create → accept → complete → ISK/items | UNCHECKED live |
| Medium | Industry / manufacturing jobs | UNCHECKED live |
| Medium | Exploration / scanning | UNCHECKED live |
| Medium | **Corporation** market (personal sell-side already PASS) | UNCHECKED live |

No blocker on insurance.

## Recent permanent patches (summary)
- **ContractProxy.cpp:** **CreateContract** traded-item owner matches **`forCorp`** (character vs corporation); courier **reward escrow** from corp cash via **`HandleCorpTransaction`** when applicable; **`GetItemsInStation`** lists personal hangar by **character owner** or **all corp hangar divisions** when **`forCorp`** is set; **`CompleteContract`** uses **`issuerCorpID`** / **`issuer forCorp`** for delivered-item ownership and failed-contract collateral transfer.
- **ContractProxy.cpp:** **AcceptContract** optional **`forCorp`** (corp hangar divisions); **`issuerCorpID`** / issuer corp wallet for WTB/WTS ISK; requested-stack lookup filters **`contributorOwnerID`** (char vs corp).
- **InsuranceService.cpp:** hull-sized premium → platinum coverage; nearest-tier matching for nominal ratios.
- **ShipDB / Ship.cpp / Damage.cpp:** insurance settlement from DB `ownerID`; abandoned-hull destruction path pays out.
- **ShipService.cpp:** Eject/Board/SelfDestruct velocity gate; **SelfDestruct** flexible RPC args + fatal kill; Board cyno message corrected.
- **MarketProxyService:** ModifyCharOrder `bid` PyBool (Crucible).

## Insurance test fixture (historical)
- Bantam typeID=582; Caldari Frigate skill gate resolved for boarding.

## Known code gaps (not PASS until tested)
- **ContractProxy.cpp:** corp-focused **create / accept / complete / station item list** paths are implemented but **unchecked** live (courier collateral/reward on **complete** still credited to the accepting **character** wallet — corp-accepter courier not modeled in DB).
- Large surface areas above remain **verification-dependent** — no substitute for targeted live tests.

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

## Deferred post-restoration policy
Solo Crucible Preservation Build is deferred until the restoration matrix is green.

## Next approved step (operations)
1. Choose **one** backlog slice from the table above.
2. Run smallest live scenario; capture client result + DB/logs as appropriate.
3. If failure is reproducible, open a **single-slice** fix request with evidence.
