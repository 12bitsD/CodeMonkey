$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $PSScriptRoot
$backendPath = Join-Path $projectRoot "backend"
$frontendPath = Join-Path $projectRoot "frontend"

Write-Host "[Sprint 4] Running backend infrastructure tests..."
Push-Location $backendPath
python -m pytest tests/test_sprint4_infra.py -q
Pop-Location

Write-Host "[Sprint 4] Running frontend context split tests..."
Push-Location $frontendPath
npx vitest run src/contexts/AppContext.sprint4.test.jsx --pool=threads
npx vitest run src/pages/HomePage.test.jsx --pool=threads
npx eslint src/contexts/AppContext.jsx src/contexts/PlanContext.jsx src/contexts/NoteContext.jsx src/contexts/GraphContext.jsx src/pages/HomePage.jsx src/pages/MyLearningPage.jsx src/pages/GraphPage.jsx src/pages/HomePage.test.jsx src/contexts/AppContext.sprint4.test.jsx
Pop-Location

Write-Host "[Sprint 4] All targeted checks passed."
