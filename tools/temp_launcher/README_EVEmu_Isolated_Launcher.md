# Temporary EVEmu isolated client launcher (Windows)

Double-click **`Launch_EVEmu_Isolated.bat`** to point your **patched Crucible** client at the **Docker isolated** server on **localhost `26100` (game) / `26101` (proxy)** — same host mapping as `docker-compose.isolated.yml` defaults.

This does **not** start Docker; start the stack from the repo root first:

```text
docker compose -f docker-compose.isolated.yml -p evemu_iso up -d --force-recreate server
```

Confirm logs: **`EVEmu Server is Online`**.

## What to click

| Action | File |
|--------|------|
| Connect client to isolated ports | `tools\temp_launcher\Launch_EVEmu_Isolated.bat` |
| Undo `start.ini` changes | `tools\temp_launcher\Restore_Normal_Client.bat` |

The launch **`.bat` keeps the window open** and prints the last lines of **`backup\launcher_last_run.log`** so a successful run does not look like “nothing happened.”

### If the game still does not appear

1. Read **`tools\temp_launcher\backup\launcher_last_run.log`** (full file).
2. Confirm **`Start-Process returned PID=...`** — if yes, open **Task Manager** and look for **ExeFile** / **exefile** (process may exit quickly on crash).
3. Start the isolated Docker stack first; confirm **26100/26101** are listening (`Test-NetConnection localhost -Port 26100`).
4. Run **`Launch_EVEmu_Isolated.ps1 -ValidateOnly`** from **`tools\temp_launcher`** to verify paths.

PowerShell entry points (same behavior): `Launch_EVEmu_Isolated.ps1`, `Restore_EVEmu_Isolated_Client.ps1`.

## One-time setup

1. Copy **`client_path.example.txt`** → **`client_path.local.txt`** (same folder).
2. Edit **`client_path.local.txt`** to **one line** only:
   - **Either** the full path to the folder that contains **`exefile.exe`** (recommended; the EVEmu guide uses **`bin\exefile.exe`**, not `eve.exe`),  
   - **Or** the full path to **`exefile.exe`** itself.

`client_path.local.txt` is **gitignored** — it stays on your machine only.

## What it changes

- In your **client `bin` folder only**: writes **`start.ini`** with `[machoNet]` pointing at **`127.0.0.1`**, **`port=<game>`**, **`proxyport=<proxy>`** (default **26100** / **26101**).
- In **`tools\temp_launcher\backup\`** (local, gitignored):
  - **`start.ini.original`** — copy of your previous `start.ini` if one existed.
  - **`isolated_launcher_state.json`** — marks an active “session” so relaunch does not re-backup.

It does **not** modify:

- Windows **hosts** file  
- `%LOCALAPPDATA%` / CCP launcher profiles for Tranquility  
- Repo **`config/`** or Docker **default** compose (ports **26000** / **26001**)  
- Any **extract** tree outside this repo  

## How to undo (restore normal client)

1. Close the game client.
2. Double-click **`Restore_Normal_Client.bat`**.

That restores **`start.ini`** from **`start.ini.original`** if the launcher had replaced an existing file, or **deletes** launcher-created **`start.ini`** if there was no original. Then it clears **`backup\isolated_launcher_state.json`**.

If you moved the client install or deleted backups, see **`backup\start.ini.original`** manually.

## Port overrides

Match `docker-compose.isolated.yml` if you use non-default host ports:

```powershell
set EVEMU_ISOLATED_PORT0=26100
set EVEMU_ISOLATED_PORT1=26101
```

Then run the `.bat` from the same console, or set user env vars in Windows.

## Validate paths (no client launch)

From **`tools\temp_launcher`**:

```powershell
pwsh -NoProfile -File .\Launch_EVEmu_Isolated.ps1 -ValidateOnly
pwsh -NoProfile -File .\Restore_EVEmu_Isolated_Client.ps1 -ValidateOnly
```

- With **`client_path.local.txt` missing**: prints launcher root and ports, **exit 0** (preflight OK).
- With **`client_path.local.txt` present** but **`exefile.exe` missing**: **error, exit 1** (fix the path).
- With a **valid client bin path**: prints paths and **exit 0**.

## If login fails

- Confirm isolated containers are up and **26100/26101** are listening.
- Your patched client may expect **extra keys** in `start.ini` (language packs, etc.). Keep a personal backup of the full `start.ini`, run the launcher once, then **merge** your extra sections into the generated file while testing — still restore with **`Restore_Normal_Client.bat`** when done so the **original** returns.
- Last resort (not automated here): **hosts** tricks or a **second copy** of the whole client install with its own `start.ini` are more invasive; prefer a duplicate install folder if you need zero overwrite risk.

## Shortcut (.lnk)

Optional: create a Windows shortcut to **`Launch_EVEmu_Isolated.bat`** in this folder; “Start in” can be left default. The `.bat` sets the working directory automatically.
