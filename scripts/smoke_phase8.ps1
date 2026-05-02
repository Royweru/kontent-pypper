param(
  [string]$BaseUrl = "http://127.0.0.1:8000"
)

$ErrorActionPreference = "Stop"

function Invoke-HealthCheck {
  param(
    [string]$Name,
    [string]$Path
  )

  $url = "$BaseUrl$Path"
  try {
    $response = Invoke-RestMethod -Uri $url -Method Get -TimeoutSec 20
    Write-Host "[OK] $Name -> $url"
    $response | ConvertTo-Json -Depth 6
    return $true
  }
  catch {
    Write-Host "[FAIL] $Name -> $url :: $($_.Exception.Message)"
    return $false
  }
}

Write-Host "=== Phase 8 Smoke Check ==="
Write-Host "Base URL: $BaseUrl"

$checks = @(
  @{ Name = "App Health"; Path = "/health" },
  @{ Name = "System Readiness"; Path = "/api/v1/system/readiness" },
  @{ Name = "Billing Health"; Path = "/api/v1/billing/health" }
)

$allPassed = $true
foreach ($check in $checks) {
  $ok = Invoke-HealthCheck -Name $check.Name -Path $check.Path
  if (-not $ok) { $allPassed = $false }
}

if (-not $allPassed) {
  Write-Host "FAILED: One or more smoke checks failed."
  exit 1
}

Write-Host "PASSED: Phase 8 smoke checks succeeded."
exit 0
