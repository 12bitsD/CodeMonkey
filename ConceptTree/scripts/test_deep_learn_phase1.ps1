param(
  [string]$BaseUrl = "http://localhost:8000",
  [string]$Token = $env:TEST_JWT_TOKEN,
  [string]$NodeId = $env:TEST_NODE_ID,
  [string]$PlanId = $env:TEST_PLAN_ID
)

$ErrorActionPreference = "Continue"
$root = Split-Path -Parent $PSScriptRoot
$backend = Join-Path $root "backend"
$results = @()
$passed = 0
$failed = 0

function Write-Step { param([string]$msg) Write-Host "`n==> $msg" -ForegroundColor Cyan }
function Write-Pass { param([string]$msg) Write-Host "  PASS $msg" -ForegroundColor Green; $script:passed++ }
function Write-Fail { param([string]$msg) Write-Host "  FAIL $msg" -ForegroundColor Red; $script:failed++ }

function Add-Result {
  param([string]$Name, [bool]$Ok, [string]$Detail = "")
  $script:results += [pscustomobject]@{ Name = $Name; Status = if ($Ok) { "PASS" } else { "FAIL" }; Detail = $Detail }
  if ($Ok) { Write-Pass $Name } else { Write-Fail "$Name — $Detail" }
}

# ── T0: 单元测试（离线，无需 DB/LLM）──────────────────────────────────────────
Write-Step "T0: State Machine Unit Tests (offline)"
Push-Location $backend
$unitOut = python -m pytest tests/unit/test_deep_learn_state_machine.py -v --tb=short 2>&1 | Out-String
Pop-Location
$unitOk = $unitOut -match "23 passed"
Add-Result "T0 state_machine unit tests (23 cases)" $unitOk ($unitOut | Select-String "passed|failed|error" | Select-Object -Last 1)

# ── T1: Import 检查 ────────────────────────────────────────────────────────────
Write-Step "T1: Backend Import Check"
Push-Location $backend
$importOut = python -c "
from routers import deep_learn
from services.deep_learn.service import DeepLearnService
from services.deep_learn.state_machine import decide_on_init
from models_deep_learn import SessionState
print('ALL_IMPORTS_OK')
" 2>&1 | Out-String
Pop-Location
Add-Result "T1 backend imports" ($importOut -match "ALL_IMPORTS_OK") $importOut.Trim()

# ── T2: Pydantic Models 字段检查 ───────────────────────────────────────────────
Write-Step "T2: Pydantic Model Fields"
Push-Location $backend
$modelOut = python -c "
from models_deep_learn import SessionState
fields = list(SessionState.model_fields.keys())
required = ['id','user_id','node_id','plan_id','state','current_concept_index',
            'difficulty_level','wrong_count_current','concepts_status','weak_points',
            'recent_turns','what_list','test_questions','test_current_index','test_results','status']
missing = [f for f in required if f not in fields]
if missing:
    print('MISSING:' + ','.join(missing))
else:
    print('FIELDS_OK')
" 2>&1 | Out-String
Pop-Location
Add-Result "T2 SessionState has all 16 fields" ($modelOut -match "FIELDS_OK") $modelOut.Trim()

# ── T3: LLM Config 文件存在 ────────────────────────────────────────────────────
Write-Step "T3: LLM Config Files"
$configs = @(
  "deep_learn_teaching.json",
  "deep_learn_assessment_per_question.json",
  "deep_learn_assessment_overall.json"
)
foreach ($cfg in $configs) {
  $path = Join-Path $backend "services\llm\configs\$cfg"
  $exists = Test-Path $path
  if ($exists) {
    # Use Python to parse JSON to avoid PowerShell UTF-8/escape issues with Chinese content
    Push-Location $backend
    $checkOut = python -c "
import json, sys
with open(r'$path', encoding='utf-8') as f:
    d = json.load(f)
sp = d.get('system_prompt','')
print('HAS_PROMPT' if len(sp) > 10 else 'NO_PROMPT')
" 2>&1 | Out-String
    Pop-Location
    Add-Result "T3 $cfg has system_prompt" ($checkOut -match "HAS_PROMPT") $checkOut.Trim()
  } else {
    Add-Result "T3 $cfg exists" $false "file not found"
  }
}

