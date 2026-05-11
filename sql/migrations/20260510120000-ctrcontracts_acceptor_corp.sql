-- Persist accepting corporation for corp-backed courier collateral (completion-safe routing).
-- +migrate Up
ALTER TABLE ctrContracts
    ADD COLUMN acceptorCorpID int NOT NULL DEFAULT 0 AFTER acceptorWalletKey;

-- +migrate Down
ALTER TABLE ctrContracts
    DROP COLUMN acceptorCorpID;
