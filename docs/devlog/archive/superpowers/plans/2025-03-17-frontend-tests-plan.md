# ConceptTree Frontend Tests Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development or superpowers:executing-plans. Steps use checkbox syntax.

**Goal:** Implement Vitest unit tests for API edge mapping and Playwright E2E tests for the main application flows using mock API responses.

**Architecture:** 
- `vitest` for unit testing pure JavaScript logic in `api.js`
- `@playwright/test` for E2E testing React application flows
- `page.route` to intercept all backend calls and return mock data, decoupling tests from Supabase

**Tech Stack:** Vitest, Playwright, Node.js

---

## Chunk 1: Setup Testing Environment

### Task 1.1: Install Testing Dependencies

**Files:**
- Modify: `ConceptTree/frontend/package.json`
- Modify: `ConceptTree/frontend/vite.config.js`

- [ ] **Step 1: Install Vitest**
```bash
cd ConceptTree/frontend
npm install -D vitest
```

- [ ] **Step 2: Install Playwright**
```bash
cd ConceptTree/frontend
npm init playwright@latest --yes -- --quiet --browser=chromium --browser=firefox --browser=webkit --lang=js --gha
```
*(Accept defaults: E2E tests in `tests/`, add GitHub Actions, install browsers)*

- [ ] **Step 3: Add test scripts to package.json**
Add to `scripts` section in `package.json`:
```json
"test:unit": "vitest run",
"test:unit:watch": "vitest",
"test:e2e": "playwright test",
"test:e2e:ui": "playwright test --ui"
```

- [ ] **Step 4: Update Playwright config**
Modify `playwright.config.js` to use localhost:5173 (Vite default):
```javascript
// Add or modify webServer section in playwright.config.js
  webServer: {
    command: 'npm run dev',
    url: 'http://localhost:5173',
    reuseExistingServer: !process.env.CI,
  },
```

- [ ] **Step 5: Commit**
```bash
git add ConceptTree/frontend/package.json ConceptTree/frontend/package-lock.json ConceptTree/frontend/playwright.config.js
git commit -m "chore(frontend): setup vitest and playwright for testing"
```

---

## Chunk 2: Unit Tests for Edge Mapping

### Task 2.1: Extract and Test Edge Mapping Logic

**Files:**
- Modify: `ConceptTree/frontend/src/services/api.js` (Export mapping functions)
- Create: `ConceptTree/frontend/src/services/api.test.js`

- [ ] **Step 1: Export mapping functions**
In `ConceptTree/frontend/src/services/api.js`, export the two mapping functions so they can be tested:
```javascript
export const mapEdgesFromBackend = (edges) => ...
export const mapEdgesToBackend = (edges) => ...
```

- [ ] **Step 2: Write unit tests**
Create `ConceptTree/frontend/src/services/api.test.js`:
```javascript
import { describe, it, expect } from 'vitest';
import { mapEdgesFromBackend, mapEdgesToBackend } from './api';

describe('Edge Mapping Utility', () => {
  describe('mapEdgesFromBackend', () => {
    it('should map from_node and to_node to from and to, preserving other properties', () => {
      const backendEdges = [{ from_node: "A", to_node: "B", style: "dotted" }];
      const result = mapEdgesFromBackend(backendEdges);
      expect(result).toEqual([{ from: "A", to: "B", style: "dotted" }]);
    });

    it('should handle null or undefined input gracefully', () => {
      expect(mapEdgesFromBackend(null)).toEqual([]);
      expect(mapEdgesFromBackend(undefined)).toEqual([]);
    });

    it('should pass through already mapped edges safely', () => {
      const mixedEdges = [{ from: "C", to: "D", label: "x" }];
      const result = mapEdgesFromBackend(mixedEdges);
      expect(result).toEqual([{ from: "C", to: "D", label: "x" }]);
    });
  });

  describe('mapEdgesToBackend', () => {
    it('should map from and to back to from_node and to_node, preserving other properties', () => {
      const frontendEdges = [{ from: "C", to: "D", label: "x" }];
      const result = mapEdgesToBackend(frontendEdges);
      expect(result).toEqual([{ from_node: "C", to_node: "D", label: "x" }]);
    });

    it('should handle null or undefined input gracefully', () => {
      expect(mapEdgesToBackend(null)).toEqual([]);
    });
  });
});
```

