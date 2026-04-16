import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import ChatMarkdownMessage from "./ChatMarkdownMessage";

describe("ChatMarkdownMessage", () => {
  it("renders markdown content for assistant messages", () => {
    render(<ChatMarkdownMessage content={"## 标题\n\n- 第一项\n- 第二项"} />);

    expect(screen.getByText("AI Reply")).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "标题" })).toBeInTheDocument();
    expect(screen.getByText("第一项")).toBeInTheDocument();
    expect(screen.getByText("第二项")).toBeInTheDocument();
  });
});
