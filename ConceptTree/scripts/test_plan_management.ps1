$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
$backendPath = Join-Path $repoRoot "backend"
$frontendPath = Join-Path $repoRoot "frontend"

Push-Location $backendPath
try {
  python -m pytest tests/test_plans_crud.py tests/test_plan_management_api.py tests/test_graph.py -q
} finally {
  Pop-Location
}

Push-Location $frontendPath
try {
  npx vitest run src/services/api.plan-management.test.js --pool=threads
  npx vitest run src/utils/planReminders.test.js --pool=threads
  npx vitest run src/pages/HomePage.loading.test.jsx --pool=threads
  npx vitest run src/pages/HomePage.recommendation.test.jsx --pool=threads
  npx vitest run src/pages/HomePage.test.jsx --pool=threads
  npx eslint src/components/loaders/GoalAnalysisLoader.jsx src/components/loaders/GraphGenerationLoader.jsx src/contexts/PlanContext.jsx src/pages/GraphPage.jsx src/pages/HomePage.jsx src/pages/MyLearningPage.jsx src/services/api.js src/types/index.js src/utils/planReminders.js src/utils/planReminders.test.js
} finally {
  Pop-Location
}
