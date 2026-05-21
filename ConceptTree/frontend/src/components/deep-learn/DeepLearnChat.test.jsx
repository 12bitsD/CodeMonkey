import React from "react";
import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import DeepLearnChat from "./DeepLearnChat.jsx";

const baseProps = {
  canSendMessage: true,
  uiFlags: { showCommands: false, showTestConfirm: null, showFailOptions: null },
  onSendMessage: vi.fn(),
  onSendCommand: vi.fn(),
};

describe("DeepLearnChat", () => {
  it("renders markdown inside question cards", () => {
    const { container } = render(
      <DeepLearnChat
        {...baseProps}
        isStreaming={false}
        messages={[
          {
            id: "q1",
            role: "assistant",
            kind: "questions",
            content: ["**诊断题** 假设你要创建数组，应该使用哪个函数？"],
          },
        ]}
      />,
    );

    expect(screen.getByText("诊断题")).toBeInTheDocument();
    expect(container.querySelector("strong")).toHaveTextContent("诊断题");
  });

  it("uses a full assistant bubble while waiting for a response", () => {
    const { container } = render(
      <DeepLearnChat
        {...baseProps}
        isStreaming
        messages={[
          { id: "a1", role: "assistant", kind: "text", content: "" },
        ]}
      />,
    );

    expect(screen.getByText("AI 回复")).toBeInTheDocument();
    const bubble = screen.getByText("AI 回复").parentElement;
    expect(bubble?.className).toContain("min-w-[min(440px,100%)]");
  });
});
