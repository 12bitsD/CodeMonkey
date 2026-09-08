import React from "react";
import { act, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import DalleImage from "./DalleImage.jsx";
import { LanguageProvider } from "../../contexts/LanguageContext.jsx";

describe("DalleImage", () => {
  beforeEach(() => {
    window.localStorage.clear();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it("keeps showing the pending state during a normal 91-second generation", () => {
    vi.useFakeTimers();

    render(
      <LanguageProvider>
        <DalleImage id="image-pending" url="" reason="Learning concept" pending />
      </LanguageProvider>,
    );

    act(() => vi.advanceTimersByTime(91000));

    expect(screen.getByText("Creating image...")).toBeInTheDocument();
    expect(screen.queryByText("Architecture diagram")).not.toBeInTheDocument();
  });

  it("falls back to a localized architecture diagram when image generation is unavailable", () => {
    render(
      <LanguageProvider>
        <DalleImage id="image-1" url="" reason="Gradient checking" />
      </LanguageProvider>,
    );

    expect(screen.getByRole("img", { name: /Learning concept architecture/i })).toBeInTheDocument();
    expect(screen.getByText("Architecture diagram")).toBeInTheDocument();
    expect(screen.getByText("Concept")).toBeInTheDocument();
    expect(screen.getByText("Mechanism")).toBeInTheDocument();
    expect(screen.getByText("Outcome")).toBeInTheDocument();
  });

  it("does not render the internal image-decision reason in the fallback diagram", () => {
    const reason = "导数的几何意义——曲面沿不同方向坡度不同，属于 Mermaid 难以表达的3D空间关系，且文中明确用了登山类比，符合规则";
    window.localStorage.setItem("concept_tree_language", "zh-CN");

    render(
      <LanguageProvider>
        <DalleImage id="image-2" url="" reason={reason} />
      </LanguageProvider>,
    );

    expect(screen.getByRole("img", { name: "学习概念架构图" })).toBeInTheDocument();
    expect(screen.getByText("学习概念")).toBeInTheDocument();
    expect(screen.queryByText(reason)).not.toBeInTheDocument();
  });
});
