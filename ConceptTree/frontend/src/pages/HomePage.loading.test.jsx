import React from "react";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import HomePage from "./HomePage.jsx";

function deferred() {
  let resolve;
  let reject;
  const promise = new Promise((res, rej) => {
    resolve = res;
    reject = rej;
  });
  return { promise, resolve, reject };
}

const {
  navigateMock,
  parseGoalMock,
  generateGraphMock,
  createPlanMock,
  toastErrorMock,
} = vi.hoisted(() => ({
  navigateMock: vi.fn(),
  parseGoalMock: vi.fn(),
  generateGraphMock: vi.fn(),
  createPlanMock: vi.fn(),
  toastErrorMock: vi.fn(),
}));

const userProfile = {
  occupation: "Engineer",
  education: "Bachelor",
  programmingLevel: "intermediate",
  mathLevel: "beginner",
  abilities: ["Python"],
  masteredKnowledge: ["variables"],
};

vi.mock("react-router-dom", () => ({
  useNavigate: () => navigateMock,
}));

vi.mock("../contexts/PlanContext", () => ({
  usePlanContext: () => ({
    userProfile,
    plans: [],
    actions: {
      createPlan: createPlanMock,
      archivePlan: vi.fn(),
      updatePlan: vi.fn(),
    },
  }),
}));

vi.mock("../contexts/AuthContext", () => ({
  useAuth: () => ({
    isAuthenticated: false,
    login: vi.fn(),
    register: vi.fn(),
    logout: vi.fn(),
  }),
}));

vi.mock("../contexts/ToastContext", () => ({
  useToast: () => ({
    error: toastErrorMock,
    success: vi.fn(),
  }),
}));

vi.mock("../services/api", () => ({
  aiApi: {
    parseGoal: parseGoalMock,
  },
  graphApi: {
    generate: generateGraphMock,
  },
}));

describe("HomePage loading scenes", () => {
  beforeEach(() => {
    createPlanMock.mockResolvedValue({ id: "plan-1" });
  });

  afterEach(() => {
    vi.clearAllMocks();
  });

  it("shows the goal analysis loader while parseGoal is pending", async () => {
    const parseDeferred = deferred();
    parseGoalMock.mockReturnValue(parseDeferred.promise);

    render(<HomePage />);

    fireEvent.change(screen.getByRole("textbox"), {
      target: { value: "layer normalization" },
    });
    fireEvent.click(screen.getByRole("button", { name: /生成图谱/i }));

    expect(await screen.findByText("AI 正在理解你的学习目标")).toBeInTheDocument();

    parseDeferred.resolve({
      interpretation: "理解 layer normalization",
      backgroundSummary: [],
      suggestedNodeCount: 5,
      shouldSplit: false,
      splitSuggestions: [],
    });

    await waitFor(() => {
      expect(screen.getByText("理解 layer normalization")).toBeInTheDocument();
    });
  });

  it("shows the graph generation loader after confirmation", async () => {
    parseGoalMock.mockResolvedValue({
      interpretation: "理解 layer normalization",
      backgroundSummary: [],
      suggestedNodeCount: 5,
      shouldSplit: false,
      splitSuggestions: [],
    });
    const generateDeferred = deferred();
    generateGraphMock.mockReturnValue(generateDeferred.promise);

    render(<HomePage />);

    fireEvent.change(screen.getByRole("textbox"), {
      target: { value: "layer normalization" },
    });
    fireEvent.click(screen.getByRole("button", { name: /生成图谱/i }));

    await waitFor(() => {
      expect(screen.getByText("理解 layer normalization")).toBeInTheDocument();
    });

    fireEvent.click(screen.getByRole("button", { name: /确认生成/i }));

    expect(await screen.findByText("正在为你生成学习图谱")).toBeInTheDocument();
    expect(screen.getByText(/构建核心概念/)).toBeInTheDocument();

    generateDeferred.resolve({ nodes: [], edges: [] });
  });
});
