import React from "react";
import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import TeachingDiagram from "./TeachingDiagram.jsx";


const diagram = {
  version: 1,
  title: "导数的几何意义",
  layout: "flow",
  nodes: [
    {
      id: "slope",
      title: "割线斜率",
      summary: "两个点之间的平均变化率",
      role: "support",
      details: { key_points: ["先固定两个点"] },
    },
    {
      id: "derivative",
      title: "导数",
      summary: "无限接近后的瞬时变化率",
      role: "core",
      details: {
        key_points: ["导数等于切线斜率"],
        example: "位移函数的导数是瞬时速度",
        misconception: "不是两个很小的量直接相除",
      },
    },
  ],
  edges: [
    { source: "slope", target: "derivative", relation: "prerequisite", label: "取极限" },
  ],
};


describe("TeachingDiagram", () => {
  it("opens the selected knowledge point details without injecting markup", () => {
    const { container } = render(<TeachingDiagram spec={diagram} />);

    fireEvent.click(screen.getByRole("button", { name: /导数：无限接近后的瞬时变化率/ }));

    expect(screen.getByRole("dialog", { name: "导数" })).toBeInTheDocument();
    expect(screen.getByText("导数等于切线斜率")).toBeInTheDocument();
    expect(screen.getByText("位移函数的导数是瞬时速度")).toBeInTheDocument();
    expect(screen.getByText("不是两个很小的量直接相除")).toBeInTheDocument();
    expect(container.querySelector("script")).toBeNull();
  });

  it("zooms only the internal canvas and resets it", () => {
    render(<TeachingDiagram spec={diagram} />);
    const rootStyle = document.documentElement.getAttribute("style");
    const canvas = screen.getByTestId("teaching-diagram-canvas");

    fireEvent.click(screen.getByRole("button", { name: "放大图表" }));
    expect(canvas.style.transform).toContain("scale(1.15)");
    expect(document.documentElement.getAttribute("style")).toBe(rootStyle);

    fireEvent.click(screen.getByRole("button", { name: "重置图表" }));
    expect(canvas.style.transform).toContain("scale(1)");
  });

  it("draws connectors between node boundaries so arrowheads stay visible", () => {
    const { container } = render(<TeachingDiagram spec={diagram} />);

    expect(container.querySelector('path[marker-end]')?.getAttribute('d'))
      .toBe('M 208 240 L 692 240');
  });

  it("allows compact pinned diagrams to fit narrow panels", () => {
    render(<TeachingDiagram spec={diagram} compact />);
    const canvas = screen.getByTestId("teaching-diagram-canvas");
    const zoomOut = screen.getByRole("button", { name: "缩小图表" });

    for (let index = 0; index < 10; index += 1) fireEvent.click(zoomOut);

    expect(canvas.style.transform).toContain("scale(0.32)");
  });
});
