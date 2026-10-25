# Scheduled pipeline run for Windows (Task Scheduler). Reads credentials from the environment or .\.env
# (not committed). Exit code != 0 means failure.
$ErrorActionPreference = "Continue"
Set-Location (Join-Path $PSScriptRoot "..")
New-Item -ItemType Directory -Force logs | Out-Null
$log = "logs\pipeline_$(Get-Date -Format yyyyMMdd_HHmmss).log"
Start-Transcript -Path $log -Append | Out-Null

if (Test-Path .env) {
  Get-Content .env | Where-Object { $_ -match '^\s*[A-Za-z_][A-Za-z0-9_]*=' -and $_ -notmatch '^\s*#' } | ForEach-Object {
    $k, $v = $_ -split '=', 2
    [Environment]::SetEnvironmentVariable($k.Trim(), $v.Trim().Trim('"'), "Process")
  }
}
foreach ($n in "GEE_PROJECT", "SUPABASE_URL", "SUPABASE_SERVICE_ROLE_KEY") {
  if (-not [Environment]::GetEnvironmentVariable($n)) { Write-Host "missing $n"; Stop-Transcript | Out-Null; exit 2 }
}
$py = if ($env:PYTHON) { $env:PYTHON } else { "python" }

Write-Host "== tests";   & $py -m pytest scripts/tests -q; if ($LASTEXITCODE -ne 0) { Stop-Transcript | Out-Null; exit 3 }
Write-Host "== update";  & $py scripts/realtime_update.py; $rc = $LASTEXITCODE
Write-Host "== checks";  & $py scripts/check_outputs.py;  if ($LASTEXITCODE -ne 0) { $rc = 4 }
Write-Host "== done rc=$rc"
Stop-Transcript | Out-Null
exit $rc