- [ ] **Step 3: Run unit tests**
```bash
cd ConceptTree/frontend
npm run test:unit
```
Expected: All 5 tests PASS.

- [ ] **Step 4: Commit**
```bash
git add ConceptTree/frontend/src/services/api.js ConceptTree/frontend/src/services/api.test.js
git commit -m "test(frontend): add unit tests for bidirectional edge mapping"
```

---

## Chunk 3: E2E Tests - Happy Path

### Task 3.1: Write Main Flow E2E Test

**Files:**
- Create: `ConceptTree/frontend/tests/main-flow.spec.js`

- [ ] **Step 1: Write E2E test for standard graph generation**
Create `ConceptTree/frontend/tests/main-flow.spec.js`:
```javascript
import { test, expect } from '@playwright/test';

test.describe('ConceptTree Main Flow', () => {
  test.beforeEach(async ({ page }) => {
    // Mock user profile to avoid auth issues during test
    await page.route('**/api/user/profile', async (route) => {
      await route.fulfill({ json: { success: true, data: { abilities: ['Python'] } } });
    });
    
    // Mock active plans (empty list)
    await page.route('**/api/plans', async (route) => {
      if (route.request().method() === 'GET') {
        await route.fulfill({ json: { success: true, data: [] } });
      } else {
        // Mock POST /api/plans
        await route.fulfill({ 
          json: { success: true, data: { id: "p_mock_123", title: "React学习" } } 
        });
      }
    });
  });

  test('should complete happy path: input -> confirm -> generate -> view graph', async ({ page }) => {
    // 1. Mock AI Parse Goal
    await page.route('**/api/ai/parse-goal', async (route) => {
      await route.fulfill({ 
        json: { 
          success: true, 
          data: { 
            interpretation: "掌握React基础", 
            backgroundSummary: [], 
            suggestedNodeCount: 5, 
            shouldSplit: false 
          } 
        } 
      });
    });

    // 2. Mock AI Generate Graph
    await page.route('**/api/ai/generate-graph', async (route) => {
      await route.fulfill({ 
        json: { 
          success: true, 
          data: { 
            interpretation: "掌握React基础", 
            nodes: [{ id: "n1", name: "JSX", isTarget: false }, { id: "n2", name: "React组件", isTarget: true }], 
            edges: [{ from_node: "n1", to_node: "n2" }],
            targetNodeId: "n2"
          } 
        } 
      });
    });

    // 3. Visit homepage
    await page.goto('/');

    // 4. Input goal and submit
    await page.fill('textarea[placeholder*="例如：我想理解"]', '我想学React');
    await page.click('button:has-text("生成图谱")');

    // 5. Assert confirmation modal appears
    await expect(page.locator('h4:has-text("识别目标")')).toBeVisible();
    await expect(page.locator('p:has-text("掌握React基础")')).toBeVisible();

    // 6. Confirm generation
    await page.click('button:has-text("确认生成")');

    // 7. Assert loading state appears
    await expect(page.locator('.animate-spin')).toBeVisible();

    // 8. Wait for navigation to graph page
    await page.waitForURL('**/graph/p_mock_123');
    
    // Test passes if URL is reached (meaning all API mocks were called successfully in sequence)
  });
});
```

- [ ] **Step 2: Run E2E test**
```bash
cd ConceptTree/frontend
npx playwright test tests/main-flow.spec.js --project=chromium
```
Expected: Test PASS.

- [ ] **Step 3: Commit**
```bash
git add ConceptTree/frontend/tests/main-flow.spec.js
git commit -m "test(frontend): add E2E test for main graph generation flow"
```

---

## Chunk 4: E2E Tests - Split Suggestions and Stats

### Task 4.1: Write Tests for Edge Cases and Stats

