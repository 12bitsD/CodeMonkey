Push-Location "$PSScriptRoot\..\backend"

python -m pytest tests/test_search_service.py -q
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

python -m pytest tests/test_chat_web_search.py -q
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Pop-Location
Push-Location "$PSScriptRoot\..\frontend"

npx vitest run src/components/chat/ChatMarkdownMessage.test.jsx src/services/api.chat-search.test.js --pool=threads
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

npx eslint src/pages/GraphPage.jsx src/components/chat/ChatMarkdownMessage.jsx src/services/api.js
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Pop-Location
exit 0
