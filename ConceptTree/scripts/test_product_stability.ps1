param(
  [switch]$SkipBuild,
  [switch]$IncludeDbIntegration,
  [switch]$DeepDbIntegration,
  [switch]$IncludeE2E
)

$ErrorActionPreference = "Continue"

$root = Split-Path -Parent $PSScriptRoot
$frontend = Join-Path $root "frontend"
$backend = Join-Path $root "backend"
$reportPath = Join-Path $root "Harness docs\PRODUCT_STABILITY_TEST_REPORT.md"
$results = @()

function Add-SkipResult {
  param([string]$Name, [string]$Coverage, [string]$Output)
  $script:results += [pscustomobject]@{
    Name = $Name
    Status = "SKIP"
    Duration = 0
    Coverage = $Coverage
    Output = $Output
  }
}

function Invoke-StabilityStep {
  param(
    [string]$Name,
    [string]$Workdir,
    [string]$Command,
    [string]$Coverage,
    [int]$Retries = 1
  )

  Write-Host ""
  Write-Host "==> $Name" -ForegroundColor Cyan
  $started = Get-Date
  $allOutput = @()
  $exit = 1

  for ($attempt = 1; $attempt -le $Retries; $attempt++) {
    if ($Retries -gt 1) {
      Write-Host "Attempt $attempt of $Retries" -ForegroundColor DarkCyan
    }
    Push-Location $Workdir
    try {
      $output = & powershell -NoProfile -ExecutionPolicy Bypass -Command $Command 2>&1
      $exit = $LASTEXITCODE
    } catch {
      $output = $_ | Out-String
      $exit = 1
    } finally {
      Pop-Location
    }
    $allOutput += "----- attempt $attempt -----"
    $allOutput += $output
    if ($exit -eq 0 -or $null -eq $exit) {
      break
    }
    if ($attempt -lt $Retries) {
      Start-Sleep -Seconds 3
    }
  }

  $ended = Get-Date
  $duration = [Math]::Round(($ended - $started).TotalSeconds, 2)
  $status = if ($exit -eq 0 -or $null -eq $exit) { "PASS" } else { "FAIL" }

  if ($status -eq "PASS") {
    Write-Host "PASS $Name ($duration s)" -ForegroundColor Green
  } else {
    Write-Host "FAIL $Name ($duration s)" -ForegroundColor Red
    $allOutput | Select-Object -Last 100 | ForEach-Object { Write-Host $_ }
  }

  $script:results += [pscustomobject]@{
    Name = $Name
    Status = $status
    Duration = $duration
    Coverage = $Coverage
    Output = ($allOutput | Out-String).Trim()
  }
}

Invoke-StabilityStep -Name "Frontend critical unit suite" -Workdir $frontend -Command "npm run test:unit -- noteCapture.test.js AppContext.sprint4.test.jsx HomePage.recommendation.test.jsx HomePage.loading.test.jsx aiRequestRegistry.test.js api.sprint3.test.js api.supabase-stability.test.js apiErrorMessages.test.js planReminders.test.js graphUtils.test.js chatPanel.test.js resourceSearch.test.js noteFormatting.test.js" -Coverage "notes save fallback; plan and graph cache; recoverable API errors and degraded sync banner; today recommendation cache; loading view; AI SSE signal; reminders; graph utilities; chat panel; resource search; note formatting"

Invoke-StabilityStep -Name "Backend no-db stability unit suite" -Workdir $backend -Command "python -m pytest tests\unit\test_llm_fast_fail.py tests\unit\test_graph_deadline_validation.py tests\unit\test_notes_node_resolution.py tests\unit\test_idempotency.py tests\unit\test_ai_graph_repair.py tests\test_chat_stream_fallback.py tests\test_sprint4_infra.py -q" -Coverage "LLM fast fail; retry behavior; AI graph repair; node date validation; note node id compatibility; idempotency helpers; chat stream fallback; database timeout and recoverable error handling"

Invoke-StabilityStep -Name "Backend syntax smoke" -Workdir $backend -Command "python -m py_compile config.py database.py main.py routers\ai.py routers\graph.py routers\notes.py routers\plans.py services\ai_service.py services\llm\client.py services\llm\providers\openai_compatible.py utils\observability.py" -Coverage "backend core imports, routers, database, observability and LLM provider syntax"

if (-not $SkipBuild) {
  Invoke-StabilityStep -Name "Frontend production build" -Workdir $frontend -Command "npm run build" -Coverage "production bundle and route/component compile"
}

