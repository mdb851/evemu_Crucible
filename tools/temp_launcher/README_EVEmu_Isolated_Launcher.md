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

1. **blue_patcher** ([README](https://raw.githubusercontent.com/bluepatcher/blue_patcher/master/README.md)): **`common.ini`** in the same **`bin`** folder must have **`cryptoPack=Placebo`** (not `CryptoAPI`). Run **`Launch_EVEmu_Isolated.ps1 -ValidateOnly`** — it reports `common.ini` status.
2. **`start.ini` must replace `server=Tranquility`** with your emulator host; the launcher template now sets **`[main]`** + **`[machoNet]`**. If you already ran an older launcher template, either run **`Restore_Normal_Client.bat`** then launch again, or run **`Launch_EVEmu_Isolated.bat -ForceRefreshIni`** to rewrite **`start.ini`** while keeping the session.
3. Read **`tools\temp_launcher\backup\launcher_last_run.log`** (full file).
4. Confirm **`Start-Process returned PID=...`** — if yes, open **Task Manager** and look for **ExeFile** (process may exit quickly on crash).
5. Start the isolated Docker stack first; confirm **26100/26101** are listening (`Test-NetConnection localhost -Port 26100`).

## Client setup (ExeFile gets a PID but no window)

The launcher only writes **`start.ini`** and starts **`ExeFile.exe`**. If **`common.ini`** or **`blue.dll`** are missing from the same **`bin`**, you do **not** have a complete **blue_patched** Crucible layout — **`ExeFile` will often exit immediately**.

Do this **in order**:

1. **Start clean** — **`Restore_Normal_Client.bat`**, then either **`Launch_EVEmu_Isolated.bat`** or from a terminal in **`tools\temp_launcher`**:  
   `Launch_EVEmu_Isolated.bat -ForceRefreshIni`
2. **Inspect the client `bin`** (the path in **`client_path.local.txt`**) — confirm **`ExeFile.exe`**, **`start.ini`**, **`common.ini`**, and **`blue.dll`** (after [blue_patcher](https://github.com/bluepatcher/blue_patcher)).
3. If **`common.ini`** exists, confirm **`cryptoPack=Placebo`** (not **`CryptoAPI`**).
4. After launch, **Task Manager** — if **`ExeFile.exe`** flashes and exits, treat as startup crash (wrong/incomplete tree, crypto, or MSVC runtime).
5. Open **`start.ini`** in that **`bin`** — expect **`server=127.0.0.1`**, **`port=`** / **`proxyport=`** matching your isolated host ports (default **26100** / **26101**).
6. **Stack up** — `Test-NetConnection 127.0.0.1 -Port 26100` and **26101** should succeed before you rely on login.
7. **`Launch_EVEmu_Isolated.ps1 -ValidateOnly`** — prints **`common.ini`** / **client bin** hints (e.g. missing **`blue.dll`**).

### Example diagnostic (this repo’s typical `client_path`)

On a host where **`client_path.local.txt`** pointed at **`...\eveonline_360229_2of2\bin`**: **`common.ini`** was **absent**, **`blue.dll`** was **absent**, **`ExeFile.exe`** was present, **`start.ini`** was launcher-correct, and **26100/26101** were **open** — i.e. **network OK, client tree incomplete**, not a launcher bug.

## Workarounds (no full reinstall)

### A — You already have a merged tree

If you have a folder like **`EVE_360229_MERGED`** with **`bin\ExeFile.exe`**, **`bin\blue.dll`**, **`common.ini`** one level above **`bin`**, and **`cryptoPack=Placebo`**: put that **`bin`** path in **`client_path.local.txt`**, then **`Restore_Normal_Client.bat`** → **`Launch_EVEmu_Isolated.bat -ForceRefreshIni`**.

### B — Split `1of2` / `2of2` archives only

CCP layout often puts **`common.ini`** in **`...\eveonline_360229_2of2\`** (parent of **`bin`**), not inside **`bin`**, and **`blue.dll`** ships in **`...\eveonline_360229_1of2\bin`**. The launcher now resolves **`common.ini`** in **bin or parent**; **`blue.dll`** must still be next to **`ExeFile.exe`**.

One-click repair (copies **`blue.dll`** from sibling **`..._1of2\bin`**, sets **`cryptoPack=Placebo`**, backs up **`*.bak_evemu`**):

* **`Fix_Split_Crucible_Client.bat`** (or **`Fix_Split_Crucible_Client.ps1`**, optional **`-BinPath '...\2of2\bin'`**, **`-WhatIf`** to preview)

Then **`Restore_Normal_Client.bat`** → **`Launch_EVEmu_Isolated.bat -ForceRefreshIni`**.

Entry points: **`Launch_EVEmu_Isolated.ps1`**, **`Restore_EVEmu_Isolated_Client.ps1`** (same behavior as the `.bat` wrappers).

## One-time setup

1. Copy **`client_path.example.txt`** → **`client_path.local.txt`** (same folder).
2. Edit **`client_path.local.txt`** to **one line** only:
   - **Either** the full path to the folder that contains **`exefile.exe`** (recommended; the EVEmu guide uses **`bin\exefile.exe`**, not `eve.exe`),  
   - **Or** the full path to **`exefile.exe`** itself.

`client_path.local.txt` is **gitignored** — it stays on your machine only.

## What it changes

- In your **client `bin` folder only**: writes **`start.ini`** with **`[main]`** (`server=127.0.0.1`, `port=`), **`[app]`**, **`[localization]`**, and **`[machoNet]`** (`address` / `port` / `proxyport`) — aligned with **blue_patcher** (replace `server=Tranquility`, not only machoNet). File is written as **UTF-8 without BOM** (BOM can break the client INI reader).
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
