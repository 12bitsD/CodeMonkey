import React from "react";
import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import ConceptProgress from "./ConceptProgress.jsx";

describe("ConceptProgress", () => {
  it("counts passed, failed, and skipped concepts as progressed", () => {
    render(
      <ConceptProgress
        whatList={["概念 A", "概念 B", "概念 C", "概念 D"]}
        conceptsStatus={{
          0: "done",
          1: "failed",
          2: "skipped",
          3: "current",
        }}
        weakPoints={[]}
      />,
    );

    expect(screen.getByText("3 / 4")).toBeInTheDocument();
    expect(screen.getByText("概念 B").closest("div")).toHaveClass("text-red-700");
    expect(screen.getByText("概念 C").closest("div")).toHaveClass("text-amber-700");
  });
});
