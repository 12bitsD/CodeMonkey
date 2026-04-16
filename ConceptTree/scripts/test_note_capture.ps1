$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $PSScriptRoot
$frontend = Join-Path $root "frontend"

Write-Host "[Note Capture] Running note formatting tests..."
Push-Location $frontend

npx vitest run src/utils/noteFormatting.test.js --pool=threads
npx vitest run src/utils/noteCapture.test.js --pool=threads
npx eslint src/pages/GraphPage.jsx src/utils/noteFormatting.js src/utils/noteFormatting.test.js src/utils/noteCapture.js src/utils/noteCapture.test.js

Pop-Location

Write-Host "[Note Capture] All targeted checks passed."
