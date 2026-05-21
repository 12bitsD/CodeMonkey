param(
  [switch]$SkipBuild,
  [switch]$IncludeDbIntegration
)

$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $PSScriptRoot
$frontend = Join-Path $root "frontend"
$backend = Join-Path $root "backend"

function Step($message) {
  Write-Host ""
  Write-Host "==> $message" -ForegroundColor Cyan
}

Step "Frontend AI request harness tests"
Push-Location $frontend
npm run test:unit -- aiRequestRegistry.test.js api.sprint3.test.js HomePage.recommendation.test.jsx
if (-not $SkipBuild) {
  Step "Frontend build smoke test"
  npm run build
}
Pop-Location

Step "Backend fast-fail and SSE fallback unit tests"
Push-Location $backend
python -m py_compile config.py database.py routers\ai.py routers\graph.py services\llm\client.py services\llm\providers\openai_compatible.py
python -m pytest tests\unit\test_llm_fast_fail.py tests\unit\test_graph_deadline_validation.py tests\test_chat_stream_fallback.py -q

if ($IncludeDbIntegration) {
  Step "Backend DB integration checks"
  python -m pytest tests\test_recommend_next_api.py tests\test_graph.py tests\test_plan_management_api.py -q
} else {
  Write-Host ""
  Write-Host "Skipped DB integration checks. Run with -IncludeDbIntegration when Supabase test DB is reachable." -ForegroundColor Yellow
}
Pop-Location

Step "Static optimization guards"
$guards = @(
  @{ Path = "frontend/src/pages/GraphPage.jsx"; Pattern = "createAiRequestRegistry" },
  @{ Path = "frontend/src/pages/GraphPage.jsx"; Pattern = "explain:" },
  @{ Path = "frontend/src/pages/GraphPage.jsx"; Pattern = "chat:" },
  @{ Path = "backend/routers/ai.py"; Pattern = "recommendation_source" },
  @{ Path = "backend/services/llm/client.py"; Pattern = "_is_non_retryable_provider_error" },
  @{ Path = "backend/database.py"; Pattern = "connect_timeout" },
  @{ Path = "frontend/src/pages/GraphPage.jsx"; Pattern = "nodeDeadlineDraft" },
  @{ Path = "frontend/src/pages/GraphPage.jsx"; Pattern = "minNodeDeadlineDate" },
  @{ Path = "backend/routers/graph.py"; Pattern = "_normalize_node_target_end_date" },
  @{ Path = "frontend/src/pages/HomePage.jsx"; Pattern = "TODAY_RECOMMENDATION_CACHE_KEY" },
  @{ Path = "frontend/src/pages/HomePage.jsx"; Pattern = "readTodayRecommendationCache" },
  @{ Path = "frontend/src/pages/HomePage.jsx"; Pattern = "writeTodayRecommendationCache" }
)

foreach ($guard in $guards) {
  $fullPath = Join-Path $root $guard.Path
  $content = Get-Content -Raw -LiteralPath $fullPath
  if ($content -notmatch [regex]::Escape($guard.Pattern)) {
    throw "Missing optimization guard '$($guard.Pattern)' in $($guard.Path)"
  }
}

Write-Host ""
Write-Host "AI stability checks passed." -ForegroundColor Green
