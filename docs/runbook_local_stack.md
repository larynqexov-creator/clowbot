# Local ClowBot Stack Runbook (Windows / PowerShell)

Goal: stop/restart the local stack **safely** without hunting processes.

This repo supports two common modes:
1) **Docker Compose** (recommended)
2) **No Docker** (run `uvicorn` + `celery` + local deps)

> Tip: Prefer the scripts in `scripts/stop_stack.ps1` and `scripts/restart_stack.ps1`.

---

## Ports used (default)
- API (uvicorn): `8000`
- MinIO: `9000` (API) + `9001` (console)
- Redis: `6379`
- Qdrant: `6333`

Adjust if you changed `docker-compose.yml` or env.

---

## 1) Docker Compose mode

### Stop
```powershell
# from repo root
pwsh -File .\scripts\stop_stack.ps1 -Mode compose
```

### Restart
```powershell
pwsh -File .\scripts\restart_stack.ps1 -Mode compose
```

### Check
```powershell
docker compose ps
```

---

## 2) No Docker mode

### Find PID by port
```powershell
# 8000 example
Get-NetTCPConnection -LocalPort 8000 -State Listen | Select-Object -First 5

# map port -> process
Get-Process -Id (Get-NetTCPConnection -LocalPort 8000 -State Listen).OwningProcess
```

Alternative (netstat):
```powershell
netstat -ano | findstr ":8000"
# take PID from the last column
Get-Process -Id <PID>
```

### Stop common process types
```powershell
# uvicorn
Get-Process -Name python -ErrorAction SilentlyContinue | Where-Object {
  $_.Path -like "*python*" 
} | Select-Object -First 5

# celery (often python)
# stop by PID once identified
Stop-Process -Id <PID> -Force
```

### Verify everything is stopped
```powershell
# ports not listening
foreach ($p in 8000,9000,9001,6379,6333) {
  $c = Get-NetTCPConnection -LocalPort $p -State Listen -ErrorAction SilentlyContinue
  if ($c) { "PORT $p still LISTENING -> PID $($c.OwningProcess)" } else { "PORT $p free" }
}
```

---

## 3) Using the scripts

### Dry-run (recommended first)
```powershell
pwsh -File .\scripts\stop_stack.ps1 -Mode ports -WhatIf
pwsh -File .\scripts\stop_stack.ps1 -Mode names -WhatIf
```

### Stop by ports
```powershell
pwsh -File .\scripts\stop_stack.ps1 -Mode ports
```

### Stop by process names (best-effort)
```powershell
pwsh -File .\scripts\stop_stack.ps1 -Mode names
```

### Stop Docker Compose
```powershell
pwsh -File .\scripts\stop_stack.ps1 -Mode compose
```
