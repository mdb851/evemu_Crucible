# OOTP 27 Realistic Announcer

This repository is a clean starter project for replacing OOTP 27's robotic
text-to-speech workflow with a generated, realistic announcer voice pack.

The code is intentionally local-first:

- discovers likely OOTP 27 install/data folders when run on the game PC
- reads announcer copy from CSV
- generates a manifest and one audio file per line
- supports offline neural TTS through [Piper](https://github.com/rhasspy/piper)
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

ootp-announcer discover
ootp-announcer init-config --output announcer.toml
ootp-announcer build --config announcer.toml --script examples/lines.csv --out build/voice-pack
```

The default config uses `dry-run`, which writes text sidecars and a manifest
without requiring a TTS engine.

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
ootp-announcer build --config announcer.toml --script examples/lines.csv --out build/voice-pack
```

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
