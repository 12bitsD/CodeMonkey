import React from "react";
import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

vi.mock("./MermaidDiagram", () => ({
  default: ({ code }) => <div data-testid="mermaid-diagram">{code}</div>,
}));

import PinnedImages from "./PinnedImages.jsx";

describe("PinnedImages", () => {
  it("opens pinned images in an enlarged preview", () => {
    render(
      <PinnedImages
        pinned={[{ id: "img-1", url: "https://example.com/flow.png", caption: "流程图" }]}
        onUnpin={vi.fn()}
      />,
    );

    fireEvent.click(screen.getByRole("button", { name: /流程图/i }));

    expect(screen.getByRole("button", { name: "关闭大图" })).toBeInTheDocument();
    expect(screen.getAllByAltText("流程图")).toHaveLength(2);
  });

  it("opens pinned Mermaid diagrams in an enlarged preview", () => {
    render(
      <PinnedImages
        pinned={[{ id: "m-1", url: "mermaid:graph TD\nA-->B", caption: "流程图" }]}
        onUnpin={vi.fn()}
      />,
    );

    fireEvent.click(screen.getByRole("button", { name: /graph TD/i }));

    expect(screen.getByRole("button", { name: "关闭大图" })).toBeInTheDocument();
    expect(screen.getAllByTestId("mermaid-diagram")).toHaveLength(2);
  });

  it("does not open preview when unpinning", () => {
    const onUnpin = vi.fn();
    render(
      <PinnedImages
        pinned={[{ id: "img-1", url: "https://example.com/flow.png", caption: "流程图" }]}
        onUnpin={onUnpin}
      />,
    );

    fireEvent.click(screen.getByRole("button", { name: "取消钉图" }));

    expect(onUnpin).toHaveBeenCalledWith("img-1");
    expect(screen.queryByRole("button", { name: "关闭大图" })).not.toBeInTheDocument();
  });
});