# ── T4: 文件树完整性 ───────────────────────────────────────────────────────────
Write-Step "T4: File Tree Completeness"
$requiredFiles = @(
  "backend\models_deep_learn.py",
  "backend\services\deep_learn\__init__.py",
  "backend\services\deep_learn\session_repo.py",
  "backend\services\deep_learn\state_machine.py",
  "backend\services\deep_learn\service.py",
  "backend\services\deep_learn\agents\__init__.py",
  "backend\services\deep_learn\agents\teaching.py",
  "backend\services\deep_learn\agents\assessment_per_question.py",
  "backend\services\deep_learn\agents\assessment_overall.py",
  "backend\routers\deep_learn.py"
)
foreach ($f in $requiredFiles) {
  $full = Join-Path $root $f
  Add-Result "T4 $f" (Test-Path $full)
}

$frontendFiles = @(
  "frontend\src\services\deepLearnApi.js",
  "frontend\src\hooks\useDeepLearnSession.js",
  "frontend\src\pages\DeepLearnPage.jsx",
  "frontend\src\components\deep-learn\ConceptProgress.jsx",
  "frontend\src\components\deep-learn\DeepLearnChat.jsx",
  "frontend\src\components\deep-learn\CommandBar.jsx",
  "frontend\src\components\deep-learn\MermaidDiagram.jsx"
)
foreach ($f in $frontendFiles) {
  $full = Join-Path $root $f
  Add-Result "T4 $f" (Test-Path $full)
}

# ── T5: App.jsx 路由注册 ───────────────────────────────────────────────────────
Write-Step "T5: App.jsx Route Registration"
$appJsx = Get-Content (Join-Path $root "frontend\src\App.jsx") -Raw
Add-Result "T5 DeepLearnPage imported" ($appJsx -match "import DeepLearnPage")
Add-Result "T5 /deep-learn route registered" ($appJsx -match "deep-learn/:planId/:nodeId")

# ── T6: main.py router 注册 ────────────────────────────────────────────────────
Write-Step "T6: main.py Router Registration"
$mainPy = Get-Content (Join-Path $backend "main.py") -Raw
Add-Result "T6 deep_learn imported in main.py" ($mainPy -match "from routers import.*deep_learn")
Add-Result "T6 deep_learn.router included" ($mainPy -match "app\.include_router\(deep_learn\.router\)")

# ── T7: State Machine 契约验证 ─────────────────────────────────────────────────
Write-Step "T7: State Machine Contract"
Push-Location $backend
$smOut = python -c "
from services.deep_learn.state_machine import *

# restart from any state
d = decide_on_command('TEACHING', 'restart', 0, 3, False)
assert d.next_state == 'INITIALIZING' and d.action == 'abandon_and_restart', f'restart failed: {d}'

# probe_stuck trigger
d = decide_on_assessment_done('EVALUATING', False, 2, 0)
assert d.teach_mode == 'probe_stuck', f'probe_stuck failed: {d}'

# final judge pass
d = decide_on_final_judge(True)
assert d.next_state == 'COMPLETED', f'final_judge pass failed: {d}'

# final judge fail
d = decide_on_final_judge(False)
assert d.next_state == 'CHOOSING_AFTER_FAIL', f'final_judge fail failed: {d}'

print('SM_CONTRACT_OK')
" 2>&1 | Out-String
Pop-Location
Add-Result "T7 state machine contract assertions" ($smOut -match "SM_CONTRACT_OK") $smOut.Trim()

