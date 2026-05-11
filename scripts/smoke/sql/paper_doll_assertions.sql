-- Tier B — post-client assertions for paper-doll persistence tables.
-- Run after appearance re-customization (or character creation with doll).
-- On an empty shard, counts are often zero until a character is created/customized.

SELECT COUNT(*) AS avatar_rows FROM avatars;
SELECT COUNT(*) AS avatar_color_rows FROM avatar_colors;
SELECT COUNT(*) AS avatar_modifier_rows FROM avatar_modifiers;
SELECT COUNT(*) AS avatar_sculpt_rows FROM avatar_sculpts;
SELECT COUNT(*) AS chr_portrait_data_rows FROM chrPortraitData;

-- Per-character spot-check: replace @char_id after your test (example: 1).
-- SET @char_id = 90000001;
-- SELECT charID, hairDarkness FROM avatars WHERE charID = @char_id;
-- SELECT COUNT(*) AS colors_for_char FROM avatar_colors WHERE charID = @char_id;
