import React from "react";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

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
    toastApi: {
      error: hoistedToastErrorMock,
      success: hoistedToastSuccessMock,
    },
  };
});

vi.mock("../services/api", () => ({
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
    pause: vi.fn(),
    resume: vi.fn(),
  },
  notesApi: {
    list: notesListMock,
    create: vi.fn(),
    delete: vi.fn(),
  },
}));

vi.mock("./AuthContext", () => ({
  useAuth: () => ({
    isAuthenticated: true,
    isLoading: false,
  }),
}));

vi.mock("./ToastContext", () => ({
  useToast: () => toastApi,
}));

import { AppProvider, useAppContext } from "./AppContext.jsx";
import { useGraphContext } from "./GraphContext.jsx";
import { useNoteContext } from "./NoteContext.jsx";
import { usePlanContext } from "./PlanContext.jsx";

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
      <div data-testid="sync-degraded">{String(app.dataSyncStatus.degraded)}</div>
      <div data-testid="sync-message">{app.dataSyncStatus.message}</div>
      <button
        onClick={() =>
          graph.actions.setGraph("plan-1", {
            title: "Graph Snapshot",
            nodes: [{ id: "n1", name: "Root" }],
            edges: [],
          })
        }
      >
        cache graph
      </button>
      <button onClick={() => app.actions.updatePlanProgress("plan-1", 2, 5)}>
        update progress
      </button>
    </div>
  );
}

describe("Sprint 4 app context split", () => {
  beforeEach(() => {
    profileGetMock.mockResolvedValue({
      occupation: "Engineer",
      education: "Bachelor",
      abilities: ["Python"],
      masteredKnowledge: [],
    });
    plansListMock.mockResolvedValue([
      { id: "plan-1", title: "Transformer", progress: 1, total: 5, status: "active" },
    ]);
    notesListMock.mockResolvedValue({
      notes: [{ id: "note-1", planId: "plan-1", content: "self-attention" }],
    });
  });

  afterEach(() => {
    vi.clearAllMocks();
    window.localStorage.clear();
  });

  it("hydrates split contexts and keeps AppContext compatibility", async () => {
    render(
      <AppProvider>
        <ContextProbe />
      </AppProvider>,
    );

    await waitFor(() => {
      expect(screen.getByTestId("app-loading")).toHaveTextContent("false");
    });

    expect(screen.getByTestId("plan-count")).toHaveTextContent("1");
    expect(screen.getByTestId("note-count")).toHaveTextContent("1");
    expect(screen.getByTestId("profile-occupation")).toHaveTextContent("Engineer");

    fireEvent.click(screen.getByRole("button", { name: "cache graph" }));
    expect(screen.getByTestId("graph-count")).toHaveTextContent("1");

    fireEvent.click(screen.getByRole("button", { name: "update progress" }));
    expect(screen.getByTestId("plan-progress")).toHaveTextContent("2");
  });

  it("falls back to cached notes when loading notes fails", async () => {
    notesListMock.mockRejectedValue(new Error("notes service down"));
    window.localStorage.setItem(
      "concept_tree_notes_cache",
      JSON.stringify({
        notes: [{ id: "cached-note", planId: "plan-1", content: "cached note" }],
      }),
    );

    render(
      <AppProvider>
        <ContextProbe />
      </AppProvider>,
    );

    await waitFor(() => {
      expect(screen.getByTestId("app-loading")).toHaveTextContent("false");
    });

    expect(screen.getByTestId("note-count")).toHaveTextContent("1");
    expect(toastApi.error).toHaveBeenCalledWith("加载笔记失败，已显示本地缓存");
  });

  it("falls back to cached plans when loading plans fails", async () => {
    plansListMock.mockRejectedValue(new Error("plans service down"));
    window.localStorage.setItem(
      "concept_tree_plans_cache",
      JSON.stringify({
        plans: [{ id: "cached-plan", title: "Cached Plan", progress: 3, total: 8 }],
      }),
    );

    render(
      <AppProvider>
        <ContextProbe />
      </AppProvider>,
    );

    await waitFor(() => {
      expect(screen.getByTestId("app-loading")).toHaveTextContent("false");
    });

    expect(screen.getByTestId("plan-count")).toHaveTextContent("1");
    expect(screen.getByTestId("plan-progress")).toHaveTextContent("3");
    expect(toastApi.error).toHaveBeenCalledWith("加载学习计划失败，已显示本地缓存");
  });

  it("exposes degraded sync status for recoverable database errors", async () => {
    plansListMock.mockRejectedValue({
      name: "ApiError",
      code: "DATABASE_UNAVAILABLE",
      recoverable: true,
      message: "database unavailable",
    });
    window.localStorage.setItem(
      "concept_tree_plans_cache",
      JSON.stringify({
        plans: [{ id: "cached-plan", title: "Cached Plan", progress: 3, total: 8 }],
      }),
    );

    render(
      <AppProvider>
        <ContextProbe />
      </AppProvider>,
    );

    await waitFor(() => {
      expect(screen.getByTestId("app-loading")).toHaveTextContent("false");
    });

    expect(screen.getByTestId("sync-degraded")).toHaveTextContent("true");
    expect(screen.getByTestId("sync-message")).toHaveTextContent(
      "数据同步暂时不可用，本地内容仍可查看",
    );
  });
});
