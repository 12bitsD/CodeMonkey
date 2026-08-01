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
  it("renders deep headings and bare latex commands readably", () => {
    render(
      <MarkdownContent
        content={`##### 实际意义

若 \\mathbf{A}^\\top \\mathbf{A} 接近奇异，则 \\mu 很小。

\\[
f(\\mathbf{x}) = // \\mathbf{A}\\mathbf{x} - \\mathbf{b} //^2
\\]`}
      />,
    );

    expect(screen.getByRole("heading", { name: "实际意义" })).toBeInTheDocument();
    expect(screen.queryByText(/\\mathbf/)).not.toBeInTheDocument();
    expect(screen.getByText(/A\^T/)).toBeInTheDocument();
    expect(screen.getByText(/mu/)).toBeInTheDocument();
  });

  it("renders common unwrapped formulas and malformed matrix latex with KaTeX", () => {
    const { container } = render(
      <MarkdownContent
        content={`f_x = 2x, f_y = 2y 令 f_x = 0.

Hessian矩阵 H = \\beginbmatrix 2 & 0 \\\\ 0 & 2 \\endbmatrix.

Hessian行列式 \\det(H) = 4 > 0。`}
      />,
    );

    expect(container.querySelectorAll(".katex").length).toBeGreaterThan(0);
    expect(container.textContent).not.toContain("\\beginbmatrix");
    expect(container.textContent).not.toContain("\\det");
    expect(screen.getAllByText(/H =/).length).toBeGreaterThan(0);
  });

  it("renders markdown tables", () => {
    const { container } = render(
      <MarkdownContent
        content={`| 问题 | 调整措施 | 原理 |
| --- | --- | --- |
| 初期震荡剧烈 | 增大 β1 | 平滑梯度方向 |
| 后期收敛缓慢 | 减小 β2 | 提高自适应速度 |`}
      />,
    );

    expect(container.querySelector("table")).toBeInTheDocument();
    expect(screen.getByText("调整措施")).toBeInTheDocument();
    expect(screen.getByText("减小 β2")).toBeInTheDocument();
  });
  it("keeps fenced code readable on the light completion-note surface", () => {
    const { container } = render(
      <MarkdownContent content={'```python\nprint("visible")\n```'} />,
    );

    const pre = container.querySelector("pre");
    expect(pre).toHaveClass("bg-zinc-50", "text-zinc-800");
    expect(pre?.querySelector("code")).toHaveClass("bg-transparent", "text-inherit");
  });

  it("does not treat an English sentence around an assignment as one long formula", () => {
    const { container } = render(
      <MarkdownContent content="At theta = 2, a buggy implementation returns g = 11 instead of 12." />,
    );

    expect(
      [...container.querySelectorAll(".katex-html")]
        .some(element => element.textContent.includes("buggy")),
    ).toBe(false);
  });
});
