import React from 'react';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

const {
  profileGetMock,
  plansListMock,
  notesListMock,
  toastApi,
} = vi.hoisted(() => {
  const hoistedToastErrorMock = vi.fn();
  const hoistedToastSuccessMock = vi.fn();

  return {
    profileGetMock: vi.fn(),
    plansListMock: vi.fn(),
    notesListMock: vi.fn(),
    toastErrorMock: hoistedToastErrorMock,
    toastSuccessMock: hoistedToastSuccessMock,
    toastApi: {
      error: hoistedToastErrorMock,
      success: hoistedToastSuccessMock,
    },
  };
});

vi.mock('../services/api', () => ({
  userProfileApi: {
    get: profileGetMock,
    update: vi.fn(async (payload) => payload),
  },
  plansApi: {
    list: plansListMock,
    create: vi.fn(),
    update: vi.fn(),
    archive: vi.fn(),
    delete: vi.fn(),
    restore: vi.fn(),
  },
  notesApi: {
    list: notesListMock,
    create: vi.fn(),
    delete: vi.fn(),
  },
}));

vi.mock('./AuthContext', () => ({
  useAuth: () => ({
    isAuthenticated: true,
    isLoading: false,
  }),
}));

vi.mock('./ToastContext', () => ({
  useToast: () => toastApi,
}));

import { AppProvider, useAppContext } from './AppContext.jsx';
import { useGraphContext } from './GraphContext.jsx';
import { useNoteContext } from './NoteContext.jsx';
import { usePlanContext } from './PlanContext.jsx';

function ContextProbe() {
  const app = useAppContext();
  const plan = usePlanContext();
  const note = useNoteContext();
  const graph = useGraphContext();

  return (
    <div>
      <div data-testid="app-loading">{String(app.isLoading)}</div>
      <div data-testid="plan-count">{plan.plans.length}</div>
      <div data-testid="note-count">{note.allNotes.length}</div>
      <div data-testid="profile-occupation">{plan.userProfile.occupation}</div>
      <div data-testid="graph-count">{Object.keys(graph.graphsByPlanId).length}</div>
      <div data-testid="plan-progress">{app.plans[0]?.progress ?? 0}</div>
      <button
        onClick={() =>
          graph.actions.setGraph('plan-1', {
            title: 'Graph Snapshot',
            nodes: [{ id: 'n1', name: 'Root' }],
            edges: [],
          })
        }
      >
        cache graph
      </button>
      <button onClick={() => app.actions.updatePlanProgress('plan-1', 2, 5)}>
        update progress
      </button>
    </div>
  );
}

describe('Sprint 4 app context split', () => {
  beforeEach(() => {
    profileGetMock.mockResolvedValue({
      occupation: 'Engineer',
      education: 'Bachelor',
      abilities: ['Python'],
      masteredKnowledge: [],
    });
    plansListMock.mockResolvedValue([
      { id: 'plan-1', title: 'Transformer', progress: 1, total: 5, status: 'active' },
    ]);
    notesListMock.mockResolvedValue({
      notes: [{ id: 'note-1', planId: 'plan-1', content: 'self-attention' }],
    });
  });

  afterEach(() => {
    vi.clearAllMocks();
  });

  it('hydrates split contexts and keeps AppContext compatibility', async () => {
    render(
      <AppProvider>
        <ContextProbe />
      </AppProvider>,
    );

    await waitFor(() => {
      expect(screen.getByTestId('app-loading')).toHaveTextContent('false');
    });

    expect(screen.getByTestId('plan-count')).toHaveTextContent('1');
    expect(screen.getByTestId('note-count')).toHaveTextContent('1');
    expect(screen.getByTestId('profile-occupation')).toHaveTextContent('Engineer');

    fireEvent.click(screen.getByRole('button', { name: 'cache graph' }));
    expect(screen.getByTestId('graph-count')).toHaveTextContent('1');

    fireEvent.click(screen.getByRole('button', { name: 'update progress' }));
    expect(screen.getByTestId('plan-progress')).toHaveTextContent('2');
  });
});
