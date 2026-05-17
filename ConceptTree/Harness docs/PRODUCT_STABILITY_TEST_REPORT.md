# Product Stability Test Report

- Generated: 2026-05-17 04:01:40 +08:00
- Workspace: `C:\Users\Victor\Desktop\CodeMonkey666\CodeMonkey\ConceptTree`
- Result: PASS
- Passed: 4
- Failed: 0
- Skipped: 2

## Coverage

- **Frontend critical unit suite** [PASS] - notes save fallback; plan and graph cache; recoverable API errors and degraded sync banner; today recommendation cache; loading view; AI SSE signal; reminders; graph utilities; chat panel; resource search; note formatting
- **Backend no-db stability unit suite** [PASS] - LLM fast fail; retry behavior; AI graph repair; node date validation; note node id compatibility; idempotency helpers; chat stream fallback; database timeout and recoverable error handling
- **Backend syntax smoke** [PASS] - backend core imports, routers, database, observability and LLM provider syntax
- **Frontend production build** [PASS] - production bundle and route/component compile
- **Backend DB integration smoke** [SKIP] - real Supabase smoke: note idempotency, node status idempotency, AI recommendation fallback and plan management update
- **Playwright main flow** [SKIP] - browser-level main flow with local services and test data

## Detected Errors

No failures were detected by the default stability suite.

## Skipped Items

- **Backend DB integration smoke** - Skipped by default. Use -IncludeDbIntegration when Supabase test DB is reachable. Use -DeepDbIntegration for the full slow release regression.
- **Playwright main flow** - Skipped by default. Use -IncludeE2E when local services and test data are ready.

## Recommendations

- Keep note saving, AI generation and deadline updates isolated: a failed action should not clear page state or crash the app.
- Keep short timeout, cancellation and bounded retry policies for every remote dependency.
- Run DB integration checks before release when Supabase pooler is stable.
- Add browser-level rapid-click, refresh-during-stream and node-switch E2E cases next.
- Add synthetic monitoring for /api/notes, /api/plans and /api/ai/recommend-next latency and error rate.

## Commands

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\test_product_stability.ps1
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\test_product_stability.ps1 -IncludeDbIntegration
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\test_product_stability.ps1 -IncludeDbIntegration -DeepDbIntegration -IncludeE2E
```