# ── T8: API Endpoint 存在性（需要后端运行）────────────────────────────────────
Write-Step "T8: API Endpoints (requires running backend)"
if (-not $Token) {
  Write-Host "  SKIP T8 — set TEST_JWT_TOKEN env var to enable API tests" -ForegroundColor Yellow
  $results += [pscustomobject]@{ Name = "T8 API endpoints"; Status = "SKIP"; Detail = "no token" }
} else {
  $headers = @{ Authorization = "Bearer $Token"; "Content-Type" = "application/json" }

  # Health check
  try {
    $health = Invoke-RestMethod -Uri "$BaseUrl/health" -Method GET -TimeoutSec 5
    Add-Result "T8 /health" ($health.status -eq "ok")
  } catch {
    Add-Result "T8 /health" $false $_.Exception.Message
  }

  # POST /sessions (needs valid node_id + plan_id)
  if ($NodeId -and $PlanId) {
    try {
      $body = @{ node_id = $NodeId; plan_id = $PlanId } | ConvertTo-Json
      $sess = Invoke-RestMethod -Uri "$BaseUrl/api/deep-learn/sessions" -Method POST -Headers $headers -Body $body -TimeoutSec 10
      $sessOk = $sess.success -eq $true -and $sess.data.session_id -ne $null
      Add-Result "T8 POST /sessions returns session_id" $sessOk
      if ($sessOk) {
        $sessionId = $sess.data.session_id
        # GET /sessions/{id}
        try {
          $get = Invoke-RestMethod -Uri "$BaseUrl/api/deep-learn/sessions/$sessionId" -Method GET -Headers $headers -TimeoutSec 5
          Add-Result "T8 GET /sessions/{id}" ($get.success -eq $true)
        } catch {
          Add-Result "T8 GET /sessions/{id}" $false $_.Exception.Message
        }
      }
    } catch {
      Add-Result "T8 POST /sessions" $false $_.Exception.Message
    }
  } else {
    Write-Host "  SKIP T8 API session tests — set TEST_NODE_ID and TEST_PLAN_ID" -ForegroundColor Yellow
  }
}

# ── T9b: GraphPage 深入学习按钮集成 ───────────────────────────────────────────
Write-Step "T9b: GraphPage Deep Learn Button Integration"
$graphPagePath = Join-Path $root "frontend\src\pages\GraphPage.jsx"
$graphPageContent = [System.IO.File]::ReadAllText($graphPagePath, [System.Text.Encoding]::UTF8)
# Check for deep-learn navigation (ASCII-safe proxy for button presence)
$hasDeepLearnNav = $graphPageContent -match "deep-learn"
$hasSparkles = $graphPageContent -match "Sparkles"
Add-Result "T9b GraphPage has 深入学习 button" ($hasDeepLearnNav -and $hasSparkles) "nav=$hasDeepLearnNav sparkles=$hasSparkles"
Add-Result "T9b GraphPage navigates to /deep-learn route" ($graphPageContent -match "deep-learn/\`$\{planId\}/\`$\{selectedNode\.id\}")
Add-Result "T9b 深入学习 button only shown when what list non-empty" ($graphPageContent -match "selectedNode\.what\?\.length")

# ── T9: Frontend Build Check ───────────────────────────────────────────────────
Write-Step "T9: Frontend Build (type/lint check)"
$frontend = Join-Path $root "frontend"
Push-Location $frontend
$buildOut = npx vite build --mode development 2>&1 | Out-String
Pop-Location
$buildOk = $buildOut -match "built in" -or $buildOut -match "dist/"
Add-Result "T9 frontend vite build" $buildOk ($buildOut | Select-String "error|Error|built in" | Select-Object -Last 3 | Out-String)

# ── Summary ────────────────────────────────────────────────────────────────────
Write-Host "`n$('─' * 60)" -ForegroundColor DarkGray
Write-Host "DEEP LEARN PHASE 1 — ACCEPTANCE TEST RESULTS" -ForegroundColor White
Write-Host "$('─' * 60)" -ForegroundColor DarkGray

$total = $results.Count
$passCount = ($results | Where-Object { $_.Status -eq "PASS" }).Count
$failCount = ($results | Where-Object { $_.Status -eq "FAIL" }).Count
$skipCount = ($results | Where-Object { $_.Status -eq "SKIP" }).Count

foreach ($r in $results) {
  $color = switch ($r.Status) {
    "PASS" { "Green" }
    "FAIL" { "Red" }
    default { "Yellow" }
  }
  Write-Host ("  [{0}] {1}" -f $r.Status, $r.Name) -ForegroundColor $color
}

Write-Host "`n  Total: $total  |  Pass: $passCount  |  Fail: $failCount  |  Skip: $skipCount" -ForegroundColor White

if ($failCount -eq 0) {
  Write-Host "`n  ALL CHECKS PASSED — Phase 1 acceptance criteria met." -ForegroundColor Green
  exit 0
} else {
  Write-Host "`n  $failCount check(s) FAILED — review output above." -ForegroundColor Red
  exit 1
}
