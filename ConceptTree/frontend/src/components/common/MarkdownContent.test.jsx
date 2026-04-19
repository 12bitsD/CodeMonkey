import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import MarkdownContent from "./MarkdownContent";

describe("MarkdownContent", () => {
  it("renders headings, lists, emphasis, code blocks, and links", () => {
    render(
      <MarkdownContent
        content={`# Title

This is **important**, with \`inline code\`.

1. First
2. Second

> Quote

\`\`\`js
const value = 1;
\`\`\`

[Open docs](https://example.com)`}
      />,
    );

    expect(screen.getByRole("heading", { name: "Title" })).toBeInTheDocument();
    expect(screen.getByText("important").tagName).toBe("STRONG");
    expect(screen.getByText("inline code").tagName).toBe("CODE");
    expect(screen.getByText("First")).toBeInTheDocument();
    expect(screen.getByText("Quote")).toBeInTheDocument();
    expect(screen.getByText("const value = 1;")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Open docs" })).toHaveAttribute(
      "href",
      "https://example.com",
    );
  });

  it("renders inline and block math formulas with katex", () => {
    const { container } = render(
      <MarkdownContent
        content={`Pythagoras can be written as \\(a^2+b^2=c^2\\).

$$
\\frac{dy}{dx} = \\frac{dy}{du} \\times \\frac{du}{dx}
$$`}
      />,
    );

    expect(container.querySelectorAll(".katex").length).toBeGreaterThanOrEqual(2);
    expect(container.querySelector(".katex-display")).toBeInTheDocument();
  });
});
