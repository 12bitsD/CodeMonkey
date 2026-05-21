import React from "react";
import { render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

const { initializeMock, parseMock, renderMock } = vi.hoisted(() => ({
  initializeMock: vi.fn(),
  parseMock: vi.fn(),
  renderMock: vi.fn(),
}));

vi.mock("mermaid", () => ({
  default: {
    initialize: initializeMock,
    parse: parseMock,
    render: renderMock,
  },
}));

import MermaidDiagram from "./MermaidDiagram.jsx";

describe("MermaidDiagram", () => {
  it("shows a clean fallback and skips render when Mermaid syntax is invalid", async () => {
    document.body.insertAdjacentHTML(
      "beforeend",
      '<div data-testid="leaked-mermaid-error"><svg><g class="error-icon"></g><text class="error-text">Syntax error</text></svg></div>',
    );
    parseMock.mockResolvedValueOnce(false);

    render(<MermaidDiagram code={"graph TD\n  A -->"} />);

    expect(await screen.findByText("[图表渲染失败]")).toBeInTheDocument();
    expect(screen.queryByTestId("leaked-mermaid-error")).not.toBeInTheDocument();
    expect(renderMock).not.toHaveBeenCalled();
  });

  it("renders SVG only after parse succeeds", async () => {
    parseMock.mockResolvedValueOnce({ diagramType: "flowchart-v2" });
    renderMock.mockResolvedValueOnce({ svg: "<svg data-testid=\"diagram\"></svg>" });

    const { container } = render(<MermaidDiagram code={"graph TD\n  A-->B"} />);

    await waitFor(() => {
      expect(container.querySelector("svg")).toBeTruthy();
    });
    expect(renderMock).toHaveBeenCalledWith(
      expect.stringMatching(/^mermaid-/),
      "graph TD\n  A-->B",
      expect.any(HTMLElement),
    );
  });
});
