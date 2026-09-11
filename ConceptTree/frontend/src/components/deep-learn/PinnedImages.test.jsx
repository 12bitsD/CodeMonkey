import React from "react";
import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import PinnedImages from "./PinnedImages.jsx";

describe("PinnedImages", () => {
  it("renders typed diagrams as interactive pinned visuals", () => {
    render(
      <PinnedImages
        pinned={[{
          id: "diagram-1",
          kind: "diagram",
          caption: "导数关系图",
          content: {
            version: 1,
            title: "导数关系图",
            layout: "flow",
            nodes: [
              { id: "a", title: "割线", summary: "平均变化", details: {} },
              { id: "b", title: "切线", summary: "瞬时变化", role: "core", details: {} },
            ],
            edges: [{ source: "a", target: "b", relation: "prerequisite" }],
          },
        }]}
        onUnpin={vi.fn()}
      />,
    );

    expect(screen.getAllByText("导数关系图")).toHaveLength(2);
    fireEvent.click(screen.getByRole("button", { name: /切线：瞬时变化/ }));
    expect(screen.getByRole("dialog", { name: "切线" })).toBeInTheDocument();
  });

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
