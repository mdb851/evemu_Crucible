# Using your voice pack with OOTP 27

OOTP’s built-in **ballpark / event sounds** live under the game **`data/sounds`** tree (and can be overridden or extended under your **user Documents** install). The game plays files whose **names match sound events** (for example `hit_hard`, `cheer_light`, `catch_ball1` …). See the [OOTP Wiki: Sounds](https://wiki.ootpdevelopments.com/index.php?title=OOTP_Baseball%3AImportant_Game_Concepts%2FTools%2C_Functions%2C_and_Editors%2FIn-Game_Editors%2FBallpark_Editor%2FSounds) for the model: multiple numbered variants are chosen at random.

This project’s **`build` output is not those filenames by default** — your CSV uses stable cue ids (`br_homer_no_doubt`, …). The missing link is a **manual mapping** from cue id → OOTP sound basename, then copying or converting into `data/sounds`.

## `export-ootp-sounds`

From the repo root (after `pip install -e .`):

```powershell
python -m ootp_announcer export-ootp-sounds `
  --voice-pack build\voice-pack-professional `
  --map packs\professional_broadcast\ootp_sound_map.example.toml `
  --dest C:\path\to\staging\sounds `
  --dry-run
```

Remove `--dry-run` to write files.

- **`.wav` sources** are copied as-is to `dest\<ootp_filename>.wav`.
- **`.mp3` sources** are converted with **ffmpeg** (must be on `PATH`, or pass `--ffmpeg path\to\ffmpeg.exe`).

**Always back up** the real `data\sounds` folder before overwriting. Prefer exporting to a **staging** folder, inspecting files, then merging into the game or your mod.

## Where to put files

Typical locations (your paths may differ; use **`discover`** from this toolkit on the game PC):

1. **Steam install:**  
   `...\steamapps\common\Out of the Park Baseball 27\data\sounds\`
2. **Per-user data (often safer for mods):**  
   `...\Documents\Out of the Park Developments\OOTP Baseball 27\`  
   (look for a `sounds` or game-data layout your version uses — community packs sometimes mirror `data\sounds` under a mod folder.)

The exact layout can change by edition; confirm with a small test file and in-game sound preferences.

## Mapping file format (`[[map]]`)

```toml
[[map]]
cue_id = "br_homer_no_doubt"
ootp_filename = "hit_hard"

[[map]]
cue_id = "br_strikeout_swing"
ootp_filename = "strikeout"
```

- **`cue_id`** must match the `id` column / manifest `id` field for that line.
- **`ootp_filename`** is the output **basename without extension** (`.wav` is always written).

You can use **`filename`** instead of **`ootp_filename`** if you prefer.

## Limits you should expect

- **Not every CSV line maps to a stock OOTP event.** Many broadcast lines are “flavor” that the stock engine does not trigger as a discrete sound id. Treat mapping as **optional overlays** for events you care about (home run roar, strikeout sting, crowd loop, …).
- **Player names** as intros use **`Player Name.wav`** in the sounds system — a different pipeline (roster-specific files), not this CSV pack’s default ids.
- **Full play-by-play** as continuous narration is **not** what the stock `sounds` folder does; that remains text + TTS in the game. This export is for **stingers and ambient replacements** you explicitly map.

## References

- [OOTP Wiki — Sounds](https://wiki.ootpdevelopments.com/index.php?title=OOTP_Baseball%3AImportant_Game_Concepts%2FTools%2C_Functions%2C_and_Editors%2FIn-Game_Editors%2FBallpark_Editor%2FSounds)
- [OOTP Mods — Sounds (forums)](https://forums.ootpdevelopments.com/forumdisplay.php?f=4011)
