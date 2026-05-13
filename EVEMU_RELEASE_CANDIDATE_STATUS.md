# EVEmu project status — release candidate

**Last updated:** 2026-05-13 (saved from operator notes; branch head refreshed to match `git rev-parse HEAD` at save time.)

## Current state

The project is in **release-candidate state** on branch `restoration/contract-accept-corp`.

* **Frozen code baseline:** `9ddbfac309db942ba8dd493ecb61aa235f0f579c`
* **Current branch head (repo at save):** `93ed5869262fb91be8d3f582e9b6821e235955e4` — includes post-freeze **documentation** and **`tools/temp_launcher`** RC client tooling; **no** further contract/market server logic is required for the personal-path PASS below unless a release-critical defect appears.
* **Isolated runtime:** build PASS, recreate PASS, server reaches **EVEmu Server is Online**

## What is passing

### Personal / non-corp validation

* client launcher to isolated stack: PASS
* personal contracts: PASS
* personal market: PASS

### Infrastructure / code-side baseline

* isolated Docker stack: PASS
* major contract, market, corp-market, and `forCorp` code-side fixes are present on the branch
* dangerous obvious code-side risks were reduced to narrow residual edge cases before freeze

## What is not failed, but still pending proof

These are currently treated as **code-side fixed / live proof pending**:

* contracts
* personal market wallet/journal proof in full detail
* corp market
* corp courier
* inventory/ownership/delivery
* runtime crash safety
* transaction/accounting behavior under full live validation

## What is blocked by setup

These are not marked failed; they are **blocked by current test setup** when no corp / multi-actor validation is available:

* corp market validation
* corp courier validation
* `forCorp` contract validation

## Known feature/design gaps

These are not treated as release-regression bugs right now; they are documented unfinished feature/design areas:

* auction RPCs
* expiry/background contract job
* `GetMyExpiredContractList`
* `CompleteContract` status handling beyond the live-traced cases

## Known legacy-data risk

* pre-SCC `forCorp` courier reward rows may require manual remediation / recreation if encountered later

## Honest summary

For the current environment and available setup, the project is a **successful release candidate**:

* **Personal contracts:** PASS
* **Personal market:** PASS
* **Client launcher / isolated stack:** PASS
* **Corp market:** BLOCKED BY SETUP
* **Corp courier:** BLOCKED BY SETUP
* **Auction / expiry:** KNOWN FEATURE GAP
* **Legacy corp courier reward rows:** KNOWN DATA RISK

## Rule going forward

This branch should remain **frozen** except for a **release-critical defect** found during validation. Otherwise, next work belongs to:

* live validation,
* feature/design backlog,
* or legacy-data remediation.

---

## Executive summary (short)

Release candidate on **`restoration/contract-accept-corp`**; **frozen code** at **`9ddbfac3`**. **Personal** contracts + market + **isolated launcher** validated PASS; **corp** flows and full wallet/journal matrix still **setup-blocked** or **live proof pending**; **auction/expiry** are **known gaps**; **legacy pre-SCC courier reward** rows are a **data risk**. Branch stays **frozen** except **release-critical** fixes.

See also: `EVEMU_RESTORATION_STATE.md`, `EVEmu_RC_VALIDATION_CHECKLIST.md`, `tools/temp_launcher/README_EVEmu_Isolated_Launcher.md`.
