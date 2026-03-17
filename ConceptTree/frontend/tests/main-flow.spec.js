import { test, expect } from '@playwright/test';

function makeFakeToken() {
  const header = Buffer.from(JSON.stringify({ alg: 'HS256', typ: 'JWT' })).toString('base64');
  const payload = Buffer.from(
    JSON.stringify({ sub: 'test_user', email: 'test@test.com', exp: 9999999999 })
  ).toString('base64');
  return `${header}.${payload}.fake_sig`;
}

async function mockCommonApis(page) {
  await page.route('**/api/user/profile', async (route) => {
    await route.fulfill({
      json: {
        success: true,
        data: {
          occupation: '',
          education: '',
          programmingLevel: '入门',
          mathLevel: '入门',
          abilities: [],
          masteredKnowledge: [],
        },
      },
    });
  });
  await page.route('**/api/plans', async (route) => {
    if (route.request().method() === 'GET') {
      await route.fulfill({ json: { success: true, data: [] } });
    } else {
      await route.fulfill({
        json: { success: true, data: { id: 'p_mock_123', title: 'Test Plan' } },
      });
    }
  });
  await page.route('**/api/notes', async (route) => {
    await route.fulfill({ json: { success: true, data: [] } });
  });
}

test.describe('ConceptTree Main Flow', () => {
  test('happy path: input → confirm modal → confirm → navigate to graph page', async ({ page }) => {
    await mockCommonApis(page);

    await page.route('**/api/ai/parse-goal', async (route) => {
      await route.fulfill({
        json: {
          success: true,
          data: {
            interpretation: '掌握React基础',
            backgroundSummary: [],
            suggestedNodeCount: 5,
            shouldSplit: false,
            splitSuggestions: null,
          },
        },
      });
    });

    await page.route('**/api/ai/generate-graph', async (route) => {
      await route.fulfill({
        json: {
          success: true,
          data: {
            interpretation: '掌握React基础',
            nodes: [
              {
                id: 'n1',
                name: 'JSX',
                status: 'unlearned',
                x: -100,
                y: -100,
                why: 'JSX is foundational',
                what: ['JSX syntax'],
                mastery: ['Write a component'],
                prompt: 'Explain JSX',
                resources: [],
                isTarget: false,
                domain: '编程',
              },
              {
                id: 'n2',
                name: 'React组件',
                status: 'unlearned',
                x: 0,
                y: 0,
                why: 'Target',
                what: ['Components'],
                mastery: ['Build a form'],
                prompt: 'Explain React',
                resources: [],
                isTarget: true,
                domain: '编程',
              },
            ],
            edges: [{ from_node: 'n1', to_node: 'n2' }],
            targetNodeId: 'n2',
          },
        },
      });
    });

    await page.goto('/');

    await page.locator('textarea').fill('我想学React');
    await page.click('button:has-text("生成图谱")');

    await expect(page.locator('text=识别目标')).toBeVisible({ timeout: 8000 });
    await expect(page.locator('text=掌握React基础')).toBeVisible();

    await page.click('button:has-text("确认生成")');

    await expect(page.locator('.animate-spin')).toBeVisible({ timeout: 5000 });

    await page.waitForURL('**/graph/p_mock_123', { timeout: 15000 });
    expect(page.url()).toContain('/graph/p_mock_123');
  });

  test('split suggestions: broad goal shows cards, clicking one updates textarea', async ({ page }) => {
    await mockCommonApis(page);

    await page.route('**/api/ai/parse-goal', async (route) => {
      await route.fulfill({
        json: {
          success: true,
          data: {
            interpretation: '学习编程',
            backgroundSummary: [],
            suggestedNodeCount: 20,
            shouldSplit: true,
            splitSuggestions: [
              { title: '前端基础', description: 'HTML/CSS/JS入门', estimatedNodes: 8 },
              { title: 'Python编程', description: 'Python语法与实践', estimatedNodes: 7 },
            ],
          },
        },
      });
    });

    await page.goto('/');

    await page.locator('textarea').fill('我想学编程');
    await page.click('button:has-text("生成图谱")');

    await expect(page.locator('text=🎯 目标较大')).toBeVisible({ timeout: 8000 });

    const suggestionCard = page.locator('h5').filter({ hasText: '前端基础' });
    await expect(suggestionCard).toBeVisible();

    await suggestionCard.click();

    await expect(page.locator('text=识别目标')).not.toBeVisible({ timeout: 3000 });

    await expect(page.locator('textarea')).toHaveValue('前端基础');
  });

  test('stats tab: shows fetched stats values and empty distribution', async ({ page }) => {
    const fakeToken = makeFakeToken();

    await page.addInitScript((token) => {
      localStorage.setItem('concept_tree_token', token);
    }, fakeToken);

    await page.route('**/api/user/profile', async (route) => {
      await route.fulfill({
        json: {
          success: true,
          data: {
            occupation: '',
            education: '',
            programmingLevel: '入门',
            mathLevel: '入门',
            abilities: [],
            masteredKnowledge: [],
          },
        },
      });
    });
    await page.route('**/api/plans', async (route) => {
      await route.fulfill({ json: { success: true, data: [] } });
    });
    await page.route('**/api/notes', async (route) => {
      await route.fulfill({ json: { success: true, data: [] } });
    });
    await page.route('**/api/stats/overview', async (route) => {
      await route.fulfill({
        json: {
          success: true,
          data: { completedPlans: 42, activePlans: 3, masteredNodes: 150, totalNotes: 10 },
        },
      });
    });
    await page.route('**/api/stats/distribution', async (route) => {
      await route.fulfill({ json: { success: true, data: [] } });
    });

    await page.goto('/my-learning');

    await page.click('button:has-text("学习统计")');

    await expect(page.getByText('42').first()).toBeVisible({ timeout: 5000 });
    await expect(page.getByText('150').first()).toBeVisible();

    await expect(
      page.locator('text=开始学习后，这里将显示你的知识领域分布')
    ).toBeVisible();
  });

  test('error state: 500 from parse-goal returns button to interactive state', async ({ page }) => {
    await mockCommonApis(page);

    await page.route('**/api/ai/parse-goal', async (route) => {
      await route.fulfill({
        status: 500,
        json: {
          success: false,
          error: { code: 'AI_SERVICE_ERROR', message: 'AI Service Error' },
        },
      });
    });

    await page.goto('/');
    await page.locator('textarea').fill('我想报错');
    await page.click('button:has-text("生成图谱")');

    await expect(page.locator('button:has-text("生成图谱")')).toBeEnabled({ timeout: 8000 });

    expect(page.url()).not.toContain('/graph');
  });

  test('generate-graph request includes userBackground when profile has abilities', async ({ page }) => {
    const fakeToken = makeFakeToken();
    await page.addInitScript((token) => {
      localStorage.setItem('concept_tree_token', token);
    }, fakeToken);

    await page.route('**/api/user/profile', async (route) => {
      await route.fulfill({
        json: {
          success: true,
          data: {
            occupation: '学生', education: '本科',
            programmingLevel: '入门', mathLevel: '无基础',
            abilities: ['JavaScript入门'],
            masteredKnowledge: ['变量', '函数'],
          },
        },
      });
    });
    await page.route('**/api/plans', async (route) => {
      if (route.request().method() === 'GET') {
        await route.fulfill({ json: { success: true, data: [] } });
      } else {
        await route.fulfill({ json: { success: true, data: { id: 'p_bg_test', title: '测试' } } });
      }
    });
    await page.route('**/api/notes', async (route) => {
      await route.fulfill({ json: { success: true, data: [] } });
    });
    await page.route('**/api/ai/parse-goal', async (route) => {
      await route.fulfill({
        json: {
          success: true,
          data: { interpretation: '掌握React', backgroundSummary: [], suggestedNodeCount: 5, shouldSplit: false, splitSuggestions: null },
        },
      });
    });

    let capturedBody = null;
    await page.route('**/api/ai/generate-graph', async (route) => {
      capturedBody = JSON.parse(route.request().postData());
      await route.fulfill({
        json: {
          success: true,
          data: {
            interpretation: '掌握React',
            nodes: [{ id: 'n1', name: 'JSX', status: 'unlearned', x: 0, y: 0, why: '', what: [], mastery: [], prompt: '', resources: [], isTarget: true, domain: '编程' }],
            edges: [],
            targetNodeId: 'n1',
          },
        },
      });
    });

    await page.goto('/');
    await page.locator('textarea').fill('我想学React');
    await page.click('button:has-text("生成图谱")');
    await expect(page.locator('text=掌握React')).toBeVisible({ timeout: 8000 });
    await page.click('button:has-text("确认生成")');
    await page.waitForURL('**/graph/p_bg_test', { timeout: 15000 });

    expect(capturedBody).not.toBeNull();
    expect(capturedBody.userBackground).toBeDefined();
    expect(capturedBody.userBackground.abilities).toContain('JavaScript入门');
    expect(capturedBody.userBackground.masteredKnowledge).toContain('变量');
  });

  test('toast appears when AI parse-goal returns 500 error', async ({ page }) => {
    await mockCommonApis(page);

    await page.route('**/api/ai/parse-goal', async (route) => {
      await route.fulfill({
        status: 500,
        json: { success: false, error: { code: 'AI_SERVICE_ERROR', message: 'Service unavailable' } },
      });
    });

    await page.goto('/');
    await page.locator('textarea').fill('触发错误');
    await page.click('button:has-text("生成图谱")');

    await expect(page.locator('text=解析目标失败，请稍后重试')).toBeVisible({ timeout: 5000 });
  });
});
