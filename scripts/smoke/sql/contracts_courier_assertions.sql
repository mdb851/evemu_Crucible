-- Tier B — post-client / post-fixture assertions for courier contracts + corp columns.
-- Run after a corp-backed courier create → accept (and optionally complete) flow.
-- Empty result sets are normal on a fresh DB with no client test yet.

-- Recent courier contracts (contractType = 3 in this codebase) with corp-routing columns.
SELECT
    contractId,
    contractType,
    status,
    issuerID,
    issuerCorpID,
    forCorp,
    acceptorID,
    acceptorWalletKey,
    acceptorCorpID,
    issuerWalletKey,
    reward,
    collateral,
    dateIssued,
    dateAccepted,
    dateCompleted
FROM ctrContracts
WHERE contractType = 3
ORDER BY contractId DESC
LIMIT 15;

-- Count rows where accept-for-corp persisted a non-zero accepting corporation.
-- After a corp-accept courier test, expect >= 1 when the flow used acceptorCorpID.
SELECT COUNT(*) AS courier_rows_with_acceptor_corp
FROM ctrContracts
WHERE contractType = 3 AND acceptorCorpID <> 0;

-- Issuer wallet key persisted on create (forCorp / corp issuer paths).
SELECT COUNT(*) AS courier_rows_with_issuer_wallet_key
FROM ctrContracts
WHERE contractType = 3 AND issuerWalletKey <> 0;
