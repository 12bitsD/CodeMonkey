import { test, expect } from '@playwright/test';

function makeFakeToken() {
  const header = Buffer.from(JSON.stringify({ alg: 'HS256', typ: 'JWT' })).toString('base64');
  const payload = Buffer.from(
    JSON.stringify({ sub: 'test_user', email: 'test@test.com', exp: 9999999999 })
  ).toString('base64');
  return `${header}.${payload}.fake_sig`;
}

function sse(events) {
  return events.map((event) => `data: ${JSON.stringify(event)}\n\n`).join('');
}

test.describe('Deep Learn flow', () => {
  test('last concept answer shows comprehensive test confirmation directly', async ({ page }) => {
    const commands = [];

    await page.addInitScript((token) => {
      localStorage.setItem('concept_tree_token', token);
    }, makeFakeToken());

    await page.route('**/api/user/profile', async (route) => {
      await route.fulfill({
        json: {
          success: true,
          data: {
            occupation: '',
            education: '',
            programmingLevel: 'beginner',
            mathLevel: 'beginner',
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
    await page.route('**/api/ai/recommend-next', async (route) => {
      await route.fulfill({ json: { success: true, data: {} } });
    });

    await page.route('**/api/deep-learn/sessions', async (route) => {
      await route.fulfill({
        json: {
          success: true,
          data: {
            session_id: 's-e2e',
            state: 'QUESTIONING',
            is_resumed: true,
            node_name: 'Mock Node',
            node_why: 'For e2e validation',
            what_list: ['Concept A', 'Concept B', 'Concept C'],
            concepts_status: { 0: 'done', 1: 'done' },
            weak_points: [],
            current_concept_index: 2,
            recent_turns: [
              { role: 'assistant', kind: 'text', content: 'Explain Concept C.' },
              { role: 'assistant', kind: 'questions', content: ['What is Concept C?'] },
            ],
          },
        },
      });
    });

    await page.route('**/api/deep-learn/sessions/s-e2e/message', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'text/event-stream',
        body: sse([
          {
            type: 'assessment',
            is_correct: true,
            explanation: 'Correct',
            feedback: 'Ready for final test.',
          },
          { type: 'concept_update', index: 2, status: 'done' },
          { type: 'state_change', from: 'EVALUATING', to: 'AI_ASSESSING_READINESS' },
          { type: 'state_change', from: 'AI_ASSESSING_READINESS', to: 'CONFIRMING_TEST' },
          {
            type: 'test_confirm_prompt',
            message: 'Ready for comprehensive test?',
            commands: ['confirm_test', 'not_ready'],
          },
          { type: 'done' },
        ]),
      });
    });

    await page.route('**/api/deep-learn/sessions/s-e2e/command', async (route) => {
      commands.push(JSON.parse(route.request().postData()).command);
      await route.fulfill({
        status: 200,
        contentType: 'text/event-stream',
        body: sse([{ type: 'done' }]),
      });
    });

    await page.goto('/deep-learn/p-e2e/n-e2e');

    await expect(page.getByText('Concept C', { exact: true })).toBeVisible({ timeout: 8000 });
    await expect(page.getByText('2 / 3')).toBeVisible();

    await page.locator('main textarea').fill('Concept C is the final concept.');
    await page.locator('main button:has(svg)').last().click();

    await expect(page.getByText('3 / 3')).toBeVisible({ timeout: 8000 });
    await expect(page.getByText('Ready for comprehensive test?')).toBeVisible();

    await page.locator('.border-blue-200 button').first().click();
    expect(commands).toEqual(['confirm_test']);
  });

  test('passing the final assessment opens the generated completion note', async ({ page }) => {
    await page.addInitScript((token) => {
      localStorage.setItem('concept_tree_token', token);
    }, makeFakeToken());

    await page.route('**/api/user/profile', route => route.fulfill({
      json: { success: true, data: {} },
    }));
    await page.route('**/api/plans', route => route.fulfill({
      json: { success: true, data: [] },
    }));
    await page.route('**/api/notes', route => route.fulfill({
      json: { success: true, data: [] },
    }));
    await page.route('**/api/ai/recommend-next', route => route.fulfill({
      json: { success: true, data: {} },
    }));
    await page.route('**/api/deep-learn/sessions', route => route.fulfill({
      json: {
        success: true,
        data: {
          session_id: 's-final',
          state: 'TESTING',
          is_resumed: true,
          node_name: 'Mock Node',
          node_why: 'For completion validation',
          what_list: ['Concept A'],
          concepts_status: { 0: 'done' },
          weak_points: [],
          current_concept_index: 0,
          recent_turns: [
            { role: 'assistant', kind: 'questions', content: ['Final question'] },
          ],
        },
      },
    }));
    await page.route('**/api/deep-learn/sessions/s-final/message', route => route.fulfill({
      status: 200,
      contentType: 'text/event-stream',
      body: sse([
        { type: 'assessment', is_correct: true, explanation: 'Correct' },
        { type: 'state_change', from: 'EVALUATING_TEST', to: 'GENERATING_NOTE' },
        { type: 'note_generating' },
        { type: 'state_change', from: 'GENERATING_NOTE', to: 'COMPLETED' },
        { type: 'note_ready', note_id: 'note-e2e' },
        { type: 'node_completed', node_id: 'n-e2e' },
        { type: 'done' },
      ]),
    }));
    await page.route('**/api/deep-learn/notes/note-e2e', route => route.fulfill({
      json: {
        id: 'note-e2e',
        node_id: 'n-e2e',
        session_id: 's-final',
        content: '# Completed',
        created_at: '2026-08-01T00:00:00Z',
      },
    }));

    await page.goto('/deep-learn/p-e2e/n-e2e');
    await page.locator('main textarea').fill('A complete and reasoned final answer.');
    await page.locator('main button:has(svg)').last().click();

    await expect(page).toHaveURL('/deep-learn/p-e2e/n-e2e/note/note-e2e');
    await expect(page.getByRole('heading', { name: 'Completed' })).toBeVisible();
  });
});