**Files:**
- Modify: `ConceptTree/frontend/tests/main-flow.spec.js`

- [ ] **Step 1: Add Split Suggestion Test**
Append to `tests/main-flow.spec.js`:
```javascript
  test('should display split suggestions when goal is too broad', async ({ page }) => {
    // 1. Mock AI Parse Goal with shouldSplit: true
    await page.route('**/api/ai/parse-goal', async (route) => {
      await route.fulfill({ 
        json: { 
          success: true, 
          data: { 
            interpretation: "目标过大", 
            shouldSplit: true, 
            splitSuggestions: [
              { title: "前端基础", description: "HTML/CSS/JS", estimatedNodes: 10 }
            ]
          } 
        } 
      });
    });

    // 2. Visit homepage
    await page.goto('/');

    // 3. Input broad goal
    await page.fill('textarea', '我想学编程');
    await page.click('button:has-text("生成图谱")');

    // 4. Assert split suggestion card appears
    const suggestionCard = page.locator('h5:has-text("前端基础")');
    await expect(suggestionCard).toBeVisible();

    // 5. Click the suggestion
    await suggestionCard.click();

    // 6. Assert modal closed and input updated
    await expect(page.locator('h4:has-text("识别目标")')).not.toBeVisible();
    await expect(page.locator('textarea')).toHaveValue('前端基础');
  });
```

- [ ] **Step 2: Add Stats Tab Test**
Append to `tests/main-flow.spec.js`:
```javascript
  test('should render stats and handle empty states gracefully', async ({ page }) => {
    // 1. Mock Stats Overview API
    await page.route('**/api/stats/overview', async (route) => {
      await route.fulfill({ 
        json: { 
          success: true, 
          data: { completedPlans: 42, activePlans: 3, masteredNodes: 150, totalNotes: 10 } 
        } 
      });
    });

    // Mock empty distribution
    await page.route('**/api/stats/distribution', async (route) => {
      await route.fulfill({ json: { success: true, data: [] } });
    });

    // 2. Mock Auth to allow access to /my-learning
    await page.addInitScript(() => {
      localStorage.setItem('concept_tree_token', 'mock_token');
    });

    // 3. Visit MyLearning page
    await page.goto('/my-learning');

    // 4. Click Stats tab
    await page.click('button:has-text("学习统计")');

    // 5. Assert values are rendered
    await expect(page.locator('text=42')).toBeVisible(); // Completed plans
    await expect(page.locator('text=150')).toBeVisible(); // Mastered nodes

    // 6. Assert empty state for distribution
    await expect(page.locator('text=开始学习后，这里将显示你的知识领域分布')).toBeVisible();
  });
```

- [ ] **Step 3: Add Error State Test**
Append to `tests/main-flow.spec.js`:
```javascript
  test('should not crash when AI API returns 500 error', async ({ page }) => {
    // 1. Mock 500 error
    await page.route('**/api/ai/parse-goal', async (route) => {
      await route.fulfill({ 
        status: 500,
        json: { success: false, error: { message: "AI Service Error" } } 
      });
    });

    // 2. Trigger flow
    await page.goto('/');
    await page.fill('textarea', '我想报错');
    await page.click('button:has-text("生成图谱")');

    // 3. Assert button becomes clickable again (not stuck in loading)
    const button = page.locator('button:has-text("生成图谱")');
    await expect(button).toBeEnabled({ timeout: 5000 });
    
    // We expect the app to stay on the homepage and not crash
    expect(page.url()).not.toContain('/graph');
  });
```

- [ ] **Step 4: Run all E2E tests**
```bash
cd ConceptTree/frontend
npx playwright test tests/main-flow.spec.js --project=chromium
```
Expected: All 4 tests PASS.

- [ ] **Step 5: Commit**
```bash
git add ConceptTree/frontend/tests/main-flow.spec.js
git commit -m "test(frontend): add E2E tests for split suggestions, stats, and error states"
```

---

## Final Review
After completing Chunks 1-4, review the implementation and verify all automated tests are passing reliably.
