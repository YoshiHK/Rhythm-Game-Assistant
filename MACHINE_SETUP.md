# MACHINE_SETUP.md

## Purpose
This document is the minimum recovery checklist for moving the UMI / RGA project to a new Windows PC.

It is designed to preserve:
- OneDrive-backed project files
- Python package reproducibility
- local bootstrap reproducibility
- scan / tips_meta workflow readiness

---

## 1. What is expected to roam vs not roam

### Roams with OneDrive (if synced)
- Project files stored under your OneDrive-backed project root
- `Chart File/`
- `Tips Output Meta/`
- source code, schemas, configs, tests

### Does **not** automatically roam
- Windows environment variables
- virtual environments (`.venv/`)
- custom PATH / PYTHONPATH settings
- Python installation itself
- OneDrive per-device sync preferences
- “Always keep on this device” status on a different PC

---

## 2. Prerequisites on a new PC

1. Install OneDrive and sign in with the same Microsoft account.
2. Let the project root sync to the new PC.
3. Install Python (recommended: the same major/minor version used previously).
4. Open PowerShell in the project root.

---

## 3. Required project files for recovery

Keep these in the project root:
- `requirements.txt`
- `.env.example`
- `bootstrap.ps1`
- `MACHINE_SETUP.md`

Recommended additional files:
- `.gitignore`
- `README.md`
- any CI runner or local runner scripts

---

## 4. First-time setup on a new PC

### Step A — Copy environment template

Copy-Item .env.example .env
Edit .env if your local paths differ.

### Step B — Run bootstrap

```
powershell -ExecutionPolicy Bypass -File .\bootstrap.ps1
```

This will:

- load .env
- set process-level PYTHONPATH
- create .venv
- install requirements.txt
- verify key folders
- print sample chart files for local-availability checking

---

## 5. OneDrive expectations for local scanning

For PC-based chart scanning and QA generation:

- the project may live in OneDrive
- but files used by local scan / adapter execution should be available locally on the PC
- a solid green circle with white checkmark in File Explorer is the safest state for strict local execution

If files are cloud-only on the new PC, scanning may discover file paths, but local adapter steps may require file contents to be downloaded first.

---

## 6. Daily workflow reminder

### Activate virtual environment

```
.\.venv\Scripts\Activate.ps1
```

### Optional: verify Python path

```
$env:PYTHONPATH
```

### Run your UMI / RGA workflow
Use your normal local runner commands from the project root.

---

## 7. Recovery after PC failure

If the old PC breaks:

1. Sign in to OneDrive on the new PC.
2. Wait for the project root to sync.
3. Open PowerShell in the project root.
4. Copy .env.example to .env and adjust if needed.
5. Run bootstrap.ps1.
6. Verify chart files that will be scanned are locally available.
7. Run your normal scan / QA workflow.

---

## 8. Non-goals

This setup does **not** attempt to preserve:

- hidden registry state
- machine-specific environment variables automatically
- pre-existing global Python packages
- OneDrive device-specific sync customizations

Those are intentionally rebuilt per machine for predictability.
