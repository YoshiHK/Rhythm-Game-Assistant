## MACHINE_SETUP.md

### Purpose

This document is the minimum recovery checklist for moving the UMI / RGA project to a new Windows PC.

It is designed to preserve:

- OneDrive-backed project files
- Python package reproducibility
- local bootstrap reproducibility
- scan / tips_meta workflow readiness
- FastAPI backend startup consistency
- ngrok tunnel recovery
- Softr → ngrok → FastAPI connectivity

---

## 1. What is expected to roam vs not roam

### Roams with OneDrive (if synced)

- Project files stored under the OneDrive-backed project root
- Chart File/
- Tips Output Meta/
- source code, schemas, configs, tests
- bootstrap.ps1
- backend_start.ps1
- ngrok_start.ps1
- MACHINE_SETUP.md

### Does **not** automatically roam

- Windows environment variables
- virtual environments (.venv/)
- custom PATH / PYTHONPATH settings
- Python installation itself
- OneDrive per-device sync preferences
- "Always keep on this device" status on a different PC
- ngrok local authentication state

---

## 2. Prerequisites on a new PC

- Install OneDrive and sign in with the same Microsoft account.
- Let the project root sync to the new PC.
- Install Python (recommended: same major/minor version).
- Install Git.
- Install ngrok.
- Open PowerShell in the project root.

---

## 3. Required project files for recovery

Keep these in the project root:

- requirements.txt
- .env.example
- bootstrap.ps1
- backend_start.ps1
- ngrok_start.ps1
- MACHINE_SETUP.md

Recommended additional files:

- .gitignore
- .gitattributes
- README.md
- CI scripts
- local runner scripts

---

## 4. Environment Variables

### Required

RGA API authentication depends on:

```text
SOFTR_API_TOKEN
```

Example:

```powershell
[Environment]::SetEnvironmentVariable(
    "SOFTR_API_TOKEN",
    "your_token_here",
    "User"
)
```

Verify:

```powershell
echo $env:SOFTR_API_TOKEN
```

---

## 5. First-time setup on a new PC

### Step A — Copy environment template

```powershell
Copy-Item .env.example .env
```

### Step B — Run bootstrap

```powershell
powershell -ExecutionPolicy Bypass -File .\bootstrap.ps1
```

---

## 6. ngrok Authentication Recovery

```powershell
ngrok config add-authtoken YOUR_AUTHTOKEN
```

---

## 7. OneDrive Expectations for Local Scanning

- adapter execution should have local file availability
- cloud-only files may require download before execution

---

## 8. Daily Workflow

### Backend

```powershell
.\backend_start.ps1
```

### ngrok

```powershell
.\ngrok_start.ps1
```

---

## 9. Recovery After PC Failure

1. Sign in to OneDrive.
2. Install Python.
3. Install ngrok.
4. Run bootstrap.ps1.
5. Restore SOFTR_API_TOKEN.
6. Run backend_start.ps1.
7. Run ngrok_start.ps1.
8. Verify Softr API returns HTTP 200.

---

## 10. Non-goals

- hidden registry state
- global Python packages
- machine-specific PATH configuration
- machine-specific environment variables automatically
- ngrok local authentication cache automatically
