$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $PSScriptRoot
$backendPath = Join-Path $projectRoot "backend"

Write-Host "[DB Security] Running static RLS hardening checks..."
Push-Location $backendPath
python -m pytest tests/test_db_security_rls.py -q
if ($LASTEXITCODE -ne 0) {
  Pop-Location
  exit $LASTEXITCODE
}
Pop-Location

Write-Host "[DB Security] All checks passed."
