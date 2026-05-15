# OOTP 27 Realistic Announcer

This repository is a clean starter project for replacing OOTP 27's robotic
text-to-speech workflow with a generated, realistic announcer voice pack.

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

On Windows PowerShell, use the same `python -m ootp_announcer ...` commands after `pip install`. The shorter `ootp-announcer` command works only if your Python **Scripts** folder is on `PATH`.

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

## Current integration target

OOTP's built-in announcer uses the game's own TTS/PBP systems. This project
creates high-quality audio assets and a manifest so the next integration step
can be based on the actual OOTP 27 files found on your PC, such as play-by-play,
pronunciation, sound, or mod folders.
