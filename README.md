# OOTP 27 Realistic Announcer

**OOTP 27 Realistic Announcer** is a small toolkit for **Out of the Park Baseball 27**: turn announcer copy in CSV into a **voice pack** (one audio file per line plus `manifest.json`), with optional harvesting of in-game English text. It replaces the stock robotic TTS workflow for lines you choose to pre-generate.

Installable Python package: **`ootp27-realistic-announcer`** (import and module path remain `ootp_announcer`). If your **Scripts** directory is on `PATH`, you can run the **`ootp27-announcer`** entry point instead of `python -m ootp_announcer`.

The code is intentionally local-first:

- discovers likely OOTP 27 install/data folders when run on the game PC
- reads announcer copy from CSV
- generates a manifest and one audio file per line
- supports offline neural TTS through [Piper](https://github.com/rhasspy/piper)
- supports [ElevenLabs](https://elevenlabs.io) cloud voices (API key via `ELEVENLABS_API_KEY` or config)
- supports any other TTS CLI through a configurable command template
- includes a dry-run backend so the content pipeline can be tested without TTS

> This cloud workspace cannot see your Windows game install. Run the CLI on the
> PC where OOTP 27 is installed, then point the config at the actual game/data
> folder that the `discover` command reports.

## Quick start

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -e .

python -m ootp_announcer discover
python -m ootp_announcer init-config --output announcer.toml
python -m ootp_announcer build --config announcer.toml --script examples/lines.csv --out build/voice-pack
```

On Windows PowerShell, use the same `python -m ootp_announcer ...` commands after `pip install -e .` or `pip install -e ".[dev]"`. If your Python **Scripts** folder is on `PATH`, you can use the **`ootp27-announcer`** command instead.

The default config uses `dry-run`, which writes text sidecars and a manifest
without requiring a TTS engine.

## Professional broadcast pack (included)

The repository includes a **ready-to-build** network-style script with **100+** cues covering opens, situational tension, hits, outs, pitching changes, baserunning, replay, weather, walk-offs, and postseason energy. See [`packs/professional_broadcast/README.md`](packs/professional_broadcast/README.md) for dry-run and ElevenLabs build commands and tuning notes.

## Development

Python **3.11+** is required. Install the package in editable mode with test tools:

```bash
python -m pip install -e ".[dev]"
python -m pytest tests -q
```

On Windows, if `python` is not on your `PATH`, use the install from `%LocalAppData%\Programs\Python\Python312\python.exe` (or run `winget install Python.Python.3.12 -s winget`).

## Use Piper for a realistic offline announcer

1. Install Piper on the game PC.
2. Download a high-quality English voice model.
3. Edit `announcer.toml`:

```toml
[voice]
backend = "piper"
piper_binary = "piper"
piper_model = "C:/voices/en_US-lessac-high.onnx"
```

Then rebuild:

```bash
python -m ootp_announcer build --config announcer.toml --script examples/lines.csv --out build/voice-pack
```

## Use ElevenLabs for studio-quality speech

1. Create an API key in the [ElevenLabs settings](https://elevenlabs.io/app/settings/api-keys).
2. On the machine that runs `python -m ootp_announcer build`, set **`ELEVENLABS_API_KEY`** (recommended). On Windows PowerShell use straight quotes: `$env:ELEVENLABS_API_KEY = 'your-key-here'`. **Check the key first** with `python -m ootp_announcer verify-elevenlabs` (no audio; only validates the key). Alternatively, set `elevenlabs_api_key` in `announcer.toml`; that file is listed in `.gitignore` so it is not committed by default—still avoid sharing the file.
3. Pick a **voice ID** from the ElevenLabs voice library (each voice has an ID in the UI or API).
4. Use **`mp3`** output (the REST API returns MPEG audio for `mp3_*` formats):

```toml
[voice]
backend = "elevenlabs"
elevenlabs_voice_id = "YOUR_VOICE_ID"
elevenlabs_model_id = "eleven_multilingual_v2"
elevenlabs_output_format = "mp3_44100_128"
elevenlabs_stability = 0.5
elevenlabs_similarity_boost = 0.75

[audio]
extension = "mp3"
```

Then run the same `python -m ootp_announcer build` command as in the quick start. Adjust `elevenlabs_stability` / `elevenlabs_similarity_boost` (0.0–1.0) to taste; higher similarity tends to track the original voice more closely. **`elevenlabs_style`** (0.0–1.0) adds expressiveness; **`elevenlabs_use_speaker_boost`** can clarify quieter voices. If the API rejects a setting for your model, set `elevenlabs_style = 0.0` or `elevenlabs_use_speaker_boost = false`. Long lines count against your ElevenLabs quota and per-request limits—split very long stadium rants into separate cues if the API rejects a row.

Use **`[build]` `delay_seconds_after_each_line`** (for example `0.35`) when rendering large packs to reduce rate limiting.

**Windows one-shot:** put your key in a one-line file **`.elevenlabs_api_key`** in the repo root (gitignored), then run `powershell -ExecutionPolicy Bypass -File .\scripts\run-elevenlabs-professional-full.ps1` from the repo root. Or set **`ELEVENLABS_API_KEY_FILE`** to the path of a one-line key file.

## Use another TTS provider

Set `backend = "command"` and provide a command template. The command must
write the audio file to `{output}`. `{text}` contains the line to speak. The
placeholder values are shell-quoted by the builder, so do not add extra quotes
around them in the template.

```toml
[voice]
backend = "command"
command_template = "my-tts-cli --voice stadium --text {text} --output {output}"
```

## CSV script format

`examples/lines.csv` shows the expected columns:

| column | required | description |
| --- | --- | --- |
| `id` | yes | stable cue identifier |
| `text` | yes | words for the announcer to speak |
| `category` | no | grouping such as `intro`, `hit`, `strikeout` |
| `filename` | no | output filename; defaults to a sanitized `id` |

## Harvesting phrases from the game (option 1)

On the PC where **OOTP 27** is installed, you can pull readable sentences out of the shipped **english.xml** (often under `data\text`) or **English.html** into a CSV, then merge the rows you want into your own script before `build`:

```powershell
python -m ootp_announcer harvest-pbp --out build\harvested-pbp-lines.csv
```

That searches every **FOUND** path from `discover` (including extra Steam library disks parsed from `steamapps\libraryfolders.vdf`, shown as `steam-library`). To point at one install explicitly:

```powershell
python -m ootp_announcer discover
python -m ootp_announcer harvest-pbp --ootp-root "C:\Program Files\Out of the Park Developments\OOTP Baseball 27" --out build\harvested-pbp-lines.csv
```

Lines that still contain unresolved `{placeholders}` are dropped; simple `{name}` tokens are stripped so the remainder can be spoken. Tune noise vs. yield with `--min-chars` / `--max-chars` (defaults 24 and 320). Expect to **curate** the CSV: some lines are interface text, not broadcasters.

If `harvest-pbp` reports no `English.html`, the install path is wrong or the game uses a different layout. Try:

- Right-click **OOTP 27** in Steam → **Manage** → **Browse local files**, then pass that folder as `--ootp-root` (Steam’s folder is often `Out of the Park Baseball 27`, not `OOTP Baseball 27`).
- In **PowerShell**, wrap paths in **single quotes** if they contain `(x86)` or spaces so parentheses are not parsed as a subexpression: `'C:\Program Files (x86)\Steam\steamapps\common\Out of the Park Baseball 27'`.
- Re-run with **`--verbose`** to print candidate HTML paths under `--ootp-root`.
- Pass the file explicitly: **`--html-file "C:\full\path\to\English.html"`** (find the file in Explorer search inside the game folder).

## Current integration target

OOTP's built-in announcer uses the game's own TTS/PBP systems. This project
creates high-quality audio assets and a manifest so the next integration step
can be based on the actual OOTP 27 files found on your PC, such as play-by-play,
pronunciation, sound, or mod folders.

## Repository name

If the Git remote still uses an older slug from another tree, consider renaming the GitHub repository to **`ootp27-realistic-announcer`** so it matches the PyPI package name. The clone path is not used by the tools.
