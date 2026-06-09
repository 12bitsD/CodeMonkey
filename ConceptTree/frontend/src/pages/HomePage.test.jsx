import React from "react";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import HomePage from "./HomePage.jsx";

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

describe("HomePage confirm generation", () => {
  beforeEach(() => {
    parseGoalMock.mockResolvedValue({
      interpretation: "理解深度学习中的反向传播",
      backgroundSummary: [],
      suggestedNodeCount: 5,
      shouldSplit: false,
      splitSuggestions: [],
    });
    generateGraphMock.mockResolvedValue({ nodes: [], edges: [] });
    createPlanMock.mockResolvedValue({ id: "plan-1" });
  });

  afterEach(() => {
    vi.clearAllMocks();
  });

  it("passes the confirmed interpretation into graph generation instead of the raw input", async () => {
    render(<HomePage />);

    const rawInput = "我想理解深度学习中的反向传播，我有 Python 基础但数学一般";

    fireEvent.change(
      screen.getByPlaceholderText(
        "例如：我想理解反向传播在神经网络训练中的作用，我有 Python 基础但数学一般...",
      ),
      {
        target: { value: rawInput },
      },
    );

    fireEvent.click(screen.getByRole("button", { name: "生成图谱" }));

    await waitFor(() => {
      expect(screen.getByText("理解深度学习中的反向传播")).toBeInTheDocument();
    });

    fireEvent.click(screen.getByRole("button", { name: "确认生成" }));

    await waitFor(() => {
      expect(generateGraphMock).toHaveBeenCalledWith(
        rawInput,
        "理解深度学习中的反向传播",
        userProfile,
        "apply",
        expect.any(Function),
      );
    });
  });

  it("falls back to raw input when interpretation is empty", async () => {
    parseGoalMock.mockResolvedValue({
      interpretation: "",
      backgroundSummary: [],
      suggestedNodeCount: 5,
      shouldSplit: false,
      splitSuggestions: [],
    });

    render(<HomePage />);

    const rawInput = "fallback test input";

    fireEvent.change(
      screen.getByPlaceholderText(
        "例如：我想理解反向传播在神经网络训练中的作用，我有 Python 基础但数学一般...",
      ),
      {
        target: { value: rawInput },
      },
    );

    fireEvent.click(screen.getByRole("button", { name: "生成图谱" }));

    await waitFor(() => {
      expect(screen.getByText("fallback test input")).toBeInTheDocument();
    });

    fireEvent.click(screen.getByRole("button", { name: "确认生成" }));

    await waitFor(() => {
      expect(generateGraphMock).toHaveBeenCalledWith(
        rawInput,
        rawInput,
        userProfile,
        "apply",
        expect.any(Function),
      );
    });
  });

  it("falls back to raw input when interpretation is null", async () => {
    parseGoalMock.mockResolvedValue({
      interpretation: null,
      backgroundSummary: [],
      suggestedNodeCount: 5,
      shouldSplit: false,
      splitSuggestions: [],
    });

    render(<HomePage />);

    const rawInput = "null interpretation test";

    fireEvent.change(
      screen.getByPlaceholderText(
        "例如：我想理解反向传播在神经网络训练中的作用，我有 Python 基础但数学一般...",
      ),
      {
        target: { value: rawInput },
      },
    );

    fireEvent.click(screen.getByRole("button", { name: "生成图谱" }));

    await waitFor(() => {
      expect(screen.getByText("null interpretation test")).toBeInTheDocument();
    });

    fireEvent.click(screen.getByRole("button", { name: "确认生成" }));

    await waitFor(() => {
      expect(generateGraphMock).toHaveBeenCalledWith(
        rawInput,
        rawInput,
        userProfile,
        "apply",
        expect.any(Function),
      );
    });
  });
});
