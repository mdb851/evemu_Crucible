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
ootp-announcer inspect --ootp-root "C:/Path/To/OOTP Baseball 27" --out ootp-inspection.md
ootp-announcer doctor --config announcer.toml --script examples/lines.csv --out build/voice-pack
ootp-announcer prepare-script --script examples/lines.csv --pronunciations examples/pronunciations.csv --out build/lines-tts.csv --report build/pronunciation-report.md
ootp-announcer build --config announcer.toml --script examples/lines.csv --out build/voice-pack
ootp-announcer package --voice-pack build/voice-pack --out build/voice-pack.zip
```

The default config uses `dry-run`, which writes text sidecars and a manifest
without requiring a TTS engine.

## Inspect the local OOTP install

Before editing game files, run an inspection report against the OOTP install or
user data folder that exists on the game PC:

```bash
ootp-announcer discover
ootp-announcer inspect --ootp-root "C:/Program Files/Out of the Park Developments/OOTP Baseball 27" --out ootp-inspection.md --json-out ootp-inspection.json
```

The report highlights likely configuration, pronunciation, play-by-play, audio,
and mod folders. Use it as the source of truth for the next integration step.
Always back up OOTP files before replacing or editing them.

## Validate before building

Run `doctor` whenever you change the config, script, voice engine, or output
folder:

```bash
ootp-announcer doctor --config announcer.toml --script examples/lines.csv --out build/voice-pack
```

The doctor command checks that the config loads, the script is valid, the output
parent exists, and the configured TTS backend has the required pieces. It returns
a non-zero exit code when a blocking error is found.

## Control pronunciation

Use a pronunciation lexicon to make neural TTS read acronyms, names, and baseball
phrases naturally:

```bash
ootp-announcer prepare-script \
  --script examples/lines.csv \
  --pronunciations examples/pronunciations.csv \
  --out build/lines-tts.csv \
  --report build/pronunciation-report.md
```

The prepared script keeps the original text in an `original_text` column while
placing the TTS-friendly version in `text`. You can also apply the lexicon at
build time:

```bash
ootp-announcer build \
  --config announcer.toml \
  --script examples/lines.csv \
  --pronunciations examples/pronunciations.csv \
  --out build/voice-pack
```

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
ootp-announcer package --voice-pack build/voice-pack --out build/voice-pack.zip
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

Generated voice packs include `INSTALL.md` with a local checklist. The tool does
not overwrite game files automatically because the exact OOTP 27 integration
point should be confirmed from the inspection report on your machine.

## Copy a voice pack to a local target

The install command is dry-run by default:

```bash
ootp-announcer install --voice-pack build/voice-pack --target "C:/Path/Confirmed/From/Inspection"
```

After reviewing the planned copies, add `--apply` to perform the install:

```bash
ootp-announcer install --voice-pack build/voice-pack --target "C:/Path/Confirmed/From/Inspection" --apply
```

Existing target files are copied into `_backup/` before they are replaced, and
an `ootp-announcer-install.json` manifest is written to the target.
