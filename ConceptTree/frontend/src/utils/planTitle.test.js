import { describe, expect, it } from "vitest";

import { compactPlanTitle } from "./planTitle";

describe("compactPlanTitle", () => {
  it("limits English summaries to seven words", () => {
    expect(
      compactPlanTitle(
        "Understand the mathematical foundations of backpropagation in neural networks",
      ),
    ).toBe("Understand the mathematical foundations of backpropagation in…");
  });

  it("limits Chinese summaries to fourteen characters", () => {
    expect(compactPlanTitle("系统学习反向传播的数学原理与工程实践")).toBe(
      "系统学习反向传播的数学原理…",
    );
  });

  it("leaves already concise titles unchanged", () => {
    expect(compactPlanTitle("Learn backpropagation")).toBe("Learn backpropagation");
  });
});