if ($IncludeDbIntegration) {
  if ($DeepDbIntegration) {
    Invoke-StabilityStep -Name "Backend DB integration suite" -Workdir $backend -Command "python -m pytest tests\test_notes_crud.py tests\test_graph.py tests\test_recommend_next_api.py tests\test_plan_management_api.py -q" -Coverage "deep real database notes CRUD, graph, recommendation and plan API regression" -Retries 2
  } else {
    $dbSmokeTests = @(
      "tests\test_notes_crud.py::test_create_note_idempotency_key_replays_same_response",
      "tests\test_graph.py::test_update_node_status_idempotency_key_prevents_duplicate_sessions",
      "tests\test_recommend_next_api.py::test_recommend_next_falls_back_to_local_rule_when_ai_fails",
      "tests\test_plan_management_api.py::test_update_plan_management_fields"
    ) -join " "
    Invoke-StabilityStep -Name "Backend DB integration smoke" -Workdir $backend -Command "python -m pytest $dbSmokeTests -q" -Coverage "real Supabase smoke: note idempotency, node status idempotency, AI recommendation fallback and plan management update" -Retries 2
  }
} else {
  Add-SkipResult -Name "Backend DB integration smoke" -Coverage "real Supabase smoke: note idempotency, node status idempotency, AI recommendation fallback and plan management update" -Output "Skipped by default. Use -IncludeDbIntegration when Supabase test DB is reachable. Use -DeepDbIntegration for the full slow release regression."
}

if ($IncludeE2E) {
  Invoke-StabilityStep -Name "Playwright main flow" -Workdir $frontend -Command "npm run test:e2e" -Coverage "browser-level main flow with local services and test data"
} else {
  Add-SkipResult -Name "Playwright main flow" -Coverage "browser-level main flow with local services and test data" -Output "Skipped by default. Use -IncludeE2E when local services and test data are ready."
}

$failures = @($results | Where-Object { $_.Status -eq "FAIL" })
$passed = @($results | Where-Object { $_.Status -eq "PASS" })
$skipped = @($results | Where-Object { $_.Status -eq "SKIP" })
$now = Get-Date -Format "yyyy-MM-dd HH:mm:ss zzz"
$overall = if ($failures.Count -eq 0) { "PASS" } else { "FAIL" }

$report = @()
$report += "# Product Stability Test Report"
$report += ""
$report += "- Generated: $now"
$report += "- Workspace: ``$root``"
$report += "- Result: $overall"
$report += "- Passed: $($passed.Count)"
$report += "- Failed: $($failures.Count)"
$report += "- Skipped: $($skipped.Count)"
$report += ""
$report += "## Coverage"
$report += ""
foreach ($item in $results) {
  $report += "- **$($item.Name)** [$($item.Status)] - $($item.Coverage)"
}
$report += ""
$report += "## Detected Errors"
$report += ""
if ($failures.Count -eq 0) {
  $report += "No failures were detected by the default stability suite."
} else {
  foreach ($item in $failures) {
    $report += "### $($item.Name)"
    $report += ""
    $report += '```text'
    $report += (($item.Output -split "`r?`n") | Select-Object -Last 120)
    $report += '```'
  }
}
$report += ""
$report += "## Skipped Items"
$report += ""
foreach ($item in $skipped) {
  $report += "- **$($item.Name)** - $($item.Output)"
}
$report += ""
$report += "## Recommendations"
$report += ""
$report += "- Keep note saving, AI generation and deadline updates isolated: a failed action should not clear page state or crash the app."
$report += "- Keep short timeout, cancellation and bounded retry policies for every remote dependency."
$report += "- Run DB integration checks before release when Supabase pooler is stable."
$report += "- Add browser-level rapid-click, refresh-during-stream and node-switch E2E cases next."
$report += "- Add synthetic monitoring for /api/notes, /api/plans and /api/ai/recommend-next latency and error rate."
$report += ""
$report += "## Commands"
$report += ""
$report += '```powershell'
$report += 'powershell -NoProfile -ExecutionPolicy Bypass -File scripts\test_product_stability.ps1'
$report += 'powershell -NoProfile -ExecutionPolicy Bypass -File scripts\test_product_stability.ps1 -IncludeDbIntegration'
$report += 'powershell -NoProfile -ExecutionPolicy Bypass -File scripts\test_product_stability.ps1 -IncludeDbIntegration -DeepDbIntegration -IncludeE2E'
$report += '```'

$report | Set-Content -Encoding UTF8 -LiteralPath $reportPath

Write-Host ""
Write-Host "Report written to: $reportPath" -ForegroundColor Cyan

if ($failures.Count -gt 0) {
  exit 1
}
exit 0
