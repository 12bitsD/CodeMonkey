import React from "react";
import { render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import HomePage from "./HomePage.jsx";

const {
  navigateMock,
  recommendNextMock,
} = vi.hoisted(() => ({
  navigateMock: vi.fn(),
  recommendNextMock: vi.fn(),
}));

vi.mock("react-router-dom", () => ({
  useNavigate: () => navigateMock,
}));

vi.mock("../contexts/PlanContext", () => ({
  usePlanContext: () => ({
    userProfile: {
      occupation: "Engineer",
      education: "Bachelor",
      programmingLevel: "intermediate",
      mathLevel: "beginner",
      abilities: ["Python"],
      masteredKnowledge: [],
    },
    plans: [
      {
        id: "plan_today",
        title: "Transformer 学习计划",
        progress: 2,
        total: 8,
        status: "active",
        lastAccess: "2026-04-15T10:00:00.000Z",
        studyFrequency: "daily",
        studyDaysPerWeek: 5,
        reminderEnabled: true,
        reminderTime: "20:00",
        targetEndDate: "2026-04-20T00:00:00.000Z",
      },
    ],
    actions: {
      createPlan: vi.fn(),
      archivePlan: vi.fn(),
      updatePlan: vi.fn(),
      pausePlan: vi.fn(),
      resumePlan: vi.fn(),
    },
  }),
}));

vi.mock("../contexts/AuthContext", () => ({
  useAuth: () => ({
    isAuthenticated: true,
    login: vi.fn(),
    register: vi.fn(),
    logout: vi.fn(),
  }),
}));

vi.mock("../contexts/ToastContext", () => ({
  useToast: () => ({
    error: vi.fn(),
    success: vi.fn(),
  }),
}));

vi.mock("../services/api", () => ({
  aiApi: {
    parseGoal: vi.fn(),
    recommendNext: recommendNextMock,
  },
  graphApi: {
    generate: vi.fn(),
  },
}));

describe("HomePage recommendation", () => {
  afterEach(() => {
    vi.clearAllMocks();
    window.localStorage.clear();
  });

  it("shows the recommended next-node reason for the top reminder plan", async () => {
    recommendNextMock.mockResolvedValue({
      recommended_node_id: "plan_today_n3",
      reason: "先补齐注意力机制，再进入更高层的 Transformer 结构会更顺。",
    });

    render(<HomePage />);

    await waitFor(() => {
      expect(recommendNextMock).toHaveBeenCalledWith(
        "plan_today",
        expect.objectContaining({ signal: expect.any(AbortSignal) }),
      );
    });

    expect(screen.getByText("AI 推荐节点")).toBeInTheDocument();
    expect(
      screen.getByText("先补齐注意力机制，再进入更高层的 Transformer 结构会更顺。"),
    ).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "去学习" })).toBeInTheDocument();
    const cached = JSON.parse(
      window.localStorage.getItem("concept_tree_today_recommendation"),
    );
    expect(cached.data.recommended_node_id).toBe("plan_today_n3");
  });

  it("uses the same-day cached recommendation without calling AI again", async () => {
    const today = new Date();
    const dateKey = [
      today.getFullYear(),
      String(today.getMonth() + 1).padStart(2, "0"),
      String(today.getDate()).padStart(2, "0"),
    ].join("-");

    window.localStorage.setItem(
      "concept_tree_today_recommendation",
      JSON.stringify({
        cacheKey:
          `${dateKey}|plan_today|2|8|active|2026-04-20T00:00:00.000Z`,
        data: {
          recommended_node_id: "plan_today_cached",
          reason: "今天已经算过一次，刷新时直接使用缓存。",
          recommendation_source: "ai",
        },
      }),
    );

    render(<HomePage />);

    await waitFor(() => {
      expect(
        screen.getByText("今天已经算过一次，刷新时直接使用缓存。"),
      ).toBeInTheDocument();
    });
    expect(recommendNextMock).not.toHaveBeenCalled();
  });
});
