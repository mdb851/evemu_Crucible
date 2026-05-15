# Professional broadcast announcer pack

Included with **OOTP 27 Realistic Announcer** (`ootp27-realistic-announcer`). Network-style play-by-play lines for **OOTP 27** voice pack generation: measured openers, situational tension, hits, outs, pitching moves, baserunning, replay, weather, walk-offs, and postseason energy.

## Quick build (dry run, no API)

From the **repository root**:

```bash
python -m ootp_announcer build ^
  --config packs/professional_broadcast/announcer.dry-run.toml ^
  --script packs/professional_broadcast/lines.csv ^
  --out build/voice-pack-professional
```

## Full build with ElevenLabs (realistic audio)

**Fastest “you drive, computer runs” path on Windows:** put your API key in a file named **`.elevenlabs_api_key`** in the repo root (one line, plain text, from Notepad). That filename is **gitignored**. Then run:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\run-elevenlabs-professional-full.ps1
```

The script checks the key, then builds all lines into `build\voice-pack-professional`.

Alternatively set **`ELEVENLABS_API_KEY`** in PowerShell, or set **`ELEVENLABS_API_KEY_FILE`** to the full path of a one-line key file.

The committed **`announcer.elevenlabs.example.toml`** already points at the professional voice id; edit there if you want a different voice or model. Optional tuning:

1. Adjust `elevenlabs_stability`, `elevenlabs_similarity_boost`, and `elevenlabs_style` (0.0–1.0).
2. Keep `audio.extension = "mp3"`. Raise `delay_seconds_after_each_line` only if ElevenLabs rate-limits you; `0.0` is fastest.

**Faster runs:** add `--max-lines 10` to only generate the first 10 rows while you dial in your voice settings, then remove it for the full pack. Example:

```bash
python -m ootp_announcer build ^
  --config announcer.toml ^
  --script packs/professional_broadcast/lines.csv ^
  --out build\voice-pack-sample ^
  --max-lines 10
```

For speed on the full pack, set `elevenlabs_model_id = "eleven_turbo_v2_5"` in your TOML (often faster than `eleven_multilingual_v2`).

```bash
python -m ootp_announcer build ^
  --config announcer.toml ^
  --script packs/professional_broadcast/lines.csv ^
  --out build/voice-pack-professional
```

## OOTP integration

OOTP’s announcer ecosystem is largely **text play-by-play** plus optional **audio** workflows depending on version and mods. Treat this pack as **broadcast-grade source audio** plus `manifest.json` for tooling: align filenames and folders with whatever hook or mod you use to replace in-game cues. Run `python -m ootp_announcer discover` on your game PC to locate install and user data paths.

## Customizing

Edit `lines.csv`: columns `id`, `text`, and optional `category` (and optional `filename`). Keep `id` unique. Shorter lines usually render more cleanly than paragraph-long reads.
