# EVEmu RC validation checklist

Canonical operator worksheet for **release-candidate** validation. Pair with `EVEMU_RESTORATION_STATE.md` (completion matrix, freeze policy).

## Setup

* Start isolated stack:
  * `docker compose -f docker-compose.isolated.yml -p evemu_iso build server`
  * `docker compose -f docker-compose.isolated.yml -p evemu_iso up -d --force-recreate server`
* Confirm server log shows:
  * `EVEmu Server is Online`
* Point client to:
  * **26100 / 26101**

## Record format for every test

* Test:
* PASS / FAIL:
* Expected:
* Actual:
* Wallet before/after:
* Journal lines:
* Server stayed up: yes/no
* Last useful log lines:

---

## 1. Contracts

### Item Exchange

* Open Contracts
* Create item exchange
* Accept
* Complete or cancel
* Verify:
  * no crash
  * item selection works
  * items move correctly
  * ISK moves correctly
  * contract state updates correctly

### Courier

* Create courier
* Accept
* Complete successfully
* Fail delivery
* Delete outstanding
* Verify:
  * no crash
  * collateral/reward behavior correct
  * contract state updates correctly

### forCorp contracts

If setup allows:

* Create `forCorp`
* Delete `forCorp`
* Complete/fail `forCorp` courier
* Verify:
  * corp-owned items appear
  * restore target is correct corp
  * reward/collateral lifecycle is correct

---

## 2. Personal market

### Sell / buy / cancel

* Create sell order
* Create buy order
* Cancel both
* Verify:
  * order appears/disappears correctly
  * wallet/journal behavior is correct

### Modify orders

* Modify buy order up/down
* Modify sell order up/down
* Verify:
  * wallet direction correct
  * journal entries correct
  * no inverted escrow behavior

### Self-buy

* Try to buy your own order
* Verify:
  * blocked cleanly
  * no wallet/journal mutation
  * no tax/fee weirdness

---

## 3. Corp market

If setup allows:

### Corp buy order

* Place corp buy order
* Modify corp buy order
* Cancel corp buy order
* Verify:
  * correct corp division wallet used
  * no personal wallet leakage

### Corp immediate buy

* Buy from sell order using corp
* Verify:
  * corp division debited
  * item lands in correct corp destination

### Corp sell into buy

* Sell using corp into buy order
* Verify:
  * corp division credited
  * correct notification / refresh behavior

### Corp sell cancel

* Cancel corp sell order
* Verify:
  * item returns to corp deliveries, not personal hangar

---

## 4. Corp courier

If setup allows:

* Create `forCorp` courier with reward
* Accept for corp
* Complete successfully
* Fail delivery
* Delete outstanding
* Verify:
  * SCC escrow behavior correct
  * reward refund/payout correct
  * correct corp division used
  * no stuck money/items

---

## 5. Things not to treat as bugs right now

These are documented feature/design gaps:

* auction RPCs
* expiry/background job
* `GetMyExpiredContractList`
* extra `CompleteContract` statuses beyond known handled cases

## 6. Legacy-data warning

If you hit an old `forCorp` courier with reward created before SCC escrow fixes:

* treat it as **legacy-data risk**
* not automatically as a new code regression

## 7. When to send Cursor back in

Only if you find a **release-critical defect**:

* crash
* wrong wallet/division/accountKey
* wrong owner/corp restore
* wrong delivery destination
* self-buy not blocked
* modify accounting still wrong
* reward/collateral lifecycle wrong

## 8. Done-enough criteria

You can call the RC validated enough when:

* contracts pass
* personal market passes
* corp market passes
* corp courier passes
* no release-critical defects remain

---

## Appendix — compact tick list (paste into notes)

Use the **Record format** block per row when something fails.

### Setup

- [ ] Isolated `build server` PASS
- [ ] `up -d --force-recreate server` PASS
- [ ] Log: **EVEmu Server is Online**
- [ ] Client **26100 / 26101**

### 1. Contracts

**Item exchange**

- [ ] Open Contracts — no crash
- [ ] Create item exchange — item selection works
- [ ] Accept — items + ISK correct
- [ ] Complete *or* cancel — state + balances correct

**Courier**

- [ ] Create courier
- [ ] Accept — collateral/reward sane
- [ ] Complete success — payout/refund sane
- [ ] Fail delivery — behavior correct
- [ ] Delete outstanding — refund + state correct

**forCorp** (if setup allows)

- [ ] Create forCorp — corp items visible
- [ ] Delete forCorp — restore to **corp**, not CEO hangar
- [ ] forCorp courier complete/fail — reward/collateral lifecycle correct

### 2. Personal market

- [ ] Sell / buy / cancel — UI + wallet + journal
- [ ] Modify buy up/down — escrow direction correct
- [ ] Modify sell up/down — escrow direction correct
- [ ] Self-buy own order — blocked, no wallet/journal mutation

### 3. Corp market (if setup allows)

- [ ] Corp buy: place / modify / cancel — **corp division** only
- [ ] Corp immediate buy — corp debited, item destination correct
- [ ] Corp sell into buy — corp credited, buyer refresh/notify OK
- [ ] Cancel corp sell — returns to **corp deliveries**, not personal hangar

### 4. Corp courier (if setup allows)

- [ ] forCorp courier + reward — create SCC/debit correct
- [ ] Accept for corp — session + wallet keys sane
- [ ] Complete — SCC payout correct
- [ ] Fail — refunds sane
- [ ] Delete outstanding — no stuck ISK/items

### 5–8. Gates

- [ ] Acknowledged **section 5** non-bugs (auction, expiry, extra CompleteContract statuses)
- [ ] Legacy pre-SCC forCorp courier + reward handled per **section 6** if encountered
- [ ] No **section 7** release-critical defects open
- [ ] **Section 8** done-enough: contracts + personal market + corp market + corp courier all PASS
