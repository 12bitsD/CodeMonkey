import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import ChatMarkdownMessage from "./ChatMarkdownMessage";

describe("ChatMarkdownMessage", () => {
  it("renders markdown content for assistant messages", () => {
    render(<ChatMarkdownMessage content={"## Heading\n\n- First\n- Second"} />);

    expect(screen.getByText("AI 回复")).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Heading" })).toBeInTheDocument();
    expect(screen.getByText("First")).toBeInTheDocument();
    expect(screen.getByText("Second")).toBeInTheDocument();
  });

  it("renders sources and search fallback state", () => {
    render(
      <ChatMarkdownMessage
        content="source-backed answer"
        searchStatus="fallback"
        sources={[
          {
            title: "Official docs",
            url: "https://example.com/docs",
            source: "example.com",
          },
        ]}
      />,
    );

    expect(
      screen.getByText("未获取到外部资料，已切换为普通回答。"),
    ).toBeInTheDocument();
    expect(screen.getByText("参考来源")).toBeInTheDocument();
    expect(
      screen.getByRole("link", { name: "Official docs example.com" }),
    ).toHaveAttribute("href", "https://example.com/docs");
  });
});
