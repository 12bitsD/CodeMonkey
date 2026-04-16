import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import MarkdownContent from "./MarkdownContent";

describe("MarkdownContent", () => {
  it("renders headings, lists, emphasis, code blocks, and links", () => {
    render(
      <MarkdownContent
        content={`# 标题

这是 **重点**，也是 \`inline code\`。

1. 第一项
2. 第二项

> 这是引用

\`\`\`js
const value = 1;
\`\`\`

[查看资料](https://example.com)`}
      />,
    );

    expect(screen.getByRole("heading", { name: "标题" })).toBeInTheDocument();
    expect(screen.getByText("重点").tagName).toBe("STRONG");
    expect(screen.getByText("inline code").tagName).toBe("CODE");
    expect(screen.getByText("第一项")).toBeInTheDocument();
    expect(screen.getByText("这是引用")).toBeInTheDocument();
    expect(screen.getByText("const value = 1;")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "查看资料" })).toHaveAttribute("href", "https://example.com");
  });
});
